"""External pet anatomy fixtures in the native +Y up, +Z forward frame."""

from math import copysign, cos, exp, pi, sin

from scipy.interpolate import PchipInterpolator

from ..kit import V, smoothstep
from . import Part
from .research_aesthetics import _closed_sections
from .research_locomotion import _FootForm
from .research_sensory import nose_pad


SIZE = (.65, 1.65, 1.)
FRONT = {"u": .85, "theta": -90.}


def square_stop_canine_muzzle(g, p):
    """Moderately stepped foreface, straight bridge and a closed lip seam."""
    size, reach, stop = p["size"], p["reach"], p["stop"]
    positions = (-.091, -.076, -.048, -.020, .008, .027, .047, .069,
                 .106, .151, .192, .217, .233, .244, .248)
    # Half width, dorsal height and ventral height from the forehead seat
    # to the squared-off tip. More width is preserved at the end than in a fox.
    profile = PchipInterpolator(positions, (
        (.022, .055, -.027), (.052, .092, -.059), (.083, .108, -.085),
        (.091, .105, -.094), (.091, .090, -.092), (.089, .068, -.085),
        (.084, .049, -.079), (.080, .041, -.073), (.075, .039, -.068),
        (.070, .037, -.063), (.067, .034, -.058), (.064, .030, -.055),
        (.057, .025, -.051), (.038, .013, -.041), (.014, -.001, -.027),
    ))
    g.setup(finish="direct", slot_finish={"rhinarium": "subsurf"})
    g.slot("skin")
    rings = []
    for z in [*(positions[0] + (.229 - positions[0]) * k / 46 for k in range(47)),
              .233, .237, .241, .244, .246, .248]:
        width, top, bottom = profile(z)
        top += (stop - 1) * .038 * (1 - smoothstep(.002, .072, z))
        collar = smoothstep(-.030, .027, z)
        center, height = (top + bottom) / 2, (top - bottom) / 2
        outline = []
        for j in range(68):
            a = pi / 2 - 2 * pi * j / 68
            x = width * copysign(abs(cos(a)) ** .71, cos(a))
            y = center + height * copysign(abs(sin(a)) ** .72, sin(a))
            lip_line = -.029 - .021 * exp(-((z - .011) / .067) ** 2)
            slit = exp(-((y - lip_line) / .007) ** 2)
            side = smoothstep(.34, .87, abs(x) / width)
            corner = 1 - smoothstep(.205, .243, z)
            x *= 1 - .16 * collar * slit * side * corner
            depth = z * (reach if z > 0 else 1)
            outline.append((x, y, depth))
        rings.append(outline)
    _closed_sections(g, rings, (0, .013, -.095), (0, -.013, .249 * reach), size)

    # Shape the separate, seated rhinarium with the catalog's rimmed nares.
    start = len(g.prims)
    nose_pad(g, {"size": .55 * size, "projection": .32})
    g.setup(finish="direct")
    for primitive in g.prims[start:]:
        primitive.slot = "rhinarium"
        for vertex in primitive.v:
            vertex.y = .70 * vertex.y + .014 * size
            vertex.z = .77 * vertex.z + .227 * reach * size


