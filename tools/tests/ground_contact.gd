extends SceneTree

# Run after the Godot import, using --headless --path godot --script on this file.
func _initialize() -> void:
	call_deferred("check_ground")

func check_ground() -> void:
	var studio = load("res://studio.tscn").instantiate()
	root.add_child(studio)
	await process_frame
	var sk: Skeleton3D = studio.model.find_children("*","Skeleton3D",true,false)[0]
	var skin: MeshInstance3D = studio.skin
	var soles := {"L": [], "R": []}
	# Collect the actual neutral sole vertices from the exported mesh. Each
	# cloven toe is rigidly weighted to its corresponding Foot bone.
	for surface in skin.mesh.get_surface_count():
		var positions: PackedVector3Array = skin.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
		for vertex in positions:
			var p: Vector3 = sk.to_local(skin.to_global(vertex))
			if absf((sk.global_transform*p).y) < .00025:
				soles["L" if p.x > 0 else "R"].append(p)
	for side in soles:
		if soles[side].size() < 3:
			push_error("Could not locate both neutral hoof soles")
			quit(1)
			return

	var max_drift := 0.0
	var lowest := INF
	var peaks := {"L":0.0, "R":0.0}
	for clip in ["Idle","Walk"]:
		studio.play_motion(clip)
		var duration: float = studio.player.get_animation(clip).length
		for sample in range(241):
			var t := sample / 240.0
			studio.player.seek(t*duration, true)
			sk.force_update_all_bone_transforms()
			for side in soles:
				var index := sk.find_bone("Foot."+side)
				var transform := sk.get_bone_global_pose(index)*sk.get_bone_global_rest(index).affine_inverse()
				var phase := fmod(t + (0.0 if side=="L" else .5), 1.0)
				var min_height := INF
				for vertex in soles[side]:
					var actual: Vector3 = sk.global_transform*(transform*vertex)
					var rest: Vector3 = sk.global_transform*vertex
					min_height = minf(min_height, actual.y)
					if clip == "Idle" or phase < .60:
						max_drift = maxf(max_drift, actual.distance_to(rest))
				lowest = minf(lowest, min_height)
				peaks[side] = maxf(peaks[side],min_height)

	print("Max planted-sole displacement: ",max_drift,", lowest sole: ",lowest,", peak clearances: ",peaks)
	quit(0 if max_drift < .0005 and lowest > -.0003 and peaks["L"] > .22 and peaks["R"] > .22 else 1)
