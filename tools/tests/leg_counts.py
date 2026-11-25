"""Build and contact-test every leg count, then open and solve each export in Godot."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

tools = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(tools))
from arthropod_recipe import configure_legs

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out",type=Path,required=True)
parser.add_argument("--godot",default="godot")
args = parser.parse_args()
out = args.out.resolve()
out.mkdir(parents=True,exist_ok=True)
preset = (tools.parent/"models/arachnid.json").read_text()
models = []
for count in range(9):
    recipe = json.loads(preset)
    configure_legs(recipe,count)
    spec,model = out/f"{count}.json",out/f"{count}.glb"
    spec.write_text(json.dumps(recipe,indent=2)+"\n")
    for script,params in [("build.py",["--recipe",spec,"--output",model]),
                          ("tests/arthropod_export.py",[model,spec,"--legs",str(count)])]:
        subprocess.run(["blender","-b","-t","3","--python-exit-code","1","-P",tools/script,"--",*params],check=True)
    models.append(model)
project = [args.godot,"--headless","--path",tools.parent/"godot"]
subprocess.run([*project,"--editor","--import"],check=True)
subprocess.run([*project,"--script",tools/"tests/runtime_gait.gd","--",*models],check=True)
