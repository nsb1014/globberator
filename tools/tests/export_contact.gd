extends SceneTree

# godot --headless --script tools/tests/export_contact.gd -- /absolute/path/to/bull.glb
# Load the exported GLB through Godot. Measure each rigid hoof/tip vertex in world space.
func _initialize() -> void:
    call_deferred("run")

func run() -> void:
    var paths := OS.get_cmdline_user_args()
    if paths.is_empty():
        quit(2)
        return
    for path in paths:
        if not check_file(path):
            push_error("Ground contact failed for " + path)
            quit(1)
            return
    quit(0)

func check_file(path: String) -> bool:
    var report = JSON.parse_string(FileAccess.get_file_as_string(path.get_basename() + ".report.json"))
    if not report is Dictionary or not report.has("contact"):
        return false
    var contact: Dictionary = report.contact
    var doc := GLTFDocument.new()
    var state := GLTFState.new()
    if doc.append_from_file(path, state) != OK:
        return false
    var model := doc.generate_scene(state)
    root.add_child(model)
    var skeletons := model.find_children("*", "Skeleton3D", true, false)
    var players := model.find_children("*", "AnimationPlayer", true, false)
    if skeletons.size() != 1 or players.size() != 1:
        return false
    var sk: Skeleton3D = skeletons[0]
    var player: AnimationPlayer = players[0]
    var probes := {}
    for obj in model.find_children("*", "MeshInstance3D", true, false):
        var mesh_node: MeshInstance3D = obj
        var skin := mesh_node.skin
        if skin == null:
            continue
        for surface in mesh_node.mesh.get_surface_count():
            var data := mesh_node.mesh.surface_get_arrays(surface)
            var verts: PackedVector3Array = data[Mesh.ARRAY_VERTEX]
            var weights = data[Mesh.ARRAY_WEIGHTS]
            var binds = data[Mesh.ARRAY_BONES]
            if weights == null or verts.is_empty():
                continue
            var stride := int(weights.size() / verts.size())
            for i in verts.size():
                for k in stride:
                    var index := i * stride + k
                    if weights[index] < 0.999:
                        continue
                    var bind: int = binds[index]
                    var bone := skin.get_bind_bone(bind)
                    if bone < 0:
                        bone = sk.find_bone(skin.get_bind_name(bind))
                    if bone < 0:
                        continue
                    var key := String(sk.get_bone_name(bone))
                    if not contact.legs.has(key):
                        continue
                    var local: Vector3 = skin.get_bind_pose(bind) * verts[i]
                    var y: float = (sk.global_transform * sk.get_bone_global_rest(bone) * local).y
                    if not probes.has(key) or y < probes[key].y:
                        probes[key] = {"bone": bone, "local": local, "y": y}
    if probes.is_empty() or probes.size() != contact.legs.size() or not player.has_animation("walk"):
        return false
    var starts := {}
    var lifted := {}
    var planted := {}
    player.play("walk")
    for frame in contact.frames:
        player.seek(frame.time, true)
        sk.force_update_all_bone_transforms()
        var travel := Vector3(frame.travel[0], frame.travel[1], frame.travel[2])
        for key in probes:
            var p: Dictionary = probes[key]
            var sole: Vector3 = sk.global_transform * sk.get_bone_global_pose(p.bone) * p.local + travel
            var length: float = contact.legs[key]
            if key in frame.stance:
                if not starts.has(key):
                    starts[key] = sole
                planted[key] = true
                if absf(sole.y) > 0.05 * length or sole.distance_to(starts[key]) > 0.05 * length:
                    return false
            else:
                starts.erase(key)
                if sole.y > 0.025 * length:
                    lifted[key] = true
    model.free()
    return lifted.size() == probes.size() and planted.size() == probes.size()
