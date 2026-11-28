"""Sculpt finishing in Blender: voxel remesh / boolean carve / smooth / decimate,
or subdivision for thin plates. Results are cached per (part, params, piece, slot)."""
import hashlib
import json

import bpy
from mathutils import Vector

from . import kit

CLAY_NAME = "Globberator Clay"
CLAY_TONE = (0.55, 0.55, 0.55, 1.0)
FACE_BUDGET = 1100
SCULPT_LEVELS = {"sculpt": 2, "sculpt_low": 1}
SUBDIVISION_LEVELS = {"subsurf": 2, "subsurf_low": 1, **SCULPT_LEVELS}
_cache = {}


def clay_material():
    material = bpy.data.materials.get(CLAY_NAME)
    if material is None:
        material = bpy.data.materials.new(CLAY_NAME)
        material.diffuse_color = CLAY_TONE
        material.roughness = 0.85
        material.use_nodes = True
        surface = material.node_tree.nodes.get("Principled BSDF")
        surface.inputs["Base Color"].default_value = CLAY_TONE
        surface.inputs["Roughness"].default_value = material.roughness
    return material


def new_object(name, verts, faces, collection=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([kit.to_blender(v) for v in verts], [], faces)
    me.validate()
    me.update()
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def bake(ob):
    """Apply all modifiers of ob in place."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)


def read_mesh(ob):
    """Vertices back in recipe coordinates, polygon index tuples."""
    verts = [Vector((v.co.x, v.co.z, -v.co.y)) for v in ob.data.vertices]
    return verts, [tuple(p.vertices) for p in ob.data.polygons]


def remove(ob):
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def auto_voxel(verts):
    lo = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
    hi = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
    return min(max((hi - lo).length / 130.0, 0.0022), 0.014)


def remesh(ob, voxel):
    m = ob.modifiers.new("remesh", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    bake(ob)


def smooth(ob, factor, iterations=4, vertex_group=""):
    s = ob.modifiers.new("smooth", "SMOOTH")
    s.factor = factor
    s.iterations = iterations
    s.vertex_group = vertex_group
    bake(ob)


def decimate(ob, budget):
    n = len(ob.data.polygons)
    if n > budget:
        d = ob.modifiers.new("decimate", "DECIMATE")
        d.ratio = budget / n
        bake(ob)


def carve(ob, cut_verts, cut_faces, voxel):
    cutter = new_object("cutter", cut_verts, cut_faces)
    remesh(cutter, voxel * 0.75)          # overlapping cutters -> one clean solid
    b = ob.modifiers.new("carve", "BOOLEAN")
    b.operation = "DIFFERENCE"
    b.solver = "EXACT"
    b.use_self = True
    b.object = cutter
    bake(ob)
    remove(cutter)


def finish_region(piece, slot, verts, faces, cut, detail=1.0):
    finishing = piece.finish_for(slot)
    if finishing == "direct" and not cut[0]:
        return verts, faces
    ob = new_object("work", verts, faces)
    if finishing in SUBDIVISION_LEVELS:
        m = ob.modifiers.new("sub", "SUBSURF")
        m.levels = SUBDIVISION_LEVELS[finishing]
        m.render_levels = m.levels
        bake(ob)
    else:
        voxel = piece.voxel or auto_voxel(verts)
        remesh(ob, voxel)
        if cut[0]:
            carve(ob, cut[0], cut[1], voxel)
            remesh(ob, voxel)
        smooth(ob, piece.smooth)
        decimate(ob, FACE_BUDGET * detail * piece.detail)
    out = read_mesh(ob)
    remove(ob)
    return out


def part_regions(part, params, skip_slots=(), *, assembly=False):
    """Cached regions in the part frame, including the skin input to fusion."""
    key = hashlib.sha1(json.dumps([part.id, params, sorted(skip_slots), assembly], sort_keys=True).encode()).hexdigest()
    if key in _cache:
        return _cache[key]
    ctx = part.build(params)
    out = {}
    for pn, piece in ctx.pieces.items():
        cut = piece.cage(None, True)
        slots = piece.slots()
        detail = 1.0 / max(1, len(slots)) ** 0.5
        regions = []
        for slot in slots:
            if slot in skip_slots:
                continue
            cage = piece.cage(slot)
            if assembly and slot == "skin" and piece.finish_for(slot) not in SCULPT_LEVELS:
                # Ordinary skin cages go straight to the creature's voxel
                # pass. Sculpt cages rely on subdivision for their silhouette.
                mesh = cage
            else:
                mesh = finish_region(piece, slot, *cage, cut, detail)
            regions.append((slot, *mesh))
        out[pn] = regions
    _cache[key] = (ctx, out)
    return _cache[key]


def clear_cache():
    _cache.clear()
