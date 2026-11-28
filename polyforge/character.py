"""Compile classified figures into neutral-clay, rigged Blender assets."""
import json
import math
from pathlib import Path
import struct
import tempfile

from mathutils import Vector

from . import animator, baker, builder, catalog, export, recipe, render, runtime_motion
from .character_brief import validate
from .spine import Spine

def compile_recipe(brief):
    brief = validate(brief)
    if brief.get("version") == 2:
        return _compile_creature(brief)[0]
    return _compile_humanoid(brief)


def _compile_humanoid(brief):
    style_bounds = {"chibi": (.43, .65), "cartoon": (.23, .48), "standard": (.12, .28)}
    low, high = style_bounds[brief["style"]]
    ratio = min(high, max(low, brief["head_fraction"]))
    head = 1.60 * ratio
    neck = 1.60 - head
    pelvis = .52 * neck
    hips = max(.105, min(.20, .22 * neck))
    shoulders = hips * 1.20
    width = head * {"oval": .38, "round": .46, "square": .48}[brief["face"]]
    depth = .37 * head
    jaw = .77 if brief["face"] == "square" else .57
    rings = [
        (.94 * pelvis, hips * .89, hips * .71), (1.04 * pelvis, hips, hips * .75),
        (.70 * neck, .90 * hips, .71 * hips), (.85 * neck, shoulders, .78 * hips),
        (.92 * neck, shoulders * .90, hips * .71),
        (neck, min(hips * .78, width * .58), min(hips * .76, depth * .66)),
        (neck + head * .065, width * jaw, depth * .72),
        (neck + head * .28, width * .92, depth * .94),
        (neck + head * .53, width, depth), (neck + head * .76, width * .94, depth * .95),
        (neck + head * .91, width * .50, depth * .52),
    ]
    minimum = recipe.LIMITS["radius"][0]
    spine = [{"y": y, "z": 0.0, "w": max(minimum, w), "h": max(minimum, d)} for y, w, d in rings]
    surface = Spine(spine)

    def seat(x, y, z):
        match = surface.project(Vector((x, y, z)))
        return {"u": match["u"], "theta": match["theta"]}

    # The same knee, calf and ankle fit both the barefoot sculpt and footwear.
    # Instance scale transforms the complete limb and its mounted tip together.
    barefoot = brief["feet"] == "bare"
    leg = {"uid": "leg", **seat(hips * .88, pelvis, hips * .30),
           "family": "leg_plantigrade", "params": {"incline_deg": 3, "ankle_outset": .08, "bare_foot": int(barefoot)},
           "scale": pelvis / .78}
    if not barefoot:
        leg.update(tip="foot_hoof", tip_params={"size": 1.46 if brief["feet"] == "boots" else 1.17, "split": 0})

    # Author the upper arm, forearm and hand once in the same local scale.
    arm = {"uid": "arm", **seat(shoulders, .85 * neck, 0),
           "segments": [[.19, -.33, -.04], [.07, -.32, .07]],
           "radii": [.136, .105, .077], "tip": "hand_basic",
           "tip_params": {"size": 1.30, "curl": .42}, "scale": .62 * neck}

    eye_size = max(.4, width * (2.6 if brief["eyes"] == "small" else 3.2))
    parts = [
        {"uid": "eyes", "part": "eye_camera", **seat(.46 * width, neck + .47 * head, .89 * depth),
         "rot": [0, 0, 12 if brief["eyes"] == "angled" else 0], "offset": max(-.034, -.07 * head),
         "params": {"size": eye_size, "bulge": .08, "sclerotic_ring": 0, "facing_deg": 0}},
        {"uid": "nose", "part": "nose_button", **seat(0, neck + .33 * head, depth),
         "offset": -.014, "params": {"size": max(.4, 2.15 * width)}},
        {"uid": "mouth", "part": "mouth_smile", **seat(0, neck + .22 * head, .86 * depth),
         "offset": -.010, "params": {"width": max(.4, 2.75 * width), "lips": .5, "curve": .35}},
        {"uid": "ears", "part": "ear_pinna", **seat(.96 * width, neck + .43 * head, -.025),
         "offset": -.022, "params": {"size": max(.4, 2.2 * width)}},
    ]
    if brief["hair"] != "bald":
        locks, sweep = {"short": (0, 0), "swept": (5, .36), "spiky": (3, 0)}[brief["hair"]]
        parts.append({"uid": "hair", "part": "hair_crown", "u": 1, "theta": -90, "offset": -.12 * head,
                      "params": {"width": width * .96, "depth": depth * .96,
                      "height": max(.04, head * (.24 if locks else .20)), "locks": locks, "sweep": sweep}})
    source = {"format": recipe.FORMAT, "version": recipe.VERSION, "name": "Character", "spine": spine, "gait": "humanoid",
              "construction": "solid", "limbs": [leg, arm], "parts": parts}
    return _normalize(source)


