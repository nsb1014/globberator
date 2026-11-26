"""Feeding anatomy in the research frame (+Y up, +Z forward)."""
import math

from ..kit import RIGHT, UP, V, lerp, smoothstep

TENTACLE_FRINGE_RADIUS = 0.230


def _sized(sculpt):
    def build(g, p):
        sculpt(g, p)
        size = p["size"]
        for piece in g.pieces.values():
            for prim in piece.prims:
                prim.v = [v * size for v in prim.v]
            if piece.voxel is not None:
                piece.voxel *= size
        for name in g.pivots:
            g.pivots[name] *= size
    return build


def _tooth(g, point, width, height, direction):
    x, y, z = point
    g.loft([(x, y, z), (x, y + direction * height * 0.43, z),
            (x * 0.96, y + direction * height * 0.80, z - height * 0.08),
            (x * 0.91, y + direction * height, z - height * 0.17)],
           [(width, width * 1.13), (width * 0.67, width * 0.73),
            (width * 0.28, width * 0.32), (width * 0.05, width * 0.05)],
           sides=10, up=RIGHT, density=2)


# The rear stations form the host overlap. The final loops shape the integrated
# nose and cheek-pad creases.
_MUZZLE_STATIONS = (
    # z, half width, dorsal rise, ventral drop, center height, cheek relief
    (-.087, .048, .061, .052, .024, .00),
    (-.071, .080, .085, .069, .025, .00),
    (-.044, .097, .102, .081, .026, .00),
    (-.004, .103, .108, .087, .023, .06),
    (.034, .101, .101, .091, .013, .16),
    (.072, .091, .082, .090, .003, .28),
    (.113, .077, .063, .077, -.003, .45),
    (.151, .068, .047, .064, -.010, .60),
    (.183, .060, .039, .054, -.012, .82),
    (.206, .053, .033, .046, -.014, .98),
    (.222, .044, .028, .037, -.014, 1.0),
    (.233, .032, .021, .027, -.013, .68),
    (.239, .019, .013, .015, -.011, .30),
    (.242, .009, .006, .007, -.010, .08),
)

# Clockwise from the center of the bridge down to the center of the chin.
# The extra ventral loops carry the two whisker pads and the philtrum.
_MUZZLE_HALF_PROFILE = (
    (0., 1.), (.24, .981), (.48, .928), (.70, .805), (.88, .607),
    (.971, .326), (1., .048), (.995, -.228), (.980, -.385), (.961, -.515),
    (.933, -.607), (.896, -.699), (.852, -.773), (.796, -.841),
    (.694, -.927), (.475, -.999), (.252, -.988),
    (.108, -.990), (0., -.991),
)


def muzzle_nose_socket(params):
    """Local seat for an independent, +Z facing nose pad."""
    return V(0, -.008, .232) * params["size"]


def muzzle_nose_scale(params):
    """Scale the nose pad to match the width of this muzzle's tip."""
    return params["size"] * (.47 - .13 * params["taper"])


def muzzle(g, p):
    g.setup(finish="sculpt")
    g.slot("skin")
    half = _MUZZLE_HALF_PROFILE
    outline = [*half, *((-x, y) for x, y in reversed(half[1:-1]))]
    rings = []
    for z, width, rise, drop, center, cheek in _MUZZLE_STATIONS:
        taper = 1.0 + (0.6 - p["taper"]) * .46 * smoothstep(.045, .222, z)
        lip_track = -.43 - .30 * smoothstep(.075, .182, z) + .095 * smoothstep(.209, .236, z)
        lip_extent = smoothstep(.082, .151, z) * (1.0 - smoothstep(.223, .243, z))
        ring = []
        for x, y in outline:
            cheek_bulge = cheek * smoothstep(-.15, -.82, y)
            seam = cheek_bulge * (1.0 - smoothstep(0.0, .30, abs(x)))
            nasal_roll = cheek * smoothstep(.05, .64, y) * (1 - .60 * abs(x))
            lip = lip_extent * math.exp(-((y - lip_track) / .097) ** 2) * smoothstep(.31, .77, abs(x))
            pad = lip_extent * math.exp(-((y - lip_track - .21) / .26) ** 2)
            pad *= math.exp(-((abs(x) - .78) / .36) ** 2)
            lateral = x * width * taper * (1.0 + .13 * cheek_bulge + .16 * pad)
            lateral -= math.copysign(.011 * lip, x)
            vertical = center + y * (rise if y >= 0.0 else drop) + .013 * seam
            forward = z + .007 * nasal_roll - .011 * seam
            forward += (.008 * pad - .006 * lip) * smoothstep(.161, .220, z)
            forward -= .012 * cheek * x * x
            ring.append((lateral, vertical, forward))
        rings.append(ring)
    _closed_sections(g, rings, (0, .024, -.095), (0, -.010, .245))


