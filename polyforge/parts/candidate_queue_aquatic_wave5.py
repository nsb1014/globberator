"""Local brood structures, axial paddles and dermal surface anatomy."""

from math import cos, exp, pi, radians, sin, tau

from mathutils import Matrix
from scipy.interpolate import PchipInterpolator

from ..kit import RIGHT, UP, V, lerp, smoothstep
from . import Part
from .research_locomotion import _closed_rings


def closing_ventral_brood_folds(g, p):
    """Paired skin folds ending in inward-turned lips along a ventral seam."""
    size, opening, fill = p["size"], p["opening"], p["fill"]
    g.setup(finish="direct")
    for side in (-1, 1):
        rings = []
        for index in range(65):
            t = index / 64
            shape = .08 + .92 * sin(pi * t)**.52
            width = .0165 * shape
            depth = (.013 + .007 * fill) * shape
            root_x = .0035 + .015 * shape
            closure = .00028 + opening * width * .70
            seam = [
                (root_x, .0014), (root_x + .0020, -.0015),
                (root_x + (.0015 + .115 * opening * width) * shape, -depth * .42),
                (lerp(root_x, closure, .42), -depth * .86),
                (lerp(root_x, closure, .80), -depth * .99),
                (closure + .0014 * shape, -depth),
                (closure, -depth * .92), (closure + .00045 * shape, -depth * .72),
                (closure + .0018 * shape, -depth * .70),
                (closure + .0022 * shape, -depth * .83),
                (lerp(root_x, closure, .75), -depth * .85),
                (lerp(root_x, closure, .26), -depth * .60),
                (root_x - .00165, -depth * .29), (root_x - .00195, .0004),
            ]
            z = lerp(.084, -.084, t)
            rings.append([V(side * x, y, z) * size for x, y in seam])
        _closed_rings(g, rings)


_SNAKE_STATIONS = PchipInterpolator((0., .08, .20, .32, .43, .56, .69, .81, .91, 1.), (
    (.018, .014, -.002), (.017, .014, -.002), (.014, .0147, -.002),
    (.011, .0149, -.003), (.008, .0159, -.004), (.006, .0167, -.0036),
    (.005, .0143, -.0038), (.0038, .0107, -.0035), (.0024, .0062, -.0026),
    (.0006, .0009, -.001),
))


def solid_axial_swim_paddle(g, p):
    """A one-piece compressed tail with no seam between root and paddle."""
    size, bend = p["size"], p["bend"]
    g.setup(finish="direct")
    rings = []
    for i in range(75):
        t = i / 74
        width, height, y = _SNAKE_STATIONS(t)
        theta = bend * 1.15 * t**1.7
        z = -.132 * t * (1 - .18 * bend**2 * t**2)
        x = .073 * bend * t**2.25
        lateral = V(cos(theta), 0, sin(theta))
        ring = []
        for j in range(40):
            a = tau * j / 40
            # The two faces are broad, with a small thickness towards the top and bottom.
            transverse = width * sin(a) * (1. - .36 * t * abs(cos(a))**2)
            point = V(x, y + height * cos(a), z) + lateral * transverse
            ring.append(point * size)
        rings.append(ring)
    _closed_rings(g, rings)


def _inflated_flank(x, z, inflation):
    width = .094 * (1 + .25 * inflation)
    length = .088 * (1 + .18 * inflation)
    y = .022 * inflation - (.007 + .015 * inflation) * ((x / width)**2 + (z / length)**2)
    return V(x, y, z)


def pressure_erectile_dermal_spine_field(g, p):
    """A skin coupon carrying recessed roots that stand with local expansion."""
    size, inflation = p["size"], p["inflation"]
    g.setup(finish="direct")
    rings = []
    for index in range(32):
        t = index / 31
        z = lerp(.083, -.084, t) * (1 + .18 * inflation)
        width = .094 * (1 + .25 * inflation) * (.85 + .15 * sin(pi * t))
        ring = []
        for i in range(40):
            a = tau * i / 40
            shift = .0035 * (sin(a) - 1)
            surface = _inflated_flank(width * cos(a), z, inflation)
            ring.append((surface + UP * shift) * size)
        rings.append(ring)
    _closed_rings(g, rings)

    for row in range(5):
        for column in range(7):
            x = (.023 * (column - 3) + .006 * (row % 2)) * (1 + .25 * inflation)
            z = .029 * (2 - row) * (1 + .18 * inflation)
            root = _inflated_flank(x, z, inflation)
            side = _inflated_flank(x + .003, z, inflation) - root
            caudad = _inflated_flank(x, z - .003, inflation) - root
            normal = side.cross(caudad).normalized()
            rise = radians(13 + 65 * inflation)
            fan = (caudad.normalized() + RIGHT * (.055 * (column - 3))).normalized()
            direction = (fan * cos(rise) + normal * sin(rise)).normalized()
            length = .023 + .006 * cos(1.34 * row + .74 * column)
            heel = root - normal * .0027
            base = root + direction * .0034
            shaft = root + direction * (length * .51)
            tip = root + direction * length + normal * length * .08
            g.loft([point * size for point in (heel, base, shaft, tip)],
                   [radius * size for radius in (.0026, .00225, .00120, .00024)],
                   sides=11, density=4, up=RIGHT)


