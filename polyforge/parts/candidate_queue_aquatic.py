"""Local fish anatomy studies. Metres, +Y dorsal, +Z rostral, +X left."""

from math import cos, exp, pi, radians, sin, tau

from mathutils import Matrix

from ..kit import RIGHT, UP, V, lerp
from . import Part
from .research_locomotion import _closed_rings


def compound_ventral_suction_disc(g, p):
    """A continuous ventral seal with lateral clefts and a recessed chamber."""
    size, release = p["size"], p["release"]
    g.setup(finish="direct")

    def ring(radius, y, textured=False):
        points = []
        for j in range(144):
            angle = tau * j / 144
            lateral, rostral = sin(angle), cos(angle)
            cleft = exp(-((rostral + .06) / .19)**2)
            x = radius * .022 * lateral * (1 + .17 * rostral - .18 * cleft)
            z = radius * .026 * rostral * (1 + .12 * lateral**2)
            height = y + release * .008 * radius**3 * max(0., rostral)**2
            if textured:
                # Rounded papilla crowns resolve as surface relief within the rim.
                relief = (.5 + .5 * cos(36 * angle + textured * pi))**2.2
                height -= .00085 * relief * (1 - .82 * cleft)
            points.append(V(x, height, z) * size)
        return points

    rings = [ring(radius, y, texture) for radius, y, texture in (
        (.08, .0040, 0), (.44, .0039, 0), (.69, .0029, 0),
        (.87, -.0009, 0), (.98, -.0054, 0), (1., -.0084, 0),
        (.984, -.0101, 0), (.956, -.01055, 0), (.931, -.01060, 1),
        (.905, -.01049, 0), (.876, -.01028, 2), (.844, -.00991, 0),
        (.813, -.00952, 1), (.782, -.00891, 0), (.74, -.00815, 0),
        (.65, -.0066, 0), (.51, -.0054, 0), (.31, -.0048, 0), (.08, -.0046, 0),
    )]
    _closed_rings(g, rings)


_FINLET_BONES = [
    {"name": f"{bank}_{index + 1:02}", "pivot": (0, 0, 0), "axis": (1, 0, 0), "angle": angle}
    for bank, angle in (("dorsal", -12), ("ventral", 12)) for index in range(8)
]


def serial_caudal_finlets(g, p):
    """Opposing eight-finlet rows with open gaps and separate root pivots."""
    size = p["size"]
    outline = (
        (-.07, -.19), (.27, -.17), (.29, .02), (.16, .43), (-.42, 1.00),
        (-.58, 1.02), (-.57, .85), (-.57, .73), (-.69, .50), (-.58, .25),
        (-.40, .10), (-.38, -.11),
    )
    for bone in _FINLET_BONES:
        bank, serial = bone["name"].split("_")
        index = int(serial) - 1
        t = index / 7
        side = 1 if bank == "dorsal" else -1
        center = V(0, side * lerp(.018, .006, t) * size, lerp(.081, -.078, t) * size)
        height = lerp(.016, .0068, t) * size
        width = lerp(.017, .011, t) * size
        g.pivots[bone["name"]] = center
        g.use(bone["name"])
        g.setup(finish="subsurf_low")
        points = [center + V(0, side * y * height, z * width) for z, y in outline]
        g.slab(points, RIGHT, .18 * height, bulge=.10)


_SPINELET_BONES = [
    {"name": f"spinelet_{index + 1}", "pivot": (0, 0, z), "axis": (1, 0, 0), "angle": -46}
    for index, z in enumerate((.040, .005, -.030))
]


