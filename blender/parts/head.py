"""Horns and ears. Surface frame: +Y out of the body, +Z toward the head, +X lateral."""
import math
from kit import V, UP, BACK, RIGHT, rot, curve_points, taper
from parts import Part


def horn_spike(g, p):
    L = 0.32 * p["length"]
    d = V(p["splay"] * 0.5, 1, 0).normalized()
    g.slot("horn")
    g.tube(curve_points(V(0, -0.03, 0), d, V(0, 0, p["curve"] * 0.6), L, 5), taper(0.055 * p["thickness"], 0.004, 5, 0.9), 6, True, True, BACK)


def horn_curl(g, p):
    R, turns, n = 0.12 * p["size"], p["turns"], 14
    pts = []
    for i in range(n):
        t = i / (n - 1)
        a = t * turns * 2 * math.pi
        r = R * (1.0 - 0.45 * t)
        pts.append(V(t * p["drift"] * 0.25 * p["size"], r * math.sin(a) - 0.02, -R + r * math.cos(a)))
    g.slot("horn")
    g.tube(pts, taper(0.055 * p["thickness"] * p["size"], 0.008, n), 6, True, True, RIGHT)


def horn_bull(g, p):
    L = 0.45 * p["length"]
    d = rot(BACK, -0.9) @ V(0.3, 1.0, 0.0).normalized()
    g.slot("horn")
    g.tube(curve_points(V(0, -0.03, 0), d, V(-0.2, p["rise"], p["forward"]), L, 7), taper(0.065 * p["thickness"], 0.006, 7, 0.8), 6, True, True, BACK)


def horn_antler(g, p):
    S = p["size"]
    L = 0.5 * S
    beam = curve_points(V(0, -0.02, 0), V(p["spread"] * 0.5, 1, -0.4).normalized(), V(0.1, -0.1, 0.35), L, 6)
    r = 0.03 * S
    g.slot("horn")
    g.tube(beam, taper(r, r * 0.3, 6), 5, True, True, BACK)
    for i in range(3):
        base = beam[1 + int(i * 4 / 3)]
        tine = curve_points(base, V(0.1, 0.6, 1).normalized(), V(0, 0.4, 0), L * 0.4 * (1 - 0.15 * i) * p["tines"], 3)
        g.tube(tine, taper(r * 0.7, r * 0.2, 3), 4, False, True, RIGHT)


def horn_rhino(g, p):
    L = 0.3 * p["length"]
    g.slot("horn")
    g.tube(curve_points(V(0, -0.03, 0), V(0, 1, 0.2).normalized(), V(0, 0, p["curve"] * 0.6), L, 5), taper(0.085 * p["thickness"], 0.005, 5, 0.8), 6, True, True, BACK)


def horn_tusk(g, p):
    L = 0.3 * p["length"]
    g.slot("teeth")
    g.tube(curve_points(V(0, -0.02, 0), V(0.2, 1.0, -0.5).normalized(), V(0, 0, p["curve"]), L, 6), taper(0.035 * p["thickness"], 0.004, 6, 0.9), 6, True, True, RIGHT)


def ear_pointy(g, p):
    s = p["size"]
    w, h = 0.07 * s * p["width"], 0.2 * s
    b = rot(RIGHT, -p["tilt"] * 0.6)
    g.slot("base")
    g.slab([b @ V(-w, -0.02, 0), b @ V(w, -0.02, 0), b @ V(0, h, 0)], b @ BACK, 0.03 * s)
    g.slot("detail")
    g.slab([b @ V(-w * 0.55, 0.01, 0.016 * s), b @ V(w * 0.55, 0.01, 0.016 * s), b @ V(0, h * 0.7, 0.016 * s)], b @ BACK, 0.01 * s)


def ear_round(g, p):
    r = 0.09 * p["size"]
    b = rot(RIGHT, -p["tilt"] * 0.6)
    outer = [b @ V(math.cos(2 * math.pi * i / 8) * r, r * 0.8 + math.sin(2 * math.pi * i / 8) * r, 0) for i in range(8)]
    inner = [b @ V(math.cos(2 * math.pi * i / 8) * r * 0.6, r * 0.8 + math.sin(2 * math.pi * i / 8) * r * 0.6, 0.02 * p["size"]) for i in range(8)]
    g.slot("base"); g.slab(outer, b @ BACK, r * 0.35)
    g.slot("detail"); g.slab(inner, b @ BACK, r * 0.1)


def ear_long(g, p):
    s = p["size"]
    h, w = 0.35 * s * p["length"], 0.06 * s
    b = rot(RIGHT, -p["tilt"] * 0.6)
    outer = [b @ V(math.cos(2 * math.pi * i / 10) * w, h * 0.5 + math.sin(2 * math.pi * i / 10) * h * 0.55, 0) for i in range(10)]
    inner = [b @ V(math.cos(2 * math.pi * i / 10) * w * 0.55, h * 0.5 + math.sin(2 * math.pi * i / 10) * h * 0.42, 0.015 * s) for i in range(10)]
    g.slot("base"); g.slab(outer, b @ BACK, 0.03 * s)
    g.slot("detail"); g.slab(inner, b @ BACK, 0.01 * s)


def ear_fan(g, p):
    # Lies flat against the side of the head; local +X runs down the head side.
    r, d = 0.22 * p["size"], p["droop"]
    outline = [V(math.cos(2 * math.pi * i / 10) * r + d * r * 0.7, 0.04, math.sin(2 * math.pi * i / 10) * r * 0.85 - r * 0.55) for i in range(10)]
    g.slot("base"); g.slab(outline, UP, 0.035)


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
    Part("ear_pointy", "ear", "Pointed triangular ear (cats, foxes, wolves, goblins).", ["cat", "fox", "wolf", "goblin"],
         {"size": (0.3, 3.0, 1.0), "width": (0.4, 2.0, 1.0), "tilt": (-1.0, 1.0, 0.2)}, ear_pointy, cap="flop", mirror=True, hint={"u": 0.86, "theta": 65.0}),
    Part("ear_round", "ear", "Round ear (bears, mice, monkeys).", ["bear", "mouse", "monkey", "cute"],
         {"size": (0.3, 3.0, 1.0), "tilt": (-1.0, 1.0, 0.0)}, ear_round, cap="flop", mirror=True, hint={"u": 0.86, "theta": 60.0}),
    Part("ear_long", "ear", "Long upright ear (rabbits, donkeys, jackalopes).", ["rabbit", "donkey", "cute"],
         {"size": (0.3, 3.0, 1.0), "length": (0.5, 2.5, 1.0), "tilt": (-1.0, 1.0, 0.3)}, ear_long, cap="flop", mirror=True, hint={"u": 0.85, "theta": 75.0}),
    Part("ear_fan", "ear", "Large flat fan ear on the side of the head (elephants).", ["elephant", "big"],
         {"size": (0.4, 3.0, 1.0), "droop": (0.0, 1.0, 0.5)}, ear_fan, cap="flop", mirror=True, hint={"u": 0.88, "theta": 20.0}),
]
