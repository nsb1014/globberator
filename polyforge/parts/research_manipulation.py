"""Manipulation parts sculpted from the research library clay studies.

Whole limbs share anatomical landmarks between their mesh and rig presets.
The unreflected hand is the creature's anatomical left (+X).
"""
import math

from mathutils import Matrix

from ..kit import UP, V, lerp, rot

FORWARD = V(0, 0, 1)
LATERAL = V(1, 0, 0)


def _loft(g, scale, points, radii, **kwargs):
    scaled = [r * scale if isinstance(r, (int, float)) else tuple(v * scale for v in r) for r in radii]
    g.loft([V(p) * scale for p in points], scaled, **kwargs)


def _oval(g, scale, point, radii, **kwargs):
    g.oval(V(point) * scale, tuple(r * scale for r in radii), **kwargs)


def _preset(p, points, radii, motion="auto"):
    scale = p.get("size", 1.0)
    return {
        "segments": [list((b - a) * scale) for a, b in zip(points, points[1:])],
        "radii": [r * scale for r in radii],
        "motion": motion,
    }


def _pincer_joints():
    return [
        V(0, 0, 0),
        V(.133, .074, .008),
        V(.279, -.033, .020),
        V(.377, -.006, .040),
        V(.518, .008, .073),
    ]


def pincer_limb(g, p):
    s = p.get("size", 1.0)
    side = -1.0 if p.get("_mirrored", False) else 1.0
    bulk = p["claw_bulk"] / 1.2 * (1 + side * .24 * p["asymmetry"])
    root, elbow, wrist, palm, end = _pincer_joints()
    g.setup(voxel=.0024 * s, detail=2.0, smooth=.32)
    g.slot("base")
    _loft(g, s, [root - V(.025, .014, 0), root, root + V(.027, .012, 0)],
          [(0.037, .048), (.044, .053), (.038, .047)], sides=24)
    for a, b, radius in ((root, elbow, .035), (elbow, wrist, .039), (wrist, palm, .030)):
        points = [a.lerp(b, t) for t in (.05, .18, .52, .80, .93)]
        _loft(g, s, points, [radius * k for k in (.77, 1.04, .97, .9, .86)], sides=22)
    for joint, radii in ((elbow, (.028, .037, .042)), (wrist, (.029, .037, .039)), (palm, (.033, .051, .045))):
        g.slot("detail")
        _oval(g, s, joint, radii, segs=22, rings=12)

    spread = .65 + .35 * bulk
    g.slot("accent")
    _loft(g, s, [
        palm - V(.013, 0, 0), palm + V(.056, .012, .012), end,
        end + V(.063, .010, .005),
    ], [(w * bulk, h * spread) for w, h in ((.040, .049), (.074, .097), (.073, .104), (.052, .073))],
        sides=30, density=6)
    _loft(g, s, [end + V(x, y * spread, z) for x, y, z in (
        (.005, .046, .002), (.087, .063, -.001), (.151, .057, -.004),
        (.205, .034, -.006), (.236, -.008, -.004),
    )], [(w * bulk, h * spread) for w, h in ((.062, .057), (.057, .049), (.038, .032), (.021, .017), (.003, .003))],
        sides=24)
    for x, y, z, radius in ((.095, .023, .003, .018), (.136, .026, .005, .012)):
        _oval(g, s, end + V(x, y * spread, z), (radius, radius * spread, radius * bulk), segs=14, rings=10)

    joint = end + V(.040, -.050 * spread, .019)
    g.pivots["jaw"] = joint * s
    g.use("jaw")
    g.setup(voxel=.0017 * s, detail=1.1, smooth=.35)
    g.slot("claw")
    _loft(g, s, [joint + V(x, y * spread, z) for x, y, z in (
        (-.023, .006, 0), (.024, -.026, 0), (.080, -.043, -.013),
        (.136, -.032, -.018), (.176, -.005, -.020), (.195, .021, -.020),
    )], [(w * bulk, h * spread) for w, h in ((.049, .045), (.051, .048), (.040, .036), (.027, .024), (.015, .013), (.0024, .0024))],
        sides=24)
    g.use("self")


def _pincer_preset(p):
    return _preset(p, _pincer_joints(), (.045, .037, .034, .044, .071))


def _grasping_joints(knuckle):
    return [V(0, 0, 0), V(.057, -.285, .058), V(.291, -.359, .141),
            V(.375, -.364 - .038 * knuckle, .163)]


