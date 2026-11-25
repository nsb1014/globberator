"""Eyes, mouths and noses. "face" frame: +Y out of the head, +Z up, +X lateral."""
import math
from kit import V, UP, BACK, RIGHT, FORWARD, rot, curve_points, taper, lerp
from parts import Part


def eye_round(g, p):
    r = 0.08 * p["size"]
    g.slot("white"); g.ellipsoid(V(0, 0.25 * r, 0), (r, r, r), None, 8, 5)
    g.slot("black")
    pr = r * p["pupil"] * 0.65
    g.ellipsoid(V(0, 1.08 * r, 0), (pr, r * 0.22, pr), None, 6, 3)
    b = max(p["brow"], 0.02)
    g.slot("accent")
    g.box(V(0, 0.7 * r, 0.95 * r), V(2.2 * r * b ** 0.3, 0.5 * r * b, 0.35 * r * (0.5 + b)), rot(FORWARD, 0.15 * b))


def eye_bug(g, p):
    r = 0.13 * p["size"]
    g.slot("dark"); g.ellipsoid(V(0, 0, 0), (r, r * p["bulge"], r * 1.1), None, 7, 4)
    g.slot("white"); g.ellipsoid(V(r * 0.3, r * p["bulge"] * 0.95, r * 0.35), (r * 0.15,) * 3, None, 4, 2)


def eye_slit(g, p):
    r = 0.075 * p["size"]
    g.slot("eye"); g.ellipsoid(V(0, 0.2 * r, 0), (r, r, r), None, 8, 5)
    g.slot("black"); g.box(V(0, 1.12 * r, 0), V(r * p["slit"], r * 0.12, r * 1.5))


def eye_stalk(g, p):
    s, h = p["size"], p["height"]
    pts = curve_points(V(0, -0.02, 0), UP, V(0, 0, p["lean"]), h, 4)
    g.slot("skin"); g.tube(pts, taper(0.035 * s, 0.022 * s, 4), 5, False, False, BACK)
    top, r = pts[3], 0.07 * s
    g.slot("white"); g.ellipsoid(top + V(0, r * 0.6, 0), (r, r, r), None, 7, 4)
    g.slot("black"); g.ellipsoid(top + V(0, r * 1.45, 0), (r * 0.4, r * 0.2, r * 0.4), None, 5, 3)


def eye_cyclops(g, p):
    r = 0.15 * p["size"]
    g.slot("white"); g.ellipsoid(V(0, 0.2 * r, 0), (r, r, r), None, 9, 6)
    ir = r * p["pupil"]
    g.slot("eye"); g.ellipsoid(V(0, 1.05 * r, 0), (ir, r * 0.2, ir), None, 8, 3)
    g.slot("black"); g.ellipsoid(V(0, 1.2 * r, 0), (ir * 0.5, r * 0.15, ir * 0.5), None, 6, 3)
    g.slot("accent"); g.box(V(0, 0.6 * r, 1.0 * r), V(2.4 * r, 0.6 * r, 0.4 * r))


def eye_bead(g, p):
    r = 0.045 * p["size"]
    g.slot("black"); g.ellipsoid(V(0, 0.3 * r, 0), (r, r, r), None, 6, 4)
    g.slot("white"); g.ellipsoid(V(r * 0.35, r * 1.15, r * 0.4), (r * 0.25,) * 3, None, 4, 2)


def mouth_jaws(g, p):
    L, W, T = 0.32 * p["length"], p["width"], max(p["teeth"], 0.05)
    g.slot("base")
    g.tube([V(0, -0.06, 0.03), V(0, L * 0.5, 0.025), V(0, L, 0.0)], [0.11, 0.09, 0.05], 6, False, True, BACK, (W, 0.55))
    g.slot("teeth")
    for side in (-1, 1):
        for i in range(3):
            y = L * (0.25 + 0.65 * i / 3)
            x = side * W * lerp(0.085, 0.04, y / L)
            g.cone(V(x, y, -0.015), V(x, y, -0.015 - 0.045 * T), 0.014 * T ** 0.5, 4, RIGHT)
    g.use("jaw")
    g.slot("detail")
    g.tube([V(0, -0.06, -0.05), V(0, L * 0.5, -0.06), V(0, L * 0.92, -0.055)], [0.09, 0.07, 0.04], 6, False, True, BACK, (W, 0.4))
    g.slot("teeth")
    for side in (-1, 1):
        for i in range(2):
            y = L * (0.35 + 0.5 * i)
            x = side * W * lerp(0.07, 0.035, y / L)
            g.cone(V(x, y, -0.04), V(x, y, -0.04 + 0.035 * T), 0.012 * T ** 0.5, 4, RIGHT)


