"""Local arthropod anatomy drafts in a +Y dorsal, +Z anterior frame.

Each origin is the nominal attachment point. Pose controls change static
comparison shapes for inspecting the parts; angles are authored, not measured.
"""

import math

from ..kit import RIGHT, UP, V, rot
from . import Part
from .candidate_arthropod import _loft
from .research_locomotion import _closed_rings


SIZE = (.5, 1.8, 1.)
UNIT = (0., 1., 0.)


def coiling_siphoning_proboscis(g, p):
    """Joined monarch galeae with a narrowing coil and a closed apex."""
    g.setup(finish="direct")
    size = p["size"]
    uncoil = p["uncoil"]
    count = 137
    step = .40 / (count - 1)
    total_bend = 16.25 * (1 - uncoil)**1.25 + .64 * uncoil
    center = V(0, 0, -.012)
    rings = []
    for index in range(count):
        u = index / (count - 1)
        # The curled distal region has tighter bends than the base. The
        # station distance stays constant while the centerline deploys.
        turn = -.11 + total_bend * (.53 * u + .47 * u**2)
        normal = V(0, math.cos(turn), math.sin(turn))
        taper = (1 - u)**.48
        radius = .00135 + .0046 * taper
        ring = []
        for point in range(20):
            theta = math.tau * point / 20
            across = math.cos(theta)
            depth = math.sin(theta) * (1 - .25 * math.exp(-(across / .24)**2))
            ring.append((center + RIGHT * (radius * across) + normal * (radius * .77 * depth)) * size)
        rings.append(ring)
        mid = u + .5 / (count - 1)
        turn = -.11 + total_bend * (.53 * mid + .47 * mid**2)
        center += V(0, -math.sin(turn), math.cos(turn)) * step
    _closed_rings(g, rings)


def opposed_spined_foreleg(g, p):
    """Mantis coxa, deep spined femur and opposing tibia with a slender tarsus."""
    g.setup(finish="direct")
    size = p["size"]
    knee = V(0, -.121, .292)
    _loft(g, size, ((0, .015, -.022), (0, -.006, .005), (0, -.041, .025),
                    (0, -.084, .056), (0, -.105, .074), (0, -.114, .089)),
          ((.016, .014), (.022, .017), (.022, .018), (.017, .014),
           (.014, .012), (.015, .013)), up=RIGHT)
    _loft(g, size, ((0, -.105, .073), (0, -.112, .094), (0, -.120, .132),
                    (0, -.118, .173), (0, -.115, .219), (0, -.118, .268), knee),
          ((.013, .015), (.018, .022), (.025, .033), (.028, .038),
           (.023, .034), (.016, .023), (.013, .014)), up=RIGHT)
    for side, spine_count, length in ((-1, 9, .021), (1, 6, .028)):
        for i in range(spine_count):
            t = i / (spine_count - 1)
            start = V(side * (.013 - .006 * t), -.146 - .005 * math.sin(math.pi * t), .134 + .132 * t)
            reach = length * (1.04 - .27 * t) * (1 if i % 2 == 0 else .78)
            _loft(g, size, (start, start + V(side * .002, -.5 * reach, .002),
                            start + V(side * .002, -reach, .008)),
                  (.0053 - .0014 * t, .0034 - .0009 * t, .00065), up=RIGHT, sides=12, density=3)

    tilt = rot(RIGHT, -math.radians(4 + p["open"] * 96))

    def tibia(point):
        return knee + tilt @ V(point)

    _loft(g, size, [tibia(v) for v in (
        (0, 0, .007), (.004, -.018, -.013), (.009, -.032, -.05),
        (.012, -.043, -.099), (.018, -.051, -.146), (.022, -.058, -.176),
    )], ((.012, .013), (.015, .014), (.014, .013), (.012, .010),
         (.009, .008), (.006, .007)), up=RIGHT)
    for side, spine_count in ((-1, 11), (1, 8)):
        for i in range(spine_count):
            t = i / (spine_count - 1)
            root = V(.010 + .011 * t + side * .007, -.022 - .030 * t, -.033 - .128 * t)
            _loft(g, size, [tibia(root + v) for v in
                            (V(0, 0, 0), V(side * .002, .008, .002),
                             V(side * .003, .017 - .004 * t, .006))],
                  (.0036, .0024, .00048), up=RIGHT, sides=10, density=3)
    _loft(g, size, [tibia(v) for v in (
        (.022, -.057, -.172), (.022, -.049, -.181), (.022, -.039, -.182),
        (.022, -.030, -.177), (.022, -.028, -.167),
    )], (.0058, .0053, .0038, .0024, .00065), up=RIGHT, sides=12, density=3)
    start = V(.022, -.058, -.173)
    for length, r0 in ((.017, .0056), (.014, .0046), (.011, .0035), (.009, .0026)):
        end = start + V(.002, -.52 * length, -.85 * length)
        _loft(g, size, [tibia(start), tibia(start.lerp(end, .34)), tibia(end)],
              [r0 * .80, r0, r0 * .62], up=RIGHT, sides=12, density=3)
        start = end


