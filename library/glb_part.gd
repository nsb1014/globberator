## A library part authored in Blender (see blender/build_library.py) and loaded
## from its GLB + JSON sidecar at runtime. Parameters are shape keys:
## "<param>.max" is blended in above the default value, "<param>.min" below it.
extends "res://library/part_base.gd"

# [{name, pivot: Vector3, surfaces: [{slot, verts, idx, shapes: {name: deltas}}]}]
var pieces: Array = []


func load_part(meta: Dictionary, glb_path: String) -> bool:
	id = meta["id"]
	category = meta["category"]
	desc = meta["desc"]
	tags = PackedStringArray(meta["tags"])
	attach = meta["attach"]
	orient = meta["orient"]
	cap = meta["capability"]
	default_mirror = meta["mirror_default"]
	hint = meta["hint"]
	params = {}
	for k in meta["params"].keys():
		params[k] = meta["params"][k]
	bones = []
	for b in meta["bones"]:
		bones.append({"name": b["name"], "pivot": _v(b["pivot"]), "axis": _v(b["axis"]), "angle": float(b["angle"])})
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(glb_path, state) != OK:
		push_error("cannot load part " + glb_path)
		return false
	var by_name := {}
	var meshes: Array = state.get_meshes()
	for node in state.get_nodes():
		var gn := node as GLTFNode
		var nm: String = gn.original_name if gn.original_name != "" else gn.resource_name
		var piece := "self"
		if "__" in nm:
			piece = nm.get_slice("__", 1)
		var surfaces := []
		if gn.mesh >= 0:
			var im: ImporterMesh = (meshes[gn.mesh] as GLTFMesh).mesh
			for s in im.get_surface_count():
				var arr: Array = im.get_surface_arrays(s)
				var verts: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
				var idx: PackedInt32Array = arr[Mesh.ARRAY_INDEX] if arr[Mesh.ARRAY_INDEX] != null else PackedInt32Array(range(verts.size()))
				var mat := im.get_surface_material(s)
				var slot: String = mat.resource_name if mat else "base"
				var shapes := {}
				for b in im.get_blend_shape_count():
					var sa: Array = im.get_surface_blend_shape_arrays(s, b)
					shapes[im.get_blend_shape_name(b)] = _as_delta(verts, sa[Mesh.ARRAY_VERTEX])
				surfaces.append({"slot": slot, "verts": verts, "idx": idx, "shapes": shapes})
		by_name[piece] = {"name": piece, "pivot": gn.position if piece != "self" else Vector3.ZERO, "surfaces": surfaces}
	pieces = []
	for name in meta["pieces"]:
		pieces.append(by_name.get(name, {"name": name, "pivot": Vector3.ZERO, "surfaces": []}))
	return true


static func _v(a) -> Vector3:
	return Vector3(a[0], a[1], a[2])


## Godot may store blend shapes as absolute positions or as offsets; normalize to offsets.
static func _as_delta(base: PackedVector3Array, shape: PackedVector3Array) -> PackedVector3Array:
	var abs_err := 0.0
	var rel_err := 0.0
	for i in base.size():
		abs_err += (shape[i] - base[i]).length()
		rel_err += shape[i].length()
	if rel_err <= abs_err:
		return shape
	var out := PackedVector3Array()
	out.resize(base.size())
	for i in base.size():
		out[i] = shape[i] - base[i]
	return out


func _weights(prm: Dictionary) -> Dictionary:
	var w := {}
	for k in params.keys():
		var r: Array = params[k]
		var v := pv(prm, k)
		var d: float = r[2]
		if v > d + 1e-6 and r[1] > d:
			w[k + ".max"] = (v - d) / (r[1] - d)
		elif v < d - 1e-6 and r[0] < d:
			w[k + ".min"] = (d - v) / (d - r[0])
	return w


func _posed(surf: Dictionary, w: Dictionary) -> PackedVector3Array:
	var verts: PackedVector3Array = surf["verts"].duplicate()
	for key in w.keys():
		if not surf["shapes"].has(key):
			continue
		var d: PackedVector3Array = surf["shapes"][key]
		var f: float = w[key]
		for i in verts.size():
			verts[i] += d[i] * f
	return verts


func build(g, prm: Dictionary) -> void:
	var w := _weights(prm)
	for pi in pieces.size():
		var piece: Dictionary = pieces[pi]
		g.bone = pi
		g.bone_b = pi
		g.weight = 1.0
		var pivot: Vector3 = piece["pivot"]
		for surf in piece["surfaces"]:
			g.slot = surf["slot"]
			var v := _posed(surf, w)
			var idx: PackedInt32Array = surf["idx"]
			for t in range(0, idx.size(), 3):
				# Godot surfaces are clockwise; Geo stores counter-clockwise.
				g.tri(pivot + v[idx[t]], pivot + v[idx[t + 2]], pivot + v[idx[t + 1]])
	g.bone = 0
	g.bone_b = 0


## Ground contact: the lowest point of the posed foot, centered over its lowest vertices.
func sole(prm: Dictionary) -> Vector3:
	var w := _weights(prm)
	var pts := PackedVector3Array()
	for piece in pieces:
		for surf in piece["surfaces"]:
			for p in _posed(surf, w):
				pts.append(p + piece["pivot"])
	if pts.is_empty():
		return Vector3(0, -0.1, 0)
	var lo := INF
	for p in pts:
		lo = minf(lo, p.y)
	var c := Vector3.ZERO
	var n := 0
	for p in pts:
		if p.y < lo + 0.012:
			c += p
			n += 1
	c /= n
	return Vector3(c.x, lo, c.z)
