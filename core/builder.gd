## Deterministic builder: recipe -> Node3D(Creature) / Skeleton3D / skinned MeshInstance3D.
##
## All bone rests have identity rotation (translation only) in skeleton space,
## which keeps the procedural animator's math simple: a bone's skinning
## transform is just its global pose minus its rest position.
extends RefCounted

const Geo = preload("res://core/geo.gd")
const Spine = preload("res://core/spine.gd")
const Recipe = preload("res://core/recipe.gd")
const Catalog = preload("res://library/catalog.gd")

const BODY_SEGS := 10
const LIMB_SEGS := 6
static var MIRROR := Transform3D(Basis.from_scale(Vector3(-1, 1, 1)), Vector3.ZERO)

const FIXED_COLORS := {
	"white": Color("#f3efe6"), "black": Color("#141414"), "dark": Color("#2c2220"),
	"horn": Color("#dccb9f"), "claw": Color("#2e2724"), "teeth": Color("#f1e9cf"), "eye": Color("#e6c13a"),
}

# Build state
var catalog
var recipe: Dictionary
var warnings: Array = []
var spine
var geo
var bone_names: PackedStringArray = []
var bone_parent: PackedInt32Array = []
var bone_rest: Array[Vector3] = []
var spine_bones: PackedInt32Array = []
var limbs: Array = []        # resolved limb dictionaries (including mirrors)
var parts_rig: Array = []
var owners: Array = []       # triangle owner descriptors
var tri_owner := PackedInt32Array()
var shift := Vector3.ZERO


static func build(src: Dictionary) -> Node3D:
	var b = load("res://core/builder.gd").new()
	return b._build(src)


func _build(src: Dictionary) -> Node3D:
	catalog = Catalog.shared()
	var norm: Dictionary = Recipe.normalize(src, catalog)
	recipe = norm["recipe"]
	warnings = norm["warnings"]
	geo = Geo.new()

	var spine0 = Spine.new(recipe["spine"])
	_resolve_limbs(spine0)
	var ground := _ground_level(spine0)
	shift = Vector3(0, -ground, 0)
	for l in limbs:
		for k in l["joints"].size():
			l["joints"][k] += shift
		l["sole"] += shift
	spine = Spine.new(recipe["spine"], shift)
	_validate_clearance()

	_make_spine_bones()
	_make_limb_bones()
	_body_geometry()
	_limb_geometry()
	_parts()
	return _assemble()


# ------------------------------------------------------------------ limbs

func _resolve_limbs(sp) -> void:
	limbs.clear()
	for l in recipe["limbs"]:
		var surf: Dictionary = sp.surface(l["u"], l["theta"])
		var radii: Array = l["radii"]
		var hip: Vector3 = surf["p"] - surf["n"] * radii[0] * 0.5
		var joints: Array[Vector3] = [hip]
		for s in l["segments"]:
			joints.append(joints[joints.size() - 1] + Vector3(s[0], s[1], s[2]))
		var def = catalog.get_part(l["tip"]) if l["tip"] != "" else null
		var role := "appendage"
		var sole_local := Vector3(0, -radii[radii.size() - 1], 0)
		if def != null:
			if def.cap == "foot":
				role = "leg"
				sole_local = def.sole(l["tip_params"])
			elif def.cap in ["hand", "grasp"]:
				role = "arm"
		var length := 0.0
		for k in range(1, joints.size()):
			length += joints[k].distance_to(joints[k - 1])
		var base := {
			"uid": l["uid"], "name": l["uid"], "u": l["u"], "v": surf["v"], "joints": joints, "radii": radii,
			"tip": l["tip"], "tip_params": l["tip_params"], "role": role, "has_foot": role == "leg",
			"sole_local": sole_local, "sole": joints[joints.size() - 1] + sole_local, "length": length,
			"mirrored": false, "side": signf(hip.x) if absf(hip.x) > 0.02 else 0.0,
		}
		limbs.append(base)
		if l["mirror"]:
			if absf(hip.x) < 0.02:
				warnings.append("limb %s is on the midline; mirror ignored" % l["uid"])
				continue
			var m := base.duplicate(true)
			var mj: Array[Vector3] = []
			for j in joints:
				mj.append(Vector3(-j.x, j.y, j.z))
			m["joints"] = mj
			m["name"] = l["uid"] + "_m"
			m["mirrored"] = true
			m["side"] = -base["side"]
			m["sole_local"] = Vector3(-sole_local.x, sole_local.y, sole_local.z)
			m["sole"] = mj[mj.size() - 1] + m["sole_local"]
			limbs.append(m)


