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
		_limbs.append(limb)
		if binding.role == "leg":
			legs.append(limb)
	_group_legs(legs)
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
	var leg_count := 0
	for limb in _limbs:
		if limb.role != "leg":
			continue
		leg_count += 1
		_step_foot(sk, limb, rule, delta, moving)
		var hip := sk.get_bone_global_pose(limb.ids[0]).origin
		var ankle: Vector3 = sk.to_local(limb.foot) - limb.sole
		var diff := hip - ankle
		var reach_length: float = limb.length * .995
		var available := sqrt(maxf(0, reach_length * reach_length - diff.x * diff.x - diff.z * diff.z))
		torso_drop = maxf(torso_drop, clampf(diff.y - available, 0, limb.length * .35))
	if leg_count > 0:
		var rest := sk.get_bone_rest(_hub)
		var parent := sk.get_bone_parent(_hub)
		var up := Vector3.UP if parent < 0 else sk.get_bone_global_pose(parent).basis.inverse() * Vector3.UP
		sk.set_bone_pose_position(_hub, rest.origin - up * torso_drop)
	elif moving:
		for i in _spine.size():
			var bone: int = _spine[i]
			sk.set_bone_pose_rotation(bone, sk.get_bone_rest(bone).basis.get_rotation_quaternion()
				* Quaternion(Vector3.UP, sin(_elapsed * 5 - i * .6) * .08))
	for limb in _limbs:
		if limb.role == "leg":
			_solve(sk, limb, sk.to_local(limb.foot) - limb.sole, true)
		elif limb.role == "arm":
			var tip: int = limb.ids.back()
			var rest_target := sk.get_bone_global_pose(tip).origin
			var phase := _elapsed / float(rule.period) + (.5 if limb.side < 0 else 0.0)
			var swing := sin(TAU * phase) * float(rule.arm_sweep) if moving else 0.0
			var clearance := .16 if moving and _humanoid else 0.0
			var target := rest_target + Vector3(limb.side * clearance, 0, swing) * float(limb.length)
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
	elif limb.swing or phase < previous:
		var plant := neutral + forward * _speed * (duty * .5 - phase) / frequency
		limb.foot = _ground(plant) if ground_relative else plant
		limb.swing = false


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
	if lengths.size() == 2:
		var length_a: float = lengths[0]
		var length_b: float = lengths[1]
		var reach_distance := clampf(root.distance_to(target), absf(length_a - length_b) + .00001, length_a + length_b - .00001)
		var bend := Vector3.FORWARD * -1 if _humanoid and grounded else positions[1] - root
		var pole := bend.slide(axis).normalized()
		if pole.is_zero_approx():
			pole = Vector3.RIGHT.slide(axis).normalized()
		if pole.is_zero_approx():
			pole = Vector3.UP.slide(axis).normalized()
		var along := (length_a * length_a - length_b * length_b + reach_distance * reach_distance) / (2 * reach_distance)
		positions[1] = root + axis * along + pole * sqrt(maxf(0, length_a * length_a - along * along))
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
	for i in lengths.size():
		var rest_a: Transform3D = rests[i]
		var rest_b: Transform3D = rests[i + 1]
		var from := frame * rest_a.origin.direction_to(rest_b.origin)
		var to := positions[i].direction_to(positions[i + 1])
		_orient(sk, ids[i], Basis(Quaternion(from.normalized(), to)) * frame * rest_a.basis)
	if grounded:
		var tip_rest: Transform3D = rests.back()
		_orient(sk, ids.back(), tip_rest.basis)


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
			return lerpf(float(a[1]), float(b[1]), f)
	return float(keys[-1][1])


static func _vec(v: Array) -> Vector3:
	return Vector3(v[0], v[1], v[2])
