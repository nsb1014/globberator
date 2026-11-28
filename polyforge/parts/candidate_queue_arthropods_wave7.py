"""External arthropod drafts with +Y dorsal and +Z anterior."""

import math

from ..kit import RIGHT, UP, V, rot
from . import Part
from .candidate_arthropod import _loft
from .candidate_queue_arthropods import SIZE, UNIT
from .research_locomotion import _closed_rings


def folding_fringe_swimming_oar(g, p):
    """Corixid distal hindleg with two tarsomeres and a directional setal fringe."""
    g.setup(finish="direct")
    size, spread = p["size"], p["spread"]
    tip_hinge = V(.003, -.020, -.132)
    swing = rot(RIGHT, math.radians(-14 + 28 * p["pitch"]))

    def distal(v):
        return tip_hinge + swing @ V(v)

    _loft(g, size, ((0, .004, .017), (0, .002, -.004), (.001, -.006, -.040),
                    (.003, -.016, -.095), tip_hinge),
          ((.017, .010), (.021, .011), (.020, .009), (.017, .008),
           (.014, .006)), up=UP)
    for path, radii in (
        (((0, 0, .005), (.002, -.001, -.021), (.004, -.002, -.073),
          (.005, -.002, -.135), (.008, -.004, -.169)),
         ((.015, .005), (.022, .006), (.026, .005), (.024, .0046), (.016, .0036))),
        (((.008, -.004, -.164), (.008, -.004, -.190), (.012, -.006, -.225),
          (.017, -.009, -.247), (.019, -.011, -.256)),
         ((.013, .004), (.019, .004), (.017, .004), (.010, .003), (.004, .002))),
    ):
        _loft(g, size, [distal(v) for v in path], radii, up=UP)
    for side in (-1, 1):
        for index in range(25):
            t = index / 24
            z = -.022 - .218 * t
            x = (.020 + .006 * math.sin(math.pi * t) - .008 * t**4) * side + .012 * t
            y = -.001 - .005 * t
            length = (.028 + .048 * math.sin(math.pi * t)**.72) * (1 if side < 0 else .81)
            root = V(x - .002 * side, y, z)
            flight = V(side * (.15 + .73 * spread), .16 * (1 - spread), -.93 + .45 * spread) * length
            _loft(g, size, [distal(root + v) for v in (
                V(0, 0, 0), .31 * flight,
                .67 * flight + V(0, .002, -.003), flight + V(0, .002, -.005),
            )], (.00175, .00150, .00102, .00029), up=UP, sides=8, density=3)
            if index % 2 == 0:
                inner = root - V(side * .008, -.0022, .002)
                _loft(g, size, [distal(inner), distal(inner + flight * .30),
                                distal(inner + flight * .76)],
                      (.00115, .00102, .00027), up=UP, sides=8, density=2)


def eversible_palpal_adhesive_pad(g, p):
    """Solifuge distal palp rim and eversible oval contact face."""
    g.setup(finish="direct")
    size, extend = p["size"], p["extend"]
    rings = []
    for z, w, h in (
        (-.025, .021, .022), (-.005, .026, .025), (.030, .026, .025),
        (.066, .027, .025), (.103, .035, .028), (.126, .039, .028),
        (.137, .034, .025), (.135, .027, .017), (.125, .023, .014),
        (.111, .018, .011), (.107, .009, .006),
    ):
        rings.append([V(w * math.cos(i * math.tau / 30),
                        h * math.sin(i * math.tau / 30), z) * size for i in range(30)])
    _closed_rings(g, rings)
    for side in (-1, 1):
        lip_height = .014 + .013 * extend
        _loft(g, size, ((0, side * .016, .106), (0, side * lip_height, .125),
                        (.001, side * (lip_height - .002), .140),
                        (.001, side * (lip_height - .004), .146)),
              ((.020, .006), (.032, .007), (.026, .005), (.012, .002)),
              up=UP, sides=22)
    _loft(g, size, (
        (0, -.003, .107), (0, -.003, .113 + .020 * extend),
        (0, -.001, .119 + .038 * extend), (0, .001, .120 + .053 * extend),
        (0, .001, .121 + .055 * extend),
    ), ((.013, .010), (.019 + .012 * extend, .013 + .007 * extend),
        (.019 + .019 * extend, .013 + .012 * extend),
        (.014 + .017 * extend, .010 + .012 * extend),
        (.007 + .011 * extend, .005 + .006 * extend)), up=UP, sides=26)


