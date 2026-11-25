"""Recipe: the versioned, human-readable description of a creature.

Coordinates use +Y up and +Z forward (the creature faces +Z). Conversion to
Blender's Z-up happens only when objects are created (kit.to_blender).

`normalize` fills defaults, clamps everything into the allowed (style) ranges
and reports each change as a warning, so the AI loop can learn from it.
"""
import copy
import json

from . import catalog, placement
from .spine import Spine

FORMAT = "polyforge.recipe"
VERSION = 2
LIMITS = {
    "vertebrae": [2, 16], "spine_y": [0.0, 8.0], "spine_z": [-8.0, 8.0], "radius": [0.04, 2.5],
    "limbs": 12, "segments": [1, 5], "segment_len": [0.02, 3.5], "limb_radius": [0.02, 1.2],
    "parts": 80, "scale": [0.2, 4.0], "offset": [-0.6, 0.6],
}
PATTERNS = ["none", "stripes", "spots", "patches", "gradient"]


def default_paint():
    return {"base": "#6f9a52", "accent": "#35552b", "detail": "#e9dcae", "pattern": "stripes", "pattern_scale": 1.0, "belly": True}


def default_recipe():
    return {
        "format": FORMAT, "version": VERSION, "name": "Blob",
        "spine": [
            {"y": 0.55, "z": -0.6, "w": 0.32, "h": 0.32}, {"y": 0.6, "z": -0.2, "w": 0.45, "h": 0.42},
            {"y": 0.62, "z": 0.25, "w": 0.45, "h": 0.42}, {"y": 0.7, "z": 0.65, "w": 0.33, "h": 0.32},
            {"y": 0.75, "z": 0.95, "w": 0.26, "h": 0.25},
        ],
        "limbs": [], "parts": [], "paint": default_paint(),
    }


def load(path):
    with open(path) as f:
        return json.load(f)


def to_json(recipe):
    return json.dumps(recipe, indent=2, sort_keys=True) + "\n"


def save(recipe, path):
    with open(path, "w") as f:
        f.write(to_json(recipe))


def _num(v, d):
    return round(float(v), 4) if isinstance(v, (int, float)) and not isinstance(v, bool) else d


def _clamp(v, r, what, warns):
    c = min(max(v, r[0]), r[1])
    if abs(c - v) > 1e-6:
        warns.append("%s clamped %.3f -> %.3f" % (what, v, c))
    return round(c, 4)


def wrap_angle(a):
    a = (a + 180.0) % 360.0 - 180.0
    return round(a, 4)


def _vec(v, d):
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return [_num(v[0], 0.0), _num(v[1], 0.0), _num(v[2], 0.0)]
    return list(d)


def _hex(c, d, what, warns):
    s = str(c).strip().lstrip("#")
    try:
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        int(s[:6], 16)
        if len(s) < 6:
            raise ValueError
        return "#" + s[:6].lower()
    except ValueError:
        warns.append("%s '%s' invalid" % (what, c))
        return d


def _unique(uid, used):
    uid = str(uid).strip() or "x"
    base, k = uid, 2
    while uid in used:
        uid = "%s_%d" % (base, k)
        k += 1
    used.add(uid)
    return uid


