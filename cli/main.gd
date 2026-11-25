## Headless command line: the AI's hands.
##
##   godot --path . -s res://cli/main.gd -- <command> [args]
##
## Commands
##   describe [--out catalog.json]             part catalog + recipe limits as JSON
##   normalize <recipe> [--out r.json]         clamp into style ranges; prints warnings
##   apply <recipe> <ops.json> --out r.json    apply editor operations
##   build <recipe> --out dir                  GLB with baked clips + report.json
##   render <recipe> --out dir [--views a,b] [--size 512] [--mask] [--pose clip@t]
##   animate <recipe> --clip walk --out f.mp4 [--seconds 4] [--view threequarter] [--size 480]
##   turntable <recipe> --out f.mp4 [--seconds 6]
##   gallery <recipe...> --out sheet.png [--view threequarter] [--size 320] [--pose clip@t]
##   renderjobs <jobs.json> [--size 256]       many renders in one process:
##       [{"recipe": path, "out": dir, "views": ["front", "30,10"], "mask": true}]
##   thumbs [--out library/thumbs]             one preview image per part
##   test                                      run the automated test suite
## Rendering commands need a display (use xvfb-run) and --rendering-driver opengl3.
extends SceneTree

const Recipe = preload("res://core/recipe.gd")
const Builder = preload("res://core/builder.gd")
const Catalog = preload("res://library/catalog.gd")
const Studio = preload("res://core/studio.gd")
const Ops = preload("res://core/ops.gd")
const Animator = preload("res://core/animator.gd")
const Baker = preload("res://core/baker.gd")

var args: PackedStringArray
var opts := {}
var pos: Array[String] = []


func _init() -> void:
	args = OS.get_cmdline_user_args()
	var i := 0
	while i < args.size():
		var a := args[i]
		if a.begins_with("--"):
			var key := a.substr(2)
			if i + 1 < args.size() and not args[i + 1].begins_with("--"):
				opts[key] = args[i + 1]
				i += 1
			else:
				opts[key] = "true"
		else:
			pos.append(a)
		i += 1
	_run.call_deferred()


func _run() -> void:
	var code := 0
	if pos.is_empty():
		print("usage: godot --path . -s res://cli/main.gd -- <describe|normalize|apply|build|render|animate|turntable|thumbs|test> ...")
		quit(2)
		return
	var cmd: String = pos[0]
	match cmd:
		"describe": code = _describe()
		"normalize": code = _normalize()
		"apply": code = _apply()
		"build": code = await _build()
		"render": code = await _render()
		"animate": code = await _animate()
		"turntable": code = await _turntable()
		"thumbs": code = await _thumbs()
		"gallery": code = await _gallery()
		"renderjobs": code = await _renderjobs()
		"test":
			var T = load("res://tests/run_tests.gd")
			code = await T.new().run(self)
		_:
			printerr("unknown command ", cmd)
			code = 2
	quit(code)


func _abs(path: String) -> String:
	if path.begins_with("res://") or path.begins_with("user://") or path.is_absolute_path():
		return path
	return OS.get_environment("PWD").path_join(path) if OS.get_environment("PWD") != "" else path


func _out_dir(key := "out") -> String:
	var d := _abs(opts.get(key, "out"))
	DirAccess.make_dir_recursive_absolute(d)
	return d


func _load_recipe(idx := 1) -> Dictionary:
	if pos.size() <= idx:
		printerr("missing recipe path")
		return {}
	return Recipe.load_file(_abs(pos[idx]))


func _write(path: String, text: String) -> void:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(text)


func _describe() -> int:
	var d: Dictionary = Catalog.shared().describe()
	d["recipe_limits"] = Recipe.LIMITS
	d["patterns"] = Recipe.PATTERNS
	d["ops"] = Ops.describe()
	var text := JSON.stringify(d, "  ", true)
	if opts.has("out"):
		_write(_abs(opts["out"]), text)
	else:
		print(text)
	return 0


func _normalize() -> int:
	var r := _load_recipe()
	if r.is_empty():
		return 1
	var n: Dictionary = Recipe.normalize(r, Catalog.shared())
	for w in n["warnings"]:
		printerr("warning: ", w)
	if opts.has("out"):
		Recipe.save_file(n["recipe"], _abs(opts["out"]))
	else:
		print(Recipe.to_json(n["recipe"]))
	return 0


