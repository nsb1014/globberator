"""Local swimming and bottom-contact structures in fish anatomical frames."""

from math import cos, pi, radians, sin, tan, tau

from mathutils import Matrix
from scipy.interpolate import PchipInterpolator

from ..kit import RIGHT, UP, V, lerp, smoothstep
from . import Part
from .research_locomotion import _closed_rings


def traveling_wave_anal_ribbon(g, p):
    """Ribbon section with amplitude increasing from the fixed insertion line."""
    size, phase, amplitude = p["size"], p["phase"], p["amplitude"]
    g.setup(finish="direct")
    rings = []
    for index in range(161):
        t = index / 160
        z = lerp(.083, -.085, t)
        root = .0012 * cos(pi * t)
        height = .0025 + .025 * sin(pi * t**.85)**.68 * (1. - .29 * t)
        ray = (.5 + .5 * cos(tau * 32 * t))**3
        angle = radians(54) * amplitude * sin(tau * (2.05 * t - phase))
        ring = []
        for j in range(24):
            a = tau * j / 24
            fraction = .5 + .5 * cos(a)
            thickness = .00027 + .00075 * (1 - fraction) + .00043 * ray * fraction
            reach = height * fraction
            turn = angle * fraction**.6
            x = sin(a) * thickness + reach * sin(turn)
            y = root - reach * cos(turn)
            ring.append(V(x, y, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)


_SWORD_CHORDS = (
    # V15 to the midline, then D1 to D15. V7–V10 bridge both sword margins.
    -.018, -.023, -.029, -.036, -.042, -.093, -.134, -.141, -.117, -.071,
    -.065, -.069, -.072, -.074, -.075, -.075, -.074, -.073, -.071, -.068,
    -.064, -.059, -.054, -.047, -.041, -.035, -.030, -.025, -.020, -.016, -.013,
)
_SWORD_EDGE = PchipInterpolator(range(len(_SWORD_CHORDS)), _SWORD_CHORDS)
_SWORD_AZIMUTH = PchipInterpolator((0., 5., 8., 15., 23., 30.),
                                   (-.74, -.36, -.25, 0., .43, .83))


def ray_fan_with_ventral_sword(g, p):
    """One sheet over a caudal ray fan, with four lower rays extending distally."""
    size, spread = p["size"], p["spread"]
    g.setup(finish="direct")
    rings = []
    for index in range(181):
        station = index / 6
        z_edge = _SWORD_EDGE(station)
        root_y = .014 * (station / 15 - 1)
        slope = tan(_SWORD_AZIMUTH(station) * spread)
        ridge = (.5 + .5 * cos(tau * station))**4
        ring = []
        for j in range(28):
            angle = tau * j / 28
            reach = .5 + .5 * cos(angle)
            z = lerp(.003, z_edge, reach)
            y = root_y + (.003 - z) * slope
            thickness = .00040 + .00186 * (1 - reach)**2 + .00102 * ridge * sin(pi * reach)**.65
            ring.append(V(sin(angle) * thickness, y, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)


_COELACANTH_BONES = [{"name": "distal_fan", "pivot": (.095, -.018, -.021),
                     "axis": (0, 0, 1), "angle": 40}]
_COELACANTH_RAY_ROOT = PchipInterpolator((0., .18, .50, .76, 1.), (
    (.055, -.009, .009), (.098, -.014, -.003), (.126, -.024, -.033),
    (.105, -.024, -.052), (.066, -.018, -.051)))
_COELACANTH_RAY_EDGE = PchipInterpolator((0., .18, .50, .76, 1.), (
    (.066, -.008, .014), (.148, -.014, .012), (.190, -.026, -.028),
    (.159, -.036, -.081), (.077, -.026, -.083)))


def lobed_fin_with_distal_ray_fan(g, p):
    """A left muscular pectoral lobe with an asymmetric distal ray fringe."""
    size, fold = p["size"], p["fold"]
    pivot = V(_COELACANTH_BONES[0]["pivot"]) * size
    g.pivots["distal_fan"] = pivot
    g.setup(finish="direct")
    centers = [
        (-.008, .000, .000), (.017, -.004, -.006), (.044, -.010, -.014),
        (.075, -.016, -.019), (.101, -.021, -.024), (.125, -.024, -.030),
        (.138, -.024, -.035),
    ]
    g.loft([V(point) * size for point in centers],
           [(width * size, depth * size) for width, depth in (
               (.021, .013), (.025, .014), (.027, .012), (.031, .009),
               (.028, .006), (.020, .0035), (.006, .0016))],
           sides=30, up=UP, density=8)

    g.use("distal_fan")
    g.setup(finish="direct")
    rings = []
    for i in range(145):
        t = i / 144
        start = V(_COELACANTH_RAY_ROOT(t))
        edge = V(_COELACANTH_RAY_EDGE(t))
        bend = Matrix.Rotation(radians(-44 * fold * smoothstep(.048, .141, start.x)), 3, "Z")
        ray = (.5 + .5 * cos(tau * 29 * t))**3
        ring = []
        for j in range(24):
            a = tau * j / 24
            reach = .5 + .5 * cos(a)
            point = start + (bend @ (edge - start)) * reach
            point.y += sin(a) * (.00055 + .0012 * (1 - reach) + .0008 * ray * sin(pi * reach))
            ring.append(point * size)
        rings.append(ring)
    _closed_rings(g, rings)


_WALKING_RAY_BONES = [
    {"name": name, "pivot": (0, 0, 0), "axis": (1, 0, 0), "angle": angle}
    for name, angle in (("rostral_ray", 24), ("middle_ray", -20), ("caudal_ray", 23))
]


def detached_pectoral_walking_rays(g, p):
    """Three free pectoral rays below the compact wing-base proxy."""
    size, stride = p["size"], p["stride"]
    g.setup(finish="direct")
    g.oval(V(0., -.001, -.008) * size, V(.012, .013, .027) * size, segs=20, rings=14)
    g.slab([V(point) * size for point in (
        (-.008, .003, .018), (.015, .012, .024), (.037, .039, .014),
        (.056, .043, -.010), (.059, .031, -.036), (.053, .016, -.055),
        (.035, .008, -.060), (.008, .002, -.040), (-.008, .001, -.014),
    )], V(-.20, 1, .05), .0045 * size, bulge=.15)

    targets = (
        ((.008, -.007, .006), (.046, -.057, .016), (.088, -.092, .024)),
        ((.009, -.008, -.005), (.059, -.051, -.012), (.108, -.092, -.019)),
        ((.007, -.008, -.017), (.057, -.046, -.048), (.098, -.092, -.061)),
    )
    for index, (bone, target) in enumerate(zip(_WALKING_RAY_BONES, targets)):
        name = bone["name"]
        g.use(name)
        g.setup(finish="direct")
        root, middle, end = map(V, target)
        g.pivots[name] = root * size
        pace = stride * (1 if index != 1 else -1)
        end += V(0, .020 * max(0., pace), .018 * pace)
        middle += V(0, .009 * max(0., pace), .010 * pace)
        neck = root.lerp(middle, .22)
        blade = middle.lerp(end, .71)
        g.loft([point * size for point in (
            root, neck, middle, blade, blade.lerp(end, .67), end,
        )], [(width * size, depth * size) for width, depth in (
            (.0042, .0044), (.0038, .0033), (.0024, .0022),
            (.0033, .00155), (.0030, .00130), (.00060, .00060),
        )], up=UP, sides=18, density=6)


_SIZE = {"size": (.60, 1.60, 1.)}
PARTS = [
    Part("traveling_wave_anal_ribbon", "locomotion",
         "Ventral ray ribbon with a fixed insertion and phase-driven lateral undulation.",
         ["knifefish", "anal", "ribbon", "traveling wave", "ray"],
         {**_SIZE, "amplitude": (0., 1., .70), "phase": (0., 1., .15)}, traveling_wave_anal_ribbon,
         orient="native", symmetry="center", hint={"u": .45, "theta": -90.}),
    Part("ray_fan_with_ventral_sword", "aesthetics",
         "Rounded caudal ray fan with four continuous elongating ventral rays.",
         ["swordtail", "caudal", "ray fan", "sword"], {**_SIZE, "spread": (.50, 1.12, 1.)},
         ray_fan_with_ventral_sword, orient="native", symmetry="center", hint={"u": .02, "theta": 0.}),
    Part("lobed_fin_with_distal_ray_fan", "locomotion",
         "Muscular lateral fin lobe continuing into a jointed asymmetrical distal ray fringe.",
         ["coelacanth", "lobe", "pectoral", "fin rays"], {**_SIZE, "fold": (0., 1., .10)},
         lobed_fin_with_distal_ray_fan, orient="native", symmetry="pair", mirror=True,
         hint={"u": .64, "theta": -12.}, bones=_COELACANTH_BONES),
    Part("detached_pectoral_walking_rays", "locomotion",
         "Three free walking rays with spatula-shaped tips and a local fin-web proxy.",
         ["sea robin", "pectoral", "walking", "ray", "digging"], {**_SIZE, "stride": (-1., 1., 0.)},
         detached_pectoral_walking_rays, orient="native", symmetry="pair", mirror=True,
         hint={"u": .66, "theta": -32.}, bones=_WALKING_RAY_BONES),
]
