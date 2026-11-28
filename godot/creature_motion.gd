extends SkeletonModifier3D

## Attach below a Skeleton3D and configure from the exported motion JSON.
## The actor owns world travel. Report its forward speed through drive().
var ground_at: Callable
var _rules: Dictionary
var _limbs: Array[Dictionary] = []
var _parts: Array[Dictionary] = []
var _spine: Array[int] = []
var _managed: Dictionary = {}
var _hub := -1
var _humanoid := false
var _hoofed_biped := false
var _gait := "walk"
var _speed := 0.0
var _elapsed := 0.0
var _reach_targets: Dictionary = {}
var _part_amounts: Dictionary = {}
var _configured := false


func configure(bindings: Dictionary) -> bool:
	var sk := get_skeleton()
	_configured = false
	if sk == null or bindings.get("version") != 1 or not bindings.has_all(["poses", "hub", "spine", "limbs", "parts"]):
		return false
	_limbs.clear()
	_parts.clear()
	_spine.clear()
	_managed.clear()
	_reach_targets.clear()
	_part_amounts.clear()
	_elapsed = 0
	_speed = 0
	_rules = bindings.poses
	_humanoid = bindings.get("profile") == "humanoid"
	_hub = sk.find_bone(bindings.hub)
	if _hub < 0:
		return false
	for name in bindings.spine:
		var bone := sk.find_bone(name)
		if bone < 0:
			return false
		_spine.append(bone)
		_managed[bone] = true
	var legs: Array[Dictionary] = []
	for binding in bindings.limbs:
		var ids: Array[int] = []
		var rests: Array[Transform3D] = []
		var lengths: Array[float] = []
		var length := 0.0
		for name in binding.joints:
			var bone := sk.find_bone(name)
			if bone < 0 or (not ids.is_empty() and sk.get_bone_parent(bone) != ids.back()):
				return false
			var rest := sk.get_bone_global_rest(bone)
			if not rests.is_empty():
				var previous: Transform3D = rests.back()
				var span := previous.origin.distance_to(rest.origin)
				if span < .00001:
					return false
				lengths.append(span)
				length += span
			ids.append(bone)
			rests.append(rest)
			_managed[bone] = true
		if lengths.is_empty():
			return false
		var sole := _vec(binding.sole_per_length) * length
		var tip: Transform3D = rests.back()
		var limb: Dictionary = {"id": binding.id, "role": binding.role, "side": float(binding.side),
			"position": float(binding.body_position), "group": binding.group, "ids": ids, "rest": rests,
			"lengths": lengths, "length": length, "sole": sole, "neutral": tip.origin + sole,
			"phase": 0.0, "foot": _ground(sk.to_global(tip.origin + sole)), "swing": false,
			"lag": Vector3.ZERO, "velocity": Vector3.ZERO}
		var supports: Array[int] = []
		for name in binding.get("joint_support", []):
			var bone := sk.find_bone(name)
			var hinge := supports.size() + 1
			if bone < 0 or hinge >= ids.size() - 1 or sk.get_bone_parent(bone) != ids[hinge]:
				return false
			supports.append(bone)
			_managed[bone] = true
		limb.joint_support = supports
		var toe = binding.get("toe_per_length")
		if _humanoid and binding.role == "leg" and lengths.size() == 3 and binding.get("hoofed", false) and toe is Array and toe.size() == 3:
			limb.toe = _vec(toe) * length
			limb.pitch = 0.0
			limb.hock_angle = .44
		_limbs.append(limb)
		if binding.role == "leg":
			legs.append(limb)
	_group_legs(legs)
	_hoofed_biped = legs.size() == 2 and legs.all(func(leg): return leg.has("toe"))
	for limb in _limbs:
		if limb.role == "arm" and not legs.is_empty():
			var nearest := INF
			for leg in legs:
				var distance := absf(leg.position - limb.position)
				if leg.side * limb.side < 0:
					distance += 2
				if distance < nearest:
					nearest = distance
					limb.gait_leg = leg
	for binding in bindings.parts:
		var bone := sk.find_bone(binding.joint)
		if bone < 0:
			return false
		_managed[bone] = true
		var hinges: Array[Dictionary] = []
		for entry in binding.hinges:
			var id := sk.find_bone(entry.joint)
			if id < 0:
				return false
			_managed[id] = true
			var local_axis := sk.get_bone_global_rest(id).basis.inverse() * _vec(entry.axis)
			hinges.append({"bone": id, "axis": local_axis.normalized(), "degrees": float(entry.degrees)})
		_parts.append({"id": binding.id, "role": binding.role, "bone": bone, "hinges": hinges,
			"lag": Vector3.ZERO, "velocity": Vector3.ZERO})
	_configured = true
	return true


