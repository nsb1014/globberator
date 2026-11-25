## Recipe operations shared by the editor and the AI. Each op is a small JSON
## object {"op": name, ...}. Ops never touch geometry; the builder does.
extends RefCounted

const Recipe = preload("res://core/recipe.gd")
const Catalog = preload("res://library/catalog.gd")

const SPEC := {
	"set_name": {"name": "string"},
	"set_spine": {"spine": "array of {y,z,w,h} (rear to front)"},
	"set_vertebra": {"index": "int", "y?": "float", "z?": "float", "w?": "float", "h?": "float"},
	"insert_vertebra": {"index": "int (insert before; -1 = append at head)", "y?": "float", "z?": "float", "w?": "float", "h?": "float"},
	"remove_vertebra": {"index": "int"},
	"scale_body": {"w?": "float factor", "h?": "float factor", "length?": "float factor"},
	"add_limb": {"uid?": "string", "u": "float", "theta": "deg", "segments": "[[x,y,z],...]", "radii?": "[...]", "tip?": "part id", "tip_params?": "{}", "mirror?": "bool"},
	"set_limb": {"uid": "string", "...": "any limb field to replace"},
	"remove_limb": {"uid": "string"},
	"add_part": {"uid?": "string", "part": "part id", "on?": "body | limb uid", "u?": "float", "theta?": "deg", "offset?": "float", "rot?": "[x,y,z] deg", "scale?": "float", "params?": "{}", "mirror?": "bool"},
	"set_part": {"uid": "string", "...": "any part field to replace (params merge)"},
	"remove_part": {"uid": "string"},
	"set_paint": {"base?": "#hex", "accent?": "#hex", "detail?": "#hex", "pattern?": "none|stripes|spots|patches|gradient", "pattern_scale?": "float", "belly?": "bool"},
}


static func describe() -> Dictionary:
	return SPEC


static func _new_uid(r: Dictionary, prefix: String) -> String:
	var used := {}
	for l in r.get("limbs", []):
		used[l.get("uid", "")] = true
	for p in r.get("parts", []):
		used[p.get("uid", "")] = true
	var k := 1
	while used.has("%s%d" % [prefix, k]):
		k += 1
	return "%s%d" % [prefix, k]


static func _find(list: Array, uid: String) -> int:
	for i in list.size():
		if list[i].get("uid", "") == uid:
			return i
	return -1