_CROC_TAIL_ROWS = (
    (.098, .036, .020), (.065, .032, .022), (.032, .027, .024),
    (.001, .019, .022), (-.030, 0., .026), (-.061, 0., .023),
    (-.091, 0., .019), (-.117, 0., .015),
)


def paired_to_single_caudal_scute_crest(g, p):
    """Short crocodilian scute run carrying the bilateral-to-median transition."""
    size, bend = p["size"], p["bend"]
    g.setup(finish="subsurf_low")
    for z, half_width, height in _CROC_TAIL_ROWS:
        sides = (-1, 1) if half_width else (0,)
        for side in sides:
            t = (.098 - z) / .215
            center = V(half_width * side + bend * .046 * t**2, .027 - .018 * t, z)
            n = V(side * .32, 1, .08)
            a = V(1, -side * .14, bend * .33 * t).normalized()
            f = a.cross(n).normalized()
            points = [
                center + f * .014 - n * .003,
                center + f * .012 + n * height * .19,
                center + f * .004 + n * height * .88,
                center - f * .003 + n * height,
                center - f * .008 + n * height * .68,
                center - f * .014 + n * height * .24,
                center - f * .017 - n * .002,
            ]
            g.slab([point * size for point in points], a, .009 * size, bulge=.22)


def pedicled_ribbed_denticle_field(g, p):
    """Magnified flank denticles carrying three longitudinal crown ribs apiece."""
    size, tilt = p["size"], p["tilt"]
    rotation = Matrix.Rotation(radians(29 * tilt), 3, "X")
    hinge = V(0, .003, -.0025)
    g.setup(finish="direct")
    for row in range(4):
        for col in range(5):
            x = .017 * (col - 2) + .008 * (row % 2)
            z = .019 * (1.5 - row)
            y = -.2 * (x*x + z*z)
            root = V(x, y, z)
            g.loft([(root + offset) * size for offset in (
                V(0, -.003, 0), V(0, -.0017, 0), V(0, .0013, -.0011), V(0, .0028, -.0025),
            )], [radius * size for radius in (.0038, .0044, .0018, .0025)], sides=14, density=3)

            rings = []
            for longitudinal, width, depth in (
                (-.0052, .0014, .0010), (-.0040, .0036, .0014),
                (-.0015, .0061, .0014), (.0020, .0071, .00135),
                (.0060, .0069, .00105), (.0091, .0054, .00067),
                (.0118, .0031, .00035), (.0131, .00078, .00022),
            ):
                ring = []
                for j in range(44):
                    a = tau * j / 44
                    lateral, vertical = width * cos(a), sin(a)
                    rib = sum(exp(-((lateral - offset * width) / .00065)**2) for offset in (-.54, 0., .54))
                    rib *= .00136 * max(0., vertical) * smoothstep(.001, .0045, width)
                    crown = V(lateral, .0030 + depth * vertical + rib, -longitudinal)
                    ring.append((root + hinge + rotation @ (crown - hinge)) * size)
                rings.append(ring)
            _closed_rings(g, rings)


_SIZE = {"size": (.60, 1.60, 1.)}
PARTS = [
    Part("closing_ventral_brood_folds", "aesthetics",
         "Paired ventral pipefish tissue folds forming an inward-lipped longitudinal closure.",
         ["pipefish", "brood", "ventral", "pouch", "fold"],
         {**_SIZE, "opening": (0., 1., .15), "fill": (0., 1., .65)}, closing_ventral_brood_folds,
         orient="native", symmetry="center", hint={"u": .36, "theta": -90.}),
    Part("solid_axial_swim_paddle", "locomotion",
         "One continuous sea snake tail with a round root and flattened axial paddle.",
         ["sea snake", "tail", "paddle", "lateral", "keel"],
         {**_SIZE, "bend": (-1., 1., .12)}, solid_axial_swim_paddle,
         orient="native", symmetry="center", hint={"u": .02, "theta": 0.}),
    Part("pressure_erectile_dermal_spine_field", "aesthetics",
         "A local porcupinefish flank sample with skin-linked changes in dermal spine stance.",
         ["porcupinefish", "dermal", "skin", "spines", "inflation"],
         {**_SIZE, "inflation": (0., 1., .75)}, pressure_erectile_dermal_spine_field,
         orient="native", symmetry="center", hint={"u": .48, "theta": 90.}),
    Part("paired_to_single_caudal_scute_crest", "aesthetics",
         "Separate crocodilian dorsal scutes moving from two lateral ranks into one median crest.",
         ["crocodile", "caudal", "scute", "keel", "transition"],
         {**_SIZE, "bend": (-1., 1., 0.)}, paired_to_single_caudal_scute_crest,
         orient="native", symmetry="center", hint={"u": .22, "theta": 90.}),
    Part("pedicled_ribbed_denticle_field", "aesthetics",
         "Magnified shark skin denticles with distinct stalks and three-ribbed swept crowns.",
         ["mako", "denticle", "dermal", "riblet", "placoid"],
         {**_SIZE, "tilt": (0., 1., .20)}, pedicled_ribbed_denticle_field,
         orient="native", symmetry="center", hint={"u": .57, "theta": 90.}),
]