func _group_legs(legs: Array[Dictionary]) -> void:
	legs.sort_custom(func(a, b): return a.length < b.length)
	var lengths: Array[float] = []
	var pair_order := {}
	var by_position := legs.duplicate()
	by_position.sort_custom(func(a, b): return a.position < b.position)
	for leg in by_position:
		if not pair_order.has(leg.group):
			pair_order[leg.group] = pair_order.size()
	for leg in legs:
		if lengths.is_empty() or leg.length > float(lengths.back()) * 1.25:
			lengths.append(leg.length)
		leg.group_length = lengths.back()
		var group_index: int = pair_order[leg.group]
		var phase := (.25 if group_index % 2 else 0.0) + (.5 if leg.side < 0 else 0.0)
		leg.phase = phase


func drive(gait: String, forward_speed: float) -> void:
	if gait in ["walk", "run"]:
		_gait = gait
	_speed = forward_speed


func reach(limb_id: String, world_target: Vector3) -> void:
	var weight: float = _reach_targets.get(limb_id, {}).get("weight", 0.0)
	_reach_targets[limb_id] = {"target": world_target, "weight": weight, "active": true}


func reach_pose(limb_id: String) -> bool:
	var sk := get_skeleton()
	for limb in _limbs:
		if limb.id == limb_id and limb.role == "arm":
			var target := _vec(_rules.reach.fallback_local) * float(limb.length)
			target.x *= float(limb.side)
			reach(limb_id, sk.to_global(sk.get_bone_global_pose(limb.ids[0]).origin + target))
			return true
	return false


func release(limb_id: String) -> void:
	if _reach_targets.has(limb_id):
		_reach_targets[limb_id].active = false


func set_part_amount(part_id: String, amount: float) -> void:
	_part_amounts[part_id] = clampf(amount, 0, 1)


func _process_modification() -> void:
	advance(get_process_delta_time())


