"""Integrated head and claw sculpts with rigid opposing pieces."""

import math

from ..kit import BACK, UP, V, rot
from . import Part


def _loft(g, scale, points, radii, **options):
    g.loft([V(point) * scale for point in points],
           [tuple(radius * scale for radius in pair) for pair in radii], **options)


def _oval(g, scale, center, radii, *, basis=None):
    g.oval(V(center) * scale, tuple(radius * scale for radius in radii),
           basis=basis, segs=28, rings=16)


def _indent(primitive, scale, center, widths, displacement):
    """Sculpt a shallow, localized depression on an existing closed cage."""
    c, w, d = V(center), V(widths), V(displacement) * scale
    for index, vertex in enumerate(primitive.v):
        point = vertex / scale - c
        distance = sum((offset / width) ** 2 for offset, width in zip(point, w))
        primitive.v[index] = vertex - math.exp(-distance) * d


def head_bovine(g, p):
    """Upright skull: +Z is forward, +Y is up, origin is at the neck seat."""
    scale, snout, brow, muzzle = (p[key] for key in ("size", "snout", "brow", "muzzle"))
    bridge = .327 + .084 * (snout - 1)
    nose = .449 + .216 * (snout - 1)
    g.setup(voxel=.0042 * scale, detail=3.3, smooth=.4)
    g.slot("base")
    _loft(g, scale,
          [(0, .025, -.174), (0, .025, -.154), (0, .031, -.077), (0, .031, .048), (0, .018, .182),
           (0, -.044, .255), (0, -.101, bridge), (0, -.163, nose - .034),
           (0, -.174, nose + .001), (0, -.174, nose + .043), (0, -.173, nose + .071)],
          [(.037, .037), (.140, .127), (.217, .199), (.249, .221), (.230, .202),
           (.193, .170), (.151, .114), (.150 * muzzle, .081), (.163 * muzzle, .077),
           (.157 * muzzle, .071), (.091 * muzzle, .041)],
          sides=56, density=7, exponent=.73)
    skull = g.prims[-1]

    for side in (-1, 1):
        # Broaden the outer orbit and cheek directly on the cranium cage so
        # the face has a continuous surface under the rim of the upper eyelid.
        _indent(skull, scale, (side * .155, .134, .223), (.103, .045, .085),
                (-side * .017 * brow, -.019 * brow, -.030 * brow))
        _indent(skull, scale, (side * .207, .071, .241), (.077, .036, .065), (side * .045, -.003, .043))
        _indent(skull, scale, (side * .207, -.061, .199), (.103, .086, .134), (-side * .025, .015, -.011))
        _indent(skull, scale, (side * .098 * muzzle, -.149, nose + .070),
                (.041 * muzzle, .023, .043), (side * .017, .001, .030))

    g.slot("detail")
    g.setup(slot_finish={"detail": "direct"})
    for side in (-1, 1):
        _oval(g, scale, (side * .166, .074, .230), (.034, .017, .020), basis=rot(UP, side * .78))

    # The transverse pivot sits inside the skull above the ramus. Back-of-jaw
    # overlap is deliberate and keeps the joint covered as the mouth opens.
    g.pivots["jaw"] = V(0, -.123, .112) * scale
    g.use("jaw")
    g.setup(voxel=.0038 * scale, detail=2.5, smooth=.35)
    g.slot("base")
    _loft(g, scale,
          [(0, -.151, .080), (0, -.187, .128), (0, -.233, .227),
           (0, -.278, bridge), (0, -.303, nose - .034), (0, -.301, nose + .028),
           (0, -.298, nose + .050)],
          [(.115, .045), (.189, .082), (.169, .076), (.135, .054),
           (.126 * muzzle, .048), (.126 * muzzle, .043), (.093 * muzzle, .030)],
          sides=38, density=6, exponent=.70)


