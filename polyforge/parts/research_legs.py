"""Researched walking limbs. All landmarks are on the +X side, relative to the hip.

The same joint stations place the rig and the sculpt. The last station is the
ankle or toe base; the terminal anatomy is built into each sculpt.
"""
import math
from functools import partial

from ..kit import BACK, RIGHT, UP, V, lerp


def _arthropod_joints(p):
    angle = math.radians(p.get("sprawl_deg", 55))
    root = V(0, 0, 0)
    coxa = V(.11, -.025, .012)
    knee = coxa + V(.43 * math.sin(angle), .39 * math.cos(angle), -.055)
    ankle = knee + V(-.015, -.355, .135)
    tarsus = ankle + V(-.085, -.17, .165)
    articles = int(round(p.get("segments", 4))) - 2
    distal = [ankle.lerp(tarsus, i / articles) for i in range(1, articles + 1)]
    radii = [.061, .044, .037, .023] + [lerp(.023, .014, i / articles) for i in range(1, articles + 1)]
    return [root, coxa, knee, ankle, *distal], radii


def _digitigrade_joints(p):
    lift = p.get("hock_lift", .6)
    return [V(0, 0, 0), V(-.037, -.265, .275),
            V(.034, -.635 + .24 * lift, -.115), V(.018, -.755, .038)], [.105, .082, .047, .039]


def _plantigrade_joints(p):
    half_angle = math.radians(p.get("knee_bend_deg", 20) / 2)
    incline = math.radians(12)
    knee = V(-.038, -.37 * math.cos(incline + half_angle), .37 * math.sin(incline + half_angle))
    ankle = knee + V(.017, -.32 * math.cos(incline - half_angle), .32 * math.sin(incline - half_angle))
    return [V(0, 0, 0), knee, ankle], [.139, .093, .072]


def _sprawling_joints(p):
    angle = math.radians(p.get("sprawl_deg", 70))
    elbow = V(.41 * math.sin(angle), -.41 * math.cos(angle), -.170)
    wrist = elbow + V(.10, -.19, .20)
    return [V(0, 0, 0), elbow, wrist], [.081, .064, .037]


def _jumping_joints(p):
    fold = p.get("fold", .8)
    thigh = math.radians(12 + 64 * fold)
    shank = math.radians(8 + 73 * fold)
    tarsus = math.radians(12 + 45 * fold)
    knee = V(.92 * math.sin(thigh), -math.cos(thigh), .392 * math.sin(thigh)) * .34
    ankle = knee + V(.19 * math.sin(shank), -math.cos(shank), -.982 * math.sin(shank)) * .36
    instep = ankle + V(-.22 * math.sin(tarsus), -math.cos(tarsus), .976 * math.sin(tarsus)) * .29
    return [V(0, 0, 0), knee, ankle, instep], [.107, .09, .046, .026]


def _bird_joints(p):
    return [V(0, 0, 0), V(.012, -.165, .065), V(.034, -.32, -.098),
            V(.017, -.655, .083)], [.114, .096, .05, .035]


def _spindle(g, start, end, profile, up=RIGHT):
    """Profile stations are fractions of a segment and two section radii."""
    g.loft([start.lerp(end, t) for t, w, h in profile],
           [(w, h) for t, w, h in profile], sides=22, density=3, up=up)


def _hook(g, root, direction, length, radius, drop, point=.0015):
    direction = direction.normalized()
    g.loft([root, root + direction * length * .40 + UP * drop * .10,
            root + direction * length * .82 - UP * drop * .25,
            root + direction * length - UP * drop],
           [radius, radius * .78, radius * .40, point], sides=14, density=3)


def _arthropod(g, p, joints):
    root, coxa, knee, ankle = joints[:4]
    tip = joints[-1]
    g.oval(root, (.065, .067, .069))
    _spindle(g, root, coxa, [(.26, .038, .038), (.62, .052, .054),
                              (.84, .051, .05), (1, .035, .035)])
    _spindle(g, coxa, knee, [(-.025, .026, .026), (.13, .051, .05), (.43, .061, .057),
                              (.77, .049, .044), (1, .028, .027)])
    g.oval(knee, (.036, .038, .034))
    _spindle(g, knee, ankle, [(.04, .022, .024), (.11, .035, .033),
                                (.67, .026, .024), (.95, .026, .023), (1, .016, .016)])
    if p.get("tibia_teeth", 0) >= .5:
        for i in range(4):
            base = knee.lerp(ankle, .41 + .14 * i) + RIGHT * .014
            g.cone(base, base + V(.034 + .005 * i, -.017, 0), .014)
    # With the femur and tibia, the subdivision of the tarsus gives 3–5 articles.
    tarsus = joints[3:]
    for i, (start, end) in enumerate(zip(tarsus, tarsus[1:])):
        r = lerp(.023, .014, i / (len(tarsus) - 1))
        _spindle(g, start, end, [(0, .55 * r, .55 * r), (.14, 1.12 * r, 1.12 * r),
                                  (.76, .92 * r, .92 * r), (.91, .98 * r, .98 * r), (1, .48 * r, .48 * r)])
    _hook(g, tip, V(-.44, .04, .70), .055, .014, .035)


