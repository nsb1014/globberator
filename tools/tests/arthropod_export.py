"""Review a rigged arthropod after GLB reimport, using only its recipe and export."""
import argparse
import json
import math
from itertools import combinations
from scipy.spatial import cKDTree
import sys
from pathlib import Path

import numpy as np
import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument("model",type=Path)
parser.add_argument("recipe",type=Path)
parser.add_argument("--legs",type=int,help="Independent expected walking foot count")
args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from locomotion import Gait

recipe = json.loads(args.recipe.read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(args.model.resolve()))
rig, = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
skin, = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.find_armature() == rig]
assert len(skin.data.materials) == 1
assert set(k.name for k in skin.data.shape_keys.key_blocks) == {"Basis","Abdomen width","Abdomen depth","Jaw breadth"}
bones = rig.data.bones
assert len(bones) == 8+sum(3 if m.get("center") else 6 for m in recipe["mounts"])
assert all(math.isfinite(c) for v in skin.data.vertices for c in v.co)
# The inner edges of the two fixed fingers stay on their own sides through
# both limits of the live jaw-breadth control.
jaw_key = skin.data.shape_keys.key_blocks["Jaw breadth"]
for side,sign in (("L",1),("R",-1)):
    jaw = skin.vertex_groups["Chelicera."+side].index
    for vertex in skin.data.vertices:
        if any(g.group == jaw for g in vertex.groups):
            x = vertex.co.x
            dx = jaw_key.data[vertex.index].co.x-x
            assert sign*x-abs(dx) > 0, (side,"jaw crosses midline")
# Sample the actual distal mesh of each palp and the dorsal/ventral surfaces
# of the front and rear abdomen. This also catches an animated but unbound rig.
def surface_vertices(name):
    group = skin.vertex_groups[name].index
    return [v.co.copy() for v in skin.data.vertices
            if any(g.group == group and g.weight > .99 for g in v.groups)]

def deformed(name,point):
    return rig.pose.bones[name].matrix @ bones[name].matrix_local.inverted() @ point

abdomen_axes = {}
for name in ("Abdomen","Abdomen.Rear"):
    verts = surface_vertices(name)
    abdomen_axes[name] = (max(verts,key=lambda v:v.z),min(verts,key=lambda v:v.z))
finger_tips = {side:min(surface_vertices("Finger."+side),key=lambda v:v.y) for side in ("L","R")}
palps = {}
points = {}
outer_axes = {}
sockets = {}
patches = {}
for mount in recipe["mounts"]:
    for side in (("C",) if mount.get("center") else ("L","R")):
        base = mount["id"]
        parent = "Carapace"
        samples = []
        for level in ("Base","Shin","Tip"):
            name = f"{base}.{level}.{side}"
            assert bones[name].parent.name == parent
            a = bones[name].head_local
            if side == "C":
                assert abs(a.x) < .0001
            else:
                counterpart = bones[f"{base}.{level}.{'R' if side == 'L' else 'L'}"]
                b = counterpart.head_local
                assert (a-Vector((-b.x,b.y,b.z))).length < .0001
            # Shared tissue at the shoulder is intentional. Beyond the body,
            # distinct appendages need space for their tapered shells.
            for i in range(17):
                point = a.lerp(bones[name].tail_local,i/16)
                if abs(point.x) > .75:
                    samples.append(tuple(point))
            parent = name
        outer_axes[base+"."+side] = samples
        verts = surface_vertices(name)
        if mount["role"] == "palp":
            hip = bones[f"{base}.Base.{side}"].head_local
            tip = max(verts,key=lambda v:(v-hip).length_squared)
            # Measure outward sweep about each mount, regardless of the recipe angle.
            reach = tip-hip
            tangent = Vector((-reach.y,reach.x,0)).normalized()
            palps[name] = (tip,tangent if side == "L" else -tangent)
        sole = min(verts,key=lambda v:v.z).copy()
        if mount["role"] == "foot":
            assert abs(sole.z) < .001, (name,"rest contact",sole.z)
            points[name] = sole
            sockets[name] = bones[f"{base}.Base.{side}"].head_local
            flat = np.array([tuple(v) for v in verts if v.z < .0001])
            assert len(flat) >= 8 and np.linalg.norm(np.ptp(flat,axis=0)) > .07, (name,"sole patch")
            # Check opposing edges as well as the lowest point to catch rocking on one vertex.
            patches[name] = [Vector(flat[i]) for i in {flat[:,axis].argmin() for axis in (0,1)}
                                                   | {flat[:,axis].argmax() for axis in (0,1)}]
        else:
            assert sole.z > .08, (name,"rest clearance",sole.z)
if args.legs is not None:
    assert len(points) == args.legs, ("walking feet",len(points),args.legs)
assert len({(round(p.x,3),round(p.y,3)) for p in points.values()}) == len(points)
for (a,first),(b,second) in combinations(outer_axes.items(),2):
    if first and second:
        separation = min(cKDTree(first).query(second)[0])
        assert separation > .115, (a,b,"overlapping neutral appendages",separation)
for track in rig.animation_data.nla_tracks:
    track.mute = True
gait = Gait(sockets)
if not points:
    abdomen_groups = {g.index for g in skin.vertex_groups if g.name.startswith("Abdomen")}
    belly_ids = [v.index for v in skin.data.vertices if any(g.group in abdomen_groups and g.weight > 0 for g in v.groups)]
    assert abs(min(skin.data.vertices[i].co.z for i in belly_ids)) < .001, "belly rest height"
