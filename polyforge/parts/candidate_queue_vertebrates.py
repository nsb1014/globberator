"""Isolated vertebrate locomotor drafts in metres, +Y up and +Z anterior."""

import math

from ..kit import UP, V, lerp, rot
from . import Part
from .research_locomotion import _closed_rings, _feather


def _sole_loft(g, sections, size, exponent=.65):
    """Close forward stations with separate dorsal and flattened plantar curves."""
    rings = []
    for z, x, width, bottom, top in sections:
        ring = []
        for i in range(24):
            angle = math.tau * i / 24
            horizontal, vertical = math.cos(angle), math.sin(angle)
            cross = math.copysign(abs(horizontal) ** exponent, horizontal)
            height = math.copysign(abs(vertical) ** (.47 if vertical < 0 else .83), vertical)
            ring.append(V(x + width * cross, lerp(bottom, top, .5 + .5 * height), z) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def burrowing_forefoot(g, p):
    """Right mole manus with a widened medial support and five free digging claws."""
    size = p["size"]
    g.setup(voxel=.00040 * size, smooth=.30, detail=3.2)
    g.slot("skin")
    # Turn the plantar-facing profile toward the +X-side wall.
    palm_frame = rot((0, 0, 1), math.radians(90. + p["roll"]))

    def in_palm(point):
        return (palm_frame @ V(*point)) * size

    g.loft([in_palm(v) for v in ((0, .005, -.011), (0, .002, -.005), (0, 0, .002),
                                (-.001, 0, .010), (-.001, .002, .014))],
           [(w * size, h * size) for w, h in ((.0045, .0042), (.0072, .0048),
             (.011, .0048), (.013, .004), (.010, .0028))],
           sides=20, up=palm_frame @ UP, exponent=.68, density=4)
    g.loft([in_palm(v) for v in ((-.004, -.001, -.003), (-.009, -.002, .002),
                                (-.013, -.002, .009), (-.013, 0, .012))],
           [r * size for r in (.0035, .0043, .0033, .0015)],
           sides=14, up=palm_frame @ UP)
    digits = ((-.0108, -.0140, .023), (-.0060, -.0070, .029), (0, 0, .033),
              (.0055, .0075, .031), (.0101, .0130, .026))
    for root, tip, end in digits:
        g.loft([in_palm(v) for v in ((root, .001, .010), (lerp(root, tip, .5), .001, .015),
                                    (tip, .0005, end - .006))],
               [r * size for r in (.0026, .0024, .0016)], sides=12, density=3, up=palm_frame @ UP)
    g.slot("keratin")
    g.setup(slot_finish={"keratin": "subsurf_low"})
    for root, tip, end in digits:
        g.loft([in_palm(v) for v in ((lerp(root, tip, .8), .0005, end - .008),
                                    (tip, .0005, end - .004), (tip, -.0027, end))],
               [(w * size, h * size) for w, h in ((.0019, .0013), (.0015, .0011), (.00035, .00035))],
               sides=10, up=palm_frame @ UP, density=3)


# The root resides in the pelvis. The nearly horizontal distal span is the contact region.
_BRACED_TAIL = (
    (.04, .037, .077, .076), (0, .000, .085, .086), (-.10, -.051, .082, .085),
    (-.22, -.124, .073, .076), (-.33, -.204, .063, .069), (-.43, -.302, .057, .063),
    (-.52, -.371, .050, .051), (-.61, -.410, .044, .041), (-.72, -.423, .037, .030),
    (-.86, -.429, .028, .024), (-.98, -.435, .019, .018), (-1.09, -.435, .011, .010),
    (-1.15, -.423, .003, .004),
)


def ground_braced_tail(g, p):
    """A loaded tail envelope with a broad proximal arch and flattened ground span."""
    rings = []
    size, brace = p["size"], p["brace"]
    for z, y, half_width, depth in _BRACED_TAIL:
        t = max(0., -z / 1.15)
        recovery = .04 - .12 * t - .065 * math.sin(t * math.pi)
        center = lerp(recovery, y, brace)
        grounded = brace * min(1., max(0., (t - .42) / .14))
        ring = []
        for i in range(24):
            angle = math.tau * i / 24
            x, q = math.cos(angle), math.sin(angle)
            vertical = math.copysign(abs(q) ** (1. - .65 * grounded if q < 0 else 1.), q)
            ring.append(V(x * half_width, center + vertical * depth, z) * size)
        rings.append(ring)
    g.setup(finish="subsurf_low")
    g.slot("skin")
    _closed_rings(g, rings)


def nail_rim_cushion_foot(g, p):
    """African elephant right hindfoot silhouette with a single broad sole and three seats."""
    size, pad = p["size"], p["spread"]
    levels = (
        (.030, .077, .068, -.014), (.002, .088, .080, -.018),
        (-.053, .095, .087, -.022), (-.114, .112, .107, -.023),
        (-.172, .132, .133, -.019), (-.208, .139, .145, -.012),
        (-.228, .134, .139, -.012), (-.239, .117, .123, -.014),
        (-.243, .088, .098, -.018), (-.243, .041, .055, -.022),
    )
    rings = []
    for y, width, length, z in levels:
        expansion = lerp(1., pad, min(1., max(0., -y / .20)))
        ring = []
        for i in range(32):
            angle = math.tau * i / 32
            x, q = math.cos(angle), math.sin(angle)
            # A flatter toe rim, rounded heel and slightly protruding lateral quarter.
            forward = math.copysign(abs(q) ** (.60 if q >= 0 else .82), q)
            lateral = math.copysign(abs(x) ** .85, x) * (1. + .060 * x - .095 * q)
            ring.append(V(width * expansion * lateral, y, z + length * expansion * forward) * size)
        rings.append(ring)
    g.setup(finish="subsurf_low")
    g.slot("skin")
    _closed_rings(g, rings)
    g.slot("keratin")
    for x, yaw, width in ((-.066, -.39, .032), (.006, .04, .039), (.079, .52, .033)):
        z = (-.012 + .141 * math.sqrt(1. - (x / .155) ** 2)) * pad
        seat = rot((0, 1, 0), yaw)
        points = [
            V(x * pad, -.184, z - .007),
            V(x * pad, -.201, z + .001),
            V(x * pad, -.224, z + .004),
            V(x * pad, -.237, z + .003),
        ]
        # Follow the rim ellipse so the outer nail does not face directly anterior.
        center = points[1]
        g.loft([(center + seat @ (point - center)) * size for point in points],
               [(width * k * size, depth * size) for k, depth in
                ((.70, .010), (1., .012), (.94, .013), (.74, .009))],
               sides=14, up=V(math.sin(yaw), 0, math.cos(yaw)), density=3)


def splayed_two_toe_sole(g, p):
    """Camel forefoot with two fleshy distal lobes joined across the loaded heel."""
    size, spread = p["size"], p["splay"]
    g.setup(voxel=.00165 * size, detail=3.6, smooth=.24)
    g.slot("skin")
    _sole_loft(g, ((-.082, 0, .015, -.102, -.071), (-.058, 0, .065, -.127, -.046),
                   (-.033, 0, .074, -.129, -.014), (-.005, 0, .071, -.127, .021),
                   (.024, 0, .060, -.122, -.020), (.058, 0, .041, -.114, -.051)),
               size)
    g.oval(V(0, -.031, -.012) * size, V(.049, .056, .042) * size, segs=20, rings=12)
    for side in (-1, 1):
        center = side * (.039 + .014 * spread)
        reach = .010 if side == -1 else 0.
        _sole_loft(g, ((-.053, .031 * side, .027, -.109, -.063),
                       (-.024, .038 * side, .041, -.128, -.037),
                       (.020, .90 * center, .044, -.129, -.028),
                       (.072, center, .042, -.129, -.045),
                       (.112 + reach, 1.04 * center, .032, -.123, -.055),
                       (.141 + reach, 1.07 * center, .018, -.115, -.077),
                       (.151 + reach, 1.07 * center, .006, -.103, -.085)), size)
    g.slot("keratin")
    g.setup(slot_finish={"keratin": "subsurf_low"})
    for side in (-1, 1):
        x = side * (.039 + .014 * spread) * 1.07
        z = .137 + (.010 if side == -1 else 0.)
        _sole_loft(g, ((z - .016, .97 * x, .012, -.092, -.078),
                       (z, x, .017, -.108, -.077),
                       (z + .014, x, .015, -.115, -.086),
                       (z + .025, x, .006, -.113, -.103)), size)


def offset_two_toe_running_foot(g, p):
    """Right ostrich pes with a longer medial digit III and shorter un-clawed digit IV."""
    size, spread = p["size"], p["splay"]
    g.setup(voxel=.0014 * size, detail=3.4, smooth=.27)
    g.slot("skin")
    _sole_loft(g, ((-.058, 0, .010, -.045, -.024), (-.037, 0, .028, -.057, .009),
                   (-.005, 0, .035, -.063, .029), (.028, 0, .038, -.076, .006),
                   (.068, .002, .035, -.110, -.042), (.088, .003, .021, -.115, -.077)), size)
    _sole_loft(g, ((-.010, -.006, .021, -.068, -.021), (.040, -.010, .029, -.087, -.032),
                   (.089, -.017, .030, -.133, -.063), (.127, -.021, .022, -.139, -.074),
                   (.174, -.024, .023, -.138, -.082), (.209, -.026, .020, -.131, -.090),
                   (.236, -.027, .012, -.123, -.099)), size)
    lateral = .053 + .024 * spread
    _sole_loft(g, ((.024, .018, .017, -.085, -.052), (.057, .52 * lateral, .021, -.111, -.070),
                   (.091, .79 * lateral, .017, -.132, -.093), (.123, lateral, .017, -.136, -.100),
                   (.152, 1.11 * lateral, .011, -.133, -.110),
                   (.168, 1.16 * lateral, .005, -.128, -.116)), size)
    g.slot("keratin")
    g.setup(slot_finish={"keratin": "subsurf_low"})
    _sole_loft(g, ((.218, -.027, .011, -.118, -.096), (.237, -.027, .013, -.123, -.096),
                   (.254, -.027, .010, -.129, -.105), (.272, -.027, .004, -.131, -.119),
                   (.281, -.027, .001, -.130, -.126)), size)


def leading_edge_alula_hinge(g, p):
    """One native right leading-edge digit and its overlapping feather cluster."""
    size = p["size"]
    hinge = rot((.24, 0, .97), math.radians(p["lift"]))
    g.setup(finish="subsurf_low")
    g.slot("digit")
    g.loft([(hinge @ V(*point)) * size for point in ((-.010, -.005, -.009),
             (.003, 0, .000), (.017, 0, .017), (.032, .000, .025))],
           [(w * size, d * size) for w, d in ((.007, .004), (.008, .005),
            (.007, .004), (.003, .002))], sides=14, density=3)
    g.slot("feather")
    for start, end, width in (
        ((.017, 0, .018), (.098, -.007, .011), .013),
        ((.013, .002, .014), (.112, -.004, -.001), .014),
        ((.010, .004, .008), (.102, .000, -.011), .015),
        ((.006, .005, .000), (.080, .003, -.020), .013),
    ):
        _feather(g, hinge @ V(*start), hinge @ V(*end), width, .0035, size, rounded=True)


PARTS = [
    Part("burrowing_forefoot", "locomotion", "Draft outward-facing digging manus with a widened medial edge.",
         ["mole", "digging", "fossorial", "manus"], {"size": (.4, 2., 1.), "roll": (-50., -25., -38.)},
         burrowing_forefoot, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("ground_braced_tail", "locomotion", "Draft thick-rooted tail with a long grounded distal support span.",
         ["kangaroo", "pentapedal", "tail", "ground contact"], {"size": (.45, 2., 1.), "brace": (0., 1., 1.)},
         ground_braced_tail, orient="native", symmetry="center", hint={"u": .06, "theta": 90.}),
    Part("nail_rim_cushion_foot", "locomotion", "Draft columnar hindfoot with plantar cushion and perimeter nails.",
         ["elephant", "pes", "sole", "nail"], {"size": (.45, 2., 1.), "spread": (.9, 1.13, 1.)},
         nail_rim_cushion_foot, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("splayed_two_toe_sole", "locomotion", "Draft soft didactyl pad with separate dorsal nails and toe lobes.",
         ["camel", "pes", "splay", "digital cushion"], {"size": (.45, 2., 1.), "splay": (.18, 1., .65)},
         splayed_two_toe_sole, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("offset_two_toe_running_foot", "locomotion", "Draft elevated-joint running foot with asymmetric toe support.",
         ["ostrich", "ratite", "didactyl", "toe"], {"size": (.45, 2., 1.), "splay": (.15, 1., .55)},
         offset_two_toe_running_foot, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("leading_edge_alula_hinge", "locomotion", "Draft independently protracting digit and leading-edge feather cluster.",
         ["bird", "alula", "leading-edge", "wing"], {"size": (.45, 2., 1.), "lift": (0., 45., 23.)},
         leading_edge_alula_hinge, orient="native", host="limb", symmetry="pair"),
]