def _digitigrade(g, p, joints):
    hip, knee, hock, ankle = joints
    thigh = (knee - hip).normalized()
    g.loft([hip - thigh * .089, hip - thigh * .055, hip + thigh * .023, hip.lerp(knee, .38),
            hip.lerp(knee, .71), knee, knee.lerp(hock, .27), knee.lerp(hock, .62),
            hock, hock.lerp(ankle, .20), hock.lerp(ankle, .73), ankle],
           [(.012, .013), (.070, .073), (.125, .108), (.14, .122), (.122, .10), (.079, .078),
            (.087, .066), (.057, .045), (.044, .039), (.043, .034), (.035, .033), (.04, .04)],
           up=RIGHT, sides=26, density=4)
    # The lateral quadriceps and tibialis run obliquely into the joint.
    g.loft([hip.lerp(knee, .10) + V(.04, 0, .011), hip.lerp(knee, .39) + V(.092, 0, .017),
            hip.lerp(knee, .71) + V(.073, 0, .042), knee + V(.031, .012, .042)],
           [(.024, .024), (.065, .036), (.065, .035), (.037, .027)], up=RIGHT)
    g.loft([knee + V(.025, 0, 0), knee.lerp(hock, .29) + V(.039, 0, .032),
            knee.lerp(hock, .72) + V(.025, 0, .014), hock + V(.015, 0, 0)],
           [.044, .044, .026, .018], up=RIGHT)
    g.oval(hock + V(0, .009, -.018), (.043, .044, .053))
    pad = ankle + V(0, -.028, .045)
    g.oval(pad, (.086, .052, .092))
    for i, reach in enumerate((.116, .137, .138, .114)):
        x = (i - 1.5) * .048
        g.oval(pad + V(x, -.009, reach - .035), (.028, .037, .049), segs=20)
    if p.get("dewclaw", 0) >= .5:
        digit = hock.lerp(ankle, .64) + V(-.030, 0, .01)
        g.oval(digit, (.019, .024, .017))
        _hook(g, digit + V(-.005, -.008, .005), V(-.32, -.7, .6), .036, .011, .014)


