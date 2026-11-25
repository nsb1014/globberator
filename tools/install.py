"""Install PolyForge into a Blender installation (add-on + app template).

    blender -b -P tools/install.py
    blender --app-template PolyForge        # then launch the builder

Copies polyforge/ to the user add-ons folder, the app template to
startup/bl_app_templates_user/PolyForge, enables the add-on and saves prefs.
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
template = os.path.join(scripts, "startup", "bl_app_templates_user", "PolyForge")
for dst in (addons, template):
    if os.path.exists(dst):
        shutil.rmtree(dst)
shutil.copytree(os.path.join(ROOT, "polyforge"), addons, ignore=shutil.ignore_patterns("__pycache__"))
shutil.copytree(os.path.join(ROOT, "app_template"), template, ignore=shutil.ignore_patterns("__pycache__"))
# Examples and thumbnails travel with the add-on.
for sub in ("examples", os.path.join("library", "thumbs")):
    src = os.path.join(ROOT, sub)
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(addons, "_data", sub), dirs_exist_ok=True)
import addon_utils  # noqa: E402
addon_utils.enable("polyforge", default_set=True, persistent=True)
bpy.ops.wm.save_userpref()
print("PolyForge installed:\n  add-on   %s\n  template %s" % (addons, template))
try:
    import scipy  # noqa: F401
except ImportError:
    print("NOTE: scipy is missing from Blender's Python. Run:\n  %s -m pip install scipy" % sys.executable)
