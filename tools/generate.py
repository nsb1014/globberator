"""Build, round-trip check and preview an articulated creature in one command."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from arthropod_recipe import describe, validate

tools = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
source = parser.add_mutually_exclusive_group()
source.add_argument("--preset", choices=["solifuge"])
source.add_argument("--recipe", type=Path, help="A segmented_arachnid JSON recipe")
parser.add_argument("--shape", metavar="CONTROL=NUMBER", action="append", default=[])
parser.add_argument("--describe", action="store_true", help="Print the preset and accepted controls as JSON")
parser.add_argument("--out", type=Path)
parser.add_argument("--oidn", type=Path, help="Optional oidnDenoise executable")
args = parser.parse_args()
preset = json.loads((tools.parent/"models/arachnid.json").read_text())
if args.describe:
    print(json.dumps(describe(preset),indent=2))
    raise SystemExit(0)
if not args.out:
    parser.error("Supply --out for a build")
recipe = json.loads(args.recipe.read_text()) if args.recipe else preset
if recipe["parts"]["body"] != "segmented_arachnid":
    parser.error("The automated contact review supports segmented_arachnid recipes")
for setting in args.shape:
    key, sep, value = setting.partition("=")
    if not sep or key not in recipe["shape"]:
        parser.error(f"Unknown shape setting {setting!r}")
    try:
        recipe["shape"][key] = float(value)
    except ValueError:
        parser.error(f"Expected a number in {setting!r}")

try:
    validate(recipe)
except (KeyError, TypeError, ValueError) as error:
    parser.error(str(error))


def blender(script,*arguments):
    subprocess.run(["blender","-b","-t","4","--python-exit-code","1","-P",str(tools/script),
                    "--",*map(str,arguments)],check=True)

args.out.mkdir(exist_ok=True,parents=True)
with tempfile.TemporaryDirectory(dir=args.out) as tmp:
    stage = Path(tmp)
    model = stage/"arachnid.glb"
    spec = stage/"recipe.json"
    spec.write_text(json.dumps(recipe,indent=2)+"\n")
    blender("build.py","--recipe",spec,"--output",model)
    blender("tests/arthropod_export.py",model,spec)
    denoise = ["--oidn",args.oidn.resolve()] if args.oidn else []
    for clip,rate in [("still",0),("turn",9),("idle",12),("walk",12)]:
        blender("render.py",model,stage,"--clip",clip,"--frame-step",2,
                "--samples",64 if clip=="still" else 12,*denoise)
        if rate:
            subprocess.run(["ffmpeg","-nostdin","-loglevel","error","-framerate",str(rate),
                            "-i",str(stage/(clip+"-%03d.png")),"-c:v","libx264","-crf","19",
                            "-pix_fmt","yuv420p","-movflags","+faststart",str(stage/(clip+".mp4"))],check=True)
    for file in ("recipe.json","arachnid.glb","still-000.png","turn.mp4","idle.mp4","walk.mp4"):
        os.replace(stage/file,args.out/file)
print("Creature package:",args.out.resolve())
