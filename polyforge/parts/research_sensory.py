"""Research sensory sculpts in the local +Y-up, +Z-forward frame."""

import math

from ..kit import BACK, UP, V, lerp, rot, smoothstep, taper


def _loop_shell(g, loops, back, front):
    """Cap a set of counterclockwise loops ordered from the back to the front."""
    sides = len(loops[0])
    verts = [v for loop in loops for v in loop]
    rear_index = len(verts)
    front_index = rear_index + 1
    verts.extend((back, front))
    faces = []
    for j in range(sides):
        k = (j + 1) % sides
        faces.append((rear_index, k, j))
        for row in range(len(loops) - 1):
            a = row * sides
            b = a + sides
            faces.append((a + j, a + k, b + k, b + j))
        end = (len(loops) - 1) * sides
        faces.append((front_index, end + j, end + k))
    g._add(verts, faces)


def _loop_band(g, loops):
    """Close the cross section of a raised lip around an opening."""
    sides = len(loops[0])
    faces = []
    for row in range(len(loops)):
        a = row * sides
        b = (row + 1) % len(loops) * sides
        for j in range(sides):
            k = (j + 1) % sides
            faces.append((a + j, a + k, b + k, b + j))
    g._add([v for loop in loops for v in loop], faces)


def _angles(sides):
    return [math.tau * i / sides for i in range(sides)]


