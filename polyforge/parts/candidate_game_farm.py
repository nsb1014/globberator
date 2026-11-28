"""Farm-animal surface fixtures in metres, with +Y up and +Z toward the muzzle."""

import math

from scipy.interpolate import PchipInterpolator

from ..kit import BACK, V
from . import Part
from .research_locomotion import _closed_rings


ANGLES = tuple(math.tau * index / 32 for index in range(32))


def _rounded_stations(stations):
    """Sample the section profile densely before voxel finishing and carving."""
    last = len(stations) - 1
    curve = PchipInterpolator(range(len(stations)), stations, axis=0)
    return curve([i / 4 for i in range(4 * last + 1)])


def suid_rostral_disc(g, p):
    """Low oval rooting surface with two forward-facing blind recesses."""
    size, width, flare = (p[name] for name in ("size", "width", "flare"))
    g.setup(voxel=.0013 * size, detail=2.8, smooth=.68)
    rings = []
    for z, w, h, raised in _rounded_stations(((-.025, .040, .027, -.006), (-.020, .047, .032, -.005),
                                               (-.009, .050, .035, -.003), (.009, .060, .038, -.001),
                                               (.021, .064, .039, 0.), (.028, .060, .036, .001),
                                               (.0305, .051, .029, .001), (.032, .028, .018, .002),
                                               (.0325, .004, .004, .002))):
        ring = []
        for angle in ANGLES:
            across, up = math.cos(angle), math.sin(angle)
            x, y = w * across * (1. + .085 * up), h * up
            lower_midline = .0055 * max(0., -up)**2 * math.exp(-(x / .017)**2)
            lower_midline *= min(1., max(0., (z + .008) / .029))
            ring.append(V(x * width, raised + y + lower_midline, z + .15 * y - .85 * x * x) * size)
        rings.append(ring)
    _closed_rings(g, rings)

    for side in (-1., 1.):
        g.cut_loft([V(side * x * width, y, z) * size for x, y, z in
                    ((.025, .003, .009), (.027, .002, .014), (.029, .002, .024),
                     (.031, .002, .035), (.033, .002, .046))],
                   [(w * flare * size, h * flare * size) for w, h in
                    ((.0017, .002), (.0048, .0062), (.0072, .010), (.0102, .014), (.0107, .014))],
                   sides=24, density=3, up=V(side * .39, 1., 0.))


def bovine_four_quarter_udder(g, p):
    """One suspended body with a shallow median cleft and four seated teats."""
    size, fullness, teat_length = (p[name] for name in ("size", "fullness", "teat_length"))
    g.setup(voxel=.0031 * size, detail=2.9, smooth=.72)
    rings = []
    for y, width, depth, center_z in _rounded_stations((
            (.032, .095, .148, .014), (.016, .131, .184, .019),
            (-.018, .153, .199, .009), (-.059, .157, .184, -.007),
            (-.095, .141, .154, -.016), (-.123, .111, .114, -.018),
            (-.142, .069, .070, -.018), (-.151, .005, .008, -.018))):
        ring = []
        for angle in ANGLES:
            across, fore = math.cos(angle), math.sin(angle)
            x, z = width * across * (1. - .10 * fore), depth * fore
            cleft = math.exp(-(x / .034) ** 2) * min(1., max(0., (-y - .020) / .075))
            # The median groove continues up the rear face between the hind quarters.
            rear_cleft = .019 * math.exp(-(x / .025)**2) * max(0., -fore)**5
            rear_cleft *= min(1., max(0., (.031 - y) / .043))
            ring.append(V(x, (y + .012 * cleft * (1. - 2.5 * z) + .105 * z) * fullness,
                          center_z + z + rear_cleft) * size)
        rings.append(ring)
    _closed_rings(g, rings)

    for side in (-1., 1.):
        for x, y, z, radius, length, rake in ((.082, -.099, .065, .015, .065, .012),
                                               (.068, -.116, -.091, .014, .062, -.007)):
            points = [V(side * (x + .007 * t), y * fullness - length * teat_length * t,
                        z + rake * t) * size for t in (-.13, .12, .42, .78, 1.)]
            g.loft(points, [radius * size * scale for scale in (1.35, 1.05, .88, .76, .55)],
                   sides=18, up=BACK, density=3)


