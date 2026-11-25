"""Back, side and tail details plus wings. Surface frame unless noted."""
import math
from ..kit import V, UP, BACK, RIGHT, rot, curve_points, taper, lerp
from . import Part


def spike(g, p):
    L = 0.2 * p["length"]
    r = 0.05 * p["thickness"]
    g.slot("horn")
    g.loft(curve_points(V(0, -0.03, 0), UP, V(0, 0, p["lean"] * 0.6), L, 6), [r, r * 0.85, r * 0.6, r * 0.35, r * 0.15, 0.003], sides=18, up=BACK)


def plate(g, p):
    h, w = 0.28 * p["height"], 0.14 * p["width"]
    l = p["lean"] * h * 0.5
    g.setup(finish="subsurf")
    g.slot("accent")
    g.slab([V(0, -0.04, -w), V(0, -0.04, w), V(0, h * 0.55, w * 0.85 + l * 0.6), V(0, h * 0.9, w * 0.25 + l), V(0, h, l * 1.05), V(0, h * 0.9, -w * 0.25 + l), V(0, h * 0.55, -w * 0.85 + l * 0.6)], RIGHT, 0.05)


def fin_dorsal(g, p):
    h, l, sw = 0.35 * p["height"], 0.25 * p["length"], p["sweep"]
    g.setup(finish="subsurf")
    g.slot("accent")
    g.slab([V(0, -0.04, -l), V(0, -0.04, l), V(0, h * 0.5, l * 0.45 - sw * l * 0.4), V(0, h * 0.9, -sw * l * 0.75), V(0, h, -sw * l), V(0, h * 0.6, -l * 0.6 - sw * l * 0.4), V(0, h * 0.3, -l * 0.95 - sw * l * 0.3)], RIGHT, 0.045)


def crest(g, p):
    h, l, n = 0.16 * p["height"], 0.2 * p["length"], 4
    outline = [V(0, -0.04, l)]
    for i in range(n):
        z1 = lerp(l, -l, (i + 0.6) / n)
        outline.append(V(0, h * (1 - 0.3 * i / n), z1 + 0.02))
        outline.append(V(0, h * 0.35, lerp(z1, lerp(l, -l, (i + 1) / n), 0.5)))
    outline.append(V(0, -0.04, -l))
    g.setup(finish="subsurf")
    g.slot("accent")
    g.slab(outline[::-1], RIGHT, 0.04, bulge=0.3)


def shell(g, p):
    """Domed carapace with carved plate grooves and a soft rim."""
    w, l, h = 0.45 * p["width"], 0.55 * p["length"], 0.3 * p["height"]
    g.setup(voxel=0.006, detail=1.6)
    g.slot("accent")
    g.oval(V(0, -h * 0.3, 0), (w, h, l), segs=32, rings=18)
    for a in (-0.5, 0.5):
        g.cut_loft([V(math.sin(a) * w * 0.98, -h * 0.3 + h * 0.75, -l * 1.05), V(math.sin(a) * w * 0.78, -h * 0.3 + h * 1.0, 0), V(math.sin(a) * w * 0.98, -h * 0.3 + h * 0.75, l * 1.05)], [0.018, 0.022, 0.018], sides=10, up=UP)
    for zf in (-0.45, 0.0, 0.45):
        g.cut_loft([V(-w * 1.05, -h * 0.3 + h * 0.3, zf * l), V(0, -h * 0.3 + h * 1.02, zf * l * 1.05), V(w * 1.05, -h * 0.3 + h * 0.3, zf * l)], [0.018, 0.02, 0.018], sides=10, up=BACK)
    g.slot("detail")
    g.loft([V(math.cos(2 * math.pi * i / 16) * w * 1.04, -h * 0.48, math.sin(2 * math.pi * i / 16) * l * 1.03) for i in range(17)], [h * 0.14] * 17, sides=14, up=UP, density=3)


