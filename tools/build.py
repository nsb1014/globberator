"""Build a versioned creature recipe using its body family."""
import argparse
import json
import runpy
import sys
from pathlib import Path

tools = Path(__file__).resolve().parent
root = tools.parent
sys.path.insert(0, str(tools))
parser = argparse.ArgumentParser()
parser.add_argument("--recipe", type=Path, default=root/"models/minotaur.json")
parser.add_argument("--output", type=Path)
parser.add_argument("--review", type=Path)
args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
recipe = json.loads(args.recipe.read_text())
family = recipe["parts"]["body"]
if family == "segmented_arachnid":
    from arachnid import build
    build(recipe, args.output or root/"godot/arachnid.glb", args.review)
elif family in {"heavy_biped", "heavy_quadruped"}:
    runpy.run_path(str(tools/"bovine.py"), init_globals={
        "root": root, "recipe": recipe, "output": args.output, "review": args.review,
    })
else:
    parser.error(f"Unknown body family {family!r}")