def _normalize(source):
    normalized, warnings = recipe.normalize(source)
    if warnings:
        raise ValueError("compiled character failed normalization: " + "; ".join(warnings))
    return normalized


def _creature_spine(brief):
    plan, dimensions = brief["body_plan"], brief["proportions"]
    width, depth, head, taper = (dimensions[k] for k in ("width", "depth", "head", "taper"))
    axis_length = 1.6 if plan in ("humanoid", "biped") else 2.0
    half_width, half_depth = width * axis_length * .5, depth * axis_length * .5
    if plan in ("humanoid", "biped"):
        neck = 1 - head
        hips = .6 + .4 * taper
        profile = [
            (neck * .14, hips * .84, hips * .79), (neck * .29, hips, hips * .91),
            (neck * .59, .77, .78), (neck * .79, 1, .86), (neck, .52, .58),
            (neck + head * .22, .78, .84), (neck + head * .48, 1, 1),
            (neck + head * .72, .86, .94), (neck + head * .90, .54, .62),
        ]
        origin = .47 if plan == "humanoid" else .7
        return [_ring(origin + axis_length * t, 0, half_width * w, half_depth * d)
                for t, w, d in sorted(profile)]
    shoulder = 1 - head
    profile = [
        (.025, taper * .53, taper * .61, -.19),
        (.12, taper, taper * .90, -.10),
        (.25, max(.20, taper * .93), max(.24, taper * .89), -.03),
        (shoulder * .50, .94, .95, .0),
        (shoulder * .73, 1, 1, .03),
        (shoulder * .92, .77, .86, .07),
        (shoulder + head * .21, .61, .68, .12),
        (shoulder + head * .52, .56, .60, .11),
        (shoulder + head * .86, .32, .32, .07),
    ]
    if plan in ("hexapod", "octopod", "blob", "radial"):
        rear = .52 + .48 * taper
        profile = [
            (.09, rear * .71, rear * .69, 0), (.22, rear, rear * .93, .03),
            (.42, 1, 1, .03), (max(.50, shoulder - .12), .90, .93, 0),
            (max(.64, shoulder + head * .13), .74, .74, 0), (.95, .48, .56, -.05),
        ]
    if plan in ("swimmer", "serpent") or brief["locomotion"].startswith("axial"):
        profile = [
            (.015, taper * .54, taper * .56, -.08), (.09, taper, taper * .90, -.08),
            (.19, .22 + .48 * taper, .26 + .48 * taper, -.07),
            (.32, .66, .71, -.05), (max(.46, shoulder * .70), .94, 1, .0),
            (max(.54, shoulder * .87), 1, .95, .06),
            (max(.66, shoulder + head * .05), .91, .85, .05),
            (max(.80, shoulder + head * .52), .62, .53, .0), (.97, .31, .28, -.03),
        ]
    origin = .72 if plan in ("quadruped", "bird", "winged", "swimmer") else .52
    return [_ring(origin + h * half_depth, axis_length * (t - .5), half_width * w, half_depth * d)
            for t, w, d, h in sorted(profile)]


def _ring(y, z, width, depth):
    minimum = recipe.LIMITS["radius"][0]
    return {"y": y, "z": z, "w": max(minimum, width), "h": max(minimum, depth)}


def _feature_choice(feature):
    query = feature.get("query", "")
    shape = feature["shape"]
    filters = {"host": feature["host"], "function": feature["function"]}
    found = catalog.search(query, shape=shape, **filters)
    if not found:
        found = catalog.search(shape, **filters)
    if not found and query:
        found = catalog.search(query, **filters)
    if not found:
        return None, {}, []
    selected = found[0]
    return selected, catalog.search_shape(selected, f"{shape} {query}"), [part.id for part in found]


