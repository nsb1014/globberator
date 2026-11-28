"""Local polygonal armor, projecting scutes and a flyingfish pectoral blade."""

from math import cos, pi, radians, sin, sqrt, tau

from scipy.interpolate import PchipInterpolator

from ..kit import V, lerp, smoothstep
from . import Part
from .research_locomotion import _closed_rings


_BOX_PROFILE = PchipInterpolator((0., .15, .28, .39, .61, .77, .86, 1.), (
    (-.021, .040), (.002, .040), (.021, .038), (.038, .027), (.044, .003),
    (.044, -.028), (.036, -.038), (.013, -.042),
))
_BOX_NORMAL_DERIVATIVE = _BOX_PROFILE.derivative()


def _polygonal_seam(u, z):
    """Approximate hexagonal tile relief from the nearest staggered column."""
    pitch = .014
    spacing = sqrt(3) * pitch / 2
    col = round(u / spacing)
    dx, dz = min(((u - i * spacing, z - pitch * (round(z / pitch - .5 * (i % 2)) + .5 * (i % 2)))
                  for i in range(col - 1, col + 2)),
                 key=lambda pair: pair[0]**2 + pair[1]**2)
    dist = max(abs(dz), abs(.5 * dz + sqrt(3) / 2 * dx), abs(.5 * dz - sqrt(3) / 2 * dx))
    serration = .00027 * sin(tau * 370 * dx) * sin(tau * 390 * dz)
    return 1 - smoothstep(.0048 + serration, .00725 + serration, dist)


def fused_polygonal_trunk_armor(g, p):
    """A continuous shell coupon around a dorsal fin opening and two corners."""
    size, armor = p["size"], p["thickness"]
    g.setup(finish="direct")
    centers = (.025, -.017)
    u_span = .148
    count = 128
    rings = []
    steps = 36
    for outer, levels in ((True, range(steps + 1)), (False, range(steps, -1, -1))):
        for index in levels:
            t = index / steps
            ring = []
            for j in range(count):
                angle = tau * j / count
                a, b = cos(angle), sin(angle)
                u_limit = (u_span - centers[0]) if a > 0 else centers[0]
                z_limit = (.057 - centers[1]) if b > 0 else (.047 + centers[1])
                ray_limit = min(u_limit / max(abs(a), 1e-6), z_limit / max(abs(b), 1e-6))
                u_hole, z_hole = .011, .019
                hole_limit = 1 / sqrt((a / u_hole)**2 + (b / z_hole)**2)
                radius = lerp(hole_limit, ray_limit, t)
                u, z = centers[0] + a * radius, centers[1] + b * radius
                fraction = min(1., max(0., u / u_span))
                x, y = _BOX_PROFILE(fraction)
                dx, dy = _BOX_NORMAL_DERIVATIVE(fraction)
                normal = V(-dy, dx, 0).normalized()
                # Seams cross the bends in the same sheet. They are weakened
                # at the aperture lip, which remains a smooth open edge.
                relief = .0018 * (_polygonal_seam(u, z) - .50) * smoothstep(0., .15, t)
                depth = relief if outer else -.0036 * armor
                longitudinal = 1 - .08 * (z / .057)**2
                surface = V(x * longitudinal, y * longitudinal, z)
                ring.append((surface + normal * depth) * size)
            rings.append(ring)

    verts = [vertex for ring in rings for vertex in ring]
    faces = []
    for i in range(len(rings)):
        n = (i + 1) % len(rings)
        for j in range(count):
            k = (j + 1) % count
            faces.append((i * count + j, n * count + j, n * count + k, i * count + k))
    volume = 0.
    for a, b, c, d in faces:
        volume += verts[a].dot(verts[b].cross(verts[c]) + verts[c].cross(verts[d]))
    if volume < 0:
        faces = [tuple(reversed(face)) for face in faces]
    g.current._add(verts, faces)


