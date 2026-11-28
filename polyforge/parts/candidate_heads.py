"""Inspect-only cranial and feeding anatomy in the native +Y-up, +Z-forward frame."""
from math import cos, exp, pi, sin

from scipy.interpolate import PchipInterpolator

from ..kit import BACK, V, smoothstep
from . import Part
from .anatomy import _loft
from .research_aesthetics import _closed_sections

SIZE = (.6, 1.8, 1)
FRONT = {"u": .89, "theta": -90}
DORSAL = {"u": .89, "theta": 90}


def seahorse_coronet(g, p):
    scale, height, lean = p["size"], p["height"], p["lean"]
    stations = (
        (-.032, .004, .040, .056),
        (-.012, .001, .051, .061),
        (.012, -.007, .045, .049),
        (.034, -.017, .034, .035),
        (.064, -.022, .027, .028),
        (.093, -.029, .032, .033),
        (.113, -.032, .031, .030),
        (.126, -.033, .018, .020),
        (.132, -.034, .005, .006),
    )
    g.setup(finish="direct")
    _loft(g, scale,
          [(0, y * height, z - max(0, y) * lean) for y, z, _, _ in stations],
          [(w, d) for _, _, w, d in stations], sides=32, up=BACK, exponent=.74, density=5)


def seahorse_suction_snout(g, p):
    scale, length, opening = p["size"], p["length"], p["opening"]
    outer = (
        (-.039, .010, .050, .056),
        (-.020, .008, .057, .055),
        (.000, .004, .050, .045),
        (.036, -.005, .039, .037),
        (.070, -.012, .031, .031),
        (.120, -.016, .028, .026),
        (.166, -.013, .028, .024),
        (.185, -.008, .035, .031),
        (.197, -.006, .037, .030),
        (.207, -.006, .031, .023),
    )
    aperture = .65 + .35 * opening
    inner = (
        (.210, -.006, .026 * aperture, .019 * opening),
        (.204, -.006, .022 * aperture, .016 * opening),
        (.189, -.007, .018 * aperture, .013 * opening),
        (.168, -.009, .014 * aperture, .010 * opening),
        (.150, -.011, .006 * aperture, .005 * opening),
    )
    angles = [pi / 2 - 2 * pi * index / 48 for index in range(48)]
    rings = [[(w * cos(a), y + d * sin(a), z * length) for a in angles]
             for z, y, w, d in outer + inner]
    g.setup(finish="subsurf_low")
    _closed_sections(g, rings, (0, .010, -.049 * length), (0, -.012, .146 * length), scale)


def monotreme_bill(g, p):
    scale, width, crown = p["size"], p["width"], p["crown"]
    upper = (
        (-.046, .088, .043, .015), (-.024, .138, .043, .011),
        (.000, .130, .031, .013), (.029, .100, .026, .008),
        (.068, .102, .023, .007), (.123, .112, .024, .005),
        (.176, .112, .021, .007), (.211, .102, .018, .009),
        (.231, .075, .014, .007), (.242, .045, .009, .006),
        (.249, .004, .002, .002),
    )
    lower = (
        (-.045, .081, -.028, .017), (-.018, .111, -.027, .020),
        (.021, .096, -.020, .015), (.070, .094, -.018, .012),
        (.126, .107, -.018, .011), (.179, .104, -.018, .010),
        (.212, .087, -.016, .007), (.233, .056, -.014, .005),
        (.240, .005, -.012, .002),
    )
    g.setup(finish="direct")
    _loft(g, scale, [(0, y, z) for z, _, y, _ in upper],
          [(w * width, d * crown) for _, w, _, d in upper], exponent=.56, sides=72, density=10)
    # Bound the indentation on the roof so dorsal nares never cut through the palate.
    for vertex in g.prims[-1].v:
        x, y, z = vertex / scale
        dx = abs(x) - .057 * width
        dz = z - .180
        along = .46 * dx + .89 * dz
        across = .89 * dx - .46 * dz
        profile = exp(-((along / .014) ** 2 + (across / .007) ** 2))
        vertex.y -= .014 * scale * profile * smoothstep(.022, .033, y)

    g.pivots["jaw"] = V(0, -.020, -.030) * scale
    g.use("jaw")
    g.setup(finish="direct")
    _loft(g, scale, [(0, y + .012 * smoothstep(-.023, .072, z), z) for z, _, y, _ in lower],
          [(w * width, d) for _, w, _, d in lower], exponent=.64, sides=40, density=6)


