"""Limb tips. Origin at the limb's end joint.
Feet: +Y up, +Z forward, sole below the origin. Hands: +Y along the arm, +Z forward."""
import math
from kit import V, UP, BACK, RIGHT, rot, curve_points, taper, lerp
from parts import Part


def foot_paw(g, p):
    s = p["size"]
    t = max(p["toes"], 0.1)
    g.setup(voxel=0.003 * s)
    g.slot("skin")
    g.loft([V(0, 0.03 * s, -0.01 * s), V(0, -0.03 * s, 0.01 * s), V(0, -0.07 * s, 0.04 * s)], [(0.06 * s, 0.06 * s), (0.075 * s, 0.08 * s), (0.085 * s, 0.09 * s)], sides=22, up=BACK)
    g.oval(V(0, -0.068 * s, 0.045 * s), (0.092 * s, 0.045 * s, 0.1 * s))
    for i in range(4):
        x = (i - 1.5) * 0.045 * s
        z = 0.12 * s - abs(i - 1.5) * 0.015 * s
        g.oval(V(x, -0.075 * s, z), (0.03 * s * t, 0.034 * s * t, 0.036 * s * t), segs=18, rings=10)


def foot_hoof(g, p):
    """Cloven hoof from the original bull: each toe widens at the ground, the cleft stays open."""
    s = p["size"]
    k = 0.385 * s
    gap = 1.0 + 0.35 * p["split"]
    data = [(.000, .110, -.10, .104, .260), (.058, .111, -.109, .108, .268), (.145, .103, -.082, .108, .237),
            (.23, .086, -.038, .095, .192), (.30, .068, -.004, .075, .144), (.336, .050, .019, .05, .09)]
    sole = -0.13 * s
    g.setup(voxel=0.0028 * s)
    g.slot("dark")
    for j in (-1, 1):
        pts = [V(j * x * 1.22 * gap * k * 0.9, sole + z * k, -y * k + 0.01 * s) for z, x, y, w, d in data]
        rad = [(w * 1.23 * k * 0.95, d * 1.1 * k * 0.95) for z, x, y, w, d in data]
        g.loft(pts, rad, sides=24, up=BACK, exponent=0.72, density=4)
    g.slot("skin")
    g.loft([V(0, 0.03 * s, 0), V(0, -0.02 * s, 0.005 * s), V(0, sole + 0.12 * k, 0.012 * s)], [(0.055 * s, 0.055 * s), (0.065 * s, 0.062 * s), (0.08 * s, 0.07 * s)], sides=22, up=BACK)


def foot_claw(g, p):
    s, sp = p["size"], p["spread"]
    tal = max(p["talons"], 0.1)
    g.setup(voxel=0.0025 * s)
    g.slot("skin")
    g.oval(V(0, -0.02 * s, 0.0), (0.04 * s, 0.03 * s, 0.045 * s), segs=18, rings=10)
    claws = []
    for i in range(4):
        a = (i - 1) * 0.45 * sp if i < 3 else math.pi
        d = V(math.sin(a), 0, math.cos(a))
        L = (0.16 if i < 3 else 0.075) * s
        base = V(0, -0.025 * s, 0)
        pts = [base, base + d * L * 0.45 + V(0, -0.012 * s, 0), base + d * L * 0.8 + V(0, -0.02 * s, 0), base + d * L + V(0, -0.022 * s, 0)]
        g.loft(pts, [0.026 * s, 0.021 * s, 0.019 * s, 0.016 * s], sides=14, up=UP)
        claws.append((pts[-1], d))
    g.slot("claw")
    for tip, d in claws:
        g.loft(curve_points(tip - d * 0.005 * s, d, V(0, -0.5, 0), 0.055 * s * tal, 4), [0.015 * s, 0.012 * s, 0.007 * s, 0.002 * s], sides=12, up=UP)


