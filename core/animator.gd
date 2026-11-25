## Procedural animator in the spirit of Spore (Hecker et al. 2008).
##
## Everything is derived from the rig the builder produced:
##   * legs plan world-space footprints and swing between them; FABRIK IK bends them
##   * the body is carried by the legs (bob, sway, lean); with no legs it slithers
##   * neck/head and tail chains get look-around, wag and follow-through
##   * parts animate by capability: eyes look and blink, jaws open, ears flop,
##     wings flap, antennae sway
##   * actions (roar, wave, hop) are written against roles, not bones, so any
##     creature can play them; missing roles are skipped
##
## The animator owns `world` (the creature's transform in the world). Bone
## poses are written in skeleton space, so recording them yields in-place clips.
extends RefCounted

const IDLE_LOOP := 6.0
const ACTIONS := {
	"roar": {"length": 2.4, "tracks": {
		"head_pitch": [[0, 0], [0.5, -26], [1.8, -30], [2.4, 0]],
		"mouth": [[0, 0], [0.45, 1], [1.9, 1], [2.3, 0]],
		"crouch": [[0, 0], [0.35, 0.07], [0.6, -0.03], [1.9, -0.03], [2.4, 0]],
		"arms_up": [[0, 0], [0.5, 1], [1.8, 1], [2.4, 0]],
		"shake": [[0, 0], [0.6, 1], [1.7, 1], [2.0, 0]],
		"flap": [[0, 0], [0.5, 1], [1.8, 1], [2.4, 0]],
	}},
	"wave": {"length": 2.6, "tracks": {
		"wave": [[0, 0], [0.5, 1], [2.1, 1], [2.6, 0]],
		"head_tilt": [[0, 0], [0.5, 12], [2.1, 12], [2.6, 0]],
		"mouth": [[0, 0], [0.5, 0.35], [2.1, 0.35], [2.6, 0]],
	}},
	"hop": {"length": 1.5, "tracks": {
		"crouch": [[0, 0], [0.35, 0.14], [0.48, 0.14], [0.6, -0.02], [1.05, 0.1], [1.25, 0.0], [1.5, 0]],
		"jump": [[0, 0], [0.5, 0], [0.78, 1], [1.05, 0], [1.5, 0]],
		"head_pitch": [[0, 0], [0.4, 10], [0.7, -12], [1.1, 6], [1.5, 0]],
		"flap": [[0, 0], [0.5, 0], [0.6, 1], [1.0, 1], [1.2, 0]],
	}},
}

var creature: Node3D
var skel: Skeleton3D
var rig: Dictionary
var rest: Array
var parents: PackedInt32Array
var G: Array[Transform3D] = []
var set_flag: PackedByteArray

var world := Transform3D.IDENTITY
var time := 0.0
var otime := 0.0   # oscillator clock: real time when idle, gait-locked when moving
var speed := 0.0
var turn := 0.0
var target_speed := 0.0
var target_turn := 0.0
var clip := "idle"
var action := ""
var action_t := 0.0
var look_point = null     # optional world-space Vector3

var legs: Array = []
var arms: Array = []
var apps: Array = []
var leg_len := 0.5
var walk_speed := 0.5
var run_speed := 1.2
var gait_clock := 0.0
var gait_freq := 1.0
var stride_cap := 1.0
var stride_walk := 0.5
var stride_run := 0.8
var duty := 0.6
var profile := "walk"
var slither_phase := 0.0
var bob := 0.0
var bob_vel := 0.0
var prev_bob := 0.0
var hop_lift := 0.0