def segmented_spinelet_dorsal(g, p):
    """Three independently seated anterior dorsal spines with posterior webs."""
    size, fold = p["size"], p["fold"]
    for index, bone in enumerate(_SPINELET_BONES):
        center = V(bone["pivot"]) * size + V(0, -.002 * abs(index - 1) * size, 0)
        rotation = Matrix.Rotation(radians(-45 * fold), 3, "X")
        factor = size * (1 - .09 * index)

        def posed(x, y, z):
            return center + rotation @ (V(x, y, z) * factor)

        g.pivots[bone["name"]] = center
        g.use(bone["name"])
        g.setup(finish="direct")
        spine_path = [(0., -.002, -.001), (0., .004, .0017), (0., .013, .000),
                      (0., .025, -.004), (0., .041, -.013), (0., .047, -.0175)]
        g.loft([posed(*point) for point in spine_path],
               [(a * factor, b * factor) for a, b in (
                   (.0038, .0034), (.0031, .0030), (.0021, .0022), (.0015, .0017),
                   (.00065, .0009), (.00036, .00045))],
               sides=14, up=V(0, 0, 1), density=5)

        web = [
            (0., .0005, -.003), (0., .013, -.001), (0., .025, -.0048),
            (0., .039, -.012), (0., .046, -.0173), (0., .043, -.023),
            (0., .037, -.031), (0., .028, -.036), (0., .014, -.038),
            (0., .002, -.032), (0., .000, -.014),
        ]
        g.slab([posed(*point) for point in web], RIGHT, .0019 * factor, bulge=.20)
        for start, mid, end in (
            ((.0005, .030, -.007), (.0012, .034, -.020), (.0005, .037, -.030)),
            ((.0005, .023, -.004), (.0012, .024, -.022), (.0005, .027, -.035)),
            ((.0005, .013, -.002), (.0012, .013, -.022), (.0005, .014, -.037)),
        ):
            g.loft([posed(*point) for point in (start, mid, end)],
                   [factor * r for r in (.00057, .00046, .00027)], sides=8, density=3)


_PELVIC_BONES = [
    {"name": side, "pivot": (sign * .016, -.003, -.005), "axis": (sign, .12, 0), "angle": -60}
    for side, sign in (("left", 1), ("right", -1))
]


def pelvic_shield_spine_pair(g, p):
    """A fused ventral shield supporting left and right trochlear spine seats."""
    size, spread = p["size"], p["spread"]
    g.setup(finish="direct")
    g.loft([V(0, y * size, z * size) for y, z in (
        (.001, .050), (.000, .036), (-.001, .014), (-.001, -.003),
        (-.0005, -.017), (.001, -.028), (.002, -.041),
    )], [(w * size, d * size) for w, d in (
        (.002, .0011), (.006, .0016), (.014, .0021), (.019, .0028),
        (.012, .0023), (.0055, .0015), (.0014, .0007),
    )], sides=24, exponent=.69, density=6, up=UP)

    for bone, sign in zip(_PELVIC_BONES, (1, -1)):
        pivot = V(bone["pivot"]) * size
        g.oval(pivot + V(0, .0021 * size, 0), V(.0043, .0037, .0058) * size, segs=16, rings=9)
        g.pivots[bone["name"]] = pivot
        angle = radians(58 * spread)
        rotation = Matrix.Rotation(-angle, 3, "X") @ Matrix.Rotation(-sign * angle * .42, 3, "Y")

        def posed(x, y, z):
            return pivot + rotation @ (V(sign * x, y, z) * size)

        g.use(bone["name"])
        g.setup(finish="direct")
        g.loft([posed(*point) for point in (
            (0., 0., .002), (.0002, -.0015, -.005), (.0013, -.0026, -.015),
            (.002, -.0037, -.030), (.0013, -.0032, -.049), (.000, -.002, -.059),
        )], [(w * size, d * size) for w, d in (
            (.0033, .0029), (.0031, .0023), (.0021, .0019),
            (.0015, .0014), (.0007, .0008), (.00022, .00028),
        )], sides=14, density=5)
        for index in range(8):
            fraction = index / 7
            z = lerp(-.014, -.051, fraction)
            radius = size * lerp(.00115, .00046, fraction)
            g.loft([posed(.0017, -.002, z), posed(.0026, -.0036, z - .003),
                    posed(.0026, -.0045, z - .005)],
                   [radius, radius * .55, radius * .13], sides=8, density=3)
        g.use("self")


