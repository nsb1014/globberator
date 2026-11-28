"""Export and reimport incumbent and metaball pilots entirely in Blender.

blender -b -t 2 --python-exit-code 1 -P tools/tests/metaball_pilots.py -- out/metaball-pilots minotaur dolphin bat
"""

import argparse
import json
from pathlib import Path
import runpy
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from polyforge import asset_validation, baker, builder, export, recipe, render
from polyforge.animator import available_clips


PILOTS = {
    "minotaur": ("examples/minotaur.json", "walk"),
    "bull": ("examples/bull.json", "walk"),
    "spider": ("examples/spider.json", "walk"),
    "dolphin": ("examples/pilots/dolphin.json", "swim"),
    "bat": ("examples/pilots/bat.json", "fly"),
}
REST_VIEWS = {
    "front": 0, "front-right": 45, "side": 90, "rear-right": 135,
    "rear": 180, "rear-left": 225, "left": 270, "front-left": 315,
}


def station_definitions(rig, mode):
    stations = {}
    for limb in rig["limbs"]:
        if limb["role"] == "wing":
            root, end = [rig["names"][idx] for idx in limb["bones"][:2]]
            host = rig["names"][limb["parent_bone"]]
            stations[f"{limb['name']}_root"] = ("crease", (host, root, end))
            continue
        if limb["role"] not in ("leg", "arm"):
            continue
        names = [rig["names"][idx] for idx in limb["bones"]]
        for index in range(1, len(names) - 1):
            stations[f"{limb['name']}_join_{index}"] = ("crease", names[index - 1:index + 2])
        stations[f"{limb['name']}_midspan"] = ("midspan", names[:2])
    if mode == "swim":
        spine = [rig["names"][idx] for idx in rig["spine"]]
        for index in sorted({1, len(spine) // 3, len(spine) // 2}):
            if index < len(spine) - 1:
                stations[f"axial_join_{index}"] = ("crease", spine[index - 1:index + 2])
        for index in sorted({1, len(spine) // 2}):
            if index + 1 < len(spine):
                stations[f"axial_span_{index}"] = ("midspan", spine[index:index + 2])
    return stations


def measure(arm, meshes, definitions, *, shell_union=False):
    bpy.context.view_layer.update()
    planes = {}
    for name, (kind, bones) in definitions.items():
        points = [arm.matrix_world @ arm.pose.bones[key].head for key in bones]
        if kind == "crease":
            origin = points[1]
            normal = (origin - points[0]).normalized() + (points[2] - origin).normalized()
            if normal.length < 1e-5:
                normal = points[2] - origin
        else:
            origin = points[0].lerp(points[1], .5)
            normal = points[1] - points[0]
        direction = normal.cross(Vector((1, 0, 0)))
        if direction.length < .01 * normal.length:
            direction = normal.cross(Vector((0, 1, 0)))
        planes[name] = {"origin": origin, "normal": normal, "direction": direction}
    groups = {name: bones[:-1] if kind == "crease" else bones[:1]
              for name, (kind, bones) in definitions.items()} if shell_union else None
    return asset_validation.measure_evaluated_sections(meshes, planes, shell_union=shell_union, bone_groups=groups)


def phase_frame(scene, action, phase):
    start, end = action.frame_range
    frame = start + (end - start) * phase
    scene.frame_set(int(frame), subframe=frame % 1)


def frame_motion(camera, meshes, scene, action, mode):
    """Frame all sampled poses with one camera so moving tips stay visible."""
    render.clay_camera(camera, meshes, 48 if mode == "fly" else 65, 26 if mode == "fly" else 9)
    view = camera.rotation_euler.to_matrix().transposed()
    corners = []
    for index in range(16):
        phase_frame(scene, action, (index + .5) / 16)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for obj in meshes:
            evaluated = obj.evaluated_get(depsgraph)
            corners.extend(view @ (evaluated.matrix_world @ Vector(corner))
                           for corner in evaluated.bound_box)
    low = [min(point[axis] for point in corners) for axis in (0, 1)]
    high = [max(point[axis] for point in corners) for axis in (0, 1)]
    center = view @ camera.location
    center.x, center.y = [(a + b) / 2 for a, b in zip(low, high)]
    camera.location = view.transposed() @ center
    camera.data.ortho_scale = max(b - a for a, b in zip(low, high)) * 1.20


def propulsion_check(arm, rig, mode, action, duration):
    scene = bpy.context.scene

    def point(bone):
        return arm.matrix_world @ arm.pose.bones[rig["names"][bone]].head

    if mode == "swim":
        flukes = next(part["bone"] for part in rig["parts"] if part["part"] == "flukes_cetacean")
        offsets = []
        hub = rig["spine"][rig["hub"]]
        for index in range(40):
            phase_frame(scene, action, index / 40)
            offsets.append(point(flukes) - point(hub))
        vertical = max(value.z for value in offsets) - min(value.z for value in offsets)
        lateral = max(value.x for value in offsets) - min(value.x for value in offsets)
        relative = vertical / rig["body_len"]
        return {"kind": "dorsoventral", "vertical_per_body_length": relative,
                "lateral_per_body_length": lateral / rig["body_len"],
                "passed": .10 <= relative <= .36 and lateral < .08 * vertical}
    if mode == "fly":
        wings = [limb["bones"] for limb in rig["limbs"] if limb["role"] == "wing"]
        samples = []
        for seconds in (.29, .69):
            phase_frame(scene, action, seconds / duration)
            tips = [point(wing[-1]) for wing in wings]
            lengths = [(point(wing[0]) - point(wing[-1])).length for wing in wings]
            samples.append((max(tip.x for tip in tips) - min(tip.x for tip in tips), sum(lengths) / len(lengths)))
        spread = 1 - samples[1][0] / samples[0][0]
        reach = 1 - samples[1][1] / samples[0][1]
        return {"kind": "powered_membrane_wing", "projected_span_reduction": spread,
                "shoulder_to_tip_reduction": reach, "passed": spread >= .15 and reach >= .07}
    return None


def fixture(folder, source, mode, strategy, renders, reuse_exports):
    folder.mkdir(parents=True, exist_ok=True)
    clips = [clip for clip in (mode, "glide" if mode == "fly" else None) if clip]
    output = folder / "animated.glb"
    blend = folder / "animated.blend"
    report_path = output.with_suffix(".report.json")
    if reuse_exports:
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        rig = baker.rig_of(next(o for o in bpy.context.scene.objects if o.type == "ARMATURE"))
        report = json.loads(report_path.read_text())
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        result = builder.build({**source, "construction": strategy}, "final")
        rig, arm = result["rig"], result["armature"]
        baked_clips = list(clips)
        if strategy == "metaball":
            baked_clips += [clip for clip in available_clips(rig) if clip not in clips]
        travel, contacts = {}, []
        durations = baker.bake_all(arm, clips=baked_clips, contacts=contacts, travel=travel)
        export.export(result, str(output))
        export.export(result, str(blend))
        report = {**result["report"], "clips": durations, "root_travel": travel}
        if contacts:
            report["contact"] = {"frames": contacts, "legs": {
                rig["names"][limb["bones"][-1]]: limb["length"] for limb in rig["limbs"] if limb["role"] == "leg"}}
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    definitions = station_definitions(rig, mode)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(output))
    scene = bpy.context.scene
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    meshes = [o for o in scene.objects if o.type == "MESH"]
    skin = next(o for o in meshes if "_skin" in o.name)
    for track in arm.animation_data.nla_tracks:
        track.mute = True
    arm.animation_data.action = None
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    scene.frame_set(0)
    shell_union = strategy == "solid" and mode == "walk"
    section_meshes = meshes if shell_union else [skin]
    rest = measure(arm, section_meshes, definitions, shell_union=shell_union)
    if renders:
        camera = render.setup("workbench", 396)
        for tag, yaw in REST_VIEWS.items():
            render.clay_camera(camera, meshes, yaw, 12)
            render.render(str(folder / f"{tag}.png"))
    pose_sections, propulsion = {}, None
    for clip in clips:
        action = min((a for a in bpy.data.actions if a.name.casefold().split("_")[0] == clip), key=lambda a: len(a.name))
        arm.animation_data.action = action
        if getattr(action, "slots", None):
            arm.animation_data.action_slot = action.slots[0]
        if clip == mode:
            propulsion = propulsion_check(arm, rig, mode, action, durations[mode] if not reuse_exports else report["clips"][mode])
        if renders:
            frame_motion(camera, meshes, scene, action, mode)
        for i in range(16):
            phase = (i + .5) / 16
            phase_frame(scene, action, phase)
            pose_sections[f"{clip}_{i:02d}"] = measure(arm, section_meshes, definitions, shell_union=shell_union)
            if renders and i in (0, 4, 8, 12):
                render.render(str(folder / f"{clip}-{i:02d}.png"))
    contact = None
    if report.get("contact", {}).get("legs"):
        contact = runpy.run_path(str(Path(__file__).with_name("export_contact.py")))["measure"](output)
        contact["passed"] = (contact["stance_drift"] <= .02
                             and min(contact["swing_clearance"].values()) > .025)
    return {"report": report, "rest": rest, "poses": pose_sections, "stations": definitions,
            "propulsion": propulsion, "contact": contact}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("fixtures", nargs="+", choices=PILOTS)
    parser.add_argument("--renders", action="store_true")
    parser.add_argument("--reuse-exports", action="store_true", help="measure an existing paired .blend and GLB export")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    for key in args.fixtures:
        source, mode = PILOTS[key]
        original = recipe.load(ROOT / source)
        destination = args.out.resolve() / key
        baseline = fixture(destination / "incumbent", original, mode, "solid", args.renders, args.reuse_exports)
        candidate = fixture(destination / "metaball", original, mode, "metaball", args.renders, args.reuse_exports)
        defs = candidate["stations"]
        crease = [name for name, value in defs.items() if value[0] == "crease"]
        midspan = [name for name, value in defs.items() if value[0] == "midspan"]
        comparisons = {
            key: asset_validation.evaluate_section_gate(candidate["rest"], measured, crease, midspan,
                                                         incumbent=baseline["poses"][key])
            for key, measured in candidate["poses"].items()
        } if crease or midspan else {}
        (destination / "sections.json").write_text(json.dumps({
            "incumbent": baseline, "metaball": candidate, "comparisons": comparisons,
            "paired_contact_passed": candidate["contact"]["passed"] and (
                candidate["contact"]["stance_drift"] <= baseline["contact"]["stance_drift"]
            ) if candidate["contact"] and baseline["contact"] else None,
            "section_status": "pending" if not comparisons else (
                "passed" if all(report["status"] == "passed" for report in comparisons.values()) else "failed"),
        }, indent=2) + "\n")
        print(key, candidate["report"]["triangles"], candidate["report"].get("warnings"), flush=True)


if __name__ == "__main__":
    main()
