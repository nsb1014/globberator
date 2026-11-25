"""Known-recipe benchmark for the fitter (no API key needed).

    python3 ai/benchmark.py [--examples bull,bird,...] [--out runs/bench]

Each example creature is rendered as a reference "photo" and segmented like a
real image. Its recipe is perturbed (wider body, shorter legs, shorter spine),
and the numeric fitter must recover the silhouette. Reports silhouette scores
before and after, and how close the recovered knobs are to the true inverse
of the perturbation. With --llm, the full forge loop (Claude draft and
critique) also runs on each reference.
"""
import argparse
import json
import os
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
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    yaw, pitch = (float(v) for v in args.view.split(","))
    rows = []
    for name in args.examples.split(","):
        truth = json.load(open(os.path.join(ROOT, "examples", name + ".json")))
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
