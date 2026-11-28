"""Isolated invertebrate anatomy in metres, with +Y dorsal and +Z distal."""

from math import atan2, cos, pi, radians, sin, tau

from scipy.interpolate import PchipInterpolator

from ..kit import RIGHT, UP, V, lerp, rot
from . import Part
from .research_locomotion import _closed_rings


def _sized(sculpt):
    def build(g, p):
        g.setup(finish="direct")
        sculpt(g, p)
        for primitive in g.current.prims:
            primitive.v = [vertex * p["size"] for vertex in primitive.v]
    return build


def _cup(g, x, y, z, radius):
    rings = []
    for thickness, height in ((.67, -.24), (.91, .18), (1., .44), (.76, .53), (.55, .27), (.28, .20)):
        rings.append([
            V(x + radius * thickness * cos(tau * i / 12), y + radius * height,
              z + radius * thickness * sin(tau * i / 12))
            for i in range(12)
        ])
    _closed_rings(g, rings)


_CLUB_STATIONS = (
    (-.004, .0030, .0031), (.025, .0030, .0032), (.052, .0028, .0032),
    (.072, .0032, .0029), (.079, .0061, .0024), (.088, .0080, .0026),
    (.105, .0070, .0025), (.113, .0046, .0022), (.121, .0034, .0019),
    (.135, .0027, .0016), (.144, .0018, .0014), (.149, .0006, .0006),
)
_CLUB_WIDTH = PchipInterpolator([z for z, _, _ in _CLUB_STATIONS], [x for _, x, _ in _CLUB_STATIONS])
_CLUB_DEPTH = PchipInterpolator([z for z, _, _ in _CLUB_STATIONS], [y for _, _, y in _CLUB_STATIONS])


def _club_height(z):
    return .004 * max(0., (z - .100) / .049) ** 2


def distal_tentacle_club(g, p):
    g.slot("club")
    g.loft([V(0, _club_height(z), z) for z, _, _ in _CLUB_STATIONS],
           [(x * p["breadth"], y) for _, x, y in _CLUB_STATIONS],
           sides=24, density=4, exponent=.79)
    g.slot("suckers")
    for index, column in enumerate((-.72, -.24, .24, .72)):
        for row in range(13):
            z = .083 + row * .0048 + index * .0005
            radial = float(_CLUB_WIDTH(z))
            taper = min(1., radial / .006)
            radius = taper * (.00185 if abs(column) < .5 else .00087)
            dorsal = float(_CLUB_DEPTH(z)) * (1 - abs(column) ** (2 / .79)) ** (.79 / 2)
            x = radial * column * p["breadth"]
            _cup(g, x, _club_height(z) + dorsal - .00017, z, radius)


def mantle_ribbon_fin(g, p):
    # +X is the free edge and -X embeds under the host flank.
    rings = []
    for row in range(51):
        t = row / 50
        envelope = max(.012, sin(pi * t) ** .69) * (1.07 - .20 * t)
        width = .035 * envelope * p["breadth"]
        stiffness = .00185 * envelope + .0004
        phase = tau * (2.15 * t - p["phase"])
        ring = []
        for step in range(20):
            theta = tau * step / 20
            across = .5 + .5 * cos(theta)
            x = -.004 + (width + .004) * across
            y = across ** 1.6 * envelope * .015 * sin(phase)
            y += stiffness * (1.17 - .54 * across) * sin(theta)
            ring.append(V(x, y, lerp(-.109, .110, t)))
        rings.append(ring)
    g.slot("ribbon")
    _closed_rings(g, rings)


# A hinge-centered outline of one great scallop valve. The two auricles
# project laterally from the umbo before the rounded ventral fan.
_VALVE_EDGE = (
    (-.023, -.001), (0, -.004), (.018, -.001), (.026, .000), (.027, .013),
    (.023, .017), (.039, .025), (.048, .037), (.054, .053), (.049, .070),
    (.037, .083), (.018, .092), (0, .095), (-.018, .091), (-.036, .082),
    (-.049, .068), (-.053, .053), (-.048, .038), (-.039, .025), (-.025, .016),
    (-.027, .012), (-.026, .001),
)
_VALVE_PLAN = PchipInterpolator(range(len(_VALVE_EDGE) + 1), _VALVE_EDGE + _VALVE_EDGE[:1])


