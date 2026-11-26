"""Compile a humanoid into a clay GLB and runtime role bindings."""
import json
import math
from pathlib import Path
import struct
import tempfile

from mathutils import Vector

from . import builder, export, recipe, render, runtime_motion
from .character_brief import validate
from .spine import Spine

CLAY = "#b8b8b8"


def compile_recipe(brief):
    brief = validate(brief)
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
              "limbs": [leg, arm], "parts": parts, "paint": {"base": CLAY, "accent": CLAY, "detail": CLAY,
              "pattern": "none", "belly": False}}
    normalized, warnings = recipe.normalize(source)
    if warnings:
        raise ValueError("compiled character failed normalization: " + "; ".join(warnings))
    return normalized


def _neutralize(objects):
    color = (*builder.hex_rgb(CLAY), 1.0)
    for obj in objects:
        obj.data.shade_smooth()
        for attr in obj.data.color_attributes:
            attr.data.foreach_set("color", color * len(attr.data))
        for mat in obj.data.materials:
            mat.diffuse_color = color
            mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = color


def _verify_glb(path, expected):
    with path.open("rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        size, kind = struct.unpack("<I4s", f.read(8))
        if (magic, version, length, kind) != (b"glTF", 2, path.stat().st_size, b"JSON"):
            raise ValueError("invalid character GLB header")
        manifest = json.loads(f.read(size))
    if not manifest.get("meshes") or not manifest.get("skins"):
        raise ValueError("character GLB is missing a mesh or skin")
    names = {node.get("name") for node in manifest.get("nodes", [])}
    joints = {joint for limb in expected["limbs"] for joint in limb["joints"]} | set(expected["spine"])
    if manifest.get("animations") or not joints <= names:
        raise ValueError("character GLB must contain the runtime joints and no baked clips")


def build(brief, out):
    source = compile_recipe(brief)
    result = builder.build(source, "final")
    report = result["report"]
    objects = [obj for obj in (result["skin"], result["parts"]) if obj is not None]
    if (report["warnings"] or (report["legs"], report["arms"]) != (2, 2) or not report["triangles"]
            or any(not all(math.isfinite(v) for v in vertex.co) for obj in objects for vertex in obj.data.vertices)):
        raise ValueError(f"character geometry or rig validation failed: {report}")
    _neutralize(objects)
    bindings = runtime_motion.manifest(result["rig"])
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out) as temp:
        stage = Path(temp)
        glb = stage / "character.glb"
        export.export(result, str(glb), "glb", animated=False)
        _verify_glb(glb, bindings)
        recipe.save(source, stage / "recipe.json")
        recipe.save(bindings, stage / "character.motion.json")
        camera = render.setup("workbench", 512)
        render.clay_camera(camera, objects, 30, 11)
        render.render(str(stage / "preview.png"))
        files = ["character.glb", "recipe.json", "preview.png", "character.motion.json"]
        for name in files:
            (stage / name).replace(out / name)
    return {"files": files, "validation": report, "runtime_motion": "character.motion.json",
            "visual_review": "not_performed"}