def pincer_crescent(g, p):
    """Crab claw: +Y follows the wrist and +Z is normal to the pinch plane."""
    scale, bulk, hook, serration = (p[key] for key in ("size", "bulk", "hook", "serration"))
    hinge = V(.066, .127, 0)
    spread = .044 * (bulk - 1)
    g.pivots["jaw"] = hinge * scale
    g.setup(voxel=.0022 * scale, detail=2.8, smooth=.35)
    g.slot("accent")
    _loft(g, scale, [(0, -.043, 0), (0, .005, 0), (-.009, .057, 0), (-.026, .113, 0)],
          [(.043, .040), (.054, .048), (.078 * bulk, .059 * bulk), (.080 * bulk, .060 * bulk)],
          up=BACK, sides=28)
    _oval(g, scale, (.035, .102, 0), (.060 * bulk, .049, .050 * bulk))
    _loft(g, scale,
          [(-.029, .075, 0), (-.052, .126, 0), (-.074, .179, 0), (-.080, .233, 0),
           (-.069, .274, 0), (-.047 + .014 * hook, .306, 0), (-.032 + .041 * hook, .316, 0)],
          [(.069 * bulk, .053 * bulk), (.080 * bulk, .060 * bulk), (.068 * bulk, .053 * bulk),
           (.052 * bulk, .039 * bulk), (.037 * bulk, .027 * bulk),
           (.022 * bulk, .016 * bulk), (.0048, .0055)],
          up=BACK, sides=30, density=5, exponent=.88)
    for index, (x, y) in enumerate(((-.043, .205), (-.045, .234), (-.035, .263))):
        _oval(g, scale, (x - .003 + .023 * (bulk - 1) + .012 * serration, y, 0),
              ((.015 - .002 * index) * (.45 + serration), .012, .015))

    g.use("jaw")
    g.setup(voxel=.0022 * scale, detail=2.6, smooth=.37)
    g.slot("accent")
    _loft(g, scale,
          [hinge - V(.002, .032, 0), hinge, (.094 + spread, .170, 0), (.111 + spread, .214, 0),
           (.105 + spread, .257, 0), (.082 - .010 * hook + spread, .287, 0),
           (.065 - .027 * hook + spread, .297, 0)],
          [(.025 * bulk, .027 * bulk), (.041 * bulk, .040 * bulk), (.045 * bulk, .041 * bulk),
           (.040 * bulk, .035 * bulk), (.030 * bulk, .027 * bulk),
           (.019 * bulk, .014 * bulk), (.0046, .0055)],
          up=BACK, sides=28, density=5, exponent=.88)
    for index, (x, y) in enumerate(((.066, .195), (.074, .223), (.072, .250))):
        _oval(g, scale, (x + .002 + spread - .022 * (bulk - 1) - .009 * serration, y, 0),
              ((.013 - .001 * index) * (.45 + serration), .012, .014))


PARTS = [
    Part("head_bovine", "head", "Integrated bovine skull with ridged brows, cheeks, muzzle and hinged lower jaw.",
         ["bull", "cow", "bovine", "minotaur", "skull", "brow", "muzzle", "hinge"],
         {"size": (.4, 3, 1), "snout": (.78, 1.40, 1), "brow": (.55, 1.50, 1),
          "muzzle": (.8, 1.35, 1)},
         head_bovine, orient="native", symmetry="center", cap="mouth", hint={"u": .96, "theta": -90},
         bones=[{"name": "jaw", "pivot": (0, -.123, .112), "axis": (1, 0, 0), "angle": 27.0}]),
    Part("pincer_crescent", "hand", "Broad crab claw with recurved tips and a hinged opposing finger.",
         ["crab", "lobster", "crustacean", "pincer", "claw", "crescent", "hinge"],
         {"size": (.4, 3, 1), "bulk": (.84, 1.25, 1), "hook": (.30, 1.30, 1),
          "serration": (0, 1, .58)},
         pincer_crescent, attach="tip", cap="grasp",
         bones=[{"name": "jaw", "pivot": (.066, .127, 0), "axis": (0, 0, 1), "angle": -28.0}]),
]
