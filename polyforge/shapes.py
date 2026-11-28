"""Editable local shape payloads. Placement and instance fit are kept separately."""
from copy import deepcopy

import bpy
from mathutils import Matrix

from . import catalog
from .solid import SolidBuilder
from .recipe import default_recipe, normalize

LIMB_FIELDS = ("segments", "radii", "tip", "tip_params", "motion", "bend_limits")
FAMILY_FIELDS = ("family", "params", "tip", "tip_params", "bend_limits")
PART_FIELDS = ("part", "params")


def extract(item):
    fields = FAMILY_FIELDS if item.get("family") else LIMB_FIELDS if "segments" in item else PART_FIELDS
    return {key: deepcopy(item[key]) for key in fields if key in item}


def normalize_shape(raw):
    if not isinstance(raw, dict):
        raise ValueError("expected a shape object")
    if "segments" in raw or "family" in raw:
        if "family" in raw and not getattr(catalog.get(raw["family"]), "preset", None):
            raise ValueError("expected a known research limb family")
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
    if "segments" in shape or "family" in shape:
        r["limbs"] = [dict(extract(shape), uid="draft", theta=0)]
    elif catalog.get(shape.get("part", "")):
        part = catalog.get(shape["part"])
    else:
        raise ValueError("A shape needs limb segments or a known part ID")
    b = SolidBuilder(r, "final")
    col = collection or bpy.context.scene.collection
    objects = []
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
        body = b.details_object(col, "Draft limb")
        if body is not None:
            objects.append(body)
        b.details.clear()
        b.place_tips()
    else:
        params = catalog.normalize_params(part, shape.get("params", {}), part.id, b.warnings)
        b.place(part, params, Matrix.Identity(4), -1, part.id, False, part.id, 0)
    detail = b.details_object(col, "Draft")
    if detail is not None:
        objects.append(detail)
    return objects, b.warnings
