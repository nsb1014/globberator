"""Editable local shape payloads. Placement and instance fit are kept separately."""
from copy import deepcopy

import bpy
from mathutils import Matrix

from . import catalog
from .builder import Builder
from .recipe import default_recipe, normalize

LIMB_FIELDS = ("segments", "radii", "tip", "tip_params", "motion")
PART_FIELDS = ("part", "params")


def extract(item):
    fields = LIMB_FIELDS if "segments" in item else PART_FIELDS
    return {key: deepcopy(item[key]) for key in fields if key in item}


def normalize_shape(raw):
    if not isinstance(raw, dict):
        raise ValueError("expected a shape object")
    if "segments" in raw:
        r = default_recipe()
        r["limbs"] = [dict(extract(raw), uid="draft", theta=0)]
        normalized, warnings = normalize(r)
        return extract(normalized["limbs"][0]), warnings
    part = catalog.get(raw.get("part", ""))
    if part is None:
        raise ValueError("expected limb segments or a known part ID")
    warnings = []
    params = catalog.normalize_params(part, raw.get("params"), part.id, warnings)
    return {"part": part.id, "params": params}, warnings


def isolated(shape, collection=None):
    """Emit just one local mesh assembly, using the creature's actual part builders."""
    r = default_recipe()
    if "segments" in shape:
        r["limbs"] = [dict(extract(shape), uid="draft", theta=0)]
    elif catalog.get(shape.get("part", "")):
        part = catalog.get(shape["part"])
    else:
        raise ValueError("A shape needs limb segments or a known part ID")
    b = Builder(r, "final")
    col = collection or bpy.context.scene.collection
    if r["limbs"]:
        from .spine import Spine
        b.spine = Spine(b.recipe["spine"])
        b.resolve_limbs(b.spine)
        limb = b.limbs[0]
        b.limbs = [limb]
        origin = limb["joints"][0]
        limb["joints"] = [joint - origin for joint in limb["joints"]]
        b.make_bones()
        b.limb_prim(limb)
        b.place_tips()
    else:
        params = catalog.normalize_params(part, shape.get("params", {}), part.id, b.warnings)
        b.place(part, params, Matrix.Identity(4), -1, part.id, False, part.id, 0)
    result = []
    if b.skin_prims:
        result.append(b.fuse(col))
    detail = b.details_object(col, "Draft")
    if detail:
        result.append(detail)
    return result, b.warnings