# Each peak has a closely spaced leading shoulder and a raked trailing edge.
# The broad blade after the fifth point overhangs the posterior attachment.
COMB_PROFILE = (
    (.060, -.004, .004, .0023), (.056, -.006, .014, .0036),
    (.049, -.009, .026, .0045), (.044, -.011, .038, .0044),
    (.040, -.012, .022, .0055), (.034, -.014, .025, .0055),
    (.030, -.016, .055, .0052), (.026, -.017, .049, .0057),
    (.021, -.018, .033, .0066), (.016, -.018, .034, .0068),
    (.011, -.019, .064, .0062), (.006, -.019, .058, .0067),
    (.001, -.019, .039, .0075), (-.005, -.019, .041, .0076),
    (-.011, -.019, .067, .0069), (-.016, -.018, .061, .0073),
    (-.021, -.016, .042, .0077), (-.026, -.015, .043, .0078),
    (-.032, -.013, .059, .0074), (-.038, -.010, .052, .0075),
    (-.045, -.004, .038, .0078), (-.054, .007, .035, .0070),
    (-.062, .014, .030, .0058), (-.070, .017, .023, .0039),
    (-.075, .018, .020, .0018),
)


def chicken_single_comb(g, p):
    """Fleshy midline sheet, with five points and one broad trailing blade."""
    size, height, cant = (p[name] for name in ("size", "height", "cant"))
    g.setup(finish="subsurf_low")
    rings = []
    for z, root, edge, thickness in COMB_PROFILE:
        ring = []
        for angle in ANGLES[::2]:
            side, level = math.cos(angle), (1. + math.sin(angle)) * .5
            y = root + level * (edge - root)
            if y > 0.:
                y *= height
            x = side * thickness * (1.10 - .58 * level) + cant * .014 * level * level
            ring.append(V(x, y, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def chicken_paired_wattles(g, p):
    """Two hanging lateral skin lobes with a persistent medial cleft."""
    size, drop, splay = (p[name] for name in ("size", "drop", "splay"))
    g.setup(finish="subsurf_low")
    for side in (-1., 1.):
        rings = []
        for y, x, z, thickness, length in ((.014, .013, .007, .0034, .011),
                                             (.004, .014, .009, .0046, .020),
                                             (-.012, .016, .012, .0051, .025),
                                             (-.032, .018, .016, .0050, .026),
                                             (-.050, .019, .020, .0047, .023),
                                             (-.064, .018, .024, .0040, .017),
                                             (-.074, .017, .026, .0031, .010),
                                             (-.079, .016, .025, .0016, .0034)):
            drift = splay * .010 * (max(0., -y) / .079) ** 1.6
            ring = []
            for angle in ANGLES[::2]:
                across, fore = math.cos(angle), math.sin(angle)
                ring.append(V(side * (x + drift + thickness * across + .18 * length * fore),
                              min(y, 0.) * drop + max(y, 0.), z + length * fore) * size)
            rings.append(ring)
        _closed_rings(g, rings)


SIZE = (.60, 1.65, 1.)
PARTS = [
    Part("suid_rostral_disc", "sensory", "Terminal rooting pad with a turned oval rim and two recessed nostrils.",
         ["pig", "boar", "suid", "rooting disc", "nose", "nostrils"],
         {"size": SIZE, "width": (.82, 1.22, 1.), "flare": (.68, 1.20, 1.)},
         suid_rostral_disc, orient="native", symmetry="center", hint={"u": .98, "theta": -90.}),
    Part("bovine_four_quarter_udder", "feeding", "Ventral bovine udder with a median cleft and four continuous teat roots.",
         ["cattle", "cow", "udder", "mammary", "teats"],
         {"size": SIZE, "fullness": (.85, 1.22, 1.), "teat_length": (.72, 1.28, 1.)},
         bovine_four_quarter_udder, orient="native", symmetry="center", hint={"u": .23, "theta": -90.}),
    Part("chicken_single_comb", "aesthetics", "Five-point single comb on a fleshy midline blade with a free posterior end.",
         ["chicken", "rooster", "cockscomb", "single comb", "fleshy crest"],
         {"size": SIZE, "height": (.65, 1.28, 1.), "cant": (-.8, .8, .12)},
         chicken_single_comb, orient="native", symmetry="center", hint={"u": .94, "theta": 90.}),
    Part("chicken_paired_wattles", "aesthetics", "Two pendant cutaneous lobes with independent jaw-side seats and a medial cleft.",
         ["chicken", "rooster", "wattles", "throat", "cutaneous lobes"],
         {"size": SIZE, "drop": (.68, 1.28, 1.), "splay": (-.40, 1., 0.)},
         chicken_paired_wattles, orient="native", symmetry="center", hint={"u": .94, "theta": -90.}),
]
TRAITS = {
    "suid_rostral_disc": {"function": "sense", "construction": "deformable"},
    "bovine_four_quarter_udder": {"function": "feed", "construction": "deformable"},
    "chicken_single_comb": {"function": "display", "construction": "deformable"},
    "chicken_paired_wattles": {"function": "display", "construction": "deformable"},
}
