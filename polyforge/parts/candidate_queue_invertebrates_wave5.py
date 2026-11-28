"""Local branching and external attachment anatomy in +Y-up part coordinates."""

from math import cos, exp, pi, sin, tau

from ..kit import RIGHT, UP, V, lerp
from . import Part
from .candidate_invertebrate import _sized
from .research_locomotion import _closed_rings


def recursive_basket_arm_fork(g, p):
    vertices = []
    faces = []
    sides = 24
    half = sides // 2

    def indexed(points):
        start = len(vertices)
        vertices.extend(points)
        return tuple(range(start, len(vertices)))

    def bridge(before, after):
        for j in range(sides):
            k = (j + 1) % sides
            faces.append((before[j], before[k], after[k], after[j]))

    def section(center, yaw, radius):
        side = V(cos(yaw), 0, -sin(yaw))
        return indexed(center + radius * (side * sin(tau * j / sides) + UP * .83 * cos(tau * j / sides))
                       for j in range(sides))

    def axial(center, yaw, length, radius, depth, before):
        # The first two generations branch at a real shared seam. Radius
        # rolls over each arm station to show the unit boundaries along it.
        for station in range(1, 18):
            t = station / 17
            bearing = yaw + p["curl"] * t * t * (.92 if depth == 0 else .30)
            direction = V(sin(yaw + (bearing - yaw) * .5), .25 * p["curl"] * t, cos(yaw + (bearing - yaw) * .5))
            point = center + length * t * direction
            taper = lerp(1., .32 if depth == 0 else .87, t)
            width = radius * taper * (1 + .055 * cos(tau * 5 * t))
            after = section(point, bearing, width)
            bridge(before, after)
            before = after
        if depth == 0:
            faces.append(before)
            return
        middle = indexed(vertices[before[half]].lerp(vertices[before[0]], i / half) for i in range(1, half))
        lips = (before[:half + 1] + middle, before[:1] + tuple(reversed(middle)) + before[half:])
        for sign, rim in zip((1, -1), lips):
            daughter_yaw = bearing + sign * p["spread"] * lerp(.85, .59, depth / 2)
            axis = V(sin(daughter_yaw), 0, cos(daughter_yaw))
            sideways = V(cos(bearing), 0, -sin(bearing))
            daughter_root = point + sign * sideways * width * .52
            daughter_r = width * .58
            child = daughter_root + axis * (.94 * width)
            first = section(child, daughter_yaw, daughter_r)
            bridge(rim, first)
            axial(child, daughter_yaw, length * (.90 if sign > 0 else 1.03),
                  daughter_r, depth - 1, first)

    root = V(0, .001, -.005)
    first = section(root, 0., .0058)
    faces.append(tuple(reversed(first)))
    axial(root, 0., .041, .0058, 2, first)
    g.slot("arm_network")
    # The cross-sections were authored clockwise looking from a branch tip.
    g._add(vertices, [tuple(reversed(face)) for face in faces])


def byssal_tether_fan(g, p):
    g.slot("root_bundle")
    g.oval(V(0, .001, 0), (.0073, .0053, .0045), segs=20, rings=12)
    for index in range(19):
        fraction = index / 18
        angle = lerp(-1.27, 1.69, fraction)
        radial = V(sin(angle), 0, cos(angle))
        tangent = UP.cross(radial)
        length = (.041 + .022 * (.5 + .5 * sin(index * 2.16))) * p["spread"]
        root = radial * (.0025 + .0010 * sin(index * 1.75)) + UP * .0013
        tip = radial * length - UP * (.025 + .0038 * sin(index * 1.49))
        tip += tangent * (.006 * sin(2.02 * index))
        mid = root.lerp(tip, .61)
        mid -= UP * min(.0094, .81 * (mid.y - tip.y)) * p["slack"]
        mid += tangent * (.005 * sin(index * 2.11) * p["slack"])
        g.slot("threads")
        g.loft([root, root.lerp(mid, .42), mid, tip + UP * .00042],
               [.00085, .00065, .00052, .00061], sides=10, up=UP, density=3)
        g.slot("plaques")
        g.oval(tip, (.0036, .00052, .0028), segs=16, rings=8)


def stalked_dorsal_elytral_scale(g, p):
    g.slot("stalk")
    attachment = .0055 + p["vault"] * .00605
    g.loft([V(0, -.006, 0), V(.0005, 0, -.0006), V(.0013, .0048, -.0017),
            V(.0014, attachment, -.0018)],
           [(.0038, .0031), (.0031, .0028), (.0043, .0034), (.0034, .0026)],
           sides=18, up=RIGHT, density=3)
    g.slot("scale")
    rings = []
    for above, levels in ((False, range(1, 19)), (True, range(18, 0, -1))):
        for level in levels:
            radius = sin(pi * level / 36)
            ring = []
            for index in range(100):
                theta = tau * index / 100
                uneven = 1. + .078 * cos(theta) + .062 * sin(3 * theta + .2)
                notch = .91 + .09 * (1 - exp(-((cos(theta) - .20) / .18) ** 2))
                x = .010 + .027 * radius * uneven * sin(theta) * notch
                z = -.005 + .028 * radius * uneven * cos(theta) * (1 - .13 * sin(theta))
                y = .0063 - .002 * radius**2 + p["vault"] * .007 * (1 - radius**2)
                y += (.00076 if above else -.00064)
                if above:
                    relief = .00041 * max(0., cos(23 * theta + 3 * radius)) ** 5
                    y += relief * sin(39 * radius)**2 * radius * (1 - radius**3)
                ring.append(V(x, y, z))
            rings.append(ring)
    _closed_rings(g, rings)


