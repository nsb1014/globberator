## PolyForge creature editor (Spore-style). Everything edits the recipe through
## Ops; the builder regenerates the creature after each change.
##
## Mouse (build mode)
##   left click palette item, then click the creature  place a part / limb / tip
##   left drag a part                                   slide it over the surface
##   left drag a spine or joint handle                  reshape the body / limb
##   wheel over a spine handle                          fatten / slim (shift: height only)
##   right drag orbit · middle drag pan · wheel zoom
## Keys: Delete removes selection · Ctrl+Z / Ctrl+Y undo/redo · Esc cancels placing
## Test drive: W/S forward/back, A/D turn, Shift run, 1/2/3 roar/wave/hop
extends Control

const Recipe = preload("res://core/recipe.gd")
const Builder = preload("res://core/builder.gd")
const Spine = preload("res://core/spine.gd")
const Catalog = preload("res://library/catalog.gd")
const Ops = preload("res://core/ops.gd")
const Animator = preload("res://core/animator.gd")
const Baker = preload("res://core/baker.gd")

const CATEGORY_TITLES := {"eye": "Eyes", "mouth": "Mouths", "nose": "Noses", "horn": "Horns", "ear": "Ears",
	"detail": "Details", "wing": "Wings", "tail": "Tails", "foot": "Feet", "hand": "Hands"}

var catalog
var recipe: Dictionary
var undo_stack: Array[String] = []
var redo_stack: Array[String] = []
var last_snap_key := ""
var last_snap_time := 0

var creature: Node3D
var spine
var rig: Dictionary
var animator
var mode := "build"
var selected := {}
var placing := ""
var drag := {}

# 3D
var viewport: SubViewport
var vp_container: SubViewportContainer
var cam: Camera3D
var cam_yaw := 40.0
var cam_pitch := 18.0
var cam_dist := 6.0
var cam_target := Vector3(0, 0.8, 0)
var handles: Node3D
var handle_list: Array = []   # [{"kind", "index"/"uid", "pos": Vector3}]
var sel_marker: MeshInstance3D

# UI
var inspector: VBoxContainer
var status: Label
var mode_buttons := {}
var examples_menu: OptionButton
var file_dialog: FileDialog
var drive_panel: HBoxContainer


func _ready() -> void:
	catalog = Catalog.shared()
	_build_ui()
	_setup_3d()
	var start := "res://examples/bull.json"
	recipe = Recipe.normalize(Recipe.load_file(start), catalog)["recipe"] if FileAccess.file_exists(start) else Recipe.default_recipe()
	_rebuild()
	_frame_camera()
	_refresh_inspector()


# ===================================================================== UI

func _build_ui() -> void:
	var root := VBoxContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(root)
	var bar := HBoxContainer.new()
	bar.add_theme_constant_override("separation", 6)
	root.add_child(bar)
	for spec in [["New", _on_new], ["Open…", _on_open], ["Save…", _on_save], ["Export GLB…", _on_export], ["Undo", _undo], ["Redo", _redo]]:
		var b := Button.new()
		b.text = spec[0]
		b.pressed.connect(spec[1])
		bar.add_child(b)
	examples_menu = OptionButton.new()
	examples_menu.add_item("Examples…")
	var d := DirAccess.open("res://examples")
	if d:
		var files := Array(d.get_files()).filter(func(f): return f.ends_with(".json"))
		files.sort()
		for f in files:
			examples_menu.add_item(f.get_basename())
	examples_menu.item_selected.connect(_on_example)
	bar.add_child(examples_menu)
	bar.add_child(VSeparator.new())
	for m in ["build", "paint", "drive"]:
		var b := Button.new()
		b.text = {"build": "Build", "paint": "Paint", "drive": "Test drive"}[m]
		b.toggle_mode = true
		b.pressed.connect(_set_mode.bind(m))
		bar.add_child(b)
		mode_buttons[m] = b
	drive_panel = HBoxContainer.new()
	for a in ["roar", "wave", "hop"]:
		var b := Button.new()
		b.text = a.capitalize()
		b.pressed.connect(func(): if animator: animator.play(a))
		drive_panel.add_child(b)
	drive_panel.visible = false
	bar.add_child(drive_panel)

	var split := HSplitContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(split)
	split.add_child(_build_palette())
	var mid := HSplitContainer.new()
	mid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	split.add_child(mid)
	vp_container = SubViewportContainer.new()
	vp_container.stretch = true
	vp_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	vp_container.custom_minimum_size = Vector2(500, 400)
	vp_container.gui_input.connect(_on_viewport_input)
	vp_container.mouse_filter = Control.MOUSE_FILTER_STOP
	mid.add_child(vp_container)
	var right := ScrollContainer.new()
	right.custom_minimum_size = Vector2(310, 0)
	right.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	mid.add_child(right)
	inspector = VBoxContainer.new()
	inspector.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	right.add_child(inspector)
	status = Label.new()
	status.text = "Ready"
	root.add_child(status)
	file_dialog = FileDialog.new()
	file_dialog.access = FileDialog.ACCESS_FILESYSTEM
	file_dialog.size = Vector2i(800, 520)
	add_child(file_dialog)
	_set_mode("build")


