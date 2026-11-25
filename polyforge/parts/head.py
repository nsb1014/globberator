"""Horns and ears. Surface frame: +Y out of the body, +Z toward the head, +X lateral."""
import math
from ..kit import V, UP, BACK, RIGHT, rot, curve_points, taper, lerp
from . import Part


def _horn_radii(n, r0, tip=0.004, swell=0.06):
    """Thick root easing into a fine rounded tip, with a slight swell near the base."""
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append(max(tip, r0 * (1 - t) ** 0.85 * (1 + swell * math.sin(math.pi * min(t * 2.5, 1.0)))))
    return out


def horn_spike(g, p):
    L = 0.32 * p["length"]
    d = V(p["splay"] * 0.5, 1, 0).normalized()
    g.slot("horn")
    g.loft(curve_points(V(0, -0.04, 0), d, V(0, 0, p["curve"] * 0.6), L, 7), _horn_radii(7, 0.055 * p["thickness"]), sides=22, up=BACK)


def horn_curl(g, p):
    R, turns, n = 0.12 * p["size"], p["turns"], 16
    pts = []
    for i in range(n):
        t = i / (n - 1)
        a = t * turns * 2 * math.pi
        r = R * (1.0 - 0.45 * t)
        pts.append(V(t * p["drift"] * 0.25 * p["size"], r * math.sin(a) - 0.03, -R + r * math.cos(a)))
    g.slot("horn")
    g.loft(pts, _horn_radii(n, 0.058 * p["thickness"] * p["size"], 0.01, 0.0), sides=22, up=RIGHT, exponent=0.85)


def horn_bull(g, p):
    """Profile of the original bull horn: out from the skull, then up and slightly forward."""
    sec = [(.00, .000, .00, .170), (.16, .005, .015, .166), (.36, .023, .00, .144), (.54, .019, .05, .125),
           (.67, -.016, .17, .098), (.705, -.06, .315, .076), (.664, -.115, .44, .043), (.558, -.163, .54, .006)]
    k = 0.62 * p["length"]
    T = p["thickness"]
    pts, rad = [], []
    for x, fwd, z, w in sec:
        # old frame: x out, -y forward, z up  ->  surface frame: +Y out of the skull, +X lateral, +Z forward
        out = x * k
        rise = z * k * (p["rise"] / 0.8)
        fw = -fwd * k + p["forward"] * 0.25 * k * (z / 0.54)
        pts.append(V(out * 0.95, rise * 0.9 + out * 0.15 - 0.03, fw))
        rad.append(max(0.004, w * 0.5 * T * (0.85 + 0.15 * p["length"])))
    g.slot("horn")
    g.loft(pts, rad, sides=24, up=BACK)


def horn_antler(g, p):
    S = p["size"]
    L = 0.5 * S
    beam = curve_points(V(0, -0.03, 0), V(p["spread"] * 0.5, 1, -0.4).normalized(), V(0.1, -0.1, 0.35), L, 7)
    r = 0.032 * S
    g.slot("horn")
    g.loft(beam, taper(r, r * 0.35, 7), sides=16, up=BACK)
    for i in range(3):
        base = beam[1 + i * 2]
        tine = curve_points(base, V(0.1, 0.6, 1).normalized(), V(0, 0.45, 0), L * 0.4 * (1 - 0.15 * i) * p["tines"], 4)
        g.loft(tine, [r * 0.75, r * 0.55, r * 0.35, r * 0.12], sides=12, up=RIGHT)


def horn_rhino(g, p):
    L = 0.3 * p["length"]
    g.slot("horn")
    g.loft(curve_points(V(0, -0.04, 0), V(0, 1, 0.2).normalized(), V(0, 0, p["curve"] * 0.6), L, 7), _horn_radii(7, 0.085 * p["thickness"], 0.006, 0.1), sides=22, up=BACK, exponent=0.9)


def horn_tusk(g, p):
    L = 0.3 * p["length"]
    g.slot("teeth")
    g.loft(curve_points(V(0, -0.03, 0), V(0.2, 1.0, -0.5).normalized(), V(0, 0, p["curve"]), L, 7), _horn_radii(7, 0.036 * p["thickness"], 0.005, 0.0), sides=18, up=RIGHT)


def _ear(g, outline, inner_scale, b, thick, cup, slot_inner="detail"):
    g.setup(finish="subsurf")
    g.slot("base")
    g.leaf([b @ q for q in outline], b @ BACK, thick, cup)


def ear_pointy(g, p):
    s = p["size"]
    w, h = 0.075 * s * p["width"], 0.21 * s
    b = rot(RIGHT, -p["tilt"] * 0.6)
    outline = [V(-w, -0.03, 0), V(-w * 0.9, h * 0.35, 0), V(-w * 0.45, h * 0.78, 0), V(0, h, 0), V(w * 0.45, h * 0.78, 0), V(w * 0.9, h * 0.35, 0), V(w, -0.03, 0), V(0, -0.05, 0)]
    _ear(g, outline, 0.6, b, 0.035 * s, 0.6)


def ear_round(g, p):
    r = 0.09 * p["size"]
    b = rot(RIGHT, -p["tilt"] * 0.6)
    outline = [V(math.cos(2 * math.pi * i / 10) * r, r * 0.75 + math.sin(2 * math.pi * i / 10) * r, 0) for i in range(10)]
    _ear(g, outline, 0.6, b, r * 0.35, 0.55)


