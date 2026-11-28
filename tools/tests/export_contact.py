"""blender -b --python-exit-code 1 -P tools/tests/export_contact.py -- path/to/bull.glb"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def measure(path):
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
                points[bone].append((mesh, v.index, mesh.matrix_world @ v.co))
    flat = {bone: min(vertices, key=lambda p: p[2].z) for bone, vertices in points.items()}
    toes = {bone: min((p for p in vertices if p[2].z <= flat[bone][2].z + 1e-5), key=lambda p: p[2].y)
            for bone, vertices in points.items()}
    probes = {bone: item[:2] for bone, item in flat.items()}
    starts, peak, worst_y, worst_slip = {}, dict.fromkeys(probes, 0.0), 0., 0.
    scene = bpy.context.scene
    for frame in manifest["frames"]:
        number = action.frame_range.x + frame["time"] * scene.render.fps
        scene.frame_set(int(number), subframe=number % 1)
        dg = bpy.context.evaluated_depsgraph_get()
        x, y, z = frame["travel"]
        for bone, (mesh, index) in probes.items():
            rolling = bone in frame.get("toe_stance", [])
            if rolling:
                mesh, index, _ = toes[bone]
            ob = mesh.evaluated_get(dg)
            p = ob.matrix_world @ ob.data.vertices[index].co + Vector((x, -z, y))
            length = manifest["legs"][bone]
            if bone in frame["stance"]:
                worst_y = max(worst_y, abs(p.z) / length)
                worst_slip = max(worst_slip, (p - starts.setdefault((bone, rolling), p.copy())).length / length)
            else:
                starts.pop((bone, False), None)
                starts.pop((bone, True), None)
                peak[bone] = max(peak[bone], p.z / length)
    return {"stance_height": worst_y, "stance_drift": worst_slip, "swing_clearance": peak}


def check(path):
    result = measure(path)
    lift = result["swing_clearance"]
    print(path.stem, "stance height / drift", result["stance_height"], result["stance_drift"], "swing clearance", lift)
    assert lift and result["stance_height"] < .05 and result["stance_drift"] < .05 and min(lift.values()) > .025


if __name__ == "__main__":
    for filename in sys.argv[sys.argv.index("--") + 1:]:
        check(Path(filename))
