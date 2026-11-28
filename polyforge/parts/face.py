"""Eyes, mouths and noses. "face" frame: +Y out of the head, +Z up, +X lateral.

Sculpted clay style: eyeballs sit under lofted lids, muzzles have carved
nostrils, jaws are rounded masses. Each sculpt region is remeshed separately.
"""
import math
from ..kit import V, UP, BACK, RIGHT, FORWARD, rot, curve_points, taper, lerp
from . import Part


def _lids(g, r, lid, cx=0.0, cy=0.0, cz=0.0, spread=1.0):
    """Upper and lower eyelid arcs hugging an eyeball of radius r centred at (cx, cy, cz)."""
    up, lo = [], []
    for i in range(5):
        a = math.radians(lerp(-75, 75, i / 4)) * spread
        drop = lid * 0.55
        up.append(V(cx + math.sin(a) * r * 1.02, cy + math.cos(a) * r * 0.62 + r * 0.25, cz + r * (0.78 - drop) * math.cos(a * 0.8)))
        lo.append(V(cx + math.sin(a) * r * 1.0, cy + math.cos(a) * r * 0.55 + r * 0.22, cz - r * 0.82 * math.cos(a * 0.8)))
    g.loft(up, [r * 0.16, r * 0.26, r * 0.3, r * 0.26, r * 0.16], sides=14, up=BACK, density=4)
    g.loft(lo, [r * 0.1, r * 0.17, r * 0.2, r * 0.17, r * 0.1], sides=12, up=BACK, density=4)


def eye_round(g, p):
    r = 0.075 * p["size"]
    g.setup(voxel=max(0.0018, r / 30))
    g.slot("white")
    g.oval(V(0, 0.2 * r, 0), (r, r * 0.92, r))
    g.slot("black")
    pr = r * p["pupil"] * 0.62
    g.oval(V(0, 1.02 * r, 0.03 * r), (pr, r * 0.16, pr * 1.05), segs=20, rings=10)
    g.slot("skin")
    _lids(g, r, p["lid"])
    b = p["brow"]
    g.loft([V(-r * 1.2, r * 0.25, r * (0.95 + 0.25 * b)), V(0, r * (0.55 + 0.25 * b), r * (1.18 + 0.35 * b)), V(r * 1.3, r * 0.3, r * (0.98 + 0.15 * b))],
           [r * (0.12 + 0.2 * b), r * (0.2 + 0.32 * b), r * (0.1 + 0.18 * b)], sides=14, up=BACK)


def eye_bug(g, p):
    r = 0.12 * p["size"]
    g.slot("dark")
    g.oval(V(0, 0, 0), (r, r * p["bulge"], r * 1.12))
    g.slot("white")
    g.oval(V(r * 0.32, r * p["bulge"] * 0.9, r * 0.38), r * 0.14, segs=14, rings=8)
    g.slot("skin")
    g.loft([V(-r, -r * 0.2, r * 0.7), V(0, r * 0.15 * p["bulge"], r * 1.12), V(r, -r * 0.2, r * 0.7)], [r * 0.08, r * 0.14, r * 0.08], sides=12, up=BACK)


def eye_slit(g, p):
    r = 0.07 * p["size"]
    g.setup(voxel=max(0.0018, r / 30))
    g.slot("eye")
    g.oval(V(0, 0.18 * r, 0), (r, r * 0.9, r))
    g.slot("black")
    g.oval(V(0, 1.0 * r, 0), (r * p["slit"] * 0.45, r * 0.15, r * 0.75), segs=16, rings=10)
    g.slot("skin")
    _lids(g, r, 0.25 + p["lid"] * 0.5, spread=1.1)


def eye_stalk(g, p):
    s, h = p["size"], p["height"]
    r = 0.065 * s
    pts = curve_points(V(0, -0.03, 0), UP, V(0, 0, p["lean"]), h, 5)
    g.slot("skin")
    g.loft(pts, taper(0.04 * s, 0.026 * s, 5), sides=16, up=BACK)
    top = pts[-1]
    g.oval(top + V(0, r * 0.45, 0), r * 1.05, segs=20, rings=12)
    g.slot("white")
    g.oval(top + V(0, r * 0.75, 0), r * 0.92)
    g.slot("black")
    g.oval(top + V(0, r * 1.62, 0), (r * 0.42, r * 0.14, r * 0.42), segs=16, rings=8)