func _init(c: Node3D) -> void:
	creature = c
	skel = c.get_node("Skeleton")
	rig = c.get_meta("rig")
	rest = rig["rest"]
	parents = rig["parents"]
	G.resize(rest.size())
	set_flag.resize(rest.size())
	leg_len = maxf(rig["leg_len"], 0.05)
	for l in rig["limbs"]:
		var st := {
			"l": l, "bones": l["bones"], "rest_j": l["joints"].duplicate(), "lengths": [],
			"side": l["side"], "u": l["u"], "sole_local": l["sole_local"],
			"plant": Vector3.ZERO, "swinging": false, "swing_t": 0.0, "swing_dur": 0.3, "lift": Vector3.ZERO,
			"phase": 0.0, "prev_phase": 0.0, "offset": 0.0, "foot": Vector3.ZERO, "lift_h": 0.1,
		}
		var j: Array = l["joints"]
		var total := 0.0
		for k in range(1, j.size()):
			var d: float = j[k].distance_to(j[k - 1])
			st["lengths"].append(d)
			total += d
		st["length"] = total
		match l["role"]:
			"leg": legs.append(st)
			"arm": arms.append(st)
			_: apps.append(st)
	_setup_gait()
	reset()


func _setup_gait() -> void:
	var n := legs.size()
	if n == 0:
		walk_speed = clampf(rig["body_len"] * 0.35, 0.2, 2.0)
		run_speed = walk_speed * 2.2
		return
	# Group mirror pairs (same uid) and sort rear -> front.
	var groups := {}
	for st in legs:
		var uid: String = st["l"]["uid"]
		if not groups.has(uid):
			groups[uid] = []
		groups[uid].append(st)
	var keys := groups.keys()
	keys.sort_custom(func(a, b): return groups[a][0]["u"] < groups[b][0]["u"])
	var P := keys.size()
	for gi in P:
		for st in groups[keys[gi]]:
			var left: bool = st["side"] >= 0.0
			var center: bool = st["side"] == 0.0
			var off := 0.0
			if n == 1:
				off = 0.0
			elif P == 1:
				off = 0.0 if left else 0.5
			elif P == 2:
				off = (0.0 if left else 0.5) + (0.25 if gi == 1 else 0.0)
			else:
				off = fposmod(float(gi % 2) * 0.5 + gi * 0.06 + (0.0 if left else 0.5), 1.0)
			if center and n > 1:
				off = fposmod(gi * 0.5 + 0.25, 1.0)
			st["offset"] = off
			st["walk_offset"] = off
			# Trot for quadrupeds when running.
			st["run_offset"] = fposmod((0.0 if left else 0.5) + (0.5 if (P == 2 and gi == 1) else 0.0), 1.0) if P == 2 else off
	var L := leg_len
	stride_cap = _stride_cap()
	stride_walk = minf(0.6 * L, stride_cap)
	stride_run = minf(0.95 * L, stride_cap * 1.05)
	walk_speed = stride_walk * _freq_for("walk") / _duty_for("walk")
	run_speed = stride_run * _freq_for("run") / _duty_for("run")


## Longest stance stride every leg can follow from its rest footprint without
## overreaching (allowing the body to sink a little).
func _stride_cap() -> float:
	var half := INF
	for st in legs:
		var rj: Array = st["rest_j"]
		var hip: Vector3 = rj[0] - Vector3(0, 0.1 * leg_len, 0)
		var v: Vector3 = rj[rj.size() - 1] - hip
		var R: float = 0.94 * st["length"]
		var disc := v.z * v.z - (v.length_squared() - R * R)
		if disc <= 0.0:
			half = minf(half, 0.02)
			continue
		half = minf(half, minf(-v.z + sqrt(disc), v.z + sqrt(disc)))
	return 2.0 * maxf(half, 0.02) * 0.9


func _duty_for(p: String) -> float:
	var n := legs.size()
	var pairs := 0
	for st in legs:
		if st["side"] >= 0.0:
			pairs += 1
	if n == 1:
		return 0.45 if p == "walk" else 0.35
	if p == "run":
		return 0.38 if n == 2 else (0.42 if n <= 4 else 0.45)
	return 0.6 if n == 2 else (0.65 if n <= 4 else 0.55)


