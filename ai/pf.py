"""Thin wrapper around the Godot CLI (cli/main.gd)."""
import json
import os
import shutil
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GODOT = os.environ.get("GODOT", "godot")


def _cmd(args, display):
    base = [GODOT, "--path", ROOT, "-s", "res://cli/main.gd", "--"] + args
    if display:
        base = [GODOT, "--rendering-driver", "opengl3", "--audio-driver", "Dummy"] + base[1:]
        if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
            base = ["xvfb-run", "-a", "-s", "-screen 0 1280x1024x24"] + base
    else:
        base.insert(1, "--headless")
    return base


def run(args, display=False, timeout=600):
    p = subprocess.run(_cmd(args, display), capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    if p.returncode != 0:
        raise RuntimeError("godot %s failed (%d):\n%s" % (args[0], p.returncode, p.stderr[-3000:]))
    return p.stdout


def describe():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "catalog.json")
        run(["describe", "--out", out])
        return json.load(open(out))


def normalize(recipe):
    """Returns (normalized recipe, warnings)."""
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.json"), os.path.join(d, "out.json")
        json.dump(recipe, open(src, "w"))
        p = subprocess.run(_cmd(["normalize", src, "--out", dst], False), capture_output=True, text=True, cwd=ROOT)
        warns = [l.split("warning: ", 1)[1] for l in p.stderr.splitlines() if "warning: " in l]
        return json.load(open(dst)), warns


def apply_ops(recipe, ops):
    """Apply editor operations; returns (recipe, errors, warnings)."""
    with tempfile.TemporaryDirectory() as d:
        src, opf, dst = os.path.join(d, "in.json"), os.path.join(d, "ops.json"), os.path.join(d, "out.json")
        json.dump(recipe, open(src, "w"))
        json.dump(ops, open(opf, "w"))
        p = subprocess.run(_cmd(["apply", src, opf, "--out", dst], False), capture_output=True, text=True, cwd=ROOT)
        errs = [l.split("op error: ", 1)[1] for l in p.stderr.splitlines() if "op error: " in l]
        warns = [l.split("warning: ", 1)[1] for l in p.stderr.splitlines() if "warning: " in l]
        if not os.path.exists(dst):
            raise RuntimeError(p.stderr[-2000:])
        return json.load(open(dst)), errs, warns


def render_jobs(jobs, size=256):
    """jobs: [{"recipe": path, "out": dir, "views": [...], "mask": bool, "color": bool}]"""
    with tempfile.TemporaryDirectory() as d:
        jf = os.path.join(d, "jobs.json")
        json.dump(jobs, open(jf, "w"))
        out = run(["renderjobs", jf, "--size", str(size)], display=True)
    for line in out.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    raise RuntimeError("no render result:\n" + out[-2000:])


def build(recipe_path, out_dir, name="creature"):
    return run(["build", recipe_path, "--out", out_dir, "--name", name], display=False)


def video(kind, recipe_path, out_path, **kw):
    args = [kind, recipe_path, "--out", out_path]
    for k, v in kw.items():
        args += ["--" + k, str(v)]
    return run(args, display=True)