func _build_palette() -> Control:
	var tabs := TabContainer.new()
	tabs.custom_minimum_size = Vector2(250, 0)
	# Limbs first.
	var limbs := VBoxContainer.new()
	limbs.name = "Limbs"
	for spec in [["Leg pair", "limb:leg"], ["Arm pair", "limb:arm"], ["Center leg", "limb:center"], ["Feeler / tail limb", "limb:feeler"]]:
		var b := Button.new()
		b.text = spec[0]
		b.pressed.connect(_start_placing.bind(spec[1]))
		limbs.add_child(b)
	var hint := Label.new()
	hint.text = "Pick a limb, then click the body.\nFeet and hands go on a limb's end."
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD
	limbs.add_child(hint)
	var body_box := HBoxContainer.new()
	for spec in [["+ Head", "head"], ["+ Tail", "tail"], ["− Head", "-head"], ["− Tail", "-tail"]]:
		var b := Button.new()
		b.text = spec[0]
		b.pressed.connect(_spine_button.bind(spec[1]))
		body_box.add_child(b)
	limbs.add_child(Label.new())
	var bl := Label.new()
	bl.text = "Spine"
	limbs.add_child(bl)
	limbs.add_child(body_box)
	tabs.add_child(limbs)
	var cats: Dictionary = catalog.by_category()
	var groups := {"Head": ["eye", "mouth", "nose", "ear", "horn"], "Body": ["detail", "wing", "tail"], "Feet & hands": ["foot", "hand"]}
	for g in groups.keys():
		var scroll := ScrollContainer.new()
		scroll.name = g
		var v := VBoxContainer.new()
		v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		scroll.add_child(v)
		for c in groups[g]:
			if not cats.has(c):
				continue
			var lab := Label.new()
			lab.text = CATEGORY_TITLES.get(c, c)
			v.add_child(lab)
			var grid := GridContainer.new()
			grid.columns = 3
			v.add_child(grid)
			for id in cats[c]:
				var def = catalog.get_part(id)
				var b := Button.new()
				b.tooltip_text = "%s\n%s" % [id, def.desc]
				b.custom_minimum_size = Vector2(72, 72)
				var tex := _thumb(id)
				if tex:
					b.icon = tex
					b.expand_icon = true
				else:
					b.text = id.replace("_", "\n")
				b.pressed.connect(_start_placing.bind(id))
				grid.add_child(b)
		tabs.add_child(scroll)
	return tabs


func _thumb(id: String) -> Texture2D:
	var path := "res://library/thumbs/%s.png" % id
	if not FileAccess.file_exists(path):
		return null
	var img := Image.load_from_file(ProjectSettings.globalize_path(path))
	return ImageTexture.create_from_image(img) if img else null


func _setup_3d() -> void:
	viewport = SubViewport.new()
	viewport.own_world_3d = true
	viewport.msaa_3d = Viewport.MSAA_4X
	vp_container.add_child(viewport)
	cam = Camera3D.new()
	cam.fov = 40
	viewport.add_child(cam)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-50, 35, 0)
	key.light_energy = 0.95
	key.shadow_enabled = true
	viewport.add_child(key)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-20, -140, 0)
	fill.light_energy = 0.35
	viewport.add_child(fill)
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.17, 0.19, 0.22)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.62, 0.66, 0.72)
	e.ambient_light_energy = 0.4
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	e.fog_enabled = true
	e.fog_light_color = Color(0.17, 0.19, 0.22)
	e.fog_density = 0.015
	env.environment = e
	viewport.add_child(env)
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(300, 300)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color(0.2, 0.215, 0.23)
	ground.material_override = gm
	viewport.add_child(ground)
	# Grid lines help judge scale while driving.
	var grid := MeshInstance3D.new()
	var im := ImmediateMesh.new()
	im.surface_begin(Mesh.PRIMITIVE_LINES)
	for i in range(-30, 31):
		im.surface_add_vertex(Vector3(i, 0.002, -30)); im.surface_add_vertex(Vector3(i, 0.002, 30))
		im.surface_add_vertex(Vector3(-30, 0.002, i)); im.surface_add_vertex(Vector3(30, 0.002, i))
	im.surface_end()
	grid.mesh = im
	var lm := StandardMaterial3D.new()
	lm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	lm.albedo_color = Color(0.26, 0.28, 0.3)
	grid.material_override = lm
	viewport.add_child(grid)
	handles = Node3D.new()
	viewport.add_child(handles)
	sel_marker = MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.04
	sm.height = 0.08
	sel_marker.mesh = sm
	var smm := StandardMaterial3D.new()
	smm.albedo_color = Color(1.0, 0.8, 0.2)
	smm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	smm.no_depth_test = true
	sel_marker.material_override = smm
	sel_marker.visible = false
	viewport.add_child(sel_marker)


