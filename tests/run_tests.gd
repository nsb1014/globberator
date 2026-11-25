## Automated test suite: `godot --headless --path . -s res://cli/main.gd -- test`
extends RefCounted

const Recipe = preload("res://core/recipe.gd")
const Builder = preload("res://core/builder.gd")
const Catalog = preload("res://library/catalog.gd")
const Ops = preload("res://core/ops.gd")
const Animator = preload("res://core/animator.gd")
const Baker = preload("res://core/baker.gd")

var failures: Array[String] = []
var passed := 0
var tree: SceneTree


func check(cond: bool, what: String) -> void:
	if cond:
		passed += 1
	else:
		failures.append(what)
		printerr("FAIL: ", what)


func examples() -> Array[String]:
	var out: Array[String] = []
	var d := DirAccess.open("res://examples")
	for f in d.get_files():
		if f.ends_with(".json"):
			out.append("res://examples/" + f)
	out.sort()
	return out


func run(t: SceneTree) -> int:
	tree = t
	var t0 := Time.get_ticks_msec()
	test_parts()
	test_roundtrip()
	test_ops()
	test_determinism()
	test_examples()
	test_leg_counts()
	test_gait_drift()
	test_actions()
	test_export()
	print("tests: %d passed, %d failed (%.1fs)" % [passed, failures.size(), (Time.get_ticks_msec() - t0) / 1000.0])
	for f in failures:
		print("  - ", f)
	return 0 if failures.is_empty() else 1


func test_parts() -> void:
	var cat = Catalog.shared()
	check(cat.order.size() >= 40, "library has at least 40 parts (%d)" % cat.order.size())
	for id in cat.order:
		var def = cat.get_part(id)
		for mode in ["min", "default", "max"]:
			var prm := {}
			for k in def.params.keys():
				var r: Array = def.params[k]
				prm[k] = r[0] if mode == "min" else (r[1] if mode == "max" else r[2])
			var g = def.make(prm)
			check(g.tri_count() > 0, "%s builds triangles (%s params)" % [id, mode])
			var finite := true
			for p in g.pos:
				if not p.is_finite():
					finite = false
					break
			check(finite, "%s geometry is finite (%s)" % [id, mode])
			check(g.aabb().size.length() < 9.0, "%s stays a sane size (%s)" % [id, mode])
		# Every part must build into a creature without warnings.
		var c: Node3D = Builder.build(Ops.showcase_recipe(id))
		check(c.get_meta("report")["warnings"].is_empty(), "%s showcase builds cleanly %s" % [id, c.get_meta("report")["warnings"]])
		c.free()


func test_roundtrip() -> void:
	var cat = Catalog.shared()
	for path in examples():
		var r := Recipe.load_file(path)
		var a: Dictionary = Recipe.normalize(r, cat)
		var j1 := Recipe.to_json(a["recipe"])
		var b: Dictionary = Recipe.normalize(JSON.parse_string(j1), cat)
		var j2 := Recipe.to_json(b["recipe"])
		check(j1 == j2, "recipe round-trip is stable: " + path.get_file())
		check(b["warnings"].is_empty(), "normalized recipe re-normalizes without warnings: " + path.get_file())
	# Out-of-range values are clamped and reported.
	var bad := Recipe.default_recipe()
	bad["spine"][0]["w"] = 99.0
	bad["parts"] = [{"part": "horn_spike", "params": {"length": 50.0}}, {"part": "nope"}]
	var n: Dictionary = Recipe.normalize(bad, cat)
	check(n["recipe"]["spine"][0]["w"] <= Recipe.LIMITS["radius"][1], "spine radius clamped")
	check(n["recipe"]["parts"].size() == 1, "unknown part removed")
	check(n["warnings"].size() >= 3, "clamps reported as warnings")