def bat_noseleaf(g, p):
    scale, spear, spread = p["size"], p["spear"], p["spread"]
    g.setup(finish="direct")
    g.oval(V(0, -.006, .012) * scale, (.095 * spread * scale, .046 * scale, .039 * scale),
           segs=88, rings=45)
    for vertex in g.prims[-1].v:
        x, y, z = vertex / scale
        x /= spread
        front = smoothstep(.016, .039, z)
        radius = ((x / .069) ** 2 + ((y + .001) / .035) ** 2) ** .5
        horseshoe = .011 * exp(-((radius - .94) / .20) ** 2) * (1 - .72 * smoothstep(.011, .030, y))
        dx = abs(x) - .029
        tilt = y + .005 - .33 * dx
        nares = .029 * exp(-((dx / .020) ** 2 + (tilt / .009) ** 2))
        septum = .006 * exp(-((x / .012) ** 2 + ((y + .006) / .021) ** 2))
        vertex.z += scale * front * (horseshoe + septum - nares)

    blade = ((.014, .022, .024, .020), (.036, .015, .040, .020),
             (.065, .007, .052, .016), (.096, .003, .047, .013),
             (.127, .006, .035, .012), (.157, .012, .021, .011),
             (.179, .022, .009, .006), (.187, .026, .002, .002))
    _loft(g, scale, [(0, y * spear, z) for y, z, _, _ in blade],
          [(w, d) for _, _, w, d in blade], up=BACK, sides=36, exponent=.72)


def sawfish_toothed_rostrum(g, p):
    scale, taper = p["size"], p["taper"]
    length = .674
    # The toothless continuation widens under the preorbital head. It gives the
    # host a long, curved contact rather than exposing the end of a short peg.
    stations = (-.285, -.267, -.242, -.213, -.182, -.150, -.116, -.068, 0,
                .12, .32, .57, .78, .91, .96, .982, .994, 1)
    widths = (.015, .049, .073, .083, .074, .065, .061, .055, .048,
              .046, .043, .040, .036, .032, .029, .027, .022, .009)
    depths = (.010, .025, .039, .043, .0435, .038, .031, .024, .018,
              .016, .014, .012, .009, .007, .006, .005, .004, .002)
    heights = (.016, .015, .013, .009, .004, .001, .001, .000, .000,
               .002, .005, .010, .015, .018, .019, .020, .021, .021)
    width_at = PchipInterpolator(stations, [w * (1 - taper * max(0, s)) for s, w in zip(stations, widths)])
    depth_at = PchipInterpolator(stations, depths)
    height_at = PchipInterpolator(stations, heights)
    samples = {*stations, *(i / 44 for i in range(-12, 44))}
    # The base of an awl-like tooth lies slightly anterior to its apex.
    # Use thin bases to preserve the exposed blade between successive teeth.
    tooth_profile = ((-.135, 0), (-.080, .60), (0, 1), (.115, .58), (.255, .27), (.315, 0))
    rows = {}
    for side, parameter in ((1, "left_teeth"), (-1, "right_teeth")):
        count = round(p[parameter])
        fractions = [index / (count - 1) for index in range(count)]
        centers = [.026 + .951 * (f + .53 * f * (1 - f)) for f in fractions]
        z_values, reaches = [stations[0]], [0]
        for center, fraction in zip(centers, fractions):
            spacing = .951 * (1.53 - 1.06 * fraction) / (count - 1)
            # The DNA-confirmed Naples rostrum's longest crown is 3.8% of TRL
            # (Fioravanti et al. 2023, table 1).
            tooth = (.0205 + .0057 * sin(pi * fraction)) * (1 - .38 * fraction ** 3)
            for offset, reach in tooth_profile:
                z_values.append(round(center + spacing * offset, 7))
                reaches.append(tooth * reach)
        rows[side] = PchipInterpolator(z_values + [1], reaches + [0])
        samples.update(z_values)

    profile = []
    for angle in (pi / 2 - 2 * pi * i / 24 for i in range(24)):
        x, y = cos(angle), sin(angle)
        side = 1 if x >= 0 else -1
        profile.append((x, y, side))
    rings = []
    ordered_samples = []
    for station in sorted(samples):
        if not ordered_samples or station - ordered_samples[-1] > 1e-5:
            ordered_samples.append(station)
    for station in ordered_samples:
        width, depth = float(width_at(station)), float(depth_at(station))
        center_y = float(height_at(station))
        reach = {side: max(0.0, float(row(station))) for side, row in rows.items()}
        section = 1 - .28 * smoothstep(-.16, 0, station)
        rings.append([(side * (abs(x) ** section * width + reach[side] * abs(x) ** 16),
                       center_y + depth * (1 if y >= 0 else -1) * abs(y) ** section,
                       length * station)
                      for x, y, side in profile])
    g.setup(finish="direct")
    _closed_sections(g, rings, (0, .016, -.297 * length), (0, .021, 1.002 * length), scale)


