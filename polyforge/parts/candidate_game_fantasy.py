"""Original fantasy parts using biological references for construction details."""

from math import cos, pi, sin, tau

from scipy.interpolate import PchipInterpolator

from ..kit import V, smoothstep
from . import Part
from .research_locomotion import _closed_rings


_SIZE = (.60, 1.60, 1.)


def unicorn_spiral_horn(g, p):
    """A straight horn shaft with one continuous raised helix."""
    g.setup(finish="direct")
    size, length = p["size"], p["length"]
    rings = []
    for i in range(121):
        t = i / 120
        shaft = .029 * (1. - t)**.92 + .00065 + .004 * (1. - smoothstep(.025, .13, t))
        fade = smoothstep(.03, .12, t) * (1. - smoothstep(.83, .99, t))
        ring = []
        for j in range(36):
            a = tau * j / 36
            ridge = (.5 + .5 * cos(a + tau * 5. * t))**4
            r = shaft * (1. + .39 * p["relief"] * fade * ridge)
            ring.append(V(r * cos(a), -.021 + .272 * t * length,
                          r * sin(a) + .042 * t * t * length) * size)
        rings.append(ring)
    _closed_rings(g, rings)


_TAIL_T = (0., .12, .30, .43, .52, .60, .70, .82, .93, 1.)
_TAIL_PROFILE = PchipInterpolator(
    _TAIL_T, ((.017, .015), (.015, .013), (.012, .010), (.020, .011),
              (.049, .012), (.055, .012), (.044, .010), (.031, .008),
              (.014, .004), (.0013, .0010)),
)


def wyvern_tail_spade(g, p):
    """A thick terminal tail vane with a narrow solid shaft and beveled shoulders."""
    g.setup(finish="direct")
    rings = []
    for i in range(61):
        t = i / 60
        half_width, half_depth = _TAIL_PROFILE(t)
        blade = smoothstep(.34, .58, t)
        width = half_width * (1. + (p["spread"] - 1.) * blade)
        curve = p["curve"] * .024 * sin(3.3 * pi * t) * (1. - smoothstep(.37, .52, t))
        shoulder = smoothstep(.32, .60, t) * (1. - smoothstep(.61, .87, t))
        scale_relief = .0019 * smoothstep(.03, .11, t) * (1. - smoothstep(.34, .52, t))
        ring = []
        for j in range(40):
            a = tau * j / 40
            across = cos(a)
            setback = .063 * shoulder * across**2
            keel = .0055 * blade * (1. - smoothstep(.86, 1., t)) * (1. - abs(across))**3
            # Stagger shallow scale relief across the cylindrical stalk.
            offset = .0060 * cos(7. * a + 9. * pi * t)
            scale = scale_relief * (.5 + .5 * cos(tau * ((t + offset) * 17. + .5 * sin(5. * a))))**5
            ring.append(V(curve + (width + scale) * across, -.019 + .225 * t - setback,
                          (half_depth * (1. - .43 * blade * across**2) + keel + scale) * sin(a))
                        * p["size"])
        rings.append(ring)
    _closed_rings(g, rings)


_FRILL_REACH = PchipInterpolator(
    (0., .15, .28, .45, .62, .81, 1.),
    (.194, .139, .175, .127, .148, .095, .122),
)
_FRILL_RIBS = (0., .28, .62, 1.)


def dragon_cheek_frill(g, p):
    """Sweep a continuous folded web from a narrow cheek mounting edge."""
    g.setup(finish="direct")
    size, spread = p["size"], p["spread"]
    columns, rows = 49, 31
    area = columns * rows
    points, quads = [], []
    for side in (1., -1.):
        for row in range(rows):
            travel = row / (rows - 1)
            opening = 1. + (spread - 1.) * smoothstep(.04, .86, travel)
            for col in range(columns):
                fan = col / (columns - 1)
                root_x = .038 - .068 * fan
                edge_x = .104 - .194 * fan
                x = (root_x + travel * (edge_x - root_x)) * opening
                reach = float(_FRILL_REACH(fan)) * (.75 + .25 * spread)
                y = -.018 + travel * reach
                ribbed = sum((1. - smoothstep(.005, .101, abs(fan - rib))) for rib in _FRILL_RIBS)
                ridge = .007 * ribbed * (1. - smoothstep(.89, 1., travel))
                rim = .21 + .79 * smoothstep(0., .058, min(travel, 1. - travel, fan, 1. - fan))
                thickness = (.0035 + .005 * (1. - smoothstep(0., .22, travel)) + ridge) * rim
                camber = -.040 * y - .16 * x * x
                points.append(V(x, y, camber + side * thickness) * size)
    for row in range(rows - 1):
        for col in range(columns - 1):
            i = row * columns + col
            quad = (i, i + columns, i + columns + 1, i + 1)
            quads.append(quad)
            quads.append(tuple(index + area for index in reversed(quad)))
    perimeter = [
        *range(columns - 1, -1, -1),
        *range(columns, area, columns),
        *range(area - columns + 1, area),
        *range(area - columns - 1, columns - 1, -columns),
    ]
    for i, first in enumerate(perimeter):
        second = perimeter[(i + 1) % len(perimeter)]
        quads.append((second, first, first + area, second + area))
    g.current._add(points, quads)


PARTS = [
    Part("unicorn_spiral_horn", "aesthetics", "Single tapered forehead horn with one raised spiral.",
         ["unicorn", "alicorn", "helical horn", "fantasy"], {"size": _SIZE, "length": (.68, 1.40, 1.),
                                                             "relief": (.25, 1.20, 1.)},
         unicorn_spiral_horn, symmetry="center", hint={"u": .91, "theta": 90.}),
    Part("wyvern_tail_spade", "aesthetics", "Rounded spade-shaped tail tip with an integrated tapered stalk.",
         ["wyvern", "dragon", "tail tip", "tail vane", "spade"], {"size": _SIZE, "spread": (.65, 1.35, 1.),
                                                                "curve": (-1., 1., .85)},
         wyvern_tail_spade, attach="tip", symmetry="center"),
    Part("dragon_cheek_frill", "aesthetics", "One small swept cheek membrane with radial relief and a single fleshy root.",
         ["dragon", "wyvern", "cheek", "webbed ear", "frill"], {"size": _SIZE, "spread": (.52, 1.25, 1.)},
         dragon_cheek_frill, mirror=True, symmetry="pair", hint={"u": .84, "theta": 30.}),
]
TRAITS = {
    "unicorn_spiral_horn": {"function": "display", "construction": "rigid"},
    "wyvern_tail_spade": {"function": "display", "construction": "rigid"},
    "dragon_cheek_frill": {"function": "display", "construction": "deformable"},
}
