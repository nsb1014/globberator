extends SceneTree

func _initialize() -> void:
	call_deferred("check_studio")

func check_studio() -> void:
	var studio = load("res://studio.tscn").instantiate()
	root.add_child(studio)
	await process_frame
	studio.select_character(2)
	var sk: Skeleton3D = studio.model.find_children("*","Skeleton3D",true,false)[0]
	var valid := sk.get_bone_count() == 38
	for feature in ["Abdomen width","Abdomen depth","Jaw breadth"]:
		var idx: int = studio.skin.find_blend_shape_by_name(feature)
		if idx < 0 or not studio.sliders.has(feature):
			quit(1)
			return
		studio.sliders[feature].value = .5
		valid = valid and is_equal_approx(studio.skin.get_blend_shape_value(idx),.5)
	studio.reset_shapes()
	valid = valid and studio.player.has_animation("Idle") and studio.player.has_animation("Walk")
	studio.play_motion("Walk")
	var duration: float = studio.player.get_animation("Walk").length
	var root_index := sk.find_bone("Carapace")
	studio.player.seek(0,true)
	sk.force_update_all_bone_transforms()
	var initial := sk.get_bone_global_pose(root_index).origin
	studio.player.seek(duration,true)
	sk.force_update_all_bone_transforms()
	var travel := sk.get_bone_global_pose(root_index).origin.z - initial.z
	valid = valid and absf(travel-1.30) < .002
	valid = valid and check_soles(studio,sk,duration)
	studio.neutral()
	var rest := sk.get_bone_global_rest(root_index).origin
	valid = valid and sk.get_bone_global_pose(root_index).origin.distance_to(rest) < .001
	studio.select_character(0)
	valid = valid and studio.sliders.has("Horn span") and not studio.sliders.has("Jaw breadth")
	print("Solifuge studio, shapes, neutral reset and forward walk: ",valid,"; travel ",travel)
	quit(0 if valid else 1)

func check_soles(studio, sk: Skeleton3D, duration: float) -> bool:
	var legs: Array = studio.gait.legs
	if legs.size() != 8:
		return false
	var soles: Array = []
	for leg in legs:
		soles.append([])
	# Identify actual flat sole patches independently of the exported labels.
	for surface in studio.skin.mesh.get_surface_count():
		var verts: PackedVector3Array = studio.skin.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
		for v in verts:
			var p := sk.to_local(studio.skin.to_global(v))
			if absf(sk.to_global(p).y) > .00025:
				continue
			var closest := 0
			var distance := INF
			for j in legs.size():
				var d := p.distance_squared_to(sk.get_bone_global_rest(legs[j].ids.back()).origin)
				if d < distance:
					distance = d
					closest = j
			soles[closest].append(p)
	for sole in soles:
		if sole.size() < 8:
			return false
	var worst := 0.
	var minimum := 8
	for frame in range(321):
		var cycle := frame/160.
		studio.player.seek(duration*frame/320.,true)
		studio.gait.pose_at(cycle)
		var support := 0
		for j in legs.size():
			var foot: int = legs[j].ids.back()
			var motion := sk.get_bone_global_pose(foot)*sk.get_bone_global_rest(foot).affine_inverse()
			var phase := fposmod(cycle-float(legs[j].touchdown),1.)
			var height := INF
			for p in soles[j]:
				var actual := sk.to_global(motion*p)
				height = minf(height,actual.y)
				if phase < .90:
					var expected := sk.to_global(p)+Vector3(0,0,.65*(cycle-phase+.45))
					worst = maxf(worst,actual.distance_to(expected))
			if height < -.001:
				return false
			if height < .001:
				support += 1
		minimum = mini(minimum,support)
	print("Godot eight-leg walk: minimum support ",minimum,", footprint error ",worst)
	return minimum == 7 and worst < .001