def anglerfish_esca_on_illicium(g, p):
    scale, flex = p["size"], p["flex"]
    g.setup(finish="direct")
    _loft(g, scale, [(0, -.019, -.050), (0, -.014, -.022), (0, -.007, .002),
                     (0, -.014, .016)],
          [(.010, .009), (.020, .014), (.011, .011), (.006, .007)], sides=22)
    g.pivots["illicium"] = V(0, -.004, 0) * scale
    g.use("illicium")
    g.setup(voxel=.00085 * scale, detail=2.6, smooth=.26)
    tip = V(0, .215 - .080 * flex, .213 + .078 * flex)
    _loft(g, scale, [(0, -.011, 0), (0, .039, .007), (0, .110, .053),
                     (0, .179 - .021 * flex, .115 + .008 * flex),
                     (0, .213 - .057 * flex, .169 + .040 * flex), tip],
          [(.009, .009), (.0078, .0072), (.006, .006),
           (.0050, .0047), (.0041, .0041), (.004, .004)], sides=20, density=6)
    for side in (-1, 1):
        points = [(side * x, y, z) for x, y, z in (
            (0, .000, -.007), (.009, -.002, .007), (.019, -.007, .017),
            (.026, -.021, .021), (.029, -.038, .019), (.025, -.047, .015))]
        _loft(g, scale, [tip + V(point) for point in points],
              [(.004, .005), (.012, .006), (.013, .006), (.011, .005),
               (.007, .0032), (.0014, .0014)], sides=22, density=5, up=BACK)


def rhinoceros_beetle_opposed_horns(g, p):
    scale, reach = p["size"], p["reach"]
    g.setup(voxel=.00165 * scale, detail=2.2, smooth=.30)
    _loft(g, scale, [(0, .017, -.063), (0, .047, -.034), (0, .078, .008),
                     (0, .107, .059), (0, .129, .127 * reach), (0, .128, .241 * reach),
                     (0, .106, .332 * reach), (0, .067, .406 * reach),
                     (0, .041, .444 * reach)],
          [(.037, .040), (.058, .049), (.050, .043), (.037, .035), (.027, .027),
           (.018, .021), (.014, .017), (.009, .012), (.0016, .003)], sides=32, density=6)
    for side in (-1, 1):
        _loft(g, scale, [(side * .013, .112, .171 * reach), (side * .021, .086, .181 * reach),
                         (side * .018, .058, .192 * reach)],
              [(.014, .014), (.013, .012), (.0019, .002)], sides=16, density=5, up=BACK)

    g.pivots["head"] = V(0, -.030, -.017) * scale
    g.use("head")
    g.setup(voxel=.0015 * scale, detail=2.1, smooth=.28)
    _loft(g, scale, [(0, -.054, -.029), (0, -.053, .010), (0, -.051, .065),
                     (0, -.051, .123 * reach), (0, -.040, .208 * reach),
                     (0, -.012, .291 * reach), (0, .016, .343 * reach),
                     (0, .044, .375 * reach)],
          [(.034, .026), (.054, .039), (.039, .028), (.027, .019),
           (.022, .015), (.016, .012), (.011, .008), (.002, .0025)], sides=30, density=6)
    for y, z, height in ((-.041, .130, .044), (-.032, .203, .040), (-.014, .269, .031)):
        _loft(g, scale, [(0, y, z * reach), (0, y + height * .56, (z + .004) * reach),
                         (0, y + height, (z + .010) * reach)],
              [(.019, .017), (.012, .009), (.0017, .0017)], up=BACK, sides=16, density=4)