def eye_cyclops(g, p):
    r = 0.14 * p["size"]
    g.slot("white")
    g.oval(V(0, 0.15 * r, 0), (r, r * 0.92, r))
    ir = r * p["pupil"]
    g.slot("eye")
    g.oval(V(0, 0.95 * r, 0), (ir * 0.95, r * 0.12, ir * 0.95), segs=22, rings=10)
    g.slot("black")
    g.oval(V(0, 1.03 * r, 0), (ir * 0.45, r * 0.1, ir * 0.45), segs=18, rings=8)
    g.slot("skin")
    _lids(g, r, 0.2 + 0.3 * p["lid"])
    g.loft([V(-r * 1.3, r * 0.3, r * 1.0), V(0, r * 0.75, r * 1.32), V(r * 1.3, r * 0.3, r * 1.0)], [r * 0.2, r * 0.32, r * 0.2], sides=14, up=BACK)


def eye_bead(g, p):
    r = 0.042 * p["size"]
    g.setup(voxel=max(0.0015, r / 22))
    g.slot("black")
    g.oval(V(0, 0.25 * r, 0), r)
    g.slot("white")
    g.oval(V(r * 0.35, r * 1.1, r * 0.4), r * 0.22, segs=12, rings=8)


# ---------------------------------------------------------------- mouths

def mouth_jaws(g, p):
    L, W, T = 0.3 * p["length"], p["width"], max(p["teeth"], 0.08)
    g.setup(voxel=0.0035)
    g.slot("base")
    g.loft([V(0, -0.06, 0.04), V(0, L * 0.35, 0.045), V(0, L * 0.75, 0.035), V(0, L, 0.01)],
           [(0.11 * W, 0.075), (0.1 * W, 0.07), (0.085 * W, 0.055), (0.05 * W, 0.04)], sides=24, up=BACK, exponent=0.8)
    g.cut_loft([V(-0.15 * W, L * 0.55, -0.025), V(0, L * 0.6, -0.03), V(0.15 * W, L * 0.55, -0.025)], [0.025, 0.03, 0.025], sides=10, up=BACK)
    g.slot("teeth")
    for side in (-1, 1):
        for i in range(4):
            y = L * (0.22 + 0.68 * i / 3)
            x = side * W * lerp(0.085, 0.04, y / L)
            g.cone(V(x, y, 0.0), V(x, y + 0.004, -0.045 * T), 0.013 * T ** 0.5, segs=10, up=BACK)
    g.use("jaw")
    g.setup(voxel=0.0035)
    g.slot("detail")
    g.loft([V(0, -0.06, -0.045), V(0, L * 0.4, -0.06), V(0, L * 0.8, -0.055), V(0, L * 0.95, -0.045)],
           [(0.095 * W, 0.045), (0.085 * W, 0.045), (0.07 * W, 0.038), (0.04 * W, 0.03)], sides=22, up=BACK, exponent=0.85)
    g.slot("teeth")
    for side in (-1, 1):
        for i in range(3):
            y = L * (0.3 + 0.5 * i / 2)
            x = side * W * lerp(0.07, 0.035, y / L)
            g.cone(V(x, y, -0.03), V(x, y + 0.004, -0.03 + 0.035 * T), 0.011 * T ** 0.5, segs=10, up=BACK)


def mouth_beak(g, p):
    L, W, hk = 0.26 * p["length"], p["width"], p["hook"]
    g.slot("horn")
    up = curve_points(V(0, -0.05, 0.015), V(0, 1, 0.04), V(0, 0, -0.55 * hk), L, 6)
    g.loft(up, [(0.085 * W, 0.07), (0.07 * W, 0.06), (0.05 * W, 0.045), (0.032 * W, 0.03), (0.016 * W, 0.016), (0.003, 0.003)], sides=22, up=BACK, exponent=0.9)
    g.use("jaw")
    g.slot("horn")
    lo = curve_points(V(0, -0.05, -0.035), V(0, 1, 0.02), V(0, 0, 0.1 * hk), L * 0.72, 5)
    g.loft(lo, [(0.07 * W, 0.04), (0.055 * W, 0.034), (0.035 * W, 0.024), (0.016 * W, 0.012), (0.003, 0.003)], sides=20, up=BACK, exponent=0.9)


def mouth_snout(g, p):
    """Bovine-style muzzle: broad nose pad with carved nostrils over a soft lower lip."""
    L, W, N = 0.13 * p["length"], p["width"], max(p["nostrils"], 0.1)
    g.setup(voxel=0.003)
    g.slot("detail")
    g.loft([V(0, -0.06, 0.05), V(0, L * 0.4, 0.035), V(0, L * 0.85, 0.02)], [(0.085 * W, 0.075), (0.1 * W, 0.08), (0.11 * W, 0.075)], sides=24, up=BACK)
    g.oval(V(0, L * 1.0, 0.0), (0.115 * W, 0.085, 0.088))
    for side in (-1, 1):
        g.cut_oval(V(side * 0.055 * W, L * 1.0 + 0.08, 0.025), (0.03 * N, 0.04 * N, 0.022 * N), rot(BACK, side * 0.45) @ rot(RIGHT, -0.4))
    g.use("jaw")
    g.setup(voxel=0.003)
    g.slot("detail")
    g.oval(V(0, L * 0.85, -0.085), (0.092 * W, 0.068, 0.038))