def mane(g, p):
    """Soft clumps of hair over the neck, in the style of the original minotaur mane."""
    s = p["size"]
    L, sp = 0.2 * p["length"] * s, p["spread"]
    g.setup(voxel=0.004 * s, detail=1.5, smooth=0.4)
    g.slot("accent")
    k = 0
    for row in range(3):
        for i in range(5):
            a = lerp(-1.25, 1.25, i / 4) * sp
            base = V(math.sin(a) * 0.12 * s, -0.04 + math.cos(a) * 0.025, (0.09 - row * 0.09) * s)
            d = V(math.sin(a) * 0.85, math.cos(a) * 0.7, -0.75).normalized()
            jitter = 0.8 + 0.4 * ((k * 0.618) % 1.0)
            r = (0.055 - 0.008 * row) * s
            g.loft(curve_points(base, d, V(0, -0.35, -0.2), L * jitter, 4), [r, r * 0.8, r * 0.45, r * 0.08], sides=14, up=BACK)
            k += 1


def frill(g, p):
    r, n = 0.35 * p["size"], 6
    b = rot(RIGHT, -p["tilt"] * 0.8)
    outline = [b @ V(r * 0.55, -0.05, 0)]
    for i in range(n * 2 + 1):
        a = math.pi * i / (n * 2)
        rr = r if i % 2 == 0 else r * 0.84
        outline.append(b @ V(math.cos(a) * rr, math.sin(a) * rr * 0.9, 0))
    outline.append(b @ V(-r * 0.55, -0.05, 0))
    g.setup(finish="subsurf")
    g.slot("accent")
    g.leaf(outline, b @ BACK, 0.045, 0.4)


def antenna(g, p):
    L = 0.4 * p["length"]
    pts = curve_points(V(0, -0.03, 0), V(0.15, 1, 0.3).normalized(), V(0, 0, p["curve"]), L, 6)
    g.setup(voxel=0.0025)
    g.slot("dark")
    g.loft(pts, taper(0.02, 0.011, 6), sides=12, up=BACK)
    b = 0.036 * max(p["bulb"], 0.1)
    g.slot("accent")
    g.oval(pts[-1], b, segs=18, rings=10)


def wing_bat(g, p):
    L, C, f = 0.9 * p["span"], p["chord"], p["fold"]
    tipd = rot(RIGHT, -f * 0.9) @ V(0, L, -0.1 * L)
    wrist = V(0, L * 0.45, 0.18 * L * C)
    rim = [V(0, -0.06, 0.02 * L * C), wrist, tipd,
           V(0, L * 0.72, -0.3 * L * C) + (tipd - V(0, L, -0.1 * L)) * 0.6,
           V(0, L * 0.6, -0.2 * L * C), V(0, L * 0.4, -0.42 * L * C),
           V(0, L * 0.25, -0.3 * L * C), V(0, L * 0.12, -0.36 * L * C), V(0, -0.03, -0.25 * L * C)]
    g.setup(slot_finish={"accent": "subsurf"}, voxel=0.005)
    g.slot("accent")
    # Support the outline through subdivision so membrane tips meet their spars.
    supported = []
    for i, point in enumerate(rim):
        supported.extend([lerp(point, rim[i-1], .08), point, lerp(point, rim[(i+1) % len(rim)], .08)])
    g.slab(supported, RIGHT, 0.018, bulge=0.2)
    g.slot("base")
    g.loft([rim[0], lerp(rim[0], wrist, 0.5), wrist, lerp(wrist, tipd, 0.5), tipd], [0.045, 0.04, 0.035, 0.022, 0.008], sides=14, up=RIGHT)
    for k in (3, 5, 7):
        g.loft([wrist, lerp(wrist, rim[k], 0.5), rim[k]], [0.024, 0.016, 0.006], sides=12, up=RIGHT)


