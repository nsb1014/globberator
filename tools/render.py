"""Render the exported GLB so the review uses the same mesh delivered to the user."""
import argparse
import math
import sys
import subprocess
import tempfile
import numpy as np
from pathlib import Path
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument("model",type=Path)
parser.add_argument("folder",type=Path)
parser.add_argument("--clip",choices=["still","turn","walk"],default="still")
parser.add_argument("--oidn",type=Path,help="Optional oidnDenoise executable for linear-light CPU denoising")
parser.add_argument("--azimuth",type=float,help="Camera angle in degrees from the front, or starting angle for a turntable")
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
scene.cycles.samples=112 if args.clip=="still" else 64
scene.cycles.adaptive_threshold=.05
scene.cycles.adaptive_min_samples=16
scene.cycles.max_bounces=3
scene.cycles.sample_clamp_indirect=2.5
scene.cycles.use_denoising=False
scene.render.resolution_x=800 if args.clip=="still" else 576
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
light("Softbox",(-4.2,-4.0,8.2),760,3.1,(1,.957,.90))
light("Fill",(4,-3,5),310,3.6,(.88,.925,1))
light("Rim",(1.5,3,7.2),920,3.2,(.88,.92,1))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.0001))
floor=bpy.context.object
mat=bpy.data.materials.new("Studio floor");mat.diffuse_color=(.18,.205,.23,1);floor.data.materials.append(mat)
cam_data=bpy.data.cameras.new("Turntable camera");cam_data.type="ORTHO";cam_data.ortho_scale=5.63
cam=bpy.data.objects.new("Camera",cam_data);scene.collection.objects.link(cam);scene.camera=cam
if args.clip=="walk":
    action=next(a for a in bpy.data.actions if a.name.split("_")[0].startswith("Walk") or a.name.startswith("Walk"))
    rig.animation_data.action=action
def render_frame(destination):
    if not args.oidn:
        scene.render.filepath=str(destination)
        bpy.ops.render.render(write_still=True)
        return
    # Feed scene-linear radiance to OIDN, then apply the same display transform
    # as the ordinary Blender PNG output. Each frame is filtered independently.
    with tempfile.TemporaryDirectory(dir=args.folder) as tmp:
        tmp=Path(tmp)
        scene.render.image_settings.file_format="OPEN_EXR"
        scene.render.filepath=str((tmp/"raw.exr").resolve())
        bpy.ops.render.render(write_still=True)
        raw=bpy.data.images.load(scene.render.filepath)
        width,height=raw.size
        rgba=np.empty((height,width,4),dtype=np.float32)
        raw.pixels.foreach_get(rgba.ravel())
        with (tmp/"color.pfm").open("wb") as stream:
            stream.write(f"PF\n{width} {height}\n-1.0\n".encode())
            rgba[:,:,:3].astype("<f4").tofile(stream)
        subprocess.run([str(args.oidn.resolve()),"--device","cpu","--hdr",str(tmp/"color.pfm"),
                        "--output",str(tmp/"clean.pfm"),"--threads","3","--affinity","0"],
                       check=True,stdout=subprocess.DEVNULL)
        with (tmp/"clean.pfm").open("rb") as stream:
            magic=stream.readline().strip()
            dimensions=stream.readline().split()
            scale=float(stream.readline())
            if magic!=b"PF" or list(map(int,dimensions))!=[width,height] or scale>=0:
                raise ValueError("Unexpected denoiser output format")
            rgba[:,:,:3]=np.fromfile(stream,dtype="<f4").reshape(height,width,3)
        raw.pixels.foreach_set(rgba.ravel())
        raw.update()
        scene.render.image_settings.file_format="PNG"
        raw.save_render(str(destination),scene=scene)
        bpy.data.images.remove(raw)

length={"still":1,"turn":72,"walk":0}[args.clip]
if args.clip=="walk":
    length=round(action.frame_range[1]-action.frame_range[0])
for i in range(length):
    if args.clip=="walk":
        scene.frame_set(round(action.frame_range[0])+i)
    angle = math.radians(args.azimuth) if args.azimuth is not None else (.54 if args.clip=="walk" else .18)
    if args.clip=="turn":
        angle += 2*math.pi*i/length
    cam.location=(10*math.sin(angle),-10*math.cos(angle),3.66)
    aim(cam,(0,0,2.42))
    render_frame((args.folder/f"{args.clip}-{i:03}.png").resolve())
