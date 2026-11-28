"""Procedural animator in the spirit of Spore (Hecker et al. 2008).

Derived entirely from the rig the builder produced:
  * legs plan world-space footprints and swing between them; FABRIK IK bends them
  * the torso sets the walking pose at a precomputed clearance; legless bodies slither
  * neck/head and tail chains get look-around, wag and follow-through
  * swimming and flight use separate motion profiles and propulsive appendages
  * parts animate by capability: eyes look and blink, jaws open, ears flop,
    wings flap, antennae sway
  * actions (roar, wave, hop) are written against roles, not bones

All math is in recipe space (+Y up, +Z forward) with identity bone rests. `G[i]`
is bone i's posed transform; `write_pose` converts it onto the Blender armature.
The animator owns `world` (the creature in the world); bone poses are written in
armature space, so recording them yields in-place clips.
"""
import math

from mathutils import Matrix, Quaternion, Vector

from .runtime_motion import HOOFED_WALK, sample_lift

IDLE_LOOP = 6.0
TAU = 2 * math.pi
UPV = Vector((0, 1, 0))
RIGHTV = Vector((1, 0, 0))
BACKV = Vector((0, 0, 1))
LEGACY_CLIPS = ("idle", "walk", "run", "roar", "wave", "hop")
GROUND_CLIPS = ("walk", "run", "crawl")
WATER_MOTION = {
    "axial_vertical": (1.4, .84),
    "axial_lateral": (1.0, .72),
    "paddling": (1.2, .48),
}
AIR_MOTION = {
    "fly": (.8, 1.15),
    "glide": (3.2, 1.25),
}
AIR_TRANSITIONS = {
    "fly_to_glide": ("fly", "glide"),
    "glide_to_fly": ("glide", "fly"),
}
AIR_TRANSITION_LENGTH = 2.4
SWIM_CLIPS = ("swim", "swim_turn")
FREE_LOOPS = ("swim", *AIR_MOTION)
FREE_CLIPS = (*SWIM_CLIPS, *AIR_MOTION, *AIR_TRANSITIONS)
CRAWL_SPEED_FACTOR = .48
ACTIONS = {
    "roar": {"length": 2.4, "tracks": {
        "head_pitch": [[0, 0], [0.5, -26], [1.8, -30], [2.4, 0]], "mouth": [[0, 0], [0.45, 1], [1.9, 1], [2.3, 0]],
        "crouch": [[0, 0], [0.35, 0.07], [0.6, -0.03], [1.9, -0.03], [2.4, 0]], "arms_up": [[0, 0], [0.5, 1], [1.8, 1], [2.4, 0]],
        "shake": [[0, 0], [0.6, 1], [1.7, 1], [2.0, 0]], "flap": [[0, 0], [0.5, 1], [1.8, 1], [2.4, 0]]}},
    "wave": {"length": 2.6, "tracks": {
        "wave": [[0, 0], [0.5, 1], [2.1, 1], [2.6, 0]], "head_tilt": [[0, 0], [0.5, 12], [2.1, 12], [2.6, 0]],
        "mouth": [[0, 0], [0.5, 0.35], [2.1, 0.35], [2.6, 0]]}},
    "hop": {"length": 1.5, "tracks": {
        "crouch": [[0, 0], [0.35, 0.14], [0.48, 0.14], [0.6, -0.02], [1.05, 0.1], [1.25, 0.0], [1.5, 0]],
        "jump": [[0, 0], [0.5, 0], [0.78, 1], [1.05, 0], [1.5, 0]],
        "head_pitch": [[0, 0], [0.4, 10], [0.7, -12], [1.1, 6], [1.5, 0]],
        "flap": [[0, 0], [0.5, 0], [0.6, 1], [1.0, 1], [1.2, 0]]}},
    "reach": {"length": 1.8, "tracks": {
        "reach": [[0, 0], [.60, 1], [1.12, .92], [1.8, 0]],
        "head_pitch": [[0, 0], [.58, 7], [1.12, 5], [1.8, 0]]}},
    "grasp": {"length": 1.8, "tracks": {
        "reach": [[0, 0], [.66, 1], [1.13, .86], [1.8, 0]],
        "grasp": [[0, .09], [.52, .92], [.74, .95], [.92, 0], [1.55, 0], [1.8, .09]]}},
    "bite": {"length": 1.25, "tracks": {
        "mouth": [[0, 0], [.27, .95], [.42, 1], [.53, 0], [1.25, 0]],
        "head_pitch": [[0, 0], [.30, -12], [.53, 15], [.78, 4], [1.25, 0]]}},
}


def _paddles(limb):
    return limb["role"] == "fin" or limb.get("motion_cap") == "paddle"


def _grasps(limb):
    return bool(limb.get("jaws")) and "grasp" in (limb.get("tip_cap"), limb.get("family_cap"))


def available_clips(rig):
    """Baked and previewable clips for the recipe's motion profile and rig."""
    profile = rig.get("locomotion")
    limbs, parts = rig["limbs"], rig["parts"]
    clips = LEGACY_CLIPS
    if rig.get("construction") == "metaball":
        legs = any(limb["role"] == "leg" for limb in limbs)
        arms = any(limb["role"] == "arm" for limb in limbs)
        mouth = any(part["cap"] == "mouth" and part.get("jaws") for part in parts)
        eligible = {"idle": True, "walk": legs, "run": legs, "roar": mouth, "wave": arms, "hop": legs}
        clips = tuple(clip for clip in LEGACY_CLIPS if eligible[clip])
        if arms:
            clips += ("reach",)
        if any(_grasps(limb) for limb in limbs):
            clips += ("grasp",)
        if mouth:
            clips += ("bite",)
    if profile == "crawl":
        return clips + ("crawl",)
    swim = SWIM_CLIPS if rig.get("construction") == "metaball" else ("swim",)
    air = (*AIR_MOTION, *AIR_TRANSITIONS) if rig.get("construction") == "metaball" else tuple(AIR_MOTION)
    if profile in ("axial_vertical", "axial_lateral") and len(rig["spine"]) > 1:
        return clips + swim
    if profile == "paddling" and (any(_paddles(limb) for limb in limbs)
                                  or any(part["cap"] == "paddle" for part in parts)):
        return clips + swim
    if profile == "flight" and (any(limb["role"] == "wing" for limb in limbs)
                                or any(part["cap"] == "flap" for part in parts)):
        return clips + air
    return clips


def clamp(x, a, b):
    return a if x < a else (b if x > b else x)


def rot(axis, angle):
    return Matrix.Rotation(angle, 3, Vector(axis))


def bend_correction(incoming, outgoing, minimum, maximum):
    """Limit a joint without stretching either adjacent span."""
    angle = incoming.angle(outgoing)
    target = clamp(angle, minimum, maximum)
    if abs(angle - target) < 1e-7:
        return Matrix.Identity(3)
    axis = incoming.cross(outgoing)
    if axis.length_squared < 1e-10:
        axis = incoming.cross(RIGHTV)
        if axis.length_squared < 1e-10:
            axis = incoming.cross(UPV)
    return rot(axis, target - angle)


