"""Invertebrate anchor, closure, aperture and sensory-margin anatomy."""

from math import cos, exp, pi, radians, sin, tau

from ..kit import RIGHT, UP, V, lerp, rot, smoothstep
from . import Part
from .candidate_invertebrate import _sized
from .research_locomotion import _closed_rings


def _closed_band(g, rings):
    """Join a closed sequence of circular sections without capping the bore."""
    count = len(rings)
    sides = len(rings[0])
    vertices = [vertex for ring in rings for vertex in ring]
    faces = [(i * sides + j, i * sides + (j + 1) % sides, (i + 1) % count * sides + (j + 1) % sides,
              (i + 1) % count * sides + j) for i in range(count) for j in range(sides)]
    volume = sum(vertices[a].dot(vertices[b].cross(vertices[c]) + vertices[c].cross(vertices[d]))
                 for a, b, c, d in faces)
    if volume < 0:
        faces = [tuple(reversed(face)) for face in faces]
    g._add(vertices, faces)


def expandable_burrowing_foot_wedge(g, p):
    extension, dilation = p["extension"], p["dilation"]
    sections = (
        (-.005, .0036, .0067, 0., 0.), (0., .0042, .0071, 0., 0.),
        (.012, .0039, .0074, .0006, 0.), (.029, .0039, .0066, .0013, .03),
        (.048, .0039, .0072, .0017, .18), (.062, .0040, .0080, .0027, .70),
        (.073, .0038, .0070, .0032, 1.), (.081, .0030, .0046, .0027, .74),
        (.085, .0013, .0016, .0021, .25), (.086, .0006, .0008, .0019, .09),
    )
    rings = []
    for z, width, height, rise, swell in sections:
        z = min(z, 0) + max(z, 0) * extension
        shape_x = width + .0064 * dilation * swell
        shape_y = height + .0102 * dilation * swell
        ring = []
        for index in range(28):
            angle = tau * index / 28
            y = rise + shape_y * sin(angle)
            x = shape_x * cos(angle) * (1 - .12 * sin(angle))
            ring.append(V(x, y, z + .0039 * swell * sin(angle)))
        rings.append(ring)
    g.slot("foot")
    _closed_rings(g, rings)


def foot_carried_shell_operculum(g, p):
    # The convex outer face points along +Y. A shallow off-axis spiral on
    # the otherwise flatter side represents growth of the opercular plate.
    tilt = rot(RIGHT, radians(p["withdrawal"] * -41))
    offset = V(0, -.0022 * p["withdrawal"], -.005 * p["withdrawal"])
    rings = []
    for outer, steps in ((False, range(1, 18)), (True, range(17, 0, -1))):
        for step in steps:
            radius = sin(pi * step / 34)
            ring = []
            for index in range(72):
                angle = tau * index / 72
                x = radius * .019 * sin(angle) * (1 + .12 * cos(angle))
                z = radius * .024 * cos(angle) - .0032 * radius * sin(angle)**2
                crown = .0078 * (1 - radius**2) ** .81
                spiral = .00038 * sin(13 * pi * radius - angle) * radius * (1 - radius)
                y = (.0011 + crown if outer else -.0011 - .0005 * (1 - radius) + spiral)
                ring.append(offset + tilt @ V(x, y, z))
            rings.append(ring)
    g.slot("calcified_plate")
    _closed_rings(g, rings)

    g.slot("soft_seat")
    g.loft([V(0, -.006, -.011), V(0, -.0036, -.004), offset + tilt @ V(0, -.0016, 0)],
           [(.0054, .0017), (.0092, .0018), (.0114, .0010)], sides=24,
           up=UP, density=3)