func _update_camera() -> void:
	var y := deg_to_rad(cam_yaw)
	var p := deg_to_rad(cam_pitch)
	cam.position = cam_target + Vector3(sin(y) * cos(p), sin(p), cos(y) * cos(p)) * cam_dist
	cam.look_at(cam_target, Vector3.UP)


func _frame_camera() -> void:
	if creature == null:
		return
	var box: AABB = rig["aabb"]
	cam_target = box.get_center()
	cam_dist = box.size.length() * 1.5 + 0.5
	_update_camera()


# ================================================================ recipe

func _snapshot(key := "") -> void:
	var now := Time.get_ticks_msec()
	if key != "" and key == last_snap_key and now - last_snap_time < 800:
		last_snap_time = now
		return
	last_snap_key = key
	last_snap_time = now
	undo_stack.append(Recipe.to_json(recipe))
	if undo_stack.size() > 200:
		undo_stack.pop_front()
	redo_stack.clear()


func _do(ops: Array, key := "", refresh_inspector := true) -> void:
	_snapshot(key)
	var res: Dictionary = Ops.apply_all(recipe, ops)
	for e in res["errors"]:
		status.text = "Error: " + e
	recipe = Recipe.normalize(res["recipe"], catalog)["recipe"]
	_rebuild()
	if refresh_inspector:
		_refresh_inspector()


func _undo() -> void:
	if undo_stack.is_empty():
		return
	redo_stack.append(Recipe.to_json(recipe))
	recipe = JSON.parse_string(undo_stack.pop_back())
	last_snap_key = ""
	_rebuild()
	_refresh_inspector()


func _redo() -> void:
	if redo_stack.is_empty():
		return
	undo_stack.append(Recipe.to_json(recipe))
	recipe = JSON.parse_string(redo_stack.pop_back())
	last_snap_key = ""
	_rebuild()
	_refresh_inspector()


func _rebuild() -> void:
	if creature:
		creature.free()
	creature = Builder.build(recipe)
	viewport.add_child(creature)
	rig = creature.get_meta("rig")
	spine = Spine.new(recipe["spine"], rig["shift"])
	var rep: Dictionary = creature.get_meta("report")
	var msg := "%s · %d legs · %d arms · %d parts · %d tris" % [recipe["name"], rep["legs"], rep["arms"], rep["parts"], rep["triangles"]]
	if not rep["warnings"].is_empty():
		msg += "   ⚠ " + "; ".join(rep["warnings"])
	status.text = msg
	animator = null
	if mode == "drive":
		animator = Animator.new(creature)
	else:
		# Neutral pose with feet planted.
		var an = Animator.new(creature)
		an.play("idle")
		an.otime = 0.0
		an._pose()
	_update_handles()


# ============================================================== modes

func _set_mode(m: String) -> void:
	mode = m
	if mode_buttons.is_empty():
		return
	for k in mode_buttons.keys():
		mode_buttons[k].button_pressed = k == m
	drive_panel.visible = m == "drive"
	placing = ""
	if creature:
		_rebuild()
		if m != "drive":
			_frame_camera()
	if inspector:
		_refresh_inspector()


func _process(delta: float) -> void:
	if mode == "drive" and animator:
		var fwd := Input.get_axis("ui_down", "ui_up")
		if Input.is_key_pressed(KEY_W):
			fwd = 1.0
		elif Input.is_key_pressed(KEY_S):
			fwd = -0.6
		var turn := 0.0
		if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
			turn = 1.2
		elif Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
			turn = -1.2
		animator.drive(fwd, turn, Input.is_key_pressed(KEY_SHIFT))
		animator.step(delta)
		creature.transform = animator.world
		var box: AABB = rig["aabb"]
		cam_target = cam_target.lerp(animator.world * box.get_center(), clampf(delta * 4.0, 0, 1))
		_update_camera()


# ============================================================ inspector

func _clear_inspector() -> void:
	for c in inspector.get_children():
		c.queue_free()


func _header(text: String) -> void:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", 17)
	inspector.add_child(l)


func _note(text: String) -> void:
	var l := Label.new()
	l.text = text
	l.autowrap_mode = TextServer.AUTOWRAP_WORD
	l.modulate = Color(0.75, 0.78, 0.82)
	inspector.add_child(l)


func _slider(label: String, lo: float, hi: float, value: float, on_change: Callable, step := 0.01) -> void:
	var row := VBoxContainer.new()
	var top := HBoxContainer.new()
	var l := Label.new()
	l.text = label
	l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var vl := Label.new()
	vl.text = "%.2f" % value
	top.add_child(l)
	top.add_child(vl)
	row.add_child(top)
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = value
	s.value_changed.connect(func(v):
		vl.text = "%.2f" % v
		on_change.call(v))
	row.add_child(s)
	inspector.add_child(row)


