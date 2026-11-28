"""Run with blender -b --python-exit-code 1 -P tools/tests/blender_locomotion.py."""
import json
import math
from pathlib import Path
import struct
import sys
import tempfile

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from polyforge import baker, builder, export, recipe
from polyforge.animator import Animator, LEGACY_CLIPS


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def specimen(profile=None, *, tail=False, fins=False, wings=False, gestures=False, metaball=False):
    source = recipe.default_recipe()
    source["name"] = profile or "ground"
    if metaball:
        source["construction"] = "metaball"
    for ring in source["spine"]:
        ring["y"] = .48
    if profile:
        source["locomotion"] = profile
    if tail:
        source["limbs"].append({"uid": "tail", "family": "tail_flexible", "u": .06, "theta": 90})
    if fins:
        source["parts"].append({"uid": "fins", "part": "fin_paired", "u": .62, "theta": -22})
    if wings:
        source["limbs"].append({"uid": "wings", "family": "wing_feathered", "u": .68, "theta": 28})
    if gestures:
        source["limbs"].append({"uid": "arms", "u": .55, "theta": -22, "tip": "hand_pincer",
                               "segments": [[.22, -.18, 0], [.04, -.14, .18]]})
        source["parts"].append({"uid": "mouth", "part": "mouth_jaws", "u": .95, "theta": -90})
    return builder.build(source, "preview")


def sample(anim, clip):
    assert anim.play(clip)
    start = [transform.copy() for transform in anim.G]
    frames = 32
    poses = []
    for _ in range(frames):
        poses.append([transform.copy() for transform in anim.G])
        for limb in anim.rig["limbs"]:
            bones, joints = limb["bones"], [Vector(j) for j in limb["joints"]]
            rest_spans = [b - a for a, b in zip(joints, joints[1:])]
            posed_spans = [anim.G[b].o - anim.G[a].o for a, b in zip(bones, bones[1:])]
            for rest_span, posed_span in zip(rest_spans, posed_spans):
                assert abs(posed_span.length - rest_span.length) < 4e-6
            if limb["role"] == "wing":
                for k, (a, b) in enumerate(zip(rest_spans, rest_spans[1:])):
                    normal = a.cross(b)
                    if normal.length_squared > 1e-8:
                        posed = posed_spans[k].cross(posed_spans[k + 1])
                        expected = anim.G[bones[k]].b @ normal
                        assert posed.normalized().dot(expected.normalized()) > .995
            for k, support in enumerate(limb.get("joint_support", ()), 1):
                assert (anim.G[support].o - anim.G[bones[k]].o).length < 4e-6
        anim.step(anim.cycle_length() / frames)
    for a, b in zip(start, anim.G):
        assert (a.o - b.o).length < 3e-6
        assert abs(a.b.to_quaternion().dot(b.b.to_quaternion())) > .99999
    assert anim.world.o.z > 0.0
    return poses


def matrix_values(scene, arm, at):
    frame = math.floor(at)
    scene.frame_set(frame, subframe=at - frame)
    evaluated = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return tuple(v for bone in evaluated.pose.bones for row in bone.matrix for v in row)


def check_bake(result, clips):
    arm = result["armature"]
    assert tuple(baker.bake_all(arm, clips)) == tuple(clips)
    for track in arm.animation_data.nla_tracks:
        track.mute = False
        scene = bpy.context.scene
        strip = track.strips[0]
        start, end = strip.frame_start, strip.frame_end
        first, last = matrix_values(scene, arm, start), matrix_values(scene, arm, end)
        left = matrix_values(scene, arm, end - .01)
        right = matrix_values(scene, arm, start + .01)
        center = matrix_values(scene, arm, start + .29 * (end - start))
        assert max(abs(a - b) for a, b in zip(first, last)) < 3e-6
        assert max(abs(a - b) for a, b in zip(first, right)) > 1e-5
        assert max(abs(a - b) for a, b in zip(first, center)) > .01
        assert max(abs(a - b) for a, b in zip(first[:16], center[:16])) < 3e-6
        assert max(abs((d - a) - (b - c)) for a, b, c, d in zip(first, last, left, right)) < 2e-5
        track.mute = True


def same_pose(a, b):
    return all((x.o - y.o).length < 3e-6 and abs(x.b.to_quaternion().dot(y.b.to_quaternion())) > .99999
               for x, y in zip(a.G, b.G))


