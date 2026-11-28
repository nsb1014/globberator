"""Local external fields, tissue folds, and apertures from marine invertebrates."""

from math import cos, pi, sin, tau

from ..kit import RIGHT, UP, V, lerp, smoothstep
from . import Part
from .candidate_invertebrate import _sized
from .candidate_queue_invertebrates_wave4 import _closed_band
from .research_locomotion import _closed_rings


def ceratal_field(g, p):
    g.slot("flank")
    g.oval(V(0, -.004, 0), (.029, .008, .049), segs=32, rings=18)
    g.slot("cerata")
    for fascicle in range(2):
        for row in range(4):
            for column in range(5):
                w = column / 4
                cycle = 2.16 * (1 + fascicle * 7 + row * 5 + column)
                x = lerp(-.013, .019, w)
                z = -.030 + .009 * row + .036 * fascicle + .0042 * sin(pi * w)
                base = V(x, .001 - .004 * (abs(x) / .025)**2 - .0017 * (z / .037)**2, z)
                reach = (.016 + .014 * sin(pi * (.23 + .69 * w))) * (.91 + .09 * sin(cycle))
                curl = p["splay"] * reach
                tail = V(curl * lerp(-.22, .38, w), reach, -.37 * curl + .002 * cos(cycle))
                shoulder = tail * .69 + V(.0019 * cos(cycle), .0011, .0027)
                thickness = .0022 + .00036 * cos(cycle + .77)
                g.loft([base, base + tail * .30, base + shoulder, base + tail],
                       [thickness * .69, thickness, thickness * .71, thickness * .13],
                       sides=12, up=RIGHT, density=3)


def sediment_lunule_test_sector(g, p):
    rings = []
    for fraction, height, lip in (
        (1., -.0037, 0.), (1., .0026, 0.), (.88, .0041, .0), (.69, .0050, .10),
        (.36, .0042, .38), (.18, .0032, .81), (0., .0026, 1.), (0., -.0004, 1.),
        (.09, -.0022, .65), (.34, -.0034, .35), (.67, -.0035, 0.),
    ):
        ring = []
        for j in range(108):
            angle = tau * j / 108
            c, s = cos(angle), sin(angle)
            outside = (abs(c)**4 + abs(s)**4)**.25
            x = lerp(.0092 * p["width"] * c * (1. - .24 * s), .040 * c / outside, fraction)
            z = lerp(.031 * s, .048 * s / outside, fraction)
            aboral = smoothstep(-.0003, .0025, height)
            fade = .80 + .20 * aboral
            x *= lerp(fade, 1., fraction)
            relief = .00040 * cos(25 * angle) * (1 - lip) * aboral
            relief *= max(0., sin(pi * fraction))
            y = height + relief - .0017 * (z / .050) - .0011 * (x / .040)**2
            ring.append(V(x, y, z))
        rings.append(ring)
    g.slot("test_sector")
    _closed_band(g, rings)


def perianal_tooth_ring(g, p):
    g.slot("soft_rim")
    rings = []
    for depth, radius, lips in (
        (-.006, .0133, .09), (-.0025, .0145, .10), (.0014, .0154, .37),
        (.0031, .0135, .45), (.0038, .0102, .71), (.0031, .0073, .86),
        (.0018, .0067, 1.), (-.0025, .0061, .65), (-.006, .0065, .06),
        (-.007, .0095, 0.),
    ):
        ring = []
        for i in range(80):
            angle = tau * i / 80
            scallop = .0016 * lips * cos(5 * angle)
            r = radius + scallop + lips * .0032 * p["opening"]
            ring.append(V(r * cos(angle), r * sin(angle) * .90, depth + .00041 * cos(5 * angle)))
        rings.append(ring)
    _closed_band(g, rings)

    g.slot("tooth_plates")
    for i in range(5):
        a = tau * i / 5
        direction = V(cos(a), sin(a) * .90, 0)
        tangent = V(-sin(a), cos(a), 0)
        root = direction * (.0119 + .0016 * p["opening"])
        g.loft([root + V(0, 0, .0005), root + V(0, 0, .0030),
                direction * (.0071 + .0037 * p["opening"]) + V(0, 0, .0060),
                direction * (.0048 + .0049 * p["opening"]) + V(0, 0, .0055)],
               [(.0027, .0023), (.00245, .00213), (.00148, .00109), (.00072, .00048)],
               sides=16, up=tangent, density=3)


