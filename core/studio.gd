## Offscreen render studio: a SubViewport with lights, optional ground and an
## orbit camera that frames a creature. Used by the CLI (renders, masks,
## videos, thumbnails) and by tests.
extends RefCounted

var viewport: SubViewport
var camera: Camera3D
var ground: MeshInstance3D
var stage: Node3D
var key: DirectionalLight3D
var env: WorldEnvironment


func _init(parent: Node, size := Vector2i(512, 512)) -> void:
	viewport = SubViewport.new()
	viewport.size = size
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.msaa_3d = Viewport.MSAA_4X
	parent.add_child(viewport)
	stage = Node3D.new()
	viewport.add_child(stage)
	camera = Camera3D.new()
	camera.fov = 30.0
	camera.near = 0.05
	camera.far = 200.0
	viewport.add_child(camera)
	key = DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-50, 35, 0)
	key.light_energy = 0.95
	key.shadow_enabled = true
	viewport.add_child(key)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-20, -140, 0)
	fill.light_energy = 0.35
	viewport.add_child(fill)
	env = WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.17, 0.19, 0.22)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.62, 0.66, 0.72)
	e.ambient_light_energy = 0.4
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	e.fog_enabled = true
	e.fog_light_color = Color(0.17, 0.19, 0.22)
	e.fog_density = 0.012
	e.fog_sky_affect = 0.0
	env.environment = e
	viewport.add_child(env)
	ground = MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(400, 400)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color(0.2, 0.215, 0.23)
	gm.roughness = 1.0
	ground.material_override = gm
	viewport.add_child(ground)


func set_mask_mode(on: bool) -> void:
	viewport.transparent_bg = on
	ground.visible = not on
	key.shadow_enabled = not on


func set_background(c: Color) -> void:
	env.environment.background_color = c


## Place the camera on an orbit around `box`. yaw 0 looks at the creature's
## face (camera on +Z), yaw 90 shows its +X side. pitch is elevation in degrees.
func frame(box: AABB, yaw_deg: float, pitch_deg: float, margin := 1.08) -> void:
	var c := box.get_center()
	var radius := box.size.length() * 0.5
	var dist := radius / sin(deg_to_rad(camera.fov * 0.5)) * margin
	var yaw := deg_to_rad(yaw_deg)
	var pitch := deg_to_rad(pitch_deg)
	var dir := Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch))
	camera.position = c + dir * dist
	camera.look_at(c, Vector3.UP)


func capture() -> Image:
	await RenderingServer.frame_post_draw
	return viewport.get_texture().get_image()


## Render after letting the scene settle a couple of frames.
func snap(tree: SceneTree, frames := 2) -> Image:
	for i in frames:
		await tree.process_frame
	return await capture()


const VIEWS := {
	"front": [0.0, 8.0], "side": [90.0, 8.0], "threequarter": [38.0, 16.0],
	"back": [180.0, 10.0], "top": [0.0, 80.0], "otherside": [-90.0, 8.0], "threequarter_left": [-38.0, 16.0],
}


static func view_angles(view: String) -> Vector2:
	if VIEWS.has(view):
		return Vector2(VIEWS[view][0], VIEWS[view][1])
	# "yaw,pitch" custom view
	var bits := view.split(",")
	if bits.size() == 2:
		return Vector2(float(bits[0]), float(bits[1]))
	return Vector2(38, 16)