func _freq_for(p: String) -> float:
	var s := 1.1 if p == "walk" else 1.75
	if legs.size() == 1:
		s *= 0.9
	return s / sqrt(leg_len)


## Put every foot on its rest footprint under the current world transform.
func reset() -> void:
	time = 0.0
	otime = 0.0
	gait_clock = 0.0
	for st in legs:
		st["plant"] = _ground(world * (st["rest_j"][st["rest_j"].size() - 1] + st["sole_local"]))
		st["foot"] = st["plant"]
		st["swinging"] = false
		st["phase"] = st["offset"]
		st["prev_phase"] = st["offset"]
	_pose()


static func _ground(p: Vector3) -> Vector3:
	return Vector3(p.x, 0.0, p.z)


func play(name: String) -> void:
	if ACTIONS.has(name):
		action = name
		action_t = 0.0
		return
	clip = name
	match name:
		"walk":
			target_speed = walk_speed
			speed = walk_speed
			profile = "walk"
		"run":
			target_speed = run_speed
			speed = run_speed
			profile = "run"
		_:
			target_speed = 0.0
	_apply_profile()
	if name in ["walk", "run"]:
		_prime_gait()


## Start a gait in its steady state: stance feet spread along the stride and
## swinging feet mid-air, as if the creature had already been walking.
func _prime_gait() -> void:
	if legs.is_empty():
		return
	gait_freq = _freq_for(profile)
	var stride := speed * duty / gait_freq
	var fwd := world.basis.z
	for st in legs:
		var p: float = fposmod(gait_clock + st["offset"], 1.0)
		st["phase"] = p
		st["prev_phase"] = p
		var rest_fp := _rest_footprint(st, 0.0)
		if p < duty:
			st["swinging"] = false
			st["plant"] = rest_fp + fwd * stride * (0.5 - p / duty)
			st["foot"] = st["plant"]
		else:
			var s := (p - duty) / (1.0 - duty)
			st["swinging"] = true
			st["swing_dur"] = (1.0 - duty) / gait_freq
			st["swing_t"] = s
			st["lift_h"] = leg_len * (0.12 if profile == "walk" else 0.18)
			st["lift"] = rest_fp + fwd * (-0.5 * stride - speed * s * st["swing_dur"])
			st["plant"] = st["lift"]
	_pose()


func _apply_profile() -> void:
	duty = _duty_for(profile)
	for st in legs:
		st["offset"] = st.get(profile + "_offset", st["offset"])


## Live control (test drive). forward in [-1, 1] (scaled to walk/run), turn in rad/s.
func drive(forward: float, turn_rate: float, running: bool) -> void:
	var top := run_speed if running else walk_speed
	target_speed = forward * top
	target_turn = turn_rate
	var want := "run" if running and forward > 0.5 else "walk"
	if want != profile:
		profile = want
		_apply_profile()


func advance_to(t: float, dt := 1.0 / 30.0) -> void:
	while time < t - 1e-6:
		step(minf(dt, t - time))


func cycle_length() -> float:
	return 1.0 / maxf(_freq_for(profile), 0.01)


# ---------------------------------------------------------------- update

func step(dt: float) -> void:
	time += dt
	speed = move_toward(speed, target_speed, dt * maxf(walk_speed, 0.3) * 3.0)
	turn = move_toward(turn, target_turn, dt * 4.0)
	var yaw := turn * dt
	world.basis = world.basis * Basis(Vector3.UP, yaw)
	world.origin += world.basis.z * speed * dt
	if action != "":
		action_t += dt
		if action_t > ACTIONS[action]["length"]:
			action = ""
	_gait(dt)
	var idle_w := clampf(1.0 - absf(speed) / maxf(walk_speed, 0.01) * 1.5, 0.0, 1.0)
	otime += dt * lerpf(gait_freq * IDLE_LOOP if not legs.is_empty() else 1.0, 1.0, idle_w)
	_pose()