## Apply one op in place. Returns "" or an error string.
static func apply(r: Dictionary, op: Dictionary) -> String:
	if not r.has("limbs"):
		r["limbs"] = []
	if not r.has("parts"):
		r["parts"] = []
	if not r.has("spine"):
		r["spine"] = Recipe.default_recipe()["spine"]
	var name := str(op.get("op", ""))
	match name:
		"set_name":
			r["name"] = str(op.get("name", r.get("name", "")))
		"set_spine":
			if typeof(op.get("spine")) != TYPE_ARRAY:
				return "set_spine needs an array"
			r["spine"] = op["spine"].duplicate(true)
		"set_vertebra":
			var i := int(op.get("index", -1))
			if i < 0 or i >= r["spine"].size():
				return "vertebra index out of range"
			for k in ["y", "z", "w", "h"]:
				if op.has(k):
					r["spine"][i][k] = float(op[k])
		"insert_vertebra":
			var i := int(op.get("index", -1))
			var sp: Array = r["spine"]
			if i < 0 or i > sp.size():
				i = sp.size()
			var ref: Dictionary = sp[clampi(i if i < sp.size() else sp.size() - 1, 0, sp.size() - 1)]
			var nb: Dictionary = sp[clampi(i - 1, 0, sp.size() - 1)]
			var v := {"y": (ref["y"] + nb["y"]) * 0.5, "z": (ref["z"] + nb["z"]) * 0.5, "w": ref["w"], "h": ref["h"]}
			if i == sp.size():
				var d: float = sp[sp.size() - 1]["z"] - sp[maxi(sp.size() - 2, 0)]["z"]
				v = {"y": ref["y"], "z": ref["z"] + (d if absf(d) > 0.05 else 0.3), "w": ref["w"] * 0.85, "h": ref["h"] * 0.85}
			elif i == 0:
				v = {"y": ref["y"], "z": ref["z"] - 0.3, "w": ref["w"] * 0.8, "h": ref["h"] * 0.8}
			for k in ["y", "z", "w", "h"]:
				if op.has(k):
					v[k] = float(op[k])
			sp.insert(i, v)
		"remove_vertebra":
			var i := int(op.get("index", -1))
			if r["spine"].size() <= 2:
				return "spine needs at least 2 vertebrae"
			if i < 0 or i >= r["spine"].size():
				return "vertebra index out of range"
			r["spine"].remove_at(i)
		"scale_body":
			for v in r["spine"]:
				v["w"] = float(v["w"]) * float(op.get("w", 1.0))
				v["h"] = float(v["h"]) * float(op.get("h", 1.0))
				v["z"] = float(v["z"]) * float(op.get("length", 1.0))
		"add_limb":
			var l := {}
			for k in op.keys():
				if k != "op":
					l[k] = op[k]
			if not l.has("uid") or _find(r["limbs"], str(l["uid"])) >= 0:
				l["uid"] = _new_uid(r, "limb")
			r["limbs"].append(l)
		"set_limb":
			var i := _find(r["limbs"], str(op.get("uid", "")))
			if i < 0:
				return "no limb %s" % op.get("uid", "")
			for k in op.keys():
				if k in ["op", "uid"]:
					continue
				if k == "tip_params" and typeof(op[k]) == TYPE_DICTIONARY:
					var tp: Dictionary = r["limbs"][i].get("tip_params", {})
					tp.merge(op[k], true)
					r["limbs"][i]["tip_params"] = tp
				else:
					r["limbs"][i][k] = op[k]
		"remove_limb":
			var i := _find(r["limbs"], str(op.get("uid", "")))
			if i < 0:
				return "no limb %s" % op.get("uid", "")
			var uid: String = r["limbs"][i]["uid"]
			r["limbs"].remove_at(i)
			var keep := []
			for p in r["parts"]:
				if p.get("on", "body") != uid:
					keep.append(p)
			r["parts"] = keep
		"add_part":
			var def = Catalog.shared().get_part(str(op.get("part", "")))
			if def == null:
				return "unknown part %s" % op.get("part", "")
			var p := {"part": def.id, "u": def.hint["u"], "theta": def.hint["theta"], "mirror": def.default_mirror}
			for k in op.keys():
				if k != "op":
					p[k] = op[k]
			if not p.has("uid") or _find(r["parts"], str(p["uid"])) >= 0:
				p["uid"] = _new_uid(r, def.category)
			r["parts"].append(p)
		"set_part":
			var i := _find(r["parts"], str(op.get("uid", "")))
			if i < 0:
				return "no part %s" % op.get("uid", "")
			for k in op.keys():
				if k in ["op", "uid"]:
					continue
				if k == "params" and typeof(op[k]) == TYPE_DICTIONARY:
					var pp: Dictionary = r["parts"][i].get("params", {})
					pp.merge(op[k], true)
					r["parts"][i]["params"] = pp
				else:
					r["parts"][i][k] = op[k]
		"remove_part":
			var i := _find(r["parts"], str(op.get("uid", "")))
			if i < 0:
				return "no part %s" % op.get("uid", "")
			r["parts"].remove_at(i)
		"set_paint":
			var pa: Dictionary = r.get("paint", Recipe.default_paint())
			for k in op.keys():
				if k != "op":
					pa[k] = op[k]
			r["paint"] = pa
		_:
			return "unknown op '%s'" % name
	return ""


static func apply_all(src: Dictionary, ops: Array) -> Dictionary:
	var r := src.duplicate(true)
	var errors := []
	for i in ops.size():
		if typeof(ops[i]) != TYPE_DICTIONARY:
			errors.append("op %d is not an object" % i)
			continue
		var e := apply(r, ops[i])
		if e != "":
			errors.append("op %d (%s): %s" % [i, ops[i].get("op", "?"), e])
	return {"recipe": r, "errors": errors}


## Small neutral creature wearing one part, for thumbnails.
static func showcase_recipe(part_id: String) -> Dictionary:
	var r := Recipe.default_recipe()
	r["name"] = part_id
	r["paint"] = {"base": "#9aa3ad", "accent": "#5f87b5", "detail": "#d8d2c4", "pattern": "none", "pattern_scale": 1.0, "belly": false}
	var def = Catalog.shared().get_part(part_id)
	if def == null:
		return r
	if def.attach == "tip":
		var arm: bool = def.cap != "foot"
		r["limbs"] = [{"uid": "l", "u": 0.62 if arm else 0.45, "theta": 0.0 if arm else -60.0,
			"segments": [[0.25, 0.0, 0.1], [0.15, -0.05, 0.25]] if arm else [[0.12, -0.25, 0.05], [0.0, -0.25, 0.05]],
			"radii": [0.09, 0.07, 0.05], "tip": part_id, "mirror": not arm}]
	else:
		r["parts"] = [{"uid": "p", "part": part_id, "u": def.hint["u"], "theta": def.hint["theta"], "mirror": def.default_mirror}]
	return r
