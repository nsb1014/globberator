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
			["bull", "bull", 4], ["uneven", "uneven", 4], ["spider", "spider", 8], ["minotaur", "minotaur", 2]]:
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
					var foot := _stance_anchor(skeleton, leg)
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
			if bindings.profile == "humanoid":
				failed = not _check_humanoid_motion(actor, skeleton, motion, bindings, stride_speed) or failed
		if sample[0] == "minotaur":
			failed = not _check_hoofed_walk(actor, skeleton, motion, bindings) or failed
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
						var sole := _stance_anchor(skeleton, leg)
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
						var foot := _stance_anchor(skeleton, leg)
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
	quit(1 if failed or not _check_multi_bend(runtime) else 0)


func _stance_anchor(skeleton: Skeleton3D, leg: Dictionary) -> Vector3:
	var tip := skeleton.get_bone_global_pose(leg.ids.back())
	if not leg.has("toe"):
		return skeleton.to_global(tip.origin + leg.sole)
	var rest: Transform3D = leg.rest.back()
	var rotation := tip.basis * rest.basis.inverse()
	return skeleton.to_global(tip.origin + rotation * leg.toe - (leg.toe - leg.sole))


func _check_humanoid_motion(actor: Node3D, skeleton: Skeleton3D, motion: SkeletonModifier3D, bindings: Dictionary, speed: float) -> bool:
	if not motion.configure(bindings):
		return false
	var minimum_knee := INF
	var arm_samples := 0
	var wrong_swing := 0
	for gait in ["walk", "run"]:
		# Speed above the nominal gait period forces the feet to change cadence.
		var fast := speed * (1.8 if gait == "walk" else 2.5)
		motion.drive(gait, fast)
		for frame in 120:
			actor.position.z += fast / 60
			motion.advance(1.0 / 60)
			for limb in motion._limbs:
				var root_joint := skeleton.get_bone_global_pose(limb.ids[0]).origin
				var tip := skeleton.get_bone_global_pose(limb.ids.back()).origin
				if limb.role == "leg":
					var knee := skeleton.get_bone_global_pose(limb.ids[1]).origin
					var next := skeleton.get_bone_global_pose(limb.ids[2]).origin
					minimum_knee = minf(minimum_knee, (knee - root_joint).slide(root_joint.direction_to(next)).z)
				elif limb.role == "arm" and frame > 10:
					var leg: Dictionary = limb.gait_leg
					var duty: float = bindings.poses[gait].duty
					var expected := 0
					if leg.phase < .07 or leg.phase > .93:
						expected = -1
					elif absf(leg.phase - duty) < .07:
						expected = 1
					if expected != 0:
						var rest := skeleton.get_bone_global_rest(limb.ids.back()).origin - skeleton.get_bone_global_rest(limb.ids[0]).origin
						var relative := tip - root_joint - rest
						arm_samples += 1
						wrong_swing += int(relative.z * expected <= 0)
	print("  ", actor.name, " fast gait knee=", minimum_knee, " phase mismatches=", wrong_swing, "/", arm_samples)
	return minimum_knee > -.0002 and arm_samples >= 20 and wrong_swing == 0


