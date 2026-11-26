extends SceneTree

func _initialize() -> void:
	call_deferred("_run")

func _run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.is_empty():
		push_error("Pass the directory of runtime GLB fixtures")
		quit(1)
		return
	var base := ProjectSettings.globalize_path("res://../../")
	var runtime: Script = load(base.path_join("godot/creature_motion.gd"))
	var failed := false
	for sample in [["serpent", "serpent", 0], ["hopper", "hopper", 1], ["chibi", "character", 2],
			["bull", "bull", 4], ["uneven", "uneven", 4], ["spider", "spider", 8]]:
		var path: String = args[0].path_join(sample[0]).path_join(sample[1])
		var state := GLTFState.new()
		var loader := GLTFDocument.new()
		if loader.append_from_file(path + ".glb", state) != OK:
			quit(1)
			return
		var actor := loader.generate_scene(state) as Node3D
		root.add_child(actor)
		var skeleton := actor.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D
		var motion: SkeletonModifier3D = runtime.new()
		motion.active = false
		skeleton.add_child(motion)
		var bindings = JSON.parse_string(FileAccess.get_file_as_string(path + ".motion.json"))
		if not motion.configure(bindings):
			quit(1)
			return
		var legs: Array = motion._limbs.filter(func(limb): return limb.role == "leg")
		var arms: Array = motion._limbs.filter(func(limb): return limb.role == "arm")
		var expected: int = sample[2]
		failed = failed or legs.size() != expected or not actor.find_children("*", "AnimationPlayer", true, false).is_empty()
		var length_groups := {}
		for leg in legs:
			length_groups[leg.group_length] = true
		if sample[0] == "uneven":
			failed = failed or length_groups.size() < 2
		var maximum_contact := 0.0
		var maximum_drift := 0.0
		var maximum_lift := 0.0
		var arm_error := 0.0
		var slope_error := 0.0
		var stride_speed := .25
		if not legs.is_empty():
			stride_speed = float(legs[0].length) * .65
		for gait in ["walk", "run"]:
			motion.drive(gait, stride_speed)
			var prior := {}
			for frame in 150:
				actor.position.z += stride_speed / 60
				motion.advance(1.0 / 60)
				for leg in legs:
					var foot := skeleton.to_global(skeleton.get_bone_global_pose(leg.ids.back()).origin + leg.sole)
					if leg.swing:
						maximum_lift = maxf(maximum_lift, foot.y)
						prior.erase(leg.id)
					else:
						if frame > 80:
							maximum_contact = maxf(maximum_contact, foot.distance_to(leg.foot))
							if prior.has(leg.id):
								maximum_drift = maxf(maximum_drift, foot.distance_to(prior[leg.id]))
						prior[leg.id] = foot
		if not arms.is_empty():
			var arm: Dictionary = arms[0]
			motion.drive("walk", 0)
			var target := skeleton.to_global(skeleton.get_bone_global_rest(arm.ids[0]).origin +
				Vector3(.35 * arm.side, 0, .5) * float(arm.length))
			motion.reach(arm.id, target)
			for _frame in 45:
				motion.advance(1.0 / 60)
			arm_error = target.distance_to(skeleton.to_global(skeleton.get_bone_global_pose(arm.ids.back()).origin))
		var secondary: Array = motion._limbs.filter(func(limb): return limb.role == "tail")
		if not secondary.is_empty():
			failed = failed or secondary[0].lag.length() < .0001
		if expected == 2:
			var start_z := actor.position.z
			motion.ground_at = func(point: Vector3): return .04 * (point.z - start_z)
			failed = failed or not motion.configure(bindings)
			motion.drive("walk", stride_speed)
			for frame in 120:
				actor.position.z += stride_speed / 60
				motion.advance(1.0 / 60)
				if frame < 60:
					continue
				for leg in motion._limbs:
					if leg.role == "leg" and not leg.swing:
						var sole := skeleton.to_global(skeleton.get_bone_global_pose(leg.ids.back()).origin + leg.sole)
						slope_error = maxf(slope_error, absf(sole.y - float(motion.ground_at.call(sole))))
			motion.ground_at = Callable()
		var scale_error := 0.0
		if not legs.is_empty():
			var length: float = legs[0].length
			var id: String = legs[0].id
			for i in skeleton.get_bone_count():
				var rest := skeleton.get_bone_rest(i)
				rest.origin *= 1.25
				skeleton.set_bone_rest(i, rest)
			failed = failed or not motion.configure(bindings)
			var resized: Array = motion._limbs.filter(func(limb): return limb.id == id)
			scale_error = absf(float(resized[0].length) - length * 1.25)
			motion.drive("walk", stride_speed * 1.25)
			for frame in 120:
				actor.position.z += stride_speed * 1.25 / 60
				motion.advance(1.0 / 60)
				if frame < 60:
					continue
				for leg in motion._limbs:
					if leg.role == "leg" and not leg.swing:
						var foot := skeleton.to_global(skeleton.get_bone_global_pose(leg.ids.back()).origin + leg.sole)
						maximum_contact = maxf(maximum_contact, foot.distance_to(leg.foot))
		var observed := {"callback": false}
		motion.modification_processed.connect(func(): observed.callback = true, CONNECT_ONE_SHOT)
		motion.active = true
		await process_frame
		await process_frame
		failed = failed or not observed.callback
		print(sample[0], " legs=", legs.size(), " groups=", length_groups.size(), " contact=", maximum_contact, " drift=", maximum_drift,
			" lift=", maximum_lift, " reach=", arm_error, " rebind=", scale_error, " slope=", slope_error,
			" live_modifier=", observed.callback)
		failed = failed or maximum_contact > .012 or maximum_drift > .012 or arm_error > .012 or scale_error > .001 or slope_error > .012
		failed = failed or (expected > 0 and maximum_lift < .008)
		actor.free()
	quit(1 if failed else 0)
