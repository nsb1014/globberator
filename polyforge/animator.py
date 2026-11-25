"""Procedural animator in the spirit of Spore (Hecker et al. 2008).

Derived entirely from the rig the builder produced:
  * legs plan world-space footprints and swing between them; FABRIK IK bends them
  * the body rides on the legs (bob, sway, lean) and sinks to keep every foot reachable;
    with no legs it slithers
  * neck/head and tail chains get look-around, wag and follow-through
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

IDLE_LOOP = 6.0
TAU = 2 * math.pi
UPV = Vector((0, 1, 0))
RIGHTV = Vector((1, 0, 0))
BACKV = Vector((0, 0, 1))
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
}


def clamp(x, a, b):
    return a if x < a else (b if x > b else x)


def rot(axis, angle):
    return Matrix.Rotation(angle, 3, Vector(axis))


def euler(x, y, z):
    """Godot's default YXZ basis: Ry * Rx * Rz."""
    return rot(UPV, y) @ rot(RIGHTV, x) @ rot(BACKV, z)


def move_toward(a, b, d):
    return b if abs(b - a) <= d else a + math.copysign(d, b - a)


def smooth(t):
    return t * t * (3 - 2 * t)


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
            {"leg": self.legs, "arm": self.arms}.get(l["role"], self.apps).append(st)
        for p in rig["parts"]:
            p["_F"] = Matrix(p["frame"])
            p["_Fi"] = p["_F"].inverted_safe()
        self._setup_gait()
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
        self.walk_speed = min(0.6 * L, cap) * self._freq("walk") / self._duty("walk")
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

    def _duty(self, p):
        n = len(self.legs)
        if n == 1:
            return 0.45 if p == "walk" else 0.35
        if p == "run":
            return 0.38 if n == 2 else (0.42 if n <= 4 else 0.45)
        return 0.6 if n == 2 else (0.65 if n <= 4 else 0.55)

    def _freq(self, p):
        s = 1.1 if p == "walk" else 1.75
        if len(self.legs) == 1:
            s *= 0.9
        return s / math.sqrt(self.leg_len)

    def cycle_length(self):
        return 1.0 / max(self._freq(self.profile), 0.01)

    # ------------------------------------------------------------ control
    @staticmethod
    def _ground(p):
        return Vector((p.x, 0.0, p.z))

    def reset(self):
        self.time = self.otime = self.gait_clock = 0.0
        for st in self.legs:
            st["plant"] = self._ground(self.world @ (st["rest_j"][-1] + st["sole_local"]))
            st["foot"] = st["plant"].copy()
            st["swinging"] = False
            st["phase"] = st["prev_phase"] = st["offset"]
        self.pose()

    def play(self, name):
        if name in ACTIONS:
            self.action, self.action_t = name, 0.0
            return
        self.clip = name
        if name == "walk":
            self.target_speed = self.speed = self.walk_speed
            self.profile = "walk"
        elif name == "run":
            self.target_speed = self.speed = self.run_speed
            self.profile = "run"
        else:
            self.target_speed = 0.0
        self._apply_profile()
        if name in ("walk", "run"):
            self._prime()

    def _apply_profile(self):
        self.duty = self._duty(self.profile)
        for st in self.legs:
            st["offset"] = st.get(self.profile + "_offset", st["offset"])

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
                st["lift_h"] = self.leg_len * (0.12 if self.profile == "walk" else 0.18)
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
        self.speed = move_toward(self.speed, self.target_speed, dt * max(self.walk_speed, 0.3) * 3.0)
        self.turn = move_toward(self.turn, self.target_turn, dt * 4.0)
        self.world.b = self.world.b @ rot(UPV, self.turn * dt)
        self.world.o = self.world.o + (self.world.b @ BACKV) * self.speed * dt
        if self.action:
            self.action_t += dt
            if self.action_t > ACTIONS[self.action]["length"]:
                self.action = ""
        self._gait(dt)
        idle_w = clamp(1.0 - abs(self.speed) / max(self.walk_speed, 0.01) * 1.5, 0.0, 1.0)
        rate = (self.gait_freq * IDLE_LOOP) if self.legs else 1.0
        self.otime += dt * (rate + (1.0 - rate) * idle_w)
        self.pose()

    def _gait(self, dt):
        if not self.legs:
            self.slither_phase += (abs(self.speed) / max(self.rig["body_len"] * 0.6, 0.1) + (0.25 if self.moving() else 0.0)) * dt
            return
        f = self._freq(self.profile)
        ref = self.walk_speed if self.profile == "walk" else self.run_speed
        self.gait_freq = max(f * clamp(abs(self.speed) / max(ref, 0.01), 0.0, 1.6), 0.6 * f)
        mv = self.moving()
        if mv:
            self.gait_clock += self.gait_freq * dt
        duty = self.duty
        for st in self.legs:
            ph = (self.gait_clock + st["offset"]) % 1.0
            prev = st["prev_phase"]
            st["phase"] = st["prev_phase"] = ph
            crossed = (prev < duty <= ph) or (ph < prev and (prev < duty or ph >= duty))
            if not st["swinging"]:
                drift = (st["plant"] - self._rest_footprint(st, 0.0)).length
                lift = (mv and crossed) or (not mv and drift > 0.12 * self.leg_len and not self._neighbor_swinging(st))
                if lift:
                    st["swinging"] = True
                    st["swing_t"] = 0.0
                    st["swing_dur"] = (1.0 - duty) / self.gait_freq if mv else 0.22 * math.sqrt(self.leg_len)
                    st["lift"] = st["plant"].copy()
                    st["lift_h"] = self.leg_len * (0.12 if self.profile == "walk" else 0.18)
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

    def pose(self):
        rig, G = self.rig, self.G
        self.flag = [False] * len(self.rest)
        inv = self.world.inv()
        moving = clamp(abs(self.speed) / max(self.walk_speed, 0.01), 0.0, 1.5)
        idle_w = clamp(1.0 - moving * 1.5, 0.0, 1.0)
        self._set(0, X())
        spine, hub = rig["spine"], rig["hub"]
        hub_bone = spine[hub]
        off = Vector()
        pitch = roll = 0.0
        crouch = self.track("crouch") * max(self.leg_len, rig["body_h"])
        jump = self.track("jump") * max(self.leg_len * 0.6, rig["body_h"] * 0.8)
        legs = self.legs
        if legs:
            swinging, lateral = 0, 0.0
            for st in legs:
                if st["swinging"]:
                    swinging += 1
                    lateral -= st["side"] * math.sin(math.pi * st["swing_t"])
            sf = swinging / len(legs)
            if len(legs) == 1:
                st0 = legs[0]
                off.y += math.sin(math.pi * clamp(st0["swing_t"], 0, 1)) * self.leg_len * 0.25 if st0["swinging"] else 0.0
            elif self.moving():
                off.y += -0.035 * self.leg_len * (1.0 - abs(sf - 0.5) * 2.0) * (1.6 if self.profile == "run" else 1.0)
            if len(legs) == 2:
                off.x += lateral * 0.06 * self.leg_len
                roll += lateral * 0.04
            pitch += 0.05 * clamp(self.speed / max(self.walk_speed, 0.01), -1.0, 2.0)
            roll += -self.turn * 0.06
        off.y += 0.012 * rig["body_h"] * self.osc(2.0) * idle_w
        off.y += -crouch + jump
        hb = euler(pitch, 0.0, roll)
        pivot = self.rest[hub_bone]
        if legs and jump <= 0.0:
            hx = X(hb, pivot + off)
            drop = 0.0
            for st in legs:
                tgt = inv @ st["foot"] - st["sole_local"]
                hip = hx @ (st["rest_j"][0] - pivot)
                maxr = st["length"] * 0.965
                dxz = math.hypot(hip.x - tgt.x, hip.z - tgt.z)
                allowed = tgt.y + (math.sqrt(maxr * maxr - dxz * dxz) if dxz < maxr else 0.0)
                drop = max(drop, hip.y - allowed)
            off.y -= min(drop, 0.45 * self.leg_len)
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
        head_pitch = math.radians(self.track("head_pitch")) + 0.04 * math.sin(TAU * self.gait_clock * 2.0) * moving
        shake = math.radians(14.0) * self.track("shake") * math.sin(self.time * 18.0)
        tilt = math.radians(self.track("head_tilt"))
        for i in range(hub + 1, n):
            share = 1.0 / max(front, 1)
            lag = (i - hub) / max(front, 1)
            walk_yaw = -0.03 * math.sin(TAU * self.gait_clock) * moving * lag if legs else 0.0
            q = euler(head_pitch * share, (look_yaw + shake) * share + walk_yaw, tilt * share)
            if not legs:
                q = rot(UPV, self._slither(i)) @ q
            self._set(spine[i], self._carry(spine[i], q))
        # tail
        wag_amp = 0.12 + 0.35 * self.track("wave") * (1.0 if not self.arms else 0.0)
        for i in range(hub - 1, -1, -1):
            k = hub - i
            if not legs:
                q = rot(UPV, self._slither(i))
            else:
                wag = wag_amp * math.sin(TAU * (2.0 + 6.0 * self.track("wave")) * self.otime / IDLE_LOOP - k * 0.7) * (0.4 + 0.6 * idle_w)
                wag += 0.1 * math.sin(TAU * self.gait_clock - k * 0.8) * moving
                droop = 0.03 * k * (1.0 - moving * 0.5) + 0.04 * self.osc(2.0, k) * idle_w
                q = euler(-droop - pitch / max(hub, 1), wag / max(hub, 1) * 1.5, 0.0)
            self._set(spine[i], self._carry(spine[i], q))
        # limbs
        for st in legs:
            target = inv @ st["foot"]
            if jump > 0.0:
                target = target + UPV * jump * 0.85
            self._solve(st, target - st["sole_local"], True)
        for ai, st in enumerate(self.arms):
            base = self._rest_end(st)
            L = st["length"]
            swing = math.sin(TAU * (self.gait_clock + (0.0 if st["side"] > 0 else 0.5))) * 0.35 * L * min(moving, 1.2)
            t = base + Vector((0, 0, swing)) + Vector((0, 0.03 * L * self.osc(2.0, ai), 0)) * idle_w
            up_w = self.track("arms_up")
            if up_w > 0.0:
                head = G[spine[-1]].o
                hip = self._hip_now(st)
                raised = hip + Vector((st["side"] * 0.35 * L, 0.85 * L, 0.15 * L))
                raised.y = max(raised.y, head.y + 0.1 * L)
                t = t.lerp(raised, up_w)
            wv = self.track("wave")
            if wv > 0.0 and ai == 0:
                hip = self._hip_now(st)
                t = t.lerp(hip + Vector((st["side"] * (0.45 + 0.25 * math.sin(self.time * 9.0)) * L, 0.75 * L, 0.2 * L)), wv)
            self._solve(st, t, False)
        for ai, st in enumerate(self.apps):
            if st["l"]["role"] == "tail":
                for k, bone in enumerate(st["bones"]):
                    phase = TAU * self.otime / IDLE_LOOP * 2 - k * 0.65
                    wag = math.sin(phase) * (0.11 + 0.09 * moving)
                    self._set(bone, self._carry(bone, euler(0.035 * math.cos(phase), wag, 0)))
                continue
            L = st["length"]
            sway = Vector((self.osc(1.0, ai), 0.5 * self.osc(2.0, ai * 2.0 + 1.5), self.osc(1.0, ai + 0.7))) * 0.08 * L
            sway += Vector((0, 0.06 * L * self.bob_vel * 30.0, -0.15 * L * moving))
            sway += Vector((st["side"] * 0.3, 0.6, 0.2)) * L * self.track("arms_up")
            self._solve(st, self._rest_end(st) + sway, False)
        for p in rig["parts"]:
            self._pose_part(p, moving, idle_w)
        for i in range(len(self.rest)):
            if not self.flag[i]:
                self._set(i, self._carry(i))

    def _slither(self, i):
        amp = 0.18 + 0.14 * clamp(abs(self.speed) / max(self.walk_speed, 0.01), 0.0, 1.0)
        return amp * math.sin(TAU * self.slither_phase - i * 1.1) * 0.6

    def _hip_now(self, st):
        p = st["l"]["parent_bone"]
        return self.G[p] @ (st["rest_j"][0] - self.rest[p])

    def _rest_end(self, st):
        p = st["l"]["parent_bone"]
        return self.G[p] @ (st["rest_j"][-1] - self.rest[p])

    def _solve(self, st, target, is_leg):
        """FABRIK from the rest shape carried by the parent bone."""
        pb = st["l"]["parent_bone"]
        gp = self.G[pb]
        rj, lens = st["rest_j"], st["lengths"]
        n = len(rj)
        j = [gp @ (rj[k] - self.rest[pb]) for k in range(n)]
        root = j[0].copy()
        if (target - root).length >= sum(lens) * 0.999:
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
        bones = st["bones"]
        prev = gp.b
        for k in range(n - 1):
            d0 = (gp.b @ (rj[k + 1] - rj[k])).normalized()
            d1 = (j[k + 1] - j[k]).normalized()
            b = arc(d0, d1) @ gp.b
            self._set(bones[k], X(b, j[k]))
            prev = b
        end_b = prev
        if is_leg:
            end_b = rot(RIGHTV, -0.35 * math.sin(math.pi * clamp(st["swing_t"], 0, 1))) if st["swinging"] else Matrix.Identity(3)
        self._set(bones[-1], X(end_b.copy(), j[-1]))
        open_ = max(self.track("mouth"), self.track("arms_up")) * 0.8 + 0.15 * (0.5 + 0.5 * self.osc(3.0, st["side"]))
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