## Lowest support point. Feet win; otherwise any non-arm limb or the belly.
func _ground_level(sp) -> float:
	var body_bottom: float = sp.bottom_y()
	var lowest := body_bottom
	var foot_low := INF
	for l in limbs:
		if l["role"] == "arm":
			continue
		lowest = minf(lowest, l["sole"].y)
		if l["has_foot"]:
			foot_low = minf(foot_low, l["sole"].y)
	var ground := foot_low if foot_low < INF else lowest
	ground = minf(ground, lowest) if foot_low == INF else ground
	# Decide which limbs touch the ground.
	for l in limbs:
		if l["role"] == "arm":
			continue
		var gap: float = l["sole"].y - ground
		if l["has_foot"]:
			# A foot limb is a leg when the ground is within its reach (IK extends it).
			var hip: Vector3 = l["joints"][0]
			var drop: float = hip.y - (ground - l["sole_local"].y)
			var end_rest: Vector3 = l["joints"][l["joints"].size() - 1]
			var horiz := Vector2(end_rest.x - hip.x, end_rest.z - hip.z).length()
			if gap <= maxf(0.06, 0.12 * l["length"]) or drop <= 0.0 or sqrt(drop * drop + horiz * horiz) <= l["length"]:
				l["role"] = "leg"
			else:
				warnings.append("limb %s has a foot but cannot reach the ground (short by %.2f)" % [l["name"], sqrt(drop * drop + horiz * horiz) - l["length"]])
				l["role"] = "appendage"
		elif gap <= maxf(0.06, 0.12 * l["length"]):
			l["role"] = "leg"
		else:
			l["role"] = "appendage"
	return ground


func _validate_clearance() -> void:
	var legs := 0
	for l in limbs:
		if l["role"] == "leg":
			legs += 1
	if legs > 0 and spine.bottom_y() < -0.02:
		warnings.append("body dips %.2f below the ground; lengthen the legs or raise the spine" % -spine.bottom_y())


# ------------------------------------------------------------------ bones

func _add_bone(bname: String, parent: int, pos: Vector3) -> int:
	var nm := bname
	var k := 2
	while bone_names.has(nm):
		nm = "%s_%d" % [bname, k]
		k += 1
	bone_names.append(nm)
	bone_parent.append(parent)
	bone_rest.append(pos)
	return bone_names.size() - 1


func _hub_index() -> int:
	var n: int = spine.vpos.size()
	var us := []
	for l in limbs:
		if l["role"] == "leg":
			us.append(l["v"])
	if us.is_empty():
		return n / 2
	var m := 0.0
	for v in us:
		m += v
	return clampi(int(round(m / us.size())), 0, n - 1)


var hub := 0

func _make_spine_bones() -> void:
	var n: int = spine.vpos.size()
	_add_bone("root", -1, Vector3.ZERO)
	spine_bones.resize(n)
	hub = _hub_index()
	spine_bones[hub] = _add_bone("spine_%d" % hub, 0, spine.vpos[hub])
	for i in range(hub + 1, n):
		spine_bones[i] = _add_bone("spine_%d" % i, spine_bones[i - 1], spine.vpos[i])
	for i in range(hub - 1, -1, -1):
		spine_bones[i] = _add_bone("spine_%d" % i, spine_bones[i + 1], spine.vpos[i])


func _spine_bone_at(v: float) -> int:
	return spine_bones[clampi(int(round(v)), 0, spine_bones.size() - 1)]


func _make_limb_bones() -> void:
	for l in limbs:
		var bones := PackedInt32Array()
		var parent := _spine_bone_at(l["v"])
		l["parent_bone"] = parent
		for k in l["joints"].size():
			var b := _add_bone("%s_%d" % [l["name"], k], parent if k == 0 else bones[k - 1], l["joints"][k])
			bones.append(b)
		l["bones"] = bones


# --------------------------------------------------------------- geometry

func _owner(desc: Dictionary) -> int:
	owners.append(desc)
	return owners.size() - 1


func _tag(start_tri: int, owner: int) -> void:
	for i in geo.tri_count() - start_tri:
		tri_owner.append(owner)


