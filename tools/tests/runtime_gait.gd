extends SceneTree

# Read an exported clip, disturb all walking chains, then solve them again in
# Godot. Compare origins and orientations to the independently baked Blender pose.
const GroundGait = preload("res://ground_gait.gd")

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var paths := OS.get_cmdline_user_args()
	if paths.is_empty():
		paths = PackedStringArray(["res://minotaur.glb","res://bull.glb","res://arachnid.glb"])
	var failed := false
	for path in paths:
		var studio = load("res://studio.tscn").instantiate()
		root.add_child(studio)
		if path.begins_with("res://"):
			var index := ["res://minotaur.glb","res://bull.glb","res://arachnid.glb"].find(path)
			studio.select_character(index)
		else:
			studio.open_creature(path)
			if studio.character < studio.CHARACTERS.size():
				quit(1)
				return
		var gait: GroundGait = studio.gait
		var sk := gait.get_skeleton()
		var player: AnimationPlayer = studio.player
		var profile := gait.profile
		player.play("Walk")
		var duration := player.current_animation_length
		var frames := roundi(duration*24)
		var error := 0.
		var disturbed := 0.
		var checks: Array[int] = []
		for leg in gait.legs:
			checks.append(leg.ids.back())
		checks.append_array(gait.spine)
		if gait.root_bone >= 0:
			checks.append(gait.root_bone)
		for frame in range(frames+1):
			sk.reset_bone_poses()
			player.seek(minf(frame/24.,duration),true)
			var expected := {}
			for id in checks:
				expected[id] = sk.get_bone_global_pose(id)
			for leg in gait.legs:
				for id in leg.ids:
					sk.set_bone_pose_rotation(id,Quaternion(Vector3.RIGHT,.55))
			for id in gait.spine:
				sk.set_bone_pose_rotation(id,Quaternion(Vector3.RIGHT,.55))
			for id in checks:
				disturbed = maxf(disturbed,sk.get_bone_global_pose(id).origin.distance_to(expected[id].origin))
			gait.pose_at(float(profile.cycles)*frame/frames)
			for id in checks:
				var pose := sk.get_bone_global_pose(id)
				error = maxf(error,pose.origin.distance_to(expected[id].origin))
				error = maxf(error,pose.basis.x.distance_to(expected[id].basis.x))
				error = maxf(error,pose.basis.y.distance_to(expected[id].basis.y))
		# Run the actual modifier callback with its managed rotation tracks disabled.
		var sample_time := roundf(.72*frames)/24.
		player.seek(sample_time,true)
		var reference := {}
		for id in checks:
			reference[id] = sk.get_bone_global_pose(id)
		var names := {}
		for leg in gait.legs:
			for joint in leg.joints:
				names[joint] = true
		for id in gait.spine:
			names[sk.get_bone_name(id)] = true
		var animation := player.get_animation("Walk")
		var disabled: Array[int] = []
		for i in animation.get_track_count():
			var target := animation.track_get_path(i)
			if target.get_subname_count() and names.has(str(target.get_subname(0))) and animation.track_is_enabled(i):
				animation.track_set_enabled(i,false)
				disabled.append(i)
		studio.play_motion("Walk")
		player.speed_scale = 0.
		sk.reset_bone_poses()
		player.seek(sample_time,true)
		var observed := {"ran":false,"error":0.}
		gait.modification_processed.connect(func():
			observed.ran = true
			for id in checks:
				var pose := sk.get_bone_global_pose(id)
				observed.error = maxf(observed.error,pose.origin.distance_to(reference[id].origin))
				observed.error = maxf(observed.error,pose.basis.y.distance_to(reference[id].basis.y))
		,CONNECT_ONE_SHOT)
		await process_frame
		await process_frame
		for i in disabled:
			animation.track_set_enabled(i,true)
		failed = failed or disabled.is_empty() or not observed.ran or observed.error > .002
		print("Live modifier with tracks disabled: ",observed)
		print(path.get_file(),": ",gait.legs.size()," walking feet, disturbed ",disturbed,", recovered error ",error)
		failed = failed or error > .002 or disturbed < .10
		studio.queue_free()
		await process_frame
	quit(1 if failed else 0)
