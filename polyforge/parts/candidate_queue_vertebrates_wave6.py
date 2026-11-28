"""Isolated climbing, walking and feather contact anatomy drafts."""

import math

from ..kit import UP, V, lerp
from . import Part
from .research_locomotion import _closed_rings, _feather


def inward_claw_bearing_forefoot(g, p):
    """Anteater forefoot with three inward-curled digits and dorsal stance pads."""
    size, flex = p["size"], p["flex"]
    g.setup(voxel=.0011 * size, smooth=.26, detail=3.9, slot_finish={"keratin": "subsurf_low"})
    g.slot("skin")
    g.loft([V(*point) * size for point in ((0., .043, -.022), (0., .013, -.009),
             (0., -.023, .007), (0., -.040, .032), (0., -.049, .050))],
           [(w * size, h * size) for w, h in ((.025, .023), (.033, .026),
             (.046, .029), (.053, .026), (.038, .021))],
           sides=20, density=3, exponent=.75)
    for x, length, width in ((-.032, .044, .014), (0., .075, .020), (.033, .060, .017)):
        toe = V(x, -.057, .061)
        bend = toe + V(x * .13, -.024, .008)
        root = toe + V(x * .12, -.020 + .010 * flex, -.018)
        g.slot("skin")
        g.loft([v * size for v in (toe - V(0., -.004, .021), toe, bend, root)],
               [r * width * size for r in (1.02, 1.0, .91, .62)], sides=14, density=3)
        tip = root + V(-.36 * length - x * .10, .024 + .017 * flex, -.69 * length)
        mid = root.lerp(tip, .55) + V(0., -.009 - .003 * flex, .002)
        g.slot("keratin")
        g.loft([v * size for v in (bend.lerp(root, .68), root, mid, tip)],
               [(w * width * size, h * width * size) for w, h in
                ((.39, .51), (.51, .58), (.38, .39), (.056, .068))],
               sides=12, density=3)
    g.slot("skin")
    # The lateral fatty pad spans the fourth and reduced, unclawed fifth digit.
    g.loft([V(*point) * size for point in ((.026, -.057, .010),
             (.043, -.065, .035), (.049, -.068, .055))],
           [(w * size, h * size) for w, h in ((.019, .013), (.023, .016), (.017, .013))],
           sides=16, density=3)


def split_axis_bark_grip_foot(g, p):
    """Woodpecker foot with anterior digits II–III and a rotating digit IV."""
    size, bark = p["size"], p["bark"]
    g.setup(voxel=.00056 * size, smooth=.24, detail=4.2, slot_finish={"keratin": "subsurf_low"})
    g.slot("skin")
    ankle = V(0., -.004, -.002)
    g.oval(ankle * size, V(.014, .011, .015) * size)
    g.loft([v * size for v in (ankle, V(0., .019, -.009), V(0., .031, -.013))],
           [r * size for r in (.011, .0115, .010)], sides=16, up=V(0, 0, 1), density=3)
    for x, z, azimuth, length, radius in (
        (-.007, .003, -.28, .049, .0048),
        (.003, .005, .19, .057, .0054),
        (-.006, -.005, -2.83 - .35 * bark, .025, .0037),
        (.007, -.003, 2.63 - .99 * bark, .046, .0048),
    ):
        root = V(x, -.005, z)
        axis = V(math.sin(azimuth), 0., math.cos(azimuth))
        joint = root + axis * length * .55 + V(0., -.004, 0.)
        tip = root + axis * length + V(0., -.011 - .005 * bark, 0.)
        g.slot("skin")
        g.loft([v * size for v in (root, joint, tip)],
               [r * radius * size for r in (1.03, .94, .60)], sides=14, density=3)
        g.slot("keratin")
        g.loft([v * size for v in (tip - axis * .004, tip + axis * .0045,
               tip + axis * .009 + V(0., -.005, 0.), tip + axis * .007 + V(0., -.010, 0.))],
               [r * radius * size for r in (.76, .65, .44, .10)], sides=11, density=3)


def stridulating_wing_feather_pair(g, p):
    """Neighboring male manakin secondaries with one pick and one ridged file."""
    size, phase = p["size"], p["phase"]
    g.setup(finish="subsurf_low")
    g.slot("file_vane")
    file_root = V(0., 0., -.007)
    file_tip = V(.010, .003, .071)
    _feather(g, file_root, file_tip, .010, .0015, size, rounded=True)
    g.slot("file_rachis")
    g.loft([V(*pt) * size for pt in ((0., .000, -.007), (.003, .001, .017),
             (.006, .001, .034), (.009, .003, .056), (.011, .003, .071))],
           [(w * size, h * size) for w, h in ((.0012, .0012), (.0029, .0021),
             (.0042, .0031), (.0040, .0032), (.0015, .0014))], sides=20, density=4)
    g.slot("ridge")
    for i in range(8):
        z = .030 + i * .0035
        x = .006 + i * .00042
        y = .0034 + i * .0001
        points = (V(x - .0034, y - .0023, z), V(x - .002, y + .0004, z),
                  V(x, y + .0016, z), V(x + .0021, y + .0004, z),
                  V(x + .0035, y - .0022, z))
        g.loft([point * size for point in points],
               [r * size for r in (.0004, .0007, .0008, .0007, .0004)],
               sides=9, density=2)
    g.slot("pick_vane")
    pick_root = V(-.018, -.004, -.007)
    pick_end = V(-.011, .002, .059)
    _feather(g, pick_root, pick_end, .009, .0013, size, rounded=True)
    g.slot("pick_rachis")
    strike_z = .039 + .010 * phase
    points = (pick_root, V(-.018, -.002, .017), V(-.016, .001, .036),
              V(-.011, .004, .057), V(-.002, .006, .056), V(.004, .0056, strike_z))
    g.loft([v * size for v in points], [r * size for r in (.001, .0015, .0020,
            .0014, .0010, .00050)], sides=12, density=3)


