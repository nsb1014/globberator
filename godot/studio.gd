extends Node3D

const MODELS := [preload("res://minotaur.glb"), preload("res://bull.glb")]
const SAVE_PATHS := ["user://minotaur_shapes.cfg", "user://bull_shapes.cfg"]
var character := 0
var selector := OptionButton.new()
var panel := PanelContainer.new()
var bull_view_width := 5.5
var walk_button: Button
var target := Vector3(0,2.42,0)
const SHAPES := ["Horn span", "Muzzle length", "Chest depth"]
var model: Node3D
var skin: MeshInstance3D
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
	model = MODELS[index].instantiate()
	add_child(model)
	skin = model.find_children("*", "MeshInstance3D", true, false)[0]
	player = model.find_children("*", "AnimationPlayer", true, false)[0]
	walk_button.text = "Walk forward" if character == 1 else "Step in place"
	azimuth = 0.55 if character == 1 else 0.12
	elevation = 0.12 if character == 1 else 0.07
	camera.size = 5.8
	for slider in sliders.values():
		slider.value = 0
	restore_shapes()
	status.text = "Drag to orbit · scroll to zoom"
	neutral()

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
	selector.add_item("Minotaur")
	selector.add_item("Bull")
	box.add_child(selector)
	selector.item_selected.connect(select_character)
	for feature in SHAPES:
		var label := Label.new()
		label.text = feature
		box.add_child(label)
		var slider := HSlider.new()
		slider.min_value = -1.0
		slider.max_value = 1.0
		slider.step = 0.02
		slider.custom_minimum_size.x = 170
		box.add_child(slider)
		sliders[feature] = slider
		slider.value_changed.connect(set_shape.bind(feature))
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
	target = Vector3(0,1.52,0.42) if character == 1 else Vector3(0,2.42,0)
	bull_view_width = 5.5
	fit_character()

func play_motion(clip: String) -> void:
	var forward := character == 1 and clip == "Walk"
	if forward:
		target = Vector3(0,1.52,1.48)
		azimuth = 1.48
		bull_view_width = 7.65
		fit_character()
	elif character == 1:
		target = Vector3(0,1.52,0.42)
		bull_view_width = 5.5
		fit_character()
	player.stop()
	player.get_animation(clip).loop_mode = Animation.LOOP_NONE if forward else Animation.LOOP_LINEAR
	player.play(clip)

func save_shapes() -> void:
	var cfg := ConfigFile.new()
	for feature in SHAPES:
		cfg.set_value("shape",feature,sliders[feature].value)
	var err := cfg.save(SAVE_PATHS[character])
	status.text = "Proportions saved" if err == OK else "Could not save proportions"

func restore_shapes() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATHS[character]) == OK:
		for feature in SHAPES:
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
	if character == 1:
		var view_size := get_viewport().get_visible_rect().size
		var width := maxf(1.0,view_size.x-controls_width(view_size))
		camera.size = maxf(3.9,bull_view_width*view_size.y/width)
	set_camera()

func set_camera() -> void:
	camera.position = target + 9.0 * Vector3(sin(azimuth)*cos(elevation),sin(elevation),cos(azimuth)*cos(elevation))
	camera.look_at(target)
	camera.h_offset = 0.0
	if character == 1:
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
			camera.size = camera.size+0.25 if character == 1 else minf(9.0,camera.size+0.25)
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