def fossorial_tibial_shovel(g, p):
    """Four toothed mole-cricket tibial blade with an offset articulated tarsus."""
    g.setup(finish="direct")
    size = p["size"]
    turn = rot(RIGHT, math.radians(p["pitch"]))
    # Side outline around the single rigid tibial shell. The four teeth are
    # continuous with the shovel and decrease toward the tarsal roots.
    outline = (
        (.028, -.014), (.041, .010), (.050, .068), (.081, .141),
        (.097, .192), (.093, .216), (.078, .231), (.073, .230),
        (.072, .210), (.062, .169), (.049, .176), (.048, .210),
        (.034, .240), (.024, .247), (.018, .243), (.021, .229),
        (.019, .192), (.010, .177), (.002, .182), (.003, .218),
        (-.011, .237), (-.022, .241), (-.028, .236), (-.022, .220),
        (-.022, .188), (-.031, .173), (-.039, .174), (-.046, .207),
        (-.059, .217), (-.066, .216), (-.066, .208), (-.057, .186),
        (-.056, .165), (-.048, .135), (-.044, .102), (-.039, .053),
        (-.034, .012), (-.023, -.012), (-.006, -.021), (.014, -.021),
    )
    rings = []
    for x, factor in ((-.021, .77), (-.012, .98), (.001, 1), (.014, .96), (.021, .73)):
        ring = []
        for y, z in outline:
            depth = x * (1 - .70 * max(0., (z - .15) / .10))
            ring.append(turn @ V(depth, y * factor, .095 + (z - .095) * factor) * size)
        rings.append(ring)
    _closed_rings(g, rings)
    tarsus_root = V(.016, -.046, .137)
    tarsus_turn = rot(RIGHT, math.radians(-10 - 40 * p["tarsus"]))

    def foot(v):
        return turn @ (tarsus_root + tarsus_turn @ V(v))

    for path, radii in (
        (((0, 0, -.012), (.009, -.010, .009), (.014, -.028, .025)),
         ((.011, .012), (.014, .024), (.009, .012))),
        (((.014, -.027, .021), (.021, -.042, .034), (.020, -.056, .042)),
         ((.010, .012), (.010, .019), (.007, .010))),
        (((.020, -.055, .039), (.023, -.068, .047), (.022, -.085, .052)),
         (.007, .006, .0042)),
    ):
        _loft(g, size, [foot(v) for v in path], radii, up=RIGHT, sides=16, density=4)
    for side in (-1, 1):
        _loft(g, size, [foot(v) for v in ((.022 + side * .003, -.083, .051),
                                        (.022 + side * .004, -.094, .060),
                                        (.022 + side * .005, -.093, .070))],
              (.003, .0022, .0006), up=RIGHT, sides=10, density=3)


def clubbed_halter_balance_organ(g, p):
    """Housefly haltere with a bent shaft, basal shoulder and pendant club."""
    g.setup(finish="direct")
    size = p["size"]
    swing = rot(UP, math.radians(p["sweep"]))
    _loft(g, size, [swing @ V(v) for v in (
        (0, 0, -.018), (0, 0, -.008), (0, 0, .003), (.001, .001, .023),
        (.003, .002, .041), (.006, .004, .066), (.009, .003, .093),
        (.014, .000, .111), (.018, -.005, .120), (.024, -.018, .123),
        (.028, -.029, .125), (.031, -.041, .126), (.032, -.047, .126),
    )], ((.009, .008), (.013, .011), (.012, .010), (.007, .006),
         (.005, .005), (.005, .0045), (.0048, .0052), (.0065, .007),
         (.010, .010), (.017, .014), (.019, .016), (.014, .012), (.005, .005)),
          up=RIGHT, sides=24, density=4)


def bipectinate_sensory_antenna(g, p):
    """Silkmoth antennal stem and two arrays of macroscopic flagellar rami."""
    g.setup(finish="direct")
    size = p["size"]
    turn = rot(UP, math.radians(p["yaw"]))
    def stem(t):
        return V(0, .175 * t - .32 * t**2.45, .345 * t)

    stations = (-.05, 0, .09, .22, .37, .60, .81, .95, 1)
    _loft(g, size, [turn @ stem(max(0, t)) + turn @ V(0, 0, min(0, t) * .345)
                    for t in stations],
          ((.009, .008), (.011, .009), (.010, .008), (.008, .007),
           (.0071, .0055), (.005, .0042), (.0032, .0030), (.0022, .002),
           (.0010, .0009)), up=RIGHT)
    for i in range(34):
        u = i / 33
        t = .115 + .858 * u
        root = stem(t) + V(0, -.0015, 0)
        tangent = (stem(t + .0001) - stem(t)).normalized()
        inward = RIGHT.cross(tangent).normalized()
        length = .012 + .102 * math.sin(math.pi * u**.77)**.89
        thick = .0016 + .0017 * (1 - u)
        for side in (-1, 1):
            # The rows enclose a shallow basket beneath the curved stem.
            branch = length * (inward * .866 + RIGHT * (side * .5))
            points = (root, root + branch * .23 + tangent * .004,
                      root + branch * .56 + tangent * .013,
                      root + branch * .84 + tangent * .022,
                      root + branch + tangent * (.018 + .004 * (1 - u)))
            _loft(g, size, [turn @ v for v in points],
                  ((thick, thick * .94), (thick * .9, thick * .92),
                   (thick * .70, thick * .76), (thick * .51, thick * .57), (.00040, .00047)),
                  up=UP, sides=10, density=3)


