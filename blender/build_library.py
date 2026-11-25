"""Build the sculpted part library in Blender and export it for Godot.

    python3 blender/build_library.py [--only id,id] [--no-blend]
    (or inside Blender: blender -b -P blender/build_library.py -- [--only ...])

Per part and per bone piece ("self", "jaw", ...), each paint region is
finished like a sculpt:
    remesh finish:  voxel remesh -> boolean carve -> remesh -> smooth -> decimate
    subsurf finish: Catmull-Clark subdivision of the cage (thin plates)
Parameters become shape keys "<param>.min" / "<param>.max". Subsurf parts get
exact keys (same topology). Remeshed parts carry the construction cage's
displacement onto the final surface (inverse-distance weighted), so the
sculpted mesh follows the parametric shape.

Outputs library/parts/<id>.glb + <id>.json, library/manifest.json and
library/parts.blend (all parts laid out for browsing and hand edits).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import mathutils  # noqa: E402
from mathutils import Vector  # noqa: E402

import kit  # noqa: E402
from parts import face, head, body, tips  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "library", "parts")
LIBRARY_VERSION = "3.0.0"
ALL_PARTS = face.PARTS + head.PARTS + body.PARTS + tips.PARTS
FACE_BUDGET = 1100          # faces per paint region before the detail multiplier

PREVIEW = {
    "skin": (0.55, 0.55, 0.55), "base": (0.6, 0.6, 0.6), "accent": (0.42, 0.5, 0.62), "detail": (0.82, 0.8, 0.76),
    "white": (0.95, 0.94, 0.9), "black": (0.05, 0.05, 0.05), "dark": (0.17, 0.13, 0.12), "horn": (0.86, 0.8, 0.62),
    "claw": (0.18, 0.15, 0.14), "teeth": (0.94, 0.91, 0.81), "eye": (0.9, 0.76, 0.23),
}


def material(slot):
    m = bpy.data.materials.get(slot)
    if m is None:
        m = bpy.data.materials.new(slot)
        m.diffuse_color = (*PREVIEW.get(slot, (0.6, 0.6, 0.6)), 1.0)
        m.roughness = 0.87
    return m


# ------------------------------------------------------------------ meshes

def new_object(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([kit.to_blender(v) for v in verts], [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bake(ob):
    """Apply all modifiers of ob in place."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def read_mesh(ob):
    me = ob.data
    verts = [Vector((v.co.x, v.co.z, -v.co.y)) for v in me.vertices]   # back to Godot coords
    faces = [tuple(p.vertices) for p in me.polygons]
    return verts, faces


def remove(ob):
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if me and me.users == 0:
        bpy.data.meshes.remove(me)


def auto_voxel(verts):
    lo = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
    hi = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
    return min(max((hi - lo).length / 130.0, 0.0022), 0.014)


def finish_region(piece, slot, verts, faces, cut, detail):
    ob = new_object("work", verts, faces)
    if piece.finish_for(slot) == "subsurf":
        m = ob.modifiers.new("sub", "SUBSURF")
        m.levels = 2
        m.render_levels = 2
        bake(ob)
    else:
        voxel = piece.voxel or auto_voxel(verts)
        m = ob.modifiers.new("remesh", "REMESH")
        m.mode = "VOXEL"
        m.voxel_size = voxel
        bake(ob)
        if cut[0]:
            cutter = new_object("cutter", cut[0], cut[1])
            cm = cutter.modifiers.new("clean", "REMESH")   # overlapping cutters -> one clean solid
            cm.mode = "VOXEL"
            cm.voxel_size = voxel * 0.75
            bake(cutter)
            b = ob.modifiers.new("carve", "BOOLEAN")
            b.operation = "DIFFERENCE"
            b.solver = "EXACT"
            b.object = cutter
            b.use_self = True
            bake(ob)
            remove(cutter)
            m = ob.modifiers.new("remesh2", "REMESH")
            m.mode = "VOXEL"
            m.voxel_size = voxel
            bake(ob)
        s = ob.modifiers.new("smooth", "SMOOTH")
        s.factor = piece.smooth
        s.iterations = 4
        bake(ob)
        budget = FACE_BUDGET * detail * piece.detail
        n = len(ob.data.polygons)
        if n > budget:
            d = ob.modifiers.new("decimate", "DECIMATE")
            d.ratio = budget / n
            bake(ob)
    out = read_mesh(ob)
    remove(ob)
    return out


def idw_transfer(final, cage0, cage1, k=8):
    """Move final verts by the cage displacement, inverse-distance weighted."""
    tree = mathutils.kdtree.KDTree(len(cage0))
    for i, c in enumerate(cage0):
        tree.insert(c, i)
    tree.balance()
    out = []
    for v in final:
        acc = Vector((0, 0, 0))
        wsum = 0.0
        for _, i, d in tree.find_n(v, k):
            w = 1.0 / (d * d + 1e-7)
            acc += (cage1[i] - cage0[i]) * w
            wsum += w
        out.append(v + acc / wsum)
    return out


def all_cage(piece):
    v, _ = piece.cage(None, False)
    vn, _ = piece.cage(None, True)
    return v + vn


# ------------------------------------------------------------------ parts

