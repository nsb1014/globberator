"""Assemble a solifuge from a shell, a jaw and repeated articulated appendages."""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

from arthropod_recipe import validate
from arthropod_parts import Sculpture, limb_chain
from character_io import clay_material, export_character

DUTY = .64
STRIDE = .65
CYCLES = 2
ABDOMEN = ("Abdomen", "Abdomen.Mid", "Abdomen.Rear")


def body(s,shape):
    s.bone("Carapace",(0,-.10,.65),(0,-.95,.69))

    shells = []
    def oval(name,center,scale):
        shells.append((s.ellipsoid(name,center,scale),"Carapace"))
    oval("Prosoma",(0,-.40,.61),(.475,.89,.265))
    for y,w,d in [(.075,.415,.235),(-.20,.45,.248),(-.44,.46,.24)]:
        oval("Thoracic shield",(0,y,.705),(w,d,.224))
    oval("Head shield",(0,-.893,.727),(.528,.514,.323))
    oval("Median eye mound",(0,-1.285,.908),(.13,.117,.096))
    s.mount((0,0,0),shells)
    eye = (.065,-1.34,.949)
    s.mount(eye,[(s.ellipsoid("Median eye",eye,(.054,.049,.054)),"Carapace")])

    # One continuous abdomen. Transverse folds fade into the ventral envelope.
    rows = []
    for station in range(201):
        t = .001 + .998*station/200
        y = .065 + 1.965*t*shape["abdomen_length"]
        envelope = math.sin(math.pi*t)**.55 * (1.07-.15*t)
        row = []
        for j in range(64):
            angle = -math.tau*j/64
            c,h = math.cos(angle),math.sin(angle)
            dorsal = max(0,h)
            arc = t + .026*(1-dorsal)
            seam = math.exp(-(math.sin(math.pi*(arc*9+.20))/.32)**2)
            relief = 1-.132*seam*(.37+.63*dorsal)
            plate = (1-seam)*dorsal*math.exp(-((abs(c)-.49)/.26)**2)
            groove = .059*math.exp(-(c/.16)**2)*dorsal*envelope
            row.append((.548*shape["abdomen_width"]*envelope*c*relief,y,
                        .668+.033*math.sin(math.pi*t)+.394*envelope*h*relief-groove+.036*envelope*plate))
        rows.append(row)
    length = 1.965 * shape["abdomen_length"]
    shell = s.surface("Segmented abdomen",rows)
    s.mount((0,0,0),[(shell,ABDOMEN[0])])
    parent = "Carapace"
    for i,name in enumerate(ABDOMEN):
        s.bone(name,(0,.065+length*i/3,.668),(0,.065+length*(i+1)/3,.668),parent)
        parent = name
    # Blend rings across each hinge. The folds stay part of one continuous shell.
    groups = [shell.vertex_groups[ABDOMEN[0]]] + [shell.vertex_groups.new(name=n) for n in ABDOMEN[1:]]
    ring_size = len(rows[0])
    for row,ring in enumerate(rows):
        position = max(0., min(2., 3*(ring[0][1]-.065)/length-.5))
        joint = int(position)
        mix = position-joint
        indices = list(range(row*ring_size,(row+1)*ring_size))
        if joint:
            groups[0].remove(indices)
        groups[joint].add(indices,1-mix,"REPLACE")
        if mix:
            groups[joint+1].add(indices,mix,"REPLACE")


