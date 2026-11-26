"""Globberator test suite:  python3 pf.py test [--fast]"""
import hashlib
import json
import math
import os
import tempfile
import time

import bpy
import bmesh
from mathutils import Vector

from . import builder, catalog, export, finish, ops, placement
from . import recipe as R
from .animator import Animator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "examples")


class T:
    def __init__(self):
        self.passed = 0
        self.failed = []

    def check(self, cond, what):
        if cond:
            self.passed += 1
        else:
            self.failed.append(what)
            print("FAIL:", what)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def examples():
    return sorted(os.path.join(EX, f) for f in os.listdir(EX) if f.endswith(".json"))


def test_parts(t, fast):
    t.check(len({p.id for p in catalog.PARTS}) == len(catalog.PARTS), "discoverable family IDs are unique")
    for p in catalog.PARTS:
        base = p.build(p.defaults())
        t.check(any(pc.cage()[0] for pc in base.pieces.values()), "%s has geometry" % p.id)
        for k, (lo, hi, d) in p.params.items():
            for v in (lo, hi):
                if abs(v - d) < 1e-9:
                    continue
                prm = p.defaults()
                prm[k] = v
                var = p.build(prm)
                same_topo = all(var.pieces[n].signature() == base.pieces[n].signature() for n in base.pieces)
                if k not in p.topology_changes:
                    t.check(same_topo, "%s %s=%.2f keeps cage topology" % (p.id, k, v))
                moved = max(((a - b).length for n in base.pieces for a, b in zip(base.pieces[n].cage()[0] + base.pieces[n].cage(None, True)[0],
                                                                                var.pieces[n].cage()[0] + var.pieces[n].cage(None, True)[0])), default=0)
                t.check(moved > 1e-4 or (k in p.topology_changes and not same_topo),
                        "%s param %s=%.2f changes the shape" % (p.id, k, v))
        if not fast:
            reset()
            ctx, regions = finish.part_regions(p, p.defaults())
            tris = sum(len(f) for regs in regions.values() for _, _, f in regs)
            t.check(tris > 0, "%s finishes into a sculpted mesh" % p.id)


def test_recipes(t):
    from . import review
    dragon = R.load(os.path.join(EX, "dragon.json"))
    decision = review.record(dragon, True, "Inspected assembly")
    review.require(dragon, decision)
    dragon["limbs"][0]["segments"][0][1] -= 0.1
    try:
        review.require(dragon, decision)
    except ValueError:
        t.check(True, "changing a limb invalidates the assembly review")
    else:
        t.check(False, "changing a limb invalidates the assembly review")
    for path in examples():
        r1, w1 = R.normalize(R.load(path))
        r2, w2 = R.normalize(json.loads(R.to_json(r1)))
        t.check(R.to_json(r1) == R.to_json(r2), "round-trip stable: " + os.path.basename(path))
        t.check(not w2, "normalized recipe re-normalizes cleanly: %s %s" % (os.path.basename(path), w2))
    bad = R.default_recipe()
    bad["spine"][0]["w"] = 99
    bad["parts"] = [{"part": "horn_spike", "params": {"length": 50}}, {"part": "nope"}]
    r, w = R.normalize(bad)
    t.check(r["spine"][0]["w"] <= R.LIMITS["radius"][1] and len(r["parts"]) == 1 and len(w) >= 3, "clamps and removals are reported")


