"""Bake procedural motion into Blender actions (one NLA track per clip) so every
exporter (glTF, FBX, USD) carries all clips."""
import json
import math

import bpy

from .animator import (
    ACTIONS, BACKV, FREE_CLIPS, FREE_LOOPS, GROUND_CLIPS, IDLE_LOOP, LEGACY_CLIPS,
    Animator, available_clips, write_pose,
)

FPS = 30
CLIPS = list(LEGACY_CLIPS)
SMOOTH_LOOPS = (*FREE_LOOPS, "crawl")


def rig_of(arm):
    return json.loads(arm["polyforge_rig"])


def _record(arm, rig, clip, contacts=None):
    an = Animator(rig)
    if clip not in an.clips:
        raise ValueError(f"Clip {clip!r} is unavailable. Available clips: {', '.join(an.clips)}")
    loop, frames, dt = True, 0, 1.0 / FPS
    if clip == "idle":
        an.play("idle")
        an.advance_to(IDLE_LOOP)
        length = IDLE_LOOP
    elif clip in GROUND_CLIPS:
        an.play(clip)
        cyc = an.cycle_length() if an.legs or clip == "crawl" else 1.0 / max(an._slither_rate(), 0.05)
        frames = max(8, round(cyc * FPS))
        dt = cyc / frames
        for _ in range(frames * 3):
            an.step(dt)
        length = cyc
    elif clip in FREE_CLIPS:
        an.play(clip)
        length = an.cycle_length()
        loop = clip in FREE_LOOPS
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
    roots = [] if clip in (*FREE_CLIPS, *GROUND_CLIPS) else None
    initial = an.world.inv()
    for f in range(frames + 1):
        if contacts is not None and clip == "walk" and f < frames:
            standing = [leg for leg in an.legs if not leg["swinging"]]
            frame = {"time": f / FPS, "travel": list(an.world.o),
                     "stance": [rig["names"][leg["bones"][-1]] for leg in standing]}
            toes = [rig["names"][leg["bones"][-1]] for leg in standing
                    if "toe_local" in leg and an._hoof_basis(leg)[1][2] < -1e-6]
            if toes:
                frame["toe_stance"] = toes
            contacts.append(frame)
        if roots is not None:
            transform = initial @ an.world
            forward = transform.b @ BACKV
            heading = math.degrees(math.atan2(forward.x, forward.z))
            roots.append([*(round(float(v), 7) for v in transform.o), round(heading, 6)])
        write_pose(arm, an)
        pose = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()) for pb in arm.pose.bones}
        if poses and (clip in FREE_CLIPS or clip == "crawl"):
            for name, (_, rotation, _) in pose.items():
                if rotation.dot(poses[-1][name][1]) < 0.0:
                    rotation.negate()
        poses.append(pose)
        if f < frames:
            an.step(dt)
    if loop:
        poses[-1] = poses[0]
    return poses, length, loop, roots


def _smooth_curves(action, slot, loop):
    if slot is not None and action.layers:
        curves = action.layers[0].strips[0].channelbag(slot).fcurves
    else:
        curves = action.fcurves
    for curve in curves:
        keys = curve.keyframe_points
        if len(keys) < 3:
            continue
        if loop:
            curve.modifiers.new("CYCLES")
        for i, key in enumerate(keys):
            frame, value = key.co
            # Loops duplicate the first key at the endpoint. Give both copies
            # the same centered tangent. Transitions retain endpoint velocity.
            if not loop and i == 0:
                tangent = (-3 * value + 4 * keys[1].co.y - keys[2].co.y) * .5
            elif not loop and i == len(keys) - 1:
                tangent = (3 * value - 4 * keys[i - 1].co.y + keys[i - 2].co.y) * .5
            else:
                previous = keys[i - 1 if i else len(keys) - 2]
                following = keys[i + 1 if i < len(keys) - 1 else 1]
                tangent = (following.co.y - previous.co.y) * .5
            key.interpolation = "BEZIER"
            key.handle_left_type = key.handle_right_type = "FREE"
            key.handle_left = (frame - 1 / 3, value - tangent / 3)
            key.handle_right = (frame + 1 / 3, value + tangent / 3)
        curve.update()


def bake(arm, clip, contacts=None):
    rig = rig_of(arm)
    poses, length, loop, roots = _record(arm, rig, clip, contacts)
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
    if clip in FREE_CLIPS or clip == "crawl":
        _smooth_curves(act, getattr(arm.animation_data, "action_slot", None), loop)
    act["polyforge_loop"] = loop
    act["polyforge_length"] = length
    if roots is not None:
        act["polyforge_root_travel"] = json.dumps({
            "fps": FPS, "columns": ["x", "y", "z", "yaw_degrees"], "samples": roots,
        })
    return act


def bake_all(arm, clips=None, contacts=None, travel=None):
    available = available_clips(rig_of(arm))
    clips = available if clips is None else tuple(clips)
    for clip in clips:
        if clip not in available:
            raise ValueError(f"Clip {clip!r} is unavailable. Available clips: {', '.join(available)}")
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
        if travel is not None and "polyforge_root_travel" in act:
            travel[clip] = json.loads(act["polyforge_root_travel"])
    ad.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    return out