def wing_feather(g, p):
    L = 0.85 * p["span"]
    C, n = 0.3 * p["chord"] * L, 6
    g.setup(finish="subsurf")
    g.slot("base")
    g.slab([V(0, -0.03, 0.12 * L), V(0, L * 0.3, 0.13 * L), V(0, L * 0.6, 0.08 * L), V(0, L * 0.62, -0.06 * L), V(0, L * 0.3, -0.1 * L), V(0, 0, -0.1 * L)], RIGHT, 0.05, bulge=0.4)
    for i in range(n):
        t = i / (n - 1)
        root = V(0, lerp(0.1, 0.62, t) * L, lerp(-0.08, 0.04, t) * L)
        d = V(0, lerp(0.05, 0.75, t), -lerp(1.0, 0.45, t)).normalized()
        fl = C * lerp(1.0, 1.45, t)
        side = V(0, -d.z, d.y) * 0.055 * L
        g.slot("accent" if i % 2 == 0 else "detail")
        g.slab([root - side * 0.8, root + side * 0.8, root + d * fl * 0.6 + side, root + d * fl + side * 0.45, root + d * fl * 1.1, root + d * fl - side * 0.45, root + d * fl * 0.6 - side], RIGHT, 0.016 + 0.003 * i, bulge=0.3)


def tail_club(g, p):
    r = 0.14 * p["size"]
    sp = max(p["spikes"], 0.1)
    g.setup(voxel=0.004 * p["size"])
    g.slot("horn")
    g.oval(V(0, r * 0.7, 0), (r * 1.25, r, r * 0.85))
    for side in (-1, 1):
        g.oval(V(side * r * 0.8, r * 0.75, 0), (r * 0.55, r * 0.5, r * 0.5), segs=18, rings=10)
        g.loft([V(side * r * 1.0, r * 0.75, 0), V(side * r * (1.25 + 0.3 * sp), r * 0.8, 0), V(side * r * (1.4 + 0.6 * sp), r * 0.85, 0)], [r * 0.3, r * 0.18 * sp ** 0.5, 0.004], sides=14, up=UP)


def tail_tuft(g, p):
    s = p["size"]
    L = 0.2 * s * p["length"]
    g.setup(voxel=0.003 * s, smooth=0.4)
    g.slot("accent")
    g.oval(V(0, 0.02 * s, 0), (0.05 * s, 0.05 * s, 0.05 * s), segs=18, rings=10)
    for i in range(7):
        a = 2 * math.pi * i / 7
        off = V(math.cos(a), 0, math.sin(a)) * 0.03 * s
        d = V(math.cos(a) * 0.45, 1, math.sin(a) * 0.45).normalized()
        ln = L * (0.8 + 0.3 * (i % 3) / 2)
        g.loft(curve_points(off, d, V(math.cos(a) * 0.2, -0.15, math.sin(a) * 0.2), ln, 4), [0.045 * s, 0.038 * s, 0.022 * s, 0.004 * s], sides=12, up=BACK)


def tail_fan(g, p):
    s, n = p["size"], 5
    L = 0.4 * s
    g.setup(finish="subsurf")
    for i in range(n):
        t = i / (n - 1)
        a = lerp(-1.0, 1.0, t) * p["spread"]
        d = V(math.sin(a), math.cos(a), p["lift"] * 0.6).normalized()
        side = d.cross(BACK).normalized() * 0.055 * s
        g.slot("accent" if i % 2 == 0 else "base")
        g.slab([-side * 0.35, side * 0.35, d * L * 0.6 + side, d * L + side * 0.5, d * L * 1.12, d * L - side * 0.5, d * L * 0.6 - side], BACK, 0.02, bulge=0.3)


def bulge(g, p):
    """Generic sculpting mass: muscles, humps, cheeks, bellies. A wide, shallow, mostly
    buried swell (width across, length along the body) that fuses into the skin."""
    w, l = 0.16 * p["width"], 0.19 * p["length"]
    h = 0.045 * p["height"]
    tp = p["taper"]
    g.setup(voxel=0.006, smooth=0.6)
    g.slot("skin")
    g.oval(V(0, h - w * 0.9, l * 0.12 * tp), (w, w * 0.9, l), segs=28, rings=16)


