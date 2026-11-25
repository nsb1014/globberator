"""Part catalog: every part definition in polyforge/parts, keyed by id."""
from .parts import face, head, body, tips

LIBRARY_VERSION = "4.0.0"

PARTS = face.PARTS + head.PARTS + body.PARTS + tips.PARTS
BY_ID = {p.id: p for p in PARTS}
assert len(BY_ID) == len(PARTS), "duplicate part ids"


def get(pid):
    return BY_ID.get(pid)


def by_category():
    out = {}
    for p in PARTS:
        out.setdefault(p.category, []).append(p.id)
    return out


def normalize_params(part, src, what, warns):
    out = {}
    src = src if isinstance(src, dict) else {}
    for k in src:
        if k not in part.params:
            warns.append("%s: unknown param '%s' for %s ignored" % (what, k, part.id))
    for k, (lo, hi, d) in part.params.items():
        v = src.get(k, d)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            v = d
        c = min(max(float(v), lo), hi)
        if abs(c - float(v)) > 1e-6:
            warns.append("%s: %s.%s clamped %.3f -> %.3f" % (what, part.id, k, float(v), c))
        out[k] = round(c, 4)
    return out


def describe_part(p):
    return {"id": p.id, "category": p.category, "desc": p.desc, "tags": p.tags, "attach": p.attach,
            "orient": p.orient, "capability": p.cap, "mirror_default": p.mirror, "hint": p.hint,
            "params": {k: {"min": v[0], "max": v[1], "default": v[2]} for k, v in p.params.items()}}


def describe():
    return {"library_version": LIBRARY_VERSION, "parts": [describe_part(p) for p in PARTS]}