def build_part(part):
    base = part.build(part.defaults())
    variants = []
    for name, (lo, hi, d) in part.params.items():
        for tag, val in (("min", lo), ("max", hi)):
            if abs(val - d) < 1e-9:
                continue
            p = part.defaults()
            p[name] = val
            v = part.build(p)
            for pn, pc in base.pieces.items():
                if v.pieces[pn].signature() != pc.signature():
                    raise RuntimeError("%s: %s.%s changes the cage topology of piece %s" % (part.id, name, tag, pn))
            variants.append(("%s.%s" % (name, tag), v))
    result = {}
    for pn, piece in base.pieces.items():
        pivot = base.pivots.get(pn, Vector((0, 0, 0))) if pn != "self" else Vector((0, 0, 0))
        cut = piece.cage(None, True)
        regions = []
        keys = {k: [] for k, _ in variants}
        slots = piece.slots()
        detail = 1.0 / max(1, len(slots)) ** 0.5
        cage0 = all_cage(piece)
        for slot in slots:
            cv, cf = piece.cage(slot)
            fv, ff = finish_region(piece, slot, cv, cf, cut, detail)
            regions.append((slot, [x - pivot for x in fv], ff))
            for kname, var in variants:
                vp = var.pieces[pn]
                if piece.finish_for(slot) == "subsurf":
                    vv, vf = vp.cage(slot)
                    kv, _ = finish_region(vp, slot, vv, vf, ([], []), detail)
                    if len(kv) != len(fv):
                        raise RuntimeError("%s: subsurf topology mismatch for %s" % (part.id, kname))
                else:
                    kv = idw_transfer(fv, cage0, all_cage(vp))
                keys[kname].append([x - pivot for x in kv])
        result[pn] = {"regions": regions, "keys": keys, "pivot": pivot}
    return base, result


def make_objects(part, built, collection, offset=Vector((0, 0, 0))):
    base, pieces = built
    objs = {}
    for pn in ["self"] + [b["name"] for b in part.bones]:
        data = pieces[pn]
        if not data["regions"]:
            if pn == "self":
                ob = bpy.data.objects.new(part.id, None)
                collection.objects.link(ob)
                ob.location = offset
                objs["self"] = ob
            continue
        verts, faces, slots = [], [], []
        for slot, rv, rf in data["regions"]:
            o = len(verts)
            verts += rv
            faces += [tuple(i + o for i in f) for f in rf]
            slots += [slot] * len(rf)
        me = bpy.data.meshes.new("%s_%s" % (part.id, pn))
        me.from_pydata([kit.to_blender(v) for v in verts], [], faces)
        order_slots = [s for s, _, _ in data["regions"]]
        for s in order_slots:
            me.materials.append(material(s))
        for poly, s in zip(me.polygons, slots):
            poly.material_index = order_slots.index(s)
        me.shade_smooth()
        me.update()
        ob = bpy.data.objects.new(part.id if pn == "self" else "%s__%s" % (part.id, pn), me)
        collection.objects.link(ob)
        if data["keys"]:
            ob.shape_key_add(name="Basis", from_mix=False)
            for kname, regs in data["keys"].items():
                sk = ob.shape_key_add(name=kname, from_mix=False)
                flat = [v for reg in regs for v in reg]
                for i, p in enumerate(flat):
                    sk.data[i].co = kit.to_blender(p)
        if pn == "self":
            ob.location = offset
        else:
            ob.parent = objs["self"]
            ob.location = kit.to_blender(data["pivot"])
        objs[pn] = ob
    return objs


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


def export_part(part):
    reset_scene()
    built = build_part(part)
    objs = make_objects(part, built, bpy.context.scene.collection)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs.values():
        ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, part.id + ".glb"), export_format="GLB", use_selection=True,
                              export_yup=True, export_apply=False, export_morph=True, export_morph_normal=False,
                              export_materials="EXPORT", export_extras=True, export_animations=False)
    meta = metadata(part, built[0])
    meta["triangles"] = sum(sum(len(f) - 2 for f in r[2]) for p in built[1].values() for r in p["regions"])
    with open(os.path.join(OUT, part.id + ".json"), "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    return meta, built


def save_blend(builds):
    reset_scene()
    cols = {}
    for i, (part, built) in enumerate(builds):
        if part.category not in cols:
            c = bpy.data.collections.new(part.category)
            bpy.context.scene.collection.children.link(c)
            cols[part.category] = c
        make_objects(part, built, cols[part.category], Vector(((i % 8) * 1.2, -(i // 8) * 1.4, 0)))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "library", "parts.blend"), compress=True)


def main(argv):
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
    os.makedirs(OUT, exist_ok=True)
    ids = [p.id for p in ALL_PARTS]
    assert len(ids) == len(set(ids)), "duplicate part ids"
    builds = []
    for part in ALL_PARTS:
        if only and part.id not in only:
            continue
        meta, built = export_part(part)
        builds.append((part, built))
        print("built %-16s %5d tris" % (part.id, meta["triangles"]), flush=True)
    with open(os.path.join(ROOT, "library", "manifest.json"), "w") as f:
        json.dump({"library_version": LIBRARY_VERSION, "parts": ids}, f, indent=2)
    if "--no-blend" not in argv and not only:
        save_blend(builds)
        print("saved library/parts.blend")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