def hooked_soft_abdominal_proleg(g, p):
    """Hornworm proleg with a soft, retracting planta and a crescent of crochets."""
    g.setup(finish="direct")
    size = p["size"]
    compress = p["compress"]
    depth = 1 - .26 * compress
    spread = 1 + .13 * compress
    _loft(g, size, [(x, y * depth, z) for x, y, z in (
        (0, .027, -.005), (0, .012, -.005), (0, -.008, -.006),
        (.004, -.024, -.004), (.012, -.046, -.002), (.017, -.066, 0),
        (.018, -.081, .001), (.019, -.098, .003), (.019, -.106, .003),
    )], [(.053, .052), (.080, .070), (.084, .074), (.063, .060),
         (.063, .065), (.058, .058), (.050 * spread, .054 * spread),
         (.054 * spread, .058 * spread), (.038 * spread, .046 * spread)], up=RIGHT)
    for index in range(18):
        angle = math.radians(-104 + 208 * index / 17)
        direction = V(math.cos(angle), 0, math.sin(angle))
        y = -.098 * depth
        root = direction * (.047 * spread) + V(.019, y, .003)
        length = .0115 if index % 2 else .014
        down = UP * (-length * (1 - .47 * compress))
        _loft(g, size, (root, root + down * .53 + direction * .002,
                        root + down * .94 - direction * .002,
                        root + down * .86 - direction * .0061),
              (.0028, .0026, .0017, .00055), up=RIGHT, sides=10, density=3)


PARTS = [
    Part("coiling_siphoning_proboscis", "feeding", "A joined pair of flexible galeae stows in a narrowing ventral coil.",
         ["monarch", "butterfly", "proboscis", "galeae"], {"size": SIZE, "uncoil": UNIT},
         coiling_siphoning_proboscis, orient="native", symmetry="center"),
    Part("opposed_spined_foreleg", "manipulation", "A long coxa carries a mantis femur and opposing spined tibia.",
         ["mantis", "foreleg", "coxal grasp", "raptorial"], {"size": SIZE, "open": (0., 1., .25)},
         opposed_spined_foreleg, orient="native", symmetry="pair"),
    Part("fossorial_tibial_shovel", "locomotion", "A four-tooth tibial shovel articulates beside an inset tarsus.",
         ["mole cricket", "digging", "tibia", "fossorial"],
         {"size": SIZE, "pitch": (-32., 32., 0.), "tarsus": (0., 1., .65)},
         fossorial_tibial_shovel, orient="native", symmetry="pair"),
    Part("clubbed_halter_balance_organ", "sensory", "A reduced fly hindwing has a narrow shaft, bulb and basal swing.",
         ["housefly", "haltere", "balance", "flight sensation"], {"size": SIZE, "sweep": (-32., 32., 0.)},
         clubbed_halter_balance_organ, orient="native", symmetry="pair"),
    Part("bipectinate_sensory_antenna", "sensory", "A silkmoth antennal stem carries tapering lateral rami on both sides.",
         ["silkmoth", "antenna", "pectinate", "rami"], {"size": SIZE, "yaw": (-28., 28., 0.)},
         bipectinate_sensory_antenna, orient="native", symmetry="pair"),
    Part("hooked_soft_abdominal_proleg", "locomotion", "A soft caterpillar proleg carries a crescent of jointless cuticular hooks.",
         ["hornworm", "caterpillar", "proleg", "crochets"], {"size": SIZE, "compress": UNIT},
         hooked_soft_abdominal_proleg, orient="native", symmetry="pair"),
]

TRAITS = {
    "coiling_siphoning_proboscis": {"function": "feed"},
    "opposed_spined_foreleg": {"function": "grasp"},
    "fossorial_tibial_shovel": {"function": "dig"},
    "clubbed_halter_balance_organ": {"function": "balance"},
    "bipectinate_sensory_antenna": {"function": "sense"},
    "hooked_soft_abdominal_proleg": {"function": "grasp"},
}
