extends Node3D

const SHAPES := ["Horn span", "Muzzle length", "Chest depth"]
const CHARACTERS := [
    {"name":"Minotaur", "scene":preload("res://minotaur.glb"), "save":"user://minotaur_shapes.cfg",
     "shapes":SHAPES, "focus":Vector3(0,2.42,0), "azimuth":0.12, "elevation":0.07, "width":0.0},
    {"name":"Bull", "scene":preload("res://bull.glb"), "save":"user://bull_shapes.cfg",
     "shapes":SHAPES, "focus":Vector3(0,1.52,0.42), "azimuth":0.55, "elevation":0.12,
     "width":5.5, "travel":2.08, "walk_width":7.65, "walk_azimuth":1.48},
    {"name":"Solifuge", "scene":preload("res://arachnid.glb"), "save":"user://arachnid_shapes.cfg",
     "shapes":["Abdomen width","Abdomen depth","Jaw breadth"], "focus":Vector3(0,0.49,0.25),
     "azimuth":0.91, "elevation":0.50, "width":5.85, "travel":1.30, "walk_width":6.65, "walk_azimuth":0.91},
]
var entries := CHARACTERS.duplicate(true)
var shape_panel := VBoxContainer.new()
var character := 0
var selector := OptionButton.new()
var panel := PanelContainer.new()
var view_width := 0.0
var walk_button: Button
var target := Vector3(0,2.42,0)
var model: Node3D
var skin: MeshInstance3D
var gait: SkeletonModifier3D
var player: AnimationPlayer
var camera := Camera3D.new()
var azimuth := 0.12
var elevation := 0.07
var rotating := false
var sliders: Dictionary = {}
var orbit := false
var status := Label.new()

func _ready() -> void:
	add_child(camera)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 5.8
	camera.current = true
	set_camera()
	var sky := Environment.new()
	sky.background_mode = Environment.BG_COLOR
	sky.background_color = Color("#292e34")
	sky.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	sky.ambient_light_color = Color("#d5d9df")
	sky.ambient_light_energy = 0.65
	var world := WorldEnvironment.new()
	world.environment = sky
	add_child(world)
	add_light(Vector3(-3, 6, 5), 1.55, true)
	add_light(Vector3(4, 4, -3), 1.20, false)
	if DisplayServer.get_name() != "headless":
		add_floor()
	make_controls()
	select_character(0)
	get_viewport().size_changed.connect(fit_character)

func select_character(index: int) -> void:
	if model:
		remove_child(model)
		model.queue_free()
	character = index
	selector.select(index)
	var entry: Dictionary = entries[index]
	model = entry.scene.instantiate()
	add_child(model)
	skin = model.find_children("*", "MeshInstance3D", true, false)[0]
	player = model.find_children("*", "AnimationPlayer", true, false)[0]
	if model.has_meta("ground_gait"):
		gait = preload("res://ground_gait.gd").new()
		var skeleton: Skeleton3D = model.find_children("*","Skeleton3D",true,false)[0]
		skeleton.add_child(gait)
		gait.configure(player,model.get_meta("ground_gait"))
	walk_button.text = "Walk forward" if entry.has("travel") else "Step in place"
	azimuth = entry.azimuth
	elevation = entry.elevation
	camera.size = 5.8
	configure_shapes(entry.shapes)
	restore_shapes()
	status.text = "Drag to orbit · scroll to zoom"
	neutral()

func open_creature(path: String) -> void:
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	if document.append_from_file(path,state) != OK:
		status.text = "Could not open the creature GLB."
		return
	var profile := preload("res://ground_gait.gd").profile_from_nodes(state.json.get("nodes",[]))
	if profile.is_empty():
		status.text = "Choose a PolyForge GLB that includes gait bindings."
		return
	var creature := document.generate_scene(state,24)
	creature.set_meta("ground_gait",profile)
	var meshes := creature.find_children("*","MeshInstance3D",true,false)
	if meshes.is_empty() or creature.find_children("*","Skeleton3D",true,false).is_empty():
		creature.free()
		status.text = "The creature needs a skinned mesh and a skeleton."
		return
	var mesh: MeshInstance3D = meshes[0]
	var bounds := mesh.get_aabb()
	var shapes := []
	for i in mesh.get_blend_shape_count():
		shapes.append(mesh.mesh.get_blend_shape_name(i))
	var packed := PackedScene.new()
	var result := packed.pack(creature)
	creature.free()
	if result != OK:
		status.text = "Could not load the creature scene."
		return
	var width := maxf(bounds.size.x,bounds.size.z)*1.35
	var entry := {"name":"Generated · %d legs" % profile.legs.size(),"scene":packed,"shapes":shapes,
		"save":"user://creature_%s.cfg" % path.sha256_text(),"focus":bounds.get_center(),
		"azimuth":.91,"elevation":.42,"width":width}
	var travel: float = profile.cycles*profile.stride
	if travel > 0:
		entry.merge({"travel":travel,"walk_width":width+travel,"walk_azimuth":.91})
	var slot := CHARACTERS.size()
	if entries.size() == slot:
		entries.append(entry)
		selector.add_item(entry.name)
	else:
		entries[slot] = entry
		selector.set_item_text(slot,entry.name)
	select_character(slot)

func add_floor() -> void:
	var floor_plane := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(200, 200)
	var surface := StandardMaterial3D.new()
	surface.albedo_color = Color("#474d53")
	surface.roughness = 1.0
	plane.material = surface
	add_child(floor_plane)
	floor_plane.mesh = plane