func _check(label: String, value: bool, on_change: Callable) -> void:
	var c := CheckBox.new()
	c.text = label
	c.button_pressed = value
	c.toggled.connect(on_change)
	inspector.add_child(c)


func _button(label: String, cb: Callable) -> void:
	var b := Button.new()
	b.text = label
	b.pressed.connect(cb)
	inspector.add_child(b)


func _refresh_inspector() -> void:
	_clear_inspector()
	if recipe.is_empty():
		return
	if mode == "paint":
		_paint_inspector()
		return
	if mode == "drive":
		_header("Test drive")
		_note("W/S move · A/D turn · Shift run\n1 Roar · 2 Wave · 3 Hop\nRight-drag to orbit.")
		return
	var name_edit := LineEdit.new()
	name_edit.text = recipe["name"]
	name_edit.text_submitted.connect(func(t): _do([{"op": "set_name", "name": t}]))
	inspector.add_child(name_edit)
	match selected.get("kind", ""):
		"part": _part_inspector()
		"limb": _limb_inspector()
		"vertebra": _vertebra_inspector()
		_:
			_header("Creature")
			_note("Click a part, limb or spine handle to edit it. Pick something from the palette and click the creature to add it.")
			_slider("Body width", 0.5, 1.6, 1.0, func(v): pass)
			inspector.get_child(inspector.get_child_count() - 1).queue_free()
			var rep: Dictionary = creature.get_meta("report") if creature else {}
			if rep:
				_note("Height %.2f · length %.2f · clearance %.2f" % [rep["height"], rep["length"], rep["clearance"]])
	_update_selection_marker()


func _find(list: Array, uid: String) -> Dictionary:
	for x in list:
		if x["uid"] == uid:
			return x
	return {}


func _part_inspector() -> void:
	var p := _find(recipe["parts"], selected["uid"])
	if p.is_empty():
		selected = {}
		return
	var def = catalog.get_part(p["part"])
	var uid: String = p["uid"]
	_header("%s  (%s)" % [p["part"], uid])
	_note(def.desc)
	for k in def.params.keys():
		var r: Array = def.params[k]
		_slider(k.capitalize(), r[0], r[1], p["params"].get(k, r[2]), func(v): _do([{"op": "set_part", "uid": uid, "params": {k: v}}], uid + k, false))
	_slider("Position along body (u)", 0.0, 1.0, p["u"], func(v): _do([{"op": "set_part", "uid": uid, "u": v}], uid + "u", false), 0.005)
	_slider("Angle around (θ)", -180, 180, p["theta"], func(v): _do([{"op": "set_part", "uid": uid, "theta": v}], uid + "t", false), 1.0)
	_slider("Offset", -0.6, 0.6, p["offset"], func(v): _do([{"op": "set_part", "uid": uid, "offset": v}], uid + "o", false))
	_slider("Scale", 0.2, 4.0, p["scale"], func(v): _do([{"op": "set_part", "uid": uid, "scale": v}], uid + "s", false))
	for i in 3:
		var axis: String = ["Tilt (x)", "Turn (y)", "Roll (z)"][i]
		_slider(axis, -180, 180, p["rot"][i], func(v):
			var rot: Array = _find(recipe["parts"], uid)["rot"].duplicate()
			rot[i] = v
			_do([{"op": "set_part", "uid": uid, "rot": rot}], uid + "r%d" % i, false), 1.0)
	_check("Mirror", p["mirror"], func(on): _do([{"op": "set_part", "uid": uid, "mirror": on}]))
	_button("Delete part", func():
		selected = {}
		_do([{"op": "remove_part", "uid": uid}]))


