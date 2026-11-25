extends SceneTree

func _initialize() -> void:
	call_deferred("check_studio")

func check_studio() -> void:
	var studio = load("res://studio.tscn").instantiate()
	root.add_child(studio)
	await process_frame
	studio.select_character(2)
	var sk: Skeleton3D = studio.model.find_children("*","Skeleton3D",true,false)[0]
	var valid := sk.get_bone_count() == 36
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
	studio.neutral()
	var rest := sk.get_bone_global_rest(root_index).origin
	valid = valid and sk.get_bone_global_pose(root_index).origin.distance_to(rest) < .001
	studio.select_character(0)
	valid = valid and studio.sliders.has("Horn span") and not studio.sliders.has("Jaw breadth")
	print("Solifuge studio, shapes, neutral reset and forward walk: ",valid,"; travel ",travel)
	quit(0 if valid else 1)