func advance(delta: float) -> void:
	if not _configured or delta <= 0:
		return
	var sk := get_skeleton()
	var rule: Dictionary = _rules[_gait]
	var moving := absf(_speed) > .0001
	_elapsed += delta
	for i in _managed:
		sk.reset_bone_pose(i)
	var torso_drop := 0.0
	var pelvis_lift := 0.0
	var leg_count := 0
	var hoofed_walk := moving and _hoofed_biped and _gait == "walk"
	for limb in _limbs:
		if limb.role != "leg":
			continue
		leg_count += 1
		_step_foot(sk, limb, rule, delta, moving)
		if leg_count == 1 and hoofed_walk:
			var phase := float(limb.phase) - float(rule.get("pelvis_dip_delay", 0.0))
			var dip := float(rule.get("pelvis_dip", .026)) * (.5 + .5 * cos(2 * TAU * phase))
			pelvis_lift = (.06 - dip) * float(limb.length)
		var hip := sk.get_bone_global_pose(limb.ids[0]).origin + Vector3.UP * pelvis_lift
		var ankle := _ankle_target(sk, limb)
		var diff := hip - ankle
		var reach_length: float = limb.length * .995
		if hoofed_walk:
			reach_length = .995 * (_hoof_upper_reach(limb.lengths) + float(limb.lengths[2]))
		var available := sqrt(maxf(0, reach_length * reach_length - diff.x * diff.x - diff.z * diff.z))
		var required_drop := minf(diff.y - available, limb.length * .35)
		var margin := .025 * float(limb.length) if hoofed_walk else 0.0
		var blend := maxf(0, 1 - absf(torso_drop - required_drop) / margin) if margin > 0 else 0.0
		torso_drop = maxf(torso_drop, required_drop) + .25 * margin * blend * blend
	if leg_count > 0:
		var rest := sk.get_bone_rest(_hub)
		var parent := sk.get_bone_parent(_hub)
		var up := Vector3.UP if parent < 0 else sk.get_bone_global_pose(parent).basis.inverse() * Vector3.UP
		sk.set_bone_pose_position(_hub, rest.origin + up * (pelvis_lift - torso_drop))
	elif moving:
		for i in _spine.size():
			var bone: int = _spine[i]
			sk.set_bone_pose_rotation(bone, sk.get_bone_rest(bone).basis.get_rotation_quaternion()
				* Quaternion(Vector3.UP, sin(_elapsed * 5 - i * .6) * .08))
	for limb in _limbs:
		if limb.role == "leg":
			_solve(sk, limb, _ankle_target(sk, limb), true)
		elif limb.role == "arm":
			var tip: int = limb.ids.back()
			var rest_target := sk.get_bone_global_pose(tip).origin
			var phase := _elapsed / float(rule.period) + (.5 if limb.side < 0 else 0.0)
			var sweep := sin(TAU * phase)
			if limb.has("gait_leg"):
				var leg: Dictionary = limb.gait_leg
				var duty: float = rule.duty
				var progress: float = leg.phase / duty if leg.phase < duty else 1 + (leg.phase - duty) / (1 - duty)
				var side_sign := -1.0 if leg.side * limb.side < 0 else 1.0
				sweep = -cos(PI * progress) * side_sign * signf(_speed)
			var swing := sweep * float(rule.arm_sweep) if moving else 0.0
			var clearance := float(rule.get("arm_clearance", .16)) if moving and _humanoid else 0.0
			var flex := float(rule.get("arm_flex", .13)) * maxf(sweep, 0) if moving and _hoofed_biped else 0.0
			var target := rest_target + Vector3(limb.side * clearance, flex, swing) * float(limb.length)
			if _reach_targets.has(limb.id):
				var reach_state: Dictionary = _reach_targets[limb.id]
				var duration := maxf(.001, float(_rules.reach.get("transition_seconds", .20)))
				reach_state.weight = move_toward(reach_state.weight, 1.0 if reach_state.active else 0.0, delta / duration)
				target = target.lerp(sk.to_local(reach_state.target), smoothstep(0, 1, reach_state.weight))
				if not reach_state.active and reach_state.weight <= 0:
					_reach_targets.erase(limb.id)
			_solve(sk, limb, target, false)
		else:
			_secondary(sk, limb, delta)
	for part in _parts:
		_pose_part(sk, part, delta)


