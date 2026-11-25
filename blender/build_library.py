"""Build the part library in Blender and export it for Godot.

    python3 blender/build_library.py [--only id,id] [--no-blend]

Uses Blender as a Python module (`pip install bpy`) or run inside Blender:
    blender -b -P blender/build_library.py -- [--only ...]

For every part this writes
    library/parts/<id>.glb   one object per bone piece ("self", "jaw", ...),
                             one material per paint slot, and two shape keys
                             per parameter ("<param>.min" / "<param>.max")
    library/parts/<id>.json  metadata Godot needs (category, params, capability,
                             attachment, placement hint, bone pivots/axes)
and also library/manifest.json plus library/parts.blend (every part laid out
on a grid so the library can be browsed and edited in Blender).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import kit  # noqa: E402
from parts import face, head, body, tips  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "library", "parts")
LIBRARY_VERSION = "2.0.0"
ALL_PARTS = face.PARTS + head.PARTS + body.PARTS + tips.PARTS

PREVIEW = {
    "skin": (0.55, 0.6, 0.65), "base": (0.6, 0.64, 0.68), "accent": (0.37, 0.53, 0.71), "detail": (0.85, 0.82, 0.77),
    "white": (0.95, 0.94, 0.9), "black": (0.05, 0.05, 0.05), "dark": (0.17, 0.13, 0.12), "horn": (0.86, 0.8, 0.62),
    "claw": (0.18, 0.15, 0.14), "teeth": (0.94, 0.91, 0.81), "eye": (0.9, 0.76, 0.23),
}


def material(slot):
    m = bpy.data.materials.get(slot)
    if m is None:
        m = bpy.data.materials.new(slot)
        m.diffuse_color = (*PREVIEW.get(slot, (0.6, 0.6, 0.6)), 1.0)
        bsdf = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*PREVIEW.get(slot, (0.6, 0.6, 0.6)), 1.0)
            bsdf.inputs["Roughness"].default_value = 0.8
    return m


def variants(part):
    """Default build plus min/max builds for every parameter, topology checked."""
    base = part.build(part.defaults())
    keys = []
    for name, (lo, hi, d) in part.params.items():
        for tag, val in (("min", lo), ("max", hi)):
            if abs(val - d) < 1e-9:
                continue
            p = part.defaults()
            p[name] = val
            v = part.build(p)
            for piece, mesh in base.pieces.items():
                other = v.pieces[piece]
                if len(other.v) != len(mesh.v) or other.f != mesh.f:
                    raise RuntimeError("%s: param %s.%s changes topology of piece %s" % (part.id, name, tag, piece))
            keys.append(("%s.%s" % (name, tag), v))
    return base, keys


def make_objects(part, collection, offset=Vector((0, 0, 0))):
    base, keys = variants(part)
    objs = {}
    order = ["self"] + [b["name"] for b in part.bones]
    for name in order:
        piece = base.pieces[name]
        if not piece.v:
            if name == "self":
                # Parts made only of hinged pieces still need a root node.
                ob = bpy.data.objects.new(part.id, None)
                collection.objects.link(ob)
                ob["piece"] = "self"
                ob["part_id"] = part.id
                ob.location = offset
                objs["self"] = ob
            continue
        pivot = base.pivots.get(name, Vector((0, 0, 0))) if name != "self" else Vector((0, 0, 0))
        mesh = bpy.data.meshes.new("%s_%s" % (part.id, name))
        verts = [kit.to_blender(v - pivot) for v in piece.v]
        mesh.from_pydata(verts, [], piece.f)
        slots = sorted(set(piece.slot), key=list(PREVIEW).index if all(s in PREVIEW for s in piece.slot) else str)
        for s in slots:
            mesh.materials.append(material(s))
        for poly, s in zip(mesh.polygons, piece.slot):
            poly.material_index = slots.index(s)
            poly.use_smooth = False
        mesh.update()
        ob = bpy.data.objects.new(part.id if name == "self" else "%s__%s" % (part.id, name), mesh)
        collection.objects.link(ob)
        ob["piece"] = name
        if keys:
            ob.shape_key_add(name="Basis", from_mix=False)
            for kname, v in keys:
                sk = ob.shape_key_add(name=kname, from_mix=False)
                vpiv = v.pivots.get(name, pivot) if name != "self" else Vector((0, 0, 0))
                for i, p in enumerate(v.pieces[name].v):
                    # Keep the default pivot so the bone stays put; the delta moves the geometry.
                    sk.data[i].co = kit.to_blender(p - pivot)
        if name == "self":
            ob.location = offset
            ob["part_id"] = part.id
        else:
            ob.parent = objs["self"]
            ob.location = kit.to_blender(pivot)
        objs[name] = ob
    return objs, base


def metadata(part, base):
    bones = []
    for b in part.bones:
        piv = base.pivots.get(b["name"], Vector(b["pivot"]))
        bones.append({"name": b["name"], "pivot": [round(piv.x, 5), round(piv.y, 5), round(piv.z, 5)],
                      "axis": list(b["axis"]), "angle": b["angle"]})
    return {
        "id": part.id, "category": part.category, "desc": part.desc, "tags": part.tags,
        "params": {k: [v[0], v[1], v[2]] for k, v in part.params.items()},
        "attach": part.attach, "orient": part.orient, "capability": part.cap,
        "mirror_default": part.mirror, "hint": part.hint, "bones": bones,
        "pieces": ["self"] + [b["name"] for b in part.bones],
        "glb": part.id + ".glb", "library_version": LIBRARY_VERSION,
    }


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene.collection


def export_part(part):
    col = reset_scene()
    objs, base = make_objects(part, col)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs.values():
        ob.select_set(True)
    path = os.path.join(OUT, part.id + ".glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=False, export_morph=True, export_morph_normal=False,
                              export_materials="EXPORT", export_extras=True, export_animations=False)
    meta = metadata(part, base)
    with open(os.path.join(OUT, part.id + ".json"), "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    return meta


def save_blend(parts):
    reset_scene()
    cols = {}
    per_row = 8
    for i, part in enumerate(parts):
        if part.category not in cols:
            c = bpy.data.collections.new(part.category)
            bpy.context.scene.collection.children.link(c)
            cols[part.category] = c
        off = Vector(((i % per_row) * 1.2, -(i // per_row) * 1.4, 0))
        make_objects(part, cols[part.category], off)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "library", "parts.blend"), compress=True)


def main(argv):
    only = None
    blend = True
    if "--only" in argv:
        only = set(argv[argv.index("--only") + 1].split(","))
    if "--no-blend" in argv:
        blend = False
    os.makedirs(OUT, exist_ok=True)
    ids = [p.id for p in ALL_PARTS]
    assert len(ids) == len(set(ids)), "duplicate part ids"
    manifest = []
    for part in ALL_PARTS:
        if only and part.id not in only:
            path = os.path.join(OUT, part.id + ".json")
            if os.path.exists(path):
                manifest.append(json.load(open(path)))
            continue
        meta = export_part(part)
        manifest.append(meta)
        print("built", part.id, "keys:", 2 * len(part.params))
    with open(os.path.join(ROOT, "library", "manifest.json"), "w") as f:
        json.dump({"library_version": LIBRARY_VERSION, "parts": [m["id"] for m in manifest]}, f, indent=2)
    if blend and not only:
        save_blend(ALL_PARTS)
        print("saved library/parts.blend")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    main(args)