func test_ops() -> void:
	var r := Recipe.default_recipe()
	var ops := [
		{"op": "add_limb", "uid": "leg", "u": 0.4, "theta": -60, "segments": [[0.1, -0.3, 0], [0, -0.3, 0]], "tip": "foot_paw"},
		{"op": "add_part", "part": "eye_round"},
		{"op": "set_part", "uid": "eye1", "params": {"size": 1.5}},
		{"op": "insert_vertebra", "index": -1},
		{"op": "set_vertebra", "index": 0, "w": 0.2},
		{"op": "scale_body", "w": 1.1},
		{"op": "set_paint", "pattern": "spots"},
		{"op": "add_part", "part": "spike", "on": "leg", "u": 0.5, "theta": 0},
		{"op": "set_limb", "uid": "leg", "tip_params": {"size": 1.3}},
	]
	var res: Dictionary = Ops.apply_all(r, ops)
	check(res["errors"].is_empty(), "ops apply without errors %s" % [res["errors"]])
	var out: Dictionary = res["recipe"]
	check(out["spine"].size() == 6, "insert_vertebra appended")
	check(out["parts"][0]["params"]["size"] == 1.5, "set_part merges params")
	check(out["limbs"][0]["tip_params"]["size"] == 1.3, "set_limb merges tip params")
	var res2: Dictionary = Ops.apply_all(out, [{"op": "remove_limb", "uid": "leg"}])
	check(res2["recipe"]["limbs"].is_empty() and res2["recipe"]["parts"].size() == 1, "remove_limb also removes its parts")
	var res3: Dictionary = Ops.apply_all(out, [{"op": "bogus"}, {"op": "remove_part", "uid": "zzz"}])
	check(res3["errors"].size() == 2, "bad ops are reported")
	var c: Node3D = Builder.build(out)
	check(c.get_meta("report")["legs"] == 2, "op-built creature has 2 legs")
	c.free()


func _mesh_hash(c: Node3D) -> int:
	var mi: MeshInstance3D = c.get_node("Skeleton/Body")
	var arr: Array = mi.mesh.surface_get_arrays(0)
	return hash(var_to_bytes(arr[Mesh.ARRAY_VERTEX]) + var_to_bytes(arr[Mesh.ARRAY_COLOR]) + var_to_bytes(arr[Mesh.ARRAY_BONES]))


func test_determinism() -> void:
	var r := Recipe.load_file("res://examples/dragon.json")
	var a: Node3D = Builder.build(r)
	var b: Node3D = Builder.build(r)
	check(_mesh_hash(a) == _mesh_hash(b), "same recipe builds identical mesh")
	a.free()
	b.free()


func test_examples() -> void:
	var expect := {"bull": 4, "minotaur": 2, "beetle": 6, "serpent": 0, "bird": 2, "spider": 8, "crab": 6, "hopper": 1, "dragon": 4}
	for path in examples():
		var c: Node3D = Builder.build(Recipe.load_file(path))
		var rep: Dictionary = c.get_meta("report")
		var key := path.get_file().get_basename()
		check(rep["warnings"].is_empty() or key == "bird", "%s builds without warnings %s" % [key, rep["warnings"]])
		if expect.has(key):
			check(rep["legs"] == expect[key], "%s has %d legs (got %d)" % [key, expect[key], rep["legs"]])
		check(rep["triangles"] < 20000, "%s triangle budget" % key)
		c.free()


## Synthetic creatures with 0..8 legs built purely through ops.
static func leg_recipe(n: int) -> Dictionary:
	var r := Recipe.default_recipe()
	r["name"] = "legs%d" % n
	r["spine"] = []
	for i in 6:
		var z := lerpf(-0.9, 0.9, i / 5.0)
		var rad := 0.3 if i in [0, 5] else 0.4
		r["spine"].append({"y": 0.75, "z": z, "w": rad, "h": rad})
	var ops := []
	var pairs := n / 2
	var odd := n % 2 == 1
	for i in pairs:
		var u := 0.3 + 0.4 * (float(i) / maxf(pairs - 1, 1)) if pairs > 1 else 0.45
		ops.append({"op": "add_limb", "uid": "p%d" % i, "u": u, "theta": -50, "segments": [[0.15, -0.3, 0.0], [0.03, -0.32, 0.04]], "radii": [0.1, 0.07, 0.05], "tip": "foot_paw", "tip_params": {"size": 0.8}, "mirror": true})
	if odd:
		ops.append({"op": "add_limb", "uid": "c", "u": 0.5 if pairs > 0 else 0.45, "theta": -90, "segments": [[0.0, -0.26, -0.06], [0.0, -0.27, 0.06]], "radii": [0.12, 0.08, 0.06], "tip": "foot_pad", "mirror": false})
	ops.append({"op": "add_part", "part": "eye_round"})
	return Ops.apply_all(r, ops)["recipe"]