def _grasping_hand(g, scale, wrist, axis, digits, knuckle):
    """Pronated left hand, with a broad metacarpal arch and palmar thumb opposition."""
    radial = axis.cross(UP).normalized()
    dorsal = radial.cross(axis)
    basis = Matrix((axis, dorsal, radial)).transposed()

    def hand(point):
        return wrist + basis @ V(point)

    # Omit the pinky in the four-digit form and bring in the ulnar palm edge.
    ulnar = .013 * (5 - digits)
    profile = (
        (-.020, .000, .000, .027, .024),
        (.008, .000, .000, .032, .024),
        (.034, .001, .001, .044, .025),
        (.065, .003, .001, .053, .023),
        (.087, .004, -.001, .057, .021),
        (.105, .003, .003, .052, .018),
        (.117, .002, .008, .036, .013),
    )
    _loft(g, scale,
          [hand((x, y, z + ulnar * .5 * max(x, 0) / .117)) for x, y, z, _, _ in profile],
          [(width - ulnar * .5 * max(x, 0) / .117, depth) for x, _, _, width, depth in profile],
          sides=30, up=dorsal, exponent=.81, density=5)

    # Thenar and hypothenar pads leave the center of the palm shallower.
    _oval(g, scale, hand((.047, -.014, .030)), (.034, .018, .023), basis=basis)
    _oval(g, scale, hand((.050, -.012, -.033 + ulnar)), (.034, .015, .018), basis=basis)

    # Lengths, splay and resting flexion progress from index to pinky.
    fingers = (
        (.104, .046, .088, .0130, .125, .13),
        (.111, .011, .101, .0135, .045, .19),
        (.103, -.021, .091, .0120, -.060, .25),
        (.088, -.050, .074, .0105, -.165, .31),
    )
    for x, z, length, radius, splay, relaxed in fingers[:digits - 1]:
        root = V(x, .003, z)
        joints = [root]
        for proportion, angle in (
            (.44, relaxed + .61 * knuckle),
            (.33, .34 + relaxed + .87 * knuckle),
            (.23, .72 + relaxed + 1.43 * knuckle),
        ):
            ray = V(math.cos(angle), -math.sin(angle), splay).normalized()
            joints.append(joints[-1] + ray * (proportion * length))
        root, proximal, middle, tip = joints
        points = [root + V(-.019, -.001, -.10 * z), root, root.lerp(proximal, .52), proximal,
                  proximal.lerp(middle, .53), middle, middle.lerp(tip, .67), tip]
        sections = ((.81, .86), (.97, 1.09), (.89, .96), (.96, 1.02),
                    (.81, .87), (.83, .87), (.72, .77), (.36, .47))
        _loft(g, scale, [hand(point) for point in points],
              [(depth * radius, width * radius) for depth, width in sections], sides=20, up=radial, density=4)

    # The distal thumb turns toward the index side of the palmar surface.
    thumb = (
        (.025, -.011, .025),
        (.044, -.019, .046),
        (.065, -.030, .066),
        (.084, -.039 - .005 * knuckle, .067),
        (.102, -.046 - .009 * knuckle, .056 - .008 * knuckle),
        (.111, -.049 - .010 * knuckle, .045 - .012 * knuckle),
    )
    _loft(g, scale, [hand(point) for point in thumb],
          [(.021, .019), (.019, .017), (.016, .015), (.014, .013), (.012, .010), (.005, .006)],
          sides=22, up=dorsal, density=5)


def arm_grasping(g, p):
    s = p.get("size", 1.0)
    knuckle = p["knuckle_walk"]
    shoulder, elbow, wrist, pad = _grasping_joints(knuckle)
    axis = (pad - wrist).normalized()
    g.setup(voxel=.0018 * s, detail=3.2, smooth=.38)
    g.slot("skin")
    _loft(g, s, [
        shoulder + V(.012, .084, -.003), shoulder + V(.015, .065, 0),
        shoulder + V(.017, .030, .005), shoulder + V(.013, -.029, .012),
        shoulder.lerp(elbow, .37) + V(.006, 0, .013), shoulder.lerp(elbow, .66), elbow,
        elbow.lerp(wrist, .27), elbow.lerp(wrist, .61), wrist, wrist + axis * .010,
    ], [
        (.012, .012), (.048, .051), (.074, .081), (.082, .082),
        (.072, .073), (.061, .055), (.054, .053),
        (.061, .060), (.047, .043), (.034, .031), (.029, .030),
    ], sides=32, up=FORWARD, density=6)
    _grasping_hand(g, s, wrist, axis, round(p["fingers"]), knuckle)