def cubomedusan_tentacle_pedalium(g, p):
    g.slot("palm")
    g.loft([V(0, 0, -.003), V(.0011, 0, .003), V(.0027, -.0008, .009),
            V(.007, -.0017, .014), V(.010, -.0028, .016)],
           [(.0034, .0016), (.0048, .0017), (.0049, .00135),
            (.0034, .00110), (.0022, .00079)], sides=22, up=UP, density=4)
    g.slot("pedal_fingers")
    for i in range(7):
        s = i / 6
        root = V(.0025 + .006 * s, -.0008 - .0015 * s, .0057 + .0080 * s)
        cross = p["spread"] * (.0037 + .0080 * sin(pi * s) ** .82)
        side = 1 if i % 2 else -1
        middle = root + V(side * cross * .56, -.0006, .0035 + .0015 * s)
        tip = root + V(side * cross, -.0012, .006 + .0014 * (1 - s))
        g.loft([root, middle, tip, tip + V(.00025 * side, -.0002, .0015)],
               [(.00160, .0010), (.00137, .00078), (.00106, .00063), (.00068, .00054)],
               sides=14, up=UP, density=3)


def valve_foramen_pedicle(g, p):
    g.slot("incomplete_foramen")
    rings = []
    for i in range(61):
        angle = lerp(.60, tau - .60, i / 60)
        cut_ends = .58 + .42 * sin(pi * i / 60)**.35
        corrugation = .00024 * cos(21 * angle)
        normal = V(sin(angle), cos(angle), 0)
        center = .0075 * normal + V(0, 0, -.00060 * cos(angle))
        ring = []
        for j in range(20):
            r = tau * j / 20
            width = (.0030 + corrugation) * cut_ends
            ring.append(center + normal * width * cos(r) + V(0, 0, (.0014 + .00018 * cos(angle)) * sin(r)))
        rings.append(ring)
    _closed_rings(g, rings)
    g.slot("pedicle")
    b = p["bend"]
    g.loft([V(0, 0, -.006), V(0, 0, .002), V(.0036 * b, .0011, .008),
            V(.0084 * b, .0022, .013), V(.012 * b, .0032, .017), V(.014 * b, .0037, .0181)],
           [(.0032, .0032), (.0035, .0034), (.0030, .0029),
            (.0025, .00247), (.0031, .0028), (.0036, .0034)], sides=22, up=UP, density=3)


_SIZE = {"size": (.65, 1.50, 1.)}
PARTS = [
    Part("recursive_basket_arm_fork", "feeding", "One basket-star arm with shared skeletal bifurcations and four curling ends.",
         ["basket star", "ophiuroid", "arm fork", "bifurcation"], {**_SIZE, "spread": (.82, 1.43, 1.), "curl": (0., 1., .38)},
         _sized(recursive_basket_arm_fork), orient="native", host="body"),
    Part("byssal_tether_fan", "locomotion", "Separate soft byssal tethers leave one root and end in substrate plaques.",
         ["mussel", "byssus", "anchor", "threads", "plaques"], {**_SIZE, "spread": (.74, 1.30, 1.), "slack": (0., 1., .32)},
         _sized(byssal_tether_fan), orient="native", host="body"),
    Part("stalked_dorsal_elytral_scale", "aesthetics", "Wide flattened scale mounted eccentrically on a short dorsal stalk.",
         ["scale worm", "elytron", "elytrophore", "polychaete"], {**_SIZE, "vault": (.60, 1.22, 1.)},
         _sized(stalked_dorsal_elytral_scale), orient="native", host="body"),
    Part("cubomedusan_tentacle_pedalium", "feeding", "Box jellyfish corner appendage, with a flattened palm supporting several distal seats.",
         ["box jellyfish", "cubomedusa", "pedalium", "tentacle roots"], {**_SIZE, "spread": (.74, 1.33, 1.)},
         _sized(cubomedusan_tentacle_pedalium), orient="native", host="body"),
    Part("valve_foramen_pedicle", "locomotion", "Brachiopod pedicle passing through a notched valve seat.",
         ["brachiopod", "lamp shell", "pedicle", "foramen", "tether"], {**_SIZE, "bend": (-1., 1., .35)},
         _sized(valve_foramen_pedicle), orient="native", host="body", symmetry="center"),
]

TRAITS = {
    "recursive_basket_arm_fork": {"shape": "repeated Y-shaped arm bifurcations with independent free ends", "construction": "deformable"},
    "byssal_tether_fan": {"shape": "splayed anchoring threads with individual flat contact plaques", "function": "support", "construction": "deformable"},
    "stalked_dorsal_elytral_scale": {"shape": "eccentrically rooted overlapping scale cover", "function": "protect", "construction": "deformable"},
    "cubomedusan_tentacle_pedalium": {"shape": "flattened branching corner fitting for seven distal tentacle seats", "construction": "deformable"},
    "valve_foramen_pedicle": {"shape": "narrow flexible anchor through an incomplete rigid foramen", "function": "support",
                              "regions": {"incomplete_foramen": "rigid", "pedicle": "deformable"}},
}