func _step_foot(sk: Skeleton3D, limb: Dictionary, rule: Dictionary, delta: float, moving: bool) -> void:
	var ground_relative: bool = rule.ground_relative
	var neutral := sk.to_global(limb.neutral)
	if ground_relative:
		neutral = _ground(neutral)
	if not moving:
		limb.foot = limb.foot.lerp(neutral, minf(1, 9 * delta))
		limb.swing = false
		if limb.has("toe"):
			limb.pitch = move_toward(limb.pitch, 0.0, 4.0 * delta)
			limb.hock_angle = move_toward(limb.hock_angle, .44, 4.0 * delta)
		return
	var duty: float = rule.duty
	var group_length: float = limb.group_length
	var stride := float(rule.stride) * group_length * sk.global_basis.z.length()
	var frequency := maxf(1 / float(rule.period), absf(_speed) * duty / stride)
	var previous: float = limb.phase
	var phase := fposmod(previous + frequency * delta, 1)
	limb.phase = phase
	var forward := sk.global_basis.z.normalized()
	if phase >= duty:
		if not limb.swing:
			limb.lift = limb.foot
			limb.swing = true
		var t := (phase - duty) / (1 - duty)
		var time_ahead := (1 - phase + duty * .5) / frequency
		var landing := neutral + forward * _speed * time_ahead
		if ground_relative:
			landing = _ground(landing)
		var lift_height := _sample(rule.lift, t) * float(limb.length) * sk.global_basis.y.length()
		limb.foot = limb.lift.lerp(landing, smoothstep(0, 1, t)) + Vector3.UP * lift_height
		if limb.has("toe"):
			var tuck := sin(PI * t)
			limb.hock_angle = .44 + .15 * (smoothstep(0, 1, tuck) if _gait == "walk" else tuck)
			limb.pitch = .24 * (1 - smoothstep(0, .66, t)) + .36 * tuck * tuck * (1 - t) if _gait == "walk" else 0.0
	elif limb.swing or phase < previous:
		var plant := neutral + forward * _speed * (duty * .5 - phase) / frequency
		limb.foot = _ground(plant) if ground_relative else plant
		limb.swing = false
	if phase < duty and limb.has("toe"):
		limb.hock_angle = .44
		limb.pitch = .24 * smoothstep(.86, 1, phase / duty) if _gait == "walk" else 0.0


func _ankle_target(sk: Skeleton3D, limb: Dictionary) -> Vector3:
	var sole: Vector3 = limb.sole
	if limb.has("toe"):
		# Keep the toe over its flat-pose position as the heel rises.
		var toe: Vector3 = limb.toe
		sole += Basis(Vector3.RIGHT, limb.pitch) * toe - toe
	return sk.to_local(limb.foot) - sole


func _hoof_upper_reach(lengths: Array) -> float:
	var a: float = lengths[0]
	var b: float = lengths[1]
	var reserve := float(_rules[_gait].get("knee_reserve", 0.0))
	return sqrt(a * a + b * b + 2 * a * b * cos(reserve)) if reserve > 0 else a + b - .00001


