"""External arthropod drafts with +Y dorsal and +Z anterior."""

import math

from ..kit import RIGHT, UP, V, rot
from . import Part
from .candidate_arthropod import _loft
from .candidate_queue_arthropods import SIZE, UNIT
from .research_locomotion import _closed_rings


def suction_disc_tarsal_palette(g, p):
    """Three expanded protarsal articles and a field of stalked, recessed discs."""
    g.setup(finish="direct")
    size = p["size"]
    lean = rot(RIGHT, math.radians(p["tilt"]))
    _loft(g, size, [lean @ V(v) for v in (
        (0, .006, .021), (0, .002, .003), (.002, -.001, -.037),
        (.003, -.003, -.067),
    )], ((.025, .018), (.032, .019), (.034, .017), (.027, .014)), up=UP)
    for index, (center, breadth, reach) in enumerate((
        (-.054, .080, .051), (-.127, .088, .042), (-.192, .066, .037),
    )):
        rings = []
        for s, width, thickness in ((-.95, .52, .60), (-.74, .83, .88),
                                    (-.36, .98, 1), (.31, 1, .92), (.72, .82, .70), (.99, .56, .45)):
            z = center + reach * s
            rings.append([lean @ V(breadth * width * math.cos(a * math.tau / 28),
                                    -.006 + .017 * thickness * math.sin(a * math.tau / 28) - .006 * index,
                                    z) * size for a in range(28)])
        _closed_rings(g, rings)

    def cup(x, z, radius, y):
        """Recessed face drawn by the last inward and returning rings."""
        rings = []
        for h, width in ((0, .18), (.38, .19), (.63, .51), (.86, .86), (1.03, 1),
                         (.99, .84), (.79, .64), (.66, .39), (.63, .12)):
            ring = []
            for a in range(12):
                angle = a * math.tau / 12
                ring.append(lean @ V(x + radius * width * math.cos(angle),
                                      y - .91 * radius * h,
                                      z + radius * width * math.sin(angle)) * size)
            rings.append(ring)
        _closed_rings(g, rings)

    cup(-.027, -.046, .038, -.017)
    cup(.032, -.088, .033, -.019)
    for row, (z, count, span, y) in enumerate((
        (-.048, 2, .021, -.019), (-.073, 3, .036, -.019), (-.111, 3, .066, -.020),
        (-.134, 5, .132, -.023), (-.153, 6, .132, -.024), (-.172, 6, .117, -.027),
        (-.192, 5, .100, -.027), (-.213, 4, .084, -.028), (-.229, 2, .033, -.026),
    )):
        for i in range(count):
            x = span * (i / (count - 1) - .5)
            # The first few small cups flank the two major ones.
            x += (.037, -.038, -.026)[row] if row < 3 else 0.
            cup(x, z - .0021 * (i % 2), (.0078 + .0011 * math.sin(row + i)), y)
    _loft(g, size, [lean @ V(v) for v in (
        (0, -.015, -.219), (0, -.013, -.245), (0, -.011, -.268),
        (0, -.012, -.286), (0, -.016, -.306),
    )], ((.019, .009), (.015, .008), (.013, .007), (.010, .006), (.006, .004)),
          up=UP, sides=19)


def petalled_pusher_foot(g, p):
    """Four supporting processes surrounding a long Limulus pretarsus."""
    g.setup(finish="direct")
    size, spread = p["size"], p["splay"]
    _loft(g, size, ((0, .012, .020), (0, .005, 0), (0, -.005, -.036),
                    (0, -.010, -.084), (0, -.009, -.116)),
          ((.024, .020), (.031, .024), (.032, .024), (.030, .025), (.026, .021)),
          up=UP)
    _loft(g, size, (
        (0, -.011, -.104), (0, -.015, -.135), (0, -.020, -.168),
        (0, -.024, -.207), (.002, -.029, -.245), (.003, -.032, -.259),
    ), ((.018, .016), (.017, .015), (.015, .013), (.012, .010),
        (.008, .007), (.005, .005)), up=UP)
    claw = rot(RIGHT, math.radians(23 * p["tip"]))
    tip = V(.003, -.030, -.249)
    _loft(g, size, [tip + claw @ V(v) for v in (
        (0, 0, .006), (0, -.001, -.010), (0, -.009, -.026),
        (0, -.018, -.034), (0, -.023, -.033),
    )], ((.0065, .006), (.006, .005), (.0045, .0035), (.0025, .002),
          (.00065, .00085)), up=RIGHT, sides=14)

    for index, lateral in enumerate((38, 119, 210, 295)):
        radial = rot(V(0, 0, 1), math.radians(lateral))
        base = V(0, -.01, -.105) + radial @ V(.024, 0, 0)
        joint = radial @ rot(UP, math.radians(-42 * spread))
        reach = (.153, .166, .147, .135)[index]
        _loft(g, size, [base + joint @ V(v) for v in (
            (-.005, 0, .011), (.004, 0, -.006), (.012, 0, -.032),
            (.021, -.002, -.066), (.023, -.004, -.105), (.018, -.006, -reach + .019),
            (.012, -.006, -reach),
        )], ((.012, .009), (.015, .011), (.023, .010), (.029, .008),
             (.028, .007), (.020, .005), (.0055, .003)), up=radial @ RIGHT, sides=20)


