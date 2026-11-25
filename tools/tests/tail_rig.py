"""Reimport a built GLB and check the tail skin and both animation clips.

blender -b --python-exit-code 1 -P tools/tests/tail_rig.py -- godot/bull.glb
Add --paired for a recipe with a lateral tail socket.
"""
import argparse
import sys
from pathlib import Path

import bpy

parser = argparse.ArgumentParser()
parser.add_argument("model", type=Path)
parser.add_argument("--paired", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(args.model.resolve()))
rig = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
mesh = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
segments = ("Tail", "TailMid", "TailTip")
suffixes = (".L", ".R") if args.paired else ("",)
expected = {name + suffix for name in segments for suffix in suffixes}
assert {b.name for b in rig.data.bones if b.name.startswith("Tail")} == expected

for suffix in suffixes:
    root, middle, tip = [rig.data.bones[name + suffix] for name in segments]
    assert root.parent.name == "Pelvis" and middle.parent == root and tip.parent == middle
    if suffix:
        assert root.head_local.x * (1 if suffix == ".L" else -1) > .01
    else:
        assert abs(root.head_local.x) < 1e-5 and abs(tip.head_local.x) > .1
    chain = {mesh.vertex_groups[b.name].index for b in (root, middle, tip)}
    weighted = set()
    transitions = set()
    for v in mesh.data.vertices:
        groups = {g.group for g in v.groups if g.weight > .001}
        if groups & chain:
            assert groups <= chain, "Tail vertex bound outside its chain"
            weighted.update(groups)
            if len(groups) == 2:
                transitions.add(frozenset(groups))
    assert weighted == chain
    for a,b in [(root,middle),(middle,tip)]:
        assert frozenset(mesh.vertex_groups[n.name].index for n in (a,b)) in transitions

for track in rig.animation_data.nla_tracks:
    track.mute = True
for clip in ("Idle", "Walk"):
    action = next(a for a in bpy.data.actions if a.name.startswith(clip))
    rig.animation_data.action = action
    start, end = map(round, action.frame_range)
    rotations = {name: [] for name in expected}
    for frame in range(start, end+1, 2):
        bpy.context.scene.frame_set(frame)
        for name in expected:
            pb = rig.pose.bones[name]
            rotations[name].append(pb.matrix_basis.to_quaternion())
            if name in {"Tail"+s for s in suffixes}:
                pelvis = pb.parent
                rest = pelvis.bone.matrix_local.inverted() @ pb.bone.head_local
                assert (pb.head - pelvis.matrix @ rest).length < 1e-4, "Root detached"
    for name, samples in rotations.items():
        assert max(samples[0].rotation_difference(q).angle for q in samples) > .02, (clip, name)
        assert samples[0].rotation_difference(samples[-1]).angle < .002, (clip, name, "loop")
print(f"PASS: {len(suffixes)} attached tail chain(s), blended joints and local motion in Idle and Walk")