def _valve(g, p, side, depth):
    opening = rot(RIGHT, radians(-side * p["gape"] / 2))
    rings = []
    for exterior, stations in ((True, range(1, 19)), (False, range(18, 0, -1))):
        for station in stations:
            t = sin(pi * station / 36)
            ring = []
            for edge in range(110):
                x, z = _VALVE_PLAN(edge / 5)
                z = float(lerp(.045, z, t))
                x = float(x) * t
                phase = 32.0 * atan2(x, max(.010, z))
                rib = .0019 * (.5 + .5 * cos(phase)) * t ** 1.6 * min(1., max(0., (z - .015) / .027))
                y = .0009 + depth * (1 - t * t) ** .86 + rib
                y += .00064 if exterior else -.00064
                ring.append(opening @ V(x, side * y, z + .005) - V(0, 0, .005))
            rings.append(ring)
    _closed_rings(g, rings)


def hinged_bivalve_valves(g, p):
    for side, depth, slot in ((1, .006, "flat_valve"), (-1, .019, "cupped_valve")):
        g.slot(slot)
        _valve(g, p, side, depth)


def _bridge(faces, a, b):
    for i in range(len(a)):
        j = (i + 1) % len(a)
        faces.append((a[i], a[j], b[j], b[i]))


def fused_double_siphon(g, p):
    # The annular lip of each half attaches to a shared midline. Internal
    # channels are only modeled to a short recess behind the visible openings.
    outer = []
    vertices = []
    faces = []
    arc = 20
    length = .186 * p["extension"]

    def ring(points):
        start = len(vertices)
        vertices.extend(points)
        return tuple(range(start, len(vertices)))

    for section in range(31):
        t = section / 30
        width = .022 * lerp(1., .80, t) * (1 + .036 * sin(tau * t * 7.4))
        height = .014 * lerp(1.05, .93, t) * (1 + .050 * sin(tau * t * 7.4 + .35))
        x = p["bend"] * t * t * .038
        z = lerp(-.006, length, t)
        outer.append(ring(V(x + width * sin(pi * i / arc), height * cos(pi * i / arc), z)
                          for i in range(2 * arc)))
    faces.append(tuple(reversed(outer[0])))
    for base, tip in zip(outer, outer[1:]):
        _bridge(faces, base, tip)
    upper, lower = (vertices[outer[-1][i]] for i in (0, arc))
    midline = ring(lower.lerp(upper, (i + 1) / 9) for i in range(8))
    for side in (1, -1):
        if side > 0:
            lip = outer[-1][:arc + 1] + midline
        else:
            lip = outer[-1][arc:] + outer[-1][:1] + tuple(reversed(midline))
        radius = .0067 if side > 0 else .0054
        socket = V(upper.x + side * .00825, 0, length)
        base = lip
        for shrink, depth in ((1.08, .0011), (.96, .00035), (.89, -.0027), (.83, -.016)):
            points = []
            for edge in lip:
                direction = (vertices[edge] - socket).normalized()
                points.append(socket + V(radius * shrink * direction.x,
                                         radius * shrink * 1.36 * direction.y, depth))
            inner = ring(points)
            _bridge(faces, base, inner)
            base = inner
        faces.append(base)
    # The outer loop proceeds clockwise when viewed from its openings.
    g.slot("sheath")
    g._add(vertices, [tuple(reversed(face)) for face in faces])


def _vertical_ring(y, radius, offset=0., tilt=0., sides=24):
    points = []
    for i in range(sides):
        angle = tau * i / sides
        x = radius * cos(angle)
        points.append(V(x, y + x * tilt, offset + radius * sin(angle) * .92))
    return points


def retractile_lamellate_rhinophore(g, p):
    g.slot("sheath")
    _closed_rings(g, [_vertical_ring(y, radius) for y, radius in (
        (-.004, .0087), (-.001, .0089), (.003, .0074), (.006, .0062),
        (.007, .0053), (.0059, .0047), (-.001, .00455), (-.003, .0021),
    )])
    deploy = p["extension"]
    g.slot("rhinophore")
    rings = [_vertical_ring(-.005, .0030)]
    rings.append(_vertical_ring(.005 * deploy - .006, .00305))
    for lamella in range(20):
        t = lamella / 20
        scale = (1.0 - .69 * t) * (.94 + .06 * cos(pi * t))
        for step, radius in ((.03, .0029), (.28, .00431), (.49, .00446), (.80, .00325)):
            y = .004 + .026 * (lamella + step) / 20
            y = (y + .006) * deploy - .006
            rings.append(_vertical_ring(y, radius * scale, offset=.0008 * t * t,
                                        tilt=.12 * deploy))
    rings.append(_vertical_ring(.037 * deploy - .006, .00115, offset=.00083))
    _closed_rings(g, rings)