func _body_geometry() -> void:
	var start: int = geo.tri_count()
	var rings: Array = []
	var samples: Array = spine.samples
	for s in samples:
		var up: Vector3 = Spine.up_of(s["t"])
		rings.append(Geo.ring(s["p"], Vector3.RIGHT, up, s["w"], s["h"], BODY_SEGS))
	geo.slot = "skin"
	for k in samples.size() - 1:
		var a: Dictionary = samples[k]
		var b: Dictionary = samples[k + 1]
		var wa := _spine_weights(a["v"])
		var wb := _spine_weights(b["v"])
		var ra: PackedVector3Array = rings[k]
		var rb: PackedVector3Array = rings[k + 1]
		for i in BODY_SEGS:
			var j := (i + 1) % BODY_SEGS
			var theta := rad_to_deg(TAU * (i + 0.5) / BODY_SEGS)
			geo.uv = Vector2((a["u"] + b["u"]) * 0.5, wrapf(theta, -180.0, 180.0))
			if a.get("tip", false):
				geo.tri_w(a["p"], rb[j], rb[i], wa["b"], wb["b"], wb["b"], wa["w"], wb["w"], wb["w"])
			elif b.get("tip", false):
				geo.tri_w(ra[i], ra[j], b["p"], wa["b"], wa["b"], wb["b"], wa["w"], wa["w"], wb["w"])
			else:
				geo.tri_w(ra[i], ra[j], rb[j], wa["b"], wa["b"], wb["b"], wa["w"], wa["w"], wb["w"])
				geo.tri_w(ra[i], rb[j], rb[i], wa["b"], wb["b"], wb["b"], wa["w"], wb["w"], wb["w"])
	_tag(start, _owner({"kind": "body"}))


func _spine_weights(v: float) -> Dictionary:
	var n: int = spine_bones.size()
	var i0 := clampi(int(floor(v)), 0, n - 1)
	var i1 := mini(i0 + 1, n - 1)
	var f := clampf(v - i0, 0.0, 1.0)
	# Smoothstep keeps each vertebra's ring mostly rigid.
	var w := 1.0 - f * f * (3.0 - 2.0 * f)
	return {"b": Vector3i(spine_bones[i0], spine_bones[i1], 0), "w": w}


func _limb_geometry() -> void:
	for l in limbs:
		var start: int = geo.tri_count()
		var joints: Array = l["joints"]
		var radii: Array = l["radii"]
		var bones: PackedInt32Array = l["bones"]
		geo.slot = "skin"
		geo.weight = 1.0
		var total := 0.0
		for k in joints.size() - 1:
			var seg_len: float = joints[k].distance_to(joints[k + 1])
			geo.bone = bones[k]
			geo.bone_b = bones[k]
			geo.uv = Vector2(10.0 + (total + seg_len * 0.5) / maxf(l["length"], 0.01), 0.0)
			geo.tube(PackedVector3Array([joints[k], joints[k + 1]]), PackedFloat32Array([radii[k], radii[k + 1]]), LIMB_SEGS, false, false, Vector3.UP)
			total += seg_len
		for k in joints.size():
			geo.bone = bones[k]
			geo.bone_b = bones[k]
			geo.uv = Vector2(10.0 + float(k) / maxf(joints.size() - 1, 1), 0.0)
			geo.ellipsoid(joints[k], Vector3.ONE * radii[k] * (1.08 if k > 0 else 1.0), Basis(), LIMB_SEGS, 4)
		geo.bone = 0
		geo.bone_b = 0
		var owner := _owner({"kind": "limb", "uid": l["uid"], "mirrored": l["mirrored"]})
		_tag(start, owner)
		# Tip part
		if l["tip"] != "":
			var def = catalog.get_part(l["tip"])
			var start_tip: int = geo.tri_count()
			var pg = def.make(l["tip_params"])
			var end_bone: int = bones[bones.size() - 1]
			var xf := Transform3D(Basis(), Vector3.ZERO)
			var end: Vector3 = joints[joints.size() - 1]
			if def.cap == "foot":
				xf = Transform3D(Basis(), end)
			else:
				var d: Vector3 = (joints[joints.size() - 1] - joints[joints.size() - 2]).normalized()
				xf = Transform3D(_frame(d, Vector3.BACK), end)
			if l["mirrored"]:
				# Feet stay upright; hands are built for the unmirrored side then reflected.
				if def.cap == "foot":
					xf = Transform3D(Basis.from_scale(Vector3(-1, 1, 1)), end)
				else:
					var oj: Array = l["joints"]
					var od: Vector3 = (oj[oj.size() - 1] - oj[oj.size() - 2]).normalized()
					od.x = -od.x
					var ox := Transform3D(_frame(od, Vector3.BACK), Vector3(-end.x, end.y, end.z))
					xf = MIRROR * ox
			var bmap := PackedInt32Array([end_bone])
			var jaws := []
			for bd in def.bones:
				var jb := _add_bone("%s_%s" % [l["name"], bd["name"]], end_bone, xf * bd["pivot"])
				bmap.append(jb)
				jaws.append({"bone": jb, "axis": bd["axis"], "angle": bd["angle"]})
			geo.append(pg, xf, bmap)
			l["jaws"] = jaws
			l["tip_frame"] = xf.basis.orthonormalized()
			_tag(start_tip, owner)
		else:
			l["jaws"] = []