def brow_ridge(g, p):
    """Heavy brow over both eyes (bulls, brutes, apes); place on the head top-front (face frame)."""
    s, w, d = p["size"], p["width"], p["depth"]
    g.setup(voxel=0.004 * s, smooth=0.6)
    g.slot("skin")
    pts, rad = [], []
    for i in range(7):
        t = i / 6
        a = (t - 0.5) * 2.2
        x = math.sin(a) * 0.15 * s * w
        pts.append(V(x, (0.03 + 0.03 * math.cos(a)) * s * d, (0.04 - 0.035 * abs(math.sin(a)) ** 1.5 - 0.03 * p["frown"] * (1 - abs(t - 0.5) * 2)) * s))
        rad.append((0.035 * s * (0.75 + 0.35 * math.cos(a)), 0.03 * s * d * (0.7 + 0.4 * math.cos(a))))
    g.loft(pts, rad, sides=20, up=UP)


def cheek(g, p):
    """Rounded cheek / jowl mass on the side of the head (face frame)."""
    s = p["size"]
    g.setup(voxel=0.004 * s, smooth=0.6)
    g.slot("skin")
    g.oval(V(0, 0.01 * s, -0.01 * s), (0.07 * s * p["width"], 0.05 * s * p["puff"], 0.08 * s), rot(BACK, -0.25 * p["tilt"]))


