"""Isolated molluscan, cnidarian and tunicate exterior anatomy."""

from math import cos, pi, radians, sin, tau

from ..kit import RIGHT, UP, V, lerp, rot
from . import Part
from .candidate_invertebrate import _sized
from .candidate_queue_invertebrates_wave4 import _closed_band
from .research_locomotion import _closed_rings


def retractile_circumanal_gill_wreath(g, p):
    g.slot("common_pocket")
    rings = []
    for radius, y in ((.022, -.006), (.0228, -.003), (.0222, .0000), (.0204, .0034),
                      (.0185, .0038), (.0174, .0021), (.0165, -.0031), (.0124, -.0048),
                      (.0091, -.0049), (.0069, -.0051), (.0067, -.0067),
                      (.0135, -.0070), (.0210, -.0069)):
        ring = []
        for i in range(56):
            angle = tau * i / 56
            r = radius * (1 + .039 * sin(3 * angle + .1) + .025 * cos(5 * angle))
            ring.append(V(r * cos(angle), y + .00055 * cos(4 * angle), .91 * r * sin(angle)))
        rings.append(ring)
    _closed_band(g, rings)

    g.slot("plumes")
    extension = p["extension"]
    for index in range(9):
        angle = tau * index / 9
        radial = V(cos(angle), 0, sin(angle))
        cross = UP.cross(radial)
        height = (.030 + .006 * sin(index * 1.71)) * extension

        def axis(t):
            root = .0085 + extension * (.011 * sin(pi * t * .86) + .0006 * t)
            return radial * root + UP * (-.005 + height * t) + cross * (.003 * extension * t * t)

        stages = (0., .22, .46, .68, .86, 1.)
        g.loft([axis(t) for t in stages],
               [lerp(.00168, .00038, t) for t in stages], sides=10, up=radial, density=2)
        for step in range(6):
            t = .22 + .117 * step
            base = axis(t)
            width = extension * .009 * sin(pi * t)**.75
            for side in (1, -1):
                reach = cross * (side * width) + UP * (width * .47) + radial * (width * .34)
                mid = base + reach * .48
                end = base + reach
                g.loft([base, mid, end], [.00071, .00045, .00015],
                       sides=8, up=radial, density=2)
                for s in (.52, .74):
                    start = base.lerp(end, s)
                    tip = start + .30 * width * UP + .12 * reach
                    g.loft([start, tip], [.00026, .00010], sides=6, up=radial, density=2)


def open_ended_tusk_shell(g, p):
    rings = []
    rows = range(63)
    for inner, stations in ((False, rows), (True, reversed(rows))):
        for row in stations:
            t = row / 62
            axis_z = -.004 + .103 * t
            x = p["curvature"] * .021 * t**2
            turn = V(1, 0, -.42 * p["curvature"] * t).normalized()
            radius = lerp(.0081, .00155, t) * (1 - .17 * t * (1 - t))
            ridge = lerp(.00059, .00017, t)
            thickness = lerp(.00082, .00037, t)
            ring = []
            for index in range(72):
                angle = tau * index / 72
                rib = ((.5 + .5 * cos(angle * 12 + .17 * t)) ** 3) * ridge
                r = radius - thickness if inner else radius + rib
                local = turn * cos(angle) + UP * sin(angle) * .96
                ring.append(V(x, 0, axis_z) + local * r)
            rings.append(ring)
    g.slot("shell")
    _closed_band(g, rings)