def mouth_beak(g, p):
    L, W, hk = 0.28 * p["length"], p["width"], p["hook"]
    g.slot("horn")
    g.tube(curve_points(V(0, -0.04, 0.01), V(0, 1, 0.05), V(0, 0, -0.5 * hk), L, 5), taper(0.085, 0.005, 5, 0.8), 6, False, True, BACK, (W, 0.8))
    g.use("jaw")
    g.tube(curve_points(V(0, -0.04, -0.04), V(0, 1, 0.05), V(0, 0, 0), L * 0.72, 4), taper(0.06, 0.005, 4), 6, False, True, BACK, (W * 0.9, 0.5))


def mouth_snout(g, p):
    L, W = 0.14 * p["length"], p["width"]
    g.slot("detail"); g.ellipsoid(V(0, L * 0.7, 0), (0.12 * W, L + 0.03, 0.1), None, 8, 5)
    nr = 0.022 * max(p["nostrils"], 0.05)
    g.slot("dark")
    for side in (-1, 1):
        g.ellipsoid(V(side * 0.05 * W, L * 1.65 + 0.02, 0.025), (nr, nr * 0.6, nr * 0.8), None, 5, 3)
    g.use("jaw")
    g.slot("detail"); g.ellipsoid(V(0, L * 0.6, -0.1), (0.085 * W, L * 0.8, 0.04), None, 6, 3)


def mouth_smile(g, p):
    W, c, lr = 0.12 * p["width"], p["curve"], 0.018 * p["lips"]
    upper, lower = [], []
    for i in range(7):
        x = lerp(-W, W, i / 6)
        z = c * 1.2 * x * x / max(W, 0.01)
        upper.append(V(x, 0.01 - abs(x) * 0.3, z + lr * 0.4))
        lower.append(V(x, 0.005 - abs(x) * 0.3, z - lr * 1.4))
    g.slot("dark"); g.slab([upper[0], upper[3], upper[6], lower[6], lower[3], lower[0]], UP, 0.02)
    g.slot("accent"); g.tube(upper, [lr * 0.6] * 7, 4, True, True, UP)
    g.use("jaw")
    g.slot("accent"); g.tube(lower, [lr * 0.6] * 7, 4, True, True, UP)


def mouth_mandibles(g, p):
    L, sp = 0.22 * p["length"], 0.05 * p["spread"]
    g.slot("horn")
    for side, bone in ((1, "jaw"), (-1, "jaw2")):
        g.use(bone)
        pts = curve_points(V(side * sp, -0.03, -0.01), V(side * 0.25, 1, 0).normalized(), V(-side * p["curl"], 0, 0), L, 5)
        g.tube(pts, taper(0.035, 0.004, 5), 5, True, True, BACK)


def mouth_trunk(g, p):
    L, T = 0.55 * p["length"], p["thickness"]
    pts = curve_points(V(0, -0.05, 0), UP, V(0, -0.3, -p["droop"]), L, 8)
    rad = taper(0.08 * T, 0.035 * T, 8)
    g.pivots["jaw"] = pts[3]
    g.slot("skin"); g.tube(pts[0:4], rad[0:4], 6, False, False, BACK)
    g.use("jaw")
    g.slot("skin"); g.tube(pts[3:8], rad[3:8], 6, False, True, BACK)


def nose_button(g, p):
    r = 0.045 * p["size"]
    g.slot("dark"); g.ellipsoid(V(0, 0.3 * r, 0), (r * 1.2, r, r * 0.9), None, 6, 4)