def test_placement(t):
    r = R.default_recipe()
    r["version"] = 1  # legacy placement migration
    r["parts"] = [
        {"uid": "a", "part": "spike", "u": 0.5, "theta": 84},           # near the midline -> centred
        {"uid": "b", "part": "spike", "u": 0.5, "theta": 60},           # lateral -> twin
        {"uid": "c", "part": "spike", "u": 0.5, "theta": 120},          # -X side -> canonical +X
        {"uid": "d", "part": "brow_ridge", "u": 0.94, "theta": 40},     # centre-only part
        {"uid": "e", "part": "eye_round", "u": 0.94, "theta": 90},      # paired-ish part at midline -> centred cyclops is fine
        {"uid": "f", "part": "ear_pointy", "u": 0.9, "theta": 90},      # pair-only part forced off the midline
    ]
    r["limbs"] = [{"uid": "l1", "u": 0.4, "theta": -84, "segments": [[0.1, -0.3, 0], [0.05, -0.3, 0]]},
                  {"uid": "l2", "u": 0.4, "theta": -130, "segments": [[-0.1, -0.3, 0], [0, -0.3, 0]]}]
    n, _ = R.normalize(r)
    P = {p["uid"]: p for p in n["parts"]}
    t.check(P["a"]["theta"] == 90.0, "part near the midline snaps to centre")
    t.check(P["b"]["theta"] == 60.0, "lateral part keeps its side")
    t.check(P["c"]["theta"] == 60.0, "-X side part is reflected to the +X side")
    t.check(P["d"]["theta"] == 90.0, "centre-only part is forced onto the midline")
    t.check(abs(abs(P["f"]["theta"]) - 90) > 0.5, "pair-only part is kept off the midline")
    L = {l["uid"]: l for l in n["limbs"]}
    t.check(L["l1"]["theta"] == -90.0 and all(s[0] == 0.0 for s in L["l1"]["segments"]), "limb near the midline is centred (x = 0)")
    t.check(L["l2"]["theta"] == -50.0 and L["l2"]["segments"][0][0] == 0.1, "-X side limb is reflected to +X")
    reset()
    res = builder.build(n, "preview")
    counts = {}
    for pr in res["rig"]["parts"]:
        counts[pr["uid"]] = counts.get(pr["uid"], 0) + 1
    t.check(counts["a"] == 1 and counts["d"] == 1, "centred parts are single")
    t.check(counts["b"] == 2 and counts["c"] == 2 and counts["f"] == 2, "lateral parts get a reflected twin automatically")
    t.check(res["report"]["legs"] + sum(1 for l in res["rig"]["limbs"] if l["role"] != "leg") == 3, "centred limb is single, lateral limb is paired")
    snapped, _ = ops.apply_all(R.default_recipe(), [{"op": "add_part", "part": "horn_bull", "u": 0.91, "theta": 50, "snap": True}])
    t.check((snapped["parts"][0]["u"], snapped["parts"][0]["theta"]) == placement.SOCKETS["horn"]["horns"], "add_part snaps to the nearest socket")


def test_ops(t):
    r, errs = ops.apply_all(R.default_recipe(), [
        {"op": "add_limb", "uid": "leg", "u": 0.4, "theta": -60, "segments": [[0.1, -0.3, 0], [0, -0.3, 0]], "tip": "foot_paw"},
        {"op": "add_part", "part": "eye_round"}, {"op": "set_part", "uid": "eye1", "params": {"size": 1.5}},
        {"op": "insert_vertebra", "index": -1}, {"op": "set_vertebra", "index": 0, "w": 0.2}, {"op": "scale_body", "w": 1.1},
        {"op": "set_paint", "pattern": "spots"}, {"op": "add_part", "part": "spike", "on": "leg", "u": 0.5, "theta": 0},
        {"op": "set_limb", "uid": "leg", "tip_params": {"size": 1.3}}])
    t.check(not errs, "ops apply cleanly %s" % errs)
    t.check(len(r["spine"]) == 6 and r["parts"][0]["params"]["size"] == 1.5 and r["limbs"][0]["tip_params"]["size"] == 1.3, "ops edit the recipe")
    r2, _ = ops.apply_all(r, [{"op": "remove_limb", "uid": "leg"}])
    t.check(not r2["limbs"] and len(r2["parts"]) == 1, "remove_limb removes its parts")
    _, errs = ops.apply_all(r, [{"op": "bogus"}, {"op": "remove_part", "uid": "zzz"}])
    t.check(len(errs) == 2, "bad ops are reported")


