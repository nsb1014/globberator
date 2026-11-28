"""Local pelvic, anal and pectoral joints and an expanding ventral skin coupon."""

from math import cos, exp, pi, radians, sin, tau

from mathutils import Matrix
from scipy.interpolate import PchipInterpolator

from ..kit import RIGHT, UP, V, lerp, smoothstep
from . import Part
from .research_locomotion import _closed_rings


def expandable_trunk_envelope(g, p):
    """A continuous ventrolateral skin section with fixed shoulder and tail borders."""
    size, inflation = p["size"], p["inflation"]
    g.setup(finish="direct")
    rings = []
    for i in range(67):
        t = i / 66
        middle = sin(pi * t)**1.55
        width = .046 + .023 * middle + .050 * inflation * middle
        y = .060 + .020 * middle + .085 * inflation * middle
        z = .142 - .284 * t
        ring = []
        samples = 48
        for j in range(2 * samples):
            outside = j < samples
            k = j if outside else 2 * samples - 1 - j
            a = lerp(-1.62, 1.62, k / (samples - 1))
            c, s = cos(a), sin(a)
            # Outer contour has a deep belly. The inner face follows its
            # expansion with a small reduction in skin thickness.
            depth = 0. if outside else .0038 - .0012 * inflation * middle
            x = (width - depth) * s
            vy = -(y - depth) * c - .020
            ring.append(V(x, vy, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)


_MUDSKIPPER_BONES = [{"name": "contact_fan", "pivot": (.054, -.047, -.011),
                      "axis": (0, 0, 1), "angle": 37.}]
_MUD_ROOT = PchipInterpolator((0., .25, .50, .75, 1.), (
    (.052, -.041, .002), (.058, -.047, -.003), (.060, -.052, -.012),
    (.058, -.055, -.021), (.053, -.052, -.024),
))
_MUD_TIPS = PchipInterpolator((0., .12, .31, .51, .71, .89, 1.), (
    (.089, -.060, .032), (.117, -.065, .022), (.133, -.067, .004),
    (.136, -.067, -.019), (.128, -.065, -.044), (.109, -.064, -.061),
    (.081, -.060, -.063),
))


def ground_contact_pectoral_crutch(g, p):
    """Short fleshy radial lever ending in a compliant mud-contact fan."""
    size, recovery = p["size"], p["recovery"]
    hinge = V(_MUDSKIPPER_BONES[0]["pivot"])
    g.pivots["contact_fan"] = hinge * size
    g.setup(finish="direct")
    centerline = [(-.009, .004, .006), (.015, -.006, .005), (.031, -.018, .000),
                  (.049, -.037, -.009), (.061, -.049, -.012)]
    g.loft([V(point) * size for point in centerline],
           [(a * size, b * size) for a, b in (
               (.016, .015), (.018, .015), (.013, .012), (.010, .009), (.009, .006),
           )], sides=28, density=9)
    g.use("contact_fan")
    g.setup(finish="direct")
    swing = Matrix.Rotation(radians(34 * recovery), 3, "Z")
    rings = []
    for i in range(105):
        t = i / 104
        root, edge = V(_MUD_ROOT(t)), V(_MUD_TIPS(t))
        ridge = (.5 + .5 * cos(tau * 15 * t))**4
        ring = []
        for j in range(26):
            a = tau * j / 26
            u = .5 + .5 * cos(a)
            point = root.lerp(edge, u)
            point.y += sin(a) * (.0008 + .0024 * (1 - u) + .00112 * ridge * sin(pi * u))
            point = hinge + swing @ (point - hinge)
            ring.append(point * size)
        rings.append(ring)
    _closed_rings(g, rings)


_CLASPER_BONES = [
    {"name": "shaft", "pivot": (.0035, -.001, -.018), "axis": (0, 1, 0), "angle": -25.},
    {"name": "terminal_fold", "pivot": (.004, -.004, -.102), "axis": (0, 0, 1), "angle": 38.},
]


def segmented_caudad_clasper(g, p):
    """Left pelvic seat, grooved cartilaginous shaft and mobile distal dermal fold."""
    size, release = p["size"], p["release"]
    for bone in _CLASPER_BONES:
        g.pivots[bone["name"]] = V(bone["pivot"]) * size
    g.setup(finish="subsurf_low")
    g.slab([V(point) * size for point in (
        (-.008, .001, .014), (.008, -.001, .018), (.030, -.003, .011),
        (.052, -.004, -.018), (.047, -.005, -.035), (.028, -.006, -.038),
        (.011, -.004, -.031), (-.008, -.002, -.021),
    )], UP, .009 * size, bulge=.32)

    g.use("shaft")
    g.setup(finish="direct")
    stations = (
        (.002, .011, .007, .00), (-.014, .010, .008, .02),
        (-.026, .009, .0065, .22), (-.043, .0078, .0055, .54),
        (-.061, .0071, .0054, .72), (-.077, .0078, .0062, .87),
        (-.091, .0095, .0065, 1.), (-.106, .0098, .0058, 1.),
        (-.119, .0076, .0044, .90), (-.128, .0037, .0028, .60),
        (-.131, .0013, .0011, .35),
    )
    profile = PchipInterpolator([-row[0] for row in stations],
                                [row[1:] for row in stations])
    rings = []
    for index in range(60):
        z = lerp(stations[0][0], stations[-1][0], index / 59)
        width, depth, gutter = profile(-z)
        ring = []
        for j in range(44):
            a = tau * j / 44
            x, dorsality = cos(a), max(0., sin(a))
            y = depth * (sin(a) - .95 * dorsality * gutter * exp(-(x / .24)**2))
            ring.append(V(.004 + width * x, y - .004, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)

    g.use("terminal_fold")
    g.setup(finish="subsurf_low")
    hinge = V(_CLASPER_BONES[1]["pivot"])
    rotation = Matrix.Rotation(radians(37 * release), 3, "Z")
    outline = (
        (.008, -.001, -.085), (.012, -.001, -.092), (.014, -.002, -.106),
        (.011, -.003, -.120), (.006, -.004, -.130), (.004, -.003, -.126),
        (.006, -.001, -.106), (.006, -.001, -.098),
    )
    g.leaf([(hinge + rotation @ (V(point) - hinge)) * size for point in outline],
           UP, .0035 * size, cup=.28)


_GONOPODIUM_BONES = [{"name": "anal_ray_bundle", "pivot": (0, -.001, .001),
                      "axis": (1, 0, 0), "angle": -91.}]


def modified_anal_ray_gonopodium(g, p):
    """Modified anal rays 3–5, a shared pivot and compact terminal features."""
    size, rotate = p["size"], p["rotate"]
    g.setup(finish="subsurf_low")
    base_outline = (
        (0., .003, .016), (0., -.006, .012), (0., -.012, .003),
        (0., -.009, -.015), (0., -.003, -.019), (0., .004, -.010),
    )
    g.slab([V(point) * size for point in base_outline], RIGHT, .0045 * size, bulge=.12)
    hinge = V(_GONOPODIUM_BONES[0]["pivot"])
    g.pivots["anal_ray_bundle"] = hinge * size
    motion = Matrix.Rotation(radians(-103 * rotate), 3, "X")
    g.use("anal_ray_bundle")
    g.setup(finish="direct")

    def moved(x, y, z):
        return (hinge + motion @ (V(x, y, z) - hinge)) * size

    for index, width in enumerate((.00215, .00157, .00135)):
        x = .0011 * (index - 1)
        y = -.0024 * (index - 1)
        path = []
        radii = []
        for sample in range(23):
            t = sample / 22
            path.append(moved(x * (1 - .61 * t), y - .012 * sin(pi * t * .70),
                              .005 - (.091 - .004 * index) * t))
            radius = width * (1 - .67 * t) * (1 + .13 * cos(tau * 9 * t))
            radii.append(radius * size)
        g.loft(path, radii, sides=12, density=2)
        if index > 0:
            z = -.080 + .0035 * index
            g.loft([moved(x * .40, y - .012, z), moved(x * 1.2, y - .016, z - .003),
                    moved(x * 1.4, y - .017, z - .002), moved(x, y - .016, z + .0010)],
                   [size * radius for radius in (.00115, .00102, .00064, .00023)],
                   sides=10, density=3)
        if index == 1:
            for tooth in range(5):
                z = -.057 - .00355 * tooth
                g.loft([moved(x, y - .011, z), moved(x, y - .014, z - .0019),
                        moved(x, y - .0144, z - .0023)],
                       [r * size for r in (.00075, .00040, .00015)], sides=8, density=2)


_SIZE = {"size": (.6, 1.6, 1.)}
PARTS = [
    Part("expandable_trunk_envelope", "aesthetics",
         "Local puffer skin envelope widening continuously between fixed trunk borders.",
         ["pufferfish", "trunk", "abdomen", "inflation", "skin"],
         {**_SIZE, "inflation": (0., 1., .56)}, expandable_trunk_envelope,
         orient="native", symmetry="center", hint={"u": .52, "theta": -90.}),
    Part("ground_contact_pectoral_crutch", "locomotion",
         "Mudskipper pectoral lever with a separate distal hinge and ray-supported contact fan.",
         ["mudskipper", "pectoral", "crutch", "substrate", "fin"],
         {**_SIZE, "recovery": (0., 1., .08)}, ground_contact_pectoral_crutch,
         orient="native", symmetry="pair", mirror=True,
         hint={"u": .62, "theta": -34.}, bones=_MUDSKIPPER_BONES),
    Part("segmented_caudad_clasper", "aesthetics",
         "Catshark pelvic fin seat with longitudinally grooved clasper and terminal fold.",
         ["catshark", "clasper", "pelvic", "groove", "cartilage"],
         {**_SIZE, "release": (0., 1., .20)}, segmented_caudad_clasper,
         orient="native", symmetry="pair", mirror=True,
         hint={"u": .46, "theta": -68.}, bones=_CLASPER_BONES),
    Part("modified_anal_ray_gonopodium", "aesthetics",
         "A narrow bundle of three modified anal rays with a basal pivot and small terminal features.",
         ["mosquitofish", "gonopodium", "anal rays", "segmentation", "fin"],
         {**_SIZE, "rotate": (0., 1., .18)}, modified_anal_ray_gonopodium,
         orient="native", symmetry="center", hint={"u": .47, "theta": -90.}, bones=_GONOPODIUM_BONES),
]