scene = bpy.context.scene
for clip in ("Idle","Walk"):
    action = next(a for a in bpy.data.actions if a.name.startswith(clip))
    rig.animation_data.action = action
    start,end = map(round,action.frame_range)
    planted = {}
    rear_bend = []
    root_heights = []
    sway = []
    abdomen_tilt = {name:[] for name in abdomen_axes}
    palp_reach = {name:[] for name in palps}
    jaw_gape = {side:[] for side in ("L","R")}
    lifts = dict.fromkeys(points,0)
    raised = set()
    peak = dict.fromkeys(points,0)
    slip,lowest,minimum_support = 0.,1.,len(points)
    footprint_error = 0.
    for sample in range((end-start)*4+1):
        scene.frame_set(start+sample//4,subframe=(sample%4)/4)
        root = rig.pose.bones["Carapace"].head
        if sample == 0:
            first_root = root.copy()
        root_heights.append(root.z)
        sway.append(root.x)
        for name,(top,bottom) in abdomen_axes.items():
            axis = (deformed(name,top)-deformed(name,bottom)).normalized()
            abdomen_tilt[name].append(axis.y)
        for name,(landmark,tangent) in palps.items():
            p = deformed(name,landmark)-root
            palp_reach[name].append(p.dot(tangent))
            assert p.z+root.z > .08, (name,"palp grazes floor")
        for side in jaw_gape:
            name = "Finger."+side
            jaw = "Chelicera."+side
            tip = finger_tips[side]
            jaw_gape[side].append(deformed(jaw,tip).z-deformed(name,tip).z)
        count = 0
        cycle = 2*sample/((end-start)*4)
        if not points and sample%4 == 0:
            actual = skin.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            co = np.empty(len(actual.vertices)*3,dtype=np.float32)
            actual.vertices.foreach_get("co",co)
            heights = co.reshape(-1,3)[:,2]
            assert abs(heights[belly_ids].min()) < .002 and heights.min() > -.002, (clip,"body contact")
            rear = rig.pose.bones["Abdomen.Rear"]
            rear_bend.append((rear.tail-rear.head).normalized().x)
        for name,sole in points.items():
            p = deformed(name,sole)
            phase = (cycle-gait.touchdown[name])%1
            # Exclude the fractional frame straddling liftoff or touchdown from the
            # exact footprint check. The support-count and penetration tests include it.
            margin = 1/((end-start)/2)
            if clip == "Idle" or margin <= phase <= gait.duty-margin:
                anchor = Vector((0,0,0)) if clip == "Idle" else Vector((0,-.65*(cycle-phase+gait.duty/2),0))
                for vertex in patches[name]:
                    footprint_error = max(footprint_error,(deformed(name,vertex)-vertex-anchor).length)
            if p.z > .10 and name not in raised:
                raised.add(name)
                lifts[name] += 1
            elif p.z < .001:
                raised.discard(name)
            lowest = min(lowest,p.z)
            peak[name] = max(peak[name],p.z)
            if p.z < .001:
                count += 1
                if name in planted:
                    slip = max(slip,(planted[name]-p).length)
                else:
                    planted[name] = p.copy()
            else:
                planted.pop(name,None)
        minimum_support = min(minimum_support,count)
    # Over one cycle, the rear flexion peak should follow the front by
    # a visible fraction of a beat. Compare deformed surface axes.
    period = (len(root_heights)-1)//(2 if clip == "Walk" else 1)
    front,rear = (np.asarray(values[:period]) for values in abdomen_tilt.values())
    if points:
        assert np.ptp(front) > .07 and np.ptp(rear) > .12, (clip,"abdomen flexion")
        delay = (np.argmax(rear)-np.argmax(front)) % period / period
        assert .12 < delay < .38, (clip,"abdomen lag",delay)
    for name,left in palp_reach.items():
        if name.endswith(".L"):
            right = palp_reach[name[:-1]+"R"]
            assert min(np.ptp(left),np.ptp(right)) > .12, (clip,name,"palp sweep")
            assert np.corrcoef(left,right)[0,1] < -.8, (clip,name,"palp alternation")
    assert min(np.ptp(values) for values in jaw_gape.values()) > .045, (clip,"jaw gape")
    assert np.corrcoef(jaw_gape["L"],jaw_gape["R"])[0,1] < -.65, (clip,"jaw alternation")
    travel = first_root.y-root.y
    assert lowest > -.002 and slip < .008 and footprint_error < .001, (clip,lowest,slip,footprint_error)
    if clip == "Walk":
        if points:
            assert min(peak.values()) > .14 and minimum_support == len(points)-1, (clip,peak,minimum_support)
            assert set(lifts.values()) == {2}, (clip,"swing count",lifts)
        else:
            assert np.ptp(sway) > .08 and np.ptp(root_heights) < .001 and np.ptp(rear_bend) > .35
        assert abs(travel-1.30) < .002
    else:
        assert minimum_support == len(points) and abs(travel) < .001
    print(f"{clip}: support >= {minimum_support}, footprint error {footprint_error:.6f}, travel {travel:.3f}")
print(f"PASS: {len(bones)} joints and {len(points)} walking feet")