def _grasping_preset(p):
    return _preset(p, _grasping_joints(p["knuckle_walk"]), (.082, .052, .035, .046))


def _hydrostatic_path(curl, taper):
    points = [V(0, 0, 0), V(.096, -.040, .013), V(.205, -.114, .029),
              V(.334, -.147, .048), V(.459, -.112, .072)]
    for i, step in enumerate((.095, .079, .064, .049, .035, .023)):
        angle = .42 + 3.10 * curl * (i / 5) ** 1.14
        points.append(points[-1] + V(math.cos(angle), math.sin(angle), .15) * step)
    radii = [.091, .083, .067, .055, .044, .035, .029, .023,
             .046 * taper + .010, .037 * taper + .004, .023 * taper]
    return points, radii


def arm_hydrostatic(g, p):
    s = p.get("size", 1.0)
    points, radii = _hydrostatic_path(p["curl"], p["taper"])
    g.setup(voxel=.0019 * s, detail=2.1, smooth=.35)
    g.slot("skin")
    _loft(g, s, points, [(r, r * .89) for r in radii], sides=30, density=5)


def _hydrostatic_preset(p):
    points, radii = _hydrostatic_path(p["curl"], p["taper"])
    return _preset(p, points, radii)


def _cup(g, base, normal, r, sides):
    """Seven rings create a convex foot, a rounded lip, and a recessed bowl."""
    across = normal.cross(FORWARD).normalized()
    along = across.cross(normal).normalized()
    profile = ((.47, 0), (.72, .15), (.99, .49), (1, .71), (.73, .74), (.54, .42), (.23, .27))
    verts = [
        base + normal * (r * height) + (across * math.cos(a) + along * math.sin(a)) * (r * radius)
        for radius, height in profile
        for a in (2 * math.pi * i / sides for i in range(sides))
    ]
    faces = []
    for k in range(len(profile) - 1):
        lower, upper = k * sides, (k + 1) * sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((lower + i, upper + i, upper + j, lower + j))
    underside = len(verts)
    verts.extend([base, base + normal * (.24 * r)])
    for i in range(sides):
        j = (i + 1) % sides
        faces.extend(((underside, i, j), (underside + 1, (len(profile) - 1) * sides + j, (len(profile) - 1) * sides + i)))
    g._add(verts, faces)


def _sucker_section(t, width_scale):
    angle = math.pi * t
    center = V(.025 * math.sin(angle), -.042 * math.sin(angle) + .104 * t ** 4, .54 * t)
    tangent = V(.025 * math.pi * math.cos(angle), -.042 * math.pi * math.cos(angle) + .416 * t ** 3, .54)
    across = UP.cross(tangent).normalized()
    normal = tangent.cross(across).normalized()
    width = (.069 * (1 - t) ** .89 + .0025) * width_scale
    depth = (.015 * (1 - t) ** .85 + .0015) * math.sqrt(width_scale)
    return center, across, normal, width, depth


def suckers(g, p):
    s = p.get("size", 1.0)
    count, rows = round(p["per_arm"]), round(p["rows"])
    width_scale = min(1.0, (39 if rows == 2 else 18) / count)
    g.setup(voxel=.0014 * s * math.sqrt(width_scale), detail=1.2, slot_finish={"accent": "direct"})
    g.slot("base")
    sections = [_sucker_section(t / 16, width_scale) for t in range(17)]
    _loft(g, s, [c for c, _, _, _, _ in sections], [(w, h) for _, _, _, w, h in sections],
          sides=24, density=3)
    g.slot("accent")
    for i in range(count):
        t = (i + 1) / (count + 1)
        # Large proximal cups occupy longer intervals; distal rows converge at the tip.
        u = 1.0 - (1 - t) ** 1.34
        center, across, normal, width, depth = _sucker_section(u, width_scale)
        fraction = 0 if rows == 1 else (.51 if i % 2 else -.51)
        radius = min(width * (.92 if rows == 1 else .53), .54 * rows / count * .72 * (1 - .64 * t))
        lift = depth * math.sqrt(1.0 - fraction ** 2) - radius * .12
        base = center + across * (fraction * width) + normal * lift
        _cup(g, base * s, normal, radius * s, 12)