func _all_finite(an) -> bool:
	for t in an.G:
		if not (t.origin.is_finite() and t.basis.x.is_finite() and t.basis.y.is_finite() and t.basis.z.is_finite()):
			return false
	return true


func test_leg_counts() -> void:
	for n in 9:
		var c: Node3D = Builder.build(leg_recipe(n))
		tree.root.add_child(c)
		var rep: Dictionary = c.get_meta("report")
		check(rep["legs"] == n, "synthetic creature has %d legs (got %d)" % [n, rep["legs"]])
		var an = Animator.new(c)
		an.play("walk")
		var start: Vector3 = an.world.origin
		var ok := true
		for f in 90:
			an.step(1.0 / 30.0)
			if not _all_finite(an):
				ok = false
				break
		check(ok, "%d-leg walk stays finite" % n)
		check(an.world.origin.distance_to(start) > 0.1, "%d-leg creature travels" % n)
		c.free()


## Planted feet must not slide: measure posed sole vs. planted footprint.
func drift_for(r: Dictionary, clip: String, turn := 0.0) -> Dictionary:
	var c: Node3D = Builder.build(r)
	tree.root.add_child(c)
	var an = Animator.new(c)
	an.play(clip)
	if turn != 0.0:
		an.drive(1.0, turn, clip == "run")
		an.speed = an.target_speed
	var worst := 0.0
	var frames := 0
	for f in 150:
		an.step(1.0 / 60.0)
		if f < 30:
			continue
		for st in an.legs:
			if st["swinging"]:
				continue
			var d: float = an.posed_sole(st).distance_to(st["plant"])
			worst = maxf(worst, d / maxf(st["length"], 0.01))
			frames += 1
	c.free()
	return {"worst": worst, "samples": frames}


func test_gait_drift() -> void:
	for path in examples():
		var r := Recipe.load_file(path)
		var key := path.get_file().get_basename()
		if key in ["serpent"]:
			continue
		for clip in ["walk", "run"]:
			var d := drift_for(r, clip)
			check(d["worst"] < 0.05, "%s %s planted-foot drift %.3f of leg length < 0.05" % [key, clip, d["worst"]])
		var dt := drift_for(r, "walk", 0.6)
		check(dt["worst"] < 0.05, "%s turning walk drift %.3f < 0.05" % [key, dt["worst"]])


func test_actions() -> void:
	for path in examples():
		var c: Node3D = Builder.build(Recipe.load_file(path))
		tree.root.add_child(c)
		var an = Animator.new(c)
		var ok := true
		for a in ["roar", "wave", "hop"]:
			an.play(a)
			for f in 60:
				an.step(1.0 / 30.0)
			ok = ok and _all_finite(an)
		check(ok, "%s plays all actions" % path.get_file())
		c.free()


func test_export() -> void:
	var c: Node3D = Builder.build(Recipe.load_file("res://examples/minotaur.json"))
	tree.root.add_child(c)
	var clips: Dictionary = Baker.bake_all(c)
	check(clips.size() == 6, "six clips baked")
	var path := OS.get_cache_dir().path_join("polyforge_test.glb")
	check(Baker.export_glb(c, path) == OK, "GLB export succeeds")
	var bones := (c.get_node("Skeleton") as Skeleton3D).get_bone_count()
	c.free()
	var doc := GLTFDocument.new()
	var st := GLTFState.new()
	check(doc.append_from_file(path, st) == OK, "GLB re-imports")
	var scene := doc.generate_scene(st)
	var skel: Skeleton3D = scene.find_children("*", "Skeleton3D", true, false)[0] if scene.find_children("*", "Skeleton3D", true, false).size() > 0 else null
	check(skel != null and skel.get_bone_count() == bones, "re-imported skeleton keeps %d bones" % bones)
	var aps := scene.find_children("*", "AnimationPlayer", true, false)
	check(aps.size() == 1 and (aps[0] as AnimationPlayer).get_animation_list().size() == 6, "re-imported GLB has 6 animations")
	if aps.size() == 1:
		var walk: Animation = (aps[0] as AnimationPlayer).get_animation("walk")
		check(walk != null and walk.length > 0.2, "walk clip has a cycle length")
	scene.free()