def stalked_jet_nectophore(g, p):
    g.slot("seat")
    g.loft([V(-.0006, 0, -.0016), V(-.0005, .00016, -.0007), V(0, .00025, .00025)],
           [(.00067, .00034), (.00075, .00043), (.00071, .00043)],
           sides=16, up=UP, density=3)
    g.slot("bell_wall")
    rings = []
    for z, width, height, mix in (
        (-.00086, .00074, .00064, 0.), (-.00042, .00105, .00090, 0.),
        (.00015, .00166, .00133, .03), (.00079, .00182, .00143, .12),
        (.00135, .00152, .00124, .33), (.00189, .00128, .00105, .62),
        (.00212, .00103, .00092, .82), (.00224, .00083, .00077, 1.),
        (.00218, .00061, .00061, 1.), (.00197, .00056, .00056, 1.),
        (.00161, .00091, .00081, .84), (.00111, .00104, .00079, .47),
        (.00055, .00092, .00065, .12), (.00017, .00040, .00027, 0.),
    ):
        turn = rot(RIGHT, radians(32 * p["bias"] * mix))
        collar = 1 - p["constriction"] * .49 * max(0., (mix - .45) / .55)
        ring = []
        for i in range(48):
            angle = tau * i / 48
            narrower = 1 - .09 * cos(angle)
            ridge = .000075 * max(0., cos(4 * angle + .62))**10 * (1 - mix)
            rim = turn @ V((width * collar + ridge) * cos(angle) * narrower,
                            (height * collar + ridge) * sin(angle), 0)
            ring.append(rim + V(.00016 * mix, -.00059 * mix + .00029 * p["bias"] * mix, z))
        rings.append(ring)
    _closed_rings(g, rings)


def basal_pedal_attachment_disc(g, p):
    rings = []
    for radius, y, lip in (
        (.0040, -.0218, 0.), (.0137, -.0218, .20), (.0222, -.0217, .74),
        (.0285, -.0215, .97), (.0299, -.02056, 1.), (.0288, -.01731, .95),
        (.0251, -.0142, .77), (.0204, -.0136, .40), (.0153, -.0092, .10),
        (.0122, -.0037, 0.), (.0123, .0008, 0.), (.0116, .0030, 0.),
    ):
        ring = []
        for index in range(88):
            angle = tau * index / 88
            asymmetry = .091 * sin(3 * angle + .7) + .042 * sin(7 * angle + .4)
            r = radius * (1 + asymmetry * lip) * lerp(1., p["spread"], lip)
            raised = p["peel"] * .012 * max(0., cos(angle - .22))**5 * lip**1.9
            ring.append(V(r * cos(angle), y + raised, r * sin(angle) * .91))
        rings.append(ring)
    g.slot("pedal_flange")
    _closed_rings(g, rings)


def _external_port(g, center, tilt, radius, height, opening, folds):
    rotation = rot(RIGHT, radians(tilt))
    rings = []
    for y, width, lobes in (
        (-.18, 1.21, 0.), (.05, 1.20, .10), (.37, 1.17, .34), (.76, 1.04, .80),
        (1.0, 1.0, 1.), (.98, .86, .97), (.88, .57 * opening, .86),
        (.71, .51 * opening, .58), (.36, .48 * opening, .2), (.15, .25 * opening, 0.),
    ):
        ring = []
        for i in range(32):
            angle = tau * i / 32
            crease = cos(folds * angle + .4)
            r = radius * width * (1 + .13 * lobes * crease)
            top_relief = lobes * .122 * crease
            ring.append(center + rotation @ V(r * cos(angle), height * (y + top_relief), .91 * r * sin(angle)))
        rings.append(ring)
    _closed_rings(g, rings)


def staggered_ascidian_siphon_pair(g, p):
    g.slot("tunic_seat")
    g.oval(V(0, -.005, 0), (.021, .0082, .026), segs=36, rings=20)
    g.slot("oral")
    _external_port(g, V(.0049, .0013, .0117), 15., .0080, .0084, p["oral_open"], 4)
    g.slot("atrial")
    _external_port(g, V(-.0058, .0018, -.0088), -11., .0067, .0064, p["atrial_open"], 4)


