## Recipe: the versioned, human-readable description of a creature.
##
## A recipe is a plain Dictionary (JSON compatible). `normalize` fills
## defaults, clamps values into the allowed (style) ranges, and reports every
## change as a warning so the AI loop can learn from it.
extends RefCounted

const FORMAT := "polyforge.recipe"
const VERSION := 1

const LIMITS := {
	"vertebrae": [2, 16],
	"spine_y": [0.0, 8.0],
	"spine_z": [-8.0, 8.0],
	"radius": [0.04, 2.5],
	"limbs": 12,
	"segments": [1, 5],
	"segment_len": [0.02, 3.5],
	"limb_radius": [0.02, 1.2],
	"parts": 80,
	"scale": [0.2, 4.0],
	"offset": [-0.6, 0.6],
}

const PATTERNS := ["none", "stripes", "spots", "patches", "gradient"]


static func default_recipe() -> Dictionary:
	return {
		"format": FORMAT,
		"version": VERSION,
		"name": "Blob",
		"spine": [
			{"y": 0.55, "z": -0.6, "w": 0.32, "h": 0.32},
			{"y": 0.6, "z": -0.2, "w": 0.45, "h": 0.42},
			{"y": 0.62, "z": 0.25, "w": 0.45, "h": 0.42},
			{"y": 0.7, "z": 0.65, "w": 0.33, "h": 0.32},
			{"y": 0.75, "z": 0.95, "w": 0.26, "h": 0.25},
		],
		"limbs": [],
		"parts": [],
		"paint": default_paint(),
	}


static func default_paint() -> Dictionary:
	return {"base": "#6f9a52", "accent": "#35552b", "detail": "#e9dcae", "pattern": "stripes", "pattern_scale": 1.0, "belly": true}