def five_row_bossed_scutes(g, p):
    """Three isolated osteoderms in each of five row-specific local frames."""
    size, boss = p["size"], p["boss"]
    g.setup(finish="direct")
    rows = (
        (V(0, .038, 0), V(0, 1, 0), .016, .013, .012, .000),
        (V(.046, .011, 0), V(1, .18, 0), .012, .011, .007, .005),
        (V(-.046, .011, 0), V(-1, .18, 0), .012, .011, .007, .005),
        (V(.029, -.031, 0), V(.68, -.75, 0), .013, .014, .008, -.006),
        (V(-.029, -.031, 0), V(-.68, -.75, 0), .013, .014, .008, -.006),
    )
    for row_center, direction, width, length, height, shift in rows:
        normal = direction.normalized()
        across = V(0, 0, 1).cross(normal)
        for index in range(3):
            falloff = 1 - .09 * index
            base = row_center * (1 - .055 * index) + V(0, 0, .038 + shift - .038 * index)
            rings = []
            for level, depth in ((.08, -.0027), (.68, -.0026), (.94, -.0018), (1., -.0001),
                                 (.95, .0012), (.82, .0020), (.68, .0032), (.53, .0047),
                                 (.39, .0065), (.23, .0083), (.08, .0100)):
                ring = []
                transition = 1 - level
                for j in range(26):
                    a = tau * j / 26
                    c, s = cos(a), sin(a)
                    petal = 1 - .11 * cos(4 * a)
                    edge = V(0, 0, length * c) + across * (width * s * (1 - .22 * abs(c)))
                    ridge = .0021 * sin(pi * level) * abs(c)**3 if depth > 0 else 0.
                    pits = .00043 * sin(pi * level) * cos(9 * a + level * 27) if depth > 0 else 0.
                    y = (depth + ridge + pits) * height / .010 * boss
                    tip_sweep = -.009 * transition**2 if depth > 0 else 0.
                    ring.append((base + falloff * (edge * (level * petal) + normal * y
                                                   + V(0, 0, tip_sweep))) * size)
                rings.append(ring)
            _closed_rings(g, rings)


_FLYING_FIN_REACH = PchipInterpolator((0., .10, .22, .38, .56, .72, .88, 1.),
                                       (.152, .186, .183, .158, .125, .089, .053, .022))


def deployable_ray_fan_wing(g, p):
    """One elongate fin with sixteen ray bands spreading from a compact base."""
    size, spread = p["size"], p["spread"]
    g.setup(finish="direct")
    rings = []
    for i in range(97):
        t = i / 96
        root = V(-.003 + .004 * t, -.001, .007 - .019 * t)
        angle = radians(9 + 53 * spread) * (1 - t)
        reach = _FLYING_FIN_REACH(t)
        ridge = (.5 + .5 * cos(tau * 15 * t))**3
        ring = []
        for j in range(28):
            a = tau * j / 28
            u = .5 + .5 * cos(a)
            travel = reach * u
            x = root.x + travel * sin(angle)
            z = root.z - travel * cos(angle)
            y = root.y + (.007 + .009 * spread) * sin(pi * t) * u * (1 - .45 * u)
            thickness = .00023 + .00165 * (1 - u)**3 + .00056 * ridge * sin(pi * u)
            ring.append(V(x, y + thickness * sin(a), z) * size)
        rings.append(ring)
    _closed_rings(g, rings)


_SIZE = {"size": (.6, 1.6, 1.)}
PARTS = [
    Part("fused_polygonal_trunk_armor", "aesthetics",
         "Rigid boxfish shell coupon with polygonal sutures, two corners and an open fin seat.",
         ["boxfish", "carapace", "suture", "polygonal", "fin opening"],
         {**_SIZE, "thickness": (.65, 1.5, 1.)}, fused_polygonal_trunk_armor,
         orient="native", symmetry="center", hint={"u": .55, "theta": 0.}),
    Part("five_row_bossed_scutes", "aesthetics",
         "Fifteen projecting osteoderms in one dorsal, two lateral and two ventrolateral rows.",
         ["sturgeon", "scute", "dorsal", "ventrolateral", "armor"],
         {**_SIZE, "boss": (.6, 1.4, 1.)}, five_row_bossed_scutes,
         orient="native", symmetry="center", hint={"u": .55, "theta": 0.}),
    Part("deployable_ray_fan_wing", "locomotion",
         "Elongated flyingfish pectoral fan with a compact root and adjustable spread.",
         ["flyingfish", "pectoral", "glide", "rayed", "fan"],
         {**_SIZE, "spread": (0., 1., .88)}, deployable_ray_fan_wing,
         orient="native", symmetry="pair", mirror=True, hint={"u": .66, "theta": 0.}),
]