def everting_jaw_crown(g, p):
    g.slot("everted_cuff")
    length = .055 * p["extension"]
    rings = []
    for t, radius, relief in (
        (-.12, .0088, 0.), (0., .0100, 0.), (.10, .0117, .26), (.22, .0139, .64),
        (.43, .0150, .81), (.60, .0144, 1.), (.77, .0124, .92), (.92, .0103, .74),
        (.99, .0098, .38), (1., .0086, 0.), (.96, .0065, 0.), (.89, .0058, 0.),
        (.82, .0045, 0.),
    ):
        ring = []
        for i in range(64):
            a = tau * i / 64
            r = radius + relief * .00031 * cos(21 * a + 4 * t) * sin(19 * t)
            ring.append(V(r * cos(a), r * sin(a) * .86, length * t))
        rings.append(ring)
    _closed_rings(g, rings)

    g.slot("jaw_tips")
    for i in range(4):
        a = tau * (i + .50) / 4
        normal = V(cos(a), sin(a) * .86, 0)
        tangent = V(-sin(a), cos(a), 0)
        radius = p["gape"] * .003
        g.loft([normal * .0074 + V(0, 0, length - .0027),
                normal * (.0110 + radius) + V(0, 0, length + .0035),
                normal * (.0103 + radius) + V(0, 0, length + .0086),
                normal * (.0050 + radius) + V(0, 0, length + .0094)],
               [(.00155, .00125), (.00165, .00122), (.00119, .00086), (.00019, .00022)],
               sides=12, up=tangent, density=4)


def pinnate_polyp_bearing_leaf(g, p):
    rings = []
    for x, base, width, rise in (
        (-.004, -.004, .0070, 0.), (.001, -.003, .0105, 0.),
        (.008, -.002, .0141, .0009), (.016, -.001, .0157, .0018),
        (.025, -.002, .0136, .0033), (.035, -.004, .0091, .0054),
        (.041, -.008, .0058, .0061), (.046, -.012, .0027, .0068), (.048, -.015, .0007, .0074),
    ):
        ring = []
        for i in range(32):
            a = tau * i / 32
            ruffle = max(0., cos(a)) * .0013 * sin(x * 420)
            y = rise + .00145 * sin(a) + ruffle
            z = base + width * cos(a) + ruffle
            ring.append(V(x, y, z))
        rings.append(ring)
    g.slot("leaf")
    _closed_rings(g, rings)
    g.slot("polyp_seats")
    for i, (x, y, z) in enumerate((
        (.005, .0015, .009), (.010, .0021, .012), (.016, .0027, .014),
        (.022, .0031, .0133), (.028, .0040, .010), (.034, .0052, .0054),
        (.040, .0057, -.0006), (.044, .0065, -.0070),
    )):
        center = V(x, y, z)
        stalk = .0060 * p["expansion"] * (1 - .12 * cos(i * 2.1))
        rings = []
        for h, width in ((-.001, .00111), (.0015, .00144), (stalk, .00187),
                          (stalk + .0011, .00194), (stalk + .0014, .00155),
                          (stalk + .00062, .00110), (stalk - .0005, .00062)):
            ring = []
            for col in range(24):
                a = tau * col / 24
                scallop = .00029 * cos(8 * a) * smoothstep(.0009, stalk + .0011, h)
                ring.append(center + V(width * cos(a), h + scallop, width * sin(a) + h * .35))
            rings.append(ring)
        _closed_rings(g, rings)


