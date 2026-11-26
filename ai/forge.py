"""Image -> Globberator creature.

    python3 ai/forge.py reference.png --out runs/myfox [--iterations 4] [--tolerance 0.8]
    python3 ai/forge.py reference.png --one-shot --out runs/character
    python3 ai/forge.py reference.png --out runs/x --init examples/bull.json --no-llm   (numeric fit only)
    python3 ai/forge.py reference.png --out runs/x --init examples/bull.json --no-llm --accept "checked by hand"

Exports (GLB/FBX/USDZ, videos) only happen once the assembled creature passes
visual review: Claude's anatomy check, or with --no-llm an explicit --accept
note after you have looked at the review views. Without it, a --no-llm run
writes recipe.json, the review views and report.json, and says export was skipped.

Loop: segment the reference -> Claude drafts a recipe from the part library ->
render -> score (silhouette, proportions, palette, Claude feature checklist) ->
Claude proposes edit ops -> numeric proportion fit -> repeat until the score
reaches the style tolerance or stops improving. Writes the best recipe, a
rigged GLB with baked clips, preview images/videos, and report.json (scores,
history and library gaps).

Score = 0.4 features + 0.3 silhouette IoU + 0.2 proportions + 0.1 palette.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
sys.path.insert(1, ROOT)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import optimize  # noqa: E402
import pf  # noqa: E402
import vision  # noqa: E402

WEIGHTS = {"features": 0.4, "silhouette": 0.3, "proportion": 0.2, "palette": 0.1}


def total(s):
    return sum(WEIGHTS[k] * s.get(k, 0.0) for k in WEIGHTS)


class Run:
    def __init__(self, args):
        self.args = args
        self.out = os.path.abspath(args.out)
        os.makedirs(self.out, exist_ok=True)
        self.work = os.path.join(self.out, "work")
        os.makedirs(self.work, exist_ok=True)
        self.log_lines = []
        self.history = []
        self.renders = 0
        self.repairs = 0
        self.usage = {"input_tokens": 0, "output_tokens": 0}

    def log(self, msg):
        print(msg, flush=True)
        self.log_lines.append(msg)

    # ---- scoring -----------------------------------------------------
    def render(self, recipe, tag, cam, extra_views=()):
        path = os.path.join(self.work, tag + ".json")
        json.dump(recipe, open(path, "w"), indent=1)
        views = ["%g,%g" % cam] + list(extra_views)
        res = pf.render_jobs([{"recipe": path, "out": os.path.join(self.work, tag), "views": views, "mask": True, "quality": "final"}], 384)[0]
        self.renders += 2 * len(views)
        imgs = res["images"]
        return {"color": imgs[0], "mask": imgs[1], "extra": [(v, imgs[2 + 2 * i]) for i, v in enumerate(extra_views)], "report": res["report"]}

    def numeric_scores(self, rnd):
        m = vision.load_mask(rnd["mask"])
        iou, prop = vision.silhouette_score(self.ref_mask, m)
        rgb = np.asarray(Image.open(rnd["color"]).convert("RGB"), np.float32) / 255.0
        pal = vision.palette_score(self.ref_rgb, self.ref_mask, rgb, m)
        return {"silhouette": round(iou, 4), "proportion": round(prop, 4), "palette": round(pal, 4)}

    # ---- main --------------------------------------------------------
    def go(self):
        a = self.args
        t0 = time.time()
        shutil.copy(a.image, os.path.join(self.out, "reference" + os.path.splitext(a.image)[1]))
        self.ref_mask, self.ref_rgb = vision.segment(a.image)
        Image.fromarray((self.ref_mask * 255).astype(np.uint8)).save(os.path.join(self.out, "reference_mask.png"))
        self.log("reference segmented: %d%% foreground" % int(self.ref_mask.mean() * 100))
        catalog = pf.describe()
        use_llm = not a.no_llm
        if use_llm:
            import claude
        analysis = {"features": [], "view_yaw": a.yaw, "view_pitch": a.pitch, "subject": "unknown", "body_plan": "other"}
        warnings = []
        if a.init:
            recipe = json.load(open(a.init))
            self.log("starting from " + a.init)
        else:
            if not use_llm:
                sys.exit("--no-llm needs --init recipe.json")
            self.log("drafting with %s ..." % claude.MODEL)
            recipe = None
            for attempt in range(2):     # one retry if the reply's recipe is not valid JSON
                res, usage = claude.draft(a.image, catalog)
                self._usage(usage)
                try:
                    recipe = json.loads(res["recipe_json"])
                    if not isinstance(recipe, dict):
                        raise TypeError("recipe_json is not an object")
                    break
                except (json.JSONDecodeError, TypeError) as exc:
                    self.repairs += 1
                    self.log("draft reply had no valid recipe (%s)%s" % (exc, "; retrying" if attempt == 0 else ""))
                    recipe = None
            if recipe is None:
                sys.exit("the draft replies did not contain a valid recipe; rerun or pass --init")
            analysis = {k: v for k, v in res.items() if k != "recipe_json"}
            self.log("subject: %s (%s), view yaw %.0f pitch %.0f" % (res["subject"], res["body_plan"], res["view_yaw"], res["view_pitch"]))
            for f in res["features"]:
                self.log("  feature [%d] %s -> %s" % (f["importance"], f["name"], f["part"]))
        if a.yaw is not None and a.init:
            analysis["view_yaw"], analysis["view_pitch"] = a.yaw, a.pitch
        cam = (analysis["view_yaw"] if analysis.get("view_yaw") is not None else 38.0, analysis.get("view_pitch") if analysis.get("view_pitch") is not None else 16.0)
        recipe, warnings = pf.normalize(recipe)
        self.first_pass_valid = not warnings
        if use_llm and a.part_rounds:
            ranked = sorted(analysis["features"], key=lambda f: -f["importance"])
            items = recipe["parts"] + recipe["limbs"]
            reviewed = set()
            for feature in ranked:
                for index, item in enumerate(items):
                    if index in reviewed or feature["part"] != item.get("part", item.get("tip")):
                        continue
                    self.refine_part(item, a.part_rounds, index)
                    reviewed.add(index)
            recipe, warnings = pf.normalize(recipe)
        best = None
        gaps = set(f["name"] for f in analysis["features"] if f.get("part") == "none")
        stall = 0
        for it in range(a.iterations):
            self.log("--- iteration %d" % it)
            # 1. numeric proportion fit
            if not a.no_fit:
                feature_rank = {f["part"]: f["importance"] for f in analysis["features"]}
                ranked = sorted(recipe["parts"], key=lambda p: -feature_rank.get(p["part"], 0))
                part_uids = [p["uid"] for p in ranked[:2]]
                fitter = optimize.Fitter(self.ref_mask, cam, os.path.join(self.work, "fit%d" % it))
                os.makedirs(fitter.work, exist_ok=True)
                knobs = optimize.default_knobs(recipe, part_uids, fit_camera=not a.fixed_camera)
                recipe, fs, f0, xs, cam = fitter.fit(recipe, knobs, rounds=a.fit_rounds, log=self.log)
                self.renders += fitter.evals
                recipe, warnings = pf.normalize(recipe)
                self.log("  fitted %s (%d renders), camera %.0f,%.0f" % ({k: v for k, v in xs.items() if abs(v - (0 if k in ('neck_raise', 'cam_yaw') else 1)) > 1e-6}, fitter.evals, cam[0], cam[1]))
            # 2. render + score
            rnd = self.render(recipe, "it%d" % it, cam, ["threequarter", "side", "front"])
            warnings = list(dict.fromkeys(warnings + rnd["report"]["warnings"]))
            if use_llm:
                closeup = os.path.join(self.work, "head%d" % it)
                pf.run(["render", os.path.join(self.work, "it%d.json" % it), "--focus", "head", "--views", "side", "--out", closeup])
                rnd["extra"].append(("head_side", os.path.join(closeup, "side.png")))
                self.renders += 1
            scores = self.numeric_scores(rnd)
            critique = None
            if use_llm:
                critique, usage = claude.critique(a.image, [("reference view", rnd["color"])] + rnd["extra"], analysis, recipe, scores, warnings, catalog)
                self._usage(usage)
                fc = critique["feature_checks"]
                imp = {f["name"]: f["importance"] for f in analysis["features"]}
                wsum = sum(imp.get(c["name"], 1) for c in fc) or 1
                scores["features"] = round(sum(imp.get(c["name"], 1) * max(0.0, min(1.0, c["score"])) for c in fc) / wsum, 4)
                gaps.update(critique["library_gaps"])
            active_weight = sum(WEIGHTS[k] for k in scores)
            scores["total"] = round(total(scores) / active_weight, 4)
            self.history.append({"iteration": it, "scores": scores, "camera": cam, "warnings": warnings})
            self.log("  scores %s" % scores)
            accepted = bool(critique and critique["anatomy_pass"]) or (not use_llm and bool(a.accept))
            note = critique["anatomy_note"] if critique else (a.accept or "")
            if best is None or (accepted, scores["total"]) > (best["accepted"], best["scores"]["total"] + 1e-4):
                best = {"accepted": accepted, "review_note": note, "recipe": recipe, "scores": scores, "render": rnd, "camera": cam}
                stall = 0
            else:
                stall += 1
            if scores["total"] >= a.tolerance and (accepted or not use_llm):
                self.log("  reached style tolerance %.2f" % a.tolerance)
                break
            if stall >= 2:
                self.log("  no improvement for 2 iterations; stopping")
                break
            # 3. LLM edits
            if critique is not None:
                if critique["done"] and accepted:
                    self.log("  judge: no further edits would help")
                    break
                try:
                    ops = json.loads(critique["ops_json"] or "[]")
                except json.JSONDecodeError:
                    ops = []
                if ops:
                    new, errs, warns = pf.apply_ops(recipe, ops)
                    for e in errs:
                        self.log("  op error: " + e)
                    self.log("  applied %d ops" % (len(ops) - len(errs)))
                    self.repairs += 1
                    recipe, warnings = new, warns
            elif a.no_fit:
                break
        self.finish(best, analysis, sorted(gaps), time.time() - t0)

    def refine_part(self, item, rounds, index):
        import claude
        pid = item.get("part", item.get("tip"))
        controls = pf.describe(pid)["parts"][0]["params"]
        allowed = ("segments", "radii", "tip_params") if "segments" in item else ("params",)
        draft = {k: item[k] for k in (*allowed, "part", "tip", "motion") if k in item}
        for i in range(rounds + 1):
            work = os.path.join(self.work, "part%d" % index, "shape%d" % i)
            os.makedirs(work, exist_ok=True)
            path = os.path.join(work, "input.json")
            with open(path, "w") as out:
                json.dump(draft, out)
            pf.run(["part", path, "--out", work, "--views", "front,side"])
            self.renders += 2
            with open(os.path.join(work, "shape.json")) as out:
                draft = json.load(out)
            review, usage = claude.refine_shape(self.args.image, [os.path.join(work, v + ".png") for v in ("front", "side")], draft, controls)
            self._usage(usage)
            if review["accept"]:
                item.update({k: draft[k] for k in allowed if k in draft})
                return
            if i < rounds:
                self.repairs += 1
                try:
                    edits = json.loads(review["shape_json"])
                    if not isinstance(edits, dict):
                        raise TypeError("shape_json is not an object")
                except (json.JSONDecodeError, TypeError) as exc:
                    self.log("  ignored a malformed shape edit for %s (%s)" % (item["uid"], exc))
                    continue
                draft.update({k: edits[k] for k in allowed if k in edits})
        self.log("isolated draft unaccepted; kept original " + item["uid"])

    def _usage(self, u):
        self.usage["input_tokens"] += (u.input_tokens or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
        self.usage["output_tokens"] += u.output_tokens or 0

    def finish(self, best, analysis, gaps, seconds):
        rp = os.path.join(self.out, "recipe.json")
        json.dump(best["recipe"], open(rp, "w"), indent=2, sort_keys=True)
        shutil.copy(best["render"]["color"], os.path.join(self.out, "best_view.png"))
        for v, p in best["render"]["extra"]:
            shutil.copy(p, os.path.join(self.out, "best_%s.png" % v))
        name = (best["recipe"].get("name") or "creature").lower().replace(" ", "_")
        pf.run(["review", rp, "--out", self.out])
        self.renders += 4
        if best["accepted"]:
            pf.run(["review", rp, "--out", self.out, "--accept", best["review_note"] or "Reviewed against reference"])
        if not self.args.no_export and not best["accepted"]:
            self.log("export skipped: the creature has not passed visual review. Inspect the review views in %s, then "
                     "rerun with --accept \"note\" (or run pf.py review %s --out %s --accept \"note\" and pf.py build)." % (self.out, rp, self.out))
        if not self.args.no_export and best["accepted"]:
            pf.build(rp, self.out, name, "glb,fbx,usdz,blend")
            pf.video("turntable", rp, os.path.join(self.out, "turntable.mp4"), seconds=6, size=420)
            pf.video("animate", rp, os.path.join(self.out, "walk.mp4"), clip="walk", seconds=4, size=420)
        report = {
            "visual_review": {"accepted": best["accepted"], "note": best["review_note"]},
            "best_scores": best["scores"], "tolerance": self.args.tolerance, "camera": best["camera"],
            "analysis": analysis, "library_gaps": gaps, "history": self.history,
            "first_pass_valid": self.first_pass_valid, "renders": self.renders, "repair_turns": self.repairs,
            "seconds": round(seconds, 1), "usage": self.usage, "weights": WEIGHTS,
        }
        json.dump(report, open(os.path.join(self.out, "report.json"), "w"), indent=2)
        open(os.path.join(self.out, "log.txt"), "w").write("\n".join(self.log_lines))
        self.log("best total %.3f -> %s" % (best["scores"]["total"], self.out))


def one_shot(args):
    from polyforge.character_brief import validate

    image = Path(args.image).resolve()
    with Image.open(image) as source:
        source.verify()
    usage = None
    model = None
    if args.brief:
        brief = json.loads(Path(args.brief).read_text())
    else:
        import claude

        brief, usage = claude.character_brief(image)
        model = claude.MODEL
    validate(brief)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out) as temp:
        stage = Path(temp)
        brief_path = stage / "character-brief.json"
        brief_path.write_text(json.dumps(brief, indent=2) + "\n")
        pf.run(["character", str(brief_path), "--out", str(stage)])
        report_path = stage / "report.json"
        report = json.loads(report_path.read_text())
        report["classification"] = {"model": model, "requests": int(model is not None),
                                    "input_tokens": usage.input_tokens if usage else 0,
                                    "output_tokens": usage.output_tokens if usage else 0}
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        for name in [*report["files"], "character-brief.json", "report.json"]:
            (stage / name).replace(out / name)
    print(out / "character.glb")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--out", required=True)
    ap.add_argument("--one-shot", action="store_true", help="one image classification followed by a deterministic humanoid rig with runtime motion")
    ap.add_argument("--brief", help="use a previously classified image brief with --one-shot")
    ap.add_argument("--part-rounds", type=int, default=1, help="maximum isolated shape revisions; 0 disables")
    ap.add_argument("--iterations", type=int, default=4)
    ap.add_argument("--tolerance", type=float, default=0.8, help="stop when the total score reaches this")
    ap.add_argument("--init", help="start from this recipe instead of an LLM draft")
    ap.add_argument("--no-llm", action="store_true", help="numeric fitting only (needs --init)")
    ap.add_argument("--accept", metavar="NOTE", help="with --no-llm: accept the visual review with this note so exports run")
    ap.add_argument("--no-fit", action="store_true", help="skip numeric proportion fitting")
    ap.add_argument("--fit-rounds", type=int, default=2)
    ap.add_argument("--fixed-camera", action="store_true")
    ap.add_argument("--yaw", type=float, default=None, help="camera yaw of the reference (with --init)")
    ap.add_argument("--pitch", type=float, default=16.0)
    ap.add_argument("--no-export", action="store_true")
    args = ap.parse_args()
    if args.one_shot:
        if args.init or args.no_llm or args.accept or args.no_export:
            ap.error("--one-shot exports automatically and accepts --brief to run without an API call")
        try:
            one_shot(args)
        except (OSError, RuntimeError, ValueError) as exc:
            ap.exit(1, f"{ap.prog}: {exc}\n")
    elif args.brief:
        ap.error("--brief requires --one-shot")
    else:
        Run(args).go()


if __name__ == "__main__":
    main()