func _solve(sk: Skeleton3D, limb: Dictionary, target: Vector3, grounded: bool) -> void:
	var ids: Array = limb.ids
	var rests: Array = limb.rest
	var lengths: Array = limb.lengths
	var positions: Array[Vector3] = []
	var root := sk.get_bone_global_pose(ids[0]).origin
	var parent := sk.get_bone_parent(ids[0])
	var frame := Basis.IDENTITY if parent < 0 else sk.get_bone_global_pose(parent).basis * sk.get_bone_global_rest(parent).basis.inverse()
	var first: Transform3D = rests[0]
	for rest in rests:
		positions.append(root + frame * (rest.origin - first.origin))
	var axis := (target - root).normalized()
	if axis.is_zero_approx():
		axis = (positions.back() - root).normalized()
	if lengths.size() == 1:
		positions[1] = root + axis * float(lengths[0])
	elif grounded and limb.has("toe"):
		var forward := frame * Vector3.BACK
		var hock_length: float = lengths[2]
		var upper_max := _hoof_upper_reach(lengths)
		var upper_min := absf(lengths[0] - lengths[1]) + .00001
		var min_reach := maxf(hock_length - upper_max, upper_min - hock_length)
		var distance := clampf(root.distance_to(target), maxf(.00001, min_reach), upper_max + hock_length)
		# Bound the hock angle so the two upper segments can reach the hock.
		var squares := distance * distance + hock_length * hock_length
		var divisor := 2 * distance * hock_length
		var min_angle := acos(clampf((squares - upper_min * upper_min) / divisor, -1, 1))
		var max_angle := acos(clampf((squares - upper_max * upper_max) / divisor, -1, 1))
		var angle := clampf(limb.hock_angle, min_angle, max_angle)
		if _gait == "walk":
			var blend := maxf(0.0, 1 - absf(float(limb.hock_angle) - max_angle) / .10)
			angle = maxf(min_angle, angle - .025 * blend * blend)
		var distal := axis * cos(angle) + _bend_pole(axis, forward) * sin(angle)
		positions[3] = root + axis * distance
		positions[2] = positions[3] - distal * hock_length
		positions[1] = _two_bone_knee(root, root.direction_to(positions[2]), root.distance_to(positions[2]), lengths[0], lengths[1], forward)
	elif lengths.size() == 2:
		var length_a: float = lengths[0]
		var length_b: float = lengths[1]
		var reach_distance := clampf(root.distance_to(target), absf(length_a - length_b) + .00001, length_a + length_b - .00001)
		var rest_axis := positions[-1] - root
		var bend := (frame * Vector3.BACK) if _humanoid and grounded else (positions[1] - root).slide(rest_axis.normalized())
		positions[1] = _two_bone_knee(root, axis, reach_distance, length_a, length_b, bend)
		positions[2] = root + axis * reach_distance
	elif root.distance_to(target) >= float(limb.length):
		for i in lengths.size():
			positions[i + 1] = positions[i] + axis * float(lengths[i])
	else:
		for _iteration in 18:
			positions[-1] = target
			for i in range(lengths.size() - 1, -1, -1):
				positions[i] = positions[i + 1] + positions[i + 1].direction_to(positions[i]) * float(lengths[i])
			positions[0] = root
			for i in lengths.size():
				positions[i + 1] = positions[i] + positions[i].direction_to(positions[i + 1]) * float(lengths[i])
			if positions[-1].distance_squared_to(target) < .0000005:
				break
		# Restore inverted bends around each joint's neighbor-to-neighbor axis.
		# Moving on this circle keeps both segment lengths and the tip target.
		for i in range(1, positions.size() - 1):
			var before: Vector3 = rests[i - 1].origin
			var joint: Vector3 = rests[i].origin
			var after: Vector3 = rests[i + 1].origin
			var authored := (joint - before).slide(before.direction_to(after))
			var chord := positions[i + 1] - positions[i - 1]
			if chord.is_zero_approx() or authored.is_zero_approx():
				continue
			var tangent := chord.normalized()
			var offset := positions[i] - positions[i - 1]
			var radial := offset.slide(tangent)
			var pole := (frame * authored).slide(tangent)
			if radial.dot(pole) < 0:
				positions[i] = positions[i - 1] + tangent * offset.dot(tangent) + pole.normalized() * radial.length()
	for i in lengths.size():
		var rest_a: Transform3D = rests[i]
		var rest_b: Transform3D = rests[i + 1]
		var from := frame * rest_a.origin.direction_to(rest_b.origin)
		var to := positions[i].direction_to(positions[i + 1])
		_orient(sk, ids[i], Basis(Quaternion(from.normalized(), to)) * frame * rest_a.basis)
	if grounded:
		var tip_rest: Transform3D = rests.back()
		var pitch := Basis(Vector3.RIGHT, limb.pitch) if limb.has("toe") else Basis.IDENTITY
		_orient(sk, ids.back(), pitch * tip_rest.basis)
	var supports: Array = limb.get("joint_support", [])
	for i in supports.size():
		var proximal: Transform3D = rests[i]
		var distal: Transform3D = rests[i + 1]
		var incoming := sk.get_bone_global_pose(ids[i]).basis * proximal.basis.inverse()
		var outgoing := sk.get_bone_global_pose(ids[i + 1]).basis * distal.basis.inverse()
		var midway := incoming.get_rotation_quaternion().slerp(outgoing.get_rotation_quaternion(), .5)
		_orient(sk, supports[i], Basis(midway) * sk.get_bone_global_rest(supports[i]).basis)


static func _bend_pole(axis: Vector3, bend: Vector3) -> Vector3:
	var pole := bend.slide(axis).normalized()
	if pole.is_zero_approx():
		pole = Vector3.RIGHT.slide(axis).normalized()
	if pole.is_zero_approx():
		pole = Vector3.UP.slide(axis).normalized()
	return pole