def ear_long(g, p):
    s = p["size"]
    h, w = 0.35 * s * p["length"], 0.065 * s
    b = rot(RIGHT, -p["tilt"] * 0.6)
    outline = [V(math.cos(2 * math.pi * i / 12) * w * (1 - 0.25 * max(0, math.sin(2 * math.pi * i / 12))), h * 0.5 + math.sin(2 * math.pi * i / 12) * h * 0.55, 0) for i in range(12)]
    _ear(g, outline, 0.6, b, 0.035 * s, 0.6)


def ear_fan(g, p):
    # Lies flat against the side of the head; local +X runs down the head side.
    r, d = 0.22 * p["size"], p["droop"]
    outline = [V(math.cos(2 * math.pi * i / 12) * r * (1 + 0.08 * math.sin(6 * math.pi * i / 12)) + d * r * 0.7, 0.03, math.sin(2 * math.pi * i / 12) * r * 0.85 - r * 0.55) for i in range(12)]
    g.setup(finish="subsurf")
    g.slot("base")
    g.leaf(outline, UP, 0.04, 0.35)


PARTS = [
    Part("horn_spike", "horn", "Straight or gently curved conical horn.", ["goat", "demon", "dinosaur"],
         {"length": (0.2, 4.0, 1.0), "thickness": (0.4, 2.5, 1.0), "curve": (-1.0, 1.0, -0.3), "splay": (-1.0, 1.0, 0.2)}, horn_spike, mirror=True, hint={"u": 0.9, "theta": 70.0}),
    Part("horn_curl", "horn", "Ram horn spiraling back, down and forward around the ear.", ["ram", "sheep", "demon"],
         {"size": (0.4, 3.0, 1.0), "turns": (0.4, 1.3, 0.85), "thickness": (0.5, 2.0, 1.0), "drift": (0.0, 1.0, 0.4)}, horn_curl, mirror=True, hint={"u": 0.88, "theta": 60.0}),
    Part("horn_bull", "horn", "Bull / buffalo horn sweeping outward then curving up and forward.", ["bull", "bovine", "minotaur", "buffalo"],
         {"length": (0.3, 3.0, 1.0), "thickness": (0.5, 2.0, 1.0), "rise": (-0.5, 1.5, 0.8), "forward": (-1.0, 1.0, 0.4)}, horn_bull, mirror=True, hint={"u": 0.9, "theta": 40.0}),
    Part("horn_antler", "horn", "Branching deer antler with forward tines.", ["deer", "moose", "elk", "forest"],
         {"size": (0.4, 3.0, 1.0), "tines": (0.2, 1.6, 1.0), "spread": (0.0, 1.0, 0.5)}, horn_antler, mirror=True, hint={"u": 0.9, "theta": 70.0}),
    Part("horn_rhino", "horn", "Thick single nose horn curving back (rhino, triceratops nose).", ["rhino", "dinosaur", "armored"],
         {"length": (0.3, 3.0, 1.0), "thickness": (0.5, 2.5, 1.0), "curve": (-1.0, 1.0, -0.5)}, horn_rhino, hint={"u": 0.97, "theta": 70.0}),
    Part("horn_tusk", "horn", "Ivory tusk curving out and up from the mouth (boar, elephant; walrus when curve is negative).", ["boar", "elephant", "walrus", "orc"],
         {"length": (0.3, 3.0, 1.0), "thickness": (0.5, 2.0, 1.0), "curve": (-1.0, 1.0, 0.7)}, horn_tusk, orient="face", mirror=True, hint={"u": 0.96, "theta": -40.0}),
    Part("ear_pointy", "ear", "Pointed cupped ear (cats, foxes, wolves, goblins, bovines when tilted).", ["cat", "fox", "wolf", "goblin", "bovine"],
         {"size": (0.3, 3.0, 1.0), "width": (0.4, 2.0, 1.0), "tilt": (-1.0, 1.0, 0.2)}, ear_pointy, cap="flop", mirror=True, hint={"u": 0.86, "theta": 65.0}),
    Part("ear_round", "ear", "Round cupped ear (bears, mice, monkeys).", ["bear", "mouse", "monkey", "cute"],
         {"size": (0.3, 3.0, 1.0), "tilt": (-1.0, 1.0, 0.0)}, ear_round, cap="flop", mirror=True, hint={"u": 0.86, "theta": 60.0}),
    Part("ear_long", "ear", "Long upright cupped ear (rabbits, donkeys, jackalopes).", ["rabbit", "donkey", "cute"],
         {"size": (0.3, 3.0, 1.0), "length": (0.5, 2.5, 1.0), "tilt": (-1.0, 1.0, 0.3)}, ear_long, cap="flop", mirror=True, hint={"u": 0.85, "theta": 75.0}),
    Part("ear_fan", "ear", "Large flat fan ear on the side of the head (elephants).", ["elephant", "big"],
         {"size": (0.4, 3.0, 1.0), "droop": (0.0, 1.0, 0.5)}, ear_fan, cap="flop", mirror=True, hint={"u": 0.88, "theta": 20.0}),
]
