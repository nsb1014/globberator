"""External arthropod drafts with +Y dorsal, +Z anterior and local pose shapers."""

import math

from ..kit import RIGHT, UP, V, rot
from . import Part
from .candidate_arthropod import _loft
from .candidate_queue_arthropods import SIZE, UNIT
from .research_locomotion import _closed_rings


def radially_folding_hindwing(g, p):
    """Earwig fan with a central rib hub and transverse ring fold."""
    g.setup(finish="direct")
    size, fold = p["size"], p["fold"]
    hub = V(.046, .002, -.120)
    _loft(g, size, ((0, 0, .018), (.011, .001, -.031), (.023, .002, -.087), hub),
          ((.017, .010), (.041, .0075), (.062, .0058), (.055, .0048)),
          up=UP, sides=20)
    ribs = 17
    layers = 9

    def fan_point(t, u):
        angle = math.radians(-91 + 179 * t)
        angle *= 1 - .95 * fold
        ray = V(math.sin(angle), 0, -math.cos(angle))
        rib = t * (ribs - 1)
        radial_corrugation = math.cos(rib * math.pi)
        length = .223 + .097 * math.sin(math.pi * t)**.82 + .027 * t
        length *= 1 - .024 * (1 - math.cos(rib * math.tau))
        crease = .51 + .075 * math.sin(math.pi * t) + .035 * radial_corrugation
        reach = (.013 + min(u, crease) * length) * (1 - .23 * fold)
        turned = max(0., u - crease) * length
        flip = math.radians(160 * fold) * (.87 + .13 * radial_corrugation)
        y = .014 * math.sin(math.pi * u) + .009 * u**2
        y += .016 * fold * radial_corrugation * math.sin(math.pi * u * .88)
        z_shift = (t - .5) * .048 * fold
        return hub + ray * (reach + turned * math.cos(flip)) + V(0, y + turned * math.sin(flip), z_shift)

    rings = []
    for i in range(81):
        t = i / 80
        points = [fan_point(t, j / (layers - 1)) for j in range(layers)]
        rings.append([(point + UP * .00125) * size for point in points]
                     + [(point - UP * .00125) * size for point in reversed(points)])
    _closed_rings(g, rings)
    for i in range(ribs):
        t = i / (ribs - 1)
        edge = [fan_point(t, u) + UP * .00065 for u in (.08, .23, .39, .57, .74, .89, .99)]
        _loft(g, size, edge, (.0035, .0031, .0027, .0030, .0024, .0016, .00045),
              up=RIGHT, sides=10, density=3)
    ring_line = []
    for index in range(25):
        t = index / 24
        around = .51 + .075 * math.sin(math.pi * t) + .035 * math.cos(t * (ribs - 1) * math.pi)
        ring_line.append(fan_point(t, around) + UP * .0011)
    _loft(g, size, ring_line, [.0020] * len(ring_line), up=UP, sides=10, density=2)


def tibial_basket_pollen_press(g, p):
    """Worker honeybee tibial basin, rim setae and opposing basitarsal press."""
    g.setup(finish="direct")
    size = p["size"]
    rim = (
        (.015, .013, .011), (-.008, .018, .010), (-.045, .028, .014),
        (-.099, .041, .017), (-.157, .053, .020), (-.205, .061, .023),
        (-.231, .051, .020), (-.245, .028, .014), (-.252, .011, .009),
    )
    rings = []
    for z, wide, deep in rim:
        cross = []
        for index in range(32):
            a = index * math.tau / 32
            lateral, side = math.cos(a), math.sin(a)
            basin = .64 * side**5 * (min(wide, .047) / .047)**2 if side > 0 else 0.
            chamfer = -.009 * (z / .252)**2 * lateral
            cross.append(V(lateral * wide, deep * (side - basin), z + chamfer) * size)
        rings.append(cross)
    _closed_rings(g, rings)
    for side in (-1, 1):
        for j in range(15):
            t = j / 14
            x = side * (.021 + .037 * t)
            z = -.041 - .172 * t
            height = .014 + .012 * t
            _loft(g, size, ((x * .90, .005, z), (x + side * .005, height * .62, z - .009),
                            (x + side * .012, height, z - .019),
                            (x + side * .010, height * 1.09, z - .027)),
                  (.0022, .0017, .0011, .00033), up=RIGHT, sides=8, density=3)

    pivot = V(0, -.002, -.246)
    turn = rot(RIGHT, math.radians(14 + 68 * p["press"]))

    def basal(v):
        return pivot + turn @ V(v)

    _loft(g, size, [basal(v) for v in (
        (0, 0, .010), (0, .001, -.007), (-.002, .001, -.027),
        (-.004, .002, -.058), (-.004, .002, -.093), (.002, .002, -.116),
    )], ((.016, .014), (.036, .015), (.042, .017), (.039, .014),
         (.027, .010), (.015, .007)), up=RIGHT)
    _loft(g, size, [basal(v) for v in (
        (-.024, .003, -.025), (-.031, .013, -.012), (-.030, .019, .009),
        (-.025, .017, .021), (-.021, .013, .023),
    )], ((.017, .009), (.015, .008), (.013, .006), (.007, .005), (.003, .002)),
          up=RIGHT, sides=18)


