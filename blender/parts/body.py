"""Back, side and tail details plus wings. Surface frame unless noted."""
import math
from kit import V, UP, BACK, RIGHT, rot, curve_points, taper, lerp
from parts import Part


def spike(g, p):
    L = 0.2 * p["length"]
    g.slot("horn"); g.cone(V(0, -0.02, 0), V(0, L, p["lean"] * L * 0.6), 0.05 * p["thickness"], 5, BACK)


def plate(g, p):
    h, w = 0.28 * p["height"], 0.14 * p["width"]
    l = p["lean"] * h * 0.5
    g.slot("accent")
    g.slab([V(0, -0.03, -w), V(0, -0.03, w), V(0, h * 0.6, w * 0.8 + l * 0.6), V(0, h, l), V(0, h * 0.6, -w * 0.8 + l * 0.6)], RIGHT, 0.035)


def fin_dorsal(g, p):
    h, l, sw = 0.35 * p["height"], 0.25 * p["length"], p["sweep"]
    g.slot("accent")
    g.slab([V(0, -0.03, -l), V(0, -0.03, l), V(0, h * 0.5, l * 0.4 - sw * l * 0.4), V(0, h, -sw * l), V(0, h * 0.35, -l * 0.9 - sw * l * 0.3)], RIGHT, 0.03)


def crest(g, p):
    h, l, n = 0.16 * p["height"], 0.2 * p["length"], 4
    outline = [V(0, -0.03, l)]
    for i in range(n):
        z1 = lerp(l, -l, (i + 0.6) / n)
        outline.append(V(0, h * (1 - 0.3 * i / n), z1 + 0.02))
        outline.append(V(0, h * 0.3, lerp(z1, lerp(l, -l, (i + 1) / n), 0.5)))
    outline.append(V(0, -0.03, -l))
    g.slot("accent"); g.slab(outline[::-1], RIGHT, 0.025)


def shell(g, p):
    w, l, h = 0.45 * p["width"], 0.55 * p["length"], 0.3 * p["height"]
    g.slot("accent"); g.ellipsoid(V(0, -h * 0.35, 0), (w, h, l), None, 9, 6)
    g.slot("detail"); g.ellipsoid(V(0, -h * 0.55, 0), (w * 1.06, h * 0.25, l * 1.04), None, 9, 3)


def mane(g, p):
    s = p["size"]
    L, sp = 0.18 * p["length"] * s, p["spread"]
    g.slot("accent")
    k = 0
    for row in range(3):
        for i in range(5):
            a = lerp(-1.2, 1.2, i / 4) * sp
            base = V(math.sin(a) * 0.12 * s, -0.03 + math.cos(a) * 0.02, (0.08 - row * 0.09) * s)
            d = V(math.sin(a) * 0.9, math.cos(a), -0.5).normalized()
            jitter = 0.8 + 0.4 * ((k * 0.618) % 1.0)
            g.cone(base, base + d * L * jitter, 0.05 * s, 4, BACK)
            k += 1


def frill(g, p):
    r, n = 0.35 * p["size"], 6
    b = rot(RIGHT, -p["tilt"] * 0.8)
    outline = [b @ V(r * 0.6, -0.05, 0)]
    for i in range(n * 2 + 1):
        a = math.pi * i / (n * 2)
        rr = r if i % 2 == 0 else r * 0.82
        outline.append(b @ V(math.cos(a) * rr, math.sin(a) * rr * 0.9, 0))
    outline.append(b @ V(-r * 0.6, -0.05, 0))
    g.slot("accent"); g.slab(outline, b @ BACK, 0.04)


def antenna(g, p):
    L = 0.4 * p["length"]
    pts = curve_points(V(0, -0.02, 0), V(0.15, 1, 0.3).normalized(), V(0, 0, p["curve"]), L, 5)
    g.slot("dark"); g.tube(pts, taper(0.018, 0.01, 5), 4, False, True, BACK)
    b = 0.035 * max(p["bulb"], 0.05)
    g.slot("accent"); g.ellipsoid(pts[4], (b, b, b), None, 6, 4)