def test_research_library(t):
    from .shapes import extract, normalize_shape

    t.check(len(catalog.RESEARCH) == 54 and catalog.get("eye_slit_pupil") is None,
            "camera-eye variants share one research family")
    t.check(catalog.get("eye_round") not in catalog.PARTS, "old eye IDs load outside the active palette")
    for query, expected in (("human hands", "hand_basic"), ("round pupil", "eye_camera"),
                            ("bird foot", "talons"), ("dorsal crest", "crest_dorsal")):
        t.check([part.id for part in catalog.search(query, limit=1)] == [expected],
                f"catalog search finds the current family for {query}")
    for query in ("spiked hair", "eye_round", "   "):
        t.check(not catalog.search(query), f"catalog search does not substitute a part for {query!r}")
    boots = catalog.search("boots", limit=1)
    t.check(bool(boots) and catalog.search_shape(boots[0], "boots") == {"part": "foot_hoof", "params": {"split": 0}},
            "boot search supplies the closed hoof settings")
    shape, warnings = normalize_shape({"family": "leg_arthropod", "params": {"segments": 5}})
    r, errors = ops.apply_all(R.default_recipe(), [
        {"op": "attach_shape", "shape": shape, "uid": "leg", "u": .55, "theta": -54},
        {"op": "add_part", "part": "suckers", "on": "leg"},
    ])
    normalized, changes = R.normalize(r)
    limb = normalized["limbs"][0]
    t.check(not (warnings or errors or changes) and extract(limb) == shape and len(limb["segments"]) > 5,
            "detailed limb shape round-trips its authored chain and hosts parts")
    _, errors = ops.apply_all(R.default_recipe(), [{"op": "add_part", "part": "suckers"}])
    t.check(bool(errors), "sucker rows require a limb host")
    r, errors = ops.apply_all(R.default_recipe(), [
        {"op": "add_part", "part": "bell_radial", "uid": "first"},
        {"op": "add_part", "part": "bell_radial", "uid": "second", "scale": 1.25},
    ])
    reset()
    result = builder.build(r, "preview")
    t.check(not errors and len(result["recipe"]["parts"]) == 1 and abs(result["report"]["clearance"]) < 1e-5,
            "selecting a second bell replaces the core and grounds the emitted canopy")
    r, errors = ops.apply_all(R.default_recipe(), [
        {"op": "add_part", "part": "nose_pad", "uid": "pad", "on": "snout"},
        {"op": "add_part", "part": "muzzle", "uid": "snout", "scale": 1.4},
    ])
    reset()
    result = builder.build(r, "preview")
    muzzle, nose = result["rig"]["parts"]
    t.check(not errors and not result["report"]["warnings"] and nose["parent"] == muzzle["bone"],
            "a nose pad follows a muzzle even when recipe order is reversed")
    moved, _ = ops.apply_all(r, [{"op": "set_part", "uid": "snout", "scale": 1.8}])
    result2 = builder.build(moved, "preview")
    m2, n2 = result2["rig"]["parts"]
    rest = result["rig"]["rest"]
    moved_rest = result2["rig"]["rest"]
    reach = (Vector(rest[nose["bone"]]) - Vector(rest[muzzle["bone"]])).length
    moved_reach = (Vector(moved_rest[n2["bone"]]) - Vector(moved_rest[m2["bone"]])).length
    t.check(abs(moved_reach / reach - 1.8 / 1.4) < 1e-5, "nose seat scales with its host")
    removed, _ = ops.apply_all(r, [{"op": "remove_part", "uid": "snout"}])
    t.check(not removed["parts"], "removing a muzzle also removes its mounted pad")