def paired_caudal_peduncle_keels(g, p):
    """Symmetric long lateral keels plus two shorter oblique vanes per side."""
    size, projection = p["size"], p["projection"]
    g.setup(finish="direct")
    for side in (-1, 1):
        for branch in (0, -1, 1):
            rings = []
            for j in range(37):
                t = j / 36
                ridge = .018 * max(.012, sin(pi * t**.76))**.75 * projection
                height = .0040 * max(.10, sin(pi * t))**.52
                x = lerp(.024, .011, t)
                z = lerp(.077, -.071, t)
                y = 0.
                if branch:
                    x = lerp(.015, .010, t)
                    z = lerp(-.052, -.095, t)
                    y = branch * lerp(.0058, .013, t)
                    ridge *= .33
                    height *= .52
                ring = []
                for k in range(18):
                    angle = tau * k / 18
                    edge = .5 + .5 * cos(angle)
                    normal = -.0020 + (ridge + .0020) * edge
                    depth = height * sin(angle) * (1.15 - .60 * edge)
                    ring.append(V(side * (x + normal), y + depth, z) * size)
                rings.append(ring)
            _closed_rings(g, rings)


def terminal_clavus(g, p):
    """A deep continuous rear fan with broad body seat and scalloped free margin."""
    size, turn = p["size"], p["turn"]
    g.setup(finish="direct")
    rings = []
    for index in range(73):
        t = index / 72
        v = 2 * t - 1
        span = 1 - abs(v)**2.6
        seat = .020 * v**2
        reach = .003 + .099 * span + .0055 * span * cos(tau * 8.5 * t + .55)
        width = .0018 + .026 * span**.67
        for_ring = []
        for k in range(36):
            a = tau * k / 36
            fraction = .5 + .5 * cos(a)
            z = seat - reach * fraction
            thickness = width * max(.02, 1 - fraction)**.72
            # The skin thins across the unsupported fringe beyond the ossicles.
            node = .0028 * span * exp(-((fraction - .85) / .11)**2)
            node *= max(0., cos(tau * 8.5 * t + .55))**2
            x = sin(a) * (thickness + node) + turn * .060 * fraction**1.7 * span
            for_ring.append(V(x, .151 * v, z) * size)
        rings.append(for_ring)
    _closed_rings(g, rings)


_SIZE = {"size": (.60, 1.60, 1.)}

PARTS = [
    Part("compound_ventral_suction_disc", "locomotion",
         "Ventral adhesive disc with lateral clefts, continuous seal and papilla fields.",
         ["clingfish", "ventral", "adhesive", "suction", "papillae"],
         {**_SIZE, "release": (0., 1., 0.)}, compound_ventral_suction_disc,
         orient="native", symmetry="center", hint={"u": .78, "theta": -90.}),
    Part("serial_caudal_finlets", "locomotion",
         "Eight independently rooted finlets in each of two opposing caudal banks.",
         ["tuna", "finlet", "posterior", "dorsal", "ventral"], _SIZE, serial_caudal_finlets,
         orient="native", symmetry="center", hint={"u": .15, "theta": 0.}, bones=_FINLET_BONES),
    Part("segmented_spinelet_dorsal", "locomotion",
         "Short bichir dorsal run with three leading spines, trailing membranes and separate hinges.",
         ["bichir", "dorsal", "finlet", "spine", "folding"], {**_SIZE, "fold": (0., 1., .05)},
         segmented_spinelet_dorsal, orient="native", symmetry="center",
         hint={"u": .35, "theta": 90.}, bones=_SPINELET_BONES),
    Part("pelvic_shield_spine_pair", "aesthetics",
         "Ventral skeletal shield with bilateral spine seats and serrated pelvic spines.",
         ["stickleback", "girdle", "pelvic", "spine", "shield"], {**_SIZE, "spread": (0., 1., .62)},
         pelvic_shield_spine_pair, orient="native", symmetry="center",
         hint={"u": .55, "theta": -90.}, bones=_PELVIC_BONES),
    Part("paired_caudal_peduncle_keels", "locomotion",
         "Opposite longitudinal peduncle keels flanked by short oblique accessory pairs.",
         ["tuna", "peduncle", "keel", "caudal"], {**_SIZE, "projection": (.6, 1.5, 1.)},
         paired_caudal_peduncle_keels, orient="native", symmetry="center", hint={"u": .10, "theta": 0.}),
    Part("terminal_clavus", "locomotion",
         "Broad terminal rudder with a full-depth seat and scalloped ossicle-supported margin.",
         ["sunfish", "clavus", "terminal", "rudder"], {**_SIZE, "turn": (-1., 1., 0.)},
         terminal_clavus, orient="native", symmetry="center", hint={"u": .01, "theta": 0.}),
]