func _limb_inspector() -> void:
	var l := _find(recipe["limbs"], selected["uid"])
	if l.is_empty():
		selected = {}
		return
	var uid: String = l["uid"]
	_header("Limb  (%s)" % uid)
	_note("Drag the yellow joint handles to reshape. Pick a foot or hand in the palette and click this limb to change its tip.")
	for k in l["radii"].size():
		_slider("Thickness %d" % k, 0.02, 1.2, l["radii"][k], func(v):
			var radii: Array = _find(recipe["limbs"], uid)["radii"].duplicate()
			radii[k] = v
			_do([{"op": "set_limb", "uid": uid, "radii": radii}], uid + "r%d" % k, false))
	_slider("Position along body (u)", 0.0, 1.0, l["u"], func(v): _do([{"op": "set_limb", "uid": uid, "u": v}], uid + "u", false), 0.005)
	_slider("Angle around (θ)", -180, 180, l["theta"], func(v): _do([{"op": "set_limb", "uid": uid, "theta": v}], uid + "t", false), 1.0)
	var tip := OptionButton.new()
	tip.add_item("(no tip)")
	var tips := [""]
	for id in catalog.order:
		if catalog.get_part(id).attach == "tip":
			tip.add_item(id)
			tips.append(id)
			if id == l["tip"]:
				tip.select(tips.size() - 1)
	tip.item_selected.connect(func(i): _do([{"op": "set_limb", "uid": uid, "tip": tips[i], "tip_params": {}}]))
	inspector.add_child(tip)
	if l["tip"] != "":
		var def = catalog.get_part(l["tip"])
		for k in def.params.keys():
			var r: Array = def.params[k]
			_slider("Tip " + k, r[0], r[1], l["tip_params"].get(k, r[2]), func(v): _do([{"op": "set_limb", "uid": uid, "tip_params": {k: v}}], uid + "tp" + k, false))
	_check("Mirror", l["mirror"], func(on): _do([{"op": "set_limb", "uid": uid, "mirror": on}]))
	_button("Add joint", func():
		var segs: Array = _find(recipe["limbs"], uid)["segments"].duplicate(true)
		if segs.size() >= 5:
			return
		var last: Array = segs[segs.size() - 1]
		segs[segs.size() - 1] = [last[0] * 0.5, last[1] * 0.5, last[2] * 0.5]
		segs.append([last[0] * 0.5, last[1] * 0.5, last[2] * 0.5])
		var radii: Array = _find(recipe["limbs"], uid)["radii"].duplicate()
		radii.append(radii[radii.size() - 1])
		_do([{"op": "set_limb", "uid": uid, "segments": segs, "radii": radii}]))
	_button("Delete limb", func():
		selected = {}
		_do([{"op": "remove_limb", "uid": uid}]))


func _vertebra_inspector() -> void:
	var i: int = selected["index"]
	if i >= recipe["spine"].size():
		selected = {}
		return
	var v: Dictionary = recipe["spine"][i]
	_header("Vertebra %d" % i)
	_note("Drag the handle in the side plane. Mouse wheel over a handle changes thickness.")
	_slider("Width", 0.04, 2.5, v["w"], func(x): _do([{"op": "set_vertebra", "index": i, "w": x}], "vw%d" % i, false))
	_slider("Height", 0.04, 2.5, v["h"], func(x): _do([{"op": "set_vertebra", "index": i, "h": x}], "vh%d" % i, false))
	_button("Insert vertebra before", func(): _do([{"op": "insert_vertebra", "index": i}]))
	_button("Remove vertebra", func():
		selected = {}
		_do([{"op": "remove_vertebra", "index": i}]))


func _paint_inspector() -> void:
	var pa: Dictionary = recipe["paint"]
	_header("Paint")
	for k in ["base", "accent", "detail"]:
		var row := HBoxContainer.new()
		var l := Label.new()
		l.text = k.capitalize()
		l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(l)
		var cp := ColorPickerButton.new()
		cp.color = Color(pa[k])
		cp.custom_minimum_size = Vector2(90, 28)
		cp.color_changed.connect(func(c): _do([{"op": "set_paint", k: "#" + c.to_html(false)}], "paint" + k, false))
		row.add_child(cp)
		inspector.add_child(row)
	var pat := OptionButton.new()
	for i in Recipe.PATTERNS.size():
		pat.add_item(Recipe.PATTERNS[i])
		if Recipe.PATTERNS[i] == pa["pattern"]:
			pat.select(i)
	pat.item_selected.connect(func(i): _do([{"op": "set_paint", "pattern": Recipe.PATTERNS[i]}]))
	inspector.add_child(pat)
	_slider("Pattern scale", 0.25, 4.0, pa["pattern_scale"], func(v): _do([{"op": "set_paint", "pattern_scale": v}], "pscale", false))
	_check("Light belly", pa["belly"], func(on): _do([{"op": "set_paint", "belly": on}]))


# ============================================================ handles

func _handle_mesh(color: Color, r: float) -> MeshInstance3D:
	var m := MeshInstance3D.new()
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0
	s.radial_segments = 12
	s.rings = 6
	m.mesh = s
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.no_depth_test = true
	m.material_override = mat
	return m


func _update_handles() -> void:
	for c in handles.get_children():
		c.queue_free()
	handle_list.clear()
	if mode != "build" or creature == null:
		return
	for i in spine.vpos.size():
		var p: Vector3 = spine.vpos[i]
		var sel: bool = selected.get("kind", "") == "vertebra" and selected.get("index", -1) == i
		var h := _handle_mesh(Color(0.35, 0.8, 1.0) if not sel else Color(1, 0.8, 0.2), 0.035)
		h.position = p
		handles.add_child(h)
		handle_list.append({"kind": "vertebra", "index": i, "pos": p})
	if selected.get("kind", "") == "limb":
		for l in rig["limbs"]:
			if l["uid"] != selected["uid"] or l["mirrored"]:
				continue
			for k in range(1, l["joints"].size()):
				var p: Vector3 = l["joints"][k]
				var h := _handle_mesh(Color(1, 0.85, 0.25), 0.03)
				h.position = p
				handles.add_child(h)
				handle_list.append({"kind": "joint", "uid": l["uid"], "index": k, "pos": p})


