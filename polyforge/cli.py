"""Globberator command line (runs inside Blender or with the `bpy` Python module).

    python3 pf.py <command> [args]          # pip install bpy numpy scipy
    blender -b -P pf.py -- <command> [args]

Commands
  new --out file.json [--name name]             start a blank recipe
  search "plain language" [--limit 5]          find active part families and preview paths
  describe [--out f.json]                      part catalog, recipe limits and ops as JSON
  surface <recipe> X Y Z                       estimate spine coordinates for a body landmark
  character <brief.json> --out dir             compile an animated humanoid GLB
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


def cmd_new(a):
    recipe = R.default_recipe()
    recipe["name"] = a.name
    R.save(R.normalize(recipe)[0], a.out)


def cmd_search(a):
    if a.limit < 1:
        raise ValueError("--limit must be positive")
    results = []
    for part in catalog.search(a.query, a.limit):
        host = "limb" if part.attach == "tip" else part.host
        result = {"id": part.id, "description": part.desc, "category": part.category,
                  "attach": part.attach, "host": host,
                  "shape": catalog.search_shape(part, a.query)}
        for key, folder in (("thumbnail", "thumbs"), ("part_reference", "references")):
            path = os.path.join("library", folder, part.id + ".png")
            if os.path.isfile(os.path.join(ROOT, path)):
                result[key] = path
        results.append(result)
    print(json.dumps(results, indent=2))


def cmd_describe(a):
    if a.part:
        selected = catalog.get(a.part)
        if selected is None:
            raise ValueError("unknown part " + a.part)
        d = {"library_version": catalog.LIBRARY_VERSION, "parts": [catalog.describe_part(selected)]}
    else:
        d = catalog.describe() if a.full else {
            "library_version": catalog.LIBRARY_VERSION,
            "parts": [{"id": item.id, "category": item.category, "attach": item.attach} for item in catalog.PARTS],
        }
    if not a.part or a.full:
        d["placement"] = "u from first to last spine ring, including caps [0,1]; theta around the local spine frame"
        d["recipe_limits"] = R.LIMITS
        d["patterns"] = R.PATTERNS
        d["ops"] = ops.SPEC
    text = json.dumps(d, indent=2, sort_keys=True)
    if a.out:
        open(a.out, "w").write(text)
    else:
        print(text)


def cmd_surface(a):
    from .spine import Spine

    recipe, warnings = R.normalize(R.load(a.recipe))
    for warning in warnings:
        print("warning:", warning, file=sys.stderr)
    spine = Spine(recipe["spine"])
    point = Vector(a.point)
    if not all(math.isfinite(value) for value in point):
        raise ValueError("surface needs a finite X Y Z landmark")
    projected = spine.project(point)
    u, theta = projected["u"], projected["theta"]
    surface = spine.surface(u, theta)
    print(json.dumps({"u": round(u, 5), "theta": round(theta, 3),
                      "surface": [round(value, 5) for value in surface["p"]],
                      "normal": [round(value, 5) for value in surface["n"]],
                      "distance": round((point - surface["p"]).length, 5)}))


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
    views = (("front", "front"), ("side", "side"), ("threequarter", "threequarter"), ("head", "side"))
    if a.accept:
        previous = R.load(path)
        if previous["recipe_hash"] != review.signature(source):
            raise ValueError("Recipe changed; regenerate review images")
        images = [os.path.join(a.out, name + ".png") for name, _ in views]
        if not previous.get("renders_complete", True) or any(
            not os.path.isfile(image) or os.path.getsize(image) == 0 for image in images
        ):
            raise ValueError("Review images are missing or empty; regenerate them before accepting")
        R.save(review.record(source, True, a.accept), path)
        return
    pending = review.record(source, False, "")
    R.save({**pending, "renders_complete": False}, path)
    reset()
    res = build(source, "final")
    pose_at(res, None)
    cam = render.setup("workbench", 640)
    render.floor(True)
    for name, view in views:
        bounds = head_bounds(res) if name == "head" else render.bounds(objs(res))
        render.frame(cam, *bounds, *render.view_angles(view))
        render.render(os.path.join(a.out, name + ".png"))
    R.save(pending, path)


def require_review(a):
    from . import review
    path = a.review or os.path.join(os.path.dirname(a.recipe), "review.json")
    if not os.path.isfile(path):
        raise ValueError("Create and inspect the review views first with pf.py review")
    review.require(R.load(a.recipe), R.load(path))


def cmd_build(a):
    from . import baker
    baked = not (a.no_anim or a.runtime_motion)
    if baked:
        require_review(a)       # check the gate before the (slow) sculpted build
    reset()
    t = time.time()
    res = build(a.recipe, "preview" if a.preview else "final")
    report = dict(res["report"])
    if baked:
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
            report["files"].append(export.export(res, os.path.join(a.out, "%s.%s" % (name, fmt)), fmt, animated=baked))
    if a.runtime_motion:
        from . import runtime_motion

        motion_path = os.path.join(a.out, name + ".motion.json")
        runtime_motion.save(res["rig"], motion_path)
        report["files"].append(motion_path)
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
    from .parts.research import PREVIEW_ANGLES

    os.makedirs(a.out, exist_ok=True)
    reset()
    cam = render.setup("workbench", a.size)
    for p in library_selection(a.part):
        models = library_objects(p)
        render.clay_camera(cam, models, *PREVIEW_ANGLES.get(p.id, (38, 18)))
        render.render(os.path.join(a.out, p.id + ".png"))
        for model in models:
            finish.remove(model)
        finish.clear_cache()
    print(json.dumps({"thumbs": a.out}))


def library_selection(part_id):
    if not part_id:
        return catalog.PARTS
    part = catalog.get(part_id)
    if part is None:
        raise ValueError("unknown part " + part_id)
    return [part]


def library_objects(part):
    _, regions = finish.part_regions(part, part.defaults())
    clay = bpy.data.materials.get("Globberator Clay")
    if clay is None:
        clay = bpy.data.materials.new("Globberator Clay")
        clay.diffuse_color = (*builder.hex_rgb("#c4c5c6"), 1.0)
        clay.roughness = 0.85
    objects = []
    for piece, slots in regions.items():
        verts, faces = [], []
        for _, region_verts, region_faces in slots:
            offset = len(verts)
            verts.extend(region_verts)
            faces.extend(tuple(i + offset for i in face) for face in region_faces)
        if faces:
            name = part.id if piece == "self" else f"{part.id}__{piece}"
            ob = finish.new_object(name, verts, faces)
            ob.data.materials.append(clay)
            ob.data.shade_smooth()
            objects.append(ob)
    if not objects:
        raise ValueError("empty part mesh: " + part.id)
    return objects


def cmd_library(a):
    """Every part at default params as its own GLB (for engines that assemble parts themselves)."""
    os.makedirs(a.out, exist_ok=True)
    parts = library_selection(a.part)
    reset()
    for p in parts:
        objs_ = library_objects(p)
        bpy.context.view_layer.update()
        for ob in objs_:
            ob.select_set(True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(a.out, p.id + ".glb"), export_format="GLB", use_selection=True)
        with open(os.path.join(a.out, p.id + ".json"), "w") as file:
            json.dump(catalog.describe_part(p), file, indent=2)
        for ob in objs_:
            finish.remove(ob)
        finish.clear_cache()
    print(json.dumps({"library": a.out, "parts": len(parts)}))


def cmd_test(a):
    from . import tests
    return tests.run(fast=a.fast)


def cmd_character(a):
    from . import character

    reset()
    report = character.build(R.load(a.brief), a.out)
    with open(os.path.join(a.out, "report.json"), "w") as file:
        json.dump(report, file, indent=2)
    print(json.dumps(report))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pf", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new", help="start a blank recipe")
    s.add_argument("--out", required=True); s.add_argument("--name", default="Creature")
    s = sub.add_parser("search", help="find active part families using plain language")
    s.add_argument("query"); s.add_argument("--limit", type=int, default=5)
    s = sub.add_parser("part", help="preview a local shape or extract one instance")
    s.add_argument("input"); s.add_argument("--uid"); s.add_argument("--out", required=True)
    s.add_argument("--size", type=int, default=384); s.add_argument("--views", default="front,side,threequarter")
    s = sub.add_parser("attach", help="attach a local shape to a creature")
    s.add_argument("recipe"); s.add_argument("shape"); s.add_argument("--out", required=True)
    s.add_argument("--on", default="body"); s.add_argument("--u", required=True, type=float)
    s.add_argument("--theta", required=True, type=float); s.add_argument("--uid")
    s.add_argument("--scale", type=float, default=1.0); s.add_argument("--rot", type=float, nargs=3, default=[0, 0, 0])
    s = sub.add_parser("describe"); s.add_argument("--out"); s.add_argument("--part"); s.add_argument("--full", action="store_true")
    s = sub.add_parser("surface", help="estimate body attachment coordinates from a recipe-space landmark")
    s.add_argument("recipe"); s.add_argument("point", metavar="XYZ", type=float, nargs=3)
    s = sub.add_parser("character", help="compile a classified humanoid into a clay GLB with runtime motion bindings")
    s.add_argument("brief"); s.add_argument("--out", required=True)
    s = sub.add_parser("normalize"); s.add_argument("recipe"); s.add_argument("--out")
    s = sub.add_parser("apply"); s.add_argument("recipe"); s.add_argument("ops"); s.add_argument("--out", required=True)
    s = sub.add_parser("review"); s.add_argument("recipe"); s.add_argument("--out", required=True); s.add_argument("--accept", metavar="INSPECTION_NOTE")
    s = sub.add_parser("build"); s.add_argument("--review"); s.add_argument("recipe"); s.add_argument("--out", required=True)
    s.add_argument("--contacts", action="store_true", help="include walk stance samples in the build report")
    s.add_argument("--formats", default="glb,blend"); s.add_argument("--no-anim", action="store_true"); s.add_argument("--preview", action="store_true")
    s.add_argument("--runtime-motion", action="store_true", help="export rig and runtime IK bindings without baked clips")
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
    s = sub.add_parser("library"); s.add_argument("--out", required=True); s.add_argument("--part")
    s = sub.add_parser("test"); s.add_argument("--fast", action="store_true")
    a = ap.parse_args(argv)
    code = globals()["cmd_" + a.cmd](a)
    return code or 0
