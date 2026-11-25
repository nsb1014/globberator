"""PolyForge command line (runs inside Blender or with the `bpy` Python module).

    python3 pf.py <command> [args]          # pip install bpy numpy scipy
    blender -b -P pf.py -- <command> [args]

Commands
  describe [--out f.json]                      part catalog, recipe limits and ops as JSON
  normalize <recipe> [--out r.json]            clamp into the style ranges, print warnings
  apply <recipe> <ops.json> --out r.json       apply editor operations
  build <recipe> --out dir [--formats glb,fbx,usdz,obj,blend] [--no-anim] [--preview]
  render <recipe> --out dir [--views a;b] [--size 512] [--mask] [--engine workbench|cycles]
                                               [--pose clip@seconds] [--focus head]
  renderjobs <jobs.json> [--size 256]          batch renders for the AI fitter
  animate <recipe> --clip walk --out f.mp4 [--seconds 4] [--view threequarter] [--size 480]
  turntable <recipe> --out f.mp4 [--seconds 6]
  gallery <recipe...> --out sheet.png [--size 320] [--cols 3]
  thumbs [--out library/thumbs] [--size 200]
  library --out dir                            export every part (default params) as GLB
  test                                         run the test suite
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

import bpy
from mathutils import Matrix, Vector

from . import builder, catalog, export, finish, kit, ops, render
from . import recipe as R
from .animator import Animator, C4, C4i, write_pose

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def build(path_or_recipe, quality="final"):
    src = R.load(path_or_recipe) if isinstance(path_or_recipe, str) else path_or_recipe
    return builder.build(src, quality)


def objs(res):
    return [o for o in (res["skin"], res["parts"]) if o is not None]


def set_world(res, anim):
    w = anim.world
    m = w.b.to_4x4()
    m.translation = w.o
    res["armature"].matrix_world = C4 @ m @ C4i


def pose_at(res, spec):
    """'clip@seconds' or None -> neutral pose with feet planted."""
    an = Animator(res["rig"])
    if spec:
        clip, _, t = spec.partition("@")
        an.play(clip)
        an.advance_to(float(t or 0.5))
    else:
        an.play("idle")
        an.otime = 0.0
        an.pose()
    write_pose(res["armature"], an)
    bpy.context.view_layer.update()
    return an


def head_bounds(res):
    lo, hi = render.bounds(objs(res))
    rig = res["rig"]
    head = Vector(rig["rest"][rig["spine"][-1]])
    c = kit.to_blender(head)
    r = max(rig["body_w"], 0.25) * 1.6
    return c - Vector((r, r, r)), c + Vector((r, r, r))


def frames_to_video(frames_dir, out, fps=30):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", os.path.join(frames_dir, "f%04d.png"),
                    "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "20", out], check=True)


# ------------------------------------------------------------------ commands

def cmd_part(a):
    """Render a standalone draft, or extract one selected instance to local coordinates."""
    from . import shapes
    reset()
    shape = R.load(a.input)
    if a.uid:
        r, _ = R.normalize(shape)
        item = next((i for i in r["limbs"] + r["parts"] if i["uid"] == a.uid), None)
        if item is None:
            raise ValueError("unknown instance " + a.uid)
        shape = shapes.extract(item)
    shape, warnings = shapes.normalize_shape(shape)
    objects, build_warnings = shapes.isolated(shape)
    warnings.extend(build_warnings)
    os.makedirs(a.out, exist_ok=True)
    R.save(shapes.extract(shape), os.path.join(a.out, "shape.json"))
    cam = render.setup("workbench", a.size)
    lo, hi = render.bounds(objects)
    for view in a.views.split(","):
        render.frame(cam, lo, hi, *render.view_angles(view))
        render.render(os.path.join(a.out, view + ".png"), transparent=True)
    print(json.dumps({"warnings": warnings, "out": a.out}))


def cmd_attach(a):
    from .shapes import normalize_shape
    shape, warnings = normalize_shape(R.load(a.shape))
    op = {"op": "attach_shape", "shape": shape, "on": a.on, "u": a.u, "theta": a.theta,
          "scale": a.scale, "rot": a.rot}
    if a.uid:
        op["uid"] = a.uid
    r, errors = ops.apply_all(R.normalize(R.load(a.recipe))[0], [op])
    if errors:
        raise ValueError("; ".join(errors))
    r, changes = R.normalize(r)
    for warning in warnings + changes:
        print("warning:", warning, file=sys.stderr)
    R.save(r, a.out)


def cmd_describe(a):
    d = catalog.describe()
    if a.part:
        selected = catalog.get(a.part)
        if selected is None:
            raise ValueError("unknown part " + a.part)
        d["parts"] = [catalog.describe_part(selected)]
    elif not a.full:
        d["parts"] = [{"id": item.id, "category": item.category, "attach": item.attach} for item in catalog.PARTS]
    d["placement"] = "u rear-to-front [0,1], theta degrees around the surface; midline single, lateral paired"
    d["recipe_limits"] = R.LIMITS
    d["patterns"] = R.PATTERNS
    d["ops"] = ops.SPEC
    text = json.dumps(d, indent=2, sort_keys=True)
    if a.out:
        open(a.out, "w").write(text)
    else:
        print(text)


def cmd_normalize(a):
    r, w = R.normalize(R.load(a.recipe))
    for x in w:
        print("warning:", x, file=sys.stderr)
    if a.out:
        R.save(r, a.out)
    else:
        print(R.to_json(r))


def cmd_apply(a):
    r, errs = ops.apply_all(R.load(a.recipe), json.load(open(a.ops)))
    for e in errs:
        print("op error:", e, file=sys.stderr)
    r, w = R.normalize(r)
    for x in w:
        print("warning:", x, file=sys.stderr)
    R.save(r, a.out)
    return 3 if errs else 0


def cmd_review(a):
    from . import review
    source = R.load(a.recipe)
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "review.json")
    if a.accept:
        previous = R.load(path)
        if previous["recipe_hash"] != review.signature(source):
            raise ValueError("Recipe changed; regenerate review images")
        R.save(review.record(source, True, a.accept), path)
        return
    reset()
    res = build(source, "final")
    pose_at(res, None)
    cam = render.setup("workbench", 640)
    render.floor(True)
    for view, focus in (("front", False), ("side", False), ("threequarter", False), ("side", True)):
        bounds = head_bounds(res) if focus else render.bounds(objs(res))
        render.frame(cam, *bounds, *render.view_angles(view))
        render.render(os.path.join(a.out, ("head" if focus else view) + ".png"))
    R.save(review.record(source, False, ""), path)


def require_review(a):
    from . import review
    path = a.review or os.path.join(os.path.dirname(a.recipe), "review.json")
    if not os.path.isfile(path):
        raise ValueError("Create and inspect the review views first with pf.py review")
    review.require(R.load(a.recipe), R.load(path))


def cmd_build(a):
    from . import baker
    reset()
    t = time.time()
    res = build(a.recipe, "preview" if a.preview else "final")
    report = dict(res["report"])
    if not a.no_anim:
        require_review(a)
        contact_frames = [] if a.contacts else None
        report["clips"] = baker.bake_all(res["armature"], contacts=contact_frames)
        if a.contacts:
            rig = res["rig"]
            report["contact"] = {"frames": contact_frames, "legs": {
                rig["names"][l["bones"][-1]]: l["length"] for l in rig["limbs"] if l["role"] == "leg"}}
    os.makedirs(a.out, exist_ok=True)
    name = (res["recipe"]["name"] or "creature").lower().replace(" ", "_")
    report["files"] = []
    for fmt in a.formats.split(","):
        fmt = fmt.strip()
        if fmt:
            report["files"].append(export.export(res, os.path.join(a.out, "%s.%s" % (name, fmt)), fmt))
    R.save(res["recipe"], os.path.join(a.out, name + ".recipe.json"))
    report["seconds"] = round(time.time() - t, 1)
    json.dump(report, open(os.path.join(a.out, name + ".report.json"), "w"), indent=2)
    print(json.dumps({"files": report["files"], "warnings": report["warnings"], "clips": report.get("clips")}))


def cmd_render(a):
    reset()
    res = build(a.recipe, "preview" if a.preview else "final")
    pose_at(res, a.pose)
    views = a.views.split(";") if ";" in a.views else a.views.split(",") if all(v in render.VIEWS for v in a.views.split(",")) else [a.views]
    cam = render.setup(a.engine, a.size)
    lo, hi = head_bounds(res) if a.focus == "head" else render.bounds(objs(res))
    os.makedirs(a.out, exist_ok=True)
    out = []
    for v in views:
        yaw, pitch = render.view_angles(v)
        render.frame(cam, lo, hi, yaw, pitch)
        tag = v.replace(",", "_")
        render.floor(True)
        out.append(render.render(os.path.join(a.out, tag + ".png")))
        if a.mask:
            render.floor(False)
            out.append(render.render(os.path.join(a.out, tag + "_rgba.png"), transparent=True))
    print(json.dumps({"images": out, "warnings": res["report"]["warnings"]}))


def cmd_renderjobs(a):
    jobs = json.load(open(a.jobs))
    results = []
    for job in jobs:
        reset()
        res = build(job["recipe"], job.get("quality", "preview"))
        pose_at(res, None)
        cam = render.setup(job.get("engine", "workbench"), a.size)
        lo, hi = render.bounds(objs(res))
        os.makedirs(job["out"], exist_ok=True)
        imgs = []
        for v in job.get("views", ["threequarter"]):
            yaw, pitch = render.view_angles(v)
            render.frame(cam, lo, hi, yaw, pitch)
            tag = v.replace(",", "_")
            if job.get("color", True):
                render.floor(True)
                imgs.append(render.render(os.path.join(job["out"], tag + ".png")))
            if job.get("mask", False):
                render.floor(False)
                imgs.append(render.render(os.path.join(job["out"], tag + "_rgba.png"), transparent=True))
        results.append({"recipe": job["recipe"], "images": imgs, "report": res["report"]})
    print("RESULT " + json.dumps(results))


def _video(a, kind):
    require_review(a)
    reset()
    res = build(a.recipe, "preview" if a.preview else "final")
    an = Animator(res["rig"])
    clip = getattr(a, "clip", "idle") if kind == "animate" else "idle"
    an.play(clip)
    follow = kind == "animate" and clip in ("walk", "run") and not a.inplace
    cam = render.setup(a.engine, a.size)
    write_pose(res["armature"], an)
    bpy.context.view_layer.update()
    lo, hi = render.bounds(objs(res))
    yaw, pitch = render.view_angles(a.view)
    fps = 30
    frames = tempfile.mkdtemp(prefix="pf_frames_")
    n = int(a.seconds * fps)
    if follow:
        travel = kit.to_blender(Vector((0, 0, an.speed * a.seconds)))
        render.frame(cam, Vector(map(min, lo, lo + travel)), Vector(map(max, hi, hi + travel)), yaw, pitch)
    render.floor(True)
    for f in range(n):
        an.step(1.0 / fps)
        write_pose(res["armature"], an)
        if follow:
            set_world(res, an)
        bpy.context.view_layer.update()
        if kind == "turntable":
            render.frame(cam, lo, hi, 360.0 * f / n, 14.0)
        elif not follow:
            render.frame(cam, lo, hi, yaw, pitch)
        render.render(os.path.join(frames, "f%04d.png" % f))
    frames_to_video(frames, a.out, fps)
    shutil.rmtree(frames, ignore_errors=True)
    print(json.dumps({"video": a.out, "frames": n}))


def cmd_animate(a):
    _video(a, "animate")


def cmd_turntable(a):
    _video(a, "turntable")


def cmd_gallery(a):
    from PIL import Image
    tiles = []
    tmp = tempfile.mkdtemp(prefix="pf_gallery_")
    for i, path in enumerate(a.recipes):
        reset()
        res = build(path, "preview" if a.preview else "final")
        pose_at(res, a.pose)
        cam = render.setup(a.engine, a.size)
        lo, hi = render.bounds(objs(res))
        yaw, pitch = render.view_angles(a.view)
        render.frame(cam, lo, hi, yaw, pitch)
        render.floor(True)
        tiles.append(render.render(os.path.join(tmp, "%02d.png" % i)))
        for w in res["report"]["warnings"]:
            print(os.path.basename(path), ":", w, file=sys.stderr)
    cols = a.cols or min(len(tiles), 4)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * a.size, rows * a.size), (30, 34, 40))
    for i, t in enumerate(tiles):
        sheet.paste(Image.open(t).convert("RGB"), ((i % cols) * a.size, (i // cols) * a.size))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out)
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"sheet": a.out, "tiles": len(tiles)}))


def cmd_thumbs(a):
    os.makedirs(a.out, exist_ok=True)
    for p in catalog.PARTS:
        if a.part and p.id != a.part:
            continue
        reset()
        res = build(ops.showcase_recipe(p.id), "final")
        pose_at(res, None)
        cam = render.setup("workbench", a.size)
        rig = res["rig"]
        if p.attach == "tip":
            centre = Vector(rig["limbs"][0]["joints"][-1])
        else:
            centre = Vector(rig["rest"][next(pr["bone"] for pr in rig["parts"] if not pr["mirrored"])])
        lo_p, hi_p = render.bounds([res["parts"]]) if res["parts"] is not None else (None, None)
        c = kit.to_blender(centre)
        r = 0.22 if p.category not in ("wing", "detail", "tail") else 0.4
        lo, hi = c - Vector((r, r, r)), c + Vector((r, r, r))
        if lo_p is not None and (hi_p - lo_p).length > 0.05 and p.category not in ("foot", "hand"):
            lo, hi = Vector(map(min, lo, lo_p)), Vector(map(max, hi, hi_p))
        yaw = 35.0 if p.category in ("eye", "mouth", "nose") else (150.0 if p.category == "tail" else 60.0)
        render.frame(cam, lo, hi, yaw, 18.0, 1.0)
        render.floor(True)
        render.render(os.path.join(a.out, p.id + ".png"))
    print(json.dumps({"thumbs": a.out}))


def cmd_library(a):
    """Every part at default params as its own GLB (for engines that assemble parts themselves)."""
    os.makedirs(a.out, exist_ok=True)
    for p in catalog.PARTS:
        reset()
        ctx, regions = finish.part_regions(p, p.defaults())
        objs_ = []
        for pn, regs in regions.items():
            verts, faces = [], []
            for slot, rv, rf in regs:
                o = len(verts)
                verts += rv
                faces += [tuple(i + o for i in f) for f in rf]
            if verts:
                ob = finish.new_object(p.id if pn == "self" else "%s__%s" % (p.id, pn), verts, faces)
                ob.data.shade_smooth()
                objs_.append(ob)
        for o in bpy.context.view_layer.objects:
            o.select_set(o in objs_)
        bpy.ops.export_scene.gltf(filepath=os.path.join(a.out, p.id + ".glb"), export_format="GLB", use_selection=True)
        json.dump(catalog.describe_part(p), open(os.path.join(a.out, p.id + ".json"), "w"), indent=2)
    print(json.dumps({"library": a.out, "parts": len(catalog.PARTS)}))


def cmd_test(a):
    from . import tests
    return tests.run(fast=a.fast)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pf", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("part", help="preview a local shape or extract one instance")
    s.add_argument("input"); s.add_argument("--uid"); s.add_argument("--out", required=True)
    s.add_argument("--size", type=int, default=384); s.add_argument("--views", default="front,side,threequarter")
    s = sub.add_parser("attach", help="attach a local shape to a creature")
    s.add_argument("recipe"); s.add_argument("shape"); s.add_argument("--out", required=True)
    s.add_argument("--on", default="body"); s.add_argument("--u", required=True, type=float)
    s.add_argument("--theta", required=True, type=float); s.add_argument("--uid")
    s.add_argument("--scale", type=float, default=1.0); s.add_argument("--rot", type=float, nargs=3, default=[0, 0, 0])
    s = sub.add_parser("describe"); s.add_argument("--out"); s.add_argument("--part"); s.add_argument("--full", action="store_true")
    s = sub.add_parser("normalize"); s.add_argument("recipe"); s.add_argument("--out")
    s = sub.add_parser("apply"); s.add_argument("recipe"); s.add_argument("ops"); s.add_argument("--out", required=True)
    s = sub.add_parser("review"); s.add_argument("recipe"); s.add_argument("--out", required=True); s.add_argument("--accept", metavar="INSPECTION_NOTE")
    s = sub.add_parser("build"); s.add_argument("--review"); s.add_argument("recipe"); s.add_argument("--out", required=True)
    s.add_argument("--contacts", action="store_true", help="include walk stance samples in the build report")
    s.add_argument("--formats", default="glb,blend"); s.add_argument("--no-anim", action="store_true"); s.add_argument("--preview", action="store_true")
    for name in ("render", "animate", "turntable"):
        s = sub.add_parser(name)
        s.add_argument("recipe"); s.add_argument("--out", required=True)
        s.add_argument("--size", type=int, default=512 if name == "render" else 420)
        s.add_argument("--engine", default="workbench"); s.add_argument("--preview", action="store_true")
        if name == "render":
            s.add_argument("--views", default="front,side,threequarter"); s.add_argument("--mask", action="store_true")
            s.add_argument("--pose"); s.add_argument("--focus")
        else:
            s.add_argument("--review"); s.add_argument("--seconds", type=float, default=4.0 if name == "animate" else 6.0)
            s.add_argument("--view", default="threequarter"); s.add_argument("--inplace", action="store_true")
            if name == "animate":
                s.add_argument("--clip", default="walk")
    s = sub.add_parser("renderjobs"); s.add_argument("jobs"); s.add_argument("--size", type=int, default=256)
    s = sub.add_parser("gallery"); s.add_argument("recipes", nargs="+"); s.add_argument("--out", required=True)
    s.add_argument("--size", type=int, default=320); s.add_argument("--cols", type=int, default=0); s.add_argument("--view", default="threequarter")
    s.add_argument("--engine", default="workbench"); s.add_argument("--pose"); s.add_argument("--preview", action="store_true")
    s = sub.add_parser("thumbs"); s.add_argument("--out", default=os.path.join(ROOT, "library", "thumbs")); s.add_argument("--size", type=int, default=200); s.add_argument("--part")
    s = sub.add_parser("library"); s.add_argument("--out", required=True)
    s = sub.add_parser("test"); s.add_argument("--fast", action="store_true")
    a = ap.parse_args(argv)
    code = globals()["cmd_" + a.cmd](a)
    return code or 0