def normalize(src):
    """Returns (recipe, warnings)."""
    w = []
    src = src if isinstance(src, dict) else {}
    templates = src.get("shapes", {})
    def expand(item):
        if not isinstance(item, dict) or "shape" not in item:
            return item
        key = item["shape"]
        base = templates.get(key) if isinstance(templates, dict) and isinstance(key, str) else None
        if not isinstance(base, dict):
            w.append("unknown shape %s" % key)
            return item
        return {**base, **item}

    r = {"format": FORMAT, "version": VERSION, "name": str(src.get("name", "Untitled"))}
    if isinstance(src.get("ground_y"), (float, int)):
        r["ground_y"] = float(src["ground_y"])
    s_in = src.get("spine")
    if not isinstance(s_in, list) or len(s_in) < 2:
        w.append("spine missing or too short; using default spine")
        s_in = default_recipe()["spine"]
    if len(s_in) > LIMITS["vertebrae"][1]:
        w.append("spine truncated to %d vertebrae" % LIMITS["vertebrae"][1])
        s_in = s_in[:LIMITS["vertebrae"][1]]
    spine = []
    reserved = {"@rear", "@front"} | {str(v["id"]) for v in s_in if isinstance(v, dict) and "id" in v}
    ring_ids = {"@rear", "@front"}
    def ring_id(index, v):
        if "id" in v and str(v["id"]) not in ring_ids:
            return _unique(v["id"], ring_ids)
        proposal = _unique("r%d" % index, reserved)
        ring_ids.add(proposal)
        return proposal
    for i, v in enumerate(s_in):
        v = v if isinstance(v, dict) else {}
        spine.append({
            "id": ring_id(i, v),
            "y": _clamp(_num(v.get("y"), 0.6), LIMITS["spine_y"], "spine[%d].y" % i, w),
            "z": _clamp(_num(v.get("z"), 0.0), LIMITS["spine_z"], "spine[%d].z" % i, w),
            "w": _clamp(_num(v.get("w"), 0.3), LIMITS["radius"], "spine[%d].w" % i, w),
            "h": _clamp(_num(v.get("h", v.get("w")), 0.3), LIMITS["radius"], "spine[%d].h" % i, w),
        })
    r["spine"] = spine
    surface = Spine(spine)
    def locate(raw, item):
        if item.get("on", "body") != "body":
            return
        saved = raw.get("bind")
        u = surface.resolve(saved)
        if u is None:
            if saved is not None:
                w.append("invalid strip on %s; rebound at its last position" % item["uid"])
            u = item["u"]
        item["bind"] = surface.bind(u)
        item["u"] = round(u, 9)

    used = set()
    limbs = []
    l_in = src.get("limbs") if isinstance(src.get("limbs"), list) else []
    if len(l_in) > LIMITS["limbs"]:
        w.append("only %d limbs allowed" % LIMITS["limbs"])
    for i, l in enumerate(l_in[:LIMITS["limbs"]]):
        l = expand(l)
        if not isinstance(l, dict):
            continue
        uid = _unique(l.get("uid", "limb%d" % i), used)
        s_src = l.get("segments")
        if not isinstance(s_src, list) or not s_src:
            w.append("limb %s has no segments; using a default leg" % uid)
            s_src = [[0.1, -0.3, 0.0], [0.0, -0.3, 0.0]]
        segs = []
        for k, sv in enumerate(s_src[:LIMITS["segments"][1]]):
            x, y, z = _vec(sv, [0.0, -0.3, 0.0])
            ln = (x * x + y * y + z * z) ** 0.5
            lo, hi = LIMITS["segment_len"]
            if ln < lo:
                w.append("limb %s segment %d too short" % (uid, k))
                x, y, z = (0.0, -lo, 0.0) if ln < 1e-6 else (x / ln * lo, y / ln * lo, z / ln * lo)
            elif ln > hi:
                w.append("limb %s segment %d too long (%.2f), scaled to %.2f" % (uid, k, ln, hi))
                x, y, z = x / ln * hi, y / ln * hi, z / ln * hi
            segs.append([round(x, 4), round(y, 4), round(z, 4)])
        r_src = l.get("radii") if isinstance(l.get("radii"), list) else []
        radii = []
        for k in range(len(segs) + 1):
            dr = 0.12 + (0.06 - 0.12) * k / len(segs)
            rv = _num(r_src[k], dr) if k < len(r_src) else (_num(r_src[-1], dr) if r_src else dr)
            radii.append(_clamp(rv, LIMITS["limb_radius"], "limb %s radius %d" % (uid, k), w))
        tip = str(l.get("tip", "") or "")
        tip_params = {}
        if tip:
            part = catalog.get(tip)
            if part is None:
                w.append("limb %s: unknown tip part '%s' removed" % (uid, tip))
                tip = ""
            elif part.attach != "tip":
                w.append("limb %s: part '%s' is not a limb tip; removed" % (uid, tip))
                tip = ""
            else:
                tip_params = catalog.normalize_params(part, l.get("tip_params", {}), "limb %s tip" % uid, w)
        # Symmetry rules: author on the +X side; near the midline snaps to centre (x = 0).
        raw = wrap_angle(_num(l.get("theta"), -45.0))
        theta, centre = placement.centred(raw, "any")
        if src.get("version", 1) == 1 and abs(raw) > 90.0:
            segs = [[-sg[0], sg[1], sg[2]] for sg in segs]
        if src.get("version", 1) == 1 and centre:
            segs = [[0.0, sg[1], sg[2]] for sg in segs]
        limbs.append({
            "uid": uid, "u": _clamp(_num(l.get("u"), 0.5), [0.0, 1.0], "limb %s u" % uid, w),
            "theta": round(theta, 4), "segments": segs, "radii": radii,
            "tip": tip, "tip_params": tip_params,
            "motion": "tail" if l.get("motion") == "tail" else "auto",
            "scale": _clamp(_num(l.get("scale"), 1.0), LIMITS["scale"], uid + ".scale", w),
            "rot": [wrap_angle(a) for a in _vec(l.get("rot"), [0, 0, 0])],
        })
        locate(l, limbs[-1])
    r["limbs"] = limbs
    limb_ids = {l["uid"] for l in limbs}
    parts = []
    p_in = src.get("parts") if isinstance(src.get("parts"), list) else []
    for i, p in enumerate(p_in[:LIMITS["parts"]]):
        p = expand(p)
        if not isinstance(p, dict):
            continue
        pid = str(p.get("part", ""))
        part = catalog.get(pid)
        if part is None:
            w.append("unknown part '%s' removed" % pid)
            continue
        if part.attach == "tip":
            w.append("part '%s' is a limb tip; set it as a limb's tip instead (removed)" % pid)
            continue
        uid = _unique(p.get("uid", "p%d" % i), used)
        on = str(p.get("on", "body"))
        if on != "body" and on not in limb_ids:
            w.append("part %s attached to unknown limb '%s'; moved to body" % (uid, on))
            on = "body"
        rot = _vec(p.get("rot", [0, 0, 0]), [0.0, 0.0, 0.0])
        theta = wrap_angle(_num(p.get("theta"), 90.0))
        if on == "body":
            raw = theta
            mode = "any"
            if src.get("version", 1) == 1:
                mode = placement.symmetry(part)
            elif p.get("bind") and abs(raw) != 90:
                mode = "pair"  # retain previously bound angles on load, including legacy pairs
            theta, centre = placement.centred(raw, mode)
            if abs(raw) > 90.0:
                rot = [rot[0], -rot[1], -rot[2]]       # reflected to the +X side
            if centre:
                rot = [rot[0], 0.0, 0.0]               # a centred part stays symmetric
        parts.append({
            "uid": uid, "part": pid, "on": on,
            "u": _clamp(_num(p.get("u"), 0.9), [0.0, 1.0], "part %s u" % uid, w),
            "theta": round(theta, 4),
            "offset": _clamp(_num(p.get("offset"), 0.0), LIMITS["offset"], "part %s offset" % uid, w),
            "rot": [wrap_angle(a) for a in rot],
            "scale": _clamp(_num(p.get("scale"), 1.0), LIMITS["scale"], "part %s scale" % uid, w),
            "params": catalog.normalize_params(part, p.get("params", {}), "part %s" % uid, w),
        })
        locate(p, parts[-1])
    r["parts"] = parts
    pa = src.get("paint") if isinstance(src.get("paint"), dict) else {}
    dp = default_paint()
    paint = {k: _hex(pa.get(k, dp[k]), dp[k], "paint." + k, w) for k in ("base", "accent", "detail")}
    pat = str(pa.get("pattern", dp["pattern"]))
    if pat not in PATTERNS:
        w.append("unknown pattern '%s'" % pat)
        pat = "none"
    paint["pattern"] = pat
    paint["pattern_scale"] = _clamp(_num(pa.get("pattern_scale"), 1.0), [0.25, 4.0], "paint.pattern_scale", w)
    paint["belly"] = bool(pa.get("belly", True))
    r["paint"] = paint
    return r, w
