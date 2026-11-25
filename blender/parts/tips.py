"""Limb tips. Origin at the limb's end joint.
Feet: +Y up, +Z forward, sole below the origin. Hands: +Y along the arm, +Z forward."""
import math
from kit import V, UP, BACK, RIGHT, rot, curve_points, taper
from parts import Part


def foot_paw(g, p):
    s = p["size"]
    g.slot("skin"); g.ellipsoid(V(0, -0.055 * s, 0.03 * s), (0.09 * s, 0.05 * s, 0.11 * s), None, 7, 4)
    t = max(p["toes"], 0.05)
    g.slot("detail")
    for i in range(3):
        g.ellipsoid(V((i - 1) * 0.055 * s, -0.07 * s, 0.13 * s), (0.032 * s * t,) * 3, None, 5, 3)


def foot_hoof(g, p):
    s = p["size"]
    gap = 0.012 * s * p["split"]
    g.slot("dark")
    for side in (-1, 1):
        c = V(side * (0.035 * s + gap), 0, 0.02 * s)
        g.tube([c, c + V(0, -0.08 * s, 0.01 * s), c + V(0, -0.13 * s, 0.03 * s)], [0.04 * s, 0.05 * s, 0.055 * s], 6, True, True, BACK, (0.8, 1.1))


def foot_claw(g, p):
    s, sp = p["size"], p["spread"]
    tal = max(p["talons"], 0.05)
    for i in range(4):
        a = (i - 1) * 0.45 * sp if i < 3 else math.pi
        d = V(math.sin(a), 0, math.cos(a))
        L = (0.16 if i < 3 else 0.08) * s
        base = V(0, -0.02 * s, 0)
        pts = [base, base + d * L * 0.5 + V(0, -0.015 * s, 0), base + d * L + V(0, -0.02 * s, 0)]
        g.slot("skin"); g.tube(pts, [0.025 * s, 0.02 * s, 0.015 * s], 4, True, False, UP)
        g.slot("claw"); g.cone(pts[2], pts[2] + d * 0.05 * s * tal + V(0, -0.02 * s, 0), 0.016 * s, 4, UP)


def foot_pad(g, p):
    s = p["size"]
    g.slot("skin"); g.tube([V(0, 0.02 * s, 0), V(0, -0.14 * s, 0)], [0.1 * s, 0.13 * s], 8, False, True, BACK)
    n = max(p["nails"], 0.05)
    g.slot("detail")
    for i in range(3):
        a = (i - 1) * 0.5
        g.ellipsoid(V(math.sin(a) * 0.125 * s, -0.11 * s, math.cos(a) * 0.125 * s), (0.03 * s * n, 0.03 * s * n, 0.02 * s * n), rot(UP, a), 5, 3)


def foot_spike(g, p):
    s = p["size"]
    g.slot("dark"); g.cone(V(0, 0.02 * s, 0), V(0, -0.12 * s, 0), 0.035 * s, 5, BACK)


def foot_webbed(g, p):
    s = p["size"]
    L = 0.22 * s * p["length"]
    g.slot("accent")
    g.slab([V(-0.03 * s, -0.025 * s, 0), V(0.03 * s, -0.025 * s, 0), V(0.1 * s, -0.03 * s, L), V(0, -0.03 * s, L * 0.85), V(-0.1 * s, -0.03 * s, L)], UP, 0.02 * s)
    g.slot("skin"); g.ellipsoid(V(0, -0.01 * s, 0), (0.04 * s,) * 3, None, 5, 3)


def hand_basic(g, p):
    s = p["size"]
    fl, c = 0.08 * s * p["fingers"], p["curl"]
    g.slot("skin"); g.ellipsoid(V(0, 0.05 * s, 0), (0.06 * s, 0.06 * s, 0.035 * s), None, 6, 4)
    for i in range(3):
        b = V((i - 1) * 0.035 * s, 0.1 * s, 0)
        g.tube([b, b + V(0, fl * 0.6, c * fl * 0.2), b + V(0, fl * (1 - 0.3 * c), c * fl * 0.6)], [0.017 * s, 0.015 * s, 0.012 * s], 4, False, True, BACK)
    tb = V(0.05 * s, 0.05 * s, 0.02 * s)
    g.tube([tb, tb + V(0.04 * s, 0.03 * s, 0.03 * s)], [0.018 * s, 0.013 * s], 4, False, True, BACK)


def hand_claw(g, p):
    s = p["size"]
    cl = 0.12 * s * p["claw"]
    g.slot("skin"); g.ellipsoid(V(0, 0.04 * s, 0), (0.055 * s, 0.05 * s, 0.035 * s), None, 6, 4)
    g.slot("claw")
    for i in range(3):
        g.tube(curve_points(V((i - 1) * 0.035 * s, 0.07 * s, 0.01 * s), UP, V(0, -0.3, 0.9), cl, 4), taper(0.018 * s, 0.002, 4), 4, False, True, BACK)