# Sections share profile stations across exterior, alveolar ridge, and palate.
# Rear palate stations retreat at the center to form the horseshoe cutout.
_UPPER_GUM = (
    # z, half width, exterior Y, gum ridge Y, vault depth, rear notch depth
    (-.064, .063, .073, .037, .010, .018),
    (-.054, .082, .085, .027, .015, .027),
    (-.035, .098, .092, .017, .024, .028),
    (-.010, .104, .091, .015, .026, .023),
    (.023, .103, .085, .012, .023, .016),
    (.058, .097, .076, .014, .024, .009),
    (.097, .087, .070, .015, .024, .003),
    (.132, .078, .066, .016, .020, .000),
    (.160, .070, .063, .017, .018, .000),
    (.181, .059, .060, .018, .014, .000),
    (.199, .048, .055, .018, .011, .000),
    (.215, .034, .048, .022, .007, .000),
    (.223, .018, .041, .028, .004, .000),
    (.226, .008, .038, .032, .001, .000),
)

_LOWER_GUM = (
    (-.090, .032, -.041, -.004, .010, .017),
    (-.081, .052, -.050, .009, .018, .022),
    (-.068, .071, -.063, .012, .027, .025),
    (-.051, .083, -.077, -.011, .025, .021),
    (-.033, .090, -.093, -.030, .025, .019),
    (-.011, .094, -.098, -.047, .023, .018),
    (.023, .097, -.104, -.054, .026, .016),
    (.056, .094, -.110, -.059, .026, .008),
    (.091, .088, -.117, -.066, .028, .000),
    (.126, .080, -.122, -.071, .026, .000),
    (.151, .069, -.123, -.073, .023, .000),
    (.175, .054, -.121, -.073, .020, .000),
    (.193, .042, -.117, -.074, .016, .000),
    (.206, .027, -.110, -.077, .011, .000),
    (.214, .014, -.105, -.083, .005, .000),
    (.217, .006, -.099, -.090, .001, .000),
)


