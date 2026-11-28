"""Swimming, suspension-feeding and support parts for marine invertebrates."""

from math import cos, exp, pi, radians, sin, tau

from scipy.interpolate import PchipInterpolator

from ..kit import BACK, RIGHT, UP, V, lerp, rot, smoothstep
from . import Part
from .candidate_invertebrate import _sized
from .research_locomotion import _closed_rings


def pedal_swimming_wings(g, p):
    # Authored starboard, with the stroke moving about the short +Z root axis.
    rotation = rot(BACK, radians(p["stroke"]))
    sections = (
        (-.003, -.002, .0065, .0027), (0., -.002, .0080, .0025),
        (.004, -.002, .0102, .0015), (.009, -.003, .0128, .0011),
        (.015, -.004, .0118, .00092), (.021, -.005, .0090, .00073),
        (.027, -.006, .0053, .00054), (.031, -.005, .0014, .00040),
        (.032, -.005, .0004, .00025),
    )
    rings = []
    for x, center, chord, thickness in sections:
        ratio = max(0., x / .032)
        local_pitch = rot(RIGHT, radians(24 * ratio * p["twist"]))
        ring = []
        for index in range(28):
            theta = tau * index / 28
            z = chord * cos(theta)
            y = thickness * sin(theta) + .15 * chord * sin(theta)**2
            cross = local_pitch @ V(0, y, z)
            point = V(x, ratio**2 * .005 * p["twist"], center) + cross
            ring.append(rotation @ point)
        rings.append(ring)
    g.slot("paddle")
    _closed_rings(g, rings)


def dendritic_oral_collecting_tentacle(g, p):
    spread = p["spread"]
    curl = 1 - spread

    def stem(t):
        return V(.031 * curl * t**2, lerp(-.006, .086, t) - .034 * curl * t**2, .009 * t**2)

    g.slot("stem")
    stations = (0., .15, .36, .60, .80, 1.)
    g.loft([stem(t) for t in stations],
           [.0046, .0042, .0037, .0032, .0022, .0011], sides=18, up=RIGHT)

    g.slot("branches")
    for index in range(11):
        t = .39 + .055 * index
        seat = stem(t)
        theta = index * 2.399
        radial = V(cos(theta), 0., sin(theta))
        tangent = UP.cross(radial)
        radius = (.023 + .019 * sin(pi * (index + .60) / 12) ** .85) * (.38 + .62 * spread)
        reach = radial * radius + UP * (.013 + .031 * curl)
        center = seat + .52 * reach
        tip = seat + reach + tangent * .0031
        g.loft([seat, center, tip], [.0020, .00155, .00053], sides=10, up=UP, density=3)
        for leaflet in range(5):
            amount = .30 + .135 * leaflet
            root = seat.lerp(tip, amount) - tangent * .0007
            side = 1 if leaflet % 2 else -1
            fork = tangent * (.009 + .005 * sin(pi * amount)) * spread * side
            fork += UP * (.010 + .005 * curl) + radial * .004
            g.loft([root, root + fork * .53, root + fork],
                   [.00104, .00074, .00038], sides=8, up=radial, density=2)
            for terminal in (-1, 1):
                joint = root + fork * (.58 if terminal > 0 else .72)
                twig = UP * .005 + radial * (.0025 * terminal) + fork * .22
                g.loft([joint, joint + twig * .55, joint + twig],
                       [.00048, .00038, .00025], sides=6, up=radial, density=2)


def crinoid_pinnulate_arm(g, p):
    def center(t):
        turn = p["curl"] * t * t
        return V(.028 * turn, .054 * turn, -.004 + .153 * t - .052 * turn)

    g.slot("arm")
    rings = []
    for station in range(85):
        t = station / 84
        point = center(t)
        vertical = (center(t + .002) - point).normalized().cross(RIGHT)
        width = lerp(.0069, .0030, t) - .00042 * cos(tau * 14 * t)
        depth = lerp(.0057, .0024, t)
        ring = []
        for index in range(36):
            angle = tau * index / 36
            groove = .0016 * max(0., cos(angle)) ** 42 * (1. - .60 * t)
            ring.append(point + RIGHT * (width * sin(angle)) + vertical * (depth * cos(angle) - groove))
        rings.append(ring)
    _closed_rings(g, rings)

    g.slot("pinnules")
    for index in range(18):
        t = .09 + .045 * index
        side = -1 if index % 2 else 1
        root = center(t) + V(side * lerp(.0051, .0023, t), .0017, 0)
        tangent = (center(t + .015) - center(t)).normalized()
        extent = lerp(.034, .017, t) * (.76 + .24 * sin(pi * t))
        lateral = V(side * extent, .14 * extent, 0)
        along = tangent * (extent * (.42 + .23 * p["curl"]))
        positions = [root + (lateral * s + along * s * s) for s in (0., .15, .32, .53, .74, 1.)]
        g.loft(positions, [.00185, .00162, .00134, .00109, .00074, .00024],
               sides=12, up=UP, density=2)


