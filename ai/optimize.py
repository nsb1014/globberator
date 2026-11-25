"""Numeric refinement: coordinate search over continuous recipe knobs against
the reference silhouette. Discrete choices (which parts) are the LLM's job;
proportions are cheaper to fit numerically."""
import copy
import json
import math
import os
import tempfile

import numpy as np

import pf
import vision


def _scale_body(r, w=1.0, h=1.0, length=1.0):
    zs = [v["z"] for v in r["spine"]]
    zc = (min(zs) + max(zs)) * 0.5
    for v in r["spine"]:
        v["w"] *= w
        v["h"] *= h
        v["z"] = zc + (v["z"] - zc) * length


def _legs(r, f):
    for l in r.get("limbs", []):
        l["segments"] = [[s[0] * f, s[1] * f, s[2] * f] for s in l["segments"]]


def _thick(r, f):
    for l in r.get("limbs", []):
        l["radii"] = [x * f for x in l["radii"]]


def _neck(r, d):
    n = len(r["spine"])
    for i in range(max(1, n - 2), n):
        r["spine"][i]["y"] += d * (1.0 if i == n - 1 else 0.6)


def _tail(r, f):
    sp = r["spine"]
    if len(sp) < 3:
        return
    z1 = sp[1]["z"]
    sp[0]["z"] = z1 + (sp[0]["z"] - z1) * f


def _part_scale(uid):
    def fn(r, f):
        for p in r.get("parts", []):
            if p["uid"] == uid:
                p["scale"] = p.get("scale", 1.0) * f
    return fn


class Knob:
    def __init__(self, name, apply, x0, step, lo, hi, multiplicative=True):
        self.name, self.apply, self.x0, self.step, self.lo, self.hi = name, apply, x0, step, lo, hi
        self.mult = multiplicative


def default_knobs(recipe, part_uids=None, fit_camera=True):
    ks = [
        Knob("body_w", lambda r, x: _scale_body(r, w=x), 1.0, 0.15, 0.5, 2.0),
        Knob("body_h", lambda r, x: _scale_body(r, h=x), 1.0, 0.15, 0.5, 2.0),
        Knob("body_len", lambda r, x: _scale_body(r, length=x), 1.0, 0.15, 0.5, 2.0),
        Knob("neck_raise", _neck, 0.0, 0.15, -0.8, 0.8, False),
        Knob("tail_len", _tail, 1.0, 0.25, 0.3, 3.0),
    ]
    if recipe.get("limbs"):
        ks += [Knob("leg_len", _legs, 1.0, 0.15, 0.4, 2.2), Knob("limb_thick", _thick, 1.0, 0.2, 0.4, 2.5)]
    for uid in (part_uids or []):
        ks.append(Knob("scale:" + uid, _part_scale(uid), 1.0, 0.25, 0.3, 3.0))
    if fit_camera:
        ks.append(Knob("cam_yaw", None, 0.0, 20.0, -90.0, 90.0, False))
    return ks


def apply_knobs(recipe, knobs, x):
    r = copy.deepcopy(recipe)
    for k, v in zip(knobs, x):
        if k.apply is not None and abs(v - k.x0) > 1e-9:
            k.apply(r, v)
    return r


class Fitter:
    def __init__(self, ref_mask, view, workdir, size=192):
        self.ref = ref_mask
        self.view = view            # (yaw, pitch)
        self.work = workdir
        self.size = size
        self.evals = 0

    def score_many(self, recipes, cams):
        jobs = []
        for i, (r, cam) in enumerate(zip(recipes, cams)):
            path = os.path.join(self.work, "cand_%d.json" % i)
            json.dump(r, open(path, "w"))
            jobs.append({"recipe": path, "out": os.path.join(self.work, "cand_%d" % i), "views": ["%g,%g" % cam], "mask": True, "color": False})
        res = pf.render_jobs(jobs, self.size)
        self.evals += len(jobs)
        scores = []
        for r in res:
            m = vision.load_mask(r["images"][-1])
            i, prop = vision.silhouette_score(self.ref, m)
            scores.append(i + 0.3 * prop)
        return scores

    def fit(self, recipe, knobs, rounds=6, log=print):
        x = [k.x0 for k in knobs]
        steps = [k.step for k in knobs]

        def cam_of(xv):
            yaw = self.view[0]
            for k, v in zip(knobs, xv):
                if k.name == "cam_yaw":
                    yaw += v
            return (yaw, self.view[1])

        best = self.score_many([apply_knobs(recipe, knobs, x)], [cam_of(x)])[0]
        start = best
        log("  fit start score %.3f" % best)
        for rnd in range(rounds):
            cands, moves = [], []
            for i, k in enumerate(knobs):
                for sgn in (1, -1):
                    xv = list(x)
                    if k.mult:
                        xv[i] = x[i] * (1 + steps[i]) ** sgn
                    else:
                        xv[i] = x[i] + sgn * steps[i]
                    xv[i] = min(max(xv[i], k.lo), k.hi)
                    if abs(xv[i] - x[i]) < 1e-9:
                        continue
                    cands.append(xv)
                    moves.append((i, sgn))
            if not cands:
                break
            scores = self.score_many([apply_knobs(recipe, knobs, c) for c in cands], [cam_of(c) for c in cands])
            j = int(np.argmax(scores))
            if scores[j] > best + 1e-4:
                # Take the best move, plus any other improving moves on different knobs (one combined check next round).
                best = scores[j]
                x = cands[j]
                log("  round %d: %s %s -> %.3f" % (rnd, knobs[moves[j][0]].name, "+" if moves[j][1] > 0 else "-", best))
            else:
                steps = [s * 0.5 for s in steps]
                log("  round %d: no gain, halving steps" % rnd)
        fitted = apply_knobs(recipe, knobs, x)
        return fitted, best, start, dict((k.name, round(v, 4)) for k, v in zip(knobs, x)), cam_of(x)
