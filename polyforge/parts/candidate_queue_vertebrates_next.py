"""Additional isolated vertebrate morphology drafts in the PolyForge native frame."""

import math

from ..kit import UP, V, lerp, rot
from . import Part
from .research_locomotion import _closed_rings, _feather


def _lobed_digit(g, base, yaw, roll, length, width, size, deploy):
    frame = rot((0, 1, 0), yaw) @ rot((0, 0, 1), roll)

    def placed(point):
        x, y, z = point
        return (base + frame @ V(x * width, y * width, z * length)) * size

    g.slot("skin")
    centers = ((0., .001, -.015), (0., .000, .006), (.002, -.001, .034),
               (.003, -.003, .065), (.002, -.006, .091), (.000, -.007, .108))
    g.loft([placed(c) for c in centers],
           [(w * width * size, h * width * size) for w, h in ((.005, .005), (.006, .006),
             (.0055, .0047), (.0045, .0040), (.0034, .0032), (.0021, .0024))],
           sides=14, density=3, up=frame @ UP)
    for side in (-1, 1):
        for start, middle, end, span in ((.005, .021, .035, .016),
                                          (.035, .050, .066, .015),
                                          (.066, .080, .092, .012),
                                          (.092, .100, .108, .008)):
            flap = V(.003 + side * .0020, -.002 - middle * .040, middle)
            across = V(side * span * lerp(.47, 1., deploy),
                       -span * .63 * (1. - deploy), -.002)
            outline = (
                flap + V(0., 0., start - middle),
                flap + across * .73 + V(0., 0., (start - middle) * .61),
                flap + across,
                flap + across * .69 + V(0., 0., (end - middle) * .57),
                flap + V(0., 0., end - middle),
                flap - V(side * .004, 0., 0.),
            )
            g.slab([placed(v) for v in outline], frame @ UP, .0042 * width * size)
    g.slot("keratin")
    g.loft([placed((0., y, z)) for y, z in ((-.007, .105), (-.006, .112), (-.009, .120))],
           [r * width * size for r in (.0027, .0022, .00055)],
           sides=12, density=3, up=frame @ UP)


def individually_lobate_swim_toes(g, p):
    """One common-coot foot with three lobate anterior toes and a separate hallux."""
    size, deploy = p["size"], p["deploy"]
    g.setup(voxel=.00060 * size, smooth=.28, detail=4.8, slot_finish={"keratin": "subsurf_low"})
    g.slot("skin")
    g.oval(V(0., .004, -.007) * size, V(.022, .014, .021) * size)
    g.loft([V(0., y, z) * size for y, z in ((.001, -.012), (.018, -.015), (.031, -.019))],
           [r * size for r in (.011, .013, .012)], sides=16, density=3, up=V(0, 0, 1))
    for x, yaw, roll, length, width in ((-.014, -.73, -.59, .81, .83),
                                          (0., .02, .35, 1., 1.),
                                          (.014, .75, .72, .87, .88)):
        origin = V(x, -.001, .009)
        _lobed_digit(g, origin, yaw * lerp(.80, 1., deploy), roll * (1. - deploy),
                     length, width, size, deploy)
    g.slot("skin")
    g.loft([V(*v) * size for v in ((-.009, .000, -.014), (-.018, -.002, -.028),
                                   (-.023, -.006, -.040))],
           [r * size for r in (.0044, .0040, .0023)], sides=13, density=3)
    g.slot("keratin")
    g.loft([V(*v) * size for v in ((-.022, -.005, -.037), (-.024, -.006, -.043),
                                   (-.024, -.009, -.048))],
           [r * size for r in (.0023, .0017, .00044)], sides=12, density=3)