def mouth_smile(g, p):
    W, c, lr = 0.12 * p["width"], p["curve"], 0.02 * p["lips"]
    g.setup(voxel=0.0025)
    upper, lower = [], []
    for i in range(7):
        x = lerp(-W, W, i / 6)
        z = c * 1.2 * x * x / max(W, 0.01)
        upper.append(V(x, 0.015 - abs(x) * 0.35, z + lr * 0.5))
        lower.append(V(x, 0.01 - abs(x) * 0.35, z - lr * 1.4))
    g.slot("dark")
    g.loft([V(-W * 0.9, 0.0, c * W * 0.9), V(0, 0.005, -lr * 0.4), V(W * 0.9, 0.0, c * W * 0.9)], [(lr * 0.8, lr), (lr * 1.2, lr * 1.3), (lr * 0.8, lr)], sides=12, up=BACK)
    g.slot("accent")
    g.loft(upper, [lr * 0.5, lr * 0.7, lr * 0.8, lr * 0.85, lr * 0.8, lr * 0.7, lr * 0.5], sides=12, up=UP)
    g.use("jaw")
    g.setup(voxel=0.0025)
    g.slot("accent")
    g.loft(lower, [lr * 0.5, lr * 0.75, lr * 0.85, lr * 0.9, lr * 0.85, lr * 0.75, lr * 0.5], sides=12, up=UP)


def mouth_mandibles(g, p):
    L, sp = 0.22 * p["length"], 0.05 * p["spread"]
    for side, bone in ((1, "jaw"), (-1, "jaw2")):
        g.use(bone)
        g.slot("horn")
        pts = curve_points(V(side * sp, -0.03, -0.01), V(side * 0.25, 1, 0).normalized(), V(-side * p["curl"], 0, 0), L, 6)
        g.loft(pts, [0.035, 0.034, 0.028, 0.02, 0.011, 0.002], sides=16, up=BACK, exponent=0.85)
        g.oval(pts[0], 0.04, segs=16, rings=10)


def mouth_trunk(g, p):
    L, T = 0.55 * p["length"], p["thickness"]
    pts = curve_points(V(0, -0.05, 0), UP, V(0, -0.3, -p["droop"]), L, 9)
    rad = taper(0.085 * T, 0.038 * T, 9)
    g.pivots["jaw"] = pts[4]
    g.slot("skin")
    g.loft(pts[0:5], rad[0:5], sides=20, up=BACK)
    g.use("jaw")
    g.slot("skin")
    g.loft(pts[4:9], rad[4:9], sides=20, up=BACK)
    g.cut_oval(pts[8] + (pts[8] - pts[7]).normalized() * 0.02, (rad[8] * 0.45, rad[8] * 0.5, rad[8] * 0.45))


def nose_button(g, p):
    r = 0.045 * p["size"]
    g.slot("dark")
    g.oval(V(0, 0.3 * r, 0), (r * 1.25, r, r * 0.9))
    for side in (-1, 1):
        g.cut_oval(V(side * r * 0.45, r * 1.2, -r * 0.15), (r * 0.25, r * 0.3, r * 0.18))


