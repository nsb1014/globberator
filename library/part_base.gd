## Base class for code-generated library parts.
##
## Local frame for surface parts: origin on the surface, +Y outward (normal).
## orient == "surface": +Z points along the spine toward the head.
## orient == "face":    +Z points up (useful for eyes, mouths, noses on the head cap).
## Tip parts (feet, hands): origin at the limb end joint.
##   feet:  +Y up, +Z creature forward; the sole is below the origin.
##   hands: +Y continues the last limb segment, +Z roughly forward.
## Bone index 0 is the part's own bone; extra bones follow in `bones` order.
extends RefCounted

const Geo = preload("res://core/geo.gd")

var id := ""
var category := ""
var desc := ""
var tags := PackedStringArray()
var params := {}            # name -> [min, max, default]
var attach := "surface"     # "surface" or "tip"
var orient := "surface"     # "surface" or "face"
var cap := ""               # animation capability: look, mouth, flop, flap, sway, foot, hand, grasp
var default_mirror := false
var hint := {"u": 0.5, "theta": 90.0}
var bones := []             # [{"name", "pivot": Vector3, "axis": Vector3, "angle": float}]


func normalize_params(src, what: String, warns: Array) -> Dictionary:
	var out := {}
	if typeof(src) != TYPE_DICTIONARY:
		src = {}
	for k in src.keys():
		if not params.has(k):
			warns.append("%s: unknown param '%s' for %s ignored" % [what, k, id])
	for k in params.keys():
		var r: Array = params[k]
		var v = src.get(k, r[2])
		if typeof(v) != TYPE_FLOAT and typeof(v) != TYPE_INT:
			v = r[2]
		var c := clampf(float(v), r[0], r[1])
		if absf(c - float(v)) > 1e-6:
			warns.append("%s: %s.%s clamped %.3f -> %.3f" % [what, id, k, float(v), c])
		out[k] = snappedf(c, 0.0001)
	return out


func pv(prm: Dictionary, k: String) -> float:
	if prm.has(k):
		return float(prm[k])
	return float(params[k][2])


func defaults() -> Dictionary:
	var d := {}
	for k in params.keys():
		d[k] = params[k][2]
	return d


## Ground contact point (feet only), in part-local units before scaling.
func sole(_prm: Dictionary) -> Vector3:
	return Vector3(0, -0.1, 0)


func make(prm: Dictionary):
	var g = Geo.new()
	g.slot = "base"
	build(g, prm)
	return g


func build(_g, _prm: Dictionary) -> void:
	pass


func describe() -> Dictionary:
	var ps := {}
	for k in params.keys():
		ps[k] = {"min": params[k][0], "max": params[k][1], "default": params[k][2]}
	return {
		"id": id, "category": category, "desc": desc, "tags": Array(tags),
		"attach": attach, "capability": cap, "mirror_default": default_mirror,
		"hint": hint, "params": ps,
	}


# ---- shared helpers -------------------------------------------------------

## Bezier-ish curved horn/tube points from origin along dir, bending toward bend.
static func curve_points(start: Vector3, dir: Vector3, bend: Vector3, length: float, n: int, twist := Vector3.ZERO) -> PackedVector3Array:
	var pts := PackedVector3Array()
	for i in n:
		var t := float(i) / (n - 1)
		pts.append(start + dir * length * t + bend * length * t * t + twist * length * t * t * t)
	return pts


static func taper(r0: float, r1: float, n: int, power := 1.0) -> PackedFloat32Array:
	var out := PackedFloat32Array()
	for i in n:
		out.append(lerpf(r0, r1, pow(float(i) / (n - 1), power)))
	return out