def _hook(g, s, start, direction, length, radius, curve, drop=0):
    reach = 1.0 - .65 * curve
    _loft(g, s, [
        start,
        start + direction * (length * .41) + V(0, -length * (.025 + drop), 0),
        start + direction * (length * (.72 - .14 * curve)) + V(0, -length * (.088 + .25 * curve + drop), 0),
        start + direction * (length * reach) + V(0, -length * (.18 + .68 * curve + drop), 0),
    ], [(radius, radius * 1.11), (radius * .78, radius * .91), (radius * .46, radius * .53),
        (radius * .08, radius * .08)], sides=18, density=6)


def talons(g, p):
    s = p.get("size", 1.0)
    grip, curve = p["grip"], p["curve"]
    g.setup(voxel=.00165 * s, detail=2.9, smooth=.34)
    g.slot("skin")
    _loft(g, s, [(0, .063, -.014), (0, .059, -.014), (0, .046, -.014),
                 (0, .010, -.014), (0, -.037, -.009), (0, -.062, .012)],
          [(.007, .008), (.023, .026), (.028, .031), (.024, .024), (.031, .029), (.042, .037)],
          sides=24, up=FORWARD)
    tips = []
    toes = ((-.64, .108, .079, .013), (0, .143, .089, .014),
            (.58, .117, .077, .012), (3.19, .099, .101, .016))
    for angle, length, claw_len, radius in toes:
        d = V(math.sin(angle), 0, math.cos(angle))
        base = V(0, -.056, .009)
        reach = length * (1 - .38 * grip)
        points = [base + d * (reach * t) + V(0, -(.024 + grip * .053) * t ** 1.25, 0)
                  for t in (0, .23, .48, .73, 1)]
        _loft(g, s, points, [(radius * w, radius * h) for w, h in ((1.7, 1.5), (1.53, 1.32), (1.33, 1.22), (1.19, 1.1), (.96, .92))],
              sides=20)
        basis = rot(UP, angle)
        for i in range(1, 6):
            t = i / 6
            y = -(.024 + grip * .053) * t ** 1.25
            _oval(g, s, base + d * (reach * t) + V(0, y + radius * .65, 0),
                  (radius * (1.24 - .26 * t), radius * .66, radius * .40), basis=basis, segs=14, rings=10)
        tips.append((points[-1] - d * .007, d, claw_len, radius))
    g.slot("claw")
    for point, d, length, radius in tips:
        _hook(g, s, point, d, length, radius, curve, .21 * grip)


def claws(g, p):
    s = p.get("size", 1.0)
    curve, extend = p["curve"], p["extend"]
    g.setup(voxel=.0012 * s, detail=2.8, smooth=.37)
    roots = [V((i - 1.5) * .070, -.020, .015 - abs(i - 1.5) * .013) for i in range(4)]
    g.slot("base")
    for i, b in enumerate(roots):
        k = 1 - .10 * abs(i - 1.5)
        _loft(g, s, [b - V(0, -.008, .024), b, b + V(0, -.004, .022), b + V(0, -.006, .034)],
              [(r * k, d * k) for r, d in ((.019, .019), (.034, .030), (.031, .025), (.026, .022))],
              sides=22)
    g.slot("claw")
    for i, b in enumerate(roots):
        k = 1 - .10 * abs(i - 1.5)
        _hook(g, s, b + V(0, -.006, .026 + .014 * extend), FORWARD,
              (.063 + .049 * extend) * k, .021 * k, curve)


def _tail_joints(segments, arch):
    points = [V(0, 0, 0)]
    for i in range(segments):
        t = (i + .5) / segments
        angle = lerp(-.66, .27 + 2.45 * arch, t)
        distance = (.98 - .29 * t) / segments
        points.append(points[-1] + V(0, math.cos(angle), math.sin(angle)) * distance)
    radii = [lerp(.068, .027, i / segments) for i in range(segments + 1)]
    return points, radii


