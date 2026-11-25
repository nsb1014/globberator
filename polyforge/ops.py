"""Recipe operations shared by the editor UI and the AI. Each op is a small
JSON object {"op": name, ...}. Ops never touch geometry; the builder does."""
import copy

from . import catalog, placement
from . import recipe as R

SPEC = {
    "set_name": {"name": "string"},
    "set_spine": {"spine": "array of {y,z,w,h} (rear to front)"},
    "set_vertebra": {"index": "int", "y?": "float", "z?": "float", "w?": "float", "h?": "float"},
    "insert_vertebra": {"index": "int (insert before; -1 = append at head)", "y?": "float", "z?": "float", "w?": "float", "h?": "float"},
    "remove_vertebra": {"index": "int"},
    "scale_body": {"w?": "float factor", "h?": "float factor", "length?": "float factor"},
    "add_limb": {"uid?": "string", "u": "float", "theta": "deg", "segments": "[[x,y,z],...]", "radii?": "[...]", "tip?": "part id", "tip_params?": "{}", "snap?": "bool (snap to the nearest named socket)"},
    "set_limb": {"uid": "string", "...": "any limb field to replace (tip_params merge)"},
    "remove_limb": {"uid": "string"},
    "add_part": {"uid?": "string", "part": "part id", "on?": "body | limb uid", "u?": "float", "theta?": "deg", "offset?": "float", "rot?": "[x,y,z] deg", "scale?": "float", "params?": "{}", "snap?": "bool (snap to the nearest named socket)"},
    "set_part": {"uid": "string", "...": "any part field to replace (params merge)"},
    "remove_part": {"uid": "string"},
    "set_paint": {"base?": "#hex", "accent?": "#hex", "detail?": "#hex", "pattern?": "none|stripes|spots|patches|gradient", "pattern_scale?": "float", "belly?": "bool"},
}


def _new_uid(r, prefix):
    used = {x.get("uid") for x in r.get("limbs", []) + r.get("parts", [])}
    k = 1
    while "%s%d" % (prefix, k) in used:
        k += 1
    return "%s%d" % (prefix, k)


def _find(lst, uid):
    for i, x in enumerate(lst):
        if x.get("uid") == uid:
            return i
    return -1


def _snap_part(p, op):
    part = catalog.get(p.get("part", ""))
    if op.get("snap") and part is not None and p.get("on", "body") == "body":
        hit = placement.snap_part(part.category, float(p.get("u", 0.5)), float(p.get("theta", 90.0)))
        if hit:
            p["u"], p["theta"] = hit[1], hit[2]
    p.pop("snap", None)


def _snap_limb(l, op):
    if op.get("snap"):
        hit = placement.snap_limb(float(l.get("u", 0.5)), float(l.get("theta", -60.0)))
        if hit:
            l["u"], l["theta"] = hit[1], hit[2]
    l.pop("snap", None)