def foot_pad(g, p):
    s = p["size"]
    n = max(p["nails"], 0.1)
    g.slot("skin")
    g.loft([V(0, 0.03 * s, 0), V(0, -0.06 * s, 0), V(0, -0.12 * s, 0), V(0, -0.14 * s, 0)], [0.1 * s, 0.112 * s, 0.128 * s, 0.12 * s], sides=26, up=BACK, exponent=0.9)
    g.slot("detail")
    for i in range(3):
        a = (i - 1) * 0.55
        g.oval(V(math.sin(a) * 0.118 * s, -0.115 * s, math.cos(a) * 0.118 * s), (0.034 * s * n, 0.03 * s * n, 0.02 * s * n), rot(UP, a), segs=16, rings=10)


def foot_spike(g, p):
    s = p["size"]
    g.slot("dark")
    g.loft([V(0, 0.03 * s, 0), V(0, -0.03 * s, 0.003 * s), V(0, -0.09 * s, 0.006 * s), V(0, -0.12 * s, 0.004 * s)], [0.036 * s, 0.032 * s, 0.018 * s, 0.003 * s], sides=16, up=BACK)


def foot_webbed(g, p):
    s = p["size"]
    L = 0.22 * s * p["length"]
    g.setup(finish="subsurf")
    g.slot("accent")
    outline = [V(-0.03 * s, -0.03 * s, -0.01 * s), V(0.03 * s, -0.03 * s, -0.01 * s), V(0.075 * s, -0.035 * s, L * 0.6), V(0.105 * s, -0.035 * s, L),
               V(0.035 * s, -0.035 * s, L * 0.82), V(0, -0.035 * s, L * 0.95), V(-0.035 * s, -0.035 * s, L * 0.82), V(-0.105 * s, -0.035 * s, L), V(-0.075 * s, -0.035 * s, L * 0.6)]
    g.slab(outline, UP, 0.025 * s)
    g.use("self")
    g.slot("skin")
    g.slab([V(0.04 * s * math.cos(2 * math.pi * i / 8), 0.0, 0.04 * s * math.sin(2 * math.pi * i / 8)) for i in range(8)], UP, 0.05 * s)


def hand_basic(g, p):
    """Palm, four fingers and a thumb sculpted as one mass (after the original minotaur hand)."""
    s = p["size"]
    fl, c = 0.085 * s * p["fingers"], p["curl"]
    g.setup(voxel=0.0028 * s)
    g.slot("skin")
    g.oval(V(0, 0.06 * s, 0), (0.06 * s, 0.075 * s, 0.04 * s))
    for j, drop in enumerate([0.9, 1.0, 0.95, 0.75]):
        x = (j - 1.5) * 0.03 * s
        L = fl * drop
        b = V(x, 0.11 * s, 0.005 * s)
        g.loft([b, b + V(0, L * 0.45, c * L * 0.12), b + V(0, L * (0.85 - 0.25 * c), c * L * 0.45), b + V(0, L * (1.0 - 0.45 * c), c * L * 0.8)],
               [0.017 * s, 0.016 * s, 0.014 * s, 0.011 * s], sides=14, up=BACK)
    tb = V(0.05 * s, 0.05 * s, 0.022 * s)
    g.loft([tb, tb + V(0.022 * s, 0.025 * s, 0.022 * s), tb + V(0.03 * s, 0.05 * s, 0.035 * s)], [0.02 * s, 0.017 * s, 0.013 * s], sides=14, up=BACK)


def hand_claw(g, p):
    s = p["size"]
    cl = 0.12 * s * p["claw"]
    g.setup(voxel=0.0028 * s)
    g.slot("skin")
    g.oval(V(0, 0.045 * s, 0), (0.055 * s, 0.06 * s, 0.038 * s))
    tips = []
    for i in range(3):
        b = V((i - 1) * 0.033 * s, 0.09 * s, 0.008 * s)
        g.loft([b, b + V(0, 0.03 * s, 0.006 * s)], [0.018 * s, 0.016 * s], sides=14, up=BACK)
        tips.append(b + V(0, 0.03 * s, 0.006 * s))
    g.slot("claw")
    for t in tips:
        g.loft(curve_points(t, UP, V(0, -0.3, 0.9), cl, 5), taper(0.016 * s, 0.002, 5), sides=12, up=BACK)


