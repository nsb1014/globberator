"""Thin wrapper around the PolyForge Blender CLI (pf.py).

Uses `python3 pf.py` (Blender as the bpy module) by default. Set PF_BLENDER to a
Blender executable to run through a regular Blender install instead.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = os.environ.get("PF_BLENDER")


def _cmd(args):
    if BLENDER:
        return [BLENDER, "-b", "--factory-startup", "--python-exit-code", "2", "-P", os.path.join(ROOT, "pf.py"), "--"] + args
    return [sys.executable, os.path.join(ROOT, "pf.py")] + args


def run(args, timeout=3600):
    p = subprocess.run(_cmd(args), capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    if p.returncode != 0:
        raise RuntimeError("pf %s failed (%d):\n%s" % (args[0], p.returncode, (p.stderr or p.stdout)[-3000:]))
    return p


def describe(part=None):
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "catalog.json")
        run(["describe", "--out", out] + (["--part", part] if part else []))
        return json.load(open(out))


def normalize(recipe):
    """Returns (normalized recipe, warnings)."""
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.json"), os.path.join(d, "out.json")
        json.dump(recipe, open(src, "w"))
        p = run(["normalize", src, "--out", dst])
        return json.load(open(dst)), [l.split("warning: ", 1)[1] for l in p.stderr.splitlines() if "warning: " in l]


def apply_ops(recipe, ops):
    """Apply editor operations; returns (recipe, errors, warnings)."""
    with tempfile.TemporaryDirectory() as d:
        src, opf, dst = (os.path.join(d, n) for n in ("in.json", "ops.json", "out.json"))
        json.dump(recipe, open(src, "w"))
        json.dump(ops, open(opf, "w"))
        p = subprocess.run(_cmd(["apply", src, opf, "--out", dst]), capture_output=True, text=True, cwd=ROOT)
        if not os.path.exists(dst):
            raise RuntimeError(p.stderr[-2000:])
        errs = [l.split("op error: ", 1)[1] for l in p.stderr.splitlines() if "op error: " in l]
        warns = [l.split("warning: ", 1)[1] for l in p.stderr.splitlines() if "warning: " in l]
        return json.load(open(dst)), errs, warns


def render_jobs(jobs, size=256):
    """jobs: [{"recipe": path, "out": dir, "views": [...], "mask": bool, "color": bool, "quality": "preview"|"final"}]
    Images per view: colour .png (if color) then transparent _rgba.png (if mask)."""
    with tempfile.TemporaryDirectory() as d:
        jf = os.path.join(d, "jobs.json")
        json.dump(jobs, open(jf, "w"))
        p = run(["renderjobs", jf, "--size", str(size)])
    for line in p.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    raise RuntimeError("no render result:\n" + p.stdout[-2000:])


def build(recipe_path, out_dir, name="creature", formats="glb,fbx,blend"):
    return run(["build", recipe_path, "--out", out_dir, "--formats", formats]).stdout


def video(kind, recipe_path, out_path, **kw):
    args = [kind, recipe_path, "--out", out_path]
    for k, v in kw.items():
        args += ["--" + k, str(v)]
    return run(args).stdout
