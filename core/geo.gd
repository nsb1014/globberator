## Low-poly geometry buffer.
##
## Triangles are stored unindexed (3 consecutive vertices) so every face is
## flat shaded. Each triangle carries a paint slot and a surface coordinate
## used for body patterns. Each vertex carries up to two bone references and a
## blend weight. Bone references are local indices; the builder remaps them.
extends RefCounted

const SLOTS := ["skin", "base", "accent", "detail", "white", "black", "dark", "horn", "claw", "teeth", "eye"]

var pos := PackedVector3Array()
var b0 := PackedInt32Array()
var b1 := PackedInt32Array()
var w0 := PackedFloat32Array()
var tri_slot := PackedStringArray()
var tri_uv := PackedVector2Array()

# Current emission state.
var bone := 0
var bone_b := 0
var weight := 1.0
var slot := "base"
var uv := Vector2.ZERO


func tri_count() -> int:
	return tri_slot.size()


## Counter-clockwise when seen from outside (right-hand normal points out).
func tri(a: Vector3, b: Vector3, c: Vector3) -> void:
	pos.append(a); pos.append(b); pos.append(c)
	for i in 3:
		b0.append(bone); b1.append(bone_b); w0.append(weight)
	tri_slot.append(slot)
	tri_uv.append(uv)


## Per-vertex weights for blended surfaces.
func tri_w(a: Vector3, b: Vector3, c: Vector3, wa: Vector3i, wb: Vector3i, wc: Vector3i, fa: float, fb: float, fc: float) -> void:
	pos.append(a); pos.append(b); pos.append(c)
	b0.append(wa.x); b1.append(wa.y); w0.append(fa)
	b0.append(wb.x); b1.append(wb.y); w0.append(fb)
	b0.append(wc.x); b1.append(wc.y); w0.append(fc)
	tri_slot.append(slot)
	tri_uv.append(uv)


func quad(a: Vector3, b: Vector3, c: Vector3, d: Vector3) -> void:
	tri(a, b, c)
	tri(a, c, d)


## Strip between two rings of equal size; rings ordered CCW looking along the
## sweep direction (from ra toward rb) means outward faces.
func ring_strip(ra: PackedVector3Array, rb: PackedVector3Array) -> void:
	var n := ra.size()
	for i in n:
		var j := (i + 1) % n
		quad(ra[i], ra[j], rb[j], rb[i])


func fan(center: Vector3, ring: PackedVector3Array, flip := false) -> void:
	var n := ring.size()
	for i in n:
		var j := (i + 1) % n
		if flip:
			tri(center, ring[j], ring[i])
		else:
			tri(center, ring[i], ring[j])


static func ring(c: Vector3, x: Vector3, y: Vector3, rx: float, ry: float, segs: int, phase := 0.0) -> PackedVector3Array:
	var out := PackedVector3Array()
	for i in segs:
		var a := TAU * (float(i) + phase) / segs
		out.append(c + x * cos(a) * rx + y * sin(a) * ry)
	return out


## Ellipsoid with radii r in basis (x, y, z). Poles on the y axis.
func ellipsoid(c: Vector3, r: Vector3, basis := Basis(), segs := 8, rings := 5) -> void:
	var bx := basis.x * r.x
	var by := basis.y * r.y
	var bz := basis.z * r.z
	var prev := PackedVector3Array()
	var top := c + by
	var bottom := c - by
	for k in range(1, rings):
		var phi := PI * float(k) / rings
		var rr := sin(phi)
		var yy := cos(phi)
		var cur := PackedVector3Array()
		for i in segs:
			var a := TAU * (float(i) + 0.5 * (k % 2)) / segs
			cur.append(c + by * yy + (bx * cos(a) - bz * sin(a)) * rr)
		if k == 1:
			for i in segs:
				tri(top, cur[i], cur[(i + 1) % segs])
		else:
			_band(prev, cur)
		prev = cur
	for i in segs:
		tri(bottom, prev[(i + 1) % segs], prev[i])


## Band between two rings whose second ring is phase shifted by half a step;
## falls back to quads when phases match.
func _band(top: PackedVector3Array, bot: PackedVector3Array) -> void:
	var n := top.size()
	for i in n:
		var j := (i + 1) % n
		quad(top[i], bot[i], bot[j], top[j])