def wing_bat(g, p):
    L, C, f = 0.9 * p["span"], p["chord"], p["fold"]
    tipd = rot(RIGHT, -f * 0.9) @ V(0, L, -0.1 * L)
    wrist = V(0, L * 0.45, 0.18 * L * C)
    pts = [V(0, -0.02, 0.1 * L * C), wrist, tipd,
           V(0, L * 0.72, -0.3 * L * C) + (tipd - V(0, L, -0.1 * L)) * 0.6,
           V(0, L * 0.55, -0.22 * L * C), V(0, L * 0.38, -0.42 * L * C),
           V(0, L * 0.18, -0.32 * L * C), V(0, -0.02, -0.25 * L * C)]
    g.slot("accent"); g.slab(pts, RIGHT, 0.015)
    g.slot("skin"); g.tube([pts[0], wrist, tipd], [0.04, 0.03, 0.01], 5, True, True, RIGHT)
    for k in (3, 5):
        g.tube([wrist, pts[k]], [0.022, 0.008], 4, False, True, RIGHT)


def wing_feather(g, p):
    L = 0.85 * p["span"]
    C, n = 0.3 * p["chord"] * L, 5
    g.slot("base")
    g.slab([V(0, -0.02, 0.12 * L), V(0, L * 0.55, 0.1 * L), V(0, L * 0.6, -0.05 * L), V(0, 0, -0.1 * L)], RIGHT, 0.04)
    for i in range(n):
        t = i / (n - 1)
        root = V(0, lerp(0.1, 0.62, t) * L, lerp(-0.08, 0.04, t) * L)
        d = V(0, lerp(0.05, 0.75, t), -lerp(1.0, 0.45, t)).normalized()
        fl = C * lerp(1.0, 1.4, t)
        side = V(0, -d.z, d.y) * 0.06 * L
        g.slot("accent" if i % 2 == 0 else "detail")
        g.slab([root - side, root + side, root + d * fl + side * 0.6, root + d * fl * 1.12, root + d * fl - side * 0.6], RIGHT, 0.012 + 0.002 * i)


def tail_club(g, p):
    r = 0.14 * p["size"]
    sp = max(p["spikes"], 0.05)
    g.slot("horn"); g.ellipsoid(V(0, r * 0.7, 0), (r * 1.25, r, r * 0.8), None, 7, 5)
    for side in (-1, 1):
        g.cone(V(side * r, r * 0.7, 0), V(side * r * (1.0 + 0.5 * sp + 0.6 * min(sp, 1)), r * 0.8, 0), r * 0.3 * min(1.0, sp + 0.3), 4, UP)


def tail_tuft(g, p):
    s = p["size"]
    L = 0.2 * s * p["length"]
    g.slot("accent")
    for i in range(7):
        a = 2 * math.pi * i / 7
        off = V(math.cos(a), 0, math.sin(a)) * 0.03 * s
        d = V(math.cos(a) * 0.4, 1, math.sin(a) * 0.4).normalized()
        g.cone(off - V(0, 0.02, 0), off + d * L * (0.8 + 0.3 * (i % 3) / 2), 0.045 * s, 4, BACK)


def tail_fan(g, p):
    s, n = p["size"], 5
    L = 0.4 * s
    for i in range(n):
        t = i / (n - 1)
        a = lerp(-1.0, 1.0, t) * p["spread"]
        d = V(math.sin(a), math.cos(a), p["lift"] * 0.6).normalized()
        side = d.cross(BACK).normalized() * 0.05 * s
        g.slot("accent" if i % 2 == 0 else "base")
        g.slab([-side * 0.3, side * 0.3, d * L + side, d * L * 1.1, d * L - side], BACK, 0.015)


