## Bake procedural motion into AnimationPlayer clips and export GLB.
extends RefCounted

const Animator = preload("res://core/animator.gd")

const FPS := 30.0
const CLIPS := ["idle", "walk", "run", "roar", "wave", "hop"]


static func bake_all(creature: Node3D) -> Dictionary:
	var ap: AnimationPlayer = creature.get_node_or_null("AnimationPlayer")
	if ap == null:
		ap = AnimationPlayer.new()
		ap.name = "AnimationPlayer"
		creature.add_child(ap)
		ap.owner = creature
	var lib := AnimationLibrary.new()
	var out := {}
	for c in CLIPS:
		var anim := bake(creature, c)
		lib.add_animation(c, anim)
		out[c] = anim.length
	if ap.has_animation_library(""):
		ap.remove_animation_library("")
	ap.add_animation_library("", lib)
	var skel: Skeleton3D = creature.get_node("Skeleton")
	skel.reset_bone_poses()
	return out


static func bake(creature: Node3D, clip: String) -> Animation:
	var an = Animator.new(creature)
	var skel: Skeleton3D = creature.get_node("Skeleton")
	var length := 1.0
	var loop := true
	var frames := 0
	var dt := 1.0 / FPS
	match clip:
		"idle":
			an.play("idle")
			an.advance_to(Animator.IDLE_LOOP)
			length = Animator.IDLE_LOOP
		"walk", "run":
			an.play(clip)
			var cyc: float = an.cycle_length()
			if an.legs.is_empty():
				cyc = 1.0 / maxf(an.speed / maxf(an.rig["body_len"] * 0.6, 0.1) + 0.25, 0.05)
			frames = maxi(8, int(round(cyc * FPS)))
			dt = cyc / frames
			for i in frames * 3:
				an.step(dt)
			length = cyc
		_:
			an.play("idle")
			an.advance_to(Animator.IDLE_LOOP)
			an.play(clip)
			length = Animator.ACTIONS[clip]["length"]
			loop = false
	if frames == 0:
		frames = int(round(length * FPS))
		dt = length / frames
	var n := skel.get_bone_count()
	var pos_k := []
	var rot_k := []
	var scl_k := []
	for i in n:
		pos_k.append([]); rot_k.append([]); scl_k.append([])
	var count := frames if loop else frames + 1
	for f in count:
		for i in n:
			pos_k[i].append(skel.get_bone_pose_position(i))
			rot_k[i].append(skel.get_bone_pose_rotation(i))
			scl_k[i].append(skel.get_bone_pose_scale(i))
		an.step(dt)
	var anim := Animation.new()
	anim.length = length
	anim.loop_mode = Animation.LOOP_LINEAR if loop else Animation.LOOP_NONE
	for i in n:
		var path := NodePath("Skeleton:" + skel.get_bone_name(i))
		var rest_pos: Vector3 = skel.get_bone_rest(i).origin
		var moves := false
		var scales := false
		for f in count:
			if not moves and pos_k[i][f].distance_to(rest_pos) > 1e-4:
				moves = true
			if not scales and (scl_k[i][f] - Vector3.ONE).length() > 1e-3:
				scales = true
		var tr := anim.add_track(Animation.TYPE_ROTATION_3D)
		anim.track_set_path(tr, path)
		for f in count:
			anim.rotation_track_insert_key(tr, f * dt, rot_k[i][f])
		if moves:
			var tp := anim.add_track(Animation.TYPE_POSITION_3D)
			anim.track_set_path(tp, path)
			for f in count:
				anim.position_track_insert_key(tp, f * dt, pos_k[i][f])
		if scales:
			var ts := anim.add_track(Animation.TYPE_SCALE_3D)
			anim.track_set_path(ts, path)
			for f in count:
				anim.scale_track_insert_key(ts, f * dt, scl_k[i][f])
	return anim


static func export_glb(creature: Node3D, path: String) -> int:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_scene(creature, state)
	if err != OK:
		push_error("glTF append failed: %d" % err)
		return err
	return doc.write_to_filesystem(state, path)
