"""Check the exported back under load. Run in Blender with --python-exit-code 1."""
import sys
from pathlib import Path

import bpy
import numpy as np

root = Path(__file__).resolve().parents[2]
arguments = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
model = Path(arguments[0]) if arguments else root/"godot/minotaur.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(model.resolve()))
scene = bpy.context.scene
rig = next(obj for obj in scene.objects if obj.type == "ARMATURE")
mesh = next(obj for obj in scene.objects if obj.type == "MESH")
coordinates = np.empty(len(mesh.data.vertices)*3, dtype=np.float32)
mesh.data.vertices.foreach_get("co", coordinates)
rest = coordinates.reshape(-1,3).copy()
edges = np.array([edge.vertices[:] for edge in mesh.data.edges])
mid = rest[edges].mean(axis=1)
rest_length = np.linalg.norm(rest[edges[:,1]]-rest[edges[:,0]], axis=1)
# Exclude nearly coincident vertices whose relative strain is ill-conditioned.
if rig.name.startswith("Bull"):
    label = "Mid-flank"
    region = ((abs(mid[:,1]) < .38) & (mid[:,2] < 2.55) & (mid[:,2] > 1.16))
    limits = (.90,1.10)
else:
    label = "Posterior rib cage"
    region = ((abs(mid[:,0]) < .83) & (mid[:,1] > .19) & (mid[:,2] > 2.78)
              & (mid[:,2] < 3.33))
    limits = (.65,1.50)
region &= rest_length > .012
edges, rest_length = edges[region], rest_length[region]
assert len(edges) > 100, f"{label} was missing from the mesh"

for track in rig.animation_data.nla_tracks:
    track.mute = True
action = next(clip for clip in bpy.data.actions if clip.name.startswith("Walk"))
rig.animation_data.action = action
smallest, largest = 1., 1.
for frame in range(round(action.frame_range[0]), round(action.frame_range[1])+1):
    scene.frame_set(frame)
    posed = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    posed.data.vertices.foreach_get("co", coordinates)
    xyz = coordinates.reshape(-1,3)
    ratio = np.linalg.norm(xyz[edges[:,1]]-xyz[edges[:,0]], axis=1)/rest_length
    smallest = min(smallest, ratio.min())
    largest = max(largest, ratio.max())
print(f"{label} edge lengths across walk: {smallest:.3f}–{largest:.3f} times rest")
assert limits[0] < smallest and largest < limits[1], f"Local collapse or stretch in {label}"
