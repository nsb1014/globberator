"""Install Globberator into a Blender installation (add-on + app template).

    blender -b -P tools/install.py
    blender --app-template Globberator        # then launch the builder

Copies polyforge/ to the user add-ons folder, the app template to
startup/bl_app_templates_user/Globberator, enables the add-on and saves prefs.
Python dependencies (numpy, scipy) must be importable by Blender's Python:
    <blender python> -m pip install scipy
"""
import os
import shutil
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scripts = bpy.utils.user_resource("SCRIPTS")
addons = os.path.join(scripts, "addons", "polyforge")
template = os.path.join(scripts, "startup", "bl_app_templates_user", "Globberator")
for dst in (addons, template):
    if os.path.exists(dst):
        shutil.rmtree(dst)
shutil.copytree(os.path.join(ROOT, "polyforge"), addons, ignore=shutil.ignore_patterns("__pycache__"))
shutil.copytree(os.path.join(ROOT, "app_template"), template, ignore=shutil.ignore_patterns("__pycache__"))
# The active research spec travels with the add-on alongside examples and thumbnails.
for sub in ("examples", os.path.join("library", "thumbs")):
    src = os.path.join(ROOT, sub)
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(addons, "_data", sub), dirs_exist_ok=True)
research = os.path.join(addons, "_data", "research")
os.makedirs(research, exist_ok=True)
shutil.copy2(os.path.join(ROOT, "research", "part_library.json"), research)
import addon_utils  # noqa: E402
bpy.utils.refresh_script_paths()
if os.path.dirname(addons) not in sys.path:
    sys.path.insert(0, os.path.dirname(addons))
addon_utils.enable("polyforge", default_set=True, persistent=True)
bpy.ops.wm.save_userpref()
print("Globberator installed:\n  add-on   %s\n  template %s" % (addons, template))
try:
    import scipy  # noqa: F401
except ImportError:
    print("NOTE: scipy is missing from Blender's Python. Run:\n  %s -m pip install scipy" % sys.executable)