static func _two_bone_knee(root: Vector3, axis: Vector3, distance: float, a: float, b: float, bend: Vector3) -> Vector3:
	var along := (a * a - b * b + distance * distance) / (2 * distance)
	return root + axis * along + _bend_pole(axis, bend) * sqrt(maxf(0, a * a - along * along))


func _secondary(sk: Skeleton3D, limb: Dictionary, delta: float) -> void:
	var target := Vector3(-limb.side * absf(_speed), sin(_elapsed * 7) * absf(_speed) * .6, 0)
	var lag := _spring(limb, target, delta)
	for i in limb.ids.size():
		var bone: int = limb.ids[i]
		var weight: float = 1.0 / (i + 1)
		var rotation := Basis.from_euler(lag * weight).get_rotation_quaternion()
		sk.set_bone_pose_rotation(bone, sk.get_bone_rest(bone).basis.get_rotation_quaternion() * rotation)


func _spring(state: Dictionary, target: Vector3, delta: float) -> Vector3:
	var settings: Dictionary = _rules.secondary
	var lag: Vector3 = state.lag
	var velocity: Vector3 = state.velocity
	target *= float(settings.drag)
	target = target.limit_length(float(settings.max_deflection))
	var steps := maxi(1, ceili(delta / .02))
	var dt := delta / steps
	for _step in steps:
		velocity += ((target - lag) * float(settings.spring) - velocity * float(settings.damping)) * dt
		lag += velocity * dt
	state.lag = lag
	state.velocity = velocity
	return lag


func _pose_part(sk: Skeleton3D, part: Dictionary, delta: float) -> void:
	var amount := float(_part_amounts.get(part.id, 0))
	for hinge in part.hinges:
		var bone: int = hinge.bone
		var rotation := Quaternion(hinge.axis, deg_to_rad(float(hinge.degrees)) * amount)
		sk.set_bone_pose_rotation(bone, sk.get_bone_rest(bone).basis.get_rotation_quaternion() * rotation)
	if part.role == "look" and amount > 0:
		sk.set_bone_pose_scale(part.bone, Vector3(1, 1 - amount * .88, 1))
	if part.role in ["sway", "flop", "flap"]:
		var bone: int = part.bone
		var target := Vector3(sin(_elapsed * 7) * absf(_speed), 0, amount * 2)
		var lag := _spring(part, target, delta)
		sk.set_bone_pose_rotation(bone, sk.get_bone_rest(bone).basis.get_rotation_quaternion()
			* Basis.from_euler(lag).get_rotation_quaternion())


func _ground(point: Vector3) -> Vector3:
	var height := float(ground_at.call(point)) if ground_at.is_valid() else global_position.y
	return Vector3(point.x, height, point.z)


func _orient(sk: Skeleton3D, bone: int, basis: Basis) -> void:
	var parent := sk.get_bone_parent(bone)
	var local := basis if parent < 0 else sk.get_bone_global_pose(parent).basis.inverse() * basis
	sk.set_bone_pose_rotation(bone, local.orthonormalized().get_rotation_quaternion())


static func _sample(keys: Array, t: float) -> float:
	for i in range(1, keys.size()):
		if t <= float(keys[i][0]):
			var a: Array = keys[i - 1]
			var b: Array = keys[i]
			var f := inverse_lerp(float(a[0]), float(b[0]), t)
			if a.size() == 3 and b.size() == 3:
				var width := float(b[0]) - float(a[0])
				return (lerpf(float(a[1]), float(b[1]), smoothstep(0, 1, f))
					+ width * f * (1 - f) * ((1 - f) * float(a[2]) - f * float(b[2])))
			return lerpf(float(a[1]), float(b[1]), f)
	return float(keys[-1][1])


static func _vec(v: Array) -> Vector3:
	return Vector3(v[0], v[1], v[2])
