"""Dorsal armor, display membranes and orbital bone in the native body frame."""

from math import cos, exp, pi, sin

from scipy.interpolate import PchipInterpolator

from ..kit import BACK, RIGHT, UP, V, lerp


def _closed_sections(g, rings, start, end, size):
    """Join consistently wound sections and close both ends with single poles."""
    sides = len(rings[0])
    verts = [V(point) * size for ring in rings for point in ring]
    verts.extend((V(start) * size, V(end) * size))
    faces = []
    for section in range(len(rings) - 1):
        a, b = section * sides, (section + 1) * sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((a + i, b + i, b + j, a + j))
    last_ring = (len(rings) - 1) * sides
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((len(verts) - 2, i, j))
        faces.append((len(verts) - 1, last_ring + j, last_ring + i))
    g._add(verts, faces)


def _angles(count):
    return [2 * pi * i / count for i in range(count)]


def carapace(g, p):
    """Bilateral domed shell with teeth integrated into the anterior rim."""
    size = p["size"]
    teeth = round(p["rim_teeth"])
    tooth_step = 0.49 * min(1, 5 / max(1, teeth))
    tooth_angles = [tooth_step * (i - (teeth - 1) / 2) for i in range(teeth)]
    crown = 0.035 + 0.15 * p["dome"]
    outline = []
    for i in range(96):
        angle = 2 * pi * i / 96 - pi
        front = cos(angle)
        serration = sum(exp(-((angle - center) / 0.105) ** 2) for center in tooth_angles)
        shoulder = 0.035 * exp(-((abs(angle) - 1.36) / 0.14) ** 2)
        x = 0.232 * sin(angle) * (1 + 0.14 * front + shoulder)
        z = 0.147 * front * (1 + shoulder) - 0.025
        outline.append((x, z, 0.024 * sin(angle) * serration, 0.033 * front * serration))

    rings = []
    for fraction in (0.16, 0.34, 0.52, 0.68, 0.80, 0.89, 0.96, 1.0, 0.998, 0.96, 0.82, 0.58, 0.30):
        if len(rings) < 8:
            y = 0.002 + crown * (1 - fraction ** 2.45) ** 0.66
        else:
            y = -0.009 - 0.032 * (1 - fraction ** 2) ** 0.55
        tooth_profile = fraction ** 7
        rings.append([(x * fraction + dx * tooth_profile, y - 0.20 * dz * tooth_profile,
                       -0.022 + (z + 0.022) * fraction + dz * tooth_profile) for x, z, dx, dz in outline])

    g.setup(detail=1.8, smooth=0.3)
    _closed_sections(g, rings, (0, crown + 0.002, -0.022), (0, -0.042, -0.022), size)


def crest_dorsal(g, p):
    """One continuous base and a row of rear-swept, tapered scale blades."""
    size = p["size"]
    count = round(p["spines"])
    span = 0.52
    step = span / count

    g.slot("detail")
    g.setup(voxel=size * min(0.0014, step / 10), detail=2.5, smooth=0.23)

    def rail_height(t):
        return -0.007 + 0.034 * sin(pi * t ** 1.35) - 0.020 * (1 - t) ** 2

    rail = [i / 10 for i in range(11)]
    g.loft([V(0, rail_height(t), (t - 1) * span) * size for t in rail],
           [(size * (0.003 + 0.010 * t), size * (0.003 + 0.009 * t)) for t in rail],
           sides=16, up=UP, density=3)

    tail_fraction = 1 - 0.965 * p["falloff"] ** 0.22
    for i in range(count):
        t = (i + 0.5) / count
        root_y, root_z = rail_height(t), (t - 1) * span
        height = 0.154 * lerp(tail_fraction, 1, t ** 1.5)
        height *= 0.66 + 0.34 * min(1, 30 / count)
        sweep = (0.21 * height + 0.24 * step)
        width = min(step * 0.49, 0.025)
        thickness = (0.0037 + 0.0067 * t) * min(1, (40 / count) ** 0.5)
        levels = (-0.025, 0.12, 0.38, 0.63, 0.83, 1.0)
        widths = (1.0, 0.94, 0.74, 0.51, 0.24, 0.08)
        sections = [V(0, root_y + height * h, root_z - sweep * max(0, h) ** 2.6) * size for h in levels]
        radii = [(size * max(0.0011, width * w), size * max(0.0009, thickness * w ** 0.8)) for w in widths]
        g.loft(sections, radii, sides=12, up=RIGHT, density=2)


