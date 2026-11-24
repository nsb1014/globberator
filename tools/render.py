"""Render the exported GLB so the review uses the same mesh delivered to the user."""
import argparse
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument("model",type=Path)
parser.add_argument("folder",type=Path)
parser.add_argument("--clip",choices=["still","turn","walk"],default="still")
args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
args.folder.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(args.model.resolve()))
rig=next(o for o in bpy.context.scene.objects if o.type=="ARMATURE")
if rig.animation_data:
    for t in rig.animation_data.nla_tracks:t.mute=True
    rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis.identity()
scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.samples=112 if args.clip=="still" else 12
scene.cycles.use_denoising=False
scene.render.resolution_x=800 if args.clip=="still" else 450
scene.render.resolution_y=scene.render.resolution_x
scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new("Studio")
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.49,.52,.56,1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value=.28
def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
def light(name,loc,power,size,color):
    data=bpy.data.lights.new(name,"AREA");data.energy=power;data.shape="DISK";data.size=size;data.color=color
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc;aim(obj,(0,0,2.5))
light("Softbox",(-3.6,-5.5,8.2),720,5,(1,.957,.90))
light("Fill",(4,-3,5),310,3.6,(.88,.925,1))
light("Rim",(1.5,3,7.2),920,3.2,(.88,.92,1))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.019))
floor=bpy.context.object
mat=bpy.data.materials.new("Studio floor");mat.diffuse_color=(.18,.205,.23,1);floor.data.materials.append(mat)
cam_data=bpy.data.cameras.new("Turntable camera");cam_data.type="ORTHO";cam_data.ortho_scale=5.63
cam=bpy.data.objects.new("Camera",cam_data);scene.collection.objects.link(cam);scene.camera=cam
if args.clip=="walk":
    action=next(a for a in bpy.data.actions if a.name.split("_")[0].startswith("Walk") or a.name.startswith("Walk"))
    rig.animation_data.action=action
length={"still":1,"turn":48,"walk":32}[args.clip]
for i in range(length):
    if args.clip=="walk":scene.frame_set(i+1)
    angle={"still":.18,"turn":.18+2*math.pi*i/48,"walk":.65}[args.clip]
    cam.location=(10*math.sin(angle),-10*math.cos(angle),3.01)
    aim(cam,(0,0,2.43))
    scene.render.filepath=str((args.folder/f"{args.clip}-{i:03}.png").resolve())
    bpy.ops.render.render(write_still=True)