def shared_colonial_cloacal_rim(g, p):
    g.slot("common_tunic")
    g.oval(V(0, -.0015, 0), (.0235, .0024, .0225), segs=40, rings=18)
    g.slot("common_outlet")
    _external_port(g, V(0, 0, 0), 0., .0056, .0035, p["excurrent"], 6)
    g.slot("zooid_rims")
    for index in range(9):
        a = tau * index / 9
        radial = V(cos(a), 0, sin(a))
        bulge = .00052 * sin(index * 1.91)
        start = radial * .0075 + UP * (bulge + .001)
        middle = radial * .0125 + UP * (bulge + .0013)
        end = radial * .0180 + UP * (bulge + .0014)
        g.loft([start, middle, end],
               [(.00145, .00079), (.00242, .00157), (.00151, .00128)], sides=14, up=UP, density=3)
        _external_port(g, end + UP * .00062, 0., .00145, .00215, 1., 5)


_SIZE = {"size": (.65, 1.50, 1.)}
PARTS = [
    Part("retractile_circumanal_gill_wreath", "locomotion", "Gill plume wreath opening from a common posterior mantle pocket.",
         ["nudibranch", "dorid", "respiration", "gill", "plume"], {**_SIZE, "extension": (.12, 1., 1.)},
         _sized(retractile_circumanal_gill_wreath), orient="native", host="body", symmetry="center"),
    Part("open_ended_tusk_shell", "aesthetics", "A curved longitudinally ribbed scaphopod shell with two open ends.",
         ["scaphopod", "dentalium", "tusk shell", "aperture"], {**_SIZE, "curvature": (.60, 1.35, 1.)},
         _sized(open_ended_tusk_shell), orient="native", host="body", symmetry="center"),
    Part("stalked_jet_nectophore", "locomotion", "A lateral colonial swimming bell with a short seat and adjustable outlet.",
         ["siphonophore", "nanomia", "swim", "nectophore", "velum"], {**_SIZE, "bias": (-1., 1., .18), "constriction": (0., 1., .32)},
         _sized(stalked_jet_nectophore), orient="native", host="body"),
    Part("basal_pedal_attachment_disc", "locomotion", "A sea anemone's uneven broad pedal flange continuous with the base of its column.",
         ["sea anemone", "metridium", "pedal disk", "basal adhesion"], {**_SIZE, "spread": (.72, 1.25, 1.), "peel": (0., 1., .08)},
         _sized(basal_pedal_attachment_disc), orient="native", host="body", symmetry="center"),
    Part("staggered_ascidian_siphon_pair", "feeding", "Two staggered four-lobed ascidian siphons on a common tunic patch.",
         ["ascidian", "tunicate", "styela", "oral siphon", "atrial siphon"], {**_SIZE, "oral_open": (.30, 1.15, 1.), "atrial_open": (.30, 1.15, .83)},
         _sized(staggered_ascidian_siphon_pair), orient="native", host="body", symmetry="center"),
    Part("shared_colonial_cloacal_rim", "feeding", "Common excurrent aperture ringed by individual exterior zooid openings.",
         ["colonial ascidian", "botryllus", "zooid", "cloacal opening"], {**_SIZE, "excurrent": (.60, 1.30, 1.)},
         _sized(shared_colonial_cloacal_rim), orient="native", host="body", symmetry="center"),
]

TRAITS = {
    "retractile_circumanal_gill_wreath": {"shape": "radial pinnate gill plumes seated within one retractile pocket", "function": "breathe", "construction": "deformable"},
    "open_ended_tusk_shell": {"shape": "curved tapering ribbed rigid tube with an open lumen", "function": "protect"},
    "stalked_jet_nectophore": {"shape": "offset muscular bell with a directional circumferential outlet", "function": "swim", "construction": "deformable"},
    "basal_pedal_attachment_disc": {"shape": "wide low soft flange continuous with a column base", "function": "support", "construction": "deformable"},
    "staggered_ascidian_siphon_pair": {"shape": "two separate short four-lobed mouths on a single tunic patch", "construction": "deformable"},
    "shared_colonial_cloacal_rim": {"shape": "single central outlet enclosed by independently seated intake rims", "construction": "deformable"},
}
