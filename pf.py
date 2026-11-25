"""PolyForge command line entry point.

    python3 pf.py <command> ...            (pip install bpy numpy scipy pillow)
    blender -b -P pf.py -- <command> ...   (a regular Blender install)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]

from polyforge import cli  # noqa: E402

code = cli.main(args)
if code:
    sys.exit(code)