def pelican_expandable_buccal_pouch(g, p):
    scale, spread, depth = p["size"], p["spread"], p["depth"]
    stations = (
        (-.085, .032, -.069, .024), (-.058, .074, -.061, .069),
        (-.009, .100, -.041, .137), (.056, .107, -.029, .172),
        (.129, .101, -.019, .170), (.218, .089, -.011, .154),
        (.304, .070, -.006, .121), (.382, .050, -.002, .083),
        (.446, .035, .000, .045), (.493, .022, .002, .020),
        (.515, .010, .001, .009), (.526, .002, .000, .002),
    )
    rings = []
    for z, width, seam, drop in stations:
        t = (z + .085) / .611
        width *= .90 + .10 * spread + .47 * spread * sin(pi * t)
        drop *= depth
        fractions = [cos(pi * i / 40) for i in range(40, -1, -1)]
        outer = []
        inside = []
        for x in fractions:
            wall = max(0.0, 1 - x * x) ** .70
            fold = .0025 * (1 - .67 * depth) * wall * sin(28 * t + 2 * x)
            y = seam - drop * wall + fold
            outer.append((width * x, y - .0038, z))
            inside.append((width * x, y + .0038, z))
        rings.append(inside + list(reversed(outer)))

    g.setup(finish="subsurf_low", slot_finish={"jaw_rim": "direct"})
    _closed_sections(g, rings, (0, -.069 - .024 * depth, -.090), (0, .000, .529), scale)
    g.slot("jaw_rim")
    for side in (-1, 1):
        rim = [(side * width * (.90 + .10 * spread + .47 * spread * sin(pi * (z + .085) / .611)),
                seam, z) for z, width, seam, _ in stations]
        _loft(g, scale, rim,
              [(radius, .83 * radius) for radius in (.010, .011, .010, .009, .0085, .008,
                                                    .007, .006, .0055, .005, .004, .0028)],
              sides=14, density=5)


def racked_baleen_plates(g, p):
    scale, count, curtain = p["size"], round(p["plates"]), p["curtain"]
    g.setup(finish="direct")
    rail = ((.139, -.004, -.185), (.144, .006, -.117), (.147, .008, -.010),
            (.135, .007, .141), (.106, .004, .267), (.069, .002, .356),
            (.035, -.001, .412), (.010, -.003, .435))
    half_width_at = PchipInterpolator([z for _, _, z in rail], [x for x, _, _ in rail])
    for side in (-1, 1):
        _loft(g, scale, [(side * x, y, z) for x, y, z in rail],
              [(.023, .021), (.027, .021), (.027, .018), (.025, .017),
               (.022, .016), (.017, .016), (.008, .009), (.003, .004)],
              sides=16, density=4)
        for index in range(count):
            t = (index + .5) / count
            z = -.174 + .601 * t
            x = float(half_width_at(z))
            drop = (.037 + .135 * sin(pi * t) ** .81) * curtain
            broad = min(.025 + .049 * sin(pi * t) ** .70, max(.004, x - .022))
            reach = min(.004 + .030 * sin(pi * t), broad * .55)
            plate_x = x - .019
            outline = [(side * (plate_x + dx), y, z + dz) for dx, y, dz in (
                (-broad, .008, -.001), (.034, .009, .002), (.033, -.24 * drop, .006),
                (.026, -.57 * drop, .010), (.009, -drop, .014),
                (-reach, -.83 * drop, .010), (-(broad - .010), -.40 * drop, .006))]
            g.slab([V(pt) * scale for pt in outline], BACK,
                   min(.0046, .25 * .601 / count) * scale, bulge=.24)
            for fringe in (.28, .56, .86):
                y = -drop * (.40 + .43 * fringe)
                root_x = side * (plate_x - (broad - .010) * (1 - fringe) - reach * fringe + .001)
                root_z = z + .006 + .004 * fringe
                fringe_len = (.007 + .013 * fringe) * min(1, drop / .09, 8 * x)
                _loft(g, scale,
                      [(root_x, y, root_z), (root_x - side * fringe_len * .45, y - fringe_len * .5, root_z + .001),
                       (root_x - side * fringe_len, y - fringe_len, root_z + .002)],
                      [(.0015, .0011), (.0011, .0009), (.00055, .00048)],
                      sides=5, density=1)