def _plantar_surface(g, ankle):
    """Transverse sections from the heel pad to the metatarsal heads.

    Medial is -X on this limb. Raising just that side of the midfoot leaves
    a lateral load-bearing rail between the heel and the ball of the foot.
    """
    from scipy.interpolate import PchipInterpolator

    # z, medial and lateral limits, low sole, medial arch lift, dorsal height
    sections = [
        (-.098, -.010, .011, -.063, .000, -.052),
        (-.090, -.034, .035, -.084, .000, -.025),
        (-.072, -.046, .049, -.101, .000, -.003),
        (-.048, -.049, .052, -.103, .000,  .030),
        (-.022, -.047, .051, -.103, .004,  .047),
        ( .010, -.043, .050, -.101, .020,  .049),
        ( .045, -.037, .051, -.101, .040,  .029),
        ( .074, -.041, .057, -.102, .044,  .011),
        ( .100, -.055, .068, -.102, .030, -.010),
        ( .125, -.070, .077, -.103, .009, -.025),
        ( .148, -.080, .081, -.103, .001, -.037),
        ( .164, -.080, .077, -.102, .000, -.045),
        ( .178, -.068, .064, -.096, .000, -.056),
        ( .183, -.049, .047, -.087, .000, -.065),
    ]
    stations = [row[0] for row in sections]
    profile = PchipInterpolator(stations, [row[1:] for row in sections])
    levels = [lerp(a, b, i / 3) for a, b in zip(stations, stations[1:]) for i in range(3)]
    levels.append(stations[-1])
    sides = 52
    vertices, faces = [], []
    for z, (inner, outer, sole, arch, top) in zip(levels, profile(levels)):
        forefoot = max(0, min(1, (z - .102) / .061))
        ray_position = max(0, min(1, (z - .012) / .16))
        tendon_height = .0050 * math.sin(math.pi * ray_position)
        tendon_x = [lerp(a, b, ray_position) for a, b in
                    ((-.017, -.053), (-.006, -.017), (.007, .016), (.018, .042))]
        for i in range(sides):
            angle = math.tau * i / sides
            across, up = math.cos(angle), math.sin(angle)
            medial = (1 - across) * .5
            x = lerp(outer, inner, medial)
            floor = sole + arch * medial ** 1.65
            edge = lerp(floor, top, .32)
            if up >= 0:
                height = lerp(edge, top, up ** .89)
                dorsal_ridges = sum(math.exp(-((x - center) / .0085) ** 2) for center in tendon_x)
                height += tendon_height * dorsal_ridges * up
            else:
                # The middle of each pad is flattened under load.
                height = lerp(floor, edge, abs(across) ** 5)
            vertices.append(ankle + V(x, height, z - .016 * across * forefoot))
    for row in range(len(levels) - 1):
        for i in range(sides):
            a = row * sides + i
            b = row * sides + (i + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    last = (len(levels) - 1) * sides
    faces.extend((tuple(reversed(range(sides))), tuple(last + i for i in range(sides))))
    g.current._add(vertices, faces)


def _plantigrade_toe(g, ankle, root_x, root_z, tip_x, tip_z, width, height):
    # Each toe has a knuckle, an interphalangeal waist, a distal pad and a
    # gently domed nail. A short free tip lifts beyond the contact patch.
    sections = [(0, .80, .88, .006), (.22, 1.04, 1.08, .003),
                (.40, .92, 1.01, .004), (.52, .83, .81, .005),
                (.67, .95, .88, .001), (.81, .97, .84, 0),
                (.92, .81, .69, .002), (.98, .50, .44, .007), (1, .21, .22, .012)]
    points, radii = [], []
    for t, breadth, depth, clearance in sections:
        half_height = height * depth
        points.append(ankle + V(lerp(root_x, tip_x, t), -.103 + clearance + half_height,
                                lerp(root_z, tip_z, t)))
        radii.append((width * breadth, half_height))
    g.loft(points, radii, up=UP, sides=20, density=3, exponent=.84)
    nail_points = []
    for station in (4, 5, 6):
        nail_points.append(points[station] + UP * (radii[station][1] - .0009))
    g.loft(nail_points, [(width * .40, .0018), (width * .65, .0030), (width * .47, .0020)],
           up=UP, sides=16, density=3)


def _plantigrade(g, p, joints):
    hip, knee, ankle = joints
    g.setup(voxel=.0021 * p.get("size", 1), detail=2.35, smooth=.38)
    g.loft([hip + V(.008, .079, -.046), hip + V(0, .044, -.024), hip.lerp(knee, .06), hip.lerp(knee, .35),
            hip.lerp(knee, .69), knee, knee.lerp(ankle, .32), knee.lerp(ankle, .58),
            knee.lerp(ankle, .86), ankle, ankle + V(0, -.039, .002), ankle + V(0, -.062, .022)],
           [(.020, .021), (.086, .078), (.14, .125), (.151, .136), (.127, .111), (.098, .092),
            (.115, .102), (.093, .092), (.061, .055), (.049, .049), (.044, .043), (.038, .036)], up=RIGHT, sides=26)
    g.oval(knee + V(0, .009, .060), (.067, .080, .049))
    _plantar_surface(g, ankle)
    # The lateral malleolus lies lower and farther back than the medial one.
    g.loft([ankle + V(.041, .050, -.002), ankle + V(.046, .015, -.008),
            ankle + V(.046, -.006, -.013), ankle + V(.039, -.027, -.010)],
           [(.013, .009), (.016, .012), (.016, .012), (.010, .007)], up=RIGHT, sides=18)
    g.loft([ankle + V(-.037, .048, .009), ankle + V(-.043, .019, .012),
            ankle + V(-.045, .004, .010), ankle + V(-.035, -.013, .008)],
           [(.010, .009), (.016, .010), (.014, .010), (.009, .007)], up=RIGHT, sides=18)
    g.loft([ankle + V(.003, .102, -.034), ankle + V(.003, .052, -.047),
            ankle + V(.002, .005, -.062), ankle + V(0, -.038, -.073)],
           [(.024, .019), (.021, .015), (.022, .017), (.028, .023)], up=BACK, sides=18)
    # Great toe through little toe, in anatomical order on the +X side.
    for toe in [(-.055, .151, -.071, .259, .0240, .0205),
                (-.018, .153, -.021, .250, .0170, .0160),
                ( .013, .149,  .019, .234, .0154, .0145),
                ( .040, .140,  .052, .215, .0135, .0132),
                ( .062, .128,  .081, .193, .0123, .0120)]:
        _plantigrade_toe(g, ankle, *toe)


def _sprawling(g, p, joints):
    root, elbow, wrist = joints
    g.loft([root - (elbow - root).normalized() * .033, root.lerp(elbow, .12),
            root.lerp(elbow, .44), root.lerp(elbow, .79), elbow, elbow.lerp(wrist, .29),
            elbow.lerp(wrist, .62), wrist], [(.055, .061), (.083, .086), (.09, .08),
            (.071, .067), (.062, .064), (.073, .065), (.055, .048), (.035, .035)],
           up=UP, sides=24)
    palm = wrist + V(.01, -.019, .057)
    g.oval(palm, (.064, .032, .077))
    toes = [(-1.05, .138), (-.53, .188), (-.04, .238), (.44, .23), (1.09, .161)]
    count = int(round(p.get("digits", 5)))
    for angle, length in toes[:count - 1] + toes[-1:]:
        d = V(math.sin(angle), 0, math.cos(angle))
        root = palm + V(.051 * math.sin(angle), -.007, .046 * math.cos(angle))
        base = root + d * length * .83 + V(0, -.025, 0)
        g.loft([root, root + d * length * .36 + V(0, -.012, 0),
                root + d * length * .63 + V(0, -.022, 0), base],
               [.021, .015, .012, .013], sides=14)
        _hook(g, base, d, length * .24, .012, .021)


def _jumping(g, p, joints):
    hip, knee, ankle, instep = joints
    thigh = (knee - hip).normalized()
    g.loft([hip - thigh * .045, hip.lerp(knee, .13), hip.lerp(knee, .41),
            hip.lerp(knee, .74), knee, knee.lerp(ankle, .26), knee.lerp(ankle, .59),
            knee.lerp(ankle, .86), ankle, ankle.lerp(instep, .35),
            ankle.lerp(instep, .66), instep],
           [(.055, .054), (.111, .111), (.119, .129), (.105, .098), (.08, .074),
            (.079, .075), (.068, .063), (.046, .045), (.045, .043),
            (.043, .039), (.03, .031), (.023, .027)], up=RIGHT, sides=24)
    g.oval(ankle + V(0, 0, -.004), (.047, .044, .052))
    palm = instep + V(0, -.013, .042)
    g.oval(palm, (.039, .022, .060))
    ends = []
    for angle, length in [(-.88, .292), (-.45, .363), (0, .40), (.46, .351), (.91, .264)]:
        d = V(math.sin(angle), -.46 * math.cos(angle), math.cos(angle)).normalized()
        tip = palm + d * length
        g.loft([palm, palm + d * length * .4, palm + d * length * .8, tip],
               [.019, .013, .009, .010], sides=14, density=3)
        g.oval(tip, (.012, .009, .014), segs=16, rings=10)
        ends.append(tip)
    for a, b in zip(ends, ends[1:]):
        # The free margin dips between rays. Keep the membrane below the ray ridges.
        web_root = palm - UP * .009
        a, b = palm.lerp(a, .94) - UP * .005, palm.lerp(b, .94) - UP * .005
        edge = a.lerp(b, .5)
        g.slab([web_root, a, palm.lerp(a.lerp(b, .22), .89),
                palm.lerp(edge, .84), palm.lerp(a.lerp(b, .78), .89), b], UP, .009, bulge=.25)


def _feathered_thigh(g, hip, hock, coverage):
    """A single closed surface with a scalloped overhang at each feather row."""
    axis = hock - hip
    sections = [(-.11, .009), (-.06, .060), (.04, .106), (.25, .119),
                (.48, .111), (.70, .084), (.87, .054), (1, .042)]

    def radius(t):
        for (t0, r0), (t1, r1) in zip(sections, sections[1:]):
            if t <= t1:
                return lerp(r0, r1, (t - t0) / (t1 - t0))
        return sections[-1][1]

    def axis_point(t):
        return hip + axis * t + BACK * (.057 * math.sin(math.pi * t))

    if coverage <= .005:
        g.loft([axis_point(t) for t, r in sections], [r for t, r in sections], up=RIGHT)
        return

    sides = 72
    span = .36 + .55 * coverage
    relief = min(1, coverage / .2)
    vertices = []
    levels = []

    def ring(parameters, heights):
        for i, (t, height) in enumerate(zip(parameters, heights)):
            angle = math.tau * i / sides
            normal = V(math.cos(angle), 0, math.sin(angle))
            vertices.append(axis_point(t) + normal * (radius(t) + height))
        levels.append(parameters)

    for t in (-.11, -.08, -.055, -.02, .03):
        ring([t] * sides, [0] * sides)
    for row, edge in enumerate((.23, .54, .85)):
        # Neighbouring rows alternate. A feather has a wide root and a long
        # tapered trailing point. Its lip returns sharply to the shaft below it.
        tips, ridges = [], []
        for i in range(sides):
            cycle = (i * 6 / sides + row * .5) % 1
            ridge = 1 - abs(2 * cycle - 1)
            tips.append(span * (edge + .19 * ridge ** .85))
            ridges.append(ridge)
        previous = levels[-1]
        ring([lerp(a, b, .46) for a, b in zip(previous, tips)],
             [relief * (.005 + .008 * r) for r in ridges])
        ring([t - .018 for t in tips], [relief * (.009 + .011 * r) for r in ridges])
        ring(tips, [relief * (.011 + .010 * r) for r in ridges])
        ring([t + .012 for t in tips], [0] * sides)
    end = max(levels[-1])
    for t in sorted({lerp(end, 1, .30), lerp(end, 1, .65), 1.0}):
        ring([t] * sides, [0] * sides)

    faces = []
    for row in range(len(levels) - 1):
        for i in range(sides):
            a = row * sides + i
            b = row * sides + (i + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    last = (len(levels) - 1) * sides
    faces += [tuple(reversed(range(sides))), tuple(last + i for i in range(sides))]
    g.current._add(vertices, faces)


def _bird(g, p, joints):
    hip, _, hock, ankle = joints
    _feathered_thigh(g, hip, hock, p.get("feathered", .7))
    axis = (hock - hip).normalized()
    g.loft([hock - axis * .04, hock, hock.lerp(ankle, .15),
            hock.lerp(ankle, .74), ankle], [.045, .046, .036, .030, .034],
           up=RIGHT, sides=22)
    if p.get("scutes", 1) >= .5:
        for i in range(7):
            t = .16 + i * .115
            start = hock.lerp(ankle, t)
            end = hock.lerp(ankle, t + .068)
            r = lerp(.037, .031, t)
            _spindle(g, start + BACK * r * .32, end + BACK * r * .32,
                     [(0, r * .55, r * .82), (.67, r * .77, r), (1, r * .70, r * .96)])
    g.oval(ankle + V(0, -.013, .021), (.052, .031, .055))
    for angle, length in ((-.76, .223), (-.08, .271), (.57, .232), (2.66, .170)):
        d = V(math.sin(angle), 0, math.cos(angle))
        root = ankle + d * .024 - UP * .013
        knuckle = root + d * length * .79 - UP * .025
        g.loft([root, root + d * length * .31 - UP * .013, root + d * length * .55 - UP * .024,
                knuckle, root + d * length - UP * .028], [.028, .024, .019, .024, .019], sides=16)
        _hook(g, root + d * length * .97 - UP * .027, d, .066, .020, .075, point=.0028)


_FAMILIES = {
    "leg_arthropod": (_arthropod_joints, _arthropod),
    "leg_digitigrade": (_digitigrade_joints, _digitigrade),
    "leg_plantigrade": (_plantigrade_joints, _plantigrade),
    "leg_sprawling": (_sprawling_joints, _sprawling),
    "leg_jumping": (_jumping_joints, _jumping),
    "leg_bird": (_bird_joints, _bird),
}


def _build(joints_fn, sculpt, g, p):
    size = p.get("size", 1)
    g.setup(voxel=.0030 * size, detail=1.65, smooth=.44)
    g.slot("base")
    joints, _ = joints_fn(p)
    sculpt(g, p, joints)
    if size != 1:
        for primitive in g.current.prims:
            primitive.v = [point * size for point in primitive.v]


def _preset(joints_fn, p):
    size = p.get("size", 1)
    joints, radii = joints_fn(p)
    return {"segments": [list((b - a) * size) for a, b in zip(joints, joints[1:])],
            "radii": [radius * size for radius in radii], "motion": "auto"}


BUILDERS = {name: partial(_build, joints, sculpt) for name, (joints, sculpt) in _FAMILIES.items()}
PRESETS = {name: partial(_preset, joints) for name, (joints, _) in _FAMILIES.items()}
OVERRIDES = {"leg_bird": {"topology_changes": ("feathered",)}}
