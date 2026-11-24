extends Node3D

const MODEL := preload("res://minotaur.glb")
const SAVE_PATH := "user://minotaur_shapes.cfg"
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
	model = MODEL.instantiate()
	add_child(model)
	skin = model.find_children("*", "MeshInstance3D", true, false)[0]
	player = model.find_children("*", "AnimationPlayer", true, false)[0]
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
	restore_shapes()
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
	var panel := PanelContainer.new()
	layer.add_child(panel)
	panel.position = Vector2(16,16)
	var margin := MarginContainer.new()
	panel.add_child(margin)
	for side in ["left", "top", "right", "bottom"]:
		margin.add_theme_constant_override("margin_"+side, 12)
	var box := VBoxContainer.new()
	margin.add_child(box)
	box.add_theme_constant_override("separation", 7)
	var title := Label.new()
	title.text = "Minotaur"
	title.add_theme_font_size_override("font_size",24)
	box.add_child(title)
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
	button(motion, "Step in place", play_motion.bind("Walk"))
	button(box, "Rotate view", toggle_orbit)
	button(box, "Save proportions", save_shapes)
	button(box, "Reset proportions", reset_shapes)
	box.add_child(status)
	status.text = "Drag to orbit · scroll to zoom"

func button(parent: Control, label: String, callback: Callable) -> void:
	var item := Button.new()
	item.text = label
	parent.add_child(item)
	item.pressed.connect(callback)

func set_shape(value: float, feature: String) -> void:
	var index := skin.find_blend_shape_by_name(feature)
	if index >= 0:
		skin.set_blend_shape_value(index,value)

func neutral() -> void:
	player.stop()
	var skeleton: Skeleton3D = model.find_children("*", "Skeleton3D", true, false)[0]
	skeleton.reset_bone_poses()

func play_motion(clip: String) -> void:
	player.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
	player.play(clip)

func save_shapes() -> void:
	var cfg := ConfigFile.new()
	for feature in SHAPES:
		cfg.set_value("shape",feature,sliders[feature].value)
	var err := cfg.save(SAVE_PATH)
	status.text = "Proportions saved" if err == OK else "Could not save proportions"

func restore_shapes() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) == OK:
		for feature in SHAPES:
			sliders[feature].value = cfg.get_value("shape",feature,0.0)

func reset_shapes() -> void:
	for slider in sliders.values():
		slider.value = 0
	status.text = "Reference proportions restored"

func toggle_orbit() -> void:
	orbit = !orbit

func set_camera() -> void:
	var target := Vector3(0,2.42,0)
	camera.position = target + 9.0 * Vector3(sin(azimuth)*cos(elevation),sin(elevation),cos(azimuth)*cos(elevation))
	camera.look_at(target)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			rotating = event.pressed
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			camera.size = max(2.4,camera.size-0.25)
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			camera.size = min(9.0,camera.size+0.25)
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
