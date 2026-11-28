"""Additional isolated vertebrate head attachments under inspection."""

from math import cos, exp, pi, sin

from ..kit import BACK, RIGHT, UP, V
from . import Part
from .anatomy import _loft
from .research_aesthetics import _closed_sections

SIZE = (.65, 1.65, 1.)
FRONT = {"u": .96, "theta": -90}
SIDE = {"u": .91, "theta": 0}


def lateral_headfoil_sensor_seats(g, p):
    """Continuous transversely swept sensor housing with anterior indentations."""
    scale, spread, notch = p["size"], p["spread"], p["notch"]
    # Lateral positions, leading and rear edges, and dorsoventral half-heights.
    half = ((0, .105, -.093, .032), (.025, .113, -.087, .032), (.060, .130, -.074, .030),
            (.105, .124, -.053, .026), (.148, .107, -.038, .022), (.178, .095, -.040, .019),
            (.199, .097, -.047, .015), (.228, .080, -.052, .014), (.249, .056, -.041, .013),
            (.260, .034, -.031, .011), (.265, .019, -.021, .008), (.268, .008, -.009, .004))
    stations = [(-x, front, rear, depth) for x, front, rear, depth in reversed(half[1:])] + list(half)
    angles = [pi / 2 + 2 * pi * i / 56 for i in range(56)]
    rings = []
    for x, front, rear, depth in stations:
        center = (front + rear) / 2
        chord = (front - rear) / 2
        mid_notch = .017 * (notch - 1) * exp(-(x / .029) ** 2)
        nare_seat = .007 * exp(-((abs(x) - .208) / .026) ** 2)
        rings.append([(x * spread,
                       depth * sin(a) + (.002 - .004 * abs(x) / .268),
                       center + chord * cos(a) - (nare_seat + mid_notch) * max(0., cos(a)) ** 4)
                      for a in angles])
    g.setup(finish="subsurf_low")
    _closed_sections(g, rings, (-.270 * spread, 0, 0), (.270 * spread, 0, 0), scale)
    g.slot("eyes")
    g.setup(slot_finish={"eyes": "direct"})
    for side in (-1, 1):
        g.oval(V(side * .266 * spread, .001, .009) * scale,
               (.006 * scale, .009 * scale, .010 * scale), segs=24, rings=14)


def immersed_lower_bill_blade(g, p):
    """A thin lower mandible that continues past the upper as a leading blade."""
    scale, reach, gape = p["size"], p["reach"], p["gape"]
    upper = ((-.025, .022, .025, .020), (.008, .025, .023, .019), (.058, .024, .018, .015),
             (.117, .020, .011, .013), (.165, .016, .007, .009), (.199, .010, .0034, .006),
             (.211, .006, .0016, .002))
    lower = ((-.024, -.018, .026, .019), (.008, -.021, .023, .016), (.064, -.018, .015, .014),
             (.123, -.015, .008, .013), (.165, -.011, .0048, .012), (.213, -.006, .0035, .010),
             (.252, -.003, .0026, .008), (.277, .000, .0011, .002))
    g.pivots["jaw"] = V(0, -.018, -.024) * scale
    for bone, stations in (("self", upper), ("jaw", lower)):
        g.use(bone)
        g.setup(finish="direct")
        points = []
        for z, y, _, _ in stations:
            if bone == "jaw":
                z += max(0, z - .1) * (reach - 1)
                y -= gape * max(0, z + .025)
            points.append((0, y, z))
        _loft(g, scale, points, [(x, y) for _, _, x, y in stations],
              up=UP, sides=28, density=5, exponent=.73)


def waterline_split_eye(g, p):
    """One ocular surface with asymmetrical upper and lower apertures."""
    scale, split, flatten = p["size"], p["split_height"], p["flatten"]
    g.setup(finish="direct")
    g.oval(V(0, 0, -.009) * scale, (.053 * scale, .050 * scale, .042 * scale),
           segs=84, rings=45)
    for vertex in g.prims[-1].v:
        x, y, z = vertex / scale
        if z <= .005:
            continue
        surface_weight = min(1, (z - .005) / .021)
        decentered_x = x + .13 * y
        upper = exp(-((decentered_x / .037) ** 2 + ((y - split - .018) / .011) ** 2))
        lower = exp(-((decentered_x / .028) ** 2 + ((y - split + .016) / .008) ** 2))
        separator = exp(-((y - split) / .0038) ** 2 - (x / .041) ** 4)
        aperture = exp(-((decentered_x / .022) ** 4 + ((y - split - .018) / .006) ** 4))
        aperture += exp(-((decentered_x / .014) ** 4 + ((y - split + .016) / .0048) ** 4))
        vertex.z += scale * surface_weight * (.009 * upper + .012 * lower + .004 * separator
                                              - flatten * .008 * aperture)