def test_isolated_edits(t):
    from .shapes import extract, isolated
    def landmarks(r):
        b = builder.Builder(r, "preview")
        sp = R.Spine(b.recipe["spine"])
        b.resolve_limbs(sp)
        ground = b.ground_level(sp)
        return {l["name"]: [v - Vector((0, ground, 0)) for v in (l["joints"][0], l["sole"])]
                for l in b.limbs if l["role"] == "leg"}

    bull = R.load(os.path.join(EX, "bull.json"))
    # Reproduce the original v1 tail edit through the normal operation entry point.
    legacy = leg_recipe(4)
    legacy["version"] = 1
    legacy["spine"].insert(0, dict(legacy["spine"][0], z=-1.7))
    for src, op in [(legacy, {"op": "set_vertebra", "index": 0, "z": -2.7}),
                    (bull, {"op": "set_limb", "uid": "tail", "scale": 2})]:
        before = landmarks(src)
        moved, errors = ops.apply_all(src, [op])
        after = landmarks(moved)
        t.check(not errors and before.keys() == after.keys() and all(
            (a - b).length < 0.00002 for k in before for a, b in zip(before[k], after[k])),
            "lengthening tail leaves all planted limb landmarks fixed")
    base, _ = R.normalize(bull)
    old_bind = next(l["bind"] for l in base["limbs"] if l["uid"] == "fore")
    for edit in ({"op": "insert_vertebra", "index": 0}, {"op": "remove_vertebra", "index": 0}):
        edited, _ = ops.apply_all(base, [edit])
        placed, warnings = R.normalize(edited)
        target = next(l for l in placed["limbs"] if l["uid"] == "fore")
        t.check(target["bind"] == old_bind and not warnings, "ring insertion/deletion outside the strip preserves its binding")
    fore = next(l for l in base["limbs"] if l["uid"] == "fore")
    draft = extract(fore)
    for u, theta in [(0.31, 22), (0.48, 90), (0.76, -42)]:
        edited, _ = ops.apply_all(base, [{"op": "set_limb", "uid": "fore", "u": u, "theta": theta}])
        new, _ = R.normalize(edited)
        instance = next(l for l in new["limbs"] if l["uid"] == "fore")
        t.check(extract(instance) == draft and abs(instance["u"] - u) < 1e-6, "sliding preserves authored geometry")
        b = builder.Builder(new, "preview")
        b.resolve_limbs(R.Spine(new["spine"]))
        bends = any(abs(sg[0]) > 1e-6 for sg in instance["segments"])
        # Off the midline: a reflected pair. On it: single only if the shape is itself
        # symmetric; a sideways-bending shape is mirrored so the creature stays symmetric.
        t.check(sum(l["uid"] == "fore" for l in b.limbs) == (2 if theta != 90 or bends else 1), "surface and shape determine copy count")
    expanded, _ = ops.apply_all(base, [{"op": "scale_body", "w": 1.15}])
    t.check(landmarks(expanded)["fore"][0].x > landmarks(base)["fore"][0].x, "chest width carries the root outward")
    reset()
    objects, warnings = isolated(draft)
    t.check(len(objects) == 2 and not warnings, "isolated foreleg has one skin mesh and its hoof")
    attached, errors = ops.apply_all(R.default_recipe(), [{"op": "attach_shape", "shape": draft, "u": .31, "theta": 15}])
    t.check(not errors and extract(R.normalize(attached)[0]["limbs"][0]) == draft, "reattached draft round-trips its shape")