func _update_selection_marker() -> void:
	sel_marker.visible = false
	if selected.get("kind", "") == "part" and creature:
		for pr in rig["parts"]:
			if pr["uid"] == selected["uid"] and not pr["mirrored"]:
				sel_marker.position = rig["rest"][pr["bone"]]
				sel_marker.visible = true


# ============================================================ picking

func _mouse_ray(pos: Vector2) -> Array:
	var scale := Vector2(viewport.size) / vp_container.size
	var p := pos * scale
	return [cam.project_ray_origin(p), cam.project_ray_normal(p)]


## Ray against the creature's rest triangles. Returns {} or {pos, owner}.
func _pick(pos: Vector2, skip_uid := "") -> Dictionary:
	if creature == null:
		return {}
	var ray := _mouse_ray(pos)
	var pick: Dictionary = creature.get_meta("pick")
	var tris: PackedVector3Array = pick["pos"]
	var owners: PackedInt32Array = pick["owner"]
	var best := INF
	var out := {}
	for t in owners.size():
		var o: Dictionary = pick["owners"][owners[t]]
		if skip_uid != "" and o.get("uid", "") == skip_uid:
			continue
		var hit = Geometry3D.ray_intersects_triangle(ray[0], ray[1], tris[t * 3], tris[t * 3 + 1], tris[t * 3 + 2])
		if hit != null:
			var d: float = ray[0].distance_to(hit)
			if d < best:
				best = d
				out = {"pos": hit, "owner": o}
	return out


func _pick_handle(pos: Vector2) -> Dictionary:
	var scale := Vector2(viewport.size) / vp_container.size
	var best := 14.0
	var out := {}
	for h in handle_list:
		if cam.is_position_behind(h["pos"]):
			continue
		var sp := cam.unproject_position(h["pos"]) / scale
		var d := sp.distance_to(pos)
		if d < best:
			best = d
			out = h
	return out


func _attach_from_hit(hit: Dictionary) -> Dictionary:
	var o: Dictionary = hit["owner"]
	if o["kind"] == "limb" or (o["kind"] == "part" and false):
		for l in rig["limbs"]:
			if l["uid"] == o["uid"] and l["mirrored"] == o.get("mirrored", false):
				var pt: Vector3 = hit["pos"]
				if l["mirrored"]:
					# Work on the unmirrored original.
					for l2 in rig["limbs"]:
						if l2["uid"] == l["uid"] and not l2["mirrored"]:
							l = l2
					pt.x = -pt.x
				var lp: Dictionary = Builder.limb_project(l, pt)
				return {"on": o["uid"], "u": lp["u"], "theta": lp["theta"], "pos": hit["pos"]}
	var pr: Dictionary = spine.project(hit["pos"])
	return {"on": "body", "u": pr["u"], "theta": pr["theta"], "pos": hit["pos"]}


# ============================================================ input

func _on_viewport_input(ev: InputEvent) -> void:
	if ev is InputEventMouseButton:
		var mb := ev as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_WHEEL_UP or mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			if mb.pressed:
				var sign := 1.0 if mb.button_index == MOUSE_BUTTON_WHEEL_UP else -1.0
				var h := _pick_handle(mb.position) if mode == "build" else {}
				if h.get("kind", "") == "vertebra":
					var v: Dictionary = recipe["spine"][h["index"]]
					var f := 1.0 + 0.06 * sign
					var op := {"op": "set_vertebra", "index": h["index"], "h": v["h"] * f}
					if not mb.shift_pressed:
						op["w"] = v["w"] * f
					_do([op], "wheel%d" % h["index"])
				else:
					cam_dist = clampf(cam_dist * (0.9 if sign > 0 else 1.1), 0.5, 60.0)
					_update_camera()
			return
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_left_press(mb.position, mb.shift_pressed)
			else:
				if drag.get("kind", "") != "":
					_refresh_inspector()
				drag = {}
		elif mb.button_index in [MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_MIDDLE]:
			drag = {"kind": "orbit" if mb.button_index == MOUSE_BUTTON_RIGHT else "pan"} if mb.pressed else {}
	elif ev is InputEventMouseMotion:
		var mm := ev as InputEventMouseMotion
		match drag.get("kind", ""):
			"orbit":
				cam_yaw -= mm.relative.x * 0.4
				cam_pitch = clampf(cam_pitch + mm.relative.y * 0.3, -10.0, 85.0)
				_update_camera()
			"pan":
				var right := cam.global_transform.basis.x
				var up := cam.global_transform.basis.y
				cam_target += (-right * mm.relative.x + up * mm.relative.y) * cam_dist * 0.0015
				_update_camera()
			"vertebra":
				_drag_vertebra(mm.position)
			"joint":
				_drag_joint(mm.position)
			"part":
				_drag_part(mm.position)
		if placing != "":
			var hit := _pick(mm.position)
			status.text = "Placing %s — click the creature (Esc to cancel)%s" % [placing, "" if hit.is_empty() else "  ·  over " + hit["owner"]["kind"]]