def ophiuroid_jointed_arm(g, p):
    turn = radians(p["bend"])
    length = .152

    def center(t):
        angle = turn * t
        if abs(turn) < 1e-6:
            return V(0, .002 * t**2, length * t - .004)
        return V(length * (1 - cos(angle)) / turn, .002 * t**2, length * sin(angle) / turn - .004)

    g.slot("joint_tissue")
    g.loft([center(i / 15) for i in range(16)],
           [(.0053 - .0031 * i / 15, .0048 - .0029 * i / 15) for i in range(16)],
           sides=20, up=UP, density=2)
    for index in range(15):
        t = (index + .40) / 15
        station = center(t)
        advance = (center(t + .03) - station).normalized()
        lateral = UP.cross(advance)
        thickness = lerp(.0062, .0028, t)
        g.slot("plates")
        g.loft([center(t - .025), station + UP * (.25 * thickness), center(t + .027)],
               [(thickness * .73, thickness * .76), (thickness * .85, thickness * .88),
                (thickness * .68, thickness * .71)], sides=14, up=UP, density=2)
        for side in (1, -1):
            wall = station + lateral * (side * thickness * .59)
            g.loft([wall - advance * .0034, wall, wall + advance * .0037],
                   [(thickness * .26, thickness * .50), (thickness * .35, thickness * .67),
                    (thickness * .23, thickness * .49)], sides=10, up=UP, density=2)
            g.slot("spines")
            for row in range(5):
                theta = radians(-28 + row * 19)
                span = thickness * lerp(1.07, 2.17, row / 4)
                root = wall + lateral * (side * thickness * .28) + UP * (thickness * (-.5 + .245 * row))
                ray = side * cos(theta) * lateral + sin(theta) * UP + advance * .55
                g.loft([root, root + ray * span * .53, root + ray * span],
                       [thickness * .095, thickness * .071, thickness * .029],
                       sides=8, up=UP, density=1)
            g.slot("plates")


_FLOAT_SECTIONS = (
    (-.109, .002, .002, .004, 0.), (-.099, .011, .009, .007, .002),
    (-.083, .022, .017, .007, .014), (-.052, .028, .025, .007, .030),
    (-.012, .031, .030, .008, .039), (.035, .029, .032, .008, .040),
    (.076, .024, .028, .011, .034), (.102, .014, .018, .013, .023),
    (.115, .006, .009, .013, .007), (.120, .001, .003, .013, 0.),
)
_FLOAT_PROFILE = PchipInterpolator([s[0] for s in _FLOAT_SECTIONS], [s[1:] for s in _FLOAT_SECTIONS])


def surface_float_sail(g, p):
    rings = []
    for row in range(71):
        z = lerp(-.109, .120, row / 70)
        width, height, lift, sail = _FLOAT_PROFILE(z)
        ring = []
        for index in range(56):
            a = -pi + tau * index / 56
            sail_ridge = exp(-(a / .25) ** 2) * sail * p["rise"]
            lateral = .016 * p["lean"] * (sail_ridge / .040)
            pleat = 1 + .068 * sin(226 * z) + .036 * sin(443 * z + .5)
            y = float(lift + height * cos(a) + sail_ridge * pleat)
            x = float(width * sin(a) + lateral)
            ring.append(V(x, y, z))
        rings.append(ring)
    g.slot("float")
    _closed_rings(g, rings)


_SIZE = {"size": (.65, 1.50, 1.)}
PARTS = [
    Part("pedal_swimming_wings", "locomotion", "A sea-angel pedal wing with a fleshy root and twistable paddle.",
         ["sea angel", "clione", "pteropod", "parapodium", "paddle"], {**_SIZE, "stroke": (-54., 54., 13.), "twist": (-1., 1., .34)},
         _sized(pedal_swimming_wings), orient="native", host="body"),
    Part("dendritic_oral_collecting_tentacle", "feeding", "A sea cucumber oral collecting tentacle with branching distal fronds.",
         ["sea cucumber", "cucumaria", "oral", "dendritic", "collector"], {**_SIZE, "spread": (.27, 1., 1.)},
         _sized(dendritic_oral_collecting_tentacle), orient="native", host="body"),
    Part("crinoid_pinnulate_arm", "feeding", "A crinoid arm segment with alternating pinnules and a shallow open food groove.",
         ["crinoid", "feather star", "pinnule", "ambulacral groove"], {**_SIZE, "curl": (0., 1., .36)},
         _sized(crinoid_pinnulate_arm), orient="native", host="body"),
    Part("ophiuroid_jointed_arm", "locomotion", "A brittle star arm with repeating plates and lateral spine combs.",
         ["brittle star", "ophiuroid", "spined arm", "skeletal segments"], {**_SIZE, "bend": (-98., 98., 29.)},
         _sized(ophiuroid_jointed_arm), orient="native", host="body"),
    Part("surface_float_sail", "locomotion", "A man o' war float with an elongated buoyant envelope and integrated crest.",
         ["siphonophore", "physalia", "float", "sail", "pneumatophore"], {**_SIZE, "rise": (.50, 1.24, 1.), "lean": (-1., 1., .35)},
         _sized(surface_float_sail), orient="native", host="body", symmetry="center"),
]

TRAITS = {
    "pedal_swimming_wings": {"shape": "soft distal paddle with a short fleshy root", "function": "swim", "construction": "deformable"},
    "dendritic_oral_collecting_tentacle": {"shape": "soft stalk with a dendritic bouquet of collecting fronds", "construction": "deformable"},
    "crinoid_pinnulate_arm": {"shape": "segmented open-groove feeding arm with alternate pinnules", "construction": "deformable"},
    "ophiuroid_jointed_arm": {"shape": "lateral spine combs on short skeletal sections", "function": "support",
                              "regions": {"joint_tissue": "deformable", "plates": "rigid", "spines": "rigid"}},
    "surface_float_sail": {"shape": "elongated buoyant envelope with a longitudinal dorsal sail", "construction": "deformable"},
}