def segmented_grasping_cirrus(g, p):
    start = V(0, 0, -.002)
    advance = .050
    turn = radians(lerp(44, 258, p["grip"]))

    def position(t):
        theta = turn * t
        return start + V(.0028 * sin(pi * t), -advance * (1 - cos(theta)) / turn, advance * sin(theta) / turn)

    g.slot("joints")
    steps = [i / 24 for i in range(25)]
    g.loft([position(t) for t in steps], [lerp(.00115, .00052, t) for t in steps],
           sides=12, up=RIGHT, density=1)
    g.slot("ossicles")
    for i in range(20):
        t = (i + .50) / 21.5
        waist = lerp(.00185, .00090, t)
        g.loft([position(t - .020), position(t), position(t + .020)],
               [(waist * .82, waist * .83), (waist, waist), (waist * .83, waist * .78)],
               sides=12, up=RIGHT, density=2)

    g.slot("contact")
    root = position(.925)
    tangent = (position(.965) - root).normalized()
    inward = tangent.cross(RIGHT).normalized()
    g.loft([root, position(.97), position(1.012) - inward * .0019,
            position(1.016) - inward * .0041],
           [.00105, .00104, .00074, .00018], sides=12, up=inward, density=4)
    g.loft([position(.892), position(.908) - inward * .0015,
            position(.918) - inward * .00225],
           [.00064, .00052, .00014], sides=10, up=RIGHT, density=3)


def subumbrella_velarial_shelf(g, p):
    rings = []
    contraction, bias = p["contraction"], p["bias"]
    for section, y_offset in ((0, .006), (.12, .003), (.34, .0015), (.61, .0011), (.87, .00065),
                              (1., .00035), (1., -.0005), (.86, -.00062), (.55, -.001), (.20, -.0016),
                              (0, -.0027), (0, .0010)):
        ring = []
        for i in range(120):
            angle = tau * i / 120
            x, z = cos(angle), sin(angle)
            box = .036 / (abs(x)**6 + abs(z)**6) ** (1 / 6)
            sector = 1 + .060 * cos(4 * angle) + .15 * bias * contraction * cos(angle - pi / 4)
            inner = lerp(.026, .014, contraction) * sector
            rim_radius = lerp(box, inner, section)
            lateral = bias * contraction * .0074 * section
            rib = .0037 * max(0., cos(4 * angle)) ** 13 * sin(pi * section)
            y = y_offset - (.001 + .008 * contraction) * section**1.8 + rib
            ring.append(V(x * rim_radius + lateral, y, z * rim_radius + lateral * .67))
        rings.append(ring)
    g.slot("shelf")
    _closed_band(g, rings)


def folded_anterior_pseudotentacles(g, p):
    rings = []
    for row in range(77):
        transverse = lerp(-1., 1., row / 76)
        x = .026 * transverse
        span = .026 * (1 - .94 * abs(transverse)**4)
        peaks = exp(-((x + .0109) / .0034) ** 2) + exp(-((x - .0106) / .0032) ** 2)
        fold = .015 * p["rise"] * peaks
        ring = []
        for column in range(48):
            angle = tau * column / 48
            edge = max(0., cos(angle)) ** 6
            z = -.006 + span * cos(angle) + .11 * fold * edge
            y = .00175 * sin(angle) * (1 - .81 * abs(transverse)**6)
            y += fold * edge
            ring.append(V(x, y, z))
        rings.append(ring)
    g.slot("folded_sheet")
    _closed_rings(g, rings)


def barrel_osculum_funnel(g, p):
    # Annular top collar exposing the tapered cavity, cut off at a local
    # transverse seat below the lip. The complete sponge body is out of scope.
    rings = []
    sections = (
        (.122, -.087, 1.0), (.133, -.064, 1.0), (.139, -.046, 1.0), (.142, -.025, 1.0),
        (.141, -.010, 1.0), (.138, -.001, .94), (.132, .008, .80), (.125, .010, .63),
        (.118, .006, .34), (.111, -.005, .14), (.107, -.024, .10), (.101, -.043, .07),
        (.088, -.067, .04), (.077, -.086, .02), (.089, -.089, .19), (.109, -.089, .48),
    )
    for radius, height, relief in sections:
        ring = []
        for i in range(128):
            angle = tau * i / 128
            drift = .050 * cos(3 * angle + .7) + .038 * sin(2 * angle - .45)
            texture = .0032 * cos(20 * angle + 13 * height) + .0023 * sin(27 * angle - 44 * height)
            web = (1 - relief) * (p["bore"] - 1) * .085
            r = radius * (1 + drift) + relief * texture + web
            y = height + (.0036 * sin(7 * angle) + .0034 * cos(4 * angle + .45)) * smoothstep(-.088, -.009, height)
            ring.append(V(r * cos(angle), y, r * sin(angle) * .90))
        rings.append(ring)
    g.slot("osculum_wall")
    _closed_band(g, rings)