def pendulous_folded_pinna(g, p):
    """One +X ear rolls over its root into a draped cartilage sheet."""
    size, fall, inturn = p["size"], p["fall"], p["inturn"]
    # X, Y and Z of the midsurface, half width along Z, shell half thickness.
    stations = (
        (-.031, -.001, -.002, .014, .010), (-.018, .006, -.003, .028, .014),
        (.002, .014, -.003, .039, .014), (.024, .013, -.004, .044, .012),
        (.045, .001, -.007, .050, .009), (.054, -.028, -.009, .055, .007),
        (.054, -.064, -.010, .060, .006), (.051, -.104, -.010, .063, .005),
        (.047, -.147, -.008, .059, .004), (.044, -.183, -.003, .051, .0037),
        (.041, -.208, .001, .035, .0034), (.039, -.221, .003, .024, .0028),
        (.037, -.227, .004, .011, .0021), (.037, -.229, .004, .003, .0011),
    )
    centerline = PchipInterpolator(range(len(stations)), stations)
    limit = len(stations) - 1
    rings = []
    for step in range(50):
        t = limit * step / 49
        x, y, z, w, thickness = centerline(t)
        dx, dy, _, _, _ = centerline(min(limit, t + .04)) - centerline(max(0., t - .04))
        nx, ny = dy / (dx * dx + dy * dy) ** .5, -dx / (dx * dx + dy * dy) ** .5
        drape = smoothstep(3, 7, t) * min(1., (w / .052) ** 2)
        cup = sin(pi * t / limit)
        ring = []
        for j in range(36):
            a = -2 * pi * j / 36
            across = cos(a)
            roll = .018 * inturn * drape * max(0., across) ** 2
            bend = .013 * drape * across ** 2 + roll
            ring.append((x - bend + nx * thickness * sin(a),
                         y * (1 + (fall - 1) * smoothstep(3, limit, t)) + ny * thickness * sin(a),
                         z + w * across + .003 * cup * sin(a)))
        rings.append(ring)
    g.setup(finish="direct")
    _closed_sections(g, rings, (-.035, -.002, -.002),
                     (.037, -.230 * fall, .004), size)


def bilateral_mystacial_pads(g, p):
    """Paired mystacial lobe fields and their recessed vibrissal seats."""
    size, fullness, relief = p["size"], p["fullness"], p["relief"]
    seats = ((.035, -.001), (.051, .004), (.068, .010), (.084, .018),
             (.041, -.016), (.060, -.012), (.078, -.005), (.089, .004),
             (.036, -.030), (.054, -.029), (.071, -.022), (.084, -.013),
             (.045, -.041), (.063, -.036), (.079, -.027))

    def front(x, y, radius):
        lateral = abs(x)
        lobe = exp(-(((lateral - .044) / .043) ** 2 + ((y + .014 - .12 * lateral) / .038) ** 2))
        cleft = exp(-((x / .011) ** 2 + ((y + .022) / .041) ** 2))
        follicles = sum(exp(-(((lateral - sx) / .0039) ** 2 + ((y - sy) / .0034) ** 2))
                        for sx, sy in seats)
        return .004 + max(0, 1 - radius ** 3) ** .53 * (
            .012 + .035 * fullness * lobe - .008 * cleft - .0047 * relief * follicles
        )

    # Rear mounting plane and free anterior surface share the same border.
    rings = []
    angles = [pi / 2 - 2 * pi * i / 152 for i in range(152)]
    for radius, depth in ((.38, -.040), (.74, -.034), (.93, -.022), (.99, -.012), (1.003, -.004)):
        rings.append([(.111 * radius * cos(a), .064 * radius * sin(a) - .008, depth)
                      for a in angles])
    for step in range(48, 0, -1):
        radius = step / 48
        ring = []
        for a in angles:
            x = .111 * radius * cos(a)
            y = .064 * radius * sin(a) - .008
            ring.append((x, y, front(x, y, radius)))
        rings.append(ring)
    g.setup(finish="direct")
    g.slot("skin")
    _closed_sections(g, rings, (0, -.008, -.043), (0, -.008, front(0, -.008, 0)), size)