## Sweep a tube along points with per-point radii. Optional caps. The cross
## section is an ellipse scaled by `squash` (x scale, y scale) in the moving frame.
func tube(points: PackedVector3Array, radii: PackedFloat32Array, segs := 6, cap_start := true, cap_end := true, up_hint := Vector3.UP, squash := Vector2.ONE, point_cap := false) -> void:
	var n := points.size()
	if n < 2:
		return
	var frames := parallel_frames(points, up_hint)
	var rings: Array[PackedVector3Array] = []
	for i in n:
		var f: Basis = frames[i]
		rings.append(ring(points[i], f.x, f.y, radii[i] * squash.x, radii[i] * squash.y, segs))
	for i in n - 1:
		ring_strip(rings[i], rings[i + 1])
	if cap_start:
		fan(points[0] - frames[0].z * radii[0] * 0.3, rings[0], true)
	if cap_end:
		var tip: Vector3 = points[n - 1] + frames[n - 1].z * (radii[n - 1] * (2.5 if point_cap else 0.3))
		fan(tip, rings[n - 1], false)


## Frames with z along the curve, x/y perpendicular, transported smoothly.
static func parallel_frames(points: PackedVector3Array, up_hint: Vector3) -> Array:
	var n := points.size()
	var out := []
	var prev_y := up_hint
	for i in n:
		var t: Vector3
		if i == 0:
			t = points[1] - points[0]
		elif i == n - 1:
			t = points[n - 1] - points[n - 2]
		else:
			t = points[i + 1] - points[i - 1]
		t = t.normalized()
		var y := prev_y - t * prev_y.dot(t)
		if y.length() < 1e-4:
			y = Vector3.FORWARD - t * Vector3.FORWARD.dot(t)
			if y.length() < 1e-4:
				y = Vector3.RIGHT - t * Vector3.RIGHT.dot(t)
		y = y.normalized()
		var x := y.cross(t).normalized()
		out.append(Basis(x, y, t))
		prev_y = y
	return out


## Cone from base center along axis to tip.
func cone(base: Vector3, tip: Vector3, r: float, segs := 6, up_hint := Vector3.UP) -> void:
	var f: Basis = parallel_frames(PackedVector3Array([base, tip]), up_hint)[0]
	var rr := ring(base, f.x, f.y, r, r, segs)
	fan(tip, rr, false)
	fan(base, rr, true)


func box(c: Vector3, size: Vector3, basis := Basis()) -> void:
	var h := size * 0.5
	var p := []
	for z in [-1, 1]:
		for y in [-1, 1]:
			for x in [-1, 1]:
				p.append(c + basis * Vector3(h.x * x, h.y * y, h.z * z))
	# indices: x + 2y + 4z
	quad(p[0], p[2], p[3], p[1])  # -z
	quad(p[4], p[5], p[7], p[6])  # +z
	quad(p[0], p[4], p[6], p[2])  # -x
	quad(p[1], p[3], p[7], p[5])  # +x
	quad(p[0], p[1], p[5], p[4])  # -y
	quad(p[2], p[6], p[7], p[3])  # +y


## Flat, double-faced polygon (fins, wings, plates) extruded by thickness along n.
func slab(outline: PackedVector3Array, n: Vector3, thickness: float) -> void:
	var newell := Vector3.ZERO
	for i in outline.size():
		var a := outline[i]
		var b := outline[(i + 1) % outline.size()]
		newell += a.cross(b)
	if newell.dot(n) < 0.0:
		outline = outline.duplicate()
		outline.reverse()
	var off := n.normalized() * thickness * 0.5
	var c := Vector3.ZERO
	for p in outline:
		c += p
	c /= outline.size()
	var top := PackedVector3Array()
	var bot := PackedVector3Array()
	for p in outline:
		top.append(p + off)
		bot.append(p - off)
	var m := outline.size()
	for i in m:
		var j := (i + 1) % m
		tri(c + off, top[i], top[j])
		tri(c - off, bot[j], bot[i])
		quad(top[j], top[i], bot[i], bot[j])


## Append another buffer transformed by xform. Bone indices map through bone_map
## (local index -> new index). Mirrored transforms flip the winding.
func append(other, xform: Transform3D, bone_map: PackedInt32Array, slot_override := "") -> void:
	var flip := xform.basis.determinant() < 0.0
	for t in other.tri_count():
		var k: int = t * 3
		var order := [0, 2, 1] if flip else [0, 1, 2]
		for o in order:
			var v: int = k + o
			pos.append(xform * other.pos[v])
			b0.append(bone_map[other.b0[v]] if other.b0[v] < bone_map.size() else bone_map[0])
			b1.append(bone_map[other.b1[v]] if other.b1[v] < bone_map.size() else bone_map[0])
			w0.append(other.w0[v])
		tri_slot.append(slot_override if slot_override != "" else other.tri_slot[t])
		tri_uv.append(other.tri_uv[t])


func aabb() -> AABB:
	if pos.is_empty():
		return AABB()
	var box_ := AABB(pos[0], Vector3.ZERO)
	for p in pos:
		box_ = box_.expand(p)
	return box_