def serrated_primary_leading_edge(g, p):
    """A vane coupon and individually curved, upward tips of leading-edge barbs."""
    size, incline = p["size"], p["incline"]
    g.setup(finish="subsurf_low")
    g.slot("vane")
    rings = []
    for x in (-.020, -.016, -.011, -.005, .002, .008, .014, .020):
        ring = []
        for j in range(26):
            angle = math.tau * j / 26
            chord = (math.cos(angle) + 1.) * .5
            z = -.019 + .023 * chord + .034 * x
            y = .0018 * math.sin(chord * math.pi) + .00067 * math.sin(angle)
            ring.append(V(x, y, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)
    g.slot("barb_tips")
    for j in range(16):
        x = -.0166 + j * .00214
        reach = .0038 + .0018 * math.sin((j + 1) * math.pi / 17)
        root = V(x, .0011, .003 + .034 * x)
        points = (root - V(0., 0., .0016), root + V(.0006, .00042, reach * .35),
                  root + V(.0015, .0010 * incline, reach * .77),
                  root + V(.0028, .0030 * incline, reach * .92),
                  root + V(.0033, .0040 * incline, reach * .87))
        g.loft([v * size for v in points],
               [(w * size, h * size) for w, h in ((.00047, .00022), (.00037, .00022),
                 (.00031, .00020), (.00021, .00014), (.000075, .000075))],
               sides=9, density=2)


def interlocking_feather_vane_patch(g, p):
    """Enlarged vane patch with distal barb hooks crossing raised proximal rails."""
    size, opening = p["size"], p["opening"]
    gap = .005 + .003 * opening
    g.setup(finish="subsurf_low")
    for side in (-1, 1):
        g.slot("barbs")
        root_x = side * gap
        g.loft([V(root_x, y, z) * size for y, z in ((0., -.021), (0., -.010),
                 (.0002, .006), (0., .019))],
               [(w * size, h * size) for w, h in ((.0012, .0009), (.00112, .0009),
                (.0010, .0008), (.0007, .00065))],
               sides=13, density=3)
        g.slot("proximal_rails" if side > 0 else "distal_hooks")
        for i in range(9):
            z = -.016 + i * .0035
            base = V(root_x - side * .00065, 0., z)
            if side < 0:
                points = (base, base + V(.0032, .0008, .0010),
                          base + V(.0073, .0015, .0023),
                          base + V(.0090, .0012, .0027),
                          base + V(.0093, -.00055, .0026),
                          base + V(.0086, -.00086, .0024))
            else:
                points = (base, base + V(-.0023, -.00038, -.0018),
                          base + V(-.0058, -.00032, -.0041),
                          base + V(-.0070, .00012, -.0051))
            radii = [lerp(.00032, .00012, j / (len(points) - 1)) * size for j in range(len(points))]
            g.loft([v * size for v in points], radii, sides=9, density=2, up=UP)


PARTS = [
    Part("inward_claw_bearing_forefoot", "locomotion", "Draft knuckle-bearing forefoot with claws folded inward.",
         ["anteater", "manus", "claw", "knuckle", "stance"], {"size": (.45, 2., 1.), "flex": (0., 1., .65)},
         inward_claw_bearing_forefoot, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("split_axis_bark_grip_foot", "locomotion", "Draft woodpecker foot with two toes in front and a reversible outer toe.",
         ["woodpecker", "foot", "climb", "zygodactyl", "bark"], {"size": (.45, 2., 1.), "bark": (0., 1., .73)},
         split_axis_bark_grip_foot, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("stridulating_wing_feather_pair", "aesthetics", "Draft bent pick and ridged shaft on two neighboring secondaries.",
         ["manakin", "stridulation", "feather", "wing"], {"size": (.45, 2., 1.), "phase": (-1., 1., .2)},
         stridulating_wing_feather_pair, orient="native", host="limb", symmetry="pair"),
    Part("serrated_primary_leading_edge", "aesthetics", "Draft owl flight vane with a comb of upturned barb tips.",
         ["owl", "primary", "feather", "serration", "leading"], {"size": (.45, 2., 1.), "incline": (.40, 1.25, 1.)},
         serrated_primary_leading_edge, orient="native", host="limb", symmetry="pair"),
    Part("interlocking_feather_vane_patch", "aesthetics", "Draft vane patch with complementary hooks and rails between adjacent barbs.",
         ["pigeon", "feather", "barbule", "vane", "hook"], {"size": (.45, 2., 1.), "opening": (0., 1., .1)},
         interlocking_feather_vane_patch, orient="native", host="limb", symmetry="pair"),
]