PARTS = [
    Part("seahorse_coronet", "aesthetics", "Compact median cranial column with a blunt dwarf-seahorse crown.",
         ["seahorse", "coronet", "column", "skull"], {"size": SIZE, "height": (.75, 1.30, 1), "lean": (-.15, .24, .03)},
         seahorse_coronet, orient="native", hint=DORSAL, symmetry="center"),
    Part("seahorse_suction_snout", "feeding", "Slender cranial tube with an inset terminal oral cavity.",
         ["seahorse", "suction", "mouth", "tube"], {"size": SIZE, "length": (.75, 1.32, 1), "opening": (.28, 1, .73)},
         seahorse_suction_snout, orient="native", hint=FRONT, symmetry="center"),
    Part("monotreme_bill", "sensory", "Flattened sensory bill with a bill shield and paired dorsal nostrils.",
         ["platypus", "monotreme", "bill", "nares"], {"size": SIZE, "width": (.85, 1.2, 1), "crown": (.75, 1.25, 1)},
         monotreme_bill, orient="native", hint=FRONT, symmetry="center",
         bones=[{"name": "jaw", "pivot": (0, -.020, -.030), "axis": (1, 0, 0), "angle": 16}]),
    Part("bat_noseleaf", "sensory", "Thin facial spear and raised horseshoe surrounding paired nostrils.",
         ["bat", "phyllostomid", "noseleaf", "echolocation"], {"size": SIZE, "spear": (.76, 1.25, 1), "spread": (.8, 1.25, 1)},
         bat_noseleaf, orient="native", hint=FRONT, symmetry="center"),
    Part("sawfish_toothed_rostrum", "feeding", "Flat anterior rostrum with independently counted lateral tooth rows.",
         ["sawfish", "rostrum", "denticles", "ray"], {"size": SIZE, "taper": (.05, .34, .15),
                                                   "left_teeth": (22, 29, 26), "right_teeth": (22, 29, 25)},
         sawfish_toothed_rostrum, orient="native", hint={"u": .996, "theta": 90}, symmetry="center",
         discrete=("left_teeth", "right_teeth")),
    Part("anglerfish_esca_on_illicium", "feeding", "Pivoted median dorsal ray carrying a bifid terminal bait.",
         ["monkfish", "anglerfish", "illicium", "esca", "lure"], {"size": SIZE, "flex": (0, 1, .30)},
         anglerfish_esca_on_illicium, orient="native", hint=DORSAL, symmetry="center",
         bones=[{"name": "illicium", "pivot": (0, -.004, 0), "axis": (1, 0, 0), "angle": 40}]),
    Part("rhinoceros_beetle_opposed_horns", "aesthetics", "Opposed cephalic and pronotal horns on distinct roots.",
         ["beetle", "dynastes", "head", "pronotum", "horns"], {"size": SIZE, "reach": (.80, 1.25, 1)},
         rhinoceros_beetle_opposed_horns, orient="native", hint=FRONT, symmetry="center",
         bones=[{"name": "head", "pivot": (0, -.030, -.017), "axis": (1, 0, 0), "angle": -4}]),
    Part("pelican_expandable_buccal_pouch", "feeding", "Open dependent scoop spanning the bowing lower mandible.",
         ["pelican", "bill", "lower jaw", "gular pouch"], {"size": SIZE, "spread": (0, 1, .50), "depth": (.24, 1, .66)},
         pelican_expandable_buccal_pouch, orient="native", hint=FRONT, symmetry="center"),
    Part("racked_baleen_plates", "feeding", "Paired palatal racks with transverse plates and medial fringes.",
         ["humpback", "whale", "baleen", "filter", "palate"], {"size": SIZE, "plates": (22, 48, 39), "curtain": (.65, 1.4, 1)},
         racked_baleen_plates, orient="native", hint=FRONT, symmetry="pair", discrete=("plates",)),
]

TRAITS = {
    "seahorse_coronet": {"function": "display", "construction": "rigid", "shape": "knobbed cranial column"},
    "seahorse_suction_snout": {"function": "feeding", "construction": "deformable", "shape": "tube with terminal opening"},
    "monotreme_bill": {"function": "sensing", "construction": "rigid", "shape": "broad oval bill with dorsal nares"},
    "bat_noseleaf": {"function": "sensing", "construction": "deformable", "shape": "nose spear and narial horseshoe"},
    "sawfish_toothed_rostrum": {"function": "feeding", "construction": "rigid", "shape": "flat rostral blade with lateral teeth"},
    "anglerfish_esca_on_illicium": {"function": "feeding", "construction": "deformable", "shape": "curved ray with bifid bait"},
    "rhinoceros_beetle_opposed_horns": {"function": "display", "construction": "rigid", "shape": "opposed head and pronotal horns"},
    "pelican_expandable_buccal_pouch": {"function": "feeding", "construction": "deformable", "shape": "open scoop suspended from bowing jaw"},
    "racked_baleen_plates": {"function": "feeding", "construction": "rigid", "shape": "paired palatal curtains of transverse plates"},
}