func _moving() -> bool:
	return absf(speed) > 0.02 or absf(turn) > 0.05


func _gait(dt: float) -> void:
	if legs.is_empty():
		slither_phase += (absf(speed) / maxf(rig["body_len"] * 0.6, 0.1) + (0.25 if _moving() else 0.0)) * dt
		return
	var f := _freq_for(profile)
	var ref := walk_speed if profile == "walk" else run_speed
	gait_freq = maxf(f * clampf(absf(speed) / maxf(ref, 0.01), 0.0, 1.6), 0.6 * f)
	if _moving():
		gait_clock += gait_freq * dt
	for st in legs:
		var ph := fposmod(gait_clock + st["offset"], 1.0)
		var prev: float = st["prev_phase"]
		st["phase"] = ph
		st["prev_phase"] = ph
		var crossed := (prev < duty and ph >= duty) or (ph < prev and (prev < duty or ph >= duty))
		var rest_target := _rest_footprint(st, 0.0)
		if not st["swinging"]:
			var drift: float = st["plant"].distance_to(rest_target)
			var lift := false
			if _moving() and crossed:
				lift = true
			elif not _moving() and drift > 0.12 * leg_len and not _neighbor_swinging(st):
				lift = true
			if lift:
				st["swinging"] = true
				st["swing_t"] = 0.0
				st["swing_dur"] = (1.0 - duty) / gait_freq if _moving() else 0.22 * sqrt(leg_len)
				st["lift"] = st["plant"]
				st["lift_h"] = leg_len * (0.12 if profile == "walk" else 0.18)
		if st["swinging"]:
			st["swing_t"] += dt / st["swing_dur"]
			var s: float = clampf(st["swing_t"], 0.0, 1.0)
			var remaining: float = (1.0 - s) * st["swing_dur"]
			var ahead := remaining + (duty / gait_freq * 0.5 if _moving() else 0.0)
			var target := _rest_footprint(st, ahead)
			var e := s * s * (3.0 - 2.0 * s)
			st["foot"] = st["lift"].lerp(target, e) + Vector3.UP * st["lift_h"] * sin(PI * s)
			if s >= 1.0:
				st["swinging"] = false
				st["plant"] = target
				st["foot"] = target
		else:
			st["foot"] = st["plant"]


func _neighbor_swinging(st: Dictionary) -> bool:
	for o in legs:
		if o != st and o["swinging"] and o["l"]["uid"] == st["l"]["uid"]:
			return true
	var count := 0
	for o in legs:
		if o["swinging"]:
			count += 1
	return count >= maxi(1, legs.size() / 2)


## Where the foot would rest `ahead` seconds from now if the body keeps moving.
func _rest_footprint(st: Dictionary, ahead: float) -> Vector3:
	var yaw := turn * ahead
	var fut := world
	fut.basis = world.basis * Basis(Vector3.UP, yaw)
	fut.origin += world.basis.z * speed * ahead
	var rj: Array = st["rest_j"]
	return _ground(fut * (rj[rj.size() - 1] + st["sole_local"]))


# ---------------------------------------------------------------- tracks

func _track(name: String) -> float:
	if action == "":
		return 0.0
	var tr: Dictionary = ACTIONS[action]["tracks"]
	if not tr.has(name):
		return 0.0
	var keys: Array = tr[name]
	var t := action_t
	if t <= keys[0][0]:
		return keys[0][1]
	for i in range(1, keys.size()):
		if t <= keys[i][0]:
			var a: Array = keys[i - 1]
			var b: Array = keys[i]
			var f: float = (t - a[0]) / maxf(b[0] - a[0], 1e-4)
			f = f * f * (3.0 - 2.0 * f)
			return lerpf(a[1], b[1], f)
	return keys[keys.size() - 1][1]


func _osc(n: float, phase := 0.0) -> float:
	return sin(TAU * n * otime / IDLE_LOOP + phase)