def chelicera(s,width):
    anchor = Vector((.196,-1.16,.695))
    hinge = Vector((.215,-1.58,.568))
    # Stations follow the fixed finger down over the shorter movable finger.
    keys = [( .224,-1.10,.682,.107,.13),(.232,-1.24,.694,.199,.232),
            (.228,-1.40,.709,.207,.231),(.207,-1.58,.710,.175,.190),
            (.184,-1.77,.705,.119,.115),(.168,-1.93,.678,.061,.061),
            (.157,-2.045,.654,.035,.039),(.154,-2.077,.585,.005,.008)]
    from scipy.interpolate import PchipInterpolator
    import numpy as np
    values = PchipInterpolator(range(len(keys)),keys,axis=0)(np.linspace(0,len(keys)-1,52))
    # Grow each jaw outward from its medial contour to keep the two pincers separate.
    rows = [[(x+w*(width-1)+w*width*math.cos(j*math.tau/32),y,z+h*math.sin(j*math.tau/32)) for j in range(32)]
            for x,y,z,w,h in values]
    fixed = "Chelicera.{side}"
    mobile = "Finger.{side}"
    tip = Vector((.155,-2.020,.574))
    parts = [(s.surface("Fixed cheliceral finger",rows),fixed)]
    lower = s.spindle("Movable finger",hinge,tip,[(0,.096),(.17,.100),(.52,.073),(.80,.039),(1,.006)],.61,-.052)
    parts.append((lower,mobile))
    for i in range(3):
        y = -1.74-.073*i
        tooth = s.spindle("Cutting tooth",(.173,y,.64),(.164,y-.015,.584),
                          [(0,.033),(.40,.028),(1,.003)])
        parts.append((tooth,fixed))
    for side,mount in s.mount(anchor,parts):
        jaw = fixed.format(side=side)
        s.bone(jaw,mount@anchor,mount@hinge,"Carapace")
        s.bone(mobile.format(side=side),mount@hinge,mount@tip,jaw)


