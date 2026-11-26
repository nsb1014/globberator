"""Generate fresh rigged GLBs for the Godot runtime-motion integration test."""
import copy
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from polyforge import builder, character, export, recipe, runtime_motion


def main():
    out = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    examples = {name: recipe.load(ROOT / "examples" / (name + ".json"))
                for name in ("serpent", "hopper", "bull", "spider")}
    examples["chibi"] = character.compile_recipe(
        {"body_plan": "humanoid", "style": "chibi", "head_fraction": .57,
         "face": "round", "eyes": "angled", "hair": "spiky", "feet": "boots"}
    )
    uneven = copy.deepcopy(examples["bull"])
    front = next(limb for limb in uneven["limbs"] if limb["uid"] == "fore")
    front["segments"][0][0] += .55
    front["segments"][1][0] -= .55
    examples["uneven"] = uneven
    for variant, source in examples.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        result = builder.build(source, "preview")
        folder = out / variant
        folder.mkdir(parents=True, exist_ok=True)
        name = "character" if variant == "chibi" else variant
        export.export(result, str(folder / (name + ".glb")), "glb", animated=False)
        runtime_motion.save(result["rig"], folder / (name + ".motion.json"))


if __name__ == "__main__":
    main()