# ------------------------------------------------------------------ pose

func _rest_rel(i: int) -> Vector3:
	var p := parents[i]
	return rest[i] - (rest[p] if p >= 0 else Vector3.ZERO)


func _carry(i: int, rot := Basis()) -> Transform3D:
	var p := parents[i]
	var gp: Transform3D = G[p] if p >= 0 else Transform3D.IDENTITY
	return Transform3D(gp.basis * rot, gp * _rest_rel(i))


func _pose() -> void:
	set_flag.fill(0)
	var inv := world.affine_inverse()
	var moving := clampf(absf(speed) / maxf(walk_speed, 0.01), 0.0, 1.5)
	var idle_w := clampf(1.0 - moving * 1.5, 0.0, 1.0)
	G[0] = Transform3D.IDENTITY
	set_flag[0] = 1
	# ---- body
	var spine: PackedInt32Array = rig["spine"]
	var hub: int = rig["hub"]
	var hub_bone := spine[hub]
	var off := Vector3.ZERO
	var pitch := 0.0
	var roll := 0.0
	var yaw_sway := 0.0
	var crouch := _track("crouch") * maxf(leg_len, rig["body_h"])
	var jump := _track("jump") * maxf(leg_len * 0.6, rig["body_h"] * 0.8)
	if legs.size() > 0:
		var swinging := 0
		var lateral := 0.0
		for st in legs:
			if st["swinging"]:
				swinging += 1
				var s: float = st["swing_t"]
				lateral -= st["side"] * sin(PI * s)
		var sf := float(swinging) / legs.size()
		var dip := 0.0
		if legs.size() == 1:
			var st0: Dictionary = legs[0]
			hop_lift = (sin(PI * clampf(st0["swing_t"], 0, 1)) * leg_len * 0.25) if st0["swinging"] else 0.0
			off.y += hop_lift
		elif _moving():
			dip = -0.035 * leg_len * (1.0 - absf(sf - 0.5) * 2.0) * (1.6 if profile == "run" else 1.0)
		off.y += dip
		if legs.size() == 2:
			off.x += lateral * 0.06 * leg_len
			roll += lateral * 0.04
		pitch += 0.05 * clampf(speed / maxf(walk_speed, 0.01), -1.0, 2.0)
		roll += -turn * 0.06
	else:
		# Slither: body stays on the ground; spine chains make the wave.
		pass
	off.y += 0.012 * rig["body_h"] * _osc(2.0) * idle_w
	off.y += -crouch + jump
	var hub_basis := Basis.from_euler(Vector3(pitch, yaw_sway, roll))
	var hub_pivot: Vector3 = rest[hub_bone]
	# Keep every foot reachable: lower the body until all hips are within reach
	# (Spore adapts body height to the legs the same way).
	if not legs.is_empty() and jump <= 0.0:
		var hx := Transform3D(hub_basis, hub_pivot + off)
		var drop := 0.0
		for st in legs:
			var tgt: Vector3 = inv * st["foot"] - st["sole_local"]
			var hip: Vector3 = hx * (st["rest_j"][0] - hub_pivot)
			var maxr: float = st["length"] * 0.965
			var dxz := Vector2(hip.x - tgt.x, hip.z - tgt.z).length()
			var allowed: float = tgt.y + (sqrt(maxr * maxr - dxz * dxz) if dxz < maxr else 0.0)
			drop = maxf(drop, hip.y - allowed)
		off.y -= minf(drop, 0.45 * leg_len)
	G[hub_bone] = Transform3D(hub_basis, hub_pivot + off)
	set_flag[hub_bone] = 1
	bob_vel = (off.y - prev_bob)
	prev_bob = off.y
	# ---- front chain (neck/head)
	var n := spine.size()
	var front_count := n - 1 - hub
	var look_yaw := deg_to_rad(22.0 * _osc(1.0) + 9.0 * _osc(3.0, 1.0)) * idle_w
	var look_pitch := deg_to_rad(7.0 * _osc(2.0, 0.5)) * idle_w
	if look_point != null:
		var lp: Vector3 = inv * look_point
		var head_pos: Vector3 = rest[spine[n - 1]]
		var d := lp - head_pos
		look_yaw = clampf(atan2(d.x, d.z), -0.9, 0.9)
		look_pitch = clampf(-atan2(d.y, Vector2(d.x, d.z).length()), -0.6, 0.6)
	var head_pitch := deg_to_rad(_track("head_pitch")) + 0.04 * sin(TAU * gait_clock * 2.0) * moving
	var shake := deg_to_rad(14.0) * _track("shake") * sin(time * 18.0)
	var tilt := deg_to_rad(_track("head_tilt"))
	for i in range(hub + 1, n):
		var share := 1.0 / maxf(front_count, 1)
		var lag := float(i - hub) / maxf(front_count, 1)
		var walk_yaw := -0.03 * sin(TAU * gait_clock) * moving * lag if legs.size() > 0 else 0.0
		var q := Basis.from_euler(Vector3(head_pitch * share, (look_yaw + shake) * share + walk_yaw, tilt * share))
		if legs.is_empty():
			q = Basis(Vector3.UP, _slither_angle(i)) * q
		G[spine[i]] = _carry(spine[i], q)
		set_flag[spine[i]] = 1
	# ---- rear chain (tail)
	var rear_count := hub
	var wag_amp := 0.12 + 0.35 * _track("wave") * (1.0 if arms.is_empty() else 0.0)
	for i in range(hub - 1, -1, -1):
		var k := hub - i
		var q: Basis
		if legs.is_empty():
			q = Basis(Vector3.UP, _slither_angle(i))
		else:
			var wag := wag_amp * sin(TAU * (2.0 + 6.0 * _track("wave")) * otime / IDLE_LOOP - k * 0.7) * (0.4 + 0.6 * idle_w)
			wag += 0.1 * sin(TAU * gait_clock - k * 0.8) * moving
			var droop := 0.03 * k * (1.0 - moving * 0.5) + 0.04 * _osc(2.0, k) * idle_w
			q = Basis.from_euler(Vector3(-droop - pitch / maxf(rear_count, 1), wag / maxf(rear_count, 1) * 1.5, 0))
		G[spine[i]] = _carry(spine[i], q)
		set_flag[spine[i]] = 1
	# ---- limbs
	for st in legs:
		var target: Vector3 = inv * st["foot"]
		if jump > 0.0:
			target += Vector3.UP * jump * 0.85
		_solve_limb(st, target - st["sole_local"], true)
	var arm_i := 0
	for st in arms:
		var base := _rest_end(st)
		var arm_len: float = st["length"]
		var swing := sin(TAU * (gait_clock + (0.0 if st["side"] > 0 else 0.5))) * 0.35 * arm_len * minf(moving, 1.2)
		var t := base + Vector3(0, 0, swing) + Vector3(0, 0.03 * arm_len * _osc(2.0, arm_i), 0) * idle_w
		var up_w := _track("arms_up")
		if up_w > 0.0:
			var head: Vector3 = G[spine[n - 1]].origin
			var hip: Vector3 = _hip_now(st)
			var raised := hip + Vector3(st["side"] * 0.35 * arm_len, 0.85 * arm_len, 0.15 * arm_len)
			raised.y = maxf(raised.y, head.y + 0.1 * arm_len)
			t = t.lerp(raised, up_w)
		var wv := _track("wave")
		if wv > 0.0 and arm_i == 0:
			var hip2: Vector3 = _hip_now(st)
			var wave_t := hip2 + Vector3(st["side"] * (0.45 + 0.25 * sin(time * 9.0)) * arm_len, 0.75 * arm_len, 0.2 * arm_len)
			t = t.lerp(wave_t, wv)
		_solve_limb(st, t, false)
		arm_i += 1
	var app_i := 0
	for st in apps:
		var base := _rest_end(st)
		var ln: float = st["length"]
		var sway := Vector3(_osc(1.0, app_i), 0.5 * _osc(2.0, app_i * 2.0 + 1.5), _osc(1.0, app_i + 0.7)) * 0.08 * ln
		sway += Vector3(0, 0.06 * ln * bob_vel * 30.0, -0.15 * ln * moving)
		sway += Vector3(st["side"] * 0.3, 0.6, 0.2) * ln * _track("arms_up")
		_solve_limb(st, base + sway, false)
		app_i += 1
	# ---- parts
	for p in rig["parts"]:
		_pose_part(p, inv, moving, idle_w)
	# ---- anything left: carry rigidly
	for i in rest.size():
		if set_flag[i] == 0:
			G[i] = _carry(i)
			set_flag[i] = 1
	_write_pose()


