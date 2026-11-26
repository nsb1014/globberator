"""Review the actual exported model in the source lighting and eight clay views."""
from pathlib import Path
import json
import math
import os
import struct
import sys

import bmesh
import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "hummingbird"
sys.path.insert(0,str(ROOT))
from polyforge import render

bpy.ops.wm.open_mainfile(filepath=str(OUT/"hummingbird.blend"))
for ob in list(bpy.context.scene.objects):
    if ob.type in ("MESH","ARMATURE"):
        bpy.data.objects.remove(ob,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(OUT/"hummingbird.glb"))
scene=bpy.context.scene
rig=next(ob for ob in scene.objects if ob.type=="ARMATURE")
meshes=[ob for ob in scene.objects if ob.type=="MESH" and ob.parent==rig]
assert len(meshes)==1 and len(rig.data.bones)==11
for ob in scene.objects:
    if ob.type=="MESH" and ob not in meshes:
        ob.hide_render=True
lo,hi=render.bounds(meshes)
physical_max=max(hi-lo)*scene.unit_settings.scale_length
assert .105<physical_max<.20, physical_max

with (OUT/"hummingbird.glb").open("rb") as file:
    file.read(12)
    n,_=struct.unpack("<II",file.read(8))
    manifest=json.loads(file.read(n))
assert any("COLOR_0" in p["attributes"] for m in manifest["meshes"] for p in m["primitives"])
audit={"max_extent_m":round(physical_max,4),"bones":len(rig.data.bones),"triangles":0,"boundary_edges":0}
for ob in meshes:
    ob.data.calc_loop_triangles()
    audit["triangles"]+=len(ob.data.loop_triangles)
    bm=bmesh.new()
    bm.from_mesh(ob.data)
    assert all(math.isfinite(c) for v in bm.verts for c in v.co)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    audit["boundary_edges"]+=sum(not e.is_manifold for e in bm.edges)
    assert bm.calc_volume(signed=True)>0
    bm.free()
assert audit["triangles"]<220000 and audit["boundary_edges"]==0,audit
feet=[rig.pose.bones[f"{side} foot"] for side in ("Left","Right")]
mesh=meshes[0]
for foot in feet:
    side=foot.name.split()[0]
    leg=rig.pose.bones[f"{side} leg"]
    assert foot.parent==leg and leg.parent.name=="Body"
    assert mesh.vertex_groups.get(foot.name) is not None
    assert mesh.vertex_groups.get(leg.name) is not None
    pivot=rig.matrix_world@foot.head
    assert (pivot-rig.matrix_world@leg.tail).length<1e-5
    tucked=rig.matrix_world@foot.tail
    # Blender world +Y points rearward, +Z points up.
    assert tucked.y>pivot.y and tucked.z>pivot.z
    axis=(rig.matrix_world@foot.matrix).to_3x3().inverted()@Vector((1,0,0))
    foot.rotation_mode="QUATERNION"
    foot.rotation_quaternion=Quaternion(axis.normalized(),math.radians(-40))
    bpy.context.view_layer.update()
    lowered=rig.matrix_world@foot.tail
    assert lowered.z<tucked.z-.02 and (rig.matrix_world@foot.head-pivot).length<1e-5
    foot.rotation_quaternion=Quaternion()
    bpy.context.view_layer.update()
audit["articulated_feet"]=len(feet)
print("REIMPORT AUDIT",audit,flush=True)
(OUT/"geometry.json").write_text(json.dumps(audit,indent=2)+"\n")

cam=scene.camera
saved_location=cam.location.copy()
saved_rotation=cam.rotation_euler.copy()
saved_scale=cam.data.ortho_scale
test=bool(os.environ.get("HUMMINGBIRD_DRAFT"))
review=OUT/"views"
review.mkdir(exist_ok=True)
original_world=scene.world
clay_world=bpy.data.worlds.new("Charcoal clay background")
scene.world=clay_world
clay_world.color=(.020,.024,.029)
scene.render.engine="BLENDER_WORKBENCH"
scene.display.render_aa="8"
sh=scene.display.shading
sh.light="STUDIO"
sh.color_type="SINGLE"
sh.single_color=(.77,.78,.79)
sh.background_type="WORLD"
sh.show_cavity=True
sh.cavity_type="WORLD"
sh.cavity_valley_factor=1.0
sh.cavity_ridge_factor=.5
sh.show_shadows=False
scene.render.resolution_x=920
scene.render.resolution_y=727
render.render(str(OUT/"hummingbird-clay.png"),transparent=False)

if not test:
    scene.render.resolution_x=360
    scene.render.resolution_y=350
    for yaw,pitch in [(0,9),(45,16),(90,9),(135,16),(180,9),(225,16),(270,9),(315,16)]:
        render.clay_camera(cam,meshes,yaw,pitch)
        render.render(str(review/f"{yaw:03}.png"),transparent=False)
    scene.render.resolution_x=640
    scene.render.resolution_y=520
    focus=sum((rig.matrix_world@foot.head for foot in feet),Vector())/len(feet)
    focus+=Vector((0,.01,-.008))
    cam.data.ortho_scale=.40
    for name,direction in (("profile",(1,-.22,-.24)),("underside",(.30,-.42,-1))):
        d=Vector(direction).normalized()
        cam.location=focus+d
        cam.rotation_euler=(-d).to_track_quat("-Z","Y").to_euler()
        render.render(str(OUT/f"feet-{name}.png"),transparent=False)
cam.location=saved_location
cam.rotation_euler=saved_rotation
cam.data.ortho_scale=saved_scale
scene.world=original_world
scene.render.engine="CYCLES"
scene.cycles.samples=16 if test else 64
scene.cycles.use_denoising=False
scene.render.resolution_x=690 if test else 1050
scene.render.resolution_y=545 if test else 830
render.render(str(OUT/"hummingbird-alpha.png"),transparent=True)