func _left_press(pos: Vector2, shift: bool) -> void:
	if mode != "build":
		return
	if placing != "":
		_place(pos)
		if not shift:
			placing = ""
		return
	var h := _pick_handle(pos)
	if not h.is_empty():
		selected = {"kind": h["kind"], "index": h["index"]} if h["kind"] == "vertebra" else {"kind": "limb", "uid": h["uid"]}
		drag = h.duplicate()
		_snapshot()
		last_snap_key = "drag"
		_refresh_inspector()
		_update_handles()
		return
	var hit := _pick(pos)
	if hit.is_empty():
		selected = {}
	else:
		var o: Dictionary = hit["owner"]
		match o["kind"]:
			"part":
				selected = {"kind": "part", "uid": o["uid"]}
				drag = {"kind": "part", "uid": o["uid"], "mirrored": o.get("mirrored", false)}
				_snapshot()
				last_snap_key = "drag"
			"limb":
				selected = {"kind": "limb", "uid": o["uid"]}
			_:
				selected = {}
	_refresh_inspector()
	_update_handles()


func _place(pos: Vector2) -> void:
	var hit := _pick(pos)
	if hit.is_empty():
		status.text = "Missed the creature."
		return
	var at := _attach_from_hit(hit)
	if placing.begins_with("limb:"):
		var kind := placing.substr(5)
		var side := signf(hit["pos"].x)
		var on_mid := absf(hit["pos"].x) < 0.06
		var sx := side if not on_mid else 0.0
		var u: float = at["u"] if at["on"] == "body" else 0.5
		var theta: float = at["theta"] if at["on"] == "body" else -60.0
		if sx < 0:
			theta = Recipe.wrap_angle(180.0 - theta)
			sx = 1.0
		var op := {"op": "add_limb", "u": u, "theta": theta, "mirror": not on_mid}
		match kind:
			"leg":
				op.merge({"segments": [[0.12 * sx, -0.32, 0.05], [0.0, -0.32, 0.0]], "radii": [0.11, 0.08, 0.06], "tip": "foot_paw"})
			"center":
				op.merge({"theta": -90.0, "mirror": false, "segments": [[0.0, -0.32, 0.05], [0.0, -0.32, 0.0]], "radii": [0.12, 0.09, 0.07], "tip": "foot_pad"})
			"arm":
				op.merge({"segments": [[0.25 * sx, -0.12, 0.05], [0.1 * sx, -0.25, 0.12]], "radii": [0.1, 0.07, 0.05], "tip": "hand_basic"})
			"feeler":
				op.merge({"segments": [[0.15 * sx, 0.2, 0.15], [0.1 * sx, 0.2, 0.2], [0.05 * sx, 0.1, 0.2]], "radii": [0.06, 0.045, 0.03, 0.02], "tip": ""})
		_do([op])
		selected = {"kind": "limb", "uid": recipe["limbs"][recipe["limbs"].size() - 1]["uid"]}
		_refresh_inspector()
		_update_handles()
		return
	var def = catalog.get_part(placing)
	if def.attach == "tip":
		if at["on"] == "body":
			status.text = "Feet and hands go on the end of a limb — click a limb."
			return
		_do([{"op": "set_limb", "uid": at["on"], "tip": placing, "tip_params": {}}])
		selected = {"kind": "limb", "uid": at["on"]}
	else:
		var theta: float = at["theta"]
		var mirror: bool = def.default_mirror
		if at["on"] == "body" and absf(sin(deg_to_rad(theta))) > 0.97:
			mirror = false
		if mirror and hit["pos"].x < 0.0:
			theta = Recipe.wrap_angle(180.0 - theta) if at["on"] == "body" else theta
		_do([{"op": "add_part", "part": placing, "on": at["on"], "u": at["u"], "theta": theta, "mirror": mirror}])
		selected = {"kind": "part", "uid": recipe["parts"][recipe["parts"].size() - 1]["uid"]}
	_refresh_inspector()


func _drag_vertebra(pos: Vector2) -> void:
	var ray := _mouse_ray(pos)
	var plane := Plane(Vector3.RIGHT, 0.0)
	var hit = plane.intersects_ray(ray[0], ray[1])
	if hit == null:
		return
	var p: Vector3 = hit - rig["shift"]
	_do([{"op": "set_vertebra", "index": drag["index"], "y": maxf(p.y, 0.0), "z": p.z}], "drag", false)
	_update_handles()


