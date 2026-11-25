extends SkeletonModifier3D

# The generator exports the contact schedule and the actual joints on this rig.
# Solve in skeleton coordinates (+Z forward) on the studio's level floor.
var player: AnimationPlayer
var profile: Dictionary
var legs: Array[Dictionary] = []
var spine: Array[int] = []
var root_bone := -1

static func profile_from_nodes(nodes: Array) -> Dictionary:
	for node in nodes:
		var encoded = node.get("extras",{}).get("ground_gait")
		if encoded is String:
			var data = JSON.parse_string(encoded)
			if data is Dictionary and data.has_all(["legs","cycles","stride","duty"]):
				if data.legs is Array and data.legs.size() <= 8 and (data.legs.size() or data.has("belly")):
					return data
	return {}

func configure(animation_player: AnimationPlayer, bindings: Dictionary) -> void:
	player = animation_player
	profile = bindings
	legs.clear()
	var sk := get_skeleton()
	spine.clear()
	if bindings.has("belly"):
		root_bone = sk.find_bone(bindings.belly.root)
		for joint in bindings.belly.spine:
			spine.append(sk.find_bone(joint))
	for binding in profile.legs:
		var leg: Dictionary = binding.duplicate()
		var ids: Array[int] = []
		for joint in leg.joints:
			ids.append(sk.find_bone(joint))
		leg.ids = ids
		var rest: Array[Transform3D] = []
		for id in ids:
			rest.append(sk.get_bone_global_rest(id))
		leg.rest = rest
		legs.append(leg)

func _process_modification() -> void:
	if player and player.current_animation == "Walk":
		pose_at(profile.cycles * player.current_animation_position / player.current_animation_length)

func pose_at(cycle: float) -> void:
	var sk := get_skeleton()
	var duty: float = profile.duty
	var stride: float = profile.stride
	if not spine.is_empty():
		var phase := TAU*cycle
		var root_rest := sk.get_bone_rest(root_bone)
		sk.set_bone_pose_position(root_bone,root_rest.origin + Vector3(profile.belly.sway*sin(phase),0,stride*cycle))
		for i in spine.size():
			var yaw: float = profile.belly.bend*sin(phase-profile.belly.lag*i)
			orient(sk,spine[i],Basis(Vector3.UP,yaw)*sk.get_bone_global_rest(spine[i]).basis)
	for leg in legs:
		var phase := fposmod(cycle-float(leg.touchdown),1.0)
		var swing := maxf(0,(phase-duty)/(1-duty))
		var blend := swing*swing*swing*(10-15*swing+6*swing*swing)
		var arc := pow(sin(PI*swing),2)
		var rock := cos(PI*swing)
		var forward := stride*(cycle-phase+duty/2+blend)
		forward += float(leg.get("step_in_place",0))*arc*(1+.35*rock)
		var ids: Array = leg.ids
		var rest: Array = leg.rest
		var tip: Transform3D = rest.back()
		var distal: Transform3D = rest[2]
		var angle := float(leg.get("distal_pitch",0))*arc
		if leg.get("distal_rock",false):
			angle *= rock
		var pitch := Basis(Vector3.RIGHT,angle)
		var target := tip.origin + Vector3(0,float(leg.lift)*arc,forward) - pitch*(tip.origin-distal.origin)
		var hip := sk.get_bone_global_pose(ids[0]).origin
		var upper: Vector3 = rest[1].origin-rest[0].origin
		var lower: Vector3 = distal.origin-rest[1].origin
		var axis := hip.direction_to(target)
		var reach := maxf(hip.distance_to(target),.00001)
		var along := (upper.length_squared()-lower.length_squared()+reach*reach)/(2*reach)
		var pole := (upper-axis*axis.dot(upper)).normalized()
		var knee := hip+axis*along+pole*sqrt(maxf(0,upper.length_squared()-along*along))
		orient(sk,ids[0],Basis(Quaternion(upper.normalized(),hip.direction_to(knee)))*rest[0].basis)
		orient(sk,ids[1],Basis(Quaternion(lower.normalized(),knee.direction_to(target)))*rest[1].basis)
		for j in range(2,ids.size()):
			var distal_basis := pitch
			if j == ids.size()-1:
				distal_basis = Basis(Vector3.RIGHT,float(leg.get("toe_pitch",0))*arc*rock)
			orient(sk,ids[j],distal_basis*rest[j].basis)

func orient(sk: Skeleton3D, id: int, basis: Basis) -> void:
	var parent := sk.get_bone_parent(id)
	var local := sk.get_bone_global_pose(parent).basis.inverse()*basis
	sk.set_bone_pose_rotation(id,local.orthonormalized().get_rotation_quaternion())