def nasal_tactile_rosette(g, p):
    """Eleven paired fleshy sampling rays around a two-nostril center."""
    scale, spread, contact = p["size"], p["spread"], p["contact"]
    g.setup(finish="direct")
    g.oval(V(0, .004, -.010) * scale, (.038 * scale, .032 * scale, .034 * scale), segs=72, rings=44)
    for vertex in g.prims[-1].v:
        x, y, z = vertex / scale
        if z <= .004:
            continue
        depression = exp(-((abs(x) - .0135) / .0065) ** 4 - ((y - .007) / .009) ** 4)
        vertex.z -= .0105 * scale * min(1, (z - .004) / .015) * depression
    lengths = (.054, .074, .084, .088, .087, .079, .063, .052, .038, .031, .024)
    for side in (-1, 1):
        for index, radius in enumerate(lengths):
            a = (.074 + index * .087) * pi
            dx, dy = side * sin(a), cos(a)
            # The last pair projects near the center below the nares.
            base = V(dx * .030, dy * .024 + .004, .001)
            ray = V(dx, dy, 0)
            tip = base + ray * (spread * radius)
            tip.z += (.025 + .21 * radius) * contact
            tip.x += side * (.0015 if index < 8 else .004)
            mid = base.lerp(tip, .50)
            mid.z -= .010 * contact
            width = .0068 + .040 * radius
            _loft(g, scale, [base, base.lerp(mid, .38), mid, mid.lerp(tip, .55), tip],
                  [(width, .64 * width), (.97 * width, .72 * width), (.82 * width, .61 * width),
                   (.64 * width, .51 * width), (.18 * width, .16 * width)],
                  up=BACK, sides=15, density=4, exponent=.81)


def paired_dorsal_nasal_tubes(g, p):
    """Joined raised housing around two forward-open nasal passages."""
    scale, length, openness = p["size"], p["length"], p["openness"]
    # March the two adjacent ducts from an embedded heel to each free rim.
    # The inner wall continues almost to the base of the saddle.
    g.setup(finish="direct")
    stations = ((-.061, -.001, .005, .005, .007), (-.050, .008, .007, .011, .012),
                (-.033, .014, .010, .014, .017), (-.011, .016, .011, .014, .016),
                (.012, .014, .011, .013, .015), (.027, .012, .011, .012, .013),
                (.030, .012, .011, .010, .011), (.028, .012, .011, .007, .008),
                (.021, .012, .011, .007, .008), (.005, .012, .010, .006, .007),
                (-.013, .010, .009, .005, .006), (-.028, .010, .008, .002, .002))
    angles = [pi / 2 - 2 * pi * i / 34 for i in range(34)]
    for side in (-1, 1):
        rings = []
        for index, (z, y, center, x_rad, y_rad) in enumerate(stations):
            factor = openness if index >= 7 else 1
            rings.append([(side * center + factor * x_rad * cos(a), y + factor * y_rad * sin(a), z * length)
                          for a in angles])
        _closed_sections(g, rings, (side * .005, -.004, -.067 * length),
                         (side * .008, .010, -.030 * length), scale)


PARTS = [
    Part("lateral_headfoil_sensor_seats", "sensory", "Continuous flattened cranial crossbar with lateral eye seats.",
         ["hammerhead", "cephalofoil", "naris", "vision"],
         {"size": SIZE, "spread": (.8, 1.28, 1.), "notch": (.65, 1.35, 1.)},
         lateral_headfoil_sensor_seats, orient="native", hint=FRONT, symmetry="center"),
    Part("immersed_lower_bill_blade", "feeding", "Narrow lower bill projects ahead of the upper bill during skimming.",
         ["skimmer", "surface", "mandible", "blade"],
         {"size": SIZE, "reach": (.77, 1.25, 1.), "gape": (.045, .30, .125)},
         immersed_lower_bill_blade, orient="native", hint=FRONT, symmetry="center",
         bones=[{"name": "jaw", "pivot": (0, -.018, -.024), "axis": (1, 0, 0), "angle": 12}]),
    Part("waterline_split_eye", "sensory", "Single globular orbit with two asymmetrical optical apertures.",
         ["four-eyed fish", "eye", "waterline", "vision"],
         {"size": SIZE, "split_height": (-.005, .006, 0.0), "flatten": (.80, 1.18, 1.)},
         waterline_split_eye, orient="forward", mirror=True, hint=SIDE, symmetry="pair"),
    Part("nasal_tactile_rosette", "sensory", "Twenty-two fleshy facial rays surrounding paired nares.",
         ["star-nosed mole", "rosette", "rhinarium", "tactile sensing"],
         {"size": SIZE, "spread": (.76, 1.20, 1.), "contact": (.65, 1.30, 1.)},
         nasal_tactile_rosette, orient="forward", hint=FRONT, symmetry="center"),
    Part("paired_dorsal_nasal_tubes", "sensory", "Raised nasal housing with paired forward-facing duct entrances.",
         ["fulmar", "tubenose", "nasal tubes", "olfaction"],
         {"size": SIZE, "length": (.76, 1.25, 1.), "openness": (.66, 1.18, 1.)},
         paired_dorsal_nasal_tubes, orient="native", hint={"u": .97, "theta": 90}, symmetry="center"),
]
TRAITS = {
    "lateral_headfoil_sensor_seats": {"function": "sense", "construction": "rigid", "shape": "continuous transverse cranial crossbar"},
    "immersed_lower_bill_blade": {"function": "feed", "construction": "rigid", "shape": "thin extended lower jaw blade"},
    "waterline_split_eye": {"function": "sense", "construction": "rigid", "shape": "two optical apertures on one globe"},
    "nasal_tactile_rosette": {"function": "sense", "construction": "deformable", "shape": "twenty-two circumoral nasal rays"},
    "paired_dorsal_nasal_tubes": {"function": "sense", "construction": "rigid", "shape": "paired tubes across dorsal bill saddle"},
}
