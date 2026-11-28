"""Known-recipe benchmark for the fitter (no API key needed).

    python3 ai/benchmark.py [--examples bull,bird,...] [--out runs/bench]

Each example creature is rendered as a reference "photo" and segmented like a
real image. Its recipe is perturbed (wider body, shorter legs, shorter spine),
and the numeric fitter must recover the silhouette. Reports silhouette scores
before and after, and how close the recovered knobs are to the true inverse
of the perturbation. With --reference, the full forge loop drafts from a held-out image.
Use --held-out with independently registered reference, candidate and incumbent
views to measure likeness without running the drafting model.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(1, ROOT)

import optimize  # noqa: E402
import pf  # noqa: E402
import vision  # noqa: E402

PERTURB = {"body_w": 1.3, "body_len": 0.8, "leg_len": 0.78}


def _load_json(path):
    with open(path, encoding="utf-8") as source:
        return json.load(source)


def _registered_views(views, root):
    out = {}
    for name, data in (views or {}).items():
        view = dict(data)
        if isinstance(view.get("mask"), str):
            path = root / view["mask"]
            if path.is_file():
                view["mask"] = path
            else:
                view.pop("mask")
                view["missing_mask"] = True
        out[name] = view
    return out


def _validity(case, root):
    path = case.get("validation_report")
    if not path or not (root / path).is_file():
        return {"status": "pending", "reason": "Candidate structural report is missing"}
    report = _load_json(root / path)
    validation = report.get("validation", report)
    topology = validation.get("skin_topology")
    statistics = {key: validation[key] for key in ("triangles", "bones", "skin_topology", "warnings")
                  if key in validation}
    failures = list(validation.get("warnings", []))
    if "triangles" in validation and validation["triangles"] <= 0:
        failures.append("Candidate mesh has no triangles")
    if topology and topology.get("nonmanifold_edges"):
        failures.append("Candidate skin has nonmanifold edges")
    if failures:
        return {"status": "failed", "findings": failures, **statistics}
    if "triangles" not in validation or "warnings" not in validation:
        return {"status": "pending", "reason": "Candidate structural measurements are incomplete", **statistics}
    return {"status": "passed", **statistics}


def _likeness(case, root):
    from polyforge.asset_validation import compare_held_out

    reference = _registered_views(case.get("reference"), root)
    candidate = _registered_views(case.get("candidate"), root)
    incumbent = _registered_views(case.get("incumbent"), root)
    views = set(reference) | set(case.get("required_views", ()))
    pending = []
    ready = {}
    for name in sorted(views):
        target = reference.get(name, {})
        proposed = candidate.get(name, {})
        if target.get("missing_mask") or not (target.get("landmarks") or target.get("mask") is not None):
            pending.append(f"{name}: independently annotated reference view is missing")
            continue
        if target.get("mask") is None and not target.get("landmark_scale"):
            pending.append(f"{name}: landmark-only reference view lacks its reference dimension")
            continue
        if ((target.get("mask") is not None and proposed.get("mask") is None)
                or not target.get("landmarks", {}).keys() <= proposed.get("landmarks", {}).keys()):
            pending.append(f"{name}: candidate view lacks paired masks or landmark annotations")
            continue
        ready[name] = target
    if not ready:
        return {"status": "pending", "views": {}, "failures": [],
                "pending": pending or ["Independently annotated held-out views are missing"]}
    result = compare_held_out(ready, candidate, incumbent, case.get("review"))
    result["pending"].extend(pending)
    if pending and result["status"] == "passed":
        result["status"] = "pending"
    return result


def _retrieval(case, root):
    expected = case.get("accepted_families", {})
    path = case.get("validation_report")
    if not expected or not path or not (root / path).is_file():
        return {"checked": 0, "hits": 0, "misses": [], "pending": sorted(expected)}
    report = _load_json(root / path)
    if "features" not in report:
        return {"checked": 0, "hits": 0, "misses": [], "pending": sorted(expected)}
    features = {feature["id"]: feature["candidates"] for feature in report["features"]}
    matches, misses = 0, []
    for feature, families in sorted(expected.items()):
        ranking = features.get(feature, [])[:5]
        if set(families).intersection(ranking):
            matches += 1
        else:
            misses.append({"feature": feature, "ranked": ranking, "accepted": families})
    return {"checked": matches + len(misses), "hits": matches, "misses": misses, "pending": []}


def score_held_out(path):
    """Report structural validity and reference likeness for each indexed case."""
    path = Path(path)
    spec = _load_json(path)
    cases = spec.get("cases", {path.stem: spec})
    if not isinstance(cases, dict) or not cases:
        raise ValueError("held-out index must name at least one case")
    results = {name: {"validity": _validity(case, path.parent), "likeness": _likeness(case, path.parent),
                      "retrieval": _retrieval(case, path.parent)}
               for name, case in cases.items()}
    aggregate = {gate: {status: sum(case[gate]["status"] == status for case in results.values())
                        for status in ("passed", "failed", "pending")}
                 for gate in ("validity", "likeness")}
    checked = sum(case["retrieval"]["checked"] for case in results.values())
    hits = sum(case["retrieval"]["hits"] for case in results.values())
    pending = sum(len(case["retrieval"]["pending"]) for case in results.values())
    aggregate["retrieval"] = {"checked": checked, "hits": hits, "pending": pending,
                             "top_five_rate": hits / checked if checked else None}
    statuses = [(case["validity"]["status"], case["likeness"]["status"]) for case in results.values()]
    first_pass = {"passed": statuses.count(("passed", "passed")),
                  "failed": sum("failed" in case for case in statuses)}
    first_pass["pending"] = len(results) - first_pass["passed"] - first_pass["failed"]
    aggregate["first_pass"] = first_pass
    return {"cases": results, "aggregate": aggregate}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--examples", default="bull,bird,beetle,dragon,minotaur")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "bench"))
    ap.add_argument("--view", default="38,16")
    ap.add_argument("--rounds", type=int, default=8)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--reference", help="held-out reference image; run a fresh small-model draft with no seed recipe")
    mode.add_argument("--held-out", type=Path, help="score indexed, independently registered held-out views")
    args = ap.parse_args()
    if args.held_out:
        scores = score_held_out(args.held_out)
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        summary = json.dumps(scores, indent=2, allow_nan=False) + "\n"
        (out / "results.json").write_text(summary, encoding="utf-8")
        print(summary, end="")
        return
    if args.reference:
        subprocess.run([sys.executable, os.path.join(HERE, "forge.py"), args.reference,
                        "--out", args.out, "--no-export"], check=True)
        with open(os.path.join(args.out, "report.json")) as f:
            report = json.load(f)
        summary = {k: report[k] for k in ("first_pass_valid", "repair_turns", "renders", "usage", "seconds", "best_scores")}
        summary["visual_acceptance"] = "pending human review of best_view.png, best_side.png and best_front.png"
        summary["validity"] = {"first_pass_valid": report["first_pass_valid"]}
        summary["likeness"] = {"status": "pending", "reason": "Independently annotated held-out views are missing"}
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
        ref_mask = vision.segment(ref)
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