func _drag_joint(pos: Vector2) -> void:
	var l := _find(recipe["limbs"], drag["uid"])
	var resolved := {}
	for rl in rig["limbs"]:
		if rl["uid"] == drag["uid"] and not rl["mirrored"]:
			resolved = rl
	if l.is_empty() or resolved.is_empty():
		return
	var k: int = drag["index"]
	var joints: Array = resolved["joints"]
	var ray := _mouse_ray(pos)
	var plane := Plane(-cam.global_transform.basis.z, joints[k])
	var hit = plane.intersects_ray(ray[0], ray[1])
	if hit == null:
		return
	var segs: Array = l["segments"].duplicate(true)
	var newp: Vector3 = hit
	var prev: Vector3 = joints[k - 1]
	var d := newp - prev
	segs[k - 1] = [d.x, d.y, d.z]
	if k < joints.size() - 1:
		var nxt: Vector3 = joints[k + 1]
		var d2 := nxt - newp
		segs[k] = [d2.x, d2.y, d2.z]
	_do([{"op": "set_limb", "uid": drag["uid"], "segments": segs}], "drag", false)
	_update_handles()


func _drag_part(pos: Vector2) -> void:
	var hit := _pick(pos, drag["uid"])
	if hit.is_empty():
		return
	var at := _attach_from_hit(hit)
	var p := _find(recipe["parts"], drag["uid"])
	var theta: float = at["theta"]
	if p.get("mirror", false) and at["on"] == "body" and drag.get("mirrored", false):
		theta = Recipe.wrap_angle(180.0 - theta)
	_do([{"op": "set_part", "uid": drag["uid"], "on": at["on"], "u": at["u"], "theta": theta}], "drag", false)
	_update_selection_marker()


func _start_placing(what: String) -> void:
	if mode != "build":
		_set_mode("build")
	placing = what
	status.text = "Placing %s — click the creature (Esc to cancel, Shift-click to keep placing)" % what


func _spine_button(which: String) -> void:
	var n: int = recipe["spine"].size()
	match which:
		"head": _do([{"op": "insert_vertebra", "index": -1}])
		"tail": _do([{"op": "insert_vertebra", "index": 0}])
		"-head": _do([{"op": "remove_vertebra", "index": n - 1}])
		"-tail": _do([{"op": "remove_vertebra", "index": 0}])


func _unhandled_key_input(ev: InputEvent) -> void:
	var k := ev as InputEventKey
	if k == null or not k.pressed or k.echo:
		return
	if k.ctrl_pressed and k.keycode == KEY_Z:
		_undo()
	elif k.ctrl_pressed and k.keycode == KEY_Y:
		_redo()
	elif k.keycode == KEY_ESCAPE:
		placing = ""
		status.text = "Ready"
	elif k.keycode == KEY_DELETE and mode == "build":
		match selected.get("kind", ""):
			"part": _do([{"op": "remove_part", "uid": selected["uid"]}])
			"limb": _do([{"op": "remove_limb", "uid": selected["uid"]}])
		selected = {}
		_refresh_inspector()
	elif mode == "drive" and animator and k.keycode in [KEY_1, KEY_2, KEY_3]:
		animator.play(["roar", "wave", "hop"][k.keycode - KEY_1])


# ============================================================ files

func _on_new() -> void:
	_snapshot()
	recipe = Recipe.normalize(Recipe.default_recipe(), catalog)["recipe"]
	selected = {}
	_rebuild()
	_frame_camera()
	_refresh_inspector()


func _on_example(i: int) -> void:
	if i == 0:
		return
	_open_path("res://examples/%s.json" % examples_menu.get_item_text(i))
	examples_menu.select(0)


func _open_path(path: String) -> void:
	var r := Recipe.load_file(path)
	if r.is_empty():
		status.text = "Could not read " + path
		return
	_snapshot()
	var n: Dictionary = Recipe.normalize(r, catalog)
	recipe = n["recipe"]
	selected = {}
	_rebuild()
	_frame_camera()
	_refresh_inspector()
	if not n["warnings"].is_empty():
		status.text += "   (loaded with %d adjustments)" % n["warnings"].size()


func _dialog(mode_: int, filter: String, cb: Callable) -> void:
	for c in file_dialog.file_selected.get_connections():
		file_dialog.file_selected.disconnect(c["callable"])
	file_dialog.file_mode = mode_
	file_dialog.filters = PackedStringArray([filter])
	file_dialog.file_selected.connect(cb, CONNECT_ONE_SHOT)
	file_dialog.popup_centered()


func _on_open() -> void:
	_dialog(FileDialog.FILE_MODE_OPEN_FILE, "*.json ; Recipes", _open_path)


func _on_save() -> void:
	_dialog(FileDialog.FILE_MODE_SAVE_FILE, "*.json ; Recipes", func(p):
		Recipe.save_file(recipe, p)
		status.text = "Saved " + p)


func _on_export() -> void:
	_dialog(FileDialog.FILE_MODE_SAVE_FILE, "*.glb ; glTF binary", func(p):
		var c: Node3D = Builder.build(recipe)
		add_child(c)
		Baker.bake_all(c)
		var err: int = Baker.export_glb(c, p)
		c.queue_free()
		status.text = ("Exported " + p) if err == OK else "Export failed (%d)" % err)