def _gum_station(stations, z):
    for a, b in zip(stations, stations[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return (z, *(lerp(start, end, t) for start, end in zip(a[1:], b[1:])))
    raise ValueError(f"Tooth station z={z} lies outside the gum")


def _gum_point(station, across, inside, lower, inset):
    z, width, outside, ridge, hollow, rear_notch = station
    lateral = abs(across)
    direction = -1.0 if lower else 1.0
    edge = smoothstep(.76, 1.0, lateral)
    if inside:
        x = across * width * (1.0 - .015 * edge)
        y = ridge + direction * (hollow * (1.0 - lateral) ** 2 + .008 * edge)
    else:
        x = across * width
        y = lerp(outside, ridge, .67 * lateral ** 2.3)
    z += rear_notch * (1.0 - lateral) ** 2
    # The lower condyles rise into the host while the underslung control drops
    # the front of the arcade.
    if lower:
        drop = .006 + .043 * smoothstep(-.066, .052, station[0])
    else:
        drop = .010 + .029 * smoothstep(-.062, -.006, station[0])
    x *= 1.0 + .10 * inset
    y -= inset * drop
    z = -.043 + (z + .043) * (1.0 - inset * (.06 if lower else .14))
    return V(x, y, z)


def _jaw_gum(g, stations, lower, inset):
    fractions = (-1., -.92, -.78, -.60, -.39, -.18, 0., .18, .39, .60, .78, .92, 1.)
    rings = []
    for station in stations:
        top = [_gum_point(station, across, lower, lower, inset) for across in fractions]
        bottom = [_gum_point(station, across, not lower, lower, inset) for across in reversed(fractions)]
        rings.append(top + bottom)
    center = [(_gum_point(station, 0.0, True, lower, inset) +
               _gum_point(station, 0.0, False, lower, inset)) * .5
              for station in (stations[0], stations[-1])]
    center[0].z -= .007
    center[1].z += .003
    _closed_sections(g, rings, *center)


def _jaw_teeth(g, stations, teeth, rows, inset, lower):
    g.slot("teeth")
    direction = 1.0 if lower else -1.0
    teeth_z = (.014, .053, .094, .137, .181) if lower else (.024, .065, .105, .156, .190)
    crown_heights = (.030, .033, .037, .065, .037)
    for row in range(5):
        for side in (-1, 1):
            for z, height in zip(teeth_z, crown_heights):
                station = _gum_station(stations, z - .0050 * row)
                across = side * (.76 - .126 * row)
                exposed = row < rows and teeth > 0.0
                point = _gum_point(station, across, True, lower, inset)
                crown = (.23 + .77 * teeth) * (1.0 - .09 * row)
                point.y -= direction * (.008 - .00035 * row)
                if not exposed:
                    # Suppressed teeth stay within the gum and keep an editable cage.
                    exterior = _gum_point(station, across, False, lower, inset)
                    point = point.lerp(exterior, .40)
                    crown = .050
                _tooth(g, point, (.0075 + .098 * height) * crown,
                       height * crown * (.85 if lower else 1.0), direction)


def jaws_toothed(g, p):
    inset, rows = p["underslung"], round(p["tooth_rows"])
    for piece, stations in (("self", _UPPER_GUM), ("jaw", _LOWER_GUM)):
        lower = piece == "jaw"
        g.use(piece)
        g.setup(finish="sculpt", slot_finish={"teeth": "direct"})
        g.slot("base")
        _jaw_gum(g, stations, lower, inset)
        _jaw_teeth(g, stations, p["teeth"], rows, inset, lower)
    g.pivots["jaw"] = V(0, -.022 - .006 * inset, -.074 + .00186 * inset)


def _closed_sections(g, rings, first_cap, last_cap):
    sides = len(rings[0])
    verts = [vert for ring in rings for vert in ring]
    faces = []
    for index in range(len(rings) - 1):
        a, b = index * sides, (index + 1) * sides
        for j in range(sides):
            following = (j + 1) % sides
            faces.append((a + j, b + j, b + following, a + following))
    first, last = len(verts), len(verts) + 1
    final_ring = len(verts) - sides
    for j in range(sides):
        following = (j + 1) % sides
        faces.extend(((first, j, following), (last, final_ring + following, final_ring + j)))
    g._add(verts + [first_cap, last_cap], faces)


def mouth_wide(g, p):
    curve = 0.036 * p["curve"]
    half_width = 0.202
    g.setup(finish="subsurf")
    g.slot("base")
    sections = [(-1.0, 0.008, 0.014, 0.031), (-0.92, 0.035, 0.038, 0.041),
                (-0.73, 0.058, 0.057, 0.048), (-0.47, 0.073, 0.069, 0.053),
                (-0.24, 0.081, 0.076, 0.055), (0, 0.082, 0.077, 0.056),
                (0.24, 0.081, 0.076, 0.055), (0.47, 0.073, 0.069, 0.053),
                (0.73, 0.058, 0.057, 0.048), (0.92, 0.035, 0.038, 0.041),
                (1.0, 0.008, 0.014, 0.031)]
    rings = []
    for x, depth, height, mid in sections:
        ring_x = x * half_width
        seam = -0.008 + curve * x * x
        front = mid + depth
        gap = 0.001 + 0.007 * (1 - x * x)
        notch = 0.003 + 0.022 * (1 - x * x)
        start = math.asin(gap / (height * 1.13))
        end = math.tau - math.asin(gap / (height * 0.89))
        angles = [start, start + 0.080] + [k * math.tau / 24 for k in range(1, 24)] + [end - 0.080, end]
        ring = [(ring_x, seam + height * math.sin(a) * (1.13 if a < math.pi else 0.89),
                 mid + depth * math.cos(a)) for a in angles]
        ring.extend((ring_x, seam + gap * side_height, front - notch * step)
                    for side_height, step in ((-0.68, 0.18), (-0.46, 0.91), (0.46, 0.91), (0.68, 0.18)))
        rings.append(ring)
    _closed_sections(g, rings, (-0.205, -0.008 + curve, 0.031), (0.205, -0.008 + curve, 0.031))


def beak_hooked(g, p):
    hook = p["hook"]
    g.setup(voxel=0.00145, detail=2.5, smooth=0.30)
    g.slot("horn")
    top = [(0, 0.029, -0.037), (0, 0.041, -0.005), (0, 0.046, 0.045),
           (0, 0.036, 0.100), (0, 0.020 - hook * 0.020, 0.151),
           (0, 0.004 - hook * 0.045, 0.180),
           (0, -0.003 - hook * 0.098, 0.193 - hook * 0.008)]
    g.loft(top, [(0.036, 0.041), (0.067, 0.068), (0.064, 0.064), (0.049, 0.052),
                 (0.030, 0.039), (0.015, 0.021), (0.0012, 0.0017)],
           sides=24, exponent=0.79)
    notch = p["tomial_tooth"]
    for side in (-1, 1):
        g.loft([(side * 0.037, 0.007, 0.098), (side * 0.040, -0.006, 0.108),
                (side * 0.036, -0.009 - 0.018 * notch, 0.117)],
               [0.014, 0.012, 0.0014], sides=12)
    cere = p["cere"]
    g.slot("detail")
    g.loft([(0, 0.023 - (1 - cere) * 0.013, -0.038),
            (0, 0.034, -0.015), (0, 0.043, 0.012), (0, 0.050, 0.026)],
           [(0.030 + 0.013 * cere, 0.025 + 0.020 * cere),
            (0.036 + 0.036 * cere, 0.030 + 0.045 * cere),
            (0.033 + 0.024 * cere, 0.029 + 0.043 * cere),
            (0.025 + 0.011 * cere, 0.025 + 0.030 * cere)], sides=22)
    g.pivots["jaw"] = V(0, -0.028, -0.030)
    g.use("jaw")
    g.setup(voxel=0.00135, detail=1.8, smooth=0.34)
    g.slot("horn")
    g.loft([(0, -0.033, -0.036), (0, -0.046, -0.012), (0, -0.057, 0.040),
            (0, -0.066, 0.090), (0, -0.063 - 0.012 * hook, 0.142)],
           [(0.030, 0.012), (0.050, 0.018), (0.044, 0.017),
            (0.029, 0.013), (0.0014, 0.0019)], sides=20, exponent=0.8)


def mandibles(g, p):
    curl = p["curl"]
    g.setup(voxel=0.00165, detail=2.2, smooth=0.32)
    g.slot("horn")
    points = [(0, 0, -0.025), (0.021, 0.002, 0.020), (0.064, 0.006, 0.073),
              (0.096, 0.004, 0.143), (0.109 - 0.040 * curl, 0.000, 0.204),
              (0.112 - 0.086 * curl, -0.010, 0.241), (0.095 - 0.149 * curl, -0.016, 0.256)]
    radii = [(0.026, 0.024), (0.037, 0.033), (0.039, 0.029), (0.035, 0.025),
             (0.025, 0.018), (0.014, 0.011), (0.0013, 0.0012)]
    g.loft(points, radii, sides=20, exponent=0.75)
    g.oval((0, 0, 0.002), (0.042, 0.039, 0.037), segs=20)
    tines = round(p["tines"])
    for index, step in enumerate((3, 2, 4)):
        x, y, z = points[step]
        scale = 1.0 - index * 0.21 if index < tines else 0.065
        g.loft([(x, y, z), (x - 0.039 * scale, y - 0.002, z + 0.008 * scale),
                (x - 0.068 * scale, y - 0.006, z + 0.029 * scale)],
               [(0.023 * scale, 0.020 * scale), (0.014 * scale, 0.013 * scale),
                (0.0013 * scale, 0.0013 * scale)], sides=14)
    chelate = max(p["chelate"], 0.045)
    x, y, z = points[4]
    g.loft([(x, y, z), (x - 0.029 * chelate, y - 0.010 * chelate, z + 0.025 * chelate),
            (x - 0.036 * chelate, y - 0.014 * chelate, z + 0.053 * chelate)],
           [(0.017 * chelate, 0.012 * chelate), (0.012 * chelate, 0.009 * chelate),
            (0.0008 * chelate, 0.0008 * chelate)], sides=12)


def mouth_palps(g, p):
    segments = round(p["segments"])
    plate = p["plate"]
    points, radii = [], []
    for k in range(91):
        t = k / 90
        phase = math.pi * t * segments
        bead = abs(math.sin(phase)) ** 0.62
        collar = 0.19 * math.exp(-((abs(math.sin(phase)) - 0.11) * 13) ** 2)
        tip = max(0.06, min(1.0, (t * 23) ** 0.65, ((1.0 - t) * 22) ** 0.65))
        radius = (0.032 - 0.014 * t) * (0.50 + 0.50 * bead + collar) * tip
        points.append((0.038 * t + 0.016 * math.sin(math.pi * t),
                       -0.081 * t + 0.012 * math.sin(2 * math.pi * t),
                       -0.014 + 0.193 * t))
        radii.append((radius * (1 + 0.87 * plate), radius * (1 - 0.56 * plate)))
    g.setup(finish="subsurf")
    g.slot("base")
    g.loft(points, radii, sides=12, density=1, exponent=0.84)


def tongue(g, p):
    fork, pad, extend = p["fork"], p["tip_pad"], p["extend"]
    reach = 0.228 + 0.188 * extend
    width = 1.0 - 0.43 * extend
    level = 0.010 + 0.031 * extend
    g.setup(voxel=0.0015, detail=2.5, smooth=0.39)
    g.slot("detail")
    g.loft([(0, -0.018, -0.026), (0, -0.014, 0.015), (0, -0.003, reach * 0.30),
            (0, level * 0.52, reach * 0.57), (0, level, reach * (0.82 - 0.15 * fork)),
            (0, level * 0.91, reach * (0.96 - 0.23 * fork)),
            (0, level * 0.88, reach * (1.01 - 0.24 * fork))],
           [(0.013, 0.013), (0.032 * width, 0.022), (0.048 * width, 0.023),
            (0.058 * width, 0.024), (0.062 * width * (0.86 + 0.27 * pad), 0.021 + 0.006 * pad),
            (0.040 * width * (0.82 + 0.31 * pad), 0.014 + 0.003 * pad), (0.009, 0.004)],
           sides=44, exponent=0.75, density=7)
    for vert in g.current.prims[-1].v:
        if vert.y > 0.006:
            start = smoothstep(0.030, 0.071, vert.z)
            end = 1 - smoothstep(reach * (0.77 - 0.15 * fork), reach * (0.94 - 0.18 * fork), vert.z)
            vert.y -= 0.0041 * start * end * math.exp(-(vert.x / 0.008) ** 2)
    for side in (-1, 1):
        g.loft([(side * 0.011, level * 0.59, reach * 0.62),
                (side * (0.016 + 0.013 * fork), level * 0.81, reach * 0.76),
                (side * (0.020 + 0.020 * fork), level * 0.90 + 0.012 * fork, reach * (0.81 + 0.12 * fork)),
                (side * (0.021 + 0.028 * fork), level * 0.88 + 0.016 * fork, reach * (0.84 + 0.19 * fork))],
               [(0.018, 0.010), (0.016, 0.010), (0.010, 0.006), (0.002, 0.002)], sides=14)


def oral_arms(g, p):
    count = round(p.get("count", 4))
    frill = p["frill"]
    g.setup(finish="direct")
    g.slot("base")
    g.oval((0, 0.012, 0), (0.042, 0.025, 0.042), segs=28)
    for index in range(5):
        angle = math.tau * index / count + math.radians(55)
        radial = V(math.cos(angle), 0, math.sin(angle))
        tangent = UP.cross(radial)
        scale = 1.0 if index < count else 0.05
        points, radii = [], []
        for k in range(37):
            t = k / 36
            wave = math.sin(math.tau * (4.2 * t + index * 0.12))
            bend = 0.022 + 0.083 * math.sin(t * math.pi / 2) + 0.042 * t * t
            centre = radial * (bend + frill * wave * 0.015 * t)
            centre += tangent * (0.022 * math.sin(math.tau * (t - index * 0.16)) * t +
                                 frill * 0.014 * wave * t)
            centre.y = 0.017 - t * (0.34 + 0.018 * math.cos(angle + 0.65))
            points.append(centre * scale)
            envelope = min(1.0, 0.44 + 3.2 * t, 0.055 + (1.0 - t) * 3.2)
            width = 0.031 * envelope * (1 + 0.42 * frill * wave) * scale
            radii.append((width, 0.010 * envelope * (1.0 - 0.27 * t) * scale))
        g.loft(points, radii, sides=18, up=radial - tangent * 0.45, exponent=0.77, density=2)


def _ring(g, radius, thickness):
    major_steps, minor_steps = 72, 8
    verts, faces = [], []
    for i in range(major_steps):
        a = math.tau * i / major_steps
        for j in range(minor_steps):
            b = math.tau * j / minor_steps
            r = radius + thickness * math.cos(b)
            verts.append((r * math.cos(a), thickness * math.sin(b), r * math.sin(a)))
            there, around = (i + 1) % major_steps, (j + 1) % minor_steps
            faces.append((i * minor_steps + j, i * minor_steps + around,
                          there * minor_steps + around, there * minor_steps + j))
    g._add(verts, faces)


def tentacle_fringe(g, p):
    radius = TENTACLE_FRINGE_RADIUS
    count = round(p.get("count", 80))
    sway = p["sway"]
    g.setup(finish="direct")
    g.slot("base")
    _ring(g, radius, 0.0055)
    for index in range(104):
        angle = math.tau * (index % count) / count
        variation = 0.56 + 0.27 * math.sin(index * 2.317) + 0.17 * math.sin(index * 3.683)
        # Unused strands stay inside the support ring so count changes keep the cage stable.
        length = 0.231 + variation * 0.141 if index < count else 0.001
        radial = V(math.cos(angle), 0, math.sin(angle))
        tangent = UP.cross(radial)
        points, radii = [], []
        for k in range(10):
            t = k / 9
            phase = math.tau * (1.22 * t + variation)
            bend = sway * length * t * (0.25 + 0.15 * math.sin(phase))
            dangle = sway * length * 0.13 * t * math.sin(phase + angle)
            points.append(radial * (radius + bend) + tangent * dangle + V(0, -length * t, 0))
            width = (0.00166 + 0.00036 * variation) * (1.0 - t * 0.96)
            radii.append(width)
        g.loft(points, radii, sides=8, up=radial, density=3)


def gill_slits(g, p):
    count = round(p.get("count", 5))
    depth, height, length = 0.055, 0.091, 0.172
    gap = 0.023 + p["spacing"] * 0.021
    g.setup(finish="direct")
    g.slot("base")
    centers = [((count - 1) * 0.5 - k) * gap for k in range(count)]
    slit_heights = [(0.067 - 0.0046 * k) * math.sqrt(max(0.20, 1 - (z / length) ** 2))
                    for k, z in enumerate(centers)]
    rings = []
    for k in range(1, 222):
        theta = math.pi * k / 222
        z, width = -length * math.cos(theta), math.sin(theta)
        ring = []
        for j in range(76):
            phi = math.tau * j / 76
            face = math.cos(phi)
            x, y = depth * width * face, -height * width * math.sin(phi)
            hollow = 0.0
            if face > 0.0:
                for center, slit_height in zip(centers, slit_heights):
                    t = y / slit_height
                    if abs(t) < 1:
                        taper = (1 - t * t) ** 0.64
                        slit_z = center + 0.012 * t + 0.014 * t * t
                        value = (z - slit_z) / (0.0062 * (0.30 + 0.70 * taper))
                        hollow += 0.012 * taper * max(0, 1 - value * value) ** 2
            ring.append((x - smoothstep(0.01, 0.26, face) * hollow, y, z))
        rings.append(ring)
    _closed_sections(g, rings, (0, 0, -length), (0, 0, length))


BUILDERS = {sculpt.__name__: _sized(sculpt) for sculpt in (
    jaws_toothed, muzzle, mouth_wide, beak_hooked, mandibles,
    mouth_palps, tongue, oral_arms, tentacle_fringe, gill_slits,
)}

EXTRA_PARAMS = {
    "oral_arms": {"count": (2, 5, 4)},
    "tentacle_fringe": {"count": (56, 104, 80)},
    "gill_slits": {"count": (3, 6, 5)},
}

OVERRIDES = {
    "jaws_toothed": {"orient": "native", "hint": {"u": 0.97, "theta": -90.0}, "cap": "mouth", "bones": [
        {"name": "jaw", "pivot": (0, -.022, -.074), "axis": (1, 0, 0), "angle": 32.0}]},
    "muzzle": {"orient": "native", "hint": {"u": 0.96, "theta": 90.0}},
    "mouth_wide": {"orient": "native", "hint": {"u": 0.97, "theta": -90.0}},
    "beak_hooked": {"orient": "native", "hint": {"u": 0.97, "theta": 90.0}, "cap": "mouth", "bones": [
        {"name": "jaw", "pivot": (0, -0.028, -0.030), "axis": (1, 0, 0), "angle": 23.0}]},
    "mandibles": {"orient": "native", "hint": {"u": 0.93, "theta": -63.0}},
    "mouth_palps": {"orient": "native", "hint": {"u": 0.93, "theta": -73.0}},
    "tongue": {"orient": "native", "hint": {"u": 0.97, "theta": -90.0}},
    "oral_arms": {"orient": "native", "hint": {"u": 0.5, "theta": -90.0}},
    "tentacle_fringe": {"orient": "native", "hint": {"u": 0.5, "theta": -90.0}},
    "gill_slits": {"orient": "native"},
}