def hand_pincer(g, p):
    s, bk = p["size"], p["bulk"]
    g.pivots["jaw"] = V(0.03 * s, 0.14 * s, 0)
    g.slot("accent")
    g.ellipsoid(V(0, 0.08 * s, 0), (0.07 * bk * s, 0.1 * s, 0.05 * bk * s), None, 7, 4)
    g.tube(curve_points(V(-0.02 * s, 0.15 * s, 0), UP, V(0.3, 0, 0), 0.14 * s, 4), taper(0.03 * s * bk, 0.004, 4), 5, False, True, BACK)
    g.use("jaw")
    g.slot("accent")
    g.tube(curve_points(V(0.035 * s, 0.14 * s, 0), UP, V(-0.35, 0, 0), 0.12 * s, 4), taper(0.024 * s * bk, 0.004, 4), 5, True, True, BACK)


def hand_tentacle(g, p):
    s, c = p["size"], p["curl"]
    pts = []
    for i in range(7):
        a = (i / 6) * c * math.pi
        k = max(c * math.pi, 0.01)
        pts.append(V(0, math.sin(a) / k, (1 - math.cos(a)) / k) * 0.3 * s)
    g.slot("skin"); g.tube(pts, taper(0.035 * s, 0.006, 7), 5, False, True, RIGHT)


def hand_mitt(g, p):
    s = p["size"]
    g.slot("skin")
    g.ellipsoid(V(0, 0.08 * s, 0), (0.07 * s, 0.09 * s, 0.045 * s), None, 7, 4)
    g.ellipsoid(V(0.06 * s, 0.06 * s, 0.02 * s), (0.025 * s, 0.04 * s, 0.025 * s), rot(BACK, -0.6), 5, 3)


T = dict(attach="tip")
PARTS = [
    Part("foot_paw", "foot", "Padded paw with three toe beads (cats, dogs, bears).", ["mammal", "cat", "dog", "bear", "cute"],
         {"size": (0.4, 3.0, 1.0), "toes": (0.0, 1.5, 1.0)}, foot_paw, cap="foot", **T),
    Part("foot_hoof", "foot", "Cloven hoof (bulls, goats, deer, minotaurs).", ["bovine", "goat", "deer", "minotaur", "horse"],
         {"size": (0.4, 3.0, 1.0), "split": (0.0, 1.0, 0.6)}, foot_hoof, cap="foot", **T),
    Part("foot_claw", "foot", "Bird / raptor foot: three forward toes and one back toe with talons.", ["bird", "dinosaur", "raptor", "dragon"],
         {"size": (0.4, 3.0, 1.0), "spread": (0.3, 1.5, 1.0), "talons": (0.0, 2.0, 1.0)}, foot_claw, cap="foot", **T),
    Part("foot_pad", "foot", "Thick round column foot with toenails (elephants, sauropods, golems).", ["elephant", "sauropod", "heavy"],
         {"size": (0.4, 3.0, 1.0), "nails": (0.0, 1.5, 1.0)}, foot_pad, cap="foot", **T),
    Part("foot_spike", "foot", "Pointed leg tip (insects, spiders, crabs).", ["insect", "spider", "crab", "arthropod"],
         {"size": (0.4, 3.0, 1.0)}, foot_spike, cap="foot", **T),
    Part("foot_webbed", "foot", "Flat webbed foot or flipper (ducks, frogs, seals).", ["duck", "frog", "aquatic"],
         {"size": (0.4, 3.0, 1.0), "length": (0.5, 2.0, 1.0)}, foot_webbed, cap="foot", **T),
    Part("hand_basic", "hand", "Four-fingered hand with palm and thumb (humanoids, apes, minotaurs).", ["humanoid", "ape", "minotaur", "cartoon"],
         {"size": (0.4, 3.0, 1.0), "fingers": (0.5, 1.8, 1.0), "curl": (0.0, 1.0, 0.4)}, hand_basic, cap="hand", **T),
    Part("hand_claw", "hand", "Clawed hand with three long curved talons (raptors, monsters, sloths).", ["monster", "raptor", "dragon", "menacing"],
         {"size": (0.4, 3.0, 1.0), "claw": (0.4, 2.5, 1.0)}, hand_claw, cap="hand", **T),
    Part("hand_pincer", "hand", "Crab / scorpion pincer with a hinged finger.", ["crab", "scorpion", "lobster", "arthropod"],
         {"size": (0.4, 3.0, 1.0), "bulk": (0.5, 2.0, 1.0)}, hand_pincer, cap="grasp",
         bones=[{"name": "jaw", "pivot": (0.03, 0.14, 0), "axis": (0, 0, 1), "angle": -30.0}], **T),
    Part("hand_tentacle", "hand", "Curling tentacle tip in place of a hand (octopus, aliens).", ["octopus", "alien", "aquatic", "creepy"],
         {"size": (0.4, 3.0, 1.0), "curl": (0.05, 1.5, 0.8)}, hand_tentacle, cap="hand", **T),
    Part("hand_mitt", "hand", "Simple rounded mitten hand with a thumb (cartoon, toy-like).", ["cartoon", "toy", "cute"],
         {"size": (0.4, 3.0, 1.0)}, hand_mitt, cap="hand", **T),
]