def _compile_creature(brief):
    source = {"format": recipe.FORMAT, "version": recipe.VERSION, "name": brief["subject"],
              "construction": "metaball", "spine": _creature_spine(brief), "limbs": [], "parts": []}
    if brief["body_plan"] == "humanoid":
        source["gait"] = "humanoid"
    if brief["locomotion"] != "ground":
        source["locomotion"] = brief["locomotion"]
    choices = []
    for feature in brief["features"]:
        part, shape, candidates = _feature_choice(feature)
        match = {"id": feature["id"], "feature": feature["shape"], "candidates": candidates}
        choices.append((feature, part, shape, match))
        if not part:
            match["unresolved"] = "no family matches the specified host, function and shape"

    limbs = {}
    placed = []
    for feature, part, shape, match in choices:
        if not part or not part.preset:
            continue
        if len(limbs) >= recipe.LIMITS["limbs"]:
            match["unresolved"] = "limb limit reached"
            continue
        item = _placement(feature, part, shape)
        if feature["function"] == "swim" and part.cap != "foot":
            item["motion"] = "fin"
        limbs[item["uid"]] = item
        match["selected"] = part.id

    core = False
    for feature, part, shape, match in choices:
        if not part or part.preset:
            continue
        host = feature.get("host_feature")
        if host and host not in limbs:
            match["unresolved"] = "host feature did not resolve to a limb"
            continue
        if part.attach == "tip":
            limb = limbs[host]
            if "tip" in limb:
                match["unresolved"] = "limb already has an explicit tip"
                continue
            params = dict(shape.get("params", {}))
            if "scale" in feature and "size" in part.params:
                lo, hi, default = part.params["size"]
                params["size"] = min(hi, max(lo, default * feature["scale"]))
            limb.update(tip=part.id, tip_params=params)
        else:
            if part.attach == "core" and core:
                match["unresolved"] = "body already has a core family"
                continue
            core |= part.attach == "core"
            item = _placement(feature, part, shape)
            if host:
                item["on"] = host
            placed.append(item)
        match["selected"] = part.id
    source["limbs"] = list(limbs.values())
    source["parts"] = placed
    return _normalize(source), [match for _, _, _, match in choices]


def _placement(feature, part, shape):
    item = {"uid": feature["id"], **part.hint, **shape}
    item.update({key: feature[key] for key in ("u", "theta", "scale", "rot", "offset") if key in feature})
    return item


def _verify_glb(path, expected=None, clips=()):
    with path.open("rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        size, kind = struct.unpack("<I4s", f.read(8))
        if (magic, version, length, kind) != (b"glTF", 2, path.stat().st_size, b"JSON"):
            raise ValueError("invalid character GLB header")
        manifest = json.loads(f.read(size))
    if not manifest.get("meshes") or not manifest.get("skins"):
        raise ValueError("character GLB is missing a mesh or skin")
    if expected is not None:
        names = {node.get("name") for node in manifest.get("nodes", [])}
        joints = {joint for limb in expected["limbs"] for joint in limb["joints"]} | set(expected["spine"])
        if not joints <= names:
            raise ValueError("character GLB is missing runtime joints")
    animations = {clip.get("name") for clip in manifest.get("animations", [])}
    if animations != set(clips):
        raise ValueError(f"character GLB has clips {sorted(animations)}, expected {sorted(clips)}")


def _creature_clips(rig, profile):
    available = animator.available_clips(rig)
    if profile == "flight":
        expected = (*animator.AIR_MOTION, *animator.AIR_TRANSITIONS)
    elif profile in ("axial_vertical", "axial_lateral", "paddling"):
        expected = animator.SWIM_CLIPS
    elif profile == "crawl":
        expected = ("crawl",)
    else:
        expected = ()
    if expected:
        available = tuple(clip for clip in available if clip not in ("walk", "run", "hop"))
    return available, sorted(set(expected) - set(available))


def build(brief, out):
    brief = validate(brief)
    legacy = brief.get("version") != 2
    source, choices = (_compile_humanoid(brief), []) if legacy else _compile_creature(brief)
    result = builder.build(source, "final")
    report = result["report"]
    objects = [obj for obj in (result["skin"], result["parts"]) if obj is not None]
    if (report["warnings"] or (legacy and (report["legs"], report["arms"]) != (2, 2))
            or not report["triangles"]
            or any(not all(math.isfinite(v) for v in vertex.co) for obj in objects for vertex in obj.data.vertices)):
        raise ValueError(f"character geometry or rig validation failed: {report}")
    bindings = runtime_motion.manifest(result["rig"]) if legacy else None
    if legacy:
        clips = {}
    else:
        names, missing = _creature_clips(result["rig"], brief["locomotion"])
        travel = {}
        clips = baker.bake_all(result["armature"], clips=names, travel=travel)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out) as temp:
        stage = Path(temp)
        glb = stage / "character.glb"
        export.export(result, str(glb), "glb", animated=not legacy)
        _verify_glb(glb, bindings, clips)
        recipe.save(source, stage / "recipe.json")
        camera = render.setup("workbench", 512)
        render.clay_camera(camera, objects, 30, 11)
        render.render(str(stage / "preview.png"))
        files = ["character.glb", "recipe.json", "preview.png"]
        if legacy:
            recipe.save(bindings, stage / "character.motion.json")
            files.append("character.motion.json")
        else:
            export.export(result, str(stage / "character.blend"), "blend")
            files.append("character.blend")
        for name in files:
            (stage / name).replace(out / name)
    result = {"files": files, "validation": report, "visual_review": "not_performed"}
    if legacy:
        result["runtime_motion"] = "character.motion.json"
    else:
        result.update(clips=clips, root_travel=travel, features=choices, uncertainties=brief["uncertainties"],
                      unresolved_clips=missing)
    return result
