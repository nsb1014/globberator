"""Local flippers and external stalks, authored in aquatic anatomical frames."""

from math import cos, pi, radians, sin, tau

from mathutils import Matrix
from scipy.interpolate import PchipInterpolator

from ..kit import V, lerp, smoothstep
from . import Part
from .research_locomotion import _closed_rings


_TURTLE_STATIONS = (
    (-.034, .000, .105, .038, .041, .034),
    (-.018, .000, .095, .054, .068, .045),
    (.012, -.008, .105, .058, .083, .041),
    (.062, -.024, .126, .048, .080, .031),
    (.108, -.036, .139, .044, .085, .023),
    (.156, -.042, .124, .043, .106, .016),
    (.218, -.047, .105, .035, .108, .011),
    (.282, -.052, .083, .028, .098, .008),
    (.342, -.057, .060, .020, .073, .006),
    (.391, -.062, .030, .009, .043, .004),
    (.424, -.067, .001, .004, .015, .003),
    (.436, -.070, -.010, .0012, .0037, .0012),
)
_TURTLE_PROFILE = PchipInterpolator([row[0] for row in _TURTLE_STATIONS],
                                    [row[1:] for row in _TURTLE_STATIONS])


def shell_seated_foreflipper(g, p):
    """A single cheloniid shoulder cuff, flex region and tapering hydrofoil."""
    size, flex, stroke = p["size"], p["flex"], p["stroke"]
    g.setup(finish="direct")
    sections = []
    for i in range(70):
        x = lerp(-.034, .436, i / 69)
        y, lead, forward, behind, depth = _TURTLE_PROFILE(x)
        elbow_turn = Matrix.Rotation(radians(56 * flex * smoothstep(.025, .252, x)), 3, "Y")
        stroke_turn = Matrix.Rotation(radians(69 * stroke * smoothstep(-.020, .085, x)), 3, "Z")
        center = V(x, y, lead - forward)
        elbow = V(.106, -.035, .102)
        ring = []
        for j in range(40):
            angle = tau * j / 40
            chord = cos(angle)
            thickness = depth * (1 + .21 * chord)
            z = chord * (forward if chord > 0 else behind)
            ridge = .00125 * max(0., cos(3 * tau * ((chord + 1) / 2 - .12)))**5
            ridge *= smoothstep(.125, .24, x) * (1 - smoothstep(.32, .432, x))
            point = center + V(0, sin(angle) * (thickness + ridge), z)
            point = elbow + elbow_turn @ (point - elbow)
            ring.append((stroke_turn @ point) * size)
        sections.append(ring)
    _closed_rings(g, sections)


_SEA_LION_REACH = PchipInterpolator((0., .12, .24, .38, .51, .66, .79, .90, 1.),
                                    (.149, .154, .129, .144, .130, .150, .139, .167, .174))


_HINDFLIPPER_BONES = [{"name": "web", "pivot": (0, 0, .015), "axis": (0, 1, 0), "angle": 148}]


def rotating_hindflipper_foot(g, p):
    """One otariid ankle and a five-rayed web with forward and trailing poses."""
    size, stance, splay = p["size"], p["stance"], p["splay"]
    g.setup(finish="direct")
    pivot = V(_HINDFLIPPER_BONES[0]["pivot"])
    g.pivots["web"] = pivot * size
    g.oval((pivot + V(0, .001, .004)) * size, V(.029, .019, .022) * size, segs=36, rings=22)
    g.use("web")
    g.setup(finish="direct")
    rotation = Matrix.Rotation(radians(148 * stance), 3, "Y")
    rings = []
    # The flexible web starts just inside the short, fixed tarsal cuff.
    for i in range(97):
        t = i / 96
        root_x = lerp(-.024, .022, t)
        angle = radians(25 + 17 * splay) * (2 * t - 1)
        length = _SEA_LION_REACH(t)
        toe = (.5 + .5 * cos(4 * tau * t))**4
        ring = []
        for j in range(36):
            a = tau * j / 36
            u = .5 + .5 * cos(a)
            x = root_x + length * u * sin(angle)
            z = .019 - length * u * cos(angle)
            y = -.005 * sin(pi * u)
            thickness = (.0019 + .019 * (1 - u)**2.8
                         + .0034 * toe * sin(pi * u)**.85)
            thickness *= .48 + .52 * sin(pi * t)**.48
            point = V(x, y + thickness * sin(a), z)
            point = pivot + rotation @ (point - pivot)
            point.y -= stance * .027 * sin(pi * u * .63)
            ring.append(point * size)
        rings.append(ring)
    _closed_rings(g, rings)


_SEADRAGON_STALKS = (
    ((-.003, .006, .048), (.020, .031, .052), (.030, .082, .075), .014, -.34),
    ((-.003, -.008, .035), (.018, -.028, .020), (.029, -.067, .003), .013, .38),
    ((-.004, .009, .006), (.015, .029, -.009), (.037, .059, -.048), .014, -.51),
    ((-.005, -.006, -.029), (.014, -.023, -.048), (.022, -.065, -.077), .012, .56),
    ((-.004, .006, -.054), (.013, .022, -.077), (.032, .049, -.117), .011, -.25),
)