def check_transitions():
    reset()
    result = specimen("flight", wings=True, fins=True, metaball=True)
    rig, arm = result["rig"], result["armature"]
    anim = Animator(rig)
    assert anim.clips == ("idle", "fly", "glide", "fly_to_glide", "glide_to_fly")
    for clip, source, target in (("fly_to_glide", "fly", "glide"), ("glide_to_fly", "glide", "fly")):
        reference = Animator(rig)
        anim.play(clip)
        reference.play(source)
        assert same_pose(anim, reference) and abs(anim.speed - reference.speed) < 1e-7
        anim.step(anim.cycle_length())
        reference.play(target)
        assert same_pose(anim, reference) and abs(anim.speed - reference.speed) < 1e-7
        anim.step(.071)
        reference.step(.071)
        assert same_pose(anim, reference)

    travel = {}
    assert tuple(baker.bake_all(arm, travel=travel)) == anim.clips
    assert set(travel) == set(anim.clips) - {"idle"}
    with tempfile.TemporaryDirectory() as output:
        glb = export.export(result, str(Path(output) / "flight.glb"))
        data = Path(glb).read_bytes()
        size = struct.unpack_from("<I", data, 12)[0]
        assert {action["name"] for action in json.loads(data[20:20 + size])["animations"]} == set(anim.clips)
        reset()
        bpy.ops.import_scene.gltf(filepath=glb)
        assert all(any(action.name.startswith(f"{clip}_") for action in bpy.data.actions) for clip in anim.clips)

    reset()
    result = specimen("axial_lateral", tail=True, metaball=True)
    anim, reference = Animator(result["rig"]), Animator(result["rig"])
    assert anim.clips == ("idle", "swim", "swim_turn")
    anim.play("swim_turn")
    reference.play("swim")
    assert same_pose(anim, reference)
    anim.step(anim.cycle_length())
    assert same_pose(anim, reference)
    forward = anim.world.b @ Vector((0, 0, 1))
    assert abs(math.degrees(math.atan2(forward.x, forward.z)) - 30) < 2e-5
    assert anim.world.o.x > .3
    travel = {}
    baker.bake_all(result["armature"], travel=travel)
    turn = travel["swim_turn"]["samples"]
    assert turn[0] == [0, 0, 0, 0] and abs(turn[-1][3] - 30) < 1e-5
    assert .5 < turn[len(turn) // 2][3] < 29.5


def run():
    reset()
    rig = specimen(wings=True, fins=True)["rig"]
    anim = Animator(rig)
    assert anim.clips == LEGACY_CLIPS
    assert not any(anim.play(clip) for clip in ("swim", "fly", "glide"))
    empty = dict(rig, limbs=[], parts=[])
    assert Animator(dict(empty, locomotion="flight")).clips == LEGACY_CLIPS
    assert Animator(dict(empty, locomotion="paddling")).clips == LEGACY_CLIPS

    for profile, axis in (("axial_vertical", 1), ("axial_lateral", 0)):
        reset()
        result = specimen(profile, tail=True)
        anim = Animator(result["rig"])
        assert anim.clips == (*LEGACY_CLIPS, "swim") and not anim.play("fly")
        tail = next(limb["bones"][-1] for limb in anim.rig["limbs"] if limb["role"] == "tail")
        poses = sample(anim, "swim")
        amplitude = max(pose[tail].o[axis] for pose in poses) - min(pose[tail].o[axis] for pose in poses)
        drift = max(pose[tail].o[1 - axis] for pose in poses) - min(pose[tail].o[1 - axis] for pose in poses)
        assert amplitude > .12 and drift < amplitude * .08
        check_bake(result, ["swim"])

    reset()
    result = specimen("paddling", fins=True, wings=True)
    anim = Animator(result["rig"])
    assert anim.clips == (*LEGACY_CLIPS, "swim") and not anim.play("fly")
    fin = next(p["bone"] for p in anim.rig["parts"] if p["cap"] == "paddle")
    poses = sample(anim, "swim")
    assert poses[7][fin].b.to_quaternion().rotation_difference(poses[23][fin].b.to_quaternion()).angle > .5
    check_bake(result, ["swim"])

    reset()
    result = specimen("flight", fins=True, wings=True)
    anim = Animator(result["rig"])
    assert anim.clips == (*LEGACY_CLIPS, "fly", "glide") and not anim.play("swim")
    wing = next(limb["bones"][-1] for limb in anim.rig["limbs"] if limb["role"] == "wing")
    excursions = {}
    for clip in ("fly", "glide"):
        poses = sample(anim, clip)
        excursions[clip] = max(pose[wing].o.y for pose in poses) - min(pose[wing].o.y for pose in poses)
    assert excursions["fly"] > .3 and excursions["glide"] < .20 * excursions["fly"]
    check_bake(result, ["fly", "glide"])
    reset()
    result = specimen("crawl", metaball=True)
    anim = Animator(result["rig"])
    assert anim.clips == ("idle", "crawl")
    sample(anim, "crawl")
    check_bake(result, ["crawl"])
    reset()
    result = specimen(gestures=True, metaball=True)
    anim = Animator(result["rig"])
    assert set(anim.clips) == {"idle", "roar", "wave", "reach", "grasp", "bite"}
    arm = next(limb for limb in anim.rig["limbs"] if limb["role"] == "arm")
    hand, claw = arm["bones"][-1], arm["jaws"][0]["bone"]
    mouth = next(part["jaws"][0]["bone"] for part in anim.rig["parts"] if part["cap"] == "mouth")
    anim.play("grasp")
    base = anim.G[hand].o.copy()
    anim.advance_to(.67)
    assert (anim.G[hand].o - base).length > .07
    open_claw = anim.G[hand].b.inverted() @ anim.G[claw].b
    anim.advance_to(1.12)
    closed_claw = anim.G[hand].b.inverted() @ anim.G[claw].b
    assert open_claw.to_quaternion().rotation_difference(closed_claw.to_quaternion()).angle > .35
    anim.play("bite")
    anim.step(.38)
    open_mouth = anim.G[anim.parents[mouth]].b.inverted() @ anim.G[mouth].b
    anim.step(.17)
    closed_mouth = anim.G[anim.parents[mouth]].b.inverted() @ anim.G[mouth].b
    assert open_mouth.to_quaternion().rotation_difference(closed_mouth.to_quaternion()).angle > .35
    assert set(baker.bake_all(result["armature"])) == set(anim.clips)
    check_transitions()
    print("Blender motion gates, joint spans, subframes, transitions, root travel and GLB export passed")


if __name__ == "__main__":
    run()