func _apply() -> int:
	var r := _load_recipe()
	if r.is_empty() or pos.size() < 3:
		printerr("usage: apply <recipe> <ops.json> --out r.json")
		return 1
	var ops_text := FileAccess.get_file_as_string(_abs(pos[2]))
	var ops = JSON.parse_string(ops_text)
	if typeof(ops) != TYPE_ARRAY:
		printerr("ops file must be a JSON array")
		return 1
	var res: Dictionary = Ops.apply_all(r, ops)
	for e in res["errors"]:
		printerr("op error: ", e)
	var n: Dictionary = Recipe.normalize(res["recipe"], Catalog.shared())
	for w in n["warnings"]:
		printerr("warning: ", w)
	Recipe.save_file(n["recipe"], _abs(opts.get("out", "out/recipe.json")))
	return 0 if res["errors"].is_empty() else 3


func _build() -> int:
	var r := _load_recipe()
	if r.is_empty():
		return 1
	var dir := _out_dir()
	var creature: Node3D = Builder.build(r)
	root.add_child(creature)
	var report: Dictionary = creature.get_meta("report")
	var name: String = str(opts.get("name", report["name"])).to_snake_case().validate_filename()
	if name == "":
		name = "creature"
	var clips: Dictionary = Baker.bake_all(creature)
	report["clips"] = clips.keys()
	var glb := dir.path_join(name + ".glb")
	var err: int = Baker.export_glb(creature, glb)
	report["glb"] = glb
	report["export_error"] = err
	Recipe.save_file(creature.get_meta("recipe"), dir.path_join(name + ".recipe.json"))
	_write(dir.path_join(name + ".report.json"), JSON.stringify(report, "  ", true))
	print(JSON.stringify({"glb": glb, "warnings": report["warnings"], "clips": report["clips"]}))
	return 0 if err == OK else 4


func _studio(size: int) -> Object:
	return Studio.new(root, Vector2i(size, size))


func _render() -> int:
	var r := _load_recipe()
	if r.is_empty():
		return 1
	var dir := _out_dir()
	var size := int(opts.get("size", "512"))
	var st = _studio(size)
	var creature: Node3D = Builder.build(r)
	st.stage.add_child(creature)
	var box: AABB = creature.get_meta("rig")["aabb"]
	_apply_pose(creature)
	if opts.get("focus", "") == "head":
		box = _head_box(creature)
	var views: PackedStringArray = str(opts.get("views", "front,side,threequarter")).split(";" if ";" in str(opts.get("views", "")) else ",")
	if opts.has("cam"):
		views = PackedStringArray([opts["cam"]])
	var mask: bool = opts.has("mask")
	var outputs := []
	for v in views:
		var ang: Vector2 = Studio.view_angles(v)
		st.frame(box, ang.x, ang.y)
		st.set_mask_mode(false)
		var img: Image = await st.snap(self)
		var fname := v.replace(",", "_")
		var p := dir.path_join(fname + ".png")
		img.save_png(p)
		outputs.append(p)
		if mask:
			st.set_mask_mode(true)
			var mimg: Image = await st.snap(self)
			var mp := dir.path_join(fname + "_mask.png")
			_alpha_to_mask(mimg).save_png(mp)
			outputs.append(mp)
	print(JSON.stringify({"images": outputs, "warnings": creature.get_meta("report")["warnings"]}))
	return 0


static func _alpha_to_mask(img: Image) -> Image:
	var out := Image.create(img.get_width(), img.get_height(), false, Image.FORMAT_L8)
	for y in img.get_height():
		for x in img.get_width():
			var a := img.get_pixel(x, y).a
			out.set_pixel(x, y, Color(a, a, a) if a > 0.5 else Color.BLACK)
	return out