func add_light(position_3d: Vector3, energy: float, shadows: bool) -> void:
	var light := DirectionalLight3D.new()
	add_child(light)
	light.position = position_3d
	light.look_at(Vector3.ZERO)
	light.light_energy = energy
	light.shadow_enabled = shadows

func make_controls() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	layer.add_child(panel)
	panel.position = Vector2(16,16)
	var margin := MarginContainer.new()
	panel.add_child(margin)
	for side in ["left", "top", "right", "bottom"]:
		margin.add_theme_constant_override("margin_"+side, 12)
	var box := VBoxContainer.new()
	margin.add_child(box)
	box.add_theme_constant_override("separation", 7)
	for entry in CHARACTERS:
		selector.add_item(entry.name)
	box.add_child(selector)
	var files := FileDialog.new()
	files.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	files.access = FileDialog.ACCESS_FILESYSTEM
	files.filters = PackedStringArray(["*.glb ; PolyForge creature"])
	box.add_child(files)
	files.file_selected.connect(open_creature)
	button(box,"Open creature GLB",func(): files.popup_centered_ratio(.7))
	selector.item_selected.connect(select_character)
	box.add_child(shape_panel)
	var motion := HBoxContainer.new()
	box.add_child(motion)
	button(motion, "Neutral", neutral)
	button(motion, "Idle", play_motion.bind("Idle"))
	walk_button = button(motion, "Step in place", play_motion.bind("Walk"))
	button(box, "Rotate view", toggle_orbit)
	button(box, "Save proportions", save_shapes)
	button(box, "Reset proportions", reset_shapes)
	box.add_child(status)
	status.text = "Drag to orbit · scroll to zoom"

func configure_shapes(features: Array) -> void:
	sliders.clear()
	for child in shape_panel.get_children():
		shape_panel.remove_child(child)
		child.queue_free()
	for feature in features:
		var label := Label.new()
		label.text = feature
		shape_panel.add_child(label)
		var slider := HSlider.new()
		slider.min_value = -1.0
		slider.max_value = 1.0
		slider.step = 0.02
		slider.custom_minimum_size.x = 170
		shape_panel.add_child(slider)
		sliders[feature] = slider
		slider.value_changed.connect(set_shape.bind(feature))

func button(parent: Control, label: String, callback: Callable) -> Button:
	var item := Button.new()
	item.text = label
	parent.add_child(item)
	item.pressed.connect(callback)
	return item

func set_shape(value: float, feature: String) -> void:
	var index := skin.find_blend_shape_by_name(feature)
	if index >= 0:
		skin.set_blend_shape_value(index,value)

func neutral() -> void:
	player.stop()
	var skeleton: Skeleton3D = model.find_children("*", "Skeleton3D", true, false)[0]
	skeleton.reset_bone_poses()
	target = entries[character].focus
	view_width = entries[character].width
	fit_character()

func play_motion(clip: String) -> void:
	var entry: Dictionary = entries[character]
	var forward := entry.has("travel") and clip == "Walk"
	target = entry.focus
	view_width = entry.width
	if forward:
		target.z += 0.5 * float(entry.travel)
		azimuth = entry.walk_azimuth
		view_width = entry.walk_width
	fit_character()
	player.stop()
	player.get_animation(clip).loop_mode = Animation.LOOP_NONE if forward else Animation.LOOP_LINEAR
	player.play(clip)

func save_shapes() -> void:
	var cfg := ConfigFile.new()
	for feature in sliders:
		cfg.set_value("shape",feature,sliders[feature].value)
	var err := cfg.save(entries[character].save)
	status.text = "Proportions saved" if err == OK else "Could not save proportions"

func restore_shapes() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(entries[character].save) == OK:
		for feature in sliders:
			sliders[feature].value = cfg.get_value("shape",feature,0.0)

func reset_shapes() -> void:
	for slider in sliders.values():
		slider.value = 0
	status.text = "Reference proportions restored"

func toggle_orbit() -> void:
	orbit = !orbit

func controls_width(view_size: Vector2) -> float:
	return minf(panel.position.x + panel.get_combined_minimum_size().x + 12.0,view_size.x*0.6)

func fit_character() -> void:
	if view_width > 0:
		var view_size := get_viewport().get_visible_rect().size
		var width := maxf(1.0,view_size.x-controls_width(view_size))
		camera.size = maxf(3.9,view_width*view_size.y/width)
	set_camera()

func set_camera() -> void:
	camera.position = target + 9.0 * Vector3(sin(azimuth)*cos(elevation),sin(elevation),cos(azimuth)*cos(elevation))
	camera.look_at(target)
	camera.h_offset = 0.0
	if view_width > 0:
		var view_size := get_viewport().get_visible_rect().size
		camera.h_offset = -0.5*controls_width(view_size)*camera.size/maxf(view_size.y,1.0)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			rotating = event.pressed
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			camera.size = max(2.4,camera.size-0.25)
			set_camera()
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			camera.size = camera.size+0.25 if view_width > 0 else minf(9.0,camera.size+0.25)
			set_camera()
	elif event is InputEventMouseMotion and rotating:
		azimuth -= event.relative.x*0.009
		elevation = clamp(elevation+event.relative.y*0.006,-0.12,0.95)
		set_camera()

func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and not event.pressed:
		rotating = false

func _process(delta: float) -> void:
	if orbit:
		azimuth += delta*0.45
		set_camera()