def totipalmate_hallux_swim_web(g, p):
    """Cormorant foot with membrane crossing all three adjacent digit pairs."""
    size, splay = p["size"], p["splay"]
    g.setup(voxel=.00073 * size, smooth=.27, detail=4.6,
            slot_finish={"keratin": "subsurf_low"})
    g.slot("skin")
    ankle = V(0, .006, -.011)
    g.oval(ankle * size, V(.021, .019, .027) * size)
    g.loft([ankle * size, V(0, .020, -.013) * size, V(.001, .035, -.018) * size],
           [r * size for r in (.014, .015, .013)], sides=16, density=3, up=V(0, 0, 1))
    digits = []
    for x, z, y in ((-.092, .023, -.016), (-.061, .105, -.020),
                    (.010, .150, -.022), (.089, .107, -.019)):
        root = V(-.008 if x < -.08 else x * .14, -.002, -.003 if x < -.08 else .005)
        end = V(x * lerp(.72, 1., splay), y, z)
        mid = root.lerp(end, .53) + V(0, -.002, .001)
        g.loft([v * size for v in (root, mid, end)],
               [r * size for r in (.0082, .0071, .0044)], sides=14, density=3)
        digits.append((root, end))
    for (left_base, left_end), (right_base, right_end) in zip(digits, digits[1:]):
        left_edge = left_base.lerp(left_end, .90)
        right_edge = right_base.lerp(right_end, .90)
        middle_base = left_base.lerp(right_base, .50)
        middle_edge = left_edge.lerp(right_edge, .50)
        scallop = (middle_base - middle_edge) * .16
        outline = (left_base, left_edge, left_edge.lerp(right_edge, .25) + scallop * .71,
                   middle_edge + scallop, left_edge.lerp(right_edge, .75) + scallop * .71,
                   right_edge, right_base, middle_base + V(0, .003, -.018))
        g.slab([v * size for v in outline], UP, .0072 * size, bulge=.37)
    g.slot("keratin")
    for root, end in digits:
        direction = (end - root).normalized()
        g.loft([v * size for v in (end - direction * .005, end + direction * .003,
                                    end + direction * .009 + V(0, -.003, 0))],
               [r * size for r in (.0048, .0038, .0007)], sides=12, density=3)


# Z stations pass the neck, wrist, midside edge, ankle and tail-tip anchors.
_COLUGO_MARGIN = (
    (.228, .061, .013), (.200, .110, .014), (.161, .189, .012),
    (.122, .264, .006), (.088, .324, .003), (.071, .339, .001),
    (.046, .328, .001), (.009, .295, .005), (-.031, .279, .006),
    (-.070, .273, .005), (-.114, .286, .002), (-.152, .307, -.002),
    (-.180, .318, -.005), (-.202, .308, -.008), (-.229, .250, -.014),
    (-.259, .183, -.017), (-.296, .118, -.020), (-.342, .063, -.019),
    (-.382, .032, -.016), (-.427, .011, -.010), (-.438, .002, -.008),
)


def multianchor_glide_membrane(g, p):
    """Continuous neck, flank and interfemoral panels for a five-anchor fixture."""
    rings = []
    size, spread = p["size"], p["spread"]
    for station, width, height in _COLUGO_MARGIN:
        lateral_reach = lerp(.52, 1., spread)
        ring = []
        for i in range(36):
            angle = math.tau * i / 36
            q = math.cos(angle)
            edge = abs(q)
            camber = .054 * math.sin(math.pi * edge) * min(1, width / .24)
            fold = .13 * (1. - spread) * edge ** 1.4 * min(1, width / .25)
            half_depth = min(.0040, width * .18)
            ring.append(V(q * width * lateral_reach,
                          height + camber - fold + half_depth * math.sin(angle),
                          station) * size)
        rings.append(ring)
    g.setup(finish="subsurf_low")
    g.slot("skin")
    _closed_rings(g, rings)


def _train_covert(g, root, tip, width, size, normal):
    """Train vane with an exposed rachis and an expanded terminal eyespot region."""
    direction = tip - root
    across = normal.cross(direction).normalized()
    dorsal = direction.cross(across).normalized()
    rings = []
    for t, vane in ((0., .06), (.22, .10), (.52, .27), (.71, .45),
                    (.81, .79), (.90, 1.), (.96, .73), (1., .12)):
        center = root + direction * t + dorsal * (.029 * math.sin(math.pi * t))
        rings.append([
            (center + across * (width * vane * math.cos(i * math.tau / 12))
             + dorsal * (.0023 * lerp(.7, 1., vane) * math.sin(i * math.tau / 12))) * size
            for i in range(12)
        ])
    _closed_rings(g, rings)


def covert_train_elevation(g, p):
    """Support the upper covert fan on its own underlying rectrix tier."""
    size = p["size"]
    elevation = rot((1, 0, 0), math.radians(p["elevation"]))
    g.setup(finish="subsurf_low")
    g.slot("rectrices")
    for i in range(-5, 6):
        q = i / 5.
        angle = q * .68
        root = V(.009 * i, -.025, .015)
        travel = .40 - .075 * abs(q)
        tip = root + travel * V(math.sin(angle), 0, -math.cos(angle))
        _feather(g, elevation @ root, elevation @ tip, .026, .0045, size, rounded=True)
    g.slot("coverts")
    tiers = ((9, .56, .045, .052, 58, .0), (13, .86, .046, .075, 65, .45),
             (17, 1.06, .047, .090, 70, -.18), (18, 1.26, .040, .104, 73, .4))
    for count, radius, width, depth, arc, phase in tiers:
        for i in range(-count, count + 1):
            q = (i + phase) / (count + abs(phase))
            angle = q * math.radians(arc)
            root = V(.0048 * i, depth, -.02 - .007 * abs(q))
            reach = radius * (1. - .17 * abs(q) ** 1.8)
            tip = root + reach * V(math.sin(angle), .011 + .025 * q * q, -math.cos(angle))
            _train_covert(g, elevation @ root, elevation @ tip,
                          width * (1. - .3 * abs(q)), size, elevation @ UP)