func _frames_to_video(frames_dir: String, out: String, fps: int) -> int:
	DirAccess.make_dir_recursive_absolute(out.get_base_dir())
	var res := []
	var code := OS.execute("ffmpeg", ["-y", "-loglevel", "error", "-framerate", str(fps), "-i", frames_dir.path_join("f%04d.png"),
		"-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "20", out], res, true)
	if code != 0:
		printerr("ffmpeg failed: ", res)
	return code


func _tmp_frames() -> String:
	var d := OS.get_cache_dir().path_join("polyforge_frames_%d" % Time.get_ticks_usec())
	DirAccess.make_dir_recursive_absolute(d)
	return d


func _animate() -> int:
	var r := _load_recipe()
	if r.is_empty():
		return 1
	var size := int(opts.get("size", "480"))
	var st = _studio(size)
	var creature: Node3D = Builder.build(r)
	st.stage.add_child(creature)
	var an = Animator.new(creature)
	var clip: String = opts.get("clip", "walk")
	var seconds := float(opts.get("seconds", "4"))
	var fps := 30
	var follow: bool = clip in ["walk", "run"] and not opts.has("inplace")
	an.play(clip)
	var box: AABB = creature.get_meta("rig")["aabb"]
	var ang: Vector2 = Studio.view_angles(opts.get("view", "threequarter"))
	var frames := _tmp_frames()
	var n := int(seconds * fps)
	for f in n:
		an.step(1.0 / fps)
		creature.transform = an.world if follow else Transform3D.IDENTITY
		var b2 := box
		b2.position += creature.position
		st.frame(b2.grow(0.3 if follow else 0.0), ang.x, ang.y)
		st.ground.position = Vector3.ZERO
		var img: Image = await st.snap(self, 1)
		img.save_png(frames.path_join("f%04d.png" % f))
	var out := _abs(opts.get("out", "out/%s.mp4" % clip))
	var code := _frames_to_video(frames, out, fps)
	print(JSON.stringify({"video": out, "frames": n}))
	return code


func _turntable() -> int:
	var r := _load_recipe()
	if r.is_empty():
		return 1
	var size := int(opts.get("size", "480"))
	var st = _studio(size)
	var creature: Node3D = Builder.build(r)
	st.stage.add_child(creature)
	var an = Animator.new(creature)
	an.play("idle")
	var box: AABB = creature.get_meta("rig")["aabb"]
	var seconds := float(opts.get("seconds", "6"))
	var fps := 30
	var frames := _tmp_frames()
	var n := int(seconds * fps)
	for f in n:
		an.step(1.0 / fps)
		st.frame(box, 360.0 * f / n, 14.0)
		var img: Image = await st.snap(self, 1)
		img.save_png(frames.path_join("f%04d.png" % f))
	var out := _abs(opts.get("out", "out/turntable.mp4"))
	var code := _frames_to_video(frames, out, fps)
	print(JSON.stringify({"video": out}))
	return code


## Render each part on a small neutral body so the AI (and the editor
## palette) can see what it looks like.
func _thumbs() -> int:
	var dir := _abs(opts.get("out", "res://library/thumbs"))
	if dir.begins_with("res://"):
		dir = ProjectSettings.globalize_path(dir)
	DirAccess.make_dir_recursive_absolute(dir)
	var st = _studio(int(opts.get("size", "160")))
	var cat = Catalog.shared()
	var only: String = opts.get("part", "")
	for id in cat.order:
		if only != "" and id != only:
			continue
		var r := Ops.showcase_recipe(id)
		var creature: Node3D = Builder.build(r)
		st.stage.add_child(creature)
		var box: AABB = _non_body_box(creature)
		var def = cat.get_part(id)
		var yaw := 35.0 if def.category in ["eye", "mouth", "nose"] else 60.0
		if def.category == "tail":
			yaw = 150.0
		st.frame(box, yaw, 18.0, 1.25)
		var img: Image = await st.snap(self)
		img.save_png(dir.path_join(id + ".png"))
		creature.free()
	print(JSON.stringify({"thumbs": dir}))
	return 0


## Contact sheet of several recipes (one row per view list entry).
func _gallery() -> int:
	var size := int(opts.get("size", "320"))
	var st = _studio(size)
	var views: PackedStringArray = str(opts.get("view", "threequarter")).split(";")
	var tiles: Array[Image] = []
	for i in range(1, pos.size()):
		var r: Dictionary = Recipe.load_file(_abs(pos[i]))
		var creature: Node3D = Builder.build(r)
		st.stage.add_child(creature)
		_apply_pose(creature)
		var box: AABB = creature.get_meta("rig")["aabb"]
		for v in views:
			var ang: Vector2 = Studio.view_angles(v)
			st.frame(box, ang.x, ang.y)
			tiles.append(await st.snap(self))
		for w in creature.get_meta("report")["warnings"]:
			printerr(pos[i].get_file(), ": ", w)
		creature.free()
	var cols := int(opts.get("cols", str(mini(tiles.size(), 4) if views.size() == 1 else views.size())))
	var rows := int(ceil(float(tiles.size()) / cols))
	var sheet := Image.create(cols * size, rows * size, false, Image.FORMAT_RGB8)
	for i in tiles.size():
		var t := tiles[i]
		t.convert(Image.FORMAT_RGB8)
		sheet.blit_rect(t, Rect2i(0, 0, size, size), Vector2i((i % cols) * size, (i / cols) * size))
	var out := _abs(opts.get("out", "out/gallery.png"))
	DirAccess.make_dir_recursive_absolute(out.get_base_dir())
	sheet.save_png(out)
	print(JSON.stringify({"sheet": out, "tiles": tiles.size()}))
	return 0


## Renders show the grounded neutral pose (feet planted by IK) unless --rest
## or --pose clip@seconds is given.
func _apply_pose(creature: Node3D) -> void:
	if opts.has("rest"):
		return
	var an = Animator.new(creature)
	if opts.has("pose"):
		var bits: PackedStringArray = str(opts["pose"]).split("@")
		an.play(bits[0])
		an.advance_to(float(bits[1]) if bits.size() > 1 else 0.5)
		creature.transform = Transform3D.IDENTITY
	else:
		an.play("idle")
		an.otime = 0.0
		an._pose()


## Bounds of everything except the body (the showcased part and its limb).
static func _non_body_box(creature: Node3D) -> AABB:
	var pick: Dictionary = creature.get_meta("pick")
	var box := AABB()
	var first := true
	for t in pick["owner"].size():
		if pick["owners"][pick["owner"][t]]["kind"] == "body":
			continue
		for k in 3:
			var p: Vector3 = pick["pos"][t * 3 + k]
			if first:
				box = AABB(p, Vector3.ZERO)
				first = false
			else:
				box = box.expand(p)
	if first:
		return creature.get_meta("rig")["aabb"]
	return box.grow(maxf(box.size.length() * 0.15, 0.08))


## Batch renders for the AI fitter (one Godot start for many candidates).
func _renderjobs() -> int:
	var jobs = JSON.parse_string(FileAccess.get_file_as_string(_abs(pos[1])))
	if typeof(jobs) != TYPE_ARRAY:
		printerr("jobs file must be a JSON array")
		return 1
	var st = _studio(int(opts.get("size", "256")))
	var results := []
	for job in jobs:
		var r: Dictionary = Recipe.load_file(_abs(job["recipe"]))
		var creature: Node3D = Builder.build(r)
		st.stage.add_child(creature)
		_apply_pose(creature)
		var box: AABB = creature.get_meta("rig")["aabb"]
		var dir := _abs(job["out"])
		DirAccess.make_dir_recursive_absolute(dir)
		var outs := []
		for v in job.get("views", ["threequarter"]):
			var ang: Vector2 = Studio.view_angles(v)
			st.frame(box, ang.x, ang.y)
			var fname: String = str(v).replace(",", "_")
			st.set_mask_mode(false)
			if job.get("color", true):
				var img: Image = await st.snap(self)
				img.save_png(dir.path_join(fname + ".png"))
				outs.append(dir.path_join(fname + ".png"))
			if job.get("mask", false):
				st.set_mask_mode(true)
				var m: Image = await st.snap(self)
				_alpha_to_mask(m).save_png(dir.path_join(fname + "_mask.png"))
				outs.append(dir.path_join(fname + "_mask.png"))
				st.set_mask_mode(false)
		results.append({"recipe": job["recipe"], "images": outs, "report": creature.get_meta("report")})
		creature.free()
	print("RESULT " + JSON.stringify(results))
	return 0


## Bounds of the parts near the front of the body (u > 0.8) for head close-ups.
static func _head_box(creature: Node3D) -> AABB:
	var rig: Dictionary = creature.get_meta("rig")
	var uids := {}
	for p in rig["parts"]:
		if p["u"] > 0.8:
			uids[p["uid"]] = true
	var pick: Dictionary = creature.get_meta("pick")
	var box := AABB()
	var first := true
	for t in pick["owner"].size():
		var o: Dictionary = pick["owners"][pick["owner"][t]]
		if o["kind"] != "part" or not uids.has(o["uid"]):
			continue
		for k in 3:
			var p: Vector3 = pick["pos"][t * 3 + k]
			box = AABB(p, Vector3.ZERO) if first else box.expand(p)
			first = false
	return rig["aabb"] if first else box.grow(box.size.length() * 0.12)
