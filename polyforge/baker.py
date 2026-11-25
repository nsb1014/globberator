"""Bake procedural motion into Blender actions (one NLA track per clip) so every
exporter (glTF, FBX, USD) carries all clips."""
import json

import bpy

from .animator import Animator, ACTIONS, IDLE_LOOP, write_pose

FPS = 30
CLIPS = ["idle", "walk", "run", "roar", "wave", "hop"]


def rig_of(arm):
    return json.loads(arm["polyforge_rig"])


def _record(arm, rig, clip, contacts=None):
    an = Animator(rig)
    loop, frames, dt = True, 0, 1.0 / FPS
    if clip == "idle":
        an.play("idle")
        an.advance_to(IDLE_LOOP)
        length = IDLE_LOOP
    elif clip in ("walk", "run"):
        an.play(clip)
        cyc = an.cycle_length() if an.legs else 1.0 / max(an.speed / max(rig["body_len"] * 0.6, 0.1) + 0.25, 0.05)
        frames = max(8, round(cyc * FPS))
        dt = cyc / frames
        for _ in range(frames * 3):
            an.step(dt)
        length = cyc
    else:
        an.play("idle")
        an.advance_to(IDLE_LOOP)
        an.play(clip)
        length = ACTIONS[clip]["length"]
        loop = False
    if frames == 0:
        frames = round(length * FPS)
        dt = length / frames
    poses = []
    for f in range(frames + 1):
        if contacts is not None and clip == "walk" and f < frames:
            contacts.append({"time": f / FPS, "travel": list(an.world.o),
                             "stance": [rig["names"][leg["bones"][-1]] for leg in an.legs if not leg["swinging"]]})
        write_pose(arm, an)
        poses.append({pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in arm.pose.bones})
        an.step(dt)
    if loop:
        poses[-1] = poses[0]
    return poses, length, loop


def bake(arm, clip, contacts=None):
    rig = rig_of(arm)
    poses, length, loop = _record(arm, rig, clip, contacts)
    act = bpy.data.actions.new("%s_%s" % (arm.name.replace("_rig", ""), clip))
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    for f, pose in enumerate(poses):
        for pb in arm.pose.bones:
            loc, q, s = pose[pb.name]
            pb.location, pb.rotation_quaternion, pb.scale = loc, q, s
            pb.keyframe_insert("location", frame=f + 1, group=pb.name)
            pb.keyframe_insert("rotation_quaternion", frame=f + 1, group=pb.name)
            if (s - s.__class__((1, 1, 1))).length > 1e-4 or f == 0:
                pb.keyframe_insert("scale", frame=f + 1, group=pb.name)
    act["polyforge_loop"] = loop
    act["polyforge_length"] = length
    return act


def bake_all(arm, clips=CLIPS, contacts=None):
    bpy.context.scene.render.fps = FPS
    ad = arm.animation_data_create()
    # Rebaking replaces the previous clips: drop their (fake-user protected) actions too.
    stale = {st.action for t in ad.nla_tracks for st in t.strips if st.action is not None}
    if ad.action is not None:
        stale.add(ad.action)
    ad.action = None
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    for act in stale:
        act.use_fake_user = False
        if act.users == 0:
            bpy.data.actions.remove(act)
    out = {}
    for clip in clips:
        act = bake(arm, clip, contacts)
        track = ad.nla_tracks.new()
        track.name = clip
        strip = track.strips.new(clip, 1, act)
        strip.name = clip
        track.mute = True
        out[clip] = act["polyforge_length"]
    ad.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    return out
