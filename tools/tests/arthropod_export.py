"""Review a rigged arthropod after GLB reimport, using only its recipe and export."""
import argparse
import json
import math
from itertools import combinations
from scipy.spatial import cKDTree
import sys
from pathlib import Path

import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument("model",type=Path)
parser.add_argument("recipe",type=Path)
args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
recipe = json.loads(args.recipe.read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(args.model.resolve()))
rig, = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
skin, = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.find_armature() == rig]
assert len(skin.data.materials) == 1
assert set(k.name for k in skin.data.shape_keys.key_blocks) == {"Basis","Abdomen width","Abdomen depth","Jaw breadth"}
bones = rig.data.bones
assert len(bones) == 6+6*len(recipe["mounts"])
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
points = {}
outer_axes = {}
for mount in recipe["mounts"]:
    for side in ("L","R"):
        base = mount["id"]
        parent = "Carapace"
        samples = []
        for level in ("Base","Shin","Tip"):
            name = f"{base}.{level}.{side}"
            assert bones[name].parent.name == parent
            counterpart = bones[f"{base}.{level}.{'R' if side == 'L' else 'L'}"]
            a,b = bones[name].head_local, counterpart.head_local
            assert (a-Vector((-b.x,b.y,b.z))).length < .0001
            # Shared tissue at the shoulder is intentional. Beyond the body,
            # distinct appendages need space for their tapered shells.
            for i in range(17):
                point = a.lerp(bones[name].tail_local,i/16)
                if abs(point.x) > .75:
                    samples.append(tuple(point))
            parent = name
        outer_axes[base+"."+side] = samples
        tip = skin.vertex_groups[name].index
        verts = [v.co for v in skin.data.vertices if any(g.group == tip and g.weight > .99 for g in v.groups)]
        sole = min(verts,key=lambda v:v.z).copy()
        if mount["role"] == "foot":
            assert abs(sole.z) < .001, (name,"rest contact",sole.z)
            points[name] = sole
        else:
            assert sole.z > .12, (name,"rest clearance",sole.z)
assert len({(round(p.x,3),round(p.y,3)) for p in points.values()}) == len(points)
for (a,first),(b,second) in combinations(outer_axes.items(),2):
    if first and second:
        separation = min(cKDTree(first).query(second)[0])
        assert separation > .115, (a,b,"overlapping neutral appendages",separation)
for track in rig.animation_data.nla_tracks:
    track.mute = True
scene = bpy.context.scene
for clip in ("Idle","Walk"):
    action = next(a for a in bpy.data.actions if a.name.startswith(clip))
    rig.animation_data.action = action
    start,end = map(round,action.frame_range)
    planted = {}
    peak = dict.fromkeys(points,0)
    slip,lowest,minimum_support = 0.,1.,len(points)
    for sample in range((end-start)*4+1):
        scene.frame_set(start+sample//4,subframe=(sample%4)/4)
        root = rig.pose.bones["Carapace"].head
        if sample == 0:
            first_root = root.copy()
        count = 0
        for name,sole in points.items():
            p = rig.pose.bones[name].matrix @ bones[name].matrix_local.inverted() @ sole
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
    travel = first_root.y-root.y
    assert lowest > -.002 and slip < .004, (clip,lowest,slip)
    if clip == "Walk":
        assert min(peak.values()) > .1 and minimum_support >= len(points)//2
        assert abs(travel-1.30) < .002
    else:
        assert minimum_support == len(points) and abs(travel) < .001
    print(f"{clip}: support >= {minimum_support}, sole drift {slip:.6f}, forward travel {travel:.3f}")
print(f"PASS: {len(bones)} joints and {len(points)} distinct planted feet")