def leg_recipe(n):
    r = R.default_recipe()
    r["name"] = "legs%d" % n
    r["spine"] = [{"y": 0.75, "z": -0.9 + 1.8 * i / 5, "w": 0.3 if i in (0, 5) else 0.4, "h": 0.3 if i in (0, 5) else 0.4} for i in range(6)]
    o = []
    pairs = n // 2
    for i in range(pairs):
        u = 0.3 + 0.4 * i / max(pairs - 1, 1) if pairs > 1 else 0.45
        o.append({"op": "add_limb", "uid": "p%d" % i, "u": u, "theta": -50, "segments": [[0.15, -0.3, 0], [0.03, -0.32, 0.04]], "radii": [0.1, 0.07, 0.05], "tip": "foot_paw", "tip_params": {"size": 0.8}})
    if n % 2:
        o.append({"op": "add_limb", "uid": "c", "u": 0.5 if pairs else 0.45, "theta": -90, "segments": [[0, -0.232, -0.05], [0, -0.242, 0.05]], "radii": [0.12, 0.08, 0.06], "tip": "foot_pad", "tip_params": {"size": 0.8}})
    return ops.apply_all(r, o)[0]


def finite(an):
    return all(all(math.isfinite(x) for x in list(g.o) + [c for row in g.b for c in row]) for g in an.G)


def test_animation(t):
    for n in range(9):
        reset()
        res = builder.build(leg_recipe(n), "preview")
        t.check(res["report"]["legs"] == n, "synthetic creature has %d legs (got %d)" % (n, res["report"]["legs"]))
        an = Animator(res["rig"])
        an.play("walk")
        start = an.world.o.copy()
        ok = True
        for _ in range(90):
            an.step(1 / 30)
            ok = ok and finite(an)
        t.check(ok, "%d-leg walk stays finite" % n)
        t.check((an.world.o - start).length > 0.1, "%d-leg creature travels" % n)
    expect = {"bull": 4, "minotaur": 2, "beetle": 6, "serpent": 0, "bird": 2, "spider": 8, "crab": 6, "hopper": 1, "dragon": 4}
    for path in examples():
        key = os.path.basename(path)[:-5]
        reset()
        res = builder.build(R.load(path), "preview")
        rep = res["report"]
        t.check(not rep["warnings"] or key == "bird", "%s builds without warnings %s" % (key, rep["warnings"]))
        if key in expect:
            t.check(rep["legs"] == expect[key], "%s has %d legs (got %d)" % (key, expect[key], rep["legs"]))
        if not rep["legs"]:
            continue
        for clip, turn in (("walk", 0.0), ("run", 0.0), ("walk", 0.6)):
            an = Animator(res["rig"])
            an.play(clip)
            if turn:
                an.drive(1.0, turn, False)
                an.speed = an.target_speed
            worst = 0.0
            torso = []
            for f in range(150):
                an.step(1 / 60)
                if f < 30:
                    continue
                body = an.G[an.rig["spine"][an.rig["hub"]]]
                torso.append((body.o.x, body.o.y, math.atan2(body.b[1][0], body.b[0][0])))
                for st in an.legs:
                    if not st["swinging"]:
                        worst = max(worst, (an.posed_sole(st) - st["plant"]).length / max(st["length"], 0.01))
            if len(an.legs) >= 3 and clip == "walk" and not turn:
                spans = [max(values) - min(values) for values in zip(*torso)]
                t.check(spans[0] < .04 * an.leg_len and spans[1] < .08 * an.leg_len and spans[2] < .05,
                        "%s steady walk torso excursion %s" % (key, spans))
            t.check(worst < 0.05, "%s %s%s planted-foot drift %.3f < 0.05" % (key, clip, " turning" if turn else "", worst))
        an = Animator(res["rig"])
        ok = True
        for a in ("roar", "wave", "hop"):
            an.play(a)
            for _ in range(60):
                an.step(1 / 30)
            ok = ok and finite(an)
        t.check(ok, "%s plays all actions" % key)