def euler(x, y, z):
    """Godot's default YXZ basis: Ry * Rx * Rz."""
    return rot(UPV, y) @ rot(RIGHTV, x) @ rot(BACKV, z)


def move_toward(a, b, d):
    return b if abs(b - a) <= d else a + math.copysign(d, b - a)


def smooth(t):
    return t * t * (3 - 2 * t)


def two_span(root, axis, distance, lengths, hint):
    a, b = lengths
    pole = hint - axis * hint.dot(axis)
    if pole.length_squared < 1e-10:
        pole = RIGHTV - axis * RIGHTV.dot(axis)
    if pole.length_squared < 1e-10:
        pole = UPV - axis * UPV.dot(axis)
    along = (a * a - b * b + distance * distance) / (2 * distance)
    bend = math.sqrt(max(0.0, a * a - along * along))
    return root + axis * along + pole.normalized() * bend


class X:
    """Rigid transform: basis b (3x3, may include scale) and origin o."""
    __slots__ = ("b", "o")

    def __init__(self, b=None, o=None):
        self.b = b if b is not None else Matrix.Identity(3)
        self.o = o if o is not None else Vector((0, 0, 0))

    def __matmul__(self, other):
        if isinstance(other, X):
            return X(self.b @ other.b, self.b @ other.o + self.o)
        return self.b @ other + self.o

    def inv(self):
        bi = self.b.inverted_safe()
        return X(bi, -(bi @ self.o))

    def copy(self):
        return X(self.b.copy(), self.o.copy())


def arc(a, b):
    d = a.dot(b)
    if d > 0.99999:
        return Matrix.Identity(3)
    if d < -0.99999:
        axis = a.cross(RIGHTV)
        if axis.length < 1e-4:
            axis = a.cross(UPV)
        return rot(axis.normalized(), math.pi)
    return rot(a.cross(b).normalized(), math.acos(clamp(d, -1.0, 1.0)))


def _vec(v):
    return Vector(v) if not isinstance(v, Vector) else v


