"""External arthropod anatomy drafts with +Y dorsal and +Z anterior."""

import math

from ..kit import RIGHT, UP, V, rot
from . import Part
from .candidate_arthropod import _loft
from .candidate_queue_arthropods import SIZE, UNIT
from .research_locomotion import _closed_rings


def opposed_terminal_forceps(g, p):
    """Paired male earwig cerci, with a basal expansion and long curved tips."""
    g.setup(finish="direct")
    size = p["size"]
    for side in (-1, 1):
        root = V(.036, 0, 0)
        swivel = rot(UP, -math.radians(25 * p["open"]))

        def place(local):
            value = root + swivel @ V(local)
            return V(value.x * side, value.y, value.z)

        _loft(g, size, [place(v) for v in (
            (0, .002, .028), (.001, .003, .005), (.014, .003, -.020),
            (.035, .005, -.046), (.052, .008, -.081), (.060, .012, -.121),
            (.056, .015, -.159), (.042, .017, -.186), (.022, .019, -.199),
            (-.015, .020, -.197), (-.032, .019, -.186),
        )], ((.012, .009), (.020, .013), (.018, .013), (.014, .011),
             (.012, .010), (.010, .008), (.008, .007), (.006, .0052),
             (.0041, .004), (.0024, .0027), (.0007, .001)),
              up=RIGHT, sides=22)
        # The small medial shoulder lies at the transition from base to curve.
        _loft(g, size, [place(v) for v in ((.015, .002, -.036), (.007, .002, -.038),
                                           (-.002, .004, -.034), (-.006, .006, -.028))],
              ((.010, .008), (.007, .006), (.004, .004), (.0008, .0012)),
              up=UP, sides=14, density=4)


def overhanging_pronotal_crown(g, p):
    """Bocydium pronotal truss with four globes and one long trailing spine."""
    g.setup(finish="direct")
    size = p["size"]
    _loft(g, size, (
        (0, -.032, -.008), (0, -.014, -.009), (0, .001, -.008), (0, .040, .006),
        (0, .082, .012), (0, .105, .013), (0, .114, .010),
    ), ((.037, .024), (.046, .031), (.041, .028), (.030, .019),
        (.018, .015), (.017, .017), (.013, .014)), up=RIGHT)
    for side in (-1, 1):
        for row in (0, 1):
            end_x = .090 - .044 * row
            end_y = .115 + .047 * row
            end_z = .020 + .022 * row
            _loft(g, size, [(side * x, y, z) for x, y, z in (
                (.010, .102 + .003 * row, .010), (.025, .102 + .016 * row, .015),
                (end_x * .79, end_y - .013, end_z - .003), (end_x * .92, end_y - .005, end_z),
                (end_x, end_y, end_z), (end_x * 1.06, end_y + .008, end_z + .002),
                (end_x * 1.08, end_y + .018, end_z + .003),
                (end_x * 1.08, end_y + .026, end_z + .003),
            )], (.010, .009, .007, .0084, .012, .0183, .0158, .007),
                  up=UP, sides=20)
    _loft(g, size, (
        (0, .101, .010), (0, .111, -.027), (0, .107, -.074),
        (0, .093, -.132), (0, .074, -.198), (0, .049, -.259), (0, .031, -.301),
    ), (.013, .014, .012, .0093, .0065, .0036, .0007), up=RIGHT, sides=20)


def rigid_eyestalk_antenna_crown(g, p):
    """One male Teleopsis head projection with its distal lens and antennal seat."""
    g.setup(finish="direct")
    size = p["size"]
    _loft(g, size, (
        (-.028, -.006, -.005), (.005, .004, -.002), (.038, .021, .000),
        (.086, .046, .008), (.155, .073, .012), (.235, .091, .018),
        (.318, .107, .019), (.367, .115, .019), (.405, .122, .019),
    ), ((.022, .025), (.023, .027), (.018, .023), (.012, .018),
        (.008, .014), (.007, .010), (.008, .011), (.013, .016), (.023, .022)), up=UP)
    _loft(g, size, (
        (.387, .119, .020), (.396, .119, .020), (.412, .120, .021),
        (.437, .121, .020), (.455, .121, .019), (.463, .120, .017),
    ), ((.014, .014), (.026, .026), (.033, .031), (.035, .032),
        (.027, .027), (.009, .011)), up=UP, sides=30)
    # The antennal collar sits medial to the eye at the anterior margin.
    rings = []
    for z, radius in ((.026, .008), (.038, .010), (.045, .009), (.047, .006),
                      (.044, .0045), (.040, .0035)):
        rings.append([V(.382 + radius * math.cos(a * math.tau / 18),
                        .115 + radius * .78 * math.sin(a * math.tau / 18), z) * size
                      for a in range(18)])
    _closed_rings(g, rings)