## Orthonormal frame with y along `y_dir` and z as close as possible to `z_hint`.
static func _frame(y_dir: Vector3, z_hint: Vector3) -> Basis:
	var y := y_dir.normalized()
	var z := z_hint - y * z_hint.dot(y)
	if z.length() < 0.2:
		z = Vector3.UP - y * Vector3.UP.dot(y)
		if z.length() < 0.2:
			z = Vector3.RIGHT - y * Vector3.RIGHT.dot(y)
	z = z.normalized()
	var x := y.cross(z).normalized()
	return Basis(x, y, z)


func _limb_surface(l: Dictionary, u: float, theta: float, offset: float) -> Dictionary:
	var joints: Array = l["joints"]
	var radii: Array = l["radii"]
	var target: float = u * l["length"]
	var acc := 0.0
	var k := 0
	var t := 0.0
	for i in joints.size() - 1:
		var sl: float = joints[i].distance_to(joints[i + 1])
		if acc + sl >= target or i == joints.size() - 2:
			k = i
			t = clampf((target - acc) / maxf(sl, 1e-4), 0.0, 1.0)
			break
		acc += sl
	var a: Vector3 = joints[k]
	var b: Vector3 = joints[k + 1]
	var dir := (b - a).normalized()
	var e90 := Vector3.UP - dir * Vector3.UP.dot(dir)
	if e90.length() < 0.2:
		e90 = Vector3.BACK - dir * Vector3.BACK.dot(dir)
	e90 = e90.normalized()
	var e0 := e90.cross(dir).normalized()
	var ang := deg_to_rad(theta)
	var n := (e0 * cos(ang) + e90 * sin(ang)).normalized()
	var r: float = lerpf(radii[k], radii[k + 1], t)
	return {"p": a.lerp(b, t) + n * (r + offset), "n": n, "t": dir, "up": e90, "bone": l["bones"][k]}


func _parts() -> void:
	var limb_by_uid := {}
	for l in limbs:
		if not l["mirrored"]:
			limb_by_uid[l["uid"]] = l
	var limb_mirror := {}
	for l in limbs:
		if l["mirrored"]:
			limb_mirror[l["uid"]] = l
	for p in recipe["parts"]:
		var def = catalog.get_part(p["part"])
		var surf: Dictionary
		var parent_bone: int
		var on_limb: bool = p["on"] != "body"
		if not on_limb:
			var s: Dictionary = spine.surface(p["u"], p["theta"], p["offset"])
			var t: Vector3 = spine.at(p["u"])["t"]
			surf = {"p": s["p"], "n": s["n"], "t": t, "up": Spine.up_of(t)}
			parent_bone = _spine_bone_at(s["v"])
		else:
			var l: Dictionary = limb_by_uid[p["on"]]
			surf = _limb_surface(l, p["u"], p["theta"], p["offset"])
			parent_bone = surf["bone"]
		var frame: Basis
		if def.orient == "face":
			# Faces stay upright in the world; parts on top of the head face along the spine.
			var zh: Vector3 = Vector3.UP - surf["n"] * Vector3.UP.dot(surf["n"])
			frame = _frame(surf["n"], Vector3.UP if zh.length() > 0.25 else surf["t"])
		else:
			frame = _frame(surf["n"], surf["t"])
		var r: Array = p["rot"]
		var local := Basis.from_euler(Vector3(deg_to_rad(r[0]), deg_to_rad(r[1]), deg_to_rad(r[2])), EULER_ORDER_YXZ)
		var xf := Transform3D(frame * local * Basis.from_scale(Vector3.ONE * p["scale"]), surf["p"])
		var pg = def.make(p["params"])
		var copies := [[xf, false, parent_bone]]
		if p["mirror"]:
			if absf(surf["p"].x) < 0.03:
				pass  # on the midline; one copy is enough
			else:
				var mparent := parent_bone
				if on_limb:
					var ml = limb_mirror.get(p["on"], null)
					if ml == null:
						mparent = -1
					else:
						var ms: Dictionary = _limb_surface(ml, p["u"], p["theta"], p["offset"])
						mparent = ms["bone"]
				else:
					mparent = _spine_bone_at(spine.surface(p["u"], 180.0 - p["theta"])["v"])
				if mparent >= 0:
					copies.append([MIRROR * xf, true, mparent])
		for c in copies:
			var cx: Transform3D = c[0]
			var start: int = geo.tri_count()
			var pname: String = p["uid"] + ("_m" if c[1] else "")
			var pb := _add_bone("P_" + pname, c[2], cx.origin)
			var bmap := PackedInt32Array([pb])
			var jaws := []
			for bd in def.bones:
				var jb := _add_bone("P_%s_%s" % [pname, bd["name"]], pb, cx * bd["pivot"])
				bmap.append(jb)
				jaws.append({"bone": jb, "axis": bd["axis"], "angle": bd["angle"]})
			geo.append(pg, cx, bmap)
			_tag(start, _owner({"kind": "part", "uid": p["uid"], "mirrored": c[1]}))
			parts_rig.append({
				"uid": p["uid"], "part": p["part"], "category": def.category, "cap": def.cap, "bone": pb, "parent": c[2],
				"frame": cx.basis.orthonormalized(), "mirrored": c[1], "jaws": jaws, "u": p["u"],
			})


