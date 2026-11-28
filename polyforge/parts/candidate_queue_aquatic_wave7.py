"""Local dorsal lock and caudal spine studies, with rounded clay edges."""

from math import cos, exp, pi, radians, sin, tau

from mathutils import Matrix
from scipy.interpolate import PchipInterpolator

from ..kit import UP, V, lerp, smoothstep
from . import Part
from .research_locomotion import _closed_rings


_TRIGGER_BONES = [
    {"name": "primary_spine", "pivot": (0, -.006, .027), "axis": (1, 0, 0), "angle": -75.},
    {"name": "locking_spine", "pivot": (0, -.005, .008), "axis": (1, 0, 0), "angle": -63.},
]


def interlocking_dorsal_spines(g, p):
    """Two unequal spines with neighboring roots, a lock recess and receiving trough."""
    size, raised, release = p["size"], p["raised"], p["release"]
    g.setup(finish="direct")
    rings = []
    for i in range(42):
        t = i / 41
        z = lerp(.045, -.087, t)
        width = .010 + .013 * sin(pi * t)**.65
        depth = .005 + .006 * sin(pi * t)**.72
        ring = []
        for j in range(42):
            a = tau * j / 42
            x, top = cos(a), max(0., sin(a))
            recessed = .010 * top * exp(-(x / .43)**4) * sin(pi * t)**.58
            ring.append(V(width * x, -depth + depth * sin(a) - recessed, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)
    for bone in _TRIGGER_BONES:
        seat = V(bone["pivot"]) - UP * .004
        g.oval(seat * size, V(.0084, .0059, .0082) * size, segs=22, rings=14)

    mount = V(_TRIGGER_BONES[0]["pivot"])
    g.pivots["primary_spine"] = mount * size
    g.use("primary_spine")
    g.setup(finish="direct")
    rotation = Matrix.Rotation(radians(-68 * (1 - raised)), 3, "X")
    primary = (
        (-.007, .0059, .0079, -.0007, 0.), (.004, .0071, .0098, -.0012, .34),
        (.013, .0067, .0099, -.0014, 1.), (.023, .0051, .0083, -.0029, .85),
        (.039, .0038, .0057, -.0062, .46), (.055, .0031, .0043, -.0094, .30),
        (.068, .0024, .0024, -.0136, .14), (.075, .0016, .0015, -.0178, .0),
    )
    profile = PchipInterpolator([row[0] for row in primary], [row[1:] for row in primary])
    rings = []
    for index in range(42):
        y = lerp(primary[0][0], primary[-1][0], index / 41)
        width, depth, shift, groove = profile(y)
        ring = []
        for i in range(42):
            a = tau * i / 42
            x, z = cos(a), sin(a)
            cut = depth * groove * .60 * max(0., -z) * exp(-(x / .39)**2)
            point = V(width * x, y, shift + depth * z + cut)
            ring.append((mount + rotation @ point) * size)
        rings.append(ring)
    _closed_rings(g, rings)

    mount = V(_TRIGGER_BONES[1]["pivot"])
    g.pivots["locking_spine"] = mount * size
    g.use("locking_spine")
    g.setup(finish="direct")
    rotation = Matrix.Rotation(radians(-92 * (1 - raised) - 25 * raised * release), 3, "X")
    g.loft([(mount + rotation @ V(x, y, z)) * size for x, y, z in (
        (0., -.004, -.0015), (0., .003, .0010), (0., .014, .0063),
        (0., .024, .0032), (0., .034, -.0032), (0., .042, -.0101),
        (0., .047, -.0132),
    )], [(a * size, b * size) for a, b in (
        (.0039, .0045), (.0043, .0047), (.0041, .0081), (.0034, .0045),
        (.0025, .0031), (.0017, .0021), (.0011, .0011),
    )], sides=20, density=6, up=V(0, 0, 1))


_TANG_BONES = [{"name": "caudal_spine", "pivot": (.005, 0., -.027),
                "axis": (0., 1., 0.), "angle": 51.}]


def folding_peduncular_scalpel(g, p):
    """One lateral body patch with a longitudinal pocket and a folding modified scale."""
    size, opened = p["size"], p["opened"]
    g.setup(finish="direct")
    rings = []
    for i in range(56):
        t = i / 55
        z = lerp(.056, -.051, t)
        width = .023 - .006 * t
        depth = .009 + .004 * sin(pi * t)
        ring = []
        for j in range(50):
            a = tau * j / 50
            y, outward = cos(a), sin(a)
            groove = .005 * exp(-(y / .26)**4) * max(0., outward)
            groove *= smoothstep(-.045, -.021, z) * (1 - smoothstep(.018, .044, z))
            x = -.003 + depth * outward - groove
            ring.append(V(x, width * y, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)

    hinge = V(_TANG_BONES[0]["pivot"])
    g.pivots["caudal_spine"] = hinge * size
    g.use("caudal_spine")
    g.setup(finish="direct")
    rotation = Matrix.Rotation(radians(51 * opened), 3, "Y")
    stations = (
        (-.007, .0009, .0031, .0000), (.000, .00155, .0063, .0000),
        (.010, .0017, .0058, .0007), (.022, .00145, .0043, .0017),
        (.034, .00125, .0027, .0014), (.044, .0011, .0015, .0013),
        (.048, .0008, .0010, .0010),
    )
    rings = []
    for z, thickness, width, lift in stations:
        ring = []
        for j in range(26):
            a = tau * j / 26
            x = lift + thickness * cos(a)
            y = width * sin(a) - .0012 * z / .048
            ring.append((hinge + rotation @ V(x, y, z)) * size)
        rings.append(ring)
    _closed_rings(g, rings)


_STING_ENVELOPE = PchipInterpolator((0., .10, .23, .38, .58, .73, .86, 1.), (
    (.0072, .0040, -.0031), (.0073, .0043, -.0017), (.0068, .0033, .0006),
    (.0069, .0027, .0031), (.0060, .0025, .0044), (.0047, .0022, .0047),
    (.0030, .0019, .0041), (.0012, .0010, .0034),
))


def barbed_caudal_sting(g, p):
    """A low tail-rooted spine with coarse recurved relief and a smooth buried root."""
    size = p["size"]
    g.setup(finish="direct")
    g.loft([V(0, y, z) * size for y, z in (
        (-.0044, .021), (-.0039, .009), (-.0046, -.003),
        (-.0049, -.014), (-.0053, -.026),
    )], [(width * size, height * size) for width, height in (
        (.005, .0031), (.010, .0044), (.0102, .0043), (.0086, .0035), (.0055, .0027),
    )], sides=28, density=6, up=UP)
    rings = []
    tooth_count = 12
    for i in range(117):
        t = i / 116
        width, depth, y = _STING_ENVELOPE(t)
        relief = .0015 * smoothstep(.17, .30, t) * (1 - smoothstep(.79, .98, t))
        phase = (tooth_count * t + .68) % 1.
        lobe = smoothstep(0., .22, phase) * (1 - smoothstep(.31, 1., phase))
        ring = []
        for j in range(30):
            a = tau * j / 30
            x, vertical = cos(a), sin(a)
            edge = relief * lobe * abs(x)**5
            center_ridge = .0009 * max(0., vertical) * (1 - abs(x))
            ring.append(V(x * (width + edge), y + vertical * depth + center_ridge,
                          lerp(.017, -.109, t)) * size)
        rings.append(ring)
    _closed_rings(g, rings)


_SIZE = {"size": (.6, 1.6, 1.)}
PARTS = [
    Part("interlocking_dorsal_spines", "aesthetics",
         "Paired triggerfish dorsal spines, with a recessed first spine and shared supporting trough.",
         ["triggerfish", "dorsal", "spines", "groove", "lock"],
         {**_SIZE, "raised": (0., 1., .95), "release": (0., 1., .0)}, interlocking_dorsal_spines,
         orient="native", symmetry="center", hint={"u": .71, "theta": 90.}, bones=_TRIGGER_BONES),
    Part("folding_peduncular_scalpel", "aesthetics",
         "Folding surgeonfish caudal scale with a recessed flank pocket.",
         ["blue tang", "peduncle", "scale", "groove", "fold"],
         {**_SIZE, "opened": (0., 1., .73)}, folding_peduncular_scalpel,
         orient="native", symmetry="pair", mirror=True,
         hint={"u": .15, "theta": 0.}, bones=_TANG_BONES),
    Part("barbed_caudal_sting", "aesthetics",
         "Dorsal stingray tail seat and flat spine with rounded recurved edge relief.",
         ["stingray", "tail", "caudal", "spine", "serration"], _SIZE, barbed_caudal_sting,
         orient="native", symmetry="center", hint={"u": .24, "theta": 90.}),
]