def apply(r, op):
    """Apply one op in place. Returns '' or an error string.
    Placement ops accept "snap": true to snap to the nearest named socket."""
    r.setdefault("limbs", [])
    r.setdefault("parts", [])
    r.setdefault("spine", R.default_recipe()["spine"])
    name = str(op.get("op", ""))
    sp = r["spine"]
    if name == "set_name":
        r["name"] = str(op.get("name", r.get("name", "")))
    elif name == "set_spine":
        if not isinstance(op.get("spine"), list):
            return "set_spine needs an array"
        r["spine"] = copy.deepcopy(op["spine"])
    elif name == "set_vertebra":
        i = int(op.get("index", -1))
        if not 0 <= i < len(sp):
            return "vertebra index out of range"
        for k in ("y", "z", "w", "h"):
            if k in op:
                sp[i][k] = float(op[k])
    elif name == "insert_vertebra":
        i = int(op.get("index", -1))
        if not 0 <= i <= len(sp):
            i = len(sp)
        if i == len(sp):
            ref = sp[-1]
            d = sp[-1]["z"] - sp[max(len(sp) - 2, 0)]["z"]
            v = {"y": ref["y"], "z": ref["z"] + (d if abs(d) > 0.05 else 0.3), "w": ref["w"] * 0.85, "h": ref["h"] * 0.85}
        elif i == 0:
            ref = sp[0]
            v = {"y": ref["y"], "z": ref["z"] - 0.3, "w": ref["w"] * 0.8, "h": ref["h"] * 0.8}
        else:
            a, b = sp[i - 1], sp[i]
            v = {k: (a[k] + b[k]) * 0.5 for k in ("y", "z", "w", "h")}
        for k in ("y", "z", "w", "h"):
            if k in op:
                v[k] = float(op[k])
        sp.insert(i, v)
    elif name == "remove_vertebra":
        i = int(op.get("index", -1))
        if len(sp) <= 2:
            return "spine needs at least 2 vertebrae"
        if not 0 <= i < len(sp):
            return "vertebra index out of range"
        sp.pop(i)
    elif name == "scale_body":
        for v in sp:
            v["w"] = v["w"] * float(op.get("w", 1.0))
            v["h"] = v["h"] * float(op.get("h", 1.0))
            v["z"] = v["z"] * float(op.get("length", 1.0))
    elif name == "add_limb":
        l = {k: v for k, v in op.items() if k != "op"}
        if "uid" not in l or _find(r["limbs"], str(l["uid"])) >= 0:
            l["uid"] = _new_uid(r, "limb")
        _snap_limb(l, op)
        r["limbs"].append(l)
    elif name == "set_limb":
        i = _find(r["limbs"], str(op.get("uid", "")))
        if i < 0:
            return "no limb %s" % op.get("uid", "")
        for k, v in op.items():
            if k in ("op", "uid"):
                continue
            if k == "tip_params" and isinstance(v, dict):
                r["limbs"][i].setdefault("tip_params", {}).update(v)
            else:
                r["limbs"][i][k] = v
        _snap_limb(r["limbs"][i], op)
    elif name == "remove_limb":
        i = _find(r["limbs"], str(op.get("uid", "")))
        if i < 0:
            return "no limb %s" % op.get("uid", "")
        uid = r["limbs"].pop(i)["uid"]
        r["parts"] = [p for p in r["parts"] if p.get("on", "body") != uid]
    elif name == "add_part":
        part = catalog.get(str(op.get("part", "")))
        if part is None:
            return "unknown part %s" % op.get("part", "")
        p = {"part": part.id, "u": part.hint["u"], "theta": part.hint["theta"]}
        p.update({k: v for k, v in op.items() if k != "op"})
        if "uid" not in p or _find(r["parts"], str(p["uid"])) >= 0:
            p["uid"] = _new_uid(r, part.category)
        _snap_part(p, op)
        r["parts"].append(p)
    elif name == "set_part":
        i = _find(r["parts"], str(op.get("uid", "")))
        if i < 0:
            return "no part %s" % op.get("uid", "")
        for k, v in op.items():
            if k in ("op", "uid"):
                continue
            if k == "params" and isinstance(v, dict):
                r["parts"][i].setdefault("params", {}).update(v)
            else:
                r["parts"][i][k] = v
        _snap_part(r["parts"][i], op)
    elif name == "remove_part":
        i = _find(r["parts"], str(op.get("uid", "")))
        if i < 0:
            return "no part %s" % op.get("uid", "")
        r["parts"].pop(i)
    elif name == "set_paint":
        pa = r.setdefault("paint", R.default_paint())
        pa.update({k: v for k, v in op.items() if k != "op"})
    else:
        return "unknown op '%s'" % name
    return ""


def apply_all(src, ops):
    r = copy.deepcopy(src)
    errors = []
    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            errors.append("op %d is not an object" % i)
            continue
        e = apply(r, op)
        if e:
            errors.append("op %d (%s): %s" % (i, op.get("op", "?"), e))
    return r, errors


def showcase_recipe(part_id):
    """Small neutral creature wearing one part (thumbnails, tests)."""
    r = R.default_recipe()
    r["name"] = part_id
    r["paint"] = {"base": "#8a8f96", "accent": "#5f87b5", "detail": "#d8d2c4", "pattern": "none", "pattern_scale": 1.0, "belly": False}
    part = catalog.get(part_id)
    if part is None:
        return r
    if part.attach == "tip":
        arm = part.cap != "foot"
        r["limbs"] = [{"uid": "l", "u": 0.62 if arm else 0.45, "theta": 0.0 if arm else -60.0,
                       "segments": [[0.25, 0.0, 0.1], [0.15, -0.05, 0.25]] if arm else [[0.12, -0.25, 0.05], [0.0, -0.25, 0.05]],
                       "radii": [0.09, 0.07, 0.05], "tip": part_id}]
    else:
        r["parts"] = [{"uid": "p", "part": part_id, "u": part.hint["u"], "theta": part.hint["theta"]}]
    return r