def hand_pincer(g, p):
    s, bk = p["size"], p["bulk"]
    g.pivots["jaw"] = V(0.03 * s, 0.15 * s, 0)
    g.setup(voxel=0.003 * s)
    g.slot("accent")
    g.loft([V(0, 0.0, 0), V(0, 0.06 * s, 0), V(0, 0.13 * s, 0)], [(0.05 * bk * s, 0.04 * bk * s), (0.075 * bk * s, 0.055 * bk * s), (0.06 * bk * s, 0.045 * bk * s)], sides=24, up=BACK)
    g.loft(curve_points(V(-0.02 * s, 0.13 * s, 0), UP, V(0.35, 0, 0), 0.15 * s, 5), [0.032 * s * bk, 0.03 * s * bk, 0.022 * s * bk, 0.012 * s * bk, 0.003 * s], sides=18, up=BACK)
    g.use("jaw")
    g.setup(voxel=0.003 * s)
    g.slot("accent")
    g.loft(curve_points(V(0.035 * s, 0.14 * s, 0), UP, V(-0.4, 0, 0), 0.13 * s, 5), [0.026 * s * bk, 0.024 * s * bk, 0.018 * s * bk, 0.01 * s * bk, 0.003 * s], sides=18, up=BACK)


def hand_tentacle(g, p):
    s, c = p["size"], p["curl"]
    pts = []
    for i in range(9):
        a = (i / 8) * c * math.pi
        k = max(c * math.pi, 0.01)
        pts.append(V(0, math.sin(a) / k, (1 - math.cos(a)) / k) * 0.3 * s)
    g.slot("skin")
    g.loft(pts, taper(0.036 * s, 0.006, 9), sides=18, up=RIGHT)


def hand_mitt(g, p):
    s = p["size"]
    g.setup(voxel=0.003 * s)
    g.slot("skin")
    g.oval(V(0, 0.085 * s, 0), (0.07 * s, 0.095 * s, 0.048 * s))
    g.loft([V(0.04 * s, 0.05 * s, 0.015 * s), V(0.07 * s, 0.075 * s, 0.025 * s), V(0.075 * s, 0.1 * s, 0.03 * s)], [0.026 * s, 0.022 * s, 0.018 * s], sides=14, up=BACK)


T = dict(attach="tip")
PARTS = [
    Part("foot_paw", "foot", "Padded paw with four toe pads (cats, dogs, bears).", ["mammal", "cat", "dog", "bear", "cute"],
         {"size": (0.4, 3.0, 1.0), "toes": (0.0, 1.5, 1.0)}, foot_paw, cap="foot", **T),
    Part("foot_hoof", "foot", "Rounded cloven hoof (bulls, goats, deer, minotaurs).", ["bovine", "goat", "deer", "minotaur", "horse"],
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
         bones=[{"name": "jaw", "pivot": (0.03, 0.15, 0), "axis": (0, 0, 1), "angle": -30.0}], **T),
    Part("hand_tentacle", "hand", "Curling tentacle tip in place of a hand (octopus, aliens).", ["octopus", "alien", "aquatic", "creepy"],
         {"size": (0.4, 3.0, 1.0), "curl": (0.05, 1.5, 0.8)}, hand_tentacle, cap="hand", **T),
    Part("hand_mitt", "hand", "Simple rounded mitten hand with a thumb (cartoon, toy-like).", ["cartoon", "toy", "cute"],
         {"size": (0.4, 3.0, 1.0)}, hand_mitt, cap="hand", **T),
]