func _slither_angle(i: int) -> float:
	var amp := 0.18 + 0.14 * clampf(absf(speed) / maxf(walk_speed, 0.01), 0.0, 1.0)
	return amp * sin(TAU * slither_phase - i * 1.1) * 0.6


func _hip_now(st: Dictionary) -> Vector3:
	var l: Dictionary = st["l"]
	var p: int = l["parent_bone"]
	return G[p] * (st["rest_j"][0] - rest[p])


func _rest_end(st: Dictionary) -> Vector3:
	var l: Dictionary = st["l"]
	var p: int = l["parent_bone"]
	var rj: Array = st["rest_j"]
	return G[p] * (rj[rj.size() - 1] - rest[p])


## FABRIK from the rest shape (carried by the parent bone) toward target.
func _solve_limb(st: Dictionary, target: Vector3, is_leg: bool) -> void:
	var l: Dictionary = st["l"]
	var pbone: int = l["parent_bone"]
	var gp: Transform3D = G[pbone]
	var rj: Array = st["rest_j"]
	var lens: Array = st["lengths"]
	var n := rj.size()
	var j: Array[Vector3] = []
	for k in n:
		j.append(gp * (rj[k] - rest[pbone]))
	var root := j[0]
	var total := 0.0
	for d in lens:
		total += d
	if root.distance_to(target) >= total * 0.999:
		var dir := (target - root).normalized()
		for k in range(1, n):
			j[k] = j[k - 1] + dir * lens[k - 1]
	else:
		# Bias the middle joints toward their rest bend so knees keep direction.
		for it in 12:
			j[n - 1] = target
			for k in range(n - 2, -1, -1):
				j[k] = j[k + 1] + (j[k] - j[k + 1]).normalized() * lens[k]
			j[0] = root
			for k in range(1, n):
				j[k] = j[k - 1] + (j[k] - j[k - 1]).normalized() * lens[k - 1]
			if j[n - 1].distance_to(target) < 0.001:
				break
	var bones: PackedInt32Array = st["bones"]
	var prev_basis := gp.basis
	for k in n - 1:
		var d0: Vector3 = (gp.basis * (rj[k + 1] - rj[k])).normalized()
		var d1: Vector3 = (j[k + 1] - j[k]).normalized()
		var q := _arc(d0, d1)
		var b := Basis(q) * gp.basis
		G[bones[k]] = Transform3D(b, j[k])
		set_flag[bones[k]] = 1
		prev_basis = b
	var end_basis := prev_basis
	if is_leg:
		end_basis = Basis()
		if st["swinging"]:
			end_basis = Basis(Vector3.RIGHT, -0.35 * sin(PI * clampf(st["swing_t"], 0.0, 1.0)))
	G[bones[n - 1]] = Transform3D(end_basis, j[n - 1])
	set_flag[bones[n - 1]] = 1
	# Grasping tips (pincers) open with the mouth / arms-up tracks.
	var open := maxf(_track("mouth"), _track("arms_up")) * 0.8 + 0.15 * (0.5 + 0.5 * _osc(3.0, st["side"]))
	for jw in l["jaws"]:
		var F: Basis = l["tip_frame"]
		var r := F * Basis(jw["axis"], deg_to_rad(jw["angle"]) * open) * F.inverse()
		var jb: int = jw["bone"]
		G[jb] = _carry(jb, r)
		set_flag[jb] = 1