def dewlap(g, p):
    """Pendant throat membrane with shallow folds running from the upper seam."""
    size = p["size"]
    reach = sin(p["extend_deg"] * pi / 180)
    depth = p["depth"]
    span = 0.34 * (1 + 0.19 * reach)
    angles = _angles(40)
    rings = []
    for i in range(1, 38):
        t = i / 38
        seam = -0.074 * (1 - t ** 1.45)
        drop = 0.164 * depth * sin(pi * t ** 1.36) ** 1.35 * (1 + 0.38 * reach)
        drop += 0.014 * sin(pi * t) + 0.004
        z = (t - 1) * span
        ring = []
        for angle in angles:
            down = (1 - cos(angle)) / 2
            width = (0.005 + 0.016 * sin(pi * t) ** 0.8) * sin(angle)
            fold = 1 + 0.19 * (1 - reach * 0.7) * sin(2 * pi * (6 * t + 1.3 * down ** 0.7))
            root_bead = 0.003 * exp(-((down - 0.08) / 0.08) ** 2)
            ring.append((width * fold + root_bead * sin(angle), seam - down * drop,
                         z + 0.055 * down * reach * sin(pi * t)))
        rings.append(ring)

    g.setup(voxel=size * 0.0019, detail=1.8, smooth=0.52)
    _closed_sections(g, rings, (0, -0.077, -span), (0, -0.002, 0), size)


def vocal_sac(g, p):
    """Flattened throat pouch whose wrinkles stretch out as the sac inflates."""
    size = p["size"]
    inflate = p["inflate"]
    sections = (0.0, 0.04, 0.14, 0.29, 0.46, 0.65, 0.81, 0.92, 0.98, 1.0)
    shape = PchipInterpolator(sections, (0.025, 0.026, 0.044, 0.093, 0.124, 0.122, 0.104, 0.070, 0.035, 0.0))
    depth = 0.34 * (1 - 0.14 * inflate)
    angles = _angles(48)
    rings = []
    for i in range(39):
        t = i / 39
        width = float(shape(t)) * (1 + 0.25 * inflate * sin(pi * t))
        center_z = 0.018 * t + 0.049 * inflate * sin(pi * t) ** 1.2
        thickness = width * (0.22 + inflate * 0.77)
        ring = []
        for angle in angles:
            ripple = cos(12 * angle + 3.1 * t + sin(3 * angle) * 0.58)
            pleat = 1 + 0.29 * (1 - inflate) ** 2 * sin(pi * t) ** 0.72 * ripple
            ring.append((sin(angle) * width, 0.009 - t * depth,
                         center_z + cos(angle) * thickness * pleat))
        rings.append(ring)

    g.setup(detail=1.7, smooth=0.3)
    _closed_sections(g, rings, (0, 0.012, 0), (0, 0.009 - depth, 0.018), size)


def supraorbital_ridge(g, p):
    """Two curved orbital shelves with a fused or divided nasal bridge."""
    size = p["size"]
    split = p["split"]
    projection = p["overhang"]
    # (transverse distance, elevation, anterior reach, depth, height) per shelf.
    sections = ((0, -0.013, 0.015, 0.028, 0.025), (0.032, -0.009, 0.033, 0.036, 0.024),
                (0.087, 0.024, 0.042, 0.041, 0.028), (0.137, 0.030, 0.036, 0.039, 0.030),
                (0.177, 0.014, 0.022, 0.028, 0.027), (0.206, -0.019, 0.004, 0.016, 0.020),
                (0.216, -0.052, -0.008, 0.006, 0.006), (0.214, -0.061, -0.010, 0.0019, 0.0027))
    points, radii = [], []
    for i, (x, y, z, thick, tall) in enumerate(sections):
        t = i / (len(sections) - 1)
        x += (0.049 * (1 - t) ** 2 + 0.012 * t) * split
        z += 0.05 * (projection - 0.5) * sin(pi * (0.25 + 0.6 * t))
        points.append(V(x, y, z) * size)
        radii.append((size * tall, size * thick * (0.73 + projection * 0.54)))

    reflected = [V(-point.x, point.y, point.z) for point in points]
    g.setup(detail=1.65, smooth=0.44)
    if split:
        g.loft(points, radii, sides=24, up=BACK)
        g.loft(reflected, radii, sides=24, up=BACK)
    else:
        g.loft(reflected[:0:-1] + points, radii[:0:-1] + radii, sides=24, up=BACK)


BUILDERS = {
    "carapace": carapace,
    "crest_dorsal": crest_dorsal,
    "dewlap": dewlap,
    "vocal_sac": vocal_sac,
    "supraorbital_ridge": supraorbital_ridge,
}

OVERRIDES = {
    "carapace": {"orient": "surface", "hint": {"u": 0.62, "theta": 90.0}},
    "crest_dorsal": {"orient": "surface", "hint": {"u": 0.79, "theta": 90.0}},
    "dewlap": {"hint": {"u": 0.82, "theta": -90.0}},
    "vocal_sac": {"hint": {"u": 0.91, "theta": -90.0}},
    "supraorbital_ridge": {"hint": {"u": 0.94, "theta": 90.0}},
}