def deployable_water_carrying_feather(g, p):
    """An enlarged sandgrouse vane slice with inner coiled and outer fringe regions."""
    size, wet = p["size"], p["wet"]
    g.setup(finish="direct")
    g.slot("shaft")
    g.loft([V(0, 0, z) * size for z in (-.002, .005, .014, .018)],
           [r * size for r in (.0011, .0011, .0008, .00045)], sides=12, density=3)
    for side in (-1, 1):
        for i in range(5):
            start = V(0, .0002, .0023 + i * .0028)
            end = start + V(side * (.0127 - .00032 * i), .0011, .0034)
            mid = start.lerp(end, .56) + V(0, .0004, 0)
            g.slot("barbs")
            g.loft([v * size for v in (start, mid, end)],
                   [r * size for r in (.00042, .00033, .00019)], sides=9, density=2)
            g.slot("barbules")
            for j in range(6):
                fraction = (j + 1) / 7.
                base = start.lerp(end, fraction) + V(0, .00035, 0)
                rise = .0012 + .0018 * wet
                curl_radius = .00043
                if j < 3:
                    path = [base]
                    for k in range(1, 13):
                        t = k / 12
                        coil = math.tau * 1.35 * t
                        bend = V(side * curl_radius * math.sin(coil),
                                 curl_radius * (1. - math.cos(coil)), .0019 * t)
                        unfolded = V(side * .00038 * t, rise * .62 * t, .00041 * t)
                        path.append(base + bend.lerp(unfolded, wet))
                    terminal = V(side * .00020, .00014, .0016).lerp(
                        V(side * .00025, rise * .59, .00058), wet)
                    path.append(path[-1] + terminal)
                else:
                    # Flattened outer fringe flexes toward the cage in the wet pose.
                    path = [base, base + V(side * .0004, wet * .0005, .0012),
                            base + V(side * lerp(.0007, .0001, wet), wet * .0012, .0027),
                            base + V(side * lerp(.0008, -.0011, wet), wet * .0019, .0032)]
                radii = [lerp(.00020, .00011, k / (len(path) - 1)) * size for k in range(len(path))]
                g.loft([point * size for point in path], radii, sides=8, density=1)


PARTS = [
    Part("individually_lobate_swim_toes", "locomotion", "Draft foot with independently lobate digits and narrow joint breaks.",
         ["coot", "toe", "swim", "lobate paddle"], {"size": (.45, 2., 1.), "deploy": (0., 1., .87)},
         individually_lobate_swim_toes, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("totipalmate_hallux_swim_web", "locomotion", "Draft four-toe foot with webbing around the medial first digit.",
         ["cormorant", "totipalmate", "webbed", "swim"], {"size": (.45, 2., 1.), "splay": (.15, 1., .94)},
         totipalmate_hallux_swim_web, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("multianchor_glide_membrane", "locomotion", "Draft continuous neck, flank and tail gliding panels.",
         ["colugo", "glide", "patagium", "membrane"], {"size": (.45, 2., 1.), "spread": (.45, 1., 1.)},
         multianchor_glide_membrane, orient="native", host="body", symmetry="center"),
    Part("covert_train_elevation", "aesthetics", "Draft upper covert train with a separate rectrix support tier.",
         ["peafowl", "train", "display", "coverts", "tail"], {"size": (.45, 2., 1.), "elevation": (0., 83., 76.)},
         covert_train_elevation, orient="native", host="body", symmetry="center", hint={"u": .08, "theta": 90.}),
    Part("deployable_water_carrying_feather", "aesthetics", "Draft enlarged water-holding vane slice, with dry and wet geometry.",
         ["sandgrouse", "barbule", "feather", "water carrying"], {"size": (.45, 2., 1.), "wet": (0., 1., .72)},
         deployable_water_carrying_feather, orient="native", host="body", symmetry="center"),
]