def elongate_lagomorph_hindfoot(g, p):
    """Four low toes sit at the end of a long fur-covered metatarsus."""
    size, length, spread = p["size"], p["length"], p["spread"]
    sections = (
        (-.070, .011, .011, -.036, -.065, .003, 0., 0.),
        (-.061, .024, .026, -.020, -.076, .003, 0., 0.),
        (-.046, .036, .039, -.007, -.083, .003, 0., 0.),
        (-.024, .040, .043, .001, -.086, .002, 0., 0.),
        (.006, .043, .045, -.004, -.088, 0., 0., 0.),
        (.035, .040, .043, -.010, -.089, 0., 0., 0.),
        (.067, .040, .044, -.020, -.090, .001, 0., 0.),
        (.102, .043, .046, -.026, -.091, .002, 0., 0.),
        (.145, .047, .050, -.032, -.092, .004, 0., .001),
        (.183, .054, .055, -.041, -.093, -.008, 0., .003),
        (.235, .058, .055, -.048, -.091, -.014, 0., .004),
    )
    form = _FootForm(sections, 4, ankle=(2, 5))
    form.cuff(-.011, .034, .035, .025, .002)
    # Native +X limb has medial digit II toward -X, with open spacing at tips.
    for i, (x, z) in enumerate(zip((-.048, -.016, .017, .046), (.276, .295, .290, .263))):
        root = form.toe(i)
        start = form.center(root)
        end = V(x * spread, -.075, z)
        blocks = ((.18, .0140, .0190), (.42, .0141, .0183), (.64, .0131, .0162),
                  (.83, .0110, .0133), (.95, .0080, .0095), (1., .0033, .0048))
        form.digit(root, [(start.lerp(end, t), width, height) for t, width, height in blocks])
    for vertex in form.vertices:
        vertex.z += (length - 1) * max(0, vertex.z - .040)
    g.setup(finish="sculpt")
    g.slot("skin")
    form.emit(g, size)


PARTS = [
    Part("square_stop_canine_muzzle", "feeding",
         "Straight canine bridge with a defined stop, closed lip commissure and square nose.",
         ["dog", "beagle", "canine", "snout", "stop", "lips"],
         {"size": SIZE, "reach": (.79, 1.25, 1.), "stop": (.76, 1.28, 1.)},
         square_stop_canine_muzzle, orient="native", hint=FRONT, symmetry="center"),
    Part("pendulous_folded_pinna", "sensory",
         "A low ear root rolls outward into a close-hanging, rounded cartilage flap.",
         ["beagle", "hound", "dog", "drooping", "floppy", "ear"],
         {"size": SIZE, "fall": (.80, 1.25, 1.), "inturn": (.60, 1.4, 1.)},
         pendulous_folded_pinna, orient="native", mirror=True, hint={"u": .87, "theta": 0.},
         symmetry="pair"),
    Part("bilateral_mystacial_pads", "sensory",
         "Paired cat whisker beds with a shallow midline furrow and staggered follicle seats.",
         ["cat", "feline", "whisker", "vibrissae", "upper lip"],
         {"size": SIZE, "fullness": (.74, 1.24, 1.), "relief": (.40, 1.22, 1.)},
         bilateral_mystacial_pads, orient="native", hint=FRONT, symmetry="center"),
    Part("elongate_lagomorph_hindfoot", "locomotion",
         "Elongated low hind foot with a continuous plantar surface and four distal toes.",
         ["rabbit", "lagomorph", "hind paw", "metatarsal", "toe"],
         {"size": SIZE, "length": (.85, 1.23, 1.), "spread": (.92, 1.15, 1.)},
         elongate_lagomorph_hindfoot, attach="tip", orient="native", cap="foot", symmetry="pair"),
]

TRAITS = {
    "square_stop_canine_muzzle": {
        "shape": "straight blunt canine rostrum with stop, lip commissure and paired nares",
        "construction": "deformable",
    },
    "pendulous_folded_pinna": {
        "shape": "rolled ear root and thin rounded hanging pinna",
        "construction": "deformable",
    },
    "bilateral_mystacial_pads": {
        "shape": "continuous shallow cheek seat with paired lobes and staggered ostia",
        "construction": "deformable",
    },
    "elongate_lagomorph_hindfoot": {
        "shape": "long low fur-covered metatarsal body and four terminal toes",
        "construction": "deformable",
        "function": "support",
    },
}