def stiff_to_membranous_forewing(g, p):
    """One hemelytron with an integrated corium, clavus and thin venated tip."""
    g.setup(finish="direct")
    size = p["size"]
    swivel = rot(UP, -math.radians(33 * p["raise"])) @ rot(RIGHT, math.radians(48 * p["raise"]))
    stations = (
        (0, 0, .014), (.05, .008, .024), (.13, .026, .044), (.24, .046, .072),
        (.36, .065, .094), (.51, .082, .106), (.64, .087, .109), (.75, .097, .100),
        (.84, .111, .088), (.92, .121, .075), (.97, .135, .057), (1, .151, .019),
    )
    rings = []
    for index in range(61):
        t = index / 60
        hi = next((i for i, row in enumerate(stations) if row[0] > t), len(stations) - 1)
        t0, center0, width0 = stations[hi - 1]
        t1, center1, width1 = stations[hi]
        alpha = (t - t0) / (t1 - t0)
        center = center0 + (center1 - center0) * alpha
        width = width0 + (width1 - width0) * alpha
        ring = []
        for side in range(48):
            phi = side * math.tau / 48
            lateral = math.cos(phi)
            face = math.sin(phi)
            transition = .62 + .05 * lateral
            thin = min(1., max(0., (t - transition) / .042))
            thickness = .010 * (1 - thin) + .0019 * thin
            bend = .019 * (1 - lateral**2) * (1 - t) + .004 * lateral
            vein = .0014 * thin * math.exp(-(math.sin((lateral + (1 - t)**1.5) * 14) / .32)**2)
            if not thin:
                vein = .0017 * math.exp(-((lateral + .56 + .19 * t) / .09)**2)
            contour = bend + face * (thickness + vein)
            ring.append(swivel @ V(center + lateral * width, contour, .016 - t * .475) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def folding_pleonal_apron(g, p):
    """Broad segmented female crab pleon and short triangular telson."""
    g.setup(finish="direct")
    size = p["size"]
    hinge = rot(RIGHT, math.radians(72 * p["open"]))
    # Seam stations progress from the posterior hinge toward the sternum.
    seams = (
        (-.025, .112, .018), (.031, .151, -.004), (.075, .166, -.017),
        (.119, .170, -.023), (.206, .157, -.026), (.302, .075, -.019),
        (.372, .007, -.005),
    )
    for (z0, width0, y0), (z1, width1, y1) in zip(seams, seams[1:]):
        length = z1 - z0
        rings = []
        for t, bulge, depth in ((-.023, .96, .37), (.08, 1.00, .75),
                                  (.28, 1.02, .98), (.63, 1.02, 1),
                                  (.93, 1.00, .81), (1.019, .96, .38)):
            ring = []
            for index in range(28):
                theta = index * math.tau / 28
                lateral = math.cos(theta)
                width = (width0 + (width1 - width0) * t) * bulge
                y = y0 + (y1 - y0) * t - .017 * (1 - lateral**2)
                y += .010 * depth * math.sin(theta)
                z = z0 + length * t + .013 * lateral**2
                ring.append(hinge @ V(width * lateral, y, z) * size)
            rings.append(ring)
        _closed_rings(g, rings)


PARTS = [
    Part("opposed_terminal_forceps", "manipulation", "Two separately rooted male earwig cerci curve into a bilateral grip.",
         ["earwig", "forceps", "cerci", "abdomen"], {"size": SIZE, "open": (0., 1., .28)},
         opposed_terminal_forceps, orient="native", symmetry="center"),
    Part("overhanging_pronotal_crown", "aesthetics", "A treehopper pronotal crown holds four stalked globes and a free trailing spine.",
         ["treehopper", "pronotum", "crown", "Bocydium"], {"size": SIZE},
         overhanging_pronotal_crown, orient="native", symmetry="center"),
    Part("rigid_eyestalk_antenna_crown", "sensory", "A rigid lateral head projection seats a terminal eye and adjacent antenna.",
         ["diopsid", "stalk-eyed fly", "compound eye", "antenna"], {"size": SIZE},
         rigid_eyestalk_antenna_crown, orient="native", symmetry="pair"),
    Part("stiff_to_membranous_forewing", "locomotion", "A thick bug forewing plate transitions into a thin rounded membrane.",
         ["hemelytron", "stink bug", "corium", "clavus", "wing membrane"], {"size": SIZE, "raise": UNIT},
         stiff_to_membranous_forewing, orient="native", symmetry="pair"),
    Part("folding_pleonal_apron", "aesthetics", "A broad female crab pleon hinges up beneath the sternum.",
         ["crab", "pleon", "apron", "abdomen", "brood shelter"], {"size": SIZE, "open": UNIT},
         folding_pleonal_apron, orient="native", symmetry="center"),
]

TRAITS = {
    "opposed_terminal_forceps": {"function": "grasp"},
    "overhanging_pronotal_crown": {"function": "display"},
    "rigid_eyestalk_antenna_crown": {"function": "sense"},
    "stiff_to_membranous_forewing": {"function": "fly"},
    "folding_pleonal_apron": {"function": "protect"},
}