FACE = dict(orient="face")
PARTS = [
    Part("bulge", "detail", "Soft muscle mass or hump that blends into the body (shoulders, haunches, chest, humps, bellies).", ["muscle", "hump", "sculpt"],
         {"width": (0.3, 4.0, 1.0), "height": (0.3, 4.0, 1.0), "length": (0.3, 4.0, 1.0), "taper": (-1.0, 1.0, 0.0)}, bulge, mirror=True, hint={"u": 0.62, "theta": 20.0}),
    Part("brow_ridge", "detail", "Heavy brow ridge over both eyes (bulls, brutes, apes); put it on the head just above the eyes.", ["bovine", "brute", "ape", "angry"],
         {"size": (0.4, 3.0, 1.0), "width": (0.5, 2.0, 1.0), "depth": (0.4, 2.0, 1.0), "frown": (-1.0, 1.0, 0.4)}, brow_ridge, hint={"u": 0.93, "theta": 55.0}, **FACE),
    Part("cheek", "detail", "Rounded cheek or jowl on the side of the head.", ["bovine", "mammal", "chubby"],
         {"size": (0.4, 3.0, 1.0), "width": (0.5, 2.0, 1.0), "puff": (0.4, 2.0, 1.0), "tilt": (-1.0, 1.0, 0.3)}, cheek, mirror=True, hint={"u": 0.94, "theta": 0.0}, **FACE),
    Part("spike", "detail", "Single conical spike; place several along the back or tail.", ["armored", "dinosaur", "hedgehog", "menacing"],
         {"length": (0.2, 4.0, 1.0), "thickness": (0.4, 2.5, 1.0), "lean": (-1.0, 1.0, -0.3)}, spike, hint={"u": 0.5, "theta": 90.0}),
    Part("plate", "detail", "Upright armor plate (stegosaurus back plates).", ["dinosaur", "armored"],
         {"height": (0.3, 3.0, 1.0), "width": (0.3, 2.5, 1.0), "lean": (-1.0, 1.0, -0.2)}, plate, hint={"u": 0.5, "theta": 90.0}),
    Part("fin_dorsal", "detail", "Swept dorsal fin or sail (sharks, fish, dimetrodon sail when long).", ["fish", "shark", "aquatic", "sail"],
         {"height": (0.3, 3.0, 1.0), "length": (0.3, 3.0, 1.0), "sweep": (-1.0, 1.0, 0.6)}, fin_dorsal, hint={"u": 0.55, "theta": 90.0}),
    Part("crest", "detail", "Spiky zig-zag crest ridge for heads and backs (dragons, iguanas).", ["dragon", "lizard", "punk"],
         {"height": (0.3, 3.0, 1.0), "length": (0.3, 3.0, 1.0)}, crest, hint={"u": 0.85, "theta": 90.0}),
    Part("shell", "detail", "Domed shell or carapace with plate grooves (turtles, beetles, armadillos).", ["turtle", "beetle", "armored", "snail"],
         {"width": (0.4, 3.0, 1.0), "length": (0.4, 3.0, 1.0), "height": (0.3, 2.0, 1.0)}, shell, hint={"u": 0.5, "theta": 90.0}),
    Part("mane", "detail", "Shaggy mane of soft clumps over the neck or head (lions, minotaurs, horses).", ["lion", "horse", "minotaur", "hairy"],
         {"size": (0.3, 3.0, 1.0), "length": (0.3, 2.5, 1.0), "spread": (0.2, 1.5, 1.0)}, mane, hint={"u": 0.75, "theta": 90.0}),
    Part("frill", "detail", "Fan-shaped neck frill or bony shield behind the head (triceratops, frilled lizard).", ["dinosaur", "lizard", "display"],
         {"size": (0.3, 3.0, 1.0), "tilt": (-1.0, 1.0, 0.4)}, frill, hint={"u": 0.82, "theta": 90.0}),
    Part("antenna", "detail", "Thin antenna with a bulb tip (insects, aliens).", ["insect", "alien", "cute"],
         {"length": (0.3, 3.0, 1.0), "curve": (-1.0, 1.0, -0.4), "bulb": (0.0, 2.0, 1.0)}, antenna, cap="sway", mirror=True, hint={"u": 0.93, "theta": 75.0}),
    Part("wing_bat", "wing", "Membrane wing with finger struts (bats, dragons, demons).", ["bat", "dragon", "demon", "flying"],
         {"span": (0.4, 4.0, 1.0), "chord": (0.4, 2.5, 1.0), "fold": (0.0, 1.0, 0.2)}, wing_bat, cap="flap", mirror=True, hint={"u": 0.62, "theta": 55.0}),
    Part("wing_feather", "wing", "Feathered bird wing made of layered flight feathers.", ["bird", "angel", "griffin", "flying"],
         {"span": (0.4, 4.0, 1.0), "chord": (0.4, 2.5, 1.0)}, wing_feather, cap="flap", mirror=True, hint={"u": 0.62, "theta": 55.0}),
    Part("tail_club", "tail", "Bony knobbed club for the tail tip (ankylosaurus); place at the rear tip (u near 0).", ["dinosaur", "armored"],
         {"size": (0.4, 3.0, 1.0), "spikes": (0.0, 1.5, 1.0)}, tail_club, hint={"u": 0.0, "theta": 90.0}, **FACE),
    Part("tail_tuft", "tail", "Hairy tuft for the tail tip (lions, bulls, donkeys); place at the rear tip (u near 0).", ["lion", "bull", "minotaur", "hairy"],
         {"size": (0.3, 3.0, 1.0), "length": (0.3, 2.5, 1.0)}, tail_tuft, hint={"u": 0.0, "theta": 90.0}, **FACE),
    Part("tail_fan", "tail", "Spread fan of tail feathers (birds, peacocks) or a fish tail fin; place at the rear tip.", ["bird", "peacock", "fish", "display"],
         {"size": (0.3, 3.0, 1.0), "spread": (0.3, 1.5, 0.8), "lift": (-1.0, 1.0, 0.3)}, tail_fan, hint={"u": 0.0, "theta": 90.0}, **FACE),
]