class Animator:
    def __init__(self, rig):
        self.rig = rig
        self.rest = [Vector(v) for v in rig["rest"]]
        self.parents = rig["parents"]
        self.clips = available_clips(rig)
        self.locomotion = rig.get("locomotion")
        self.motion_time = 0.0
        self.spine_progress = self._spine_progress()
        n = len(self.rest)
        self.G = [X() for _ in range(n)]
        self.flag = [False] * n
        self.world = X()
        self.time = self.otime = 0.0
        self.speed = self.turn = self.target_speed = self.target_turn = 0.0
        self.clip, self.action, self.action_t = "idle", "", 0.0
        self.look_point = None
        self.legs, self.arms, self.apps = [], [], []
        self.leg_len = max(rig["leg_len"], 0.05)
        self.gait_clock, self.gait_freq, self.duty, self.profile = 0.0, 1.0, 0.6, "walk"
        self.slither_phase = self.bob_vel = self.prev_bob = 0.0
        for l in rig["limbs"]:
            J = [Vector(j) for j in l["joints"]]
            lens = [(J[k] - J[k - 1]).length for k in range(1, len(J))]
            st = {"l": l, "bones": l["bones"], "rest_j": J, "lengths": lens, "length": sum(lens), "side": l["side"],
                  "u": l["u"], "sole_local": Vector(l["sole_local"]), "plant": Vector(), "swinging": False, "swing_t": 0.0,
                  "swing_dur": 0.3, "lift": Vector(), "phase": 0.0, "prev_phase": 0.0, "offset": 0.0, "foot": Vector(), "lift_h": 0.1,
                  "tip_frame": Matrix(l.get("tip_frame", [[1, 0, 0], [0, 1, 0], [0, 0, 1]])), "jaws": l.get("jaws", [])}
            if "toe_local" in l:
                st["toe_local"] = Vector(l["toe_local"])
            {"leg": self.legs, "arm": self.arms}.get(l["role"], self.apps).append(st)
        for p in rig["parts"]:
            p["_F"] = Matrix(p["frame"])
            p["_Fi"] = p["_F"].inverted_safe()
        biped = rig.get("gait") == "humanoid" and len(self.legs) == 2
        self.hoofed_biped = biped and all("toe_local" in leg for leg in self.legs)
        self.humanoid = biped and (self.hoofed_biped or all(len(leg["lengths"]) == 2 for leg in self.legs))
        self._setup_gait()
        for arm in self.arms:
            arm["gait_leg"] = min(self.legs, default=None, key=lambda leg:
                abs(leg["u"] - arm["u"]) + (2 if leg["side"] * arm["side"] < 0 else 0))
        self.walk_settle = self._standing_clearance()
        self.run_settle = self._standing_clearance("run") if self.humanoid else self.walk_settle
        self.reset()

    # ---------------------------------------------------------- gait setup
    def _setup_gait(self):
        n = len(self.legs)
        if n == 0:
            self.walk_speed = clamp(self.rig["body_len"] * 0.35, 0.2, 2.0)
            self.run_speed = self.walk_speed * 2.2
            return
        groups = {}
        for st in self.legs:
            groups.setdefault(st["l"]["uid"], []).append(st)
        keys = sorted(groups, key=lambda k: groups[k][0]["u"])
        P = len(keys)
        for gi, k in enumerate(keys):
            for st in groups[k]:
                left, center = st["side"] >= 0.0, st["side"] == 0.0
                if n == 1:
                    off = 0.0
                elif P == 1:
                    off = 0.0 if left else 0.5
                elif P == 2:
                    off = (0.0 if left else 0.5) + (0.25 if gi == 1 else 0.0)
                else:
                    off = ((gi % 2) * 0.5 + gi * 0.06 + (0.0 if left else 0.5)) % 1.0
                if center and n > 1:
                    off = (gi * 0.5 + 0.25) % 1.0
                st["offset"] = st["walk_offset"] = off
                st["run_offset"] = (((0.0 if left else 0.5) + (0.5 if gi == 1 else 0.0)) % 1.0) if P == 2 else off
        L = self.leg_len
        cap = self._stride_cap()
        walk_stride = HOOFED_WALK["stride"] if self.hoofed_biped else .6
        self.walk_speed = min(walk_stride * L, cap) * self._freq("walk") / self._duty("walk")
        self.run_speed = min(0.95 * L, cap * 1.05) * self._freq("run") / self._duty("run")

    def _stride_cap(self):
        half = float("inf")
        for st in self.legs:
            rj = st["rest_j"]
            hip = rj[0] - Vector((0, 0.1 * self.leg_len, 0))
            v = rj[-1] - hip
            R = 0.94 * st["length"]
            disc = v.z * v.z - (v.length_squared - R * R)
            if disc <= 0:
                half = min(half, 0.02)
                continue
            half = min(half, -v.z + math.sqrt(disc), v.z + math.sqrt(disc))
        return 2.0 * max(half, 0.02) * 0.9

    def _standing_clearance(self, profile="walk"):
        """Choose one reachable pelvis height for the stride before any foot swings."""
        drop = 0.0
        speed = self.run_speed if profile == "run" else self.walk_speed
        half_stride = speed * self._duty(profile) / self._freq(profile) * .5
        for leg in self.legs:
            hip, sole = leg["rest_j"][0], leg["rest_j"][-1]
            horizontal = math.hypot(sole.x - hip.x, abs(sole.z - hip.z) + half_stride)
            reach = (.985 if self.humanoid else .94) * leg["length"]
            vertical = math.sqrt(max(0.0, reach * reach - horizontal * horizontal))
            drop = max(drop, hip.y + leg["sole_local"].y - vertical)
        return min(drop, 0.45 * self.leg_len)

    def _duty(self, p):
        if p == "crawl":
            return max(.75, self._duty("walk"))
        n = len(self.legs)
        if self.hoofed_biped and p == "walk":
            return HOOFED_WALK["duty"]
        if n == 1:
            return 0.45 if p == "walk" else 0.35
        if p == "run":
            return 0.38 if n == 2 else (0.42 if n <= 4 else 0.45)
        return 0.6 if n == 2 else (0.75 if n == 4 else 0.65 if n <= 4 else 0.55)

    def _freq(self, p):
        if p == "crawl":
            return .67 * self._freq("walk")
        if self.hoofed_biped and p == "walk":
            return 1.0 / HOOFED_WALK["period"]
        if self.humanoid:
            return 1 / (.64 if p == "run" else .92)
        s = 1.1 if p == "walk" else 1.75
        if len(self.legs) == 1:
            s *= 0.9
        return s / math.sqrt(self.leg_len)

    def cycle_length(self):
        if self.clip in SWIM_CLIPS:
            return WATER_MOTION[self.locomotion][0] * (2 if self.clip == "swim_turn" else 1)
        if self.clip in AIR_MOTION:
            return AIR_MOTION[self.clip][0]
        if self.clip in AIR_TRANSITIONS:
            return AIR_TRANSITION_LENGTH
        if self.clip == "crawl" and not self.legs:
            return 1.0 / self._slither_rate()
        return 1.0 / max(self._freq(self.profile), 0.01)

    # ------------------------------------------------------------ control
    @staticmethod
    def _ground(p):
        return Vector((p.x, 0.0, p.z))

    def reset(self):
        self.time = self.otime = self.gait_clock = self.motion_time = 0.0
        self.motion_basis = self.world.b.copy()
        self._plant_feet()
        self.pose()

    def _plant_feet(self):
        for st in self.legs:
            st["plant"] = self._ground(self.world @ (st["rest_j"][-1] + st["sole_local"]))
            st["foot"] = st["plant"].copy()
            st["swinging"] = False
            st["phase"] = st["prev_phase"] = st["offset"]

    def play(self, name):
        if name not in self.clips:
            return False
        if name in ACTIONS:
            if self.clip in FREE_CLIPS:
                self.play("idle")
            self.action, self.action_t = name, 0.0
            return True
        was_free = self.clip in FREE_CLIPS
        self.clip = name
        if name in FREE_CLIPS:
            self.action = ""
            self.motion_time = 0.0
            self.motion_basis = self.world.b.copy()
            self.target_speed = self.speed = self._free_speed(0.0)
            self.turn = self.target_turn = 0.0
            self.pose()
            return True
        if name == "walk":
            self.target_speed = self.speed = self.walk_speed
            self.profile = "walk"
        elif name == "run":
            self.target_speed = self.speed = self.run_speed
            self.profile = "run"
        elif name == "crawl":
            self.target_speed = self.speed = CRAWL_SPEED_FACTOR * self.walk_speed
            self.gait_clock = self.slither_phase = 0.0
            self.profile = "crawl"
        else:
            self.target_speed = 0.0
            if self.profile == "crawl":
                self.profile = "walk"
        self._apply_profile()
        if name in GROUND_CLIPS:
            self._prime()
            if name == "crawl" and not self.legs:
                self.pose()
        elif was_free:
            self.speed = self.turn = self.target_turn = 0.0
            self._plant_feet()
            self.pose()
        return True

    def _apply_profile(self):
        self.duty = self._duty(self.profile)
        profile = "walk" if self.profile == "crawl" else self.profile
        for st in self.legs:
            st["offset"] = st.get(profile + "_offset", st["offset"])

    def _lift_height(self):
        if self.profile == "crawl":
            return self.leg_len * .10
        if self.humanoid:
            return self.leg_len * (.11 if self.profile == "walk" else .15)
        return self.leg_len * (.16 if self.profile == "walk" else .18)

    def _prime(self):
        """Start a gait in its steady state, as if already walking."""
        if not self.legs:
            return
        self.gait_freq = self._freq(self.profile)
        stride = self.speed * self.duty / self.gait_freq
        fwd = self.world.b @ BACKV
        for st in self.legs:
            p = (self.gait_clock + st["offset"]) % 1.0
            st["phase"] = st["prev_phase"] = p
            rest_fp = self._rest_footprint(st, 0.0)
            if p < self.duty:
                st["swinging"] = False
                st["plant"] = rest_fp + fwd * stride * (0.5 - p / self.duty)
                st["foot"] = st["plant"].copy()
            else:
                s = (p - self.duty) / (1.0 - self.duty)
                st["swinging"] = True
                st["swing_dur"] = (1.0 - self.duty) / self.gait_freq
                st["swing_t"] = s
                st["lift_h"] = self._lift_height()
                st["lift"] = rest_fp + fwd * (-0.5 * stride - self.speed * s * st["swing_dur"])
                st["plant"] = st["lift"].copy()
        self.pose()

    def drive(self, forward, turn_rate, running):
        self.target_speed = forward * (self.run_speed if running else self.walk_speed)
        self.target_turn = turn_rate
        want = "run" if running and forward > 0.5 else "walk"
        if want != self.profile:
            self.profile = want
            self._apply_profile()

    def advance_to(self, t, dt=1.0 / 30.0):
        while self.time < t - 1e-6:
            self.step(min(dt, t - self.time))

    # -------------------------------------------------------------- update
    def moving(self):
        return abs(self.speed) > 0.02 or abs(self.turn) > 0.05

    def step(self, dt):
        self.time += dt
        if self.clip in FREE_CLIPS:
            self._step_free(dt)
            self.pose()
            return
        self.speed = move_toward(self.speed, self.target_speed, dt * max(self.walk_speed, 0.3) * 3.0)
        self.turn = move_toward(self.turn, self.target_turn, dt * 4.0)
        self.world.b = self.world.b @ rot(UPV, self.turn * dt)
        self.world.o = self.world.o + (self.world.b @ BACKV) * self.speed * dt
        if self.action:
            self.action_t += dt
            if self.action_t > ACTIONS[self.action]["length"]:
                self.action = ""
        self._gait(dt)
        if self.clip == "crawl":
            self.otime = IDLE_LOOP * (self.gait_clock if self.legs else self.slither_phase)
        else:
            idle_w = clamp(1.0 - abs(self.speed) / max(self.walk_speed, 0.01) * 1.5, 0.0, 1.0)
            rate = (self.gait_freq * IDLE_LOOP) if self.legs else 1.0
            self.otime += dt * (rate + (1.0 - rate) * idle_w)
        self.pose()

    def _free_speed(self, at):
        if self.clip in SWIM_CLIPS:
            rate = WATER_MOTION[self.locomotion][1]
        elif self.clip in AIR_TRANSITIONS:
            start, end = AIR_TRANSITIONS[self.clip]
            mix = smooth(clamp(at / AIR_TRANSITION_LENGTH, 0.0, 1.0))
            rate = (1 - mix) * AIR_MOTION[start][1] + mix * AIR_MOTION[end][1]
        else:
            rate = AIR_MOTION[self.clip][1]
        return rate * self.rig["body_len"]

    def _free_heading(self, at):
        if self.clip != "swim_turn":
            return 0.0
        return math.radians(30) * smooth(clamp(at / self.cycle_length(), 0.0, 1.0))

    def _step_free(self, dt):
        a = self.motion_time
        b = a + dt
        mid = (a + b) * .5
        middle = self.motion_basis @ rot(UPV, self._free_heading(mid))
        final = self.motion_basis @ rot(UPV, self._free_heading(b))
        v0 = (self.world.b @ BACKV) * self._free_speed(a)
        vm = (middle @ BACKV) * self._free_speed(mid)
        v1 = (final @ BACKV) * self._free_speed(b)
        self.world.o += (v0 + 4 * vm + v1) * (dt / 6)
        self.world.b = final
        self.speed = self._free_speed(b)
        self.motion_time = b

    def _slither_rate(self):
        return abs(self.speed) / max(self.rig["body_len"] * 0.6, 0.1) + (0.25 if self.moving() else 0.0)

    def _gait(self, dt):
        if not self.legs:
            self.slither_phase += self._slither_rate() * dt
            return
        f = self._freq(self.profile)
        ref = self.run_speed if self.profile == "run" else self.walk_speed
        if self.profile == "crawl":
            ref *= CRAWL_SPEED_FACTOR
        self.gait_freq = max(f * clamp(abs(self.speed) / max(ref, 0.01), 0.0, 1.6), 0.6 * f)
        mv = self.moving()
        if mv:
            self.gait_clock += self.gait_freq * dt
        duty = self.duty
        for st in self.legs:
            ph = (self.gait_clock + st["offset"]) % 1.0
            prev = st["prev_phase"]
            st["phase"] = st["prev_phase"] = ph
            if self.hoofed_biped and self.profile == "walk" and mv:
                self._step_hoofed_walk(st, ph, prev)
                continue
            crossed = (prev < duty <= ph) or (ph < prev and (prev < duty or ph >= duty))
            if not st["swinging"]:
                drift = (st["plant"] - self._rest_footprint(st, 0.0)).length
                lift = (mv and crossed) or (not mv and drift > 0.12 * self.leg_len and not self._neighbor_swinging(st))
                if lift:
                    st["swinging"] = True
                    st["swing_t"] = 0.0
                    st["swing_dur"] = (1.0 - duty) / self.gait_freq if mv else 0.22 * math.sqrt(self.leg_len)
                    st["lift"] = st["plant"].copy()
                    st["lift_h"] = self._lift_height()
            if st["swinging"]:
                st["swing_t"] += dt / st["swing_dur"]
                s = clamp(st["swing_t"], 0.0, 1.0)
                ahead = (1.0 - s) * st["swing_dur"] + (duty / self.gait_freq * 0.5 if mv else 0.0)
                target = self._rest_footprint(st, ahead)
                st["foot"] = st["lift"].lerp(target, smooth(s)) + UPV * st["lift_h"] * math.sin(math.pi * s)
                if s >= 1.0:
                    st["swinging"] = False
                    st["plant"] = target
                    st["foot"] = target.copy()
            else:
                st["foot"] = st["plant"].copy()

    def _step_hoofed_walk(self, st, phase, previous):
        if phase < self.duty:
            if st["swinging"] or phase < previous:
                ahead = (self.duty * .5 - phase) / self.gait_freq
                st["plant"] = self._rest_footprint(st, ahead)
            st["swinging"] = False
            st["foot"] = st["plant"].copy()
            return
        if not st["swinging"]:
            st["swinging"] = True
            st["lift"] = st["plant"].copy()
        progress = (phase - self.duty) / (1 - self.duty)
        st["swing_t"] = progress
        ahead = (1 - phase + self.duty * .5) / self.gait_freq
        target = self._rest_footprint(st, ahead)
        lift = sample_lift(HOOFED_WALK["lift"], progress)
        st["foot"] = st["lift"].lerp(target, smooth(progress)) + UPV * st["length"] * lift

    def _neighbor_swinging(self, st):
        if any(o is not st and o["swinging"] and o["l"]["uid"] == st["l"]["uid"] for o in self.legs):
            return True
        return sum(1 for o in self.legs if o["swinging"]) >= max(1, len(self.legs) // 2)

    def _rest_footprint(self, st, ahead):
        fb = self.world.b @ rot(UPV, self.turn * ahead)
        fo = self.world.o + (self.world.b @ BACKV) * self.speed * ahead
        return self._ground(fb @ (st["rest_j"][-1] + st["sole_local"]) + fo)

    # -------------------------------------------------------------- tracks
    def track(self, name):
        if not self.action:
            return 0.0
        keys = ACTIONS[self.action]["tracks"].get(name)
        if not keys:
            return 0.0
        t = self.action_t
        if t <= keys[0][0]:
            return keys[0][1]
        for i in range(1, len(keys)):
            if t <= keys[i][0]:
                a, b = keys[i - 1], keys[i]
                f = smooth((t - a[0]) / max(b[0] - a[0], 1e-4))
                return a[1] + (b[1] - a[1]) * f
        return keys[-1][1]

    def osc(self, n, phase=0.0):
        return math.sin(TAU * n * self.otime / IDLE_LOOP + phase)

    # ---------------------------------------------------------------- pose
    def _rest_rel(self, i):
        p = self.parents[i]
        return self.rest[i] - (self.rest[p] if p >= 0 else Vector())

    def _carry(self, i, r=None):
        p = self.parents[i]
        gp = self.G[p] if p >= 0 else X()
        return X(gp.b @ r if r is not None else gp.b.copy(), gp @ self._rest_rel(i))

    def _set(self, i, x):
        self.G[i] = x
        self.flag[i] = True

    def _spine_progress(self):
        distances = [0.0]
        bones = self.rig["spine"]
        for rear, front in zip(bones, bones[1:]):
            distances.append(distances[-1] + (self.rest[front] - self.rest[rear]).length)
        return {bone: distance / max(distances[-1], 0.0001) for bone, distance in zip(bones, distances)}

    def _axial_angle(self, progress, phase):
        aft = 1.0 - progress
        return (.045 + .42 * min(aft, 1.2) ** 1.4) * math.sin(phase - 2.8 * aft)

    def _pose_chain(self, st, rotations=()):
        for k, bone in enumerate(st["bones"]):
            posed = self._carry(bone, rotations[k] if rotations else None)
            ranges = st["l"].get("bend_limits")
            if ranges and 0 < k < len(st["bones"]) - 1 and ranges[k - 1]:
                previous = self.G[st["bones"][k - 1]].o
                outgoing = posed.b @ (st["rest_j"][k + 1] - st["rest_j"][k])
                low, high = map(math.radians, ranges[k - 1])
                correction = bend_correction(posed.o - previous, outgoing, low, high)
                posed.b = correction @ posed.b
            self._set(bone, posed)
        self._pose_joint_support(st)

    def _pose_joint_support(self, st):
        bones = st["bones"]
        for k, bone in enumerate(st["l"].get("joint_support", ()), 1):
            incoming = self.G[bones[k - 1]].b.to_quaternion()
            outgoing = self.G[bones[k]].b.to_quaternion()
            self._set(bone, X(incoming.slerp(outgoing, .5).to_matrix(), self.G[bones[k]].o.copy()))

    @staticmethod
    def _paddle_rotation(phase, side, amount):
        # The return stroke feathers the blade while the powered stroke sweeps aft.
        sweep = .46 * math.sin(phase) + .08 * math.sin(2 * phase)
        recover = .25 * math.cos(phase)
        return euler(amount * recover, side * amount * sweep, side * amount * .6 * recover)

    @staticmethod
    def _wing_rotation(mode, phase, side):
        if mode == "glide":
            # Hold the wings open with a shallow dihedral and slow trim.
            return euler(.025 * math.sin(phase), side * -.16, side * (.08 + .025 * math.sin(phase)))
        stroke = .66 * math.sin(phase) + .11 * math.sin(2 * phase)
        return euler(.13 * math.cos(phase), .14 * side * math.cos(phase), side * stroke)

    @staticmethod
    def _hinge_delta(st, joint, amount, axis):
        """Flex toward the authored bend without straightening through it."""
        joints = st["rest_j"]
        if joint < len(joints) - 1:
            incoming = (joints[joint] - joints[joint - 1]).normalized()
            outgoing = (joints[joint + 1] - joints[joint]).normalized()
            hinge = incoming.cross(outgoing)
            if hinge.length_squared > 1e-8:
                bend = incoming.angle(outgoing)
                return rot(hinge, clamp(amount, -.65 * bend, max(0.0, 2.3 - bend)))
        return rot(axis, amount)

    def _wing_chain(self, st, mode, phase, side):
        rotations = [self._wing_rotation(mode, phase, side)]
        strength = .018 if mode == "glide" else .31
        for k in range(1, len(st["bones"])):
            lag = phase - min(.45 * k, 1.6)
            rotations.append(self._hinge_delta(st, k, -strength * math.sin(lag) / k, BACKV * side))
        return rotations

    @staticmethod
    def _air_trim(mode, phase, height):
        if mode == "fly":
            return -.035 + .045 * math.sin(phase - .5), .11 * height * math.sin(phase - .65)
        return .06 + .024 * math.sin(phase), .04 * height * math.cos(phase)

    @staticmethod
    def _mix_orientation(first, second, weight):
        return first.to_quaternion().slerp(second.to_quaternion(), weight).to_matrix()

    def _air_modes(self):
        if self.clip in AIR_TRANSITIONS:
            source, target = AIR_TRANSITIONS[self.clip]
            target_time = self.motion_time - AIR_TRANSITION_LENGTH
            weight = smooth(clamp(self.motion_time / AIR_TRANSITION_LENGTH, 0.0, 1.0))
        else:
            source = target = self.clip
            target_time = self.motion_time
            weight = 0.0
        phase_a = TAU * (self.motion_time / AIR_MOTION[source][0] % 1.0)
        phase_b = TAU * (target_time / AIR_MOTION[target][0] % 1.0)
        return (source, phase_a), (target, phase_b), weight

    def _pose_free(self):
        swim = self.clip in SWIM_CLIPS
        if swim:
            phase = TAU * (self.motion_time / WATER_MOTION[self.locomotion][0] % 1.0)
        else:
            air_a, air_b, air_weight = self._air_modes()
            phase = air_a[1]
        axial = swim and self.locomotion != "paddling"
        lateral = self.locomotion == "axial_lateral"
        axis = UPV if lateral else RIGHTV
        spine = self.rig["spine"]
        hub = self.rig["hub"]
        center = spine[hub]
        height = self.rig["body_h"]
        if axial:
            angles = {bone: self._axial_angle(progress, phase) for bone, progress in self.spine_progress.items()}
            basis = rot(axis, angles[center])
            lift = 0.0 if lateral else .11 * height * math.sin(phase)
        elif swim:
            basis = rot(RIGHTV, .055 * math.sin(phase))
            lift = .09 * height * math.cos(phase)
        else:
            pitch_a, lift_a = self._air_trim(*air_a, height)
            pitch_b, lift_b = self._air_trim(*air_b, height)
            basis = rot(RIGHTV, (1 - air_weight) * pitch_a + air_weight * pitch_b)
            lift = (1 - air_weight) * lift_a + air_weight * lift_b
        if self.clip == "swim_turn":
            pulse = math.sin(math.pi * clamp(self.motion_time / self.cycle_length(), 0.0, 1.0)) ** 2
            basis = euler(0.0, .08 * pulse, -.20 * pulse) @ basis

        self._set(center, X(basis, self.rest[center] + UPV * lift))
        for bone in (*spine[hub + 1:], *reversed(spine[:hub])):
            rotation = rot(axis, angles[bone] - angles[self.parents[bone]]) if axial else None
            self._set(bone, self._carry(bone, rotation))

        for st in (*self.legs, *self.arms, *self.apps):
            limb, bones = st["l"], st["bones"]
            role, side = limb["role"], st["side"] or 1.0
            rotations = []
            if swim and role == "tail" and axial:
                progress = self.spine_progress[limb["parent_bone"]]
                previous = angles[limb["parent_bone"]]
                for k in range(len(bones)):
                    # Each tail span carries the wave farther aft. A half-span
                    # offset makes the terminal bone articulate rigid flukes.
                    distance = sum(st["lengths"][:k]) + .5 * st["lengths"][min(k, len(bones) - 2)]
                    angle = self._axial_angle(progress - distance / max(self.rig["body_len"], .05), phase)
                    rotations.append(rot(axis, clamp(angle - previous, -.32, .32)))
                    previous = angle
            elif swim and _paddles(limb):
                stroke_phase = phase - .45 * (1 - st["u"])
                amount = .25 if axial else 1.0
                if role == "leg":
                    # Webbed feet row with the leg and feather at the ankle.
                    if side < 0:
                        stroke_phase += math.pi
                    rotations = [rot(RIGHTV, amount * .42 * math.sin(stroke_phase))]
                    rotations += [self._hinge_delta(st, k, amount * .20 * math.cos(stroke_phase) / k, RIGHTV)
                                  for k in range(1, len(bones))]
                else:
                    rotations = [self._paddle_rotation(stroke_phase - .35 * k, side, amount / (1 + 3 * k))
                                 for k in range(len(bones))]
            elif not swim and role == "wing":
                rotations = self._wing_chain(st, *air_a, side)
                if air_weight:
                    target = self._wing_chain(st, *air_b, side)
                    rotations = [self._mix_orientation(a, b, air_weight) for a, b in zip(rotations, target)]
            elif not swim and role in ("leg", "tail"):
                tuck = .32 if role == "leg" else -.04
                trim = (1 - air_weight) * math.sin(air_a[1] + .65) + air_weight * math.sin(air_b[1] + .65)
                rotations = [rot(RIGHTV, tuck + .025 * trim)] + [None] * (len(bones) - 1)
            self._pose_chain(st, rotations)

        for p in self.rig["parts"]:
            side = -1.0 if p["mirrored"] else 1.0
            rotation = None
            if swim and p["cap"] == "paddle":
                rotation = self._paddle_rotation(phase - .45 * (1 - p["u"]), side, .25 if axial else 1.0)
            elif not swim and p["cap"] == "flap":
                rotation = self._wing_rotation(*air_a, side)
                if air_weight:
                    rotation = self._mix_orientation(rotation, self._wing_rotation(*air_b, side), air_weight)
            self._set(p["bone"], self._carry(p["bone"], rotation))
        self._carry_unposed()

    def _carry_unposed(self):
        for i in range(len(self.rest)):
            if not self.flag[i]:
                self._set(i, self._carry(i))

    def pose(self):
        rig, G = self.rig, self.G
        self.flag = [False] * len(self.rest)
        self._set(0, X())
        if self.clip in FREE_CLIPS:
            self._pose_free()
            return
        inv = self.world.inv()
        moving = clamp(abs(self.speed) / max(self.walk_speed, 0.01), 0.0, 1.5)
        idle_w = clamp(1.0 - moving * 1.5, 0.0, 1.0)
        spine, hub = rig["spine"], rig["hub"]
        hub_bone = spine[hub]
        off = Vector()
        pitch = roll = 0.0
        crouch = self.track("crouch") * max(self.leg_len, rig["body_h"])
        jump = self.track("jump") * max(self.leg_len * 0.6, rig["body_h"] * 0.8)
        legs = self.legs
        hoofed_walk = self.hoofed_biped and self.profile == "walk"
        if legs:
            swinging, lateral = 0, 0.0
            for st in legs:
                if st["swinging"]:
                    swinging += 1
                    sway = math.sin(math.pi * st["swing_t"])
                    lateral -= st["side"] * (smooth(sway) if hoofed_walk else sway)
            sf = swinging / len(legs)
            if len(legs) == 1:
                st0 = legs[0]
                off.y += math.sin(math.pi * clamp(st0["swing_t"], 0, 1)) * self.leg_len * 0.25 if st0["swinging"] else 0.0
            elif self.moving():
                if hoofed_walk:
                    phase = self.gait_clock - HOOFED_WALK["pelvis_dip_delay"]
                    step_dip = .5 + .5 * math.cos(2 * TAU * phase)
                    off.y -= HOOFED_WALK["pelvis_dip"] * self.leg_len * step_dip
                else:
                    off.y += -0.035 * self.leg_len * (1.0 - abs(sf - 0.5) * 2.0) * (1.6 if self.profile == "run" else 1.0)
            if len(legs) == 2:
                off.x += lateral * 0.06 * self.leg_len
                roll += lateral * 0.04
            lean = .018 if self.hoofed_biped and self.profile == "walk" else .05
            pitch += lean * clamp(self.speed / max(self.walk_speed, 0.01), -1.0, 2.0)
            roll += -self.turn * 0.06
        off.y += 0.012 * rig["body_h"] * self.osc(2.0) * idle_w
        off.y += -crouch + jump
        hb = euler(pitch, 0.0, roll)
        pivot = self.rest[hub_bone]
        if legs and jump <= 0.0:
            if self.humanoid:
                settle = self.run_settle if self.profile == "run" else self.walk_settle
                speed = self.run_speed if self.profile == "run" else self.walk_speed
                off.y -= settle * clamp(abs(self.speed) / speed, 0, 1)
            else:
                off.y -= self.walk_settle
        if hoofed_walk and self.moving() and not self.action:
            # Extend the supporting leg without asking the hoof to leave its plant.
            rise = .06 * self.leg_len
            blend_width = .025 * self.leg_len
            for leg in legs:
                hip = pivot + off + hb @ (leg["rest_j"][0] - pivot)
                ankle = inv @ leg["foot"] - self._hoof_contact_offset(leg, self._hoof_basis(leg))
                delta = hip - ankle
                reach = .995 * (self._hoof_upper_reach(leg["lengths"]) + leg["lengths"][2])
                allowed = math.sqrt(max(0, reach * reach - delta.x * delta.x - delta.z * delta.z))
                ceiling = allowed - delta.y
                blend = max(0.0, 1 - abs(rise - ceiling) / blend_width)
                rise = min(rise, ceiling) - .25 * blend_width * blend * blend
            off.y += rise
        self._set(hub_bone, X(hb, pivot + off))
        self.bob_vel = off.y - self.prev_bob
        self.prev_bob = off.y
        # neck / head
        n = len(spine)
        front = n - 1 - hub
        look_yaw = math.radians(22.0 * self.osc(1.0) + 9.0 * self.osc(3.0, 1.0)) * idle_w
        if self.look_point is not None:
            d = inv @ self.look_point - self.rest[spine[-1]]
            look_yaw = clamp(math.atan2(d.x, d.z), -0.9, 0.9)
        head_bob = .015 if self.hoofed_biped and self.profile == "walk" else .04
        head_pitch = math.radians(self.track("head_pitch")) + head_bob * math.sin(TAU * self.gait_clock * 2.0) * moving
        shake = math.radians(14.0) * self.track("shake") * math.sin(self.time * 18.0)
        tilt = math.radians(self.track("head_tilt"))
        for i in range(hub + 1, n):
            share = 1.0 / max(front, 1)
            lag = (i - hub) / max(front, 1)
            walk_yaw = -0.03 * math.sin(TAU * self.gait_clock) * moving * lag if legs else 0.0
            q = euler(head_pitch * share, (look_yaw + shake) * share + walk_yaw, tilt * share)
            if self.clip == "crawl":
                q = rot(UPV, self._crawl_bend(i)) @ q
            elif not legs:
                q = rot(UPV, self._slither(i)) @ q
            self._set(spine[i], self._carry(spine[i], q))
        # Rear torso inherits the hub. Undulation belongs to crawling bodies and tail chains.
        for i in range(hub - 1, -1, -1):
            angle = self._crawl_bend(i) if self.clip == "crawl" else 0.0 if legs else self._slither(i)
            q = rot(UPV, angle)
            self._set(spine[i], self._carry(spine[i], q))
        # limbs
        for st in legs:
            target = inv @ st["foot"]
            if jump > 0.0:
                target = target + UPV * jump * 0.85
            self._solve(st, target, True)
        for ai, st in enumerate(self.arms):
            base = self._rest_end(st)
            L = st["length"]
            sweep = math.sin(TAU * (self.gait_clock + (0.0 if st["side"] > 0 else 0.5)))
            leg = st["gait_leg"]
            if leg is not None:
                phase = leg["phase"]
                progress = phase / self.duty if phase < self.duty else 1 + (phase - self.duty) / (1 - self.duty)
                side_sign = -1 if leg["side"] * st["side"] < 0 else 1
                sweep = -math.cos(math.pi * progress) * side_sign * math.copysign(1, self.speed)
            sweep_amount = HOOFED_WALK["arm_sweep"] if self.hoofed_biped and self.profile == "walk" else (.24 if self.humanoid else .35)
            swing = sweep * sweep_amount * L * min(moving, 1.2)
            # Keep the hanging hands outside the knees' forward swing envelope.
            clearance_amount = HOOFED_WALK["arm_clearance"] if hoofed_walk else .20
            flex_amount = HOOFED_WALK["arm_flex"] if hoofed_walk else .13
            clearance = st["side"] * clearance_amount * L * min(moving, 1.0) if self.humanoid else 0.0
            flex = flex_amount * L * max(0.0, sweep) * min(moving, 1.0) if self.hoofed_biped else 0.0
            t = base + Vector((clearance, flex, swing)) + Vector((0, 0.03 * L * self.osc(2.0, ai), 0)) * idle_w
            up_w = self.track("arms_up")
            if up_w > 0.0:
                head = G[spine[-1]].o
                hip = self._hip_now(st)
                raised = hip + Vector((st["side"] * 0.35 * L, 0.85 * L, 0.15 * L))
                raised.y = max(raised.y, head.y + 0.1 * L)
                t = t.lerp(raised, up_w)
            reach = self.track("reach")
            if reach > 0.0 and (self.action != "grasp" or _grasps(st["l"])):
                hip = self._hip_now(st)
                reaching = hip + Vector((st["side"] * .43, .08, .76)) * L
                t = t.lerp(reaching, reach)
            wv = self.track("wave")
            if wv > 0.0 and ai == 0:
                hip = self._hip_now(st)
                wave = math.sin(self.time * 9.0)
                if self.humanoid:
                    raised_hand = Vector((st["side"] * (.69 + .10 * wave), .53, .20))
                else:
                    raised_hand = Vector((st["side"] * (.45 + .25 * wave), .75, .20))
                t = t.lerp(hip + raised_hand * L, wv)
            self._solve(st, t, False)
        for ai, st in enumerate(self.apps):
            if st["l"]["role"] == "tail":
                for k, bone in enumerate(st["bones"]):
                    phase = TAU * self.otime / IDLE_LOOP * 2 - k * 0.65
                    wag = math.sin(phase) * (0.11 + 0.09 * moving)
                    self._set(bone, self._carry(bone, euler(0.035 * math.cos(phase), wag, 0)))
                continue
            if st["l"]["role"] == "wing":
                flap = (0.12 * self.osc(1.0, 0.2) * idle_w
                        + 0.22 * math.sin(TAU * self.gait_clock) * moving
                        + self.track("flap") * 0.65 * math.sin(self.time * 9.0))
                for k, bone in enumerate(st["bones"]):
                    self._set(bone, self._carry(bone, rot(BACKV, st["side"] * flap / (1 + 2 * k))))
                continue
            L = st["length"]
            sway = Vector((self.osc(1.0, ai), 0.5 * self.osc(2.0, ai * 2.0 + 1.5), self.osc(1.0, ai + 0.7))) * 0.08 * L
            sway += Vector((0, 0.06 * L * self.bob_vel * 30.0, -0.15 * L * moving))
            sway += Vector((st["side"] * 0.3, 0.6, 0.2)) * L * self.track("arms_up")
            self._solve(st, self._rest_end(st) + sway, False)
        for p in rig["parts"]:
            self._pose_part(p, moving, idle_w)
        self._carry_unposed()

    def _slither(self, i):
        amp = 0.18 + 0.14 * clamp(abs(self.speed) / max(self.walk_speed, 0.01), 0.0, 1.0)
        return amp * math.sin(TAU * self.slither_phase - i * 1.1) * 0.6

    def _crawl_bend(self, i):
        n = len(self.rig["spine"]) - 1
        phase = self.gait_clock if self.legs else self.slither_phase
        strain = (.035 if self.legs else .18) * min(1.0, 4.0 / max(n, 1))
        return strain * math.sin(TAU * phase + 4.2 * i / max(n, 1))

    def _hip_now(self, st):
        p = st["l"]["parent_bone"]
        return self.G[p] @ (st["rest_j"][0] - self.rest[p])

    def _rest_end(self, st):
        p = st["l"]["parent_bone"]
        return self.G[p] @ (st["rest_j"][-1] - self.rest[p])

    def _hoof_basis(self, st):
        if not self.moving() or self.profile != "walk":
            return Matrix.Identity(3)
        if st["swinging"]:
            s = st["swing_t"]
            pitch = .24 * (1 - smooth(clamp(s / .66, 0, 1)))
            pitch += .36 * math.sin(math.pi * s) ** 2 * (1 - s)
        else:
            pitch = .24 * smooth(clamp((st["phase"] / self.duty - .86) / .14, 0, 1))
        return rot(RIGHTV, pitch)

    @staticmethod
    def _hoof_contact_offset(st, basis):
        toe = st["toe_local"]
        return basis @ toe - (toe - st["sole_local"])

    def _hoof_upper_reach(self, lengths):
        a, b = lengths[:2]
        if self.profile == "walk":
            return math.sqrt(a * a + b * b + 2 * a * b * math.cos(HOOFED_WALK["knee_reserve"]))
        return a + b - .00001

    def _hoofed_chain(self, root, target, rest_axis, forward, lengths, swing):
        """Aim the distal span forward, then solve the thigh and shin to the hock."""
        a, b, c = lengths
        chord = target - root
        axis = chord.normalized() if chord.length_squared > 1e-10 else rest_axis.normalized()
        upper_max, upper_min = self._hoof_upper_reach(lengths), abs(a - b) + .00001
        min_reach = max(.00001, c - upper_max, upper_min - c)
        distance = clamp(chord.length, min_reach, upper_max + c)
        ankle = root + axis * distance
        forward -= axis * forward.dot(axis)
        if forward.length_squared < 1e-10:
            forward = RIGHTV - axis * RIGHTV.dot(axis)
        forward.normalize()
        limit = 2 * distance * c
        upper = math.acos(clamp((distance * distance + c * c - upper_max ** 2) / limit, -1, 1))
        lower = math.acos(clamp((distance * distance + c * c - upper_min ** 2) / limit, -1, 1))
        angle = clamp(.44 + .15 * swing, lower, upper)
        if self.profile == "walk":
            preferred = .44 + .15 * swing
            blend = max(0.0, 1 - abs(preferred - upper) / .10)
            angle = max(lower, angle - .025 * blend * blend)
        hock = ankle - (axis * math.cos(angle) + forward * math.sin(angle)) * c
        upper_chord = hock - root
        knee = two_span(root, upper_chord.normalized(), upper_chord.length, (a, b), forward)
        return [root, knee, hock, ankle]

    def _solve(self, st, target, is_leg):
        """Solve rigid spans, individual hinges, or multi-bend chains."""
        pb = st["l"]["parent_bone"]
        gp = self.G[pb]
        rj, lens = st["rest_j"], st["lengths"]
        n = len(rj)
        j = [gp @ (rj[k] - self.rest[pb]) for k in range(n)]
        root = j[0].copy()
        humanoid_leg = self.humanoid and is_leg
        hoofed = is_leg and "toe_local" in st
        if hoofed:
            end_b = self._hoof_basis(st)
            target = target - self._hoof_contact_offset(st, end_b)
        elif is_leg:
            pitch = .20 if humanoid_leg else .35
            end_b = rot(RIGHTV, -pitch * math.sin(math.pi * clamp(st["swing_t"], 0, 1))) if st["swinging"] else Matrix.Identity(3)
            target = target - (end_b @ st["sole_local"] if humanoid_leg else st["sole_local"])
        if hoofed:
            swing = math.sin(math.pi * st["swing_t"]) if st["swinging"] else 0.0
            if self.profile == "walk":
                swing = smooth(swing)
            j = self._hoofed_chain(root, target, j[-1] - root, gp.b @ BACKV, lens, swing)
        elif len(lens) == 1:
            d = target - root
            j[1] = root + (d if d.length_squared > 1e-10 else j[1] - root).normalized() * lens[0]
        elif len(lens) == 2:
            d = target - root
            distance = clamp(d.length, abs(lens[0] - lens[1]) + 1e-5, sum(lens) - 1e-5)
            axis = d.normalized() if d.length_squared > 1e-10 else (j[-1] - root).normalized()
            rest_axis = (rj[2] - rj[0]).normalized()
            rest_bend = rj[1] - rj[0]
            rest_bend -= rest_axis * rest_bend.dot(rest_axis)
            bend_hint = gp.b @ (BACKV if humanoid_leg else rest_bend)
            j = [root, two_span(root, axis, distance, lens, bend_hint), root + axis * distance]
        elif (target - root).length >= sum(lens) * 0.999:
            d = (target - root).normalized()
            for k in range(1, n):
                j[k] = j[k - 1] + d * lens[k - 1]
        else:
            for _ in range(12):
                j[-1] = target.copy()
                for k in range(n - 2, -1, -1):
                    j[k] = j[k + 1] + (j[k] - j[k + 1]).normalized() * lens[k]
                j[0] = root.copy()
                for k in range(1, n):
                    j[k] = j[k - 1] + (j[k] - j[k - 1]).normalized() * lens[k - 1]
                if (j[-1] - target).length < 0.001:
                    break
            for k in range(1, n - 1):
                rest_axis = (rj[k + 1] - rj[k - 1]).normalized()
                rest_bend = rj[k] - rj[k - 1]
                authored = gp.b @ (rest_bend - rest_axis * rest_bend.dot(rest_axis))
                chord = (j[k + 1] - j[k - 1]).normalized()
                offset = j[k] - j[k - 1]
                radial = offset - chord * offset.dot(chord)
                pole = authored - chord * authored.dot(chord)
                if chord.length_squared > 1e-10 and radial.dot(pole) < -1e-10:
                    j[k] = j[k - 1] + chord * offset.dot(chord) + pole.normalized() * radial.length
        for k, limits in enumerate(st["l"].get("bend_limits", ()), 1):
            if limits is None:
                continue
            low, high = map(math.radians, limits)
            correction = bend_correction(j[k] - j[k - 1], j[k + 1] - j[k], low, high)
            for i in range(k + 1, n):
                j[i] = j[k] + correction @ (j[i] - j[k])
        bones = st["bones"]
        prev = gp.b
        for k in range(n - 1):
            d0 = (gp.b @ (rj[k + 1] - rj[k])).normalized()
            d1 = (j[k + 1] - j[k]).normalized()
            b = arc(d0, d1) @ gp.b
            self._set(bones[k], X(b, j[k]))
            prev = b
        if not is_leg:
            end_b = prev
        self._set(bones[-1], X(end_b.copy(), j[-1]))
        self._pose_joint_support(st)
        open_ = max(self.track("mouth"), self.track("arms_up")) * 0.8 + 0.15 * (0.5 + 0.5 * self.osc(3.0, st["side"]))
        if self.action == "grasp" and _grasps(st["l"]):
            open_ = self.track("grasp")
        F = st["tip_frame"]
        for jw in st["jaws"]:
            r = F @ rot(jw["axis"], math.radians(jw["angle"]) * open_) @ F.inverted_safe()
            self._set(jw["bone"], self._carry(jw["bone"], r))

    def _pose_part(self, p, moving, idle_w):
        b, F, Fi = p["bone"], p["_F"], p["_Fi"]
        rloc = Matrix.Identity(3)
        ph = b * 0.37
        cap = p["cap"]
        if cap == "look":
            tl = self.otime % IDLE_LOOP
            blink = 1.0
            if idle_w > 0.5:
                for bt in (1.6, 4.3):
                    d = abs(tl - bt)
                    if d < 0.09:
                        blink = min(blink, 0.1 + 0.9 * d / 0.09)
            rloc = rot(BACKV, math.radians(10.0 * self.osc(1.0, 0.3)) * idle_w) @ Matrix.Diagonal((1, 1, blink))
        elif cap == "flop":
            a = 0.12 * self.osc(2.0, ph) * (0.5 + idle_w * 0.5) + clamp(self.bob_vel * 25.0, -0.4, 0.4) + 0.15 * moving * math.sin(TAU * self.gait_clock * 2.0)
            rloc = rot(RIGHTV, a)
        elif cap == "flap":
            a = 0.08 * self.osc(1.0, ph) * idle_w + 0.06 * math.sin(TAU * self.gait_clock) * moving + self.track("flap") * 0.75 * math.sin(self.time * 9.0)
            rloc = rot(BACKV, a)
        elif cap == "sway":
            rloc = rot(RIGHTV, 0.18 * self.osc(2.0, ph)) @ rot(BACKV, 0.12 * self.osc(1.0, ph * 2.0))
        self._set(b, self._carry(b, F @ rloc @ Fi))
        if cap == "mouth":
            open_ = self.track("mouth") + 0.06 * (0.5 + 0.5 * self.osc(1.0, 2.0)) * idle_w
            for jw in p["jaws"]:
                r = F @ rot(jw["axis"], math.radians(jw["angle"]) * open_) @ Fi
                self._set(jw["bone"], self._carry(jw["bone"], r))

    # ------------------------------------------------------------ blender
    def deform_matrices(self):
        """Per bone 4x4 deformation in recipe space: v_posed = D @ v_rest."""
        out = []
        for i, g in enumerate(self.G):
            m = g.b.to_4x4()
            m.translation = g.o - g.b @ self.rest[i]
            out.append(m)
        return out

    def posed_sole(self, st):
        end = st["bones"][-1]
        if "toe_local" in st:
            return self.world @ (self.G[end].o + self._hoof_contact_offset(st, self.G[end].b))
        return self.world @ (self.G[end] @ st["sole_local"])


C4 = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # recipe -> Blender
C4i = C4.inverted()


def write_pose(arm_ob, anim, names=None):
    """Apply the animator's pose to a Blender armature object (pose bones' matrix_basis)."""
    names = names or anim.rig["names"]
    bones = arm_ob.data.bones
    pbs = arm_ob.pose.bones
    D = anim.deform_matrices()
    M = []
    for i, nm in enumerate(names):
        M.append(C4 @ D[i] @ C4i @ bones[nm].matrix_local)
    for i, nm in enumerate(names):
        p = anim.parents[i]
        R = bones[nm].matrix_local
        if p >= 0:
            Rp = bones[names[p]].matrix_local
            basis = R.inverted() @ Rp @ M[p].inverted() @ M[i]
        else:
            basis = R.inverted() @ M[i]
        pbs[nm].matrix_basis = basis
    return M