_SIZE = {"size": (.65, 1.50, 1.)}
PARTS = [
    Part("expandable_burrowing_foot_wedge", "locomotion", "Razor clam foot with a narrow root and a dilatable terminal anchor.",
         ["bivalve", "razor clam", "burrowing", "foot", "anchor"], {**_SIZE, "extension": (.52, 1.18, 1.), "dilation": (0., 1., .55)},
         _sized(expandable_burrowing_foot_wedge), orient="native", host="body", symmetry="center"),
    Part("foot_carried_shell_operculum", "aesthetics", "A convex gastropod closure plate seated on a flexible local foot pad.",
         ["gastropod", "turban snail", "operculum", "shell", "closure"], {**_SIZE, "withdrawal": (0., 1., .32)},
         _sized(foot_carried_shell_operculum), orient="native", host="body", symmetry="center"),
    Part("segmented_grasping_cirrus", "manipulation", "A crinoid cirrus with a short ossicle chain and a terminal contact hook.",
         ["feather star", "crinoid", "cirrus", "cirral", "hook", "grasp"], {**_SIZE, "grip": (0., 1., .58)},
         _sized(segmented_grasping_cirrus), orient="native", host="body"),
    Part("subumbrella_velarial_shelf", "locomotion", "Box jellyfish velarium with a four-cornered seat and deformable central aperture.",
         ["box jellyfish", "cubomedusa", "velarium", "bell", "jet"], {**_SIZE, "contraction": (0., 1., .46), "bias": (-1., 1., .3)},
         _sized(subumbrella_velarial_shelf), orient="native", host="body", symmetry="center"),
    Part("folded_anterior_pseudotentacles", "sensory", "Two sensory points raised from one continuous flatworm margin.",
         ["flatworm", "polyclad", "pseudotentacle", "fold", "sheet"], {**_SIZE, "rise": (.53, 1.24, 1.)},
         _sized(folded_anterior_pseudotentacles), orient="native", host="body", symmetry="center"),
    Part("barrel_osculum_funnel", "aesthetics", "A sponge's uneven terminal rim and open thick-walled osculum sector.",
         ["sponge", "poriferan", "barrel sponge", "osculum", "cavity"], {**_SIZE, "bore": (.84, 1.14, 1.)},
         _sized(barrel_osculum_funnel), orient="native", host="body", symmetry="center"),
]

TRAITS = {
    "expandable_burrowing_foot_wedge": {"shape": "narrow pedal wedge with a distally swollen sediment anchor", "construction": "deformable"},
    "foot_carried_shell_operculum": {"shape": "convex oval plate carried on a soft foot seat", "function": "protect",
                                    "regions": {"soft_seat": "deformable", "calcified_plate": "rigid"}},
    "segmented_grasping_cirrus": {"shape": "serial short segments with an opposed terminal hooking pair",
                                  "regions": {"joints": "deformable", "ossicles": "rigid", "contact": "rigid"}},
    "subumbrella_velarial_shelf": {"shape": "inward bell shelf with a steerable aperture", "function": "swim", "construction": "deformable"},
    "folded_anterior_pseudotentacles": {"shape": "two triangular raised folds on a continuous sheet margin", "construction": "deformable"},
    "barrel_osculum_funnel": {"shape": "wide irregular terminal rim around a tapered shallow cavity", "construction": "deformable"},
}