static func _arc(a: Vector3, b: Vector3) -> Quaternion:
	var d := a.dot(b)
	if d > 0.99999:
		return Quaternion.IDENTITY
	if d < -0.99999:
		var axis := a.cross(Vector3.RIGHT)
		if axis.length() < 1e-4:
			axis = a.cross(Vector3.UP)
		return Quaternion(axis.normalized(), PI)
	return Quaternion(a.cross(b).normalized(), acos(clampf(d, -1.0, 1.0)))


func _pose_part(p: Dictionary, inv: Transform3D, moving: float, idle_w: float) -> void:
	var b: int = p["bone"]
	var F: Basis = p["frame"]
	var Fi := F.inverse()
	var rloc := Basis()
	var ph := float(b) * 0.37
	match p["cap"]:
		"look":
			# Blink twice per idle loop; squash along the face-up axis.
			var tl := fposmod(otime, IDLE_LOOP)
			var blink := 1.0
			for bt in ([1.6, 4.3] if idle_w > 0.5 else []):
				var d := absf(tl - bt)
				if d < 0.09:
					blink = minf(blink, lerpf(0.1, 1.0, d / 0.09))
			var lyaw := deg_to_rad(10.0 * _osc(1.0, 0.3)) * idle_w
			rloc = Basis(Vector3.BACK, lyaw) * Basis.from_scale(Vector3(1, 1, blink))
		"flop":
			var a := 0.12 * _osc(2.0, ph) * (0.5 + idle_w * 0.5) + clampf(bob_vel * 25.0, -0.4, 0.4) + 0.15 * moving * sin(TAU * gait_clock * 2.0)
			rloc = Basis(Vector3.RIGHT, a)
		"flap":
			var fl := _track("flap")
			var a := 0.08 * _osc(1.0, ph) * idle_w + 0.06 * sin(TAU * gait_clock) * moving + fl * 0.75 * sin(time * 9.0)
			rloc = Basis(Vector3.BACK, a)
		"sway":
			rloc = Basis(Vector3.RIGHT, 0.18 * _osc(2.0, ph)) * Basis(Vector3.BACK, 0.12 * _osc(1.0, ph * 2.0))
	var rs := F * rloc * Fi
	if p["mirrored"]:
		pass  # F already contains the reflection; conjugation mirrors the motion.
	G[b] = _carry(b, rs)
	set_flag[b] = 1
	if p["cap"] == "mouth":
		var open := _track("mouth") + 0.06 * (0.5 + 0.5 * _osc(1.0, 2.0)) * idle_w
		for jw in p["jaws"]:
			var jb: int = jw["bone"]
			var r := F * Basis(jw["axis"], deg_to_rad(jw["angle"]) * open) * Fi
			G[jb] = _carry(jb, r)
			set_flag[jb] = 1


func _write_pose() -> void:
	for i in rest.size():
		var p := parents[i]
		var local: Transform3D = (G[p].affine_inverse() * G[i]) if p >= 0 else G[i]
		skel.set_bone_pose_position(i, local.origin)
		skel.set_bone_pose_rotation(i, local.basis.get_rotation_quaternion())
		skel.set_bone_pose_scale(i, local.basis.get_scale())


## World-space position of a leg's sole as actually posed (for tests).
func posed_sole(st: Dictionary) -> Vector3:
	var bones: PackedInt32Array = st["bones"]
	var end: int = bones[bones.size() - 1]
	return world * (G[end] * st["sole_local"])
