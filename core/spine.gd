## Spine curve in the sagittal plane (x = 0).
##
## Vertebrae are interpolated with a Catmull-Rom curve. Each sample carries
## its position, tangent, ellipse radii, arc-length parameter u in [0, 1] and
## a fractional vertebra index used for skin weights.
extends RefCounted

const SUB := 9
const CAP := 8

var vpos: Array[Vector3] = []
var vw: Array[float] = []
var vh: Array[float] = []
var samples: Array = []   # Array of Dictionary
var length := 0.0


func _init(spine: Array, shift := Vector3.ZERO) -> void:
	for v in spine:
		vpos.append(Vector3(0.0, v["y"], v["z"]) + shift)
		vw.append(v["w"])
		vh.append(v["h"])
	_sample()


static func _cr(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t: float) -> Vector3:
	var t2 := t * t
	var t3 := t2 * t
	return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)


static func _crf(a: float, b: float, c: float, d: float, t: float) -> float:
	return _cr(Vector3(a, 0, 0), Vector3(b, 0, 0), Vector3(c, 0, 0), Vector3(d, 0, 0), t).x


func _sample() -> void:
	var n := vpos.size()
	samples.clear()
	for i in n - 1:
		var i0 := maxi(i - 1, 0)
		var i3 := mini(i + 2, n - 1)
		var steps := SUB if i < n - 2 else SUB + 1
		for k in steps:
			var t := float(k) / SUB
			var p := _cr(vpos[i0], vpos[i], vpos[i + 1], vpos[i3], t)
			var ww := maxf(0.03, _crf(vw[i0], vw[i], vw[i + 1], vw[i3], t))
			var hh := maxf(0.03, _crf(vh[i0], vh[i], vh[i + 1], vh[i3], t))
			samples.append({"p": p, "w": ww, "h": hh, "v": float(i) + t})
	_tangents()
	_add_caps()
	_tangents()
	_arc()


func _tangents() -> void:
	for k in samples.size():
		var a: Vector3 = samples[maxi(k - 1, 0)]["p"]
		var b: Vector3 = samples[mini(k + 1, samples.size() - 1)]["p"]
		var t := (b - a)
		t.x = 0.0
		samples[k]["t"] = t.normalized() if t.length() > 1e-6 else Vector3.BACK


## Rounded end caps so the body closes; u = 0 is the rear tip, u = 1 the front tip.
func _add_caps() -> void:
	var first: Dictionary = samples[0]
	var last: Dictionary = samples[samples.size() - 1]
	var rear := []
	var front := []
	for k in range(1, CAP + 1):
		var a := PI * 0.5 * float(k) / CAP
		for e in [[first, -1.0, rear], [last, 1.0, front]]:
			var src: Dictionary = e[0]
			var cl: float = minf(src["w"], src["h"]) * 0.95
			var c := cos(a) if k < CAP else 0.0
			e[2].append({"p": src["p"] + src["t"] * e[1] * cl * sin(a), "w": maxf(src["w"] * c, 0.0), "h": maxf(src["h"] * c, 0.0), "v": src["v"], "tip": k == CAP})
	rear.reverse()
	samples = rear + samples + front


func _arc() -> void:
	var acc := 0.0
	for k in samples.size():
		if k > 0:
			acc += samples[k]["p"].distance_to(samples[k - 1]["p"])
		samples[k]["s"] = acc
	length = maxf(acc, 1e-4)
	for k in samples.size():
		var sm: Dictionary = samples[k]
		sm["u"] = sm["s"] / length
		var a: Dictionary = samples[maxi(k - 1, 0)]
		var b: Dictionary = samples[mini(k + 1, samples.size() - 1)]
		var ds: float = maxf(b["s"] - a["s"], 1e-5)
		sm["dw"] = clampf((b["w"] - a["w"]) / ds, -20.0, 20.0)
		sm["dh"] = clampf((b["h"] - a["h"]) / ds, -20.0, 20.0)


## Interpolated sample at arc parameter u.
func at(u: float) -> Dictionary:
	u = clampf(u, 0.0, 1.0)
	for k in range(1, samples.size()):
		if samples[k]["u"] >= u:
			var a: Dictionary = samples[k - 1]
			var b: Dictionary = samples[k]
			var span: float = b["u"] - a["u"]
			var f: float = 0.0 if span < 1e-6 else (u - a["u"]) / span
			return {
				"p": a["p"].lerp(b["p"], f),
				"t": a["t"].lerp(b["t"], f).normalized(),
				"w": lerpf(a["w"], b["w"], f),
				"h": lerpf(a["h"], b["h"], f),
				"v": lerpf(a["v"], b["v"], f),
				"dw": lerpf(a["dw"], b["dw"], f),
				"dh": lerpf(a["dh"], b["dh"], f),
				"u": u,
			}
	return samples[samples.size() - 1]


## Up vector of the cross-section frame (perpendicular to tangent, in sagittal plane).
static func up_of(t: Vector3) -> Vector3:
	return t.cross(Vector3.RIGHT).normalized()


## Surface point at (u, theta). theta in degrees: 0 = +x side, 90 = top,
## 180 = -x side, -90 = belly. Returns position, outward normal and a part
## frame (y = normal, z = forward along the spine).
func surface(u: float, theta_deg: float, offset := 0.0) -> Dictionary:
	var s := at(u)
	var t: Vector3 = s["t"]
	var up := up_of(t)
	var a := deg_to_rad(theta_deg)
	var w: float = maxf(s["w"], 0.005)
	var h: float = maxf(s["h"], 0.005)
	var ca := cos(a)
	var sa := sin(a)
	var p: Vector3 = s["p"] + Vector3.RIGHT * ca * w + up * sa * h
	var nr := (Vector3.RIGHT * ca / w + up * sa / h).normalized()
	var r := sqrt(pow(w * ca, 2) + pow(h * sa, 2))
	var drds: float = (w * s["dw"] * ca * ca + h * s["dh"] * sa * sa) / maxf(r, 1e-4)
	var n := (nr - t * clampf(drds, -8.0, 8.0)).normalized()
	p += n * offset
	var z := (t - n * t.dot(n)).normalized()
	if z.length() < 1e-4:
		z = Vector3.BACK
	var x := n.cross(z).normalized()
	return {"p": p, "n": n, "basis": Basis(x, n, z), "v": s["v"], "u": u}


## Nearest (u, theta, distance-to-surface) for a point, used by the editor.
func project(point: Vector3) -> Dictionary:
	var best := {"u": 0.5, "theta": 90.0, "d": INF}
	for s in samples:
		var t: Vector3 = s["t"]
		var rel: Vector3 = point - s["p"]
		var along := rel.dot(t)
		if absf(along) > length / samples.size() * 1.5 and s != samples[0] and s != samples[samples.size() - 1]:
			continue
		var up := up_of(t)
		var lx: float = rel.dot(Vector3.RIGHT) / s["w"]
		var ly: float = rel.dot(up) / s["h"]
		var theta := rad_to_deg(atan2(ly, lx))
		var radial := Vector2(lx * s["w"], ly * s["h"]).length()
		var surf_r := Vector2(cos(deg_to_rad(theta)) * s["w"], sin(deg_to_rad(theta)) * s["h"]).length()
		var d := absf(radial - surf_r) + absf(along)
		if d < best["d"]:
			best = {"u": s["u"], "theta": theta, "d": d}
	return best


func bottom_y() -> float:
	var m := INF
	for s in samples:
		m = minf(m, s["p"].y - s["h"])
	# end caps hang a bit lower when the spine tilts; small margin
	return m