F = dict(orient="face")
PARTS = [
    Part("eye_round", "eye", "Round cartoon eye: white ball with a black pupil and optional brow.", ["cute", "mammal", "cartoon"],
         {"size": (0.4, 3.0, 1.0), "pupil": (0.3, 0.9, 0.55), "brow": (0.0, 1.0, 0.0)}, eye_round, cap="look", mirror=True, hint={"u": 0.93, "theta": 35.0}, **F),
    Part("eye_bug", "eye", "Large faceted compound eye, dark and glossy (insects, aliens).", ["insect", "alien", "creepy"],
         {"size": (0.4, 3.0, 1.0), "bulge": (0.4, 1.2, 0.8)}, eye_bug, cap="look", mirror=True, hint={"u": 0.93, "theta": 30.0}, **F),
    Part("eye_slit", "eye", "Reptile eye: colored iris with a vertical slit pupil.", ["reptile", "cat", "menacing"],
         {"size": (0.4, 3.0, 1.0), "slit": (0.1, 0.6, 0.25)}, eye_slit, cap="look", mirror=True, hint={"u": 0.92, "theta": 40.0}, **F),
    Part("eye_stalk", "eye", "Eyeball on a bendy stalk (snails, crabs, aliens).", ["alien", "mollusk", "silly"],
         {"size": (0.4, 3.0, 1.0), "height": (0.1, 0.8, 0.3), "lean": (-0.6, 0.6, 0.2)}, eye_stalk, cap="look", mirror=True, hint={"u": 0.95, "theta": 70.0}, **F),
    Part("eye_cyclops", "eye", "Single large central eye with a heavy brow.", ["monster", "alien"],
         {"size": (0.5, 3.0, 1.0), "pupil": (0.3, 0.9, 0.5)}, eye_cyclops, cap="look", hint={"u": 0.95, "theta": 60.0}, **F),
    Part("eye_bead", "eye", "Tiny black bead eye with a highlight (birds, rodents, small critters).", ["bird", "rodent", "small"],
         {"size": (0.4, 3.0, 1.0)}, eye_bead, cap="look", mirror=True, hint={"u": 0.93, "theta": 30.0}, **F),
    Part("mouth_jaws", "mouth", "Toothy predator jaws (upper and hinged lower jaw).", ["predator", "reptile", "dinosaur", "menacing"],
         {"length": (0.4, 2.5, 1.0), "width": (0.5, 2.0, 1.0), "teeth": (0.0, 1.5, 1.0)}, mouth_jaws, cap="mouth", hint={"u": 0.97, "theta": -20.0},
         bones=[{"name": "jaw", "pivot": (0, -0.05, -0.02), "axis": (1, 0, 0), "angle": -38.0}], **F),
    Part("mouth_beak", "mouth", "Bird beak, optionally hooked (parrots, raptors) or straight.", ["bird", "turtle", "squid"],
         {"length": (0.3, 3.0, 1.0), "width": (0.5, 2.0, 1.0), "hook": (0.0, 1.0, 0.3)}, mouth_beak, cap="mouth", hint={"u": 0.98, "theta": -10.0},
         bones=[{"name": "jaw", "pivot": (0, -0.02, -0.03), "axis": (1, 0, 0), "angle": -25.0}], **F),
    Part("mouth_snout", "mouth", "Blunt mammal muzzle with nostrils and a small lower jaw (bovines, pigs, dogs, bears).", ["mammal", "bovine", "pig", "dog"],
         {"length": (0.3, 2.5, 1.0), "width": (0.5, 2.2, 1.0), "nostrils": (0.0, 2.0, 1.0)}, mouth_snout, cap="mouth", hint={"u": 0.97, "theta": -15.0},
         bones=[{"name": "jaw", "pivot": (0, -0.02, -0.06), "axis": (1, 0, 0), "angle": -28.0}], **F),
    Part("mouth_smile", "mouth", "Flat friendly mouth with curved lips (cartoon, humanoid, frog).", ["cartoon", "humanoid", "frog", "friendly"],
         {"width": (0.4, 3.0, 1.0), "curve": (-1.0, 1.0, 0.5), "lips": (0.3, 2.0, 1.0)}, mouth_smile, cap="mouth", hint={"u": 0.97, "theta": -35.0},
         bones=[{"name": "jaw", "pivot": (0, -0.03, -0.02), "axis": (1, 0, 0), "angle": -22.0}], **F),
    Part("mouth_mandibles", "mouth", "Pair of curved insect mandibles that open sideways.", ["insect", "arachnid", "alien", "menacing"],
         {"length": (0.4, 2.5, 1.0), "curl": (0.0, 1.5, 0.7), "spread": (0.5, 2.0, 1.0)}, mouth_mandibles, cap="mouth", hint={"u": 0.98, "theta": -20.0},
         bones=[{"name": "jaw", "pivot": (0.05, 0.0, -0.01), "axis": (0, 0, 1), "angle": 25.0},
                {"name": "jaw2", "pivot": (-0.05, 0.0, -0.01), "axis": (0, 0, 1), "angle": -25.0}], **F),
    Part("mouth_trunk", "mouth", "Long flexible trunk or proboscis that curls up when 'opened'.", ["elephant", "tapir", "alien"],
         {"length": (0.3, 3.0, 1.0), "thickness": (0.4, 2.0, 1.0), "droop": (0.0, 1.5, 1.0)}, mouth_trunk, cap="mouth", hint={"u": 0.97, "theta": 0.0},
         bones=[{"name": "jaw", "pivot": (0, 0.25, -0.12), "axis": (1, 0, 0), "angle": 50.0}], **F),
    Part("nose_button", "nose", "Small round nose (cartoon mammals).", ["cute", "mammal", "cartoon"],
         {"size": (0.4, 3.0, 1.0)}, nose_button, hint={"u": 0.99, "theta": 20.0}, **F),
]