def setal_antennal_capture_scoop(g, p):
    """A strongly curved Emerita feeding antenna with two plumose margins."""
    g.setup(finish="direct")
    size, fold = p["size"], p["fold"]
    hinge = rot(RIGHT, math.radians(74 * fold))
    seat = V(.003, -.013, -.003)
    _loft(g, size, ((0, .013, -.020), (0, .000, -.007), (.002, -.011, .003),
                    (.004, -.015, .019)),
          ((.016, .014), (.014, .012), (.013, .012), (.013, .011)), up=RIGHT)

    def flag(t):
        angle = math.radians(134 * t)
        local = V(.023 * t, .134 * (1 - math.cos(angle)), .148 * math.sin(angle))
        return seat + hinge @ local

    nodes = [flag(i / 34) for i in range(35)]
    _loft(g, size, nodes, [.0125 * (1 - i / 35)**.70 + .0011 for i in range(35)],
          up=RIGHT, sides=16, density=2)
    for row in (-1, 1):
        for i in range(21):
            t = .14 + .83 * i / 20
            angular = math.radians(134 * t)
            tangent = hinge @ V(.07, math.sin(angular), math.cos(angular))
            interior = tangent.cross(RIGHT).normalized()
            root = flag(t) + V(row * (.006 - .002 * t), 0, 0)
            length = (.013 + .052 * math.sin(math.pi * t)**.79) * (1 - .29 * fold)
            ray = interior * length + RIGHT * (row * .014 * (1 - t))
            middle = root + .54 * ray + tangent * .013
            end = root + ray + tangent * .021
            _loft(g, size, (root, middle, end), (.00165, .00112, .00029),
                  up=RIGHT, sides=8, density=2)
            for factor in (-1, 1):
                _loft(g, size, (middle, middle.lerp(end, .58) + tangent * (factor * .004),
                                middle.lerp(end, .87) + tangent * (factor * .006)),
                      (.00075, .00054, .00024), up=RIGHT, sides=7, density=2)


PARTS = [
    Part("folding_fringe_swimming_oar", "locomotion", "A flattened corixid hind tarsus spreads a directional fringe into a swimming paddle.",
         ["water boatman", "corixid", "swimming oar", "setal fringe"],
         {"size": SIZE, "spread": (0., 1., .87), "pitch": (0., 1., .5)},
         folding_fringe_swimming_oar, orient="native", symmetry="pair"),
    Part("eversible_palpal_adhesive_pad", "manipulation", "A solifuge palp extends a fitting pad from its paired terminal lips.",
         ["solifuge", "pedipalp", "adhesion", "eversible pad"], {"size": SIZE, "extend": (0., 1., .81)},
         eversible_palpal_adhesive_pad, orient="native", symmetry="pair"),
    Part("setal_antennal_capture_scoop", "feeding", "A curved mole crab antenna supports two facing rows of coarse plumose setae.",
         ["mole crab", "antenna", "suspension", "filter-feeding"], {"size": SIZE, "fold": UNIT},
         setal_antennal_capture_scoop, orient="native", symmetry="pair"),
]

TRAITS = {
    "folding_fringe_swimming_oar": {"function": "swim"},
    "eversible_palpal_adhesive_pad": {"function": "adhere"},
    "setal_antennal_capture_scoop": {"function": "feed"},
}