def biramous_chaetal_parapodium(g, p):
    spread = p["spread"]
    for side in (1, -1):
        y = .010 * side * spread
        outer = .044 if side > 0 else .038
        g.slot("rami")
        g.loft([V(-.004, side * .002, 0), V(.012, y * .61, .0015),
                V(.031, y, .0028), V(outer, y * .96, .005)],
               [(.009, .0054), (.008, .006), (.006, .0040), (.0021, .0022)], sides=16)
        g.loft([V(.012, y * .69, -.004), V(.028, y * 1.40, -.003),
                V(outer * 1.24, y * 1.66, -.006)],
               [(.003, .0027), (.0032, .0035), (.00055, .00056)], sides=12)
        g.slot("chaetae")
        for index in range(10):
            s = index / 9
            seat = V(outer - .006 + .001 * s, y + side * .0017 * (s - .55), .001 + .008 * s)
            tip = seat + V(.016 + .010 * sin(pi * s), side * (.008 * s - .001), .014 * (s - .42))
            mid = seat.lerp(tip, .57) + UP * side * .0014
            g.loft([seat, mid, tip], [.00060, .00046, .00015], sides=8, density=2)


_SIZE = {"size": (.65, 1.50, 1.)}
PARTS = [
    Part("distal_tentacle_club", "feeding", "Squid strike stalk with a broadened distal sucker club.",
         ["squid", "cephalopod", "tentacle", "club", "suckers"], {**_SIZE, "breadth": (.84, 1.22, 1.)},
         _sized(distal_tentacle_club), orient="native", host="body"),
    Part("mantle_ribbon_fin", "locomotion", "Cuttlefish lateral mantle ribbon with a continuous root and traveling wave.",
         ["cuttlefish", "cephalopod", "mantle", "fin", "wave"], {**_SIZE, "breadth": (.74, 1.28, 1.), "phase": (0., 1., .20)},
         _sized(mantle_ribbon_fin), orient="native", host="body"),
    Part("hinged_bivalve_valves", "aesthetics", "Paired scallop valves with a shared hinge, auricles and unequal depth.",
         ["scallop", "bivalve", "shell", "hinge", "valve"], {**_SIZE, "gape": (0., 95., 15.)},
         _sized(hinged_bivalve_valves), orient="native", host="body", symmetry="center"),
    Part("fused_double_siphon", "feeding", "Fused bivalve siphon ending in two separate ports and a shared bridge.",
         ["geoduck", "bivalve", "siphon", "intake", "excurrent"], {**_SIZE, "extension": (.56, 1.25, 1.), "bend": (-.65, .85, .26)},
         _sized(fused_double_siphon), orient="native", host="body", symmetry="center"),
    Part("retractile_lamellate_rhinophore", "sensory", "Retractile lamellate nudibranch sensory stalk in a raised sheath.",
         ["nudibranch", "rhinophore", "dorid", "lamellae", "sheath"], {**_SIZE, "extension": (.32, 1., 1.)},
         _sized(retractile_lamellate_rhinophore), orient="native", host="body"),
    Part("biramous_chaetal_parapodium", "locomotion", "Divided ragworm parapodium with two rami and separate chaetal fans.",
         ["annelid", "ragworm", "parapodium", "chaetae", "biramous"], {**_SIZE, "spread": (.78, 1.26, 1.)},
         _sized(biramous_chaetal_parapodium), orient="native", host="body"),
]


TRAITS = {
    "distal_tentacle_club": {
        "shape": "narrow strike stalk broadening into a flattened distal club",
        "construction": "deformable",
    },
    "mantle_ribbon_fin": {
        "shape": "long tapering mantle ribbon with a continuous lateral seam",
        "function": "swim",
        "construction": "deformable",
    },
    "hinged_bivalve_valves": {
        "shape": "opposed auriculate fan shells with an unequal bowl depth",
        "function": "protect",
    },
    "fused_double_siphon": {
        "shape": "shared muscular sheath with two recessed openings",
        "construction": "deformable",
    },
    "retractile_lamellate_rhinophore": {
        "shape": "tapered pleated sensory stem seated inside a round sheath",
        "construction": "deformable",
    },
    "biramous_chaetal_parapodium": {
        "shape": "two fleshy rami with separate terminal bristle fans",
        "function": "support",
        "construction": "deformable",
    },
}