def antenniform_feeling_leg(g, p):
    """A proximal walking-leg linkage transitions into a long flexible distal chain."""
    g.setup(finish="direct")
    size, sweep = p["size"], p["sweep"]
    yaw = rot(UP, math.radians(-25 + 55 * sweep))
    _loft(g, size, [yaw @ V(v) for v in (
        (-.017, .006, -.005), (-.001, .006, -.002), (.029, .006, .003),
        (.049, .005, .012), (.067, .006, .021),
    )], ((.019, .018), (.022, .019), (.024, .020),
         (.019, .016), (.018, .014)), up=UP)
    for start, finish, radius in (
        ((.058, .005, .016), (.084, .003, .039), .016),
        ((.079, .003, .034), (.294, -.013, .100), .012),
        ((.289, -.013, .098), (.320, -.012, .122), .0093),
        ((.313, -.012, .119), (.527, -.014, .203), .0074),
        ((.520, -.014, .199), (.576, -.013, .259), .0059),
    ):
        a, b = V(start), V(finish)
        _loft(g, size, [yaw @ a, yaw @ a.lerp(b, .15), yaw @ a.lerp(b, .85), yaw @ b],
              (radius * .77, radius, radius * .94, radius * .68), up=UP, sides=18)
    # Coarse tarsal articles follow a flexible, unbroken sensory chain.
    root = V(.573, -.013, .255)
    for index in range(27):
        t = index / 26
        extent = .034 - .015 * t
        angle = math.radians(41 + 36 * t - 46 * sweep * t + 14 * math.sin(math.pi * t))
        axis = V(math.cos(angle), -.038 + .09 * t, math.sin(angle))
        end = root + axis * extent
        radius = .0048 - .0036 * t
        _loft(g, size, [yaw @ (root - axis * .00055), yaw @ root.lerp(end, .13),
                        yaw @ root.lerp(end, .84), yaw @ end],
              (radius * .80, radius, radius * .92, radius * .60), up=UP,
              sides=12, density=3)
        root = end


def eversible_ventral_tube_pair(g, p):
    """Sminthurid collophore with two long recurving eversible vesicles."""
    g.setup(finish="direct")
    size, reach = p["size"], p["reach"]
    rings = []
    # Passage is modeled externally as a cylindrical rim and recessed base.
    for y, x, z in (
        (.027, .033, .025), (.001, .040, .028), (-.048, .036, .024),
        (-.088, .031, .022), (-.108, .028, .022), (-.119, .026, .021),
        (-.118, .019, .015), (-.108, .016, .011), (-.091, .013, .010),
    ):
        rings.append([V(x * math.cos(a * math.tau / 24), y,
                        .014 * (1 - y / .027) / 5 + z * math.sin(a * math.tau / 24)) * size
                      for a in range(24)])
    _closed_rings(g, rings)
    center = V(0, -.088, .015)
    extend = .066 + .934 * reach
    for side in (-1, 1):
        stations = (
            (.010, 0, 0), (.018, -.028, .001), (.043, -.045, .003),
            (.091, -.056, .009), (.151, -.060, .016), (.208, -.069, .027),
            (.246, -.089, .035), (.253, -.121, .045), (.236, -.149, .054),
            (.213, -.151, .057),
        )
        _loft(g, size, [center + V(side * x * extend, y * extend, z * extend)
                         for x, y, z in stations],
              tuple(radius * (.44 + .56 * reach) for radius in
                    (.013, .015, .014, .011, .010, .011, .014, .016, .017, .012)),
              up=UP, sides=20)


PARTS = [
    Part("suction_disc_tarsal_palette", "manipulation", "A beetle protarsal palette carries two large discs and staggered smaller cups.",
         ["diving beetle", "palette", "suction", "tarsus"], {"size": SIZE, "tilt": (-25., 25., 0.)},
         suction_disc_tarsal_palette, orient="native", symmetry="pair"),
    Part("petalled_pusher_foot", "locomotion", "Four deployable processes frame the tip of a horseshoe crab pushing leg.",
         ["horseshoe crab", "pusher", "pretarsus", "flaps"], {"size": SIZE, "splay": (0., 1., .4), "tip": UNIT},
         petalled_pusher_foot, orient="native", symmetry="pair"),
    Part("antenniform_feeling_leg", "sensory", "A short leg linkage carries a long, finely jointed tactile reach.",
         ["whip spider", "tactile leg", "antenniform", "tarsus"], {"size": SIZE, "sweep": (0., 1., .4)},
         antenniform_feeling_leg, orient="native", symmetry="pair"),
    Part("eversible_ventral_tube_pair", "manipulation", "Two recurved soft vesicles deploy from one ventral tube.",
         ["springtail", "collophore", "ventral tube", "vesicles"], {"size": SIZE, "reach": (0., 1., .85)},
         eversible_ventral_tube_pair, orient="native", symmetry="center"),
]

TRAITS = {
    "suction_disc_tarsal_palette": {"function": "grasp"},
    "petalled_pusher_foot": {"function": "walk"},
    "antenniform_feeling_leg": {"function": "sense"},
    "eversible_ventral_tube_pair": {"function": "adhere"},
}