# ------------------------------------------------------------- assembly

static func _hash(i: int) -> float:
	var x := int(i * 374761393 + 668265263) & 0x7fffffff
	x = (x ^ (x >> 13)) * 1274126177 & 0x7fffffff
	return float(x & 0xffff) / 65535.0


static func _hash2(a: int, b: int) -> float:
	return _hash(a * 92821 + b * 68917 + 17)


func _paint_skin(uv: Vector2, pal: Dictionary, paint: Dictionary) -> Color:
	var base: Color = pal["base"]
	var acc: Color = pal["accent"]
	var det: Color = pal["detail"]
	var sc: float = paint["pattern_scale"]
	var pat: String = paint["pattern"]
	if uv.x >= 10.0:
		var t := uv.x - 10.0
		match pat:
			"stripes":
				return acc if fposmod(t * 3.0 * sc, 1.0) < 0.35 else base
			"spots", "patches":
				return acc if _hash(int(t * 6.0 * sc)) > 0.7 else base
			"gradient":
				return base.lerp(acc, clampf(t, 0.0, 1.0))
		return base
	var u := uv.x
	var th := uv.y
	var s := sin(deg_to_rad(th))
	if paint["belly"] and s < -0.5:
		return det
	match pat:
		"stripes":
			if s > -0.3 and fposmod(u * 9.0 * sc, 1.0) < 0.38 and u > 0.08 and u < 0.92:
				return acc
		"spots":
			var cu := int(floor(u * 14.0 * sc))
			var ct := int(floor((th + 180.0) / 36.0))
			if s > -0.4 and _hash2(cu, ct) > 0.72:
				return acc
		"patches":
			var cu2 := int(floor(u * 5.0 * sc))
			var ct2 := int(floor((th + 180.0) / 72.0))
			if _hash2(cu2, ct2) > 0.55:
				return acc
		"gradient":
			return acc.lerp(base, clampf((s + 1.0) * 0.5, 0.0, 1.0))
	return base