def stalked_camouflage_blades(g, p):
    """Five separate stalks supporting irregular compressed dermal blades."""
    size, flow = p["size"], p["flow"]
    g.setup(finish="subsurf_low")
    for i, (root_data, neck_data, tip_data, blade_width, camber) in enumerate(_SEADRAGON_STALKS):
        root, neck, tip = V(root_data), V(neck_data), V(tip_data)
        neck.z -= .009 * flow
        tip.z -= .016 * flow
        tip.x += .005 * flow
        along = (tip - neck).normalized()
        side = along.cross(V(.71, .15, -.30)).normalized()
        normal = side.cross(along).normalized()
        middle = root.lerp(neck, .54) + V(.003, 0, .002 * cos(i))
        g.loft([point * size for point in (root, middle, neck, neck.lerp(tip, .41))],
               [r * size for r in (.0032, .0030, .0024, .0009)], sides=12, density=4, up=normal)
        outline = [(0., 0.), (.17, -.40), (.29, -.81), (.47, -.94),
                   (.57, -.73), (.69, -.93), (.78, -.53), (1., -.07),
                   (.86, .19), (.80, .54), (.57, .87), (.46, .76),
                   (.34, .52), (.22, .69), (.10, .23)]
        blade = []
        for t, across in outline:
            cup = camber * blade_width * sin(pi * t) * (1 - .5 * abs(across))
            point = neck.lerp(tip, t) + side * (blade_width * across) + normal * cup
            blade.append(point * size)
        g.leaf(blade, normal, .0020 * size, cup=.26)


def external_egg_suspension_stalks(g, p):
    """Staggered ventral stalk cups, optionally carrying separate ova."""
    size, eggs = p["size"], p["eggs"]
    g.setup(finish="direct")
    for row in range(3):
        for column in range(4):
            x = .013 * (column - 1.5) + .0030 * (row % 2)
            z = .015 * (1 - row)
            offset = .0020 * sin(2.2 * column + 1.6 * row)
            root = V(x, .0025 - .0007 * abs(column - 1.5), z)
            end = root + V(.0016 * (column - 1.5), -.010 + offset, .0009 * (row - 1))
            curve = root.lerp(end, .53) + V(0, 0, .001 * cos(row + column))
            rings = []
            ring_stations = (
                (root + V(0, .0008, 0), .0025),
                (root, .0038), (root.lerp(curve, .46), .0029), (curve, .0022),
                (curve.lerp(end, .65), .0023), (end - V(0, -.0014, 0), .0035),
                (end, .00425), (end + V(0, -.0006, 0), .0041),
                (end + V(0, -.0002, 0), .00355), (end + V(0, .0012, 0), .0024),
                (end + V(0, .0016, 0), .0007),
            )
            for center, radius in ring_stations:
                rings.append([(center + V(radius * cos(a), 0, radius * sin(a))) * size
                              for a in (tau * i / 28 for i in range(28))])
            _closed_rings(g, rings)
            if eggs:
                g.slot("egg")
                center = end + V(.00021 * sin(column), -.0041, .00023 * cos(row))
                g.oval(center * size, V(.0046, .0047, .0045) * size, segs=24, rings=16)
                g.slot("base")


_SIZE = {"size": (.6, 1.6, 1.)}
PARTS = [
    Part("shell_seated_foreflipper", "locomotion",
         "Cheloniid shoulder cuff and tapered digit-supported blade with elbow flex.",
         ["green turtle", "sea turtle", "foreflipper", "shell notch", "swim"],
         {**_SIZE, "flex": (0., 1., .30), "stroke": (-.73, .75, 0.)},
         shell_seated_foreflipper, orient="native", symmetry="pair", mirror=True,
         hint={"u": .74, "theta": -12.}),
    Part("rotating_hindflipper_foot", "locomotion",
         "Otariid hindfoot with an ankle transition and spread web for paddling and stance.",
         ["sea lion", "hindflipper", "foot", "webbing", "ankle"],
         {**_SIZE, "stance": (0., 1., .15), "splay": (0., 1., .66)},
         rotating_hindflipper_foot, orient="native", symmetry="pair", mirror=True,
         hint={"u": .16, "theta": -42.}, bones=_HINDFLIPPER_BONES),
    Part("stalked_camouflage_blades", "aesthetics",
         "Individually rooted stalks carrying lobed seadragon dermal blades.",
         ["leafy seadragon", "dermal", "stalk", "leaf", "camouflage"],
         {**_SIZE, "flow": (-1., 1., .10)}, stalked_camouflage_blades,
         orient="native", symmetry="pair", mirror=True, hint={"u": .37, "theta": 0.}),
    Part("external_egg_suspension_stalks", "aesthetics",
         "Staggered ventral cotylephores with cupped ends and optional ova.",
         ["banjo catfish", "egg", "cotylephore", "brood", "stalk"],
         {**_SIZE, "eggs": (0, 1, 1)}, external_egg_suspension_stalks,
         orient="native", symmetry="center", hint={"u": .56, "theta": -90.}, discrete=("eggs",)),
]
