"""blender -b --python-exit-code 1 -P tools/tests/export_contact.py -- path/to/bull.glb"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def check(path):
    manifest = json.loads(path.with_suffix(".report.json").read_text())["contact"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    action = next(a for a in bpy.data.actions if "walk" in a.name.lower().split("_"))
    for track in arm.animation_data.nla_tracks:
        track.mute = True
    arm.animation_data.action = action
    # Probe actual rigidly weighted sole vertices in the imported neutral mesh.
    # Each demo has rigid hooves/tips. Empty groups fail instead of silently skipping a foot.
    points = {bone: [] for bone in manifest["legs"]}
    for mesh in (o for o in bpy.context.scene.objects if o.type == "MESH"):
        for v in mesh.data.vertices:
            if len(v.groups) != 1 or v.groups[0].weight < 0.999:
                continue
            bone = mesh.vertex_groups[v.groups[0].group].name
            if bone in points:
                points[bone].append((mesh, v.index, (mesh.matrix_world @ v.co).z))
    probes = {bone: min(vertices, key=lambda p: p[2])[:2] for bone, vertices in points.items()}
    starts, peak, worst_y, worst_slip = {}, dict.fromkeys(probes, 0.0), 0., 0.
    scene = bpy.context.scene
    for frame in manifest["frames"]:
        number = action.frame_range.x + frame["time"] * scene.render.fps
        scene.frame_set(int(number), subframe=number % 1)
        dg = bpy.context.evaluated_depsgraph_get()
        x, y, z = frame["travel"]
        for bone, (mesh, index) in probes.items():
            ob = mesh.evaluated_get(dg)
            p = ob.matrix_world @ ob.data.vertices[index].co + Vector((x, -z, y))
            length = manifest["legs"][bone]
            if bone in frame["stance"]:
                worst_y = max(worst_y, abs(p.z) / length)
                worst_slip = max(worst_slip, (p - starts.setdefault(bone, p.copy())).length / length)
            else:
                starts.pop(bone, None)
                peak[bone] = max(peak[bone], p.z / length)
    print(path.stem, "stance height / drift", worst_y, worst_slip, "swing clearance", peak)
    assert probes and worst_y < .05 and worst_slip < .05 and min(peak.values()) > .025


if __name__ == "__main__":
    for filename in sys.argv[sys.argv.index("--") + 1:]:
        check(Path(filename))