def latched_ventral_springfork(g, p):
    """Springtail manubrium, paired dens and distal mucrones with coarse latch."""
    g.setup(finish="direct")
    size = p["size"]
    kick = rot(RIGHT, math.radians(7 + 139 * p["release"]))

    def moving(v):
        return kick @ V(v)

    _loft(g, size, [moving(v) for v in (
        (0, .013, -.019), (0, -.007, .011), (0, -.020, .047),
        (0, -.027, .084), (0, -.025, .107),
    )], ((.029, .016), (.038, .019), (.041, .019), (.044, .015), (.035, .013)),
          up=RIGHT)
    for side in (-1, 1):
        _loft(g, size, [moving((side * x, y, z)) for x, y, z in (
            (.027, -.024, .089), (.034, -.025, .111), (.042, -.027, .142),
            (.050, -.027, .190), (.056, -.024, .229), (.058, -.021, .252),
        )], ((.024, .016), (.025, .014), (.023, .013), (.017, .010),
             (.010, .007), (.007, .005)), up=RIGHT)
        _loft(g, size, [moving((side * x, y, z)) for x, y, z in (
            (.057, -.021, .244), (.061, -.017, .263), (.064, -.004, .282),
            (.064, .006, .298), (.063, .009, .300),
        )], ((.009, .007), (.009, .006), (.007, .004), (.0024, .003), (.0007, .0007)),
              up=RIGHT, sides=16)
        # Low medial locking shoulders on the proximal dens.
        _loft(g, size, [moving((side * x, y, z)) for x, y, z in (
            (.028, -.025, .106), (.020, -.016, .113), (.017, -.010, .124),
        )], ((.013, .009), (.011, .009), (.006, .004)), up=RIGHT, sides=14)
    # The catch is part of the host-side demonstrator and remains stationary.
    _loft(g, size, ((0, .018, .112), (0, .006, .113), (0, -.012, .119),
                    (0, -.022, .125)), ((.022, .012), (.022, .013), (.018, .011), (.011, .007)),
          up=RIGHT)
    for side in (-1, 1):
        _loft(g, size, ((side * .013, -.011, .121), (side * .017, -.022, .125),
                        (side * .022, -.030, .131), (side * .024, -.034, .128)),
              (.008, .006, .004, .0015), up=RIGHT, sides=12)


def folding_rostral_sheath(g, p):
    """Four external stink-bug labial articles with a continuous face groove."""
    g.setup(finish="direct")
    size, bend = p["size"], p["bend"]
    start = V(0, .004, .013)
    for index, (length, width, depth, resting, feeding) in enumerate((
        (.099, .028, .021, -9., -42.), (.093, .022, .018, -9., -121.),
        (.126, .018, .014, 2., -76.), (.106, .013, .010, 1., -68.),
    )):
        basis = rot(RIGHT, math.radians(resting + (feeding - resting) * bend))
        rings = []
        for station, scale in ((-.027, .72), (.08, .95), (.26, 1.), (.52, .95),
                               (.78, .93), (.93, .74), (1.027, .66 if index < 3 else .48)):
            ring = []
            for a in range(28):
                phi = a * math.tau / 28
                lateral, face = math.cos(phi), math.sin(phi)
                depression = math.exp(-(lateral / .21)**2) * .47 * max(0., face)**2
                v = V(width * scale * lateral, depth * scale * (face - depression),
                      -length * station)
                ring.append((start + basis @ v) * size)
            rings.append(ring)
        _closed_rings(g, rings)
        start += basis @ V(0, 0, -length)


PARTS = [
    Part("radially_folding_hindwing", "locomotion", "An earwig hindwing fan folds across its radial ribs and a transverse crease.",
         ["earwig", "wing", "radial", "crease"], {"size": SIZE, "fold": (0., .93, 0.)},
         radially_folding_hindwing, orient="native", symmetry="pair"),
    Part("tibial_basket_pollen_press", "manipulation", "A worker bee pollen basket meets a hinged basitarsal press.",
         ["bee", "corbicula", "pollen basket", "basitarsus"], {"size": SIZE, "press": (0., 1., .28)},
         tibial_basket_pollen_press, orient="native", symmetry="pair"),
    Part("latched_ventral_springfork", "locomotion", "A paired abdominal springfork swings from a fixed underside catch.",
         ["springtail", "furcula", "retinaculum", "jump"], {"size": SIZE, "release": (0., 1., .0)},
         latched_ventral_springfork, orient="native", symmetry="center"),
    Part("folding_rostral_sheath", "feeding", "A groove follows four folding external labial articles.",
         ["stink bug", "labium", "rostrum", "sheath"], {"size": SIZE, "bend": UNIT},
         folding_rostral_sheath, orient="native", symmetry="center"),
]

TRAITS = {
    "radially_folding_hindwing": {"function": "fly"},
    "tibial_basket_pollen_press": {"function": "carry"},
    "latched_ventral_springfork": {"function": "jump"},
    "folding_rostral_sheath": {"function": "feed"},
}
