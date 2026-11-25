extends SceneTree

const TOUCHDOWN := {"Hind.L": 0.0, "Fore.L": 0.50, "Hind.R": 0.75, "Fore.R": 0.25}
const DUTY := 0.80
const STRIDE := 1.04

func _initialize() -> void:
	call_deferred("check_bull")

func check_bull() -> void:
	var studio = load("res://studio.tscn").instantiate()
	root.add_child(studio)
	await process_frame
	studio.select_character(1)
	var sk: Skeleton3D = studio.model.find_children("*","Skeleton3D",true,false)[0]
	var skin: MeshInstance3D = studio.skin
	var soles := {}
	var peaks := {}
	var valid := sk.get_bone_count() == 28
	for feature in studio.SHAPES:
		var index := skin.find_blend_shape_by_name(feature)
		if index < 0:
			quit(1)
			return
		studio.sliders[feature].value = 0.5
		valid = valid and is_equal_approx(skin.get_blend_shape_value(index),0.5)
	studio.reset_shapes()
	for leg in TOUCHDOWN:
		soles[leg] = []
		peaks[leg] = 0.0
	for surface in skin.mesh.get_surface_count():
		var vertices: PackedVector3Array = skin.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
		for vertex in vertices:
			var p: Vector3 = sk.to_local(skin.to_global(vertex))
			if absf((sk.global_transform*p).y) < 0.00025:
				var leg := ("Fore" if p.z > 0 else "Hind") + (".L" if p.x > 0 else ".R")
				soles[leg].append(p)
	for leg in soles:
		if soles[leg].size() < 3:
			push_error("Missing neutral hoof sole for "+leg)
			quit(1)
			return

	var drift := 0.0
	var lowest := INF
	var travel := 0.0
	var start := Vector3.ZERO
	for clip in ["Idle","Walk"]:
		studio.play_motion(clip)
		var duration: float = studio.player.get_animation(clip).length
		for frame in range(353):
			var t := frame / 352.0
			var cycle := 2*t if clip == "Walk" else 0.0
			studio.player.seek(t*duration,true)
			sk.force_update_all_bone_transforms()
			if clip == "Walk":
				var pelvis := sk.global_transform * sk.get_bone_global_pose(sk.find_bone("Pelvis")).origin
				if frame == 0:
					start = pelvis
				if frame == 352:
					travel = pelvis.z-start.z
			for leg in soles:
				var phase := fposmod(cycle-TOUCHDOWN[leg],1.0)
				var bone := sk.find_bone("Foot."+leg)
				var transform := sk.get_bone_global_pose(bone)*sk.get_bone_global_rest(bone).affine_inverse()
				var clearance := INF
				for vertex in soles[leg]:
					var actual: Vector3 = sk.global_transform*(transform*vertex)
					var expected: Vector3 = sk.global_transform*vertex
					clearance = minf(clearance,actual.y)
					if clip == "Idle" or phase < DUTY:
						if clip == "Walk":
							expected.z += STRIDE*(cycle-phase+DUTY/2.0)
						drift = maxf(drift,actual.distance_to(expected))
				lowest = minf(lowest,clearance)
				peaks[leg] = maxf(peaks[leg],clearance)
	for peak in peaks.values():
		valid = valid and peak > 0.14
	studio.select_character(0)
	var biped: Skeleton3D = studio.model.find_children("*","Skeleton3D",true,false)[0]
	valid = valid and biped.get_bone_count() == 24
	print("Planted deviation ",drift,", lowest sole ",lowest,", clearances ",peaks,", forward travel ",travel)
	quit(0 if valid and drift < 0.001 and lowest > -0.002 and absf(travel-2*STRIDE) < 0.003 else 1)