static func load_file(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("cannot open recipe %s" % path)
		return {}
	var data = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_DICTIONARY:
		push_error("recipe %s is not a JSON object" % path)
		return {}
	return data


static func to_json(recipe: Dictionary) -> String:
	return JSON.stringify(recipe, "  ", true) + "\n"


static func save_file(recipe: Dictionary, path: String) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(to_json(recipe))


static func _num(v, def: float) -> float:
	if typeof(v) == TYPE_FLOAT or typeof(v) == TYPE_INT:
		return snappedf(float(v), 0.0001)
	return def


static func _clamp(v: float, r: Array, what: String, warns: Array) -> float:
	var c := clampf(v, r[0], r[1])
	if absf(c - v) > 1e-6:
		warns.append("%s clamped %.3f -> %.3f" % [what, v, c])
	return snappedf(c, 0.0001)


static func _vec(v, def: Array) -> Array:
	if typeof(v) == TYPE_ARRAY and v.size() == 3:
		return [_num(v[0], 0.0), _num(v[1], 0.0), _num(v[2], 0.0)]
	return def.duplicate()


static func wrap_angle(a: float) -> float:
	return snappedf(wrapf(a, -180.0, 180.0), 0.0001)


## Returns {"recipe": Dictionary, "warnings": Array[String]}.
static func normalize(src: Dictionary, catalog) -> Dictionary:
	var w: Array = []
	var r := {"format": FORMAT, "version": VERSION}
	r["name"] = str(src.get("name", "Untitled"))
	# Spine
	var spine: Array = []
	var s_in = src.get("spine", [])
	if typeof(s_in) != TYPE_ARRAY or s_in.size() < 2:
		w.append("spine missing or too short; using default spine")
		s_in = default_recipe()["spine"]
	if s_in.size() > LIMITS["vertebrae"][1]:
		w.append("spine truncated to %d vertebrae" % LIMITS["vertebrae"][1])
		s_in = s_in.slice(0, LIMITS["vertebrae"][1])
	for i in s_in.size():
		var v = s_in[i]
		if typeof(v) != TYPE_DICTIONARY:
			v = {}
		spine.append({
			"y": _clamp(_num(v.get("y"), 0.6), LIMITS["spine_y"], "spine[%d].y" % i, w),
			"z": _clamp(_num(v.get("z"), 0.0), LIMITS["spine_z"], "spine[%d].z" % i, w),
			"w": _clamp(_num(v.get("w"), 0.3), LIMITS["radius"], "spine[%d].w" % i, w),
			"h": _clamp(_num(v.get("h", v.get("w")), 0.3), LIMITS["radius"], "spine[%d].h" % i, w),
		})
	r["spine"] = spine
	var uids := {}
	# Limbs
	var limbs: Array = []
	var l_in = src.get("limbs", [])
	if typeof(l_in) != TYPE_ARRAY:
		l_in = []
	for i in mini(l_in.size(), LIMITS["limbs"]):
		var l = l_in[i]
		if typeof(l) != TYPE_DICTIONARY:
			continue
		var uid := _unique(str(l.get("uid", "limb%d" % i)), uids)
		var segs: Array = []
		var s_src = l.get("segments", [])
		if typeof(s_src) != TYPE_ARRAY or s_src.is_empty():
			w.append("limb %s has no segments; using a default leg" % uid)
			s_src = [[0.1, -0.3, 0.0], [0.0, -0.3, 0.0]]
		for k in mini(s_src.size(), LIMITS["segments"][1]):
			var vv := _vec(s_src[k], [0.0, -0.3, 0.0])
			var vec := Vector3(vv[0], vv[1], vv[2])
			var ln := vec.length()
			var lim: Array = LIMITS["segment_len"]
			if ln < lim[0]:
				w.append("limb %s segment %d too short" % [uid, k])
				vec = Vector3(0, -lim[0], 0) if ln < 1e-6 else vec.normalized() * lim[0]
			elif ln > lim[1]:
				w.append("limb %s segment %d too long (%.2f), scaled to %.2f" % [uid, k, ln, lim[1]])
				vec = vec.normalized() * lim[1]
			segs.append([snappedf(vec.x, 0.0001), snappedf(vec.y, 0.0001), snappedf(vec.z, 0.0001)])
		var radii: Array = []
		var r_src = l.get("radii", [])
		if typeof(r_src) != TYPE_ARRAY:
			r_src = []
		for k in segs.size() + 1:
			var dr: float = lerpf(0.12, 0.06, float(k) / segs.size())
			var rv: float = _num(r_src[k], dr) if k < r_src.size() else (_num(r_src[r_src.size() - 1], dr) if r_src.size() > 0 else dr)
			radii.append(_clamp(rv, LIMITS["limb_radius"], "limb %s radius %d" % [uid, k], w))
		var tip := str(l.get("tip", ""))
		var tip_params := {}
		if tip != "":
			var def = catalog.get_part(tip)
			if def == null:
				w.append("limb %s: unknown tip part '%s' removed" % [uid, tip])
				tip = ""
			elif def.attach != "tip":
				w.append("limb %s: part '%s' is not a limb tip; removed" % [uid, tip])
				tip = ""
			else:
				tip_params = def.normalize_params(l.get("tip_params", {}), "limb %s tip" % uid, w)
		limbs.append({
			"uid": uid,
			"u": _clamp(_num(l.get("u"), 0.5), [0.0, 1.0], "limb %s u" % uid, w),
			"theta": wrap_angle(_num(l.get("theta"), -45.0)),
			"segments": segs,
			"radii": radii,
			"tip": tip,
			"tip_params": tip_params,
			"mirror": bool(l.get("mirror", true)),
		})
	if l_in.size() > LIMITS["limbs"]:
		w.append("only %d limbs allowed" % LIMITS["limbs"])
	r["limbs"] = limbs
	# Parts
	var parts: Array = []
	var p_in = src.get("parts", [])
	if typeof(p_in) != TYPE_ARRAY:
		p_in = []
	var limb_ids := {}
	for l in limbs:
		limb_ids[l["uid"]] = true
	for i in mini(p_in.size(), LIMITS["parts"]):
		var p = p_in[i]
		if typeof(p) != TYPE_DICTIONARY:
			continue
		var pid := str(p.get("part", ""))
		var def = catalog.get_part(pid)
		if def == null:
			w.append("unknown part '%s' removed" % pid)
			continue
		if def.attach == "tip":
			w.append("part '%s' is a limb tip; set it as a limb's tip instead (removed)" % pid)
			continue
		var uid := _unique(str(p.get("uid", "p%d" % i)), uids)
		var on := str(p.get("on", "body"))
		if on != "body" and not limb_ids.has(on):
			w.append("part %s attached to unknown limb '%s'; moved to body" % [uid, on])
			on = "body"
		var rot := _vec(p.get("rot", [0, 0, 0]), [0.0, 0.0, 0.0])
		parts.append({
			"uid": uid,
			"part": pid,
			"on": on,
			"u": _clamp(_num(p.get("u"), 0.9), [0.0, 1.0], "part %s u" % uid, w),
			"theta": wrap_angle(_num(p.get("theta"), 90.0)),
			"offset": _clamp(_num(p.get("offset"), 0.0), LIMITS["offset"], "part %s offset" % uid, w),
			"rot": [wrap_angle(rot[0]), wrap_angle(rot[1]), wrap_angle(rot[2])],
			"scale": _clamp(_num(p.get("scale"), 1.0), LIMITS["scale"], "part %s scale" % uid, w),
			"params": def.normalize_params(p.get("params", {}), "part %s" % uid, w),
			"mirror": bool(p.get("mirror", def.default_mirror)),
		})
	r["parts"] = parts
	# Paint
	var pa = src.get("paint", {})
	if typeof(pa) != TYPE_DICTIONARY:
		pa = {}
	var dp := default_paint()
	var paint := {}
	for key in ["base", "accent", "detail"]:
		var c := str(pa.get(key, dp[key]))
		if not Color.html_is_valid(c):
			w.append("paint.%s '%s' invalid" % [key, c])
			c = dp[key]
		paint[key] = "#" + Color.html(c).to_html(false)
	var pat := str(pa.get("pattern", dp["pattern"]))
	if not pat in PATTERNS:
		w.append("unknown pattern '%s'" % pat)
		pat = "none"
	paint["pattern"] = pat
	paint["pattern_scale"] = _clamp(_num(pa.get("pattern_scale"), 1.0), [0.25, 4.0], "paint.pattern_scale", w)
	paint["belly"] = bool(pa.get("belly", true))
	r["paint"] = paint
	return {"recipe": r, "warnings": w}


static func _unique(uid: String, used: Dictionary) -> String:
	uid = uid.strip_edges()
	if uid == "":
		uid = "x"
	var base := uid
	var k := 2
	while used.has(uid):
		uid = "%s_%d" % [base, k]
		k += 1
	used[uid] = true
	return uid