FACE = dict(orient="face")
PARTS = [
    Part("spike", "detail", "Single conical spike; place several along the back or tail.", ["armored", "dinosaur", "hedgehog", "menacing"],
         {"length": (0.2, 4.0, 1.0), "thickness": (0.4, 2.5, 1.0), "lean": (-1.0, 1.0, -0.3)}, spike, hint={"u": 0.5, "theta": 90.0}),
    Part("plate", "detail", "Upright armor plate (stegosaurus back plates).", ["dinosaur", "armored"],
         {"height": (0.3, 3.0, 1.0), "width": (0.3, 2.5, 1.0), "lean": (-1.0, 1.0, -0.2)}, plate, hint={"u": 0.5, "theta": 90.0}),
    Part("fin_dorsal", "detail", "Swept dorsal fin or sail (sharks, fish, dimetrodon sail when long).", ["fish", "shark", "aquatic", "sail"],
         {"height": (0.3, 3.0, 1.0), "length": (0.3, 3.0, 1.0), "sweep": (-1.0, 1.0, 0.6)}, fin_dorsal, hint={"u": 0.55, "theta": 90.0}),
    Part("crest", "detail", "Spiky zig-zag crest ridge for heads and backs (dragons, iguanas).", ["dragon", "lizard", "punk"],
         {"height": (0.3, 3.0, 1.0), "length": (0.3, 3.0, 1.0)}, crest, hint={"u": 0.85, "theta": 90.0}),
    Part("shell", "detail", "Domed shell or carapace covering the back (turtles, beetles, armadillos).", ["turtle", "beetle", "armored", "snail"],
         {"width": (0.4, 3.0, 1.0), "length": (0.4, 3.0, 1.0), "height": (0.3, 2.0, 1.0)}, shell, hint={"u": 0.5, "theta": 90.0}),
    Part("mane", "detail", "Shaggy mane of tufts over the neck or head (lions, minotaurs, horses, punk crests).", ["lion", "horse", "minotaur", "hairy"],
         {"size": (0.3, 3.0, 1.0), "length": (0.3, 2.5, 1.0), "spread": (0.2, 1.5, 1.0)}, mane, hint={"u": 0.75, "theta": 90.0}),
    Part("frill", "detail", "Fan-shaped neck frill or bony shield behind the head (triceratops, frilled lizard).", ["dinosaur", "lizard", "display"],
         {"size": (0.3, 3.0, 1.0), "tilt": (-1.0, 1.0, 0.4)}, frill, hint={"u": 0.82, "theta": 90.0}),
    Part("antenna", "detail", "Thin antenna with a bulb tip (insects, aliens).", ["insect", "alien", "cute"],
         {"length": (0.3, 3.0, 1.0), "curve": (-1.0, 1.0, -0.4), "bulb": (0.0, 2.0, 1.0)}, antenna, cap="sway", mirror=True, hint={"u": 0.93, "theta": 75.0}),
    Part("wing_bat", "wing", "Membrane wing with finger struts (bats, dragons, demons).", ["bat", "dragon", "demon", "flying"],
         {"span": (0.4, 4.0, 1.0), "chord": (0.4, 2.5, 1.0), "fold": (0.0, 1.0, 0.2)}, wing_bat, cap="flap", mirror=True, hint={"u": 0.62, "theta": 55.0}),
    Part("wing_feather", "wing", "Feathered bird wing made of layered flight feathers.", ["bird", "angel", "griffin", "flying"],
         {"span": (0.4, 4.0, 1.0), "chord": (0.4, 2.5, 1.0)}, wing_feather, cap="flap", mirror=True, hint={"u": 0.62, "theta": 55.0}),
    Part("tail_club", "tail", "Bony club for the tail tip (ankylosaurus); place at the rear tip (u near 0).", ["dinosaur", "armored"],
         {"size": (0.4, 3.0, 1.0), "spikes": (0.0, 1.5, 1.0)}, tail_club, hint={"u": 0.0, "theta": 90.0}, **FACE),
    Part("tail_tuft", "tail", "Hairy tuft for the tail tip (lions, bulls, donkeys); place at the rear tip (u near 0).", ["lion", "bull", "minotaur", "hairy"],
         {"size": (0.3, 3.0, 1.0), "length": (0.3, 2.5, 1.0)}, tail_tuft, hint={"u": 0.0, "theta": 90.0}, **FACE),
    Part("tail_fan", "tail", "Spread fan of tail feathers (birds, peacocks) or a fish tail fin; place at the rear tip.", ["bird", "peacock", "fish", "display"],
         {"size": (0.3, 3.0, 1.0), "spread": (0.3, 1.5, 0.8), "lift": (-1.0, 1.0, 0.3)}, tail_fan, hint={"u": 0.0, "theta": 90.0}, **FACE),
]