def _tail_ring(g, s, a, b, axis, entry, exit, radius):
    """Keep segment ends parallel to their shared hinge so the shells can articulate."""
    stations = ((.026, .66, .69), (.043, .76, .77), (.09, .87, .83), (.20, .97, .91),
                (.37, 1.08, 1.04), (.53, 1.09, 1.05), (.71, 1.02, .99),
                (.85, .94, .9), (.94, .82, .81), (.974, .69, .71))
    sides = 28
    coords = []
    for t, width, height in stations:
        normal = entry.lerp(axis, min(2 * t, 1)).lerp(exit, max(2 * t - 1, 0)).normalized()
        dorsal = V(0, normal.z, -normal.y)
        center = a.lerp(b, t)
        for i in range(sides):
            angle = 2 * math.pi * i / sides
            crest = (.058 * math.sin(math.pi * t)
                     * sum(math.exp(-((angle - x) / .16) ** 2) for x in (1.18, 1.96)))
            radial = LATERAL * (width * math.cos(angle)) + dorsal * (height * math.sin(angle))
            coords.append((center + radial * (radius * (1.0 + crest))) * s)
    faces = [tuple(range(sides - 1, -1, -1))]
    for k in range(len(stations) - 1):
        bottom, top = k * sides, (k + 1) * sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((bottom + i, bottom + j, top + j, top + i))
    faces.append(tuple(range((len(stations) - 1) * sides, len(stations) * sides)))
    g._add(coords, faces)


def tail_segmented(g, p):
    s = p.get("size", 1.0)
    points, radii = _tail_joints(round(p["segments"]), p["arch"])
    g.setup(voxel=.0018 * s, detail=2.2, smooth=.30, slot_finish={"accent": "direct"})
    g.slot("skin")
    _loft(g, s, [*points[:-1], points[-1], points[-1] + (points[-1] - points[-2]).normalized() * .026],
          [r * .59 for r in radii] + [.012], sides=20, up=LATERAL, density=5)
    g.slot("accent")
    axes = [(b - a).normalized() for a, b in zip(points, points[1:])]
    hinges = [axes[0]] + [(a + b).normalized() for a, b in zip(axes, axes[1:])] + [axes[-1]]
    for i, axis in enumerate(axes):
        _tail_ring(g, s, points[i], points[i + 1], axis, hinges[i], hinges[i + 1],
                   (radii[i] + radii[i + 1]) * .5)


def _tail_preset(p):
    return _preset(p, *_tail_joints(round(p["segments"]), p["arch"]), motion="tail")


def stinger(g, p):
    s = p.get("size", 1.0)
    bulb, hook = p["bulb"], p["hook"]
    g.setup(voxel=.00155 * s, detail=1.7, smooth=.35)
    g.slot("base")
    _loft(g, s, [(0, -.022, .001), (0, .006, .001), (0, .038, 0), (0, .065, -.002)],
          [(.026, .027), (.023, .023), (.029, .031), (.034, .036)], sides=22, up=FORWARD)
    width = .46 + .54 * bulb
    _loft(g, s, [
        (0, .042, 0), (0, .077, .001), (0, .117, -.004),
        (0, .155, -.015), (0, .189, -.026 - .026 * hook),
        (0, .225 - .027 * hook, -.037 - .061 * hook),
        (0, .256 - .081 * hook, -.043 - .120 * hook),
        (0, .278 - .180 * hook, -.047 - .171 * hook),
    ], [(r * width, d * width) for r, d in ((.029, .029), (.052, .055), (.059, .065), (.051, .056),
                                          (.034, .039), (.019, .023), (.009, .011), (.0014, .0014))],
        sides=28, up=FORWARD, density=6)


BUILDERS = {
    "pincer_limb": pincer_limb,
    "arm_grasping": arm_grasping,
    "arm_hydrostatic": arm_hydrostatic,
    "suckers": suckers,
    "talons": talons,
    "claws": claws,
    "tail_segmented": tail_segmented,
    "stinger": stinger,
}
OVERRIDES = {
    "pincer_limb": {"cap": "grasp", "bones": [{"name": "jaw", "pivot": (.558, -.042, .092), "axis": (0, 0, 1), "angle": -26.0}]},
    "arm_grasping": {"cap": "hand"},
    "arm_hydrostatic": {"cap": "hand"},
    "suckers": {"orient": "surface"},
    "talons": {"cap": "foot"},
    "claws": {"cap": "foot"},
    "stinger": {"orient": "surface"},
}
PRESETS = {
    "pincer_limb": _pincer_preset,
    "arm_grasping": _grasping_preset,
    "arm_hydrostatic": _hydrostatic_preset,
    "tail_segmented": _tail_preset,
}