F = dict(orient="face")
PARTS = [
    Part("eye_round", "eye", "Round eye under soft lids with an optional heavy brow (mammals, cartoon, bovines).", ["cute", "mammal", "cartoon", "bovine"],
         {"size": (0.4, 3.0, 1.0), "pupil": (0.3, 0.9, 0.55), "brow": (0.0, 1.0, 0.3), "lid": (0.0, 1.0, 0.3)}, eye_round, cap="look", mirror=True, hint={"u": 0.93, "theta": 35.0}, **F),
    Part("eye_bug", "eye", "Large compound eye, dark and glossy (insects, aliens).", ["insect", "alien", "creepy"],
         {"size": (0.4, 3.0, 1.0), "bulge": (0.4, 1.2, 0.8)}, eye_bug, cap="look", mirror=True, hint={"u": 0.93, "theta": 30.0}, **F),
    Part("eye_slit", "eye", "Reptile eye: raised iris with a vertical slit pupil under hooded lids.", ["reptile", "cat", "menacing"],
         {"size": (0.4, 3.0, 1.0), "slit": (0.1, 0.6, 0.25), "lid": (0.0, 1.0, 0.4)}, eye_slit, cap="look", mirror=True, hint={"u": 0.92, "theta": 40.0}, **F),
    Part("eye_stalk", "eye", "Eyeball on a bendy stalk (snails, crabs, aliens).", ["alien", "mollusk", "silly"],
         {"size": (0.4, 3.0, 1.0), "height": (0.1, 0.8, 0.3), "lean": (-0.6, 0.6, 0.2)}, eye_stalk, cap="look", mirror=True, hint={"u": 0.95, "theta": 70.0}, **F),
    Part("eye_cyclops", "eye", "Single large central eye with lids and a heavy brow.", ["monster", "alien"],
         {"size": (0.5, 3.0, 1.0), "pupil": (0.3, 0.9, 0.5), "lid": (0.0, 1.0, 0.3)}, eye_cyclops, cap="look", hint={"u": 0.95, "theta": 60.0}, **F),
    Part("eye_bead", "eye", "Small glossy bead eye with a highlight (birds, rodents, small critters).", ["bird", "rodent", "small"],
         {"size": (0.4, 3.0, 1.0)}, eye_bead, cap="look", mirror=True, hint={"u": 0.93, "theta": 30.0}, **F),
    Part("mouth_jaws", "mouth", "Toothy predator jaws (upper and hinged lower jaw).", ["predator", "reptile", "dinosaur", "menacing"],
         {"length": (0.4, 2.5, 1.0), "width": (0.5, 2.0, 1.0), "teeth": (0.0, 1.5, 1.0)}, mouth_jaws, cap="mouth", hint={"u": 0.97, "theta": -20.0},
         bones=[{"name": "jaw", "pivot": (0, -0.05, -0.02), "axis": (1, 0, 0), "angle": -38.0}], **F),
    Part("mouth_beak", "mouth", "Bird beak, optionally hooked (parrots, raptors) or straight.", ["bird", "turtle", "squid"],
         {"length": (0.3, 3.0, 1.0), "width": (0.5, 2.0, 1.0), "hook": (0.0, 1.0, 0.3)}, mouth_beak, cap="mouth", hint={"u": 0.98, "theta": -10.0},
         bones=[{"name": "jaw", "pivot": (0, -0.03, -0.03), "axis": (1, 0, 0), "angle": -25.0}], **F),
    Part("mouth_snout", "mouth", "Broad mammal muzzle with carved nostrils and a soft lower lip (bovines, pigs, dogs, bears).", ["mammal", "bovine", "pig", "dog"],
         {"length": (0.3, 2.5, 1.0), "width": (0.5, 2.2, 1.0), "nostrils": (0.0, 2.0, 1.0)}, mouth_snout, cap="mouth", hint={"u": 0.97, "theta": -15.0},
         bones=[{"name": "jaw", "pivot": (0, -0.02, -0.06), "axis": (1, 0, 0), "angle": -28.0}], **F),
    Part("mouth_smile", "mouth", "Friendly mouth with soft curved lips (cartoon, humanoid, frog).", ["cartoon", "humanoid", "frog", "friendly"],
         {"width": (0.4, 3.0, 1.0), "curve": (-1.0, 1.0, 0.5), "lips": (0.3, 2.0, 1.0)}, mouth_smile, cap="mouth", hint={"u": 0.97, "theta": -35.0},
         bones=[{"name": "jaw", "pivot": (0, -0.03, -0.02), "axis": (1, 0, 0), "angle": -22.0}], **F),
    Part("mouth_mandibles", "mouth", "Pair of curved insect mandibles that open sideways.", ["insect", "arachnid", "alien", "menacing"],
         {"length": (0.4, 2.5, 1.0), "curl": (0.0, 1.5, 0.7), "spread": (0.5, 2.0, 1.0)}, mouth_mandibles, cap="mouth", hint={"u": 0.98, "theta": -20.0},
         bones=[{"name": "jaw", "pivot": (0.05, 0.0, -0.01), "axis": (0, 0, 1), "angle": 25.0},
                {"name": "jaw2", "pivot": (-0.05, 0.0, -0.01), "axis": (0, 0, 1), "angle": -25.0}], **F),
    Part("mouth_trunk", "mouth", "Long flexible trunk or proboscis that curls up when 'opened'.", ["elephant", "tapir", "alien"],
         {"length": (0.3, 3.0, 1.0), "thickness": (0.4, 2.0, 1.0), "droop": (0.0, 1.5, 1.0)}, mouth_trunk, cap="mouth", hint={"u": 0.97, "theta": 0.0},
         bones=[{"name": "jaw", "pivot": (0, 0.25, -0.12), "axis": (1, 0, 0), "angle": 50.0}], **F),
    Part("nose_button", "nose", "Small round nose with nostrils (cartoon mammals).", ["cute", "mammal", "cartoon"],
         {"size": (0.4, 3.0, 1.0)}, nose_button, hint={"u": 0.99, "theta": 20.0}, **F),
]
