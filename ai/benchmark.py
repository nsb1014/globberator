"""Known-recipe benchmark for the fitter (no API key needed).

    python3 ai/benchmark.py [--examples bull,bird,...] [--out runs/bench]

Each example creature is rendered as a reference "photo" and segmented like a
real image. Its recipe is perturbed (wider body, shorter legs, shorter spine),
and the numeric fitter must recover the silhouette. Reports silhouette scores
before and after, and how close the recovered knobs are to the true inverse
of the perturbation. With --reference, the full forge loop drafts from a held-out image.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import optimize  # noqa: E402
import pf  # noqa: E402
import vision  # noqa: E402

ROOT = os.path.dirname(HERE)
PERTURB = {"body_w": 1.3, "body_len": 0.8, "leg_len": 0.78}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", default="bull,bird,beetle,dragon,minotaur")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "bench"))
    ap.add_argument("--view", default="38,16")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--reference", help="held-out reference image; run a fresh small-model draft with no seed recipe")
    args = ap.parse_args()
    if args.reference:
        subprocess.run([sys.executable, os.path.join(HERE, "forge.py"), args.reference,
                        "--out", args.out, "--no-export"], check=True)
        with open(os.path.join(args.out, "report.json")) as f:
            report = json.load(f)
        summary = {k: report[k] for k in ("first_pass_valid", "repair_turns", "renders", "usage", "seconds", "best_scores")}
        summary["visual_acceptance"] = "pending human review of best_view.png, best_side.png and best_front.png"
        print(json.dumps(summary, indent=2))
        return
    os.makedirs(args.out, exist_ok=True)
    yaw, pitch = (float(v) for v in args.view.split(","))
    rows = []
    for name in args.examples.split(","):
        truth, _ = pf.normalize(json.load(open(os.path.join(ROOT, "examples", name + ".json"))))
        work = os.path.join(args.out, name)
        os.makedirs(work, exist_ok=True)
        tpath = os.path.join(work, "truth.json")
        json.dump(truth, open(tpath, "w"))
        ref = pf.render_jobs([{"recipe": tpath, "out": work, "views": [args.view], "mask": False}], 384)[0]["images"][0]
        ref_mask, _ = vision.segment(ref)
        knobs = optimize.default_knobs(truth, fit_camera=False)
        x = [PERTURB.get(k.name, k.x0) for k in knobs]
        start = optimize.apply_knobs(truth, knobs, x)
        fitter = optimize.Fitter(ref_mask, (yaw, pitch), work)
        knobs = optimize.default_knobs(start, fit_camera=False)
        fitted, best, s0, xs, _ = fitter.fit(start, knobs, rounds=args.rounds, log=lambda m: print(name, m))
        err = {k: round(xs[k] * PERTURB[k] - 1.0, 3) for k in PERTURB if k in xs}
        rows.append({"example": name, "start": round(s0, 3), "fitted": round(best, 3), "renders": fitter.evals, "knob_error": err})
        json.dump(fitted, open(os.path.join(work, "fitted.json"), "w"), indent=1)
        print(json.dumps(rows[-1]))
    json.dump(rows, open(os.path.join(args.out, "results.json"), "w"), indent=2)
    print("\nexample    start  fitted  renders  residual (fitted x perturbation - 1)")
    for r in rows:
        print("%-10s %.3f  %.3f   %4d     %s" % (r["example"], r["start"], r["fitted"], r["renders"], r["knob_error"]))


if __name__ == "__main__":
    main()