def eversible_scalid_introvert(g, p):
    g.slot("introvert")
    length = .037 * p["protrusion"]
    rings = []
    for t, radius in ((-.12, .0105), (0., .0117), (.084, .0121), (.17, .0116), (.28, .0101),
                      (.47, .0097), (.64, .0095), (.80, .0082), (.91, .0072), (.98, .0075),
                      (1., .0066), (.98, .0051), (.93, .0045), (.87, .0031)):
        ring = []
        for col in range(80):
            angle = tau * col / 80
            ripple = .0005 * cos(5 * angle + .35) * smoothstep(.75, 1., t)
            r = radius + ripple
            ring.append(V(r * cos(angle), r * sin(angle), length * t))
        rings.append(ring)
    _closed_rings(g, rings)

    g.slot("scalids")
    for row in range(5):
        phase = tau * .025 * (row % 2) / 25
        for i in range(25):
            a = tau * i / 25 + phase
            radial = V(cos(a), sin(a), 0)
            t = .25 + .125 * row
            r = (.0101 if row < 4 else .0087) - .00025 * row
            root = radial * r + V(0, 0, length * t)
            reach = (.00152 + .00012 * row) * (.52 + .48 * p["protrusion"])
            g.loft([root, root + radial * reach * .78 + V(0, 0, -.0003),
                    root + radial * reach * .87 + V(0, 0, -.0010)],
                   [.00043, .00034, .00012], sides=8, up=RIGHT, density=2)


_SIZE = {"size": (.65, 1.50, 1.)}
PARTS = [
    Part("ceratal_field", "aesthetics", "Two staggered fields of tapering separate cerata attached to one nudibranch flank.",
         ["nudibranch", "aeolid", "cerata", "dorsal papillae", "flank"], {**_SIZE, "splay": (.54, 1.28, 1.)},
         _sized(ceratal_field), orient="native", host="body"),
    Part("sediment_lunule_test_sector", "aesthetics", "A flattened rigid sand dollar test sector around one fully open lunule.",
         ["sand dollar", "echinoid", "test", "lunule", "sediment"], {**_SIZE, "width": (.72, 1.28, 1.)},
         _sized(sediment_lunule_test_sector), orient="native", host="body", symmetry="center"),
    Part("perianal_tooth_ring", "aesthetics", "Five low projecting tooth plates encircling a sea cucumber's terminal opening.",
         ["sea cucumber", "holothurian", "anal teeth", "aperture"], {**_SIZE, "opening": (0., 1., .55)},
         _sized(perianal_tooth_ring), orient="native", host="body", symmetry="center"),
    Part("everting_jaw_crown", "feeding", "External bloodworm pharynx cuff ending in four radial curved jaw tips.",
         ["annelid", "bloodworm", "glycerid", "everted proboscis", "jaws"], {**_SIZE, "extension": (.35, 1., 1.), "gape": (.15, 1., .55)},
         _sized(everting_jaw_crown), orient="native", host="body", symmetry="center"),
    Part("pinnate_polyp_bearing_leaf", "feeding", "One triangular tapered sea pen leaf with repeated marginal polyp seats.",
         ["sea pen", "pennatulacean", "polyp", "rachis", "leaf"], {**_SIZE, "expansion": (.36, 1.22, 1.)},
         _sized(pinnate_polyp_bearing_leaf), orient="native", host="body"),
    Part("eversible_scalid_introvert", "locomotion", "Macroscopic priapulid introvert with several transverse rows of shallow projecting scalids.",
         ["priapulid", "introvert", "scalid", "sleeve", "worm"], {**_SIZE, "protrusion": (.31, 1., 1.)},
         _sized(eversible_scalid_introvert), orient="native", host="body", symmetry="center"),
]

TRAITS = {
    "ceratal_field": {"shape": "staggered rows of independent tapered mantle outgrowths", "function": "breathe", "construction": "deformable"},
    "sediment_lunule_test_sector": {"shape": "elongate aperture with unequal face contours through a rigid test plate"},
    "perianal_tooth_ring": {"shape": "five rigid flanges surrounding a soft terminal aperture", "function": "protect",
                            "regions": {"soft_rim": "deformable", "tooth_plates": "rigid"}},
    "everting_jaw_crown": {"shape": "soft tapered sleeve with four curved tips on its exposed leading face",
                          "regions": {"everted_cuff": "deformable", "jaw_tips": "rigid"}},
    "pinnate_polyp_bearing_leaf": {"shape": "soft lateral leaf with a row of independent scalloped polyp seats", "construction": "deformable"},
    "eversible_scalid_introvert": {"shape": "stretchable sleeve exposing repeated circumferential rows of scalids",
                                  "function": "support", "construction": "deformable"},
}
