"""Recipe operations shared by the editor UI and the AI. Each op is a small
JSON object {"op": name, ...}. Ops never touch geometry; the builder does."""
import copy

from . import catalog, placement
from . import recipe as R

SPEC = {
    "attach_shape": {"shape": "{part,params} or {segments,radii,tip,tip_params,motion}", "u": "float", "theta": "degrees", "uid?": "string", "scale?": "float", "rot?": "[x,y,z]"},
    "reground": {"note": "drop the frozen floor height; the builder re-finds the ground from the feet"},
    "set_name": {"name": "string"},
    "set_spine": {"spine": "array of {y,z,w,h} (rear to front)"},
    "set_vertebra": {"index": "int", "y?": "float", "z?": "float", "w?": "float", "h?": "float"},
    "insert_vertebra": {"index": "int (insert before; -1 = append at head)", "y?": "float", "z?": "float", "w?": "float", "h?": "float"},
    "remove_vertebra": {"index": "int"},
    "scale_body": {"w?": "float factor", "h?": "float factor", "length?": "float factor"},
    "add_limb": {"uid?": "string", "u": "float", "theta": "deg", "segments?": "[[x,y,z],...]", "radii?": "[...]", "family?": "research limb id, supplies the joint chain", "params?": "{}", "tip?": "part id", "tip_params?": "{}", "root_blend?": "0..1, blend a generic skin limb into its host", "glute_shape?": "0..1, rear upper-thigh fullness for paired humanoid legs", "ball_hip?": "bool, use a separate rotating ball for paired humanoid legs", "ball_hip_inset?": "0..0.75, fraction toward the body centerline", "snap?": "bool (snap to the nearest named socket)"},
    "set_limb": {"uid": "string", "keep_ground?": "bool (keep the frozen floor; default re-grounds)", "...": "any limb field to replace (tip_params merge)"},
    "remove_limb": {"uid": "string"},
    "add_part": {"uid?": "string", "part": "part id", "on?": "body | limb uid | muzzle uid for nose_pad", "u?": "float", "theta?": "deg", "offset?": "float", "rot?": "[x,y,z] deg", "scale?": "float", "params?": "{}", "snap?": "bool (snap to the nearest named socket)"},
    "set_part": {"uid": "string", "...": "any part field to replace (params merge)"},
    "remove_part": {"uid": "string"},

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
    if name in ("set_spine", "insert_vertebra", "remove_vertebra", "set_vertebra", "scale_body"):
        # Bind legacy or newly added instances BEFORE changing the shape.
        normalized, _ = R.normalize(r)
        r.update(normalized)
    if name == "attach_shape":
        from .shapes import extract
        shape = op.get("shape")
        if not isinstance(shape, dict) or not ({"segments", "family", "part"} & shape.keys()):
            return "attach_shape requires a part or limb shape"
        fields = {k: op[k] for k in ("uid", "u", "theta", "on", "offset", "rot", "scale") if k in op}
        is_limb = "segments" in shape or "family" in shape
        if is_limb and fields.get("on", "body") != "body":
            return "limbs attach to the body surface"
        part = catalog.get(shape.get("part", ""))
        if part and part.attach == "tip":
            target = fields.get("on")
            if not target or _find(r["limbs"], target) < 0:
                return "tip shapes require a host limb uid in on"
            return apply(r, {"op": "set_limb", "uid": target, "tip": part.id,
                             "tip_params": shape.get("params", {})})
        return apply(r, {**extract(shape), **fields, "op": "add_limb" if is_limb else "add_part"})
    if name == "reground":
        r.pop("ground_y", None)
        return ""
    # Spine edits keep the floor where it is so the legs don't jump (a longer tail
    # must not lift the creature). Limb edits change where the feet are, so they
    # re-ground automatically unless the op asks to keep the current floor.
    keep_ground = bool(op.pop("keep_ground", False)) if isinstance(op, dict) else False
    if name in ("add_limb", "set_limb", "remove_limb") and not keep_ground:
        r.pop("ground_y", None)
    elif r["limbs"] and "ground_y" not in r and name in (
            "set_vertebra", "insert_vertebra", "remove_vertebra", "scale_body", "set_spine"):
        from .builder import Builder
        current = Builder(r, "preview")
        surface = R.Spine(current.recipe["spine"])
        current.resolve_limbs(surface)
        r["ground_y"] = current.ground_level(surface)
    sp = r["spine"]
    if name == "set_name":
        r["name"] = str(op.get("name", r.get("name", "")))
    elif name == "set_spine":
        if not isinstance(op.get("spine"), list):
            return "set_spine needs an array"
        replacement = copy.deepcopy(op["spine"])
        if len(replacement) == len(sp):
            for old, new in zip(sp, replacement):
                if isinstance(new, dict):
                    new.setdefault("id", old["id"])
        r["spine"] = replacement
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
        # Merge adjacent strips locally when an endpoint is removed.
        ids = ["@rear"] + [v["id"] for v in sp] + ["@front"]
        left, gone, right = ids[i:i + 3]
        for item in r["limbs"] + r["parts"]:
            bind = item.get("bind")
            if bind and gone in bind[:2]:
                t = bind[2] * 0.5 if bind[1] == gone else 0.5 + bind[2] * 0.5
                item["bind"] = [left, right, t]
        sp.pop(i)
    elif name == "scale_body":
        for v in sp:
            v["w"] = v["w"] * float(op.get("w", 1.0))
            v["h"] = v["h"] * float(op.get("h", 1.0))
            v["z"] = v["z"] * float(op.get("length", 1.0))
    elif name == "add_limb":
        l = {k: v for k, v in op.items() if k != "op"}
        if l.get("family"):
            family = catalog.get(str(l["family"]))
            if family is None or family.preset is None:
                return "unknown limb family %s" % l["family"]
            for key in ("u", "theta"):
                l.setdefault(key, family.hint[key])
        if "uid" not in l or _find(r["limbs"], str(l["uid"])) >= 0:
            l["uid"] = _new_uid(r, "limb")
        _snap_limb(l, op)
        r["limbs"].append(l)
    elif name == "set_limb":
        i = _find(r["limbs"], str(op.get("uid", "")))
        if i < 0:
            return "no limb %s" % op.get("uid", "")
        if "tip" in op and op["tip"] != r["limbs"][i].get("tip"):
            r["limbs"][i]["tip_params"] = {}
        if "u" in op or op.get("snap") or "on" in op:
            r["limbs"][i].pop("bind", None)
        for k, v in op.items():
            if k in ("op", "uid"):
                continue
            if k in ("tip_params", "params") and isinstance(v, dict):
                r["limbs"][i].setdefault(k, {}).update(v)
            else:
                r["limbs"][i][k] = v
        _snap_limb(r["limbs"][i], op)
    elif name == "remove_limb":
        i = _find(r["limbs"], str(op.get("uid", "")))
        if i < 0:
            return "no limb %s" % op.get("uid", "")
        uid = r["limbs"].pop(i)["uid"]
        removed = {p["uid"] for p in r["parts"] if p.get("on") == uid and "uid" in p}
        r["parts"] = [p for p in r["parts"] if p.get("on") not in removed | {uid}]
    elif name == "add_part":
        part = catalog.get(str(op.get("part", "")))
        if part is None:
            return "unknown part %s" % op.get("part", "")
        if part.attach == "limb":
            if op.get("on", "body") != "body":
                return "limbs attach to the body surface"
            fields = {k: v for k, v in op.items() if k not in ("part", "on", "op")}
            return apply(r, {**fields, "op": "add_limb", "family": part.id})
        if part.host == "limb" and _find(r["limbs"], op.get("on", "body")) < 0:
            return "%s requires a host limb" % part.id
        if part.attach == "core":
            r["parts"] = [p for p in r["parts"] if getattr(catalog.get(p.get("part")), "attach", None) != "core"]
            r.pop("ground_y", None)
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
        definition = catalog.get(r["parts"][i].get("part"))
        if definition and definition.attach == "core" and {"offset", "scale", "params"} & op.keys():
            r.pop("ground_y", None)
        if "u" in op or op.get("snap") or "on" in op:
            r["parts"][i].pop("bind", None)
        for k, v in op.items():
            if k in ("op", "uid"):
                continue
            if k == "params" and isinstance(v, dict):
                r["parts"][i].setdefault("params", {}).update(v)
            else:
                r["parts"][i][k] = v
        if "theta" in op and r["parts"][i].get("on", "body") == "body":
            angle = R.wrap_angle(float(op["theta"]))
            if abs(abs(angle) - 90) <= placement.CENTER_SNAP_DEG:
                r["parts"][i]["theta"] = 90.0 if angle > 0 else -90.0
        _snap_part(r["parts"][i], op)
    elif name == "remove_part":
        i = _find(r["parts"], str(op.get("uid", "")))
        if i < 0:
            return "no part %s" % op.get("uid", "")
        removed = r["parts"].pop(i)
        if removed.get("part") == "muzzle":
            r["parts"] = [p for p in r["parts"] if p.get("on") != removed["uid"]]
        part = catalog.get(removed.get("part"))
        if part and part.attach == "core":
            r.pop("ground_y", None)
    else:
        return "unknown op '%s'" % name
    return ""


def apply_all(src, ops):
    r = R.normalize(src)[0] if src.get("shapes") or src.get("version", 1) == 1 else copy.deepcopy(src)
    r.pop("paint", None)  # Version 2 recipes may carry obsolete styling data.
    errors = []
    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            errors.append("op %d is not an object" % i)
            continue
        e = apply(r, dict(op))
        if e:
            errors.append("op %d (%s): %s" % (i, op.get("op", "?"), e))
    return r, errors


def showcase_recipe(part_id):
    """Small neutral creature wearing one part (thumbnails, tests)."""
    r = R.default_recipe()
    r["name"] = part_id

    part = catalog.get(part_id)
    if part is None:
        return r
    if part.preset:
        r["limbs"] = [{"uid": "l", "family": part_id, **part.hint}]
    elif part.attach == "tip" or part.host == "limb":
        arm = part.cap != "foot"
        r["limbs"] = [{"uid": "l", "u": 0.62 if arm else 0.45, "theta": 0.0 if arm else -60.0,
                       "segments": [[0.25, 0.0, 0.1], [0.15, -0.05, 0.25]] if arm else [[0.12, -0.25, 0.05], [0.0, -0.25, 0.05]],
                       "radii": [0.09, 0.07, 0.05], "tip": part_id if part.attach == "tip" else ""}]
        if part.host == "limb":
            r["parts"] = [{"uid": "p", "part": part_id, "on": "l", "u": .54, "theta": -80}]
    else:
        r["parts"] = [{"uid": "p", "part": part_id, "u": part.hint["u"], "theta": part.hint["theta"]}]
    return r