func _check_hoofed_walk(actor: Node3D, skeleton: Skeleton3D, motion: SkeletonModifier3D, bindings: Dictionary) -> bool:
	if not motion.configure(bindings):
		return false
	var legs: Array = motion._limbs.filter(func(limb): return limb.role == "leg" and limb.has("toe"))
	if legs.size() != 2:
		return false
	var speed := .35 * float(legs[0].length)
	var duty: float = bindings.poses.walk.duty
	var frames := roundi(float(bindings.poses.walk.period) * 60)
	var initial_phase: float = legs[0].phase
	var maximum_roll := 0.0
	var maximum_tuck := 0.0
	var minimum_hock := INF
	var maximum_flex := 0.0
	var support_error := 0.0
	motion.drive("walk", speed)
	for frame in frames * 2:
		actor.position.z += speed / 60
		motion.advance(1.0 / 60)
		if frame < frames:
			continue
		for leg in legs:
			var hip := skeleton.get_bone_global_pose(leg.ids[0]).origin
			var knee := skeleton.get_bone_global_pose(leg.ids[1]).origin
			var hock := skeleton.get_bone_global_pose(leg.ids[2]).origin
			var tip := skeleton.get_bone_global_pose(leg.ids[3])
			for i in leg.joint_support.size():
				var joint: int = leg.joint_support[i]
				var previous := skeleton.get_bone_global_pose(leg.ids[i]).basis * skeleton.get_bone_global_rest(leg.ids[i]).basis.inverse()
				var next := skeleton.get_bone_global_pose(leg.ids[i + 1]).basis * skeleton.get_bone_global_rest(leg.ids[i + 1]).basis.inverse()
				var expected := previous.get_rotation_quaternion().slerp(next.get_rotation_quaternion(), .5)
				var support := skeleton.get_bone_global_pose(joint)
				var actual := (support.basis * skeleton.get_bone_global_rest(joint).basis.inverse()).get_rotation_quaternion()
				support_error = maxf(support_error, support.origin.distance_to(skeleton.get_bone_global_pose(leg.ids[i + 1]).origin))
				support_error = maxf(support_error, 1 - absf(actual.dot(expected)))
			var rest: Transform3D = leg.rest.back()
			var rotation := tip.basis * rest.basis.inverse()
			var pitch := atan2(rotation.y.z, rotation.y.y)
			minimum_hock = minf(minimum_hock, -(hock - knee).slide(knee.direction_to(tip.origin)).z / float(leg.length))
			if not leg.swing and leg.phase > duty * .9:
				maximum_roll = maxf(maximum_roll, pitch)
			elif leg.swing:
				maximum_tuck = maxf(maximum_tuck, hip.direction_to(tip.origin).angle_to(hock.direction_to(tip.origin)))
		for arm in motion._limbs:
			if arm.role == "arm" and absf(arm.gait_leg.phase - duty) < .07:
				var shoulder := skeleton.get_bone_global_pose(arm.ids[0]).origin
				var wrist := skeleton.get_bone_global_pose(arm.ids.back()).origin
				var rest := skeleton.get_bone_global_rest(arm.ids.back()).origin - skeleton.get_bone_global_rest(arm.ids[0]).origin
				maximum_flex = maxf(maximum_flex, (wrist - shoulder - rest).y / float(arm.length))
	var cadence_error := absf(wrapf(float(legs[0].phase) - initial_phase, -.5, .5))
	print("  hoofed walk roll=", maximum_roll, " tuck=", maximum_tuck, " hock=", minimum_hock,
		" wrist lift=", maximum_flex, " cadence error=", cadence_error, " support error=", support_error)
	var flex_ok := maximum_flex > .015 and maximum_flex < .055 if bindings.poses.walk.has("arm_flex") else maximum_flex > .08
	return maximum_roll > .16 and maximum_tuck > .5 and minimum_hock > .03 and flex_ok and cadence_error < .0001 and support_error < .0001


func _check_multi_bend(runtime: Script) -> bool:
	var skeleton := Skeleton3D.new()
	root.add_child(skeleton)
	var positions := [Vector3.ZERO, Vector3(0, -.4, .18), Vector3(0, -.73, -.10), Vector3(0, -1.05, .06)]
	var ids: Array[int] = []
	var rests: Array[Transform3D] = []
	var lengths: Array[float] = []
	var total := 0.0
	for i in positions.size():
		skeleton.add_bone("joint_%d" % i)
		skeleton.set_bone_parent(i, i - 1)
		var segment: Vector3 = positions[i] - positions[i - 1] if i else Vector3.ZERO
		skeleton.set_bone_rest(i, Transform3D(Basis.IDENTITY, segment))
		skeleton.reset_bone_pose(i)
		ids.append(i)
		rests.append(skeleton.get_bone_global_rest(i))
		if i:
			lengths.append(segment.length())
			total += lengths.back()
	var motion := runtime.new() as SkeletonModifier3D
	skeleton.add_child(motion)
	var limb := {"ids": ids, "rest": rests, "lengths": lengths, "length": total}
	var failed := false
	for target in [Vector3(.12, -.79, .41), Vector3(-.12, -.80, -.31), Vector3(.2, -1.10, .04)]:
		for i in ids:
			skeleton.reset_bone_pose(i)
		motion._solve(skeleton, limb, target, false)
		var result: Array[Vector3] = []
		for i in ids:
			result.append(skeleton.get_bone_global_pose(i).origin)
		failed = failed or result.back().distance_to(target) > .005
		for i in range(1, positions.size() - 1):
			var before: Vector3 = positions[i - 1]
			var after: Vector3 = positions[i + 1]
			var authored: Vector3 = (positions[i] - before).slide(before.direction_to(after))
			var bend := (result[i] - result[i - 1]).slide(result[i - 1].direction_to(result[i + 1]))
			failed = failed or bend.dot(authored) <= 0
	print("three-segment chain preserved opposite authored bends while reaching: ", not failed)
	skeleton.free()
	return not failed