def make_rig(s):
    data = bpy.data.armatures.new("Solifuge skeleton")
    rig = bpy.data.objects.new("Solifuge skeleton",data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name,(a,b,parent) in s.bones.items():
        bone = data.edit_bones.new(name)
        bone.head,bone.tail = a,b
        if parent:
            bone.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in s.meshes:
        obj.select_set(True)
    skin = s.meshes[0]
    bpy.context.view_layer.objects.active = skin
    bpy.ops.object.join()
    skin.name = "Solifuge clay"
    skin.parent = rig
    modifier = skin.modifiers.new("Skeleton","ARMATURE")
    modifier.object = rig
    skin.shape_key_add(name="Basis")
    for name, bone_prefix, axis, center, scale in [
        ("Abdomen width","Abdomen",0,0,.22), ("Abdomen depth","Abdomen",2,.67,.21),
        ("Jaw breadth","Chelicera.",0,0,.16)]:
        key = skin.shape_key_add(name=name)
        key.slider_min = -1
        groups = {g.index for g in skin.vertex_groups if g.name.startswith(bone_prefix)}
        for v in skin.data.vertices:
            if any(g.group in groups for g in v.groups):
                local_center = math.copysign(center,v.co.x) if axis == 0 else center
                key.data[v.index].co[axis] += (v.co[axis]-local_center)*scale
    return rig,skin


def solve_foot(points, foot_offset):
    hip,knee,ankle,toe = points
    # Keep the distal segment level. Solve the upper two links against the target
    # in the rest knee's bending plane, allowing a forward and vertical swing.
    target = ankle+foot_offset
    direction = target-hip
    reach = direction.length
    direction.normalize()
    upper,lower = (knee-hip).length,(ankle-knee).length
    along = (upper*upper-lower*lower+reach*reach)/(2*reach)
    if abs(along) > upper+1e-5:
        raise ValueError("Foot target exceeds limb reach")
    pole = knee-hip
    pole = (pole-direction*direction.dot(pole)).normalized()
    bend = hip + along*direction + math.sqrt(max(0,upper*upper-along*along))*pole
    return [(knee-hip).rotation_difference(bend-hip),
            (ankle-knee).rotation_difference(target-bend), Quaternion()]


def bake(rig,chains):
    scene = bpy.context.scene
    scene.frame_start = 0
    scene.render.fps = 24
    rig.animation_data_create()
    for clip,frames in [("Idle",48),("Walk",64)]:
        walk = clip == "Walk"
        action = bpy.data.actions.new(clip)
        action.use_fake_user = True
        rig.animation_data.action = action
        for frame in range(frames+1):
            t = frame/frames
            cycle = t*(CYCLES if walk else 1)
            phase = math.tau*cycle
            # Offset the body toward the supporting tripod and rise over midstance.
            shift = (Vector((.053*math.cos(phase-1.9),0,.034*math.cos(2*phase-3.8)))
                     if walk else Vector((0,0,.021*math.sin(phase))))
            rotation = {}
            for i,name in enumerate(ABDOMEN):
                breath = math.sin(phase-.80*i)
                pitch = (.046+.020*i)*breath
                yaw = (.032+.012*i)*math.sin(phase-.80*i-.55) if walk else 0.
                rotation[name] = Quaternion((0,0,1),yaw) @ Quaternion((1,0,0),pitch)
            for role,side,names,points,offset in chains:
                sign = 1 if side == "L" else -1
                if role == "foot":
                    delta = -shift
                    if walk:
                        f = (cycle+offset)%1
                        swing = max(0,(f-DUTY)/(1-DUTY))
                        ease = swing**3*(10-15*swing+6*swing*swing)
                        delta.y += STRIDE*(f-DUTY/2-ease)
                        delta.z += .235*math.sin(math.pi*swing)**2
                    rotation.update(zip(names,solve_foot(points,delta),strict=True))
                else:
                    # One palp reaches as its partner recovers. The finer sensory
                    # pair follows on a shorter arc, slightly behind the palps.
                    beat = phase + (math.pi if side == "R" else 0)
                    palp = role == "palp"
                    for i,name in enumerate(names):
                        probe = beat-.25*i-(0 if palp else .85)
                        sweep = (.158 if palp else .078)*math.sin(probe)
                        lift = (.088 if palp else .052)*math.cos(probe)
                        rotation[name] = Quaternion((0,0,1),sign*sweep) @ Quaternion((1,0,0),lift)
            for side,sign in [("L",1),("R",-1)]:
                # A short gape follows the reach on this side.
                pulse = ((1+sign*math.sin(phase-.65))/2)**3
                jaw = Quaternion((0,0,1),sign*(.012+.045*pulse))
                rotation["Chelicera."+side] = jaw
                rotation["Finger."+side] = jaw @ Quaternion((1,0,0),.032+.17*pulse)
            for pb in rig.pose.bones:
                inherited = rotation.get(pb.parent.name,Quaternion()) if pb.parent else Quaternion()
                rest = pb.bone.matrix_local.to_quaternion()
                pb.rotation_quaternion = rest.inverted() @ inherited.inverted() @ rotation.get(pb.name,inherited) @ rest
                pb.keyframe_insert("rotation_quaternion",frame=frame,group=pb.name)
            root = rig.pose.bones["Carapace"]
            travel = -STRIDE*cycle if walk else 0
            root.location = root.bone.matrix_local.to_quaternion().inverted() @ (shift + Vector((0,travel,0)))
            root.keyframe_insert("location",frame=frame,group=root.name)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation="LINEAR"
    rig.animation_data.action=None
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    scene.frame_set(0)
    bpy.context.view_layer.update()


def build(recipe, output, review):
    validate(recipe)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sculpt = Sculpture(clay_material())
    body(sculpt,recipe["shape"])
    chelicera(sculpt,recipe["shape"]["jaw_width"])
    chains = []
    foot_count = 0
    for mount in recipe["mounts"]:
        for side,names,points in limb_chain(sculpt,mount):
            offset = ((foot_count % 2)*.5 + (.5 if side == "R" else 0)) % 1
            chains.append((mount["role"],side,names,points,offset))
        if mount["role"] == "foot":
            foot_count += 1
    rig,skin = make_rig(sculpt)
    bake(rig,chains)
    export_character(rig,skin,output)
    if review:
        review.mkdir(parents=True,exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str((review/"Solifuge.blend").resolve()))
    print(f"WROTE {output}, {len(sculpt.bones)} bones, {len(skin.data.vertices)} vertices")
