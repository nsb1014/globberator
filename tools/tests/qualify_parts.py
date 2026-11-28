"""Check candidate library geometry and render eight views of exported GLBs.

blender -b -t 2 --python-exit-code 1 -P tools/tests/qualify_parts.py -- --out out/part-qualification
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
from struct import pack
import sys

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from polyforge import catalog, finish, render
from polyforge.cli import library_objects, reset

VIEWS = {
    "front": (0, 0), "right": (90, 0), "left": (-90, 0), "back": (180, 0),
    "top": (0, 90), "bottom": (0, -90), "threequarter": (38, 20), "rear_threequarter": (218, 20),
}
TRIANGLE_BUDGET = 20_000


def control_cases(part):
    defaults = part.defaults()
    cases = {"default": defaults}
    for name, (low, high, _) in part.params.items():
        for label, value in (("min", low), ("max", high)):
            if value != defaults[name]:
                cases[f"{name}:{label}"] = {**defaults, name: value}
    if len(defaults) > 1:
        for label, index in (("all_min", 0), ("all_max", 1)):
            cases[label] = {name: bounds[index] for name, bounds in part.params.items()}
    return cases


def mesh_metrics(objects, *, weld_export=False):
    counts = dict(objects=len(objects), vertices=0, triangles=0, nonfinite_vertices=0,
                  invalid_edges=0, degenerate_triangles=0, nonpositive_volume_components=0)
    signature = hashlib.sha256()
    for obj in objects:
        data = obj.data
        counts["vertices"] += len(data.vertices)
        counts["nonfinite_vertices"] += sum(not all(map(math.isfinite, vertex.co)) for vertex in data.vertices)
        for vertex in data.vertices:
            signature.update(pack("<3f", *vertex.co))
        for face in data.polygons:
            signature.update(pack("<" + "I" * (1 + len(face.vertices)), len(face.vertices), *face.vertices))
        data.calc_loop_triangles()
        counts["triangles"] += len(data.loop_triangles)
        counts["degenerate_triangles"] += sum(
            (data.vertices[b].co - data.vertices[a].co).cross(
                data.vertices[c].co - data.vertices[a].co).length_squared <= 1e-24
            for a, b, c in (face.vertices for face in data.loop_triangles)
        )
        mesh = bmesh.new()
        try:
            mesh.from_mesh(data)
            if weld_export:
                # glTF can split otherwise identical vertices at normal/attribute seams.
                bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1e-7)
            counts["invalid_edges"] += sum(not edge.is_manifold or not edge.is_contiguous for edge in mesh.edges)
            pending = set(mesh.faces)
            while pending:
                stack = [pending.pop()]
                pivot = stack[0].verts[0].co
                volume = 0.
                while stack:
                    face = stack.pop()
                    a, *rim = [vertex.co - pivot for vertex in face.verts]
                    volume += sum(a.dot(b.cross(c)) for b, c in zip(rim, rim[1:]))
                    attached = {neighbor for edge in face.edges for neighbor in edge.link_faces} & pending
                    pending.difference_update(attached)
                    stack.extend(attached)
                counts["nonpositive_volume_components"] += volume <= 0
        finally:
            mesh.free()
    counts["signature"] = signature.hexdigest()
    return counts


def mesh_passes(metrics):
    return (0 < metrics["triangles"] <= TRIANGLE_BUDGET and not any(metrics[key] for key in
            ("nonfinite_vertices", "invalid_edges", "degenerate_triangles", "nonpositive_volume_components")))


def control_metrics(part, params):
    objects = library_objects(part, params)
    try:
        return mesh_metrics(objects)
    finally:
        for obj in objects:
            finish.remove(obj)
        finish.clear_cache()


def export_preview(part, directory, cam, view_names):
    objects = library_objects(part)
    try:
        for obj in bpy.context.selected_objects:
            obj.select_set(False)
        for obj in objects:
            obj.select_set(True)
        path = directory / f"{part.id}.glb"
        result = bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True)
        if "FINISHED" not in result:
            raise RuntimeError(f"Could not export {part.id}")
    finally:
        for obj in objects:
            finish.remove(obj)
        finish.clear_cache()
    existing = set(bpy.data.objects)
    imported = []
    try:
        result = bpy.ops.import_scene.gltf(filepath=str(path))
        imported = [obj for obj in bpy.data.objects if obj not in existing]
        meshes = [obj for obj in imported if obj.type == "MESH"]
        if "FINISHED" not in result or not meshes:
            raise RuntimeError(f"No reimported meshes for {part.id}")
        bpy.context.view_layer.update()
        metrics = mesh_metrics(meshes, weld_export=True)
        for name in view_names:
            render.clay_camera(cam, meshes, *VIEWS[name])
            path = render.render(str(directory / f"{name}.png"), transparent=True)
            image = bpy.data.images.load(path)
            try:
                pixels = np.empty(len(image.pixels), dtype=np.float32)
                image.pixels.foreach_get(pixels)
                if not (pixels[3::4] > .5).any():
                    raise RuntimeError(f"Empty reimport preview for {part.id}: {name}")
            finally:
                bpy.data.images.remove(image)
        return metrics
    finally:
        for obj in reversed(imported):
            finish.remove(obj)


def qualify(part, directory, cam, args):
    controls = {}
    for name, params in control_cases(part).items():
        try:
            controls[name] = control_metrics(part, params)
        except (ValueError, RuntimeError, TypeError) as exc:
            controls[name] = {"error": str(exc)}
    repeated = control_metrics(part, part.defaults())
    deterministic = controls["default"].get("signature") == repeated["signature"]
    after_export = export_preview(part, directory, cam, () if args.no_render else VIEWS)
    failures = [name for name, metrics in controls.items() if "error" in metrics or not mesh_passes(metrics)]
    if not mesh_passes(after_export):
        failures.append("reimport")
    if not deterministic:
        failures.append("repeatability")
    return {"status": "failed" if failures else "passed", "triangle_budget": TRIANGLE_BUDGET,
            "failures": failures, "deterministic": deterministic, "control_cases": controls,
            "reimport": after_export, "views": [] if args.no_render else list(VIEWS)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--size", type=int, default=384)
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    ids = args.ids or sorted(catalog.CANDIDATE_PARTS)
    unknown = sorted(set(ids) - set(catalog.CANDIDATE_PARTS))
    if unknown:
        parser.error("Unknown candidate IDs: " + ", ".join(unknown))
    if not ids:
        parser.error("No candidate meshes are registered")
    reset()
    cam = render.setup(size=args.size)
    all_passed = True
    for identifier in ids:
        directory = args.out.resolve() / identifier
        directory.mkdir(parents=True, exist_ok=True)
        try:
            report = qualify(catalog.CANDIDATE_PARTS[identifier], directory, cam, args)
        except (ValueError, RuntimeError, TypeError) as exc:
            report = {"status": "failed", "error": str(exc)}
        (directory / "structure.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"{identifier}: {report['status']} {report.get('failures', report.get('error', ''))}", flush=True)
        all_passed &= report["status"] == "passed"
    return all_passed


if __name__ == "__main__":
    if not main():
        raise SystemExit(1)
