"""Image -> PolyForge creature.

    python3 ai/forge.py reference.png --out runs/myfox [--iterations 4] [--tolerance 0.8]
    python3 ai/forge.py reference.png --out runs/x --init examples/bull.json --no-llm   (numeric fit only)

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
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import optimize  # noqa: E402
import pf  # noqa: E402
import vision  # noqa: E402

ROOT = os.path.dirname(HERE)
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
        examples = [json.load(open(os.path.join(ROOT, "examples", e))) for e in ("bull.json", "bird.json", "minotaur.json")]
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
            sheet = os.path.join(ROOT, "library", "thumbs")
            ids = [p["id"] for p in catalog["parts"]]
            sheet_path = vision.contact_sheet([os.path.join(sheet, i + ".png") for i in ids], ids, os.path.join(self.work, "library_sheet.png"))
            self.log("drafting with %s ..." % claude.MODEL)
            res, usage = claude.draft(a.image, catalog, examples, sheet_path)
            self._usage(usage)
            analysis = {k: v for k, v in res.items() if k != "recipe_json"}
            recipe = json.loads(res["recipe_json"])
            self.log("subject: %s (%s), view yaw %.0f pitch %.0f" % (res["subject"], res["body_plan"], res["view_yaw"], res["view_pitch"]))
            for f in res["features"]:
                self.log("  feature [%d] %s -> %s" % (f["importance"], f["name"], f["part"]))
        if a.yaw is not None and a.init:
            analysis["view_yaw"], analysis["view_pitch"] = a.yaw, a.pitch
        cam = (analysis.get("view_yaw") or 38.0, analysis.get("view_pitch") if analysis.get("view_pitch") is not None else 16.0)
        recipe, warnings = pf.normalize(recipe)
        best = None
        gaps = set(f["name"] for f in analysis["features"] if f.get("part") == "none")
        stall = 0
        for it in range(a.iterations):
            self.log("--- iteration %d" % it)
            # 1. numeric proportion fit
            if not a.no_fit:
                part_uids = [p["uid"] for p in recipe.get("parts", [])][:4]
                fitter = optimize.Fitter(self.ref_mask, cam, os.path.join(self.work, "fit%d" % it))
                os.makedirs(fitter.work, exist_ok=True)
                knobs = optimize.default_knobs(recipe, part_uids, fit_camera=not a.fixed_camera)
                recipe, fs, f0, xs, cam = fitter.fit(recipe, knobs, rounds=a.fit_rounds, log=self.log)
                recipe, warnings = pf.normalize(recipe)
                self.log("  fitted %s (%d renders), camera %.0f,%.0f" % ({k: v for k, v in xs.items() if abs(v - (0 if k in ('neck_raise', 'cam_yaw') else 1)) > 1e-6}, fitter.evals, cam[0], cam[1]))
            # 2. render + score
            rnd = self.render(recipe, "it%d" % it, cam, ["threequarter", "side", "front"])
            scores = self.numeric_scores(rnd)
            critique = None
            if use_llm:
                critique, usage = claude.critique(a.image, [("reference view", rnd["color"])] + rnd["extra"], analysis, recipe, scores, warnings, catalog, examples)
                self._usage(usage)
                fc = critique["feature_checks"]
                imp = {f["name"]: f["importance"] for f in analysis["features"]}
                wsum = sum(imp.get(c["name"], 1) for c in fc) or 1
                scores["features"] = round(sum(imp.get(c["name"], 1) * max(0.0, min(1.0, c["score"])) for c in fc) / wsum, 4)
                gaps.update(critique["library_gaps"])
            else:
                scores["features"] = scores["silhouette"]  # no judge available
            scores["total"] = round(total(scores), 4)
            self.history.append({"iteration": it, "scores": scores, "camera": cam, "warnings": warnings})
            self.log("  scores %s" % scores)
            if best is None or scores["total"] > best["scores"]["total"] + 1e-4:
                best = {"recipe": recipe, "scores": scores, "render": rnd, "camera": cam}
                stall = 0
            else:
                stall += 1
            if scores["total"] >= a.tolerance:
                self.log("  reached style tolerance %.2f" % a.tolerance)
                break
            if stall >= 2:
                self.log("  no improvement for 2 iterations; stopping")
                break
            # 3. LLM edits
            if critique is not None:
                if critique["done"]:
                    self.log("  judge: no further edits would help")
                    break
                try:
                    ops = json.loads(critique["ops_json"] or "[]")
                except json.JSONDecodeError:
                    ops = []
                if ops:
                    new, errs, warns = pf.apply_ops(best["recipe"], ops)
                    for e in errs:
                        self.log("  op error: " + e)
                    self.log("  applied %d ops" % (len(ops) - len(errs)))
                    recipe, warnings = new, warns
            elif a.no_fit:
                break
        self.finish(best, analysis, sorted(gaps), time.time() - t0)

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
        if not self.args.no_export:
            pf.build(rp, self.out, name, "glb,fbx,usdz,blend")
            pf.video("turntable", rp, os.path.join(self.out, "turntable.mp4"), seconds=6, size=420)
            pf.video("animate", rp, os.path.join(self.out, "walk.mp4"), clip="walk", seconds=4, size=420)
        report = {
            "best_scores": best["scores"], "tolerance": self.args.tolerance, "camera": best["camera"],
            "analysis": analysis, "library_gaps": gaps, "history": self.history,
            "seconds": round(seconds, 1), "usage": self.usage, "weights": WEIGHTS,
        }
        json.dump(report, open(os.path.join(self.out, "report.json"), "w"), indent=2)
        open(os.path.join(self.out, "log.txt"), "w").write("\n".join(self.log_lines))
        self.log("best total %.3f -> %s" % (best["scores"]["total"], self.out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--out", required=True)
    ap.add_argument("--iterations", type=int, default=4)
    ap.add_argument("--tolerance", type=float, default=0.8, help="stop when the total score reaches this")
    ap.add_argument("--init", help="start from this recipe instead of an LLM draft")
    ap.add_argument("--no-llm", action="store_true", help="numeric fitting only (needs --init)")
    ap.add_argument("--no-fit", action="store_true", help="skip numeric proportion fitting")
    ap.add_argument("--fit-rounds", type=int, default=6)
    ap.add_argument("--fixed-camera", action="store_true")
    ap.add_argument("--yaw", type=float, default=None, help="camera yaw of the reference (with --init)")
    ap.add_argument("--pitch", type=float, default=16.0)
    ap.add_argument("--no-export", action="store_true")
    Run(ap.parse_args()).go()


if __name__ == "__main__":
    main()