def _groove(x, y, path):
    """Blend a smoothly fading indentation along a variable-width curve."""
    depth = 0.0
    for (ax, ay, aw), (bx, by, bw) in zip(path, path[1:]):
        dx, dy = bx - ax, by - ay
        t = min(1.0, max(0.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        width = lerp(aw, bw, t)
        distance = math.hypot(x - (ax + t * dx), y - (ay + t * dy))
        depth = max(depth, 1 - smoothstep(0.0, width, distance))
    return depth


def eye_camera(g, p):
    s = p["size"]
    basis = rot(UP, math.radians(p["facing_deg"]))
    eye_depth = 0.063 + 0.030 * p["bulge"]
    eye_center = -0.021 + 0.013 * p["bulge"]
    eye_front = eye_center + eye_depth

    def point(x, y, z):
        return basis @ V(x, y, z) * s

    g.setup(finish="subsurf", slot_finish={"base": "sculpt"})
    g.slot("white")
    g.oval(point(0, -0.005, eye_center), (0.098 * s, 0.069 * s, eye_depth * s),
           basis, segs=18, rings=12)

    g.slot("base")
    _camera_lids(g, point, eye_center, eye_depth)

    g.slot("eye")
    iris = []
    pupil_width = 0.014 * p["slit"]
    for rx, ry, dz in (
        (0.043, 0.046, -0.021), (0.047, 0.050, -0.015),
        (0.046, 0.049, -0.009), (0.039, 0.044, -0.002),
        (0.025, 0.028, 0.005), (pupil_width + 0.0035, 0.0175, 0.010),
        (pupil_width, 0.014, 0.009), (pupil_width, 0.014, -0.003),
    ):
        iris.append([point(rx * math.cos(a), ry * math.sin(a) + 0.008, eye_front + dz)
                     for a in _angles(28)])
    _loop_band(g, iris)
    g.slot("black")
    g.oval(point(0, 0.008, eye_front + 0.0005),
           ((pupil_width + 0.001) * s, 0.0155 * s, 0.003 * s), basis, segs=14, rings=8)

    strength = p["sclerotic_ring"]
    if strength > 0.0:
        g.slot("horn")
        ring = []
        for i in range(17):
            a = math.pi * i / 16
            ring.append(point(0.098 * math.cos(a), 0.057 * math.sin(a),
                              0.029 + 0.030 * p["bulge"] - 0.025 * abs(math.cos(a))))
        g.loft(ring, [0.009 * strength * s] * len(ring), sides=10, density=1, up=BACK)


def _camera_lids(g, point, eye_center, eye_depth):
    """A continuous orbit with separate upper hood and lower lid profiles."""
    # Indices match across all rows. The upper and lower margins meet at
    # the canthi, and the inner two rows fold under the globe.
    profiles = (
        # span, upper arc, lower arc, globe relief, depth offset
        (0.103, 0.072, 0.057, 0.04, -0.034),
        (0.115, 0.090, 0.071, 0.29, -0.011),
        (0.114, 0.088, 0.069, 0.53,  0.009),
        (0.109, 0.075, 0.063, 0.74,  0.014),
        (0.105, 0.060, 0.057, 0.95,  0.010),
        (0.102, 0.052, 0.052, 1.00,  0.009),
        (0.100, 0.048, 0.049, 1.00,  0.005),
        (0.099, 0.048, 0.048, 1.00, -0.004),
        (0.099, 0.053, 0.051, 0.90, -0.017),
        (0.101, 0.065, 0.055, 0.42, -0.031),
    )
    loops = [[] for _ in profiles]
    for a in _angles(24):
        x, y = math.cos(a), math.sin(a)
        center_y = 0.002 + 0.0055 * x
        arc = y * (0.51 + 0.49 * abs(y) ** 0.55)
        margin_y = center_y + (0.048 if y >= 0 else 0.049) * arc
        radial = (0.096 * x / 0.098) ** 2 + ((margin_y + 0.005) / 0.069) ** 2
        globe = eye_depth * math.sqrt(max(0.014, 1 - radial))
        upper_fold = max(0.0, arc) * 0.009
        for loop, (width, upper, lower, relief, offset) in zip(loops, profiles):
            height = (upper if y >= 0 else lower) * arc
            hood = upper_fold if 0.35 < relief < 0.90 and offset > 0 else 0.0
            loop.append(point(width * x, center_y + height, eye_center + relief * globe + offset + hood))
    _loop_band(g, loops)


def eye_compound(g, p):
    s = p["size"]
    rx, ry = 0.078, 0.104
    depth = 0.029 + p["bulge"] * 0.062
    tilt = rot(UP, math.radians(18)) @ rot(BACK, math.radians(-26))

    def point(x, y, z):
        return tilt @ V(x, y, z) * s

    g.setup(finish="subsurf_low")
    g.oval(point(0, 0, -0.012), ((rx + 0.004) * s, (ry + 0.004) * s, 0.034 * s),
           tilt, segs=32, rings=16)
    g.oval(point(0, 0, -0.002), (rx * s, ry * s, depth * s), tilt, segs=32, rings=20)

    # Sample each facet on the same ellipsoidal surface, with its buried
    # rim overlapping the dome so the grooves are blind and the cage is closed.
    radius = 0.00875
    step_y = math.sqrt(3) * radius

    def dome(x, y):
        return -0.002 + depth * math.sqrt(max(0.01, 1 - (x / rx) ** 2 - (y / ry) ** 2))

    for col in range(-6, 7):
        for row in range(-7, 8):
            x = col * radius * 1.5
            y = (row + 0.5 * (col % 2)) * step_y
            if (x / rx) ** 2 + (y / ry) ** 2 > 0.81:
                continue

            loops = []
            for scale, lift in ((0.97, -0.009), (0.87, 0.0015), (0.79, 0.0048), (0.44, 0.0054)):
                loop = []
                for a in _angles(6):
                    xx = x + scale * radius * math.cos(a)
                    yy = y + scale * radius * math.sin(a)
                    loop.append(point(xx, yy, dome(xx, yy) + lift))
                loops.append(loop)
            height = dome(x, y)
            _loop_shell(g, loops, point(x, y, height - 0.010), point(x, y, height + 0.0055))


def eye_simple(g, p):
    s = p["size"]
    count = round(p["cluster"])
    basis = rot(UP, math.radians(19))
    radius = 0.056 / (1 + 0.10 * (count - 1))
    centres = [((i - (count - 1) * 0.5) * radius * 1.72,
                radius * (1 - 0.20 * i / max(1, count - 1))) for i in range(count)]
    width = abs(centres[0][0]) + radius * 1.4
    g.setup(finish="subsurf")
    outlines = []
    for scale, z in ((0.45, -0.032), (0.88, -0.024), (1.0, -0.007), (0.91, 0.021), (0.51, 0.029)):
        outline = []
        for a in _angles(28):
            x = width * math.cos(a)
            scallop = max(r * math.sqrt(max(0.0, 1 - ((x - cx) / (1.44 * r)) ** 2))
                          for cx, r in centres)
            sin_a = math.sin(a)
            y = math.copysign(max(scallop * 1.25, radius * 0.47 * abs(sin_a)), sin_a)
            y *= min(1.0, abs(sin_a) * 8)
            outline.append(basis @ V(x * scale, y * scale, z) * s)
        outlines.append(outline)
    _loop_shell(g, outlines, basis @ V(0, 0, -0.036 * s), basis @ V(0, 0, 0.032 * s))
    g.slot("dark")
    for x, r in centres:
        g.oval(basis @ V(x, -0.01 * x / width, 0.011) * s, (r * s, r * 1.06 * s, r * 0.77 * s),
               basis, segs=14, rings=9)


def eye_stalked(g, p):
    s = p["size"]
    extension = 1 - p["retract"] * 0.85
    height = (0.082 + 0.200 * p["stalk"]) * extension
    head = V(0.126 * extension, height, 0.064 + 0.026 * p["retract"])
    g.setup(voxel=0.00165 * s, detail=2.4, smooth=0.38)
    g.oval(V(0, 0.004, 0.007) * s, V(0.047, 0.035, 0.040) * s)
    g.loft([V(0, 0.004, 0.007) * s, V(head.x * 0.23, height * 0.40, 0.025) * s,
            (head + V(-0.031, -0.032, -0.010)) * s, head * s],
           [r * s for r in (0.032, 0.025, 0.023, 0.034)], sides=18, up=BACK)

    axis = V(1.52, 0.31, 1).normalized()
    basis = BACK.rotation_difference(axis).to_matrix()

    def point(x, y, z):
        return (head + basis @ V(x, y, z)) * s

    loops = []
    for r, z in (
        (0.024, -0.067), (0.044, -0.053), (0.053, -0.032), (0.054, -0.019),
        (0.051, -0.015), (0.056, -0.010), (0.057, 0.005), (0.054, 0.020),
        (0.050, 0.024), (0.052, 0.030), (0.047, 0.045), (0.034, 0.057),
        (0.018, 0.060), (0.014, 0.055), (0.012, 0.043),
    ):
        loops.append([point(r * math.cos(a), r * 1.07 * math.sin(a), z) for a in _angles(28)])
    _loop_shell(g, loops, point(0, 0, -0.073), point(0, 0, 0.041))


def antenna_segmented(g, p):
    s = p["size"]
    count = round(p["segments"])
    elbow = math.radians(p["elbow_deg"])
    g.setup(voxel=0.00105 * s, detail=2.3, smooth=0.31)

    path = [V(0, 0, -0.019)]
    for i in range(140):
        t = (i + 0.5) / 140
        angle = math.radians(2 + 85 * t ** 0.85) + elbow * smoothstep(0.20, 0.32, t)
        tangent = V(math.sin(angle), math.cos(angle), 0.30 - t * 0.19).normalized()
        path.append(path[-1] + tangent * (0.407 / 140))

    def at(t):
        step = t * 140
        i = min(int(step), 139)
        return path[i].lerp(path[i + 1], step - i)

    points, radii = [], []
    section = ((0.0, 0.7), (0.12, 0.92), (0.35, 1.0), (0.69, 0.97), (0.89, 0.88))
    for i in range(count):
        for fraction, profile in section:
            t = (i + fraction) / count
            points.append(at(t) * s)
            radii.append((0.029 * (1 - t) ** 1.14 + 0.0025) * profile * s)
    points.append(path[-1] * s)
    radii.append(0.0018 * s)
    g.oval(V(0, 0.001, -0.013) * s, V(0.030, 0.024, 0.029) * s)
    g.loft(points, radii, sides=16, density=1, up=BACK)

    club = p["club"]
    if club > 0.0:
        end = at(0.95)
        direction = (at(1.0) - at(0.89)).normalized()
        across = direction.cross(BACK).normalized()
        for i in range(4):
            a = (i - 1.5) * 0.23
            reach = (direction * math.cos(a) + across * math.sin(a)) * (0.064 * club)
            tip = end + reach + BACK * (0.009 * i * club)
            g.loft([end * s, (end + reach * 0.47) * s, tip * s],
                   [r * club * s for r in (0.006, 0.008, 0.002)], sides=12, density=3, up=BACK)


def ear_pinna(g, p):
    s = p["size"]
    point, cup, flat = p["point"], p["cup"], p["flat"]
    rounded = [
        (-0.044, -0.012), (-0.070, 0.019), (-0.084, 0.068), (-0.074, 0.121),
        (-0.051, 0.167), (-0.010, 0.195), (0.039, 0.191), (0.079, 0.157),
        (0.087, 0.111), (0.074, 0.064), (0.046, 0.029), (0.035, -0.009),
    ]
    pointed = [
        (-0.048, -0.013), (-0.075, 0.021), (-0.080, 0.071), (-0.063, 0.127),
        (-0.023, 0.177), (0.038, 0.232), (0.090, 0.270), (0.101, 0.235),
        (0.087, 0.160), (0.085, 0.093), (0.046, 0.039), (0.035, -0.010),
    ]
    outline = [V(lerp(x, xx, point), lerp(y, yy, point) * (1 - 0.24 * flat), 0)
               for (x, y), (xx, yy) in zip(rounded, pointed)][::-1]
    center = V(0.002, (0.079 + 0.016 * point) * (1 - 0.24 * flat), 0)
    depth = (1 - flat * 0.65)

    def form(v, z):
        return V(v.x, v.y, (z - 0.15 * v.y + 0.13 * v.x) * depth) * s

    loops = []
    for scale, z in ((0.42, -0.057), (0.86, -0.042), (0.99, -0.019),
                     (1.0, 0.012), (0.92, 0.037), (0.72, 0.037),
                     (0.59, 0.028 - 0.041 * cup), (0.31, 0.021 - 0.059 * cup)):
        loops.append([form(center.lerp(v, scale), z) for v in outline])
    g.setup(finish="subsurf")
    _loop_shell(g, loops, form(center, -0.060), form(center, 0.020 - 0.063 * cup))
    fold = [V(-0.031, 0.018, 0), V(-0.023, 0.046, 0),
            V(0.010, 0.067, 0), V(0.050, 0.073, 0)]
    g.loft([form(v, 0.033 - 0.043 * cup) for v in fold], [r * s for r in (0.009, 0.014, 0.012, 0.005)],
           sides=10, density=2, up=BACK)


def tympanum(g, p):
    s = p["size"]
    rim, recess = p["rim"], p["recess"]
    loops = []
    for scale, depth in (
        (0.37, -0.032), (0.84, -0.027), (0.99, -0.008), (1.0, 0.008),
        (0.94, 0.013 + 0.028 * rim), (0.84, 0.014 + 0.028 * rim),
        (0.73, 0.012 - 0.010 * recess), (0.53, 0.010 - 0.020 * recess),
        (0.24, 0.011 - 0.026 * recess),
    ):
        loop = []
        for a in _angles(36):
            irregular = 1 + 0.027 * math.cos(5 * a) + 0.018 * math.sin(8 * a)
            r = 0.094 * scale * irregular
            loop.append(V(r * math.cos(a), r * 0.95 * math.sin(a),
                          depth + 0.0035 * math.sin(3 * a) * scale) * s)
        loops.append(loop)
    g.setup(finish="subsurf")
    _loop_shell(g, loops, V(0, 0, -0.034 * s), V(0, 0, (0.012 - 0.029 * recess) * s))


def nose_pad(g, p):
    s = p["size"]
    projection = 0.026 + 0.081 * p["projection"]
    # The rear surface straddles the attachment origin. Both nares are
    # inset patches of the front grid with their own rim and throat loops.
    stations = (
        # height, half-width, projection
        (-0.074, 0.016, 0.32), (-0.066, 0.033, 0.51),
        (-0.049, 0.056, 0.67), (-0.025, 0.081, 0.88),
        ( 0.001, 0.105, 1.00), ( 0.030, 0.116, 0.97),
        ( 0.053, 0.107, 0.83), ( 0.071, 0.074, 0.60),
        ( 0.075, 0.039, 0.42),
    )
    columns = (-1, -0.86, -0.59, -0.39, -0.19, 0, 0.19, 0.39, 0.59, 0.86, 1)
    cavity_row = (2, 5)
    cavity_cols = ((1, 4), (6, 9))
    verts, faces = [], []

    def vertex(x, y, z):
        verts.append(V(x, y, z) * s)
        return len(verts) - 1

    def surface(x, y, width, peak):
        return 0.009 + y * 0.065 + projection * peak * (1 - 0.77 * (x / width) ** 2)

    def front_height(x, y):
        for (lo, wa, ha), (hi, wb, hb) in zip(stations, stations[1:]):
            if lo <= y <= hi:
                t = (y - lo) / (hi - lo)
                return surface(x, y, lerp(wa, wb, t), lerp(ha, hb, t))
        raise ValueError("Nostril control outside the nose surface")

    def bridge(a, b):
        for i in range(len(a)):
            j = (i + 1) % len(a)
            faces.append((a[i], a[j], b[j], b[i]))

    front, back = [], []
    for row, (y, width, crest) in enumerate(stations):
        front.append([])
        back.append([])
        for col, u in enumerate(columns):
            x = width * u
            interior = cavity_row[0] < row < cavity_row[1] and any(a < col < b for a, b in cavity_cols)
            front[row].append(None if interior else vertex(x, y, surface(x, y, width, crest)))
            depth = -0.048 + 0.016 * u ** 2 + 0.020 * (abs(y) / 0.075) ** 2
            back[row].append(vertex(0.89 * x, 0.90 * y, depth))

    def perimeter(rows, y0, y1, x0, x1):
        return [*rows[y0][x0:x1 + 1], *(rows[j][x1] for j in range(y0 + 1, y1 + 1)),
                *(rows[y1][i] for i in range(x1 - 1, x0 - 1, -1)),
                *(rows[j][x0] for j in range(y1 - 1, y0, -1))]

    for j in range(len(stations) - 1):
        for i in range(len(columns) - 1):
            faces.append((back[j][i], back[j + 1][i], back[j + 1][i + 1], back[j][i + 1]))
            if cavity_row[0] <= j < cavity_row[1] and any(a <= i < b for a, b in cavity_cols):
                continue
            faces.append((front[j][i], front[j][i + 1], front[j + 1][i + 1], front[j + 1][i]))

    bounds = (0, len(stations) - 1, 0, len(columns) - 1)
    previous = perimeter(back, *bounds)
    outer = perimeter(front, *bounds)
    for x_scale, y_scale, z in ((0.99, 0.98, -0.020), (1.02, 1.02, 0.001)):
        ring = []
        for index in outer:
            x, y, _ = verts[index] / s
            ring.append(vertex(x * x_scale, y * y_scale, z + 0.085 * y))
        bridge(previous, ring)
        previous = ring
    bridge(previous, outer)

    opening = (
        (0.029, -0.037), (0.037, -0.039), (0.046, -0.034), (0.055, -0.026),
        (0.069, -0.017), (0.081, -0.005), (0.086,  0.008),
        (0.080,  0.017), (0.066,  0.016), (0.054,  0.009),
        (0.041, -0.003), (0.034, -0.020),
    )
    floor_depth = 0.022 + 0.17 * projection - 0.008 * (1 - smoothstep(0.026, 0.0665, projection))
    for side in (-1, 1):
        previous = perimeter(front, *cavity_row, *cavity_cols[1])
        if side < 0:
            # Mirror the right patch cells before reversing their winding.
            previous = perimeter(front, *cavity_row, *cavity_cols[0])
            previous = [previous[(3 - i) % len(previous)] for i in range(len(previous))]
        for scale, offset, depth in ((1.15, 0.0, 0.002), (1.0, 0.0, 0.002),
                                     (0.88, 0.002, -0.31 * floor_depth),
                                     (0.63, 0.005, -0.73 * floor_depth),
                                     (0.33, 0.008, -floor_depth)):
            ring = []
            for x, y in opening:
                x = lerp(0.056, x, scale) + offset
                y = lerp(-0.010, y, scale)
                ring.append(vertex(side * x, y, front_height(x, y) + depth))
            if side > 0:
                bridge(previous, ring)
            else:
                bridge(previous[::-1], ring[::-1])
            previous = ring
        faces.append(tuple(previous if side > 0 else previous[::-1]))

    g.setup(finish="sculpt")
    g.slot("dark")
    g._add(verts, faces)


def nostril_slit(g, p):
    s = p["size"]
    flap = p["flap"]
    outline = []
    for a in _angles(72):
        cos_a = math.cos(a)
        outline.append((0.126 * cos_a, 0.046 * (1 + 0.26 * cos_a) * math.sin(a) + 0.021 * cos_a))

    path = [(-0.105, -0.026, 0.002), (-0.074, -0.022, 0.007), (-0.021, -0.005, 0.010),
            (0.026, 0.013, 0.011), (0.070, 0.020, 0.012), (0.096, 0.011, 0.003)]
    slit = [(x, y, r * (1 + 0.38 * flap)) for x, y, r in path]
    lip = [(x, y + 0.015, r * 1.7) for x, y, r in path]
    loops = [[V(x * scale, y * scale, depth + x * 0.048) * s for x, y in outline]
             for scale, depth in ((0.44, -0.032), (0.79, -0.026), (0.98, -0.009), (1.0, 0.004))]

    def depth(x, y, scale):
        crest = 0.004 + 0.048 * math.sqrt(1 - scale ** 2)
        cavity = _groove(x, y, slit) * (0.023 + 0.009 * flap)
        ridge = _groove(x, y, lip) * (0.004 + 0.012 * flap)
        return crest + x * 0.048 + (ridge - cavity) * min(1.0, (1 - scale) * 30)

    for i in range(1, 33):
        scale = math.cos(math.pi * i / 66)
        loops.append([V(x * scale, y * scale, depth(x * scale, y * scale, scale)) * s for x, y in outline])
    g.setup(voxel=0.00125 * s, detail=1.90, smooth=0.37)
    _loop_shell(g, loops, V(0, 0, -0.035 * s), V(0, 0, depth(0, 0, 0) * s))


def whiskers(g, p):
    s = p["size"]
    count = round(p["count"])
    spread = math.radians(p["spread_deg"])
    droop = p["droop"]
    g.setup(voxel=0.00145 * s, detail=1.45, smooth=0.42, slot_finish={"detail": "subsurf"})
    g.oval(V(0, 0, -0.008) * s, (0.037 * s, 0.070 * s, 0.037 * s))
    roots = []
    for i in range(count):
        t = i / (count - 1)
        root = V(0.017, lerp(-0.053, 0.053, t), 0.021 - 0.010 * abs(2 * t - 1))
        roots.append(root)
        r = 0.007 - 0.002 * abs(2 * t - 1)
        g.oval(root * s, (r * 1.5 * s, r * s, r * s), segs=12, rings=8)

    g.slot("detail")
    for i, root in enumerate(roots):
        t = i / (count - 1)
        angle = (t - 0.48) * spread * 0.62
        length = 0.246 + 0.084 * (1 - abs(2 * t - 1))
        points = []
        for u in (0.0, 0.26, 0.51, 0.76, 1.0):
            points.append((root + V(
                length * u * math.cos(angle),
                length * u * math.sin(angle) + 0.068 * u * (1 - u) - (0.008 + 0.035 * droop) * u ** 3,
                0.091 * u - 0.027 * u ** 2,
            )) * s)
        g.loft(points, taper(0.0049 * s, 0.00065 * s, 5, power=0.82), sides=8, density=1, up=BACK)


def pectines(g, p):
    s = p["size"]
    teeth = round(p["teeth"])
    basis = rot(UP, math.radians(20 - p["splay_deg"]))
    l = 0.239

    def point(x, y, z):
        return basis @ V(x, y, z) * s

    def spine(t):
        return V(l * t, -0.016 * math.sin(math.pi * t) + 0.029 * t, 0.026 + 0.016 * t)

    g.setup(finish="subsurf")
    g.oval(point(0, 0, 0.022), V(0.033, 0.027, 0.029) * s, basis, segs=16, rings=10)
    g.loft([point(*spine(t)) for t in (0, 0.22, 0.48, 0.75, 0.92, 1.0)],
           [(r * s, r * 0.82 * s) for r in (0.022, 0.017, 0.014, 0.012, 0.009, 0.003)],
           sides=14, density=2, up=BACK)
    for i in range(teeth):
        t = lerp(0.062, 0.97, i / (teeth - 1))
        root = spine(t) + V(0, -0.009, -0.003)
        length = 0.064 - 0.039 * t + 0.014 * math.sin(math.pi * t)
        radius = min(0.012, l / teeth * 0.51) * (1 - 0.25 * t)
        offsets = [V(0, 0, 0), V(0.10, -0.37, -0.10), V(0.27, -0.74, -0.22), V(0.56, -0.96, -0.33)]
        g.loft([point(*(root + v * length)) for v in offsets],
               [r * radius * s for r in (1.0, 0.89, 0.64, 0.15)], sides=8, density=1, up=BACK)


BUILDERS = {
    "eye_camera": eye_camera,
    "eye_compound": eye_compound,
    "eye_simple": eye_simple,
    "eye_stalked": eye_stalked,
    "antenna_segmented": antenna_segmented,
    "ear_pinna": ear_pinna,
    "tympanum": tympanum,
    "nose_pad": nose_pad,
    "nostril_slit": nostril_slit,
    "whiskers": whiskers,
    "pectines": pectines,
}

OVERRIDES = {
    "antenna_segmented": {"topology_changes": ("club",)},
    "eye_camera": {"orient": "native", "hint": {"u": 0.955, "theta": 28.0}},
    "ear_pinna": {"orient": "native", "hint": {"u": 0.90, "theta": 63.0}},
    "nose_pad": {"hint": {"u": 0.99, "theta": -90.0}},
    "nostril_slit": {"hint": {"u": 0.973, "theta": -68.0}},
    "whiskers": {"hint": {"u": 0.948, "theta": 8.0}},
    "pectines": {"hint": {"u": 0.60, "theta": -79.0}},
}