def islands(ob):
    """Sizes of connected vertex islands, largest first."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    seen, sizes = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        size, stack = 0, [v]
        seen.add(v.index)
        while stack:
            x = stack.pop()
            size += 1
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        sizes.append(size)
    bm.free()
    return sorted(sizes, reverse=True)


def test_build_and_export(t):
    from . import baker
    reset()
    a = builder.build(R.load(os.path.join(EX, "dragon.json")), "preview")
    ha = hashlib.sha1(str([tuple(round(c, 5) for c in v.co) for v in a["skin"].data.vertices[:2000]]).encode()).hexdigest()
    reset()
    b = builder.build(R.load(os.path.join(EX, "dragon.json")), "preview")
    hb = hashlib.sha1(str([tuple(round(c, 5) for c in v.co) for v in b["skin"].data.vertices[:2000]]).encode()).hexdigest()
    t.check(ha == hb, "same recipe builds identical geometry")
    reset()
    res = builder.build(R.load(os.path.join(EX, "bull.json")), "final")
    isl = islands(res["skin"])
    t.check(isl[0] / sum(isl) > 0.95, "bull body, legs and skin parts fuse into one surface (islands %s)" % isl[:5])
    t.check(len(res["skin"].vertex_groups) > 10, "skin is weighted to the skeleton")
    contacts = []
    clips = baker.bake_all(res["armature"], contacts=contacts)
    t.check(len(clips) == 6, "six clips baked")
    d = tempfile.mkdtemp()
    for fmt in ("glb", "fbx", "obj"):
        path = export.export(res, os.path.join(d, "bull." + fmt), fmt)
        t.check(os.path.getsize(path) > 10000, "%s export written" % fmt)
    import runpy
    from pathlib import Path
    fixture = Path(d, "bull.glb")
    rig = res["rig"]
    lengths = {rig["names"][l["bones"][-1]]: l["length"] for l in rig["limbs"] if l["role"] == "leg"}
    fixture.with_suffix(".report.json").write_text(json.dumps({"contact": {"frames": contacts, "legs": lengths}}))
    scripts = Path(ROOT, "tools", "tests")
    runpy.run_path(str(scripts / "export_contact.py"))["check"](fixture)
    t.check(True, "exported and reimported hoof surfaces plant, lift and hold")
    reset()
    bpy.ops.import_scene.gltf(filepath=os.path.join(d, "bull.glb"))
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    t.check(len(arms) == 1 and len(arms[0].data.bones) == res["report"]["bones"], "re-imported GLB keeps the skeleton")
    names = {a.name for a in bpy.data.actions}
    t.check(all(any(c in n for n in names) for c in baker.CLIPS), "re-imported GLB carries all clips %s" % sorted(names))


def test_review_fixes(t):
    """Regressions from the PR 21 review."""
    from . import baker
    # 1. Limb edits re-ground; spine edits keep the floor.
    r = leg_recipe(4)
    r, _ = ops.apply_all(r, [{"op": "insert_vertebra", "index": 0}])
    t.check("ground_y" in r, "spine edit freezes the floor height")
    r, _ = ops.apply_all(r, [{"op": "set_limb", "uid": "p0", "segments": [[0.15, -0.2, 0], [0.03, -0.22, 0.04]]}])
    t.check("ground_y" not in r, "limb edit re-grounds")
    r, _ = ops.apply_all(r, [{"op": "set_limb", "uid": "p1", "segments": [[0.15, -0.2, 0], [0.03, -0.22, 0.04]]}])
    reset()
    res = builder.build(r, "preview")
    t.check(res["report"]["legs"] == 4 and not res["report"]["warnings"], "shortened legs still reach the ground %s" % res["report"]["warnings"])
    kept, _ = ops.apply_all({**r, "ground_y": 0.5}, [{"op": "set_limb", "uid": "p0", "radii": [0.1, 0.07, 0.05], "keep_ground": True}])
    t.check(kept.get("ground_y") == 0.5 and "keep_ground" not in kept["limbs"][0], "keep_ground keeps the floor and is not stored")
    from importlib import import_module
    import sys as _sys
    _sys.path.insert(0, os.path.join(ROOT, "ai"))
    opt = import_module("optimize")
    t.check("ground_y" not in opt.apply_knobs({**r, "ground_y": 0.5}, [], []), "fitter drops a frozen floor")
    # 2. A version-2 limb that snaps to the midline stays symmetric: a sideways shape
    #    becomes a mirrored pair (authored geometry kept), a straight one stays single.
    v2 = R.normalize(R.default_recipe())[0]
    v2, _ = ops.apply_all(v2, [{"op": "add_limb", "uid": "mid", "u": 0.45, "theta": -82, "rot": [10, 20, 30],
                                "segments": [[0.12, -0.3, 0.05], [0.0, -0.3, 0.0]], "tip": "foot_pad"},
                               {"op": "add_limb", "uid": "straight", "u": 0.6, "theta": -88,
                                "segments": [[0.0, -0.3, 0.05], [0.0, -0.3, 0.0]], "tip": "foot_pad"}])
    n, _ = R.normalize(v2)
    t.check(n["limbs"][0]["theta"] == -90.0 and n["limbs"][0]["segments"][0][0] == 0.12, "midline snap keeps the authored limb shape")
    reset()
    res = builder.build(n, "preview")
    copies = {}
    for lm in res["rig"]["limbs"]:
        copies.setdefault(lm["uid"], []).append(lm)
    mid = copies["mid"]
    t.check(len(mid) == 2 and all(abs(a + b) < 1e-5 for a, b in zip([j[0] for j in mid[0]["joints"]], [j[0] for j in mid[1]["joints"]])),
            "sideways limb on the midline gets a mirror twin")
    t.check(len(copies["straight"]) == 1, "straight limb on the midline stays single")
    # 5/6. Rebuilds and rebakes do not leave orphan data.
    reset()
    res = builder.build(R.load(os.path.join(EX, "hopper.json")), "preview")
    baker.bake_all(res["armature"])
    n_actions = len(bpy.data.actions)
    baker.bake_all(res["armature"])
    t.check(len(bpy.data.actions) == n_actions, "rebaking replaces the previous actions (%d -> %d)" % (n_actions, len(bpy.data.actions)))
    builder.build(R.load(os.path.join(EX, "hopper.json")), "preview")
    t.check(not any(m.name.startswith("PF_skin.") for m in bpy.data.materials if m.users == 0), "rebuilds reuse the skin material")


def test_hoof_groove(t):
    from mathutils.bvhtree import BVHTree

    part = catalog.get("foot_hoof")
    gaps = []
    for split in (0.0, .0001, .05, .25, .6, 1.0):
        _, regions = finish.part_regions(part, {**part.defaults(), "split": split})
        _, verts, faces = next(region for region in regions["self"] if region[0] == "dark")
        tree = BVHTree.FromPolygons(verts, faces)
        hit = tree.ray_cast(Vector((0, -.116, .25)), Vector((0, 0, -1)))[0]
        t.check((hit is not None) == (split == 0), f"hoof split {split} has the expected center toe opening")
        gaps.append(0.0 if split == 0 else min(abs(v.x) for v in verts))
    t.check(all(a < b for a, b in zip(gaps, gaps[1:])), "hoof groove widens as split increases")


def test_character_compile(t):
    from .character import compile_recipe

    brief = {"body_plan": "humanoid", "style": "standard", "head_fraction": .05,
             "face": "oval", "eyes": "small", "hair": "bald", "feet": "bare"}
    regular = compile_recipe(brief)
    chibi = compile_recipe({**brief, "style": "chibi", "head_fraction": .93,
                            "hair": "spiky", "feet": "boots"})
    t.check(len(regular["limbs"]) == len(chibi["limbs"]) == 2 and
            regular["limbs"][0]["family"] == chibi["limbs"][0]["family"] == "leg_plantigrade" and
            chibi["limbs"][0]["tip_params"]["split"] == 0,
            "character compiler fits valid rigs at proportion bounds and chooses footwear")
    t.check(all(a["segments"] == b["segments"] and a["radii"] == b["radii"] and a["scale"] > b["scale"]
                for a, b in zip(regular["limbs"], chibi["limbs"])),
            "proportion changes scale complete limb chains while preserving their local shapes")
    t.check(max(r["w"] for r in chibi["spine"]) > max(r["w"] for r in regular["spine"]) and
            any(part["part"] == "hair_crown" for part in chibi["parts"]),
            "chibi classification yields an oversized head and styled hair")
    booted = compile_recipe({**brief, "feet": "boots"})
    from .spine import Spine
    model = builder.Builder(booted, "preview")
    model.resolve_limbs(Spine(booted["spine"]))
    leg = model.limbs[0]
    toe = catalog.get(leg["tip"]).build(leg["tip_params"]).pieces["self"].cage("dark")[0]
    t.check(leg["joints"][-1].x + leg["scale"] * min(point.x for point in toe) > .01,
            "full-size boots clear the midline on long-legged proportions")


def test_humanoid_gait(t):
    from .character import compile_recipe

    source = compile_recipe({"body_plan": "humanoid", "style": "chibi", "head_fraction": .57,
                             "face": "round", "eyes": "angled", "hair": "bald", "feet": "boots"})
    reset()
    result = builder.build(source, "preview")
    scale = 1.25
    resized, errors = ops.apply_all(source, [
        {"op": "set_limb", "uid": limb["uid"], "scale": limb["scale"] * scale} for limb in source["limbs"]
    ])
    reset()
    resized_result = builder.build(resized, "preview")
    t.check(not errors and all(
        abs(a["length"] * scale - b["length"]) < .001 and
        (Vector(a["sole_local"]) * scale - Vector(b["sole_local"])).length < .001
        for a, b in zip(result["rig"]["limbs"], resized_result["rig"]["limbs"])
    ), "resizing rebuilds limb lengths and sole offsets at the same scale")
    for label, rig in (("humanoid", result["rig"]), ("resized humanoid", resized_result["rig"])):
        _check_humanoid_gait(t, label, rig)


def _check_humanoid_gait(t, label, rig):
    for clip, minimum_period in (("walk", .85), ("run", .58)):
        anim = Animator(rig)
        anim.play(clip)
        dt = anim.cycle_length() / 60
        worst_plant, least_forward, lateral = 0.0, float("inf"), 0.0
        for frame in range(120):
            anim.step(dt)
            if frame < 60:
                continue
            for leg in anim.legs:
                hip, knee, ankle = (anim.G[bone].o for bone in leg["bones"])
                axis = (ankle - hip).normalized()
                bend = knee - hip - axis * (knee - hip).dot(axis)
                least_forward = min(least_forward, bend.z)
                lateral = max(lateral, abs(bend.x))
                if not leg["swinging"]:
                    worst_plant = max(worst_plant, (anim.posed_sole(leg) - leg["plant"]).length)
        t.check(anim.cycle_length() >= minimum_period, f"{label} {clip} has a readable cadence")
        t.check(least_forward > 0 and lateral < .04 * anim.leg_len,
                f"{label} {clip} knees stay forward through the cycle")
        t.check(worst_plant < .004 * anim.leg_len, f"{label} {clip} keeps stance feet planted ({worst_plant:.5f})")


def run(fast=False):
    t = T()
    t0 = time.time()
    test_recipes(t)
    test_placement(t)
    test_ops(t)
    test_research_library(t)
    test_isolated_edits(t)
    test_review_fixes(t)
    test_hoof_groove(t)
    test_character_compile(t)
    test_humanoid_gait(t)
    test_parts(t, fast)
    test_animation(t)
    test_build_and_export(t)
    print("tests: %d passed, %d failed (%.0fs)" % (t.passed, len(t.failed), time.time() - t0))
    for f in t.failed:
        print("  -", f)
    return 1 if t.failed else 0