func _assemble() -> Node3D:
	var paint: Dictionary = recipe["paint"]
	var pal := FIXED_COLORS.duplicate()
	pal["base"] = Color(paint["base"])
	pal["accent"] = Color(paint["accent"])
	pal["detail"] = Color(paint["detail"])
	var n: int = geo.pos.size()
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	var bones := PackedInt32Array()
	var weights := PackedFloat32Array()
	verts.resize(n); normals.resize(n); colors.resize(n); bones.resize(n * 4); weights.resize(n * 4)
	for t in geo.tri_count():
		var k: int = t * 3
		var a: Vector3 = geo.pos[k]
		var b: Vector3 = geo.pos[k + 1]
		var c: Vector3 = geo.pos[k + 2]
		var nn := (b - a).cross(c - a)
		nn = nn.normalized() if nn.length() > 1e-12 else Vector3.UP
		var slot: String = geo.tri_slot[t]
		var col: Color = _paint_skin(geo.tri_uv[t], pal, paint) if slot == "skin" else pal.get(slot, pal["base"])
		var jit := (_hash(t) - 0.5) * 0.06
		col = Color(clampf(col.r + jit, 0, 1), clampf(col.g + jit, 0, 1), clampf(col.b + jit, 0, 1))
		# Godot treats clockwise triangles as front faces: emit a, c, b.
		var order := [0, 2, 1]
		for o in 3:
			var src: int = k + order[o]
			var dst: int = k + o
			verts[dst] = geo.pos[src]
			normals[dst] = nn
			colors[dst] = col
			var bb0: int = geo.b0[src]
			var bb1: int = geo.b1[src]
			var ww: float = geo.w0[src]
			if bb0 == bb1:
				ww = 1.0
			bones[dst * 4] = bb0
			bones[dst * 4 + 1] = bb1
			weights[dst * 4] = ww
			weights[dst * 4 + 1] = 1.0 - ww
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	arrays[Mesh.ARRAY_BONES] = bones
	arrays[Mesh.ARRAY_WEIGHTS] = weights
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.82
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mesh.surface_set_material(0, mat)

	var skel := Skeleton3D.new()
	skel.name = "Skeleton"
	for i in bone_names.size():
		skel.add_bone(bone_names[i])
	for i in bone_names.size():
		var par := bone_parent[i]
		skel.set_bone_parent(i, par)
		var ppos := bone_rest[par] if par >= 0 else Vector3.ZERO
		skel.set_bone_rest(i, Transform3D(Basis(), bone_rest[i] - ppos))
	skel.reset_bone_poses()
	var mi := MeshInstance3D.new()
	mi.name = "Body"
	mi.mesh = mesh
	skel.add_child(mi)
	mi.skin = skel.create_skin_from_rest_transforms()
	mi.skeleton = NodePath("..")

	var root := Node3D.new()
	root.name = recipe["name"].validate_node_name() if recipe["name"] != "" else "Creature"
	root.add_child(skel)
	skel.owner = root
	mi.owner = root

	var legs := 0
	var arms := 0
	var leg_len := 0.0
	for l in limbs:
		if l["role"] == "leg":
			legs += 1
			leg_len += l["length"]
		elif l["role"] == "arm":
			arms += 1
	leg_len = leg_len / legs if legs > 0 else 0.0
	var box: AABB = geo.aabb()
	var rig := {
		"rest": bone_rest, "parents": bone_parent, "names": bone_names,
		"spine": spine_bones, "hub": hub, "limbs": limbs, "parts": parts_rig,
		"leg_len": leg_len, "body_len": spine.length, "aabb": box,
		"body_h": spine.vh[hub], "hub_height": spine.vpos[hub].y, "shift": shift,
	}
	var report := {
		"name": recipe["name"], "library_version": Catalog.VERSION,
		"warnings": warnings, "triangles": geo.tri_count(), "bones": bone_names.size(),
		"legs": legs, "arms": arms, "parts": parts_rig.size(),
		"height": snappedf(box.end.y, 0.001), "length": snappedf(box.size.z, 0.001), "width": snappedf(box.size.x, 0.001),
		"clearance": snappedf(spine.bottom_y(), 0.001),
	}
	root.set_meta("rig", rig)
	root.set_meta("recipe", recipe)
	root.set_meta("report", report)
	root.set_meta("pick", {"pos": geo.pos, "owner": tri_owner, "owners": owners})
	return root


## Inverse of _limb_surface: nearest (u, theta) on a resolved limb for a point.
static func limb_project(l: Dictionary, point: Vector3) -> Dictionary:
	var joints: Array = l["joints"]
	var best := {"u": 0.5, "theta": 0.0, "d": INF}
	var acc := 0.0
	for k in joints.size() - 1:
		var a: Vector3 = joints[k]
		var b: Vector3 = joints[k + 1]
		var seg := b - a
		var sl := seg.length()
		var t := clampf((point - a).dot(seg) / maxf(sl * sl, 1e-6), 0.0, 1.0)
		var c := a + seg * t
		var d := point.distance_to(c)
		if d < best["d"]:
			var dir := seg / maxf(sl, 1e-6)
			var e90 := Vector3.UP - dir * Vector3.UP.dot(dir)
			if e90.length() < 0.2:
				e90 = Vector3.BACK - dir * Vector3.BACK.dot(dir)
			e90 = e90.normalized()
			var e0 := e90.cross(dir).normalized()
			var rel := point - c
			best = {"u": (acc + t * sl) / maxf(l["length"], 1e-4), "theta": rad_to_deg(atan2(rel.dot(e90), rel.dot(e0))), "d": d}
		acc += sl
	return best
