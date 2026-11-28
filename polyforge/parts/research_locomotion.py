"""Locomotor anatomy in metres, +Y dorsal, +Z rostral, paired parts authored at +X.

The reference soles are presented plantar-side up. In the rig the pad surfaces
face the ground and the hallux points medially, toward the other foot.
"""
import math

from mathutils import Matrix
from mathutils.bvhtree import BVHTree

from ..kit import BACK, RIGHT, UP, V, lerp, rot


def _tube(g, path, radii, size, *, up=UP, sides=12, density=3):
    widths = [(r[0] * size, r[1] * size) if isinstance(r, tuple) else r * size
              for r in radii]
    g.loft([V(v) * size for v in path], widths, sides=sides, density=density, up=up)


def _oval(g, center, radii, size, basis=None):
    g.oval(V(center) * size, tuple(r * size for r in radii),
           basis=basis, segs=18, rings=10)


def _ankle_cuff(g, path, radii, size, sides=18):
    """Round the mounting rim into a flat section where the shank continues."""
    root = V(path[0])
    outward = (root - V(path[1])).normalized()
    width, depth = radii[0]
    rim = min(width, depth) * .05
    stations = [root + outward * rim, root + outward * (.76 * rim), *path]
    sections = [(.06 * width, .06 * depth), (.91 * width, .91 * depth), *radii]
    _tube(g, stations, sections, size, up=BACK, sides=sides)


class _FootForm:
    """One quad skin from heel to ankle, with open sockets for each digit."""

    def __init__(self, sections, count, ankle, hallux=None, plantar=None):
        self.vertices, self.faces = [], []
        self.rows = []
        columns = 2 * count
        for z, medial, lateral, top, bottom, rake, arch, ridge in sections:
            dorsal, sole = [], []
            for i in range(columns + 1):
                u = i / count - 1
                x = u * (medial if u < 0 else lateral)
                depth = top - bottom
                # The sidewall is rounded by the two margins and its central row.
                upper = top - depth * .25 * abs(u)**2.4
                lower = bottom + depth * .19 * abs(u)**2.4
                lower += arch * (1 - .65 * u) * (1 - .55 * abs(u))
                if plantar and len(self.rows) in plantar:
                    lower += .001 * plantar[len(self.rows)][i]
                upper += ridge * (i % 2) * (1 - .45 * abs(u))
                where = z + rake * abs(u + .07)**1.65
                dorsal.append(self.point((x, upper, where)))
                sole.append(self.point((x, lower, where)))
            sides = {}
            # Only the final cross section needs interior web commissures.
            for i in (range(0, columns + 1, 2) if len(self.rows) == len(sections) - 1 else (0, columns)):
                sides[i] = self.point((self.vertices[dorsal[i]] + self.vertices[sole[i]]) * .5)
            self.rows.append((dorsal, sole, sides))

        back, front = ankle
        left, right = 1, columns - 1
        for k, ((d, p, m), (dn, pn, mn)) in enumerate(zip(self.rows, self.rows[1:])):
            for i in range(columns):
                if not (back <= k < front and left <= i < right):
                    self.faces.append((d[i], dn[i], dn[i + 1], d[i + 1]))
                self.faces.append((p[i], p[i + 1], pn[i + 1], pn[i]))
            for i in (0, columns):
                if i == 0 and hallux and hallux[0] <= k < hallux[1]:
                    continue
                side = [(d[i], m[i], mn[i], dn[i]), (m[i], p[i], pn[i], mn[i])]
                self.faces.extend(side if i == 0 else [tuple(reversed(f)) for f in side])

        # Two half-fans close the rounded posterior heel with a level central edge.
        d, p, m = self.rows[0]
        self.faces += [(*d, m[columns], m[0]), (*reversed(p), m[0], m[columns])]
        d0 = self.rows[back][0]
        d1 = self.rows[front][0]
        self.ankle = [d0[left], *(self.rows[k][0][left] for k in range(back + 1, front + 1)),
                      *d1[left + 1:right + 1], *(self.rows[k][0][right] for k in range(front - 1, back - 1, -1)),
                      *reversed(d0[left + 1:right])]
        if hallux:
            a, b = hallux
            lo, mid, hi = self.rows[a], self.rows[(a + b) // 2], self.rows[b]
            self.hallux = [lo[0][0], lo[2][0], lo[1][0], mid[1][0],
                           hi[1][0], hi[2][0], hi[0][0], mid[0][0]]

    def point(self, value):
        self.vertices.append(V(value))
        return len(self.vertices) - 1

    def center(self, loop):
        return sum((self.vertices[i] for i in loop), V(0, 0, 0)) / len(loop)

    def bridge(self, a, b):
        for i in range(len(a)):
            j = (i + 1) % len(a)
            self.faces.append((a[i], a[j], b[j], b[i]))

    def cuff(self, z, depth, width, height, swelling):
        """Carry the dorsal opening around the ankle bones into a level mounting rim."""
        root = self.ankle
        base = self.center(root)
        directions = []
        for i in root:
            point = self.vertices[i]
            a = math.atan2((point.z - base.z) / depth, (point.x - base.x) / width)
            directions.append((math.cos(a), math.sin(a)))
        for y, scale, correction, blend in ((.006, 1.08, 1., .50), (.016, 1.01, .24, .94),
                                             (height - .004, 1., 0., 1.), (height, .96, 0., 1.),
                                             (height, .72, 0., 1.)):
            loop = []
            for i, (x, fore) in zip(self.ankle, directions):
                malleolus = swelling * correction * abs(x)**4
                goal = V(x * (width * scale + malleolus), y - .005 * correction * (1 + x),
                         z + fore * depth * scale)
                loop.append(self.point(self.vertices[i].lerp(goal, blend)))
            self.bridge(root, loop)
            root = loop
        self.faces.append(tuple(root))

    def toe(self, i):
        d, p, m = self.rows[-1]
        j = 2 * i
        return [d[j], m[j], p[j], p[j + 1], p[j + 2], m[j + 2], d[j + 2], d[j + 1]]

    def digit(self, root, stations, roll=0.):
        """Bridge the physical opening into rounded proximal, joint and tip sections."""
        points = [self.center(root), *(s[0] for s in stations)]
        perimeter = [(-.74, .73), (-1, 0), (-.75, -.76), (0, -1), (.75, -.76),
                     (1, 0), (.74, .73), (0, 1)]
        across = UP.cross(points[1] - points[0]).normalized()
        for k, (c, w, h) in enumerate(stations, 1):
            axis = (points[min(k + 1, len(stations))] - points[k - 1]).normalized()
            # Carry the transverse direction through a downward-flexed tip.
            across = (across - axis * across.dot(axis)).normalized()
            dorsal = axis.cross(across)
            turn = rot(axis, roll * k / len(stations))
            across, dorsal = turn @ across, turn @ dorsal
            loop = [self.point(c + across * (x * w) + dorsal * (y * h)) for x, y in perimeter]
            self.bridge(root, loop)
            root = loop
        self.faces.append(tuple(root))

    def emit(self, g, size):
        # Drop unused points inside the dorsal opening.
        used = sorted({i for f in self.faces for i in f})
        index = {vertex: i for i, vertex in enumerate(used)}
        g.current._add([self.vertices[i] * size for i in used],
                       [tuple(index[i] for i in face) for face in self.faces])


def _plantar_pad(g, surface, center, width, length, thickness, size, angle=0., metacarpal=False):
    """A low, closed cushion with a tucked-in perimeter embedded in the sole."""
    rings = []
    basis = rot(UP, angle)

    def height(x, z):
        point = center + basis @ V(width * x, 0, length * z)
        return surface.ray_cast(V(point.x, -1., point.z), UP)[0].y

    # Fit the local slope and curvature at five plantar landmarks. The pad
    # follows the rounded toe without transferring polygon ridges from its cage.
    reach = .72
    y0 = height(0, 0)

    def profile(negative, positive):
        return ((positive - negative) / (2 * reach),
                (positive + negative - 2 * y0) / (2 * reach**2))

    dx, xx = profile(height(-reach, 0), height(reach, 0))
    dz, zz = profile(height(0, -reach), height(0, reach))
    for r, h in ((.10, -1.), (.52, -.95), (.79, -.69), (.94, -.25),
                 (1., .24), (.98, .51), (.79, .80), (.22, .90)):
        loop = []
        for j in range(16):
            a = math.tau * j / 16
            x, z = math.cos(a), math.sin(a)
            if metacarpal:
                z += .32 * math.exp(-(x / .33)**2) * max(0., -z)**3
                x *= 1 - .21 * z
            point = center + basis @ V(width * r * x, 0, length * r * z)
            u, v = r * x, r * z
            point.y = y0 + u * (dx + u * xx) + v * (dz + v * zz) + thickness * h + .0015
            loop.append(point * size)
        rings.append(loop)
    _closed_rings(g, rings)


def paw_padded(g, p):
    size, spread, count = p["size"], p["spread"], round(p["toe_pads"])
    # Longitudinal landmarks: heel, instep, metacarpal pad and web commissures.
    sections = [
        (-.067, .010, .010, -.043, -.061, .003, 0, 0),
        (-.061, .026, .026, -.030, -.068, .007, 0, 0),
        (-.051, .043, .043, -.010, -.076, .004, 0, 0),
        (-.037, .050, .050, -.001, -.083, .002, 0, 0),
        (-.013, .052, .052, .001, -.089, 0, 0, 0),
        ( .015, .062, .062, -.004, -.095, 0, 0, 0),
        ( .045, .079, .079, -.012, -.099, -.004, 0, .001),
        ( .075, .088, .088, -.017, -.101, -.009, 0, .002),
        ( .120, .089, .089, -.022, -.096, -.024, 0, .003),
    ]
    form = _FootForm(sections, count, ankle=(2, 6))
    form.cuff(-.012, .044, .046, .036, .002)
    span = .065 + .036 * spread
    width = min(.034, .49 * 2 * span / (count - 1))
    pads = []
    for i in range(count):
        u = 2 * i / (count - 1) - 1
        root = form.toe(i)
        start = form.center(root)
        end = V(span * u, -.059, .198 - .036 * abs(u)**1.6)
        stations = []
        for t, w, h, relief in ((.15, .85, .026, .002), (.32, .96, .034, .004),
                                (.54, 1., .038, .005), (.74, .94, .035, .004),
                                (.90, .76, .026, 0), (1., .34, .011, -.001)):
            c = start.lerp(end, t) + UP * relief
            spacing = lerp(2 * .089 / count, 2 * span / (count - 1), t)
            stations.append((c, min(width * w, .48 * spacing), h))
        form.digit(root, stations)
        center = start.lerp(end, .55)
        center.y = -.090
        pads.append((center, math.atan2(end.x - start.x, end.z - start.z)))
    g.setup(finish="sculpt")
    g.slot("skin")
    form.emit(g, size)
    g.slot("accent")
    surface = BVHTree.FromPolygons(form.vertices, form.faces)
    _plantar_pad(g, surface, V(0, -.098, .067), .061, .045, .014, size, metacarpal=True)
    for center, angle in pads:
        _plantar_pad(g, surface, center, .85 * width, .028, .013, size, angle)


def foot_webbed_long(g, p):
    s, count = p["size"], round(p["toes"])
    reach = .14 + .84 * p["web"]**.60
    g.setup(voxel=.0026 * s)
    g.slot("skin")
    _ankle_cuff(g, [(0, .023, -.024), (0, -.014, -.012), (0, -.032, .019), (0, -.036, .054)],
          [(.024, .025), (.025, .027), (.034, .024), (.038, .017)], s)
    roots, ends = [], []
    for i in range(count):
        u = i / (count - 1)
        a = math.radians(lerp(-45, 52, u))
        length = .14 + .135 * math.sin(math.pi * u)**.8
        root = V((u - .5) * .052, -.036, .038)
        tip = root + V(math.sin(a), 0, math.cos(a)) * length
        mid = lerp(root, tip, .57) + V(0, .002, 0)
        _tube(g, [root, mid, lerp(mid, tip, .85), tip], [.016, .0115, .009, .011], s)
        _oval(g, tip, (.016, .013, .020), s, rot(UP, a))
        roots.append(root)
        ends.append(tip)
    for i in range(count - 1):
        a, b = roots[i:i + 2]
        left, right = lerp(a, ends[i], reach), lerp(b, ends[i + 1], reach)
        border = []
        for j in range(9):
            t = j / 8
            outer = lerp(left, right, t)
            base = lerp(a, b, t)
            border.append(lerp(base, outer, 1 - .25 * math.sin(math.pi * t)**.70))
        g.slab([v * s for v in [a, *border, b]], UP, .011 * s, bulge=.18)


def _ape_nail(g, center, tangent, width, length, size, inward=0.):
    """Seat the nail plate in the dorsal pad, pronating the opposable toe."""
    t = tangent.normalized()
    across = UP.cross(t).normalized()
    dorsal = t.cross(across).normalized()
    turn = rot(t, inward)
    across, dorsal = turn @ across, turn @ dorsal
    frame = Matrix((across, dorsal, t)).transposed()
    g.oval((center + dorsal * (.63 * width)) * size,
           (width * .67 * size, .0028 * size, length * size), frame, segs=10, rings=5)


def foot_grasping(g, p):
    """Plantigrade primate foot: heel, ankle, four rays and hallux in one skin."""
    size, curl = p["size"], p["curl"]
    angle = math.radians(p["hallux_angle_deg"])
    # Posterior heel and forward ball share load; higher medial midfoot forms the arch.
    sections = [
        (-.099, .009, .009, -.054, -.071, .003, 0, 0),
        (-.094, .023, .024, -.040, -.080, .008, 0, 0),
        (-.081, .039, .041, -.020, -.089, .004, 0, 0),
        (-.054, .046, .049, -.005, -.091, .002, 0, 0),
        (-.024, .047, .051, -.002, -.087, 0, .002, 0),
        ( .008, .047, .049, -.005, -.082, 0, .009, .001),
        ( .031, .050, .048, -.011, -.080, 0, .011, .003),
        ( .057, .055, .051, -.020, -.086, 0, .005, .004),
        ( .082, .065, .058, -.029, -.089, -.002, 0, .005),
        ( .097, .068, .063, -.034, -.089, -.007, 0, .004),
        ( .110, .068, .065, -.038, -.085, -.010, 0, .003),
    ]

    # Transverse control points in millimetres. The eminence under the
    # hallux runs diagonally into the heel; four pads support the toe rays.
    plantar_relief = {
        3: (0, -1, -2, -2, -3, -2, -2, -1, 0),
        4: (-2, -5, -4, -1, 2, 0, -2, -2, 0),
        5: (-3, -7, -6, -2, 3, 1, -3, -3, -1),
        6: (-4, -9, -7, -3, 3, 1, -3, -3, -1),
        7: (-3, -7, -5, -1, 2, -1, -4, -3, -1),
        8: (0, -3, 1, -3, 1, -3, 1, -3, 0),
        9: (1, -5, 2, -5, 2, -5, 2, -4, 1),
    }

    form = _FootForm(sections, 4, ankle=(3, 6), hallux=(5, 7), plantar=plantar_relief)
    form.cuff(-.012, .032, .033, .029, .004)
    nails = []
    for i, (length, width, splay) in enumerate([
        (.091, .0173, -.072), (.099, .0172, -.023), (.095, .0164, .038), (.080, .0142, .102)
    ]):
        root = form.toe(i)
        start = form.center(root)
        forward = V(splay, 0, 1).normalized()
        # Integrate phalanx directions along the ray. The bend is distributed
        # through the two joints without folding the underside at full flexion.
        center, previous_t = start, 0.
        stations = []
        for t, flex, w, h in (
            (.14, -.15, .98, 1.01), (.32, -.08, .95, .88), (.46, .12 + .24 * curl, 1.02, .98),
            (.61, .17 + .52 * curl, .87, .78), (.74, .22 + .86 * curl, .91, .84),
            (.86, .25 + 1.08 * curl, .87, .86), (.94, .26 + 1.25 * curl, .72, .69),
            (1., .27 + 1.26 * curl, .31, .30),
        ):
            direction = forward * math.cos(flex) - UP * math.sin(flex)
            center = center + direction * ((t - previous_t) * length)
            stations.append((center, width * w, width * h))
            previous_t = t
        form.digit(root, stations)
        nail_base = stations[-3][0].lerp(stations[-2][0], .26)
        nails.append((nail_base, direction, width, .10 * length, 0.))
    root = form.hallux
    saddle = form.center(root)
    forward = V(-math.sin(angle), 0, math.cos(angle))
    joint = saddle + V(-.041, -.006, .003) + forward * .017
    distal = joint + forward * .031 - UP * (.006 + .008 * curl)
    direction = (forward + RIGHT * (.17 + .22 * curl) - UP * (.27 + .64 * curl)).normalized()
    end = distal + direction * .033
    form.digit(root, [(saddle + V(-.020, -.002, .001), .024, .026),
                      (saddle + V(-.035, -.004, .005), .023, .023),
                      (joint, .023, .022), (joint.lerp(distal, .50), .022, .020),
                      (distal, .020, .019), (distal.lerp(end, .50), .021, .019),
                      (distal.lerp(end, .83), .016, .014), (end, .007, .007)], roll=-.45)
    nails.append((distal.lerp(end, .48), direction, .023, .013, -.45))
    g.slot("skin")
    g.setup(finish="sculpt")
    form.emit(g, size)
    g.slot("detail")
    for center, axis, width, length, inward in nails:
        _ape_nail(g, center, axis, width, length, size, inward)


def _feather(g, start, end, width, thickness, size, rounded=False):
    """Cambered flight vane, with a broad inner web and a raised dorsal shaft."""
    direction = end - start
    across = UP.cross(direction).normalized()
    dorsal = direction.cross(across).normalized()
    sections = [(0, .12), (.12, .56), (.31, .91), (.55, 1), (.76, .75), (.93, .33), (1, .035)]
    if rounded:
        sections = [(0, .16), (.15, .40), (.42, .86), (.70, 1), (.87, .91), (.96, .58), (1, .11)]
    camber = max(.053 * direction.length, .26 * width) if rounded else .040 * direction.length
    vertices, faces = [], []
    for t, breadth in sections:
        arch = math.sin(math.pi * t)
        shaft = (start + direction * t + across * (.055 * direction.length * arch)
                 + dorsal * (camber * arch))
        # A slight roll leaves a shingled free edge when adjacent vanes overlap.
        for lateral, relief in [(-.84, -.14), (-.22, .45), (0, 1), (.19, .54), (1.16, .10), (0, -.50)]:
            point = (shaft + across * (lateral * breadth * width)
                     + dorsal * (relief * thickness * (.15 + .85 * breadth)
                                 + lateral * width * breadth * .13))
            vertices.append(point * size)
    for i in range(len(sections) - 1):
        for j in range(6):
            k = (j + 1) % 6
            faces.append((i * 6 + j, (i + 1) * 6 + j, (i + 1) * 6 + k, i * 6 + k))
    faces.extend([tuple(range(6)), tuple(reversed(range(len(vertices) - 6, len(vertices))))])
    g.current._add(vertices, faces)


def _wing_frame(p):
    fold = p["fold"]
    return [V(0, 0, 0), V(.16, .025, -.095), V(.38 - .07 * fold, .055, .014 - .120 * fold),
            V(.55 - .09 * fold, .059, -.055 - .13 * fold)]


# Span station, anterior depth, posterior depth, dorsal and ventral thickness.
# Humerus and ulna support the broad propatagium; the carpus rounds into the hand.
_MANTLE_STATIONS = (
    (-.105, .022, .025, .020, .017), (-.071, .045, .059, .041, .033),
    ( .012, .067, .108, .068, .045), ( .175, .079, .145, .073, .048),
    ( .320, .073, .158, .059, .042), ( .490, .062, .148, .049, .034),
    ( .600, .059, .131, .043, .030), ( .705, .064, .114, .042, .027),
    ( .790, .059, .096, .038, .024), ( .905, .048, .076, .032, .021),
    (1.005, .031, .055, .025, .017), (1.068, .019, .031, .016, .012),
    (1.100, .007, .011, .007, .006),
)


def _wing_axis(joints, u):
    """Shoulder, elbow, wrist and hand stations in the current folding pose."""
    if u < .32:
        return lerp(joints[0], joints[1], u / .32)
    if u < .705:
        return lerp(joints[1], joints[2], (u - .32) / .385)
    return lerp(joints[2], joints[3], (u - .705) / .295)


def _wing_mantle(g, joints, size):
    """One editable subdivision cage from the shoulder socket through the carpus."""
    # Support loops preserve the rounded anterior ridge and the thin posterior lip.
    section = ((1, 0), (.94, .57), (.65, .91), (.14, 1), (-.32, .82),
               (-.68, .53), (-.92, .24), (-1, .03), (-.97, -.19),
               (-.61, -.62), (-.12, -.94), (.47, -.82), (.86, -.49))
    rings = []
    for u, front, back, upper, lower in _MANTLE_STATIONS:
        axis = _wing_axis(joints, u)
        ring = [size * (axis + V(0, h * (upper if h >= 0 else lower),
                                  chord * (front if chord >= 0 else back)))
                for chord, h in section]
        rings.append(ring)
    _closed_rings(g, rings)


def wing_feathered(g, p):
    from scipy.interpolate import PchipInterpolator

    size, fold, count, slots = p["size"], p["fold"], round(p["primaries"]), p["slots"]
    joints = _wing_frame(p)
    g.setup(finish="subsurf", slot_finish={"base": "sculpt"})
    g.slot("base")
    _wing_mantle(g, joints, size)
    dimensions = PchipInterpolator([row[0] for row in _MANTLE_STATIONS],
                                   [row[1:] for row in _MANTLE_STATIONS])

    def follicle(u, chord, height):
        front, back, upper, _ = dimensions(u)
        axis = _wing_axis(joints, u)
        return axis + V(0, height * upper, chord * (front if chord >= 0 else back))

    def primary_tip(u):
        return V(lerp(.064, .92, u) - fold * .275 * u,
                 .013 - .023 * u - .010 * math.sin(math.pi * u),
                 lerp(-.345, -.29, u) - fold * (.045 + .408 * u)
                 - .035 * math.sin(math.pi * u))

    def secondary_tip(u):
        return V(lerp(-.049, .068, u), .002 - .007 * u,
                 lerp(-.207, -.352 - .035 * fold, u))

    g.slot("accent")
    for i in range(count):
        u = i / (count - 1)
        start = follicle(lerp(.40, .99, u), -.42, -.08)
        width = (.61 / count) * lerp(1.19, .86, slots) * lerp(1, .88, u)
        _feather(g, start, primary_tip(u), width, .0145, size)
    for i in range(6):
        u = i / 5
        start = follicle(lerp(.025, .42, u), -.40, -.14)
        _feather(g, start, secondary_tip(u), lerp(.043, .047, u), .013, size, rounded=True)

    g.slot("detail")
    for number, reach, chord, root_height, width in [(9, .67, .16, .72, .053),
                                                     (7, .42, .49, .77, .050)]:
        for i in range(number):
            u = i / (number - 1)
            station = lerp(.015, .98, u)
            start = follicle(station, chord, root_height)
            tip = secondary_tip(u / .39) if u < .39 else primary_tip((u - .39) / .61)
            end = lerp(start, tip, reach)
            end.y += (.019 if number == 9 else .030) * (1 - .40 * u)
            _feather(g, start, end, width * (1 - .12 * u), .013, size, rounded=True)


def _closed_rings(g, rings):
    """Join parallel closed cross sections. Wind outward in either local frame."""
    n = len(rings[0])
    verts = [v for ring in rings for v in ring]
    faces = [tuple(reversed(range(n)))]
    for i in range(len(rings) - 1):
        for j in range(n):
            k = (j + 1) % n
            faces.append((i * n + j, i * n + k, (i + 1) * n + k, (i + 1) * n + j))
    faces.append(tuple(range(len(verts) - n, len(verts))))
    volume = 0.
    for face in faces:
        a = verts[face[0]]
        for j in range(1, len(face) - 1):
            volume += a.dot(verts[face[j]].cross(verts[face[j + 1]]))
    if volume < 0:
        faces = [tuple(reversed(face)) for face in faces]
    g.current._add(verts, faces)


def elytron(g, p):
    s, dome = p["size"], p["dome"]
    vault = p.get("vault", 0.0)
    hinge = rot(BACK, math.radians(p["open_deg"]))
    rings = []
    # A straight sutural edge, opposed by the bowed lateral margin of the case.
    for z, width, crown in [(.015, .015, .012), (0, .080, .030), (-.045, .17, .073),
                            (-.15, .25, .121), (-.29, .274, .127), (-.43, .24, .108),
                            (-.54, .173, .074), (-.615, .078, .036), (-.63, .012, .01)]:
        ring = []
        for j in range(20):
            a = math.tau * j / 20
            x = width * .5 * (1 - math.cos(a))
            arch = math.sin(a)
            across = x / width
            y = arch * (crown * dome if arch >= 0 else .014) + .009 * (1 - across)
            if vault:
                # The sutural edge sits near the crown and the outer rim
                # drops towards the flank, joining the two cases into a dome.
                shoulder = crown * dome * (.58 - 1.07 * across ** 1.55)
                thickness = arch * (crown * dome * .27 if arch >= 0 else .024)
                y = lerp(y, shoulder + thickness, vault)
            ring.append(hinge @ V(x, y, z) * s)
        rings.append(ring)
    g.setup(finish="subsurf")
    g.slot("base")
    _closed_rings(g, rings)


def wing_membrane_insect(g, p):
    s, fold, veins = p["size"], p["fold"], round(p["veins"])
    a = math.radians(13 + 62 * fold)
    length = V(math.cos(a), .07, -math.sin(a))
    chord = V(-math.sin(a), 0, -math.cos(a))
    # Each cross section supplies the surface height for its branching veins.
    sections = [(0, .010), (.08, .023), (.24, .057), (.45, .10), (.65, .15),
              (.80, .165), (.91, .125), (.975, .068), (1, .009)]
    def surface(t, w, u):
        arch = math.sqrt(max(0, 1 - u * u))
        return length * (.67 * t) + chord * (w * u + .025 * math.sin(math.pi * t)) + UP * (.009 * arch)
    g.slot("base")
    g.setup(finish="subsurf")
    rings = []
    for t, w in sections:
        ring = []
        for j in range(14):
            a = math.tau * j / 14
            point = surface(t, w, math.cos(a))
            if j > 7:
                point -= UP * (.017 * abs(math.sin(a)))
            ring.append(point * s)
        rings.append(ring)
    _closed_rings(g, rings)
    g.slot("detail")
    for i in range(veins):
        u = lerp(-.82, .82, i / max(1, veins - 1)) if veins > 1 else 0
        route = [surface(t, w, u * min(1, t * 3) + .055 * math.sin(math.tau * t)) for t, w in sections[:-1]]
        _tube(g, route, [.0065, .0065, .0057, .005, .0043, .0034, .002, .001], s,
              sides=7, density=1)
        if i % 2 == 1:
            branch = [surface(t, w, min(.97, u + .27 * (t - .45) / .5)) for t, w in sections[3:-1]]
            _tube(g, branch, [.0038, .0032, .0025, .0017, .0009], s, sides=7, density=1)


def fin_paired(g, p):
    s, sweep = p["size"], p["sweep"]
    droop = math.radians(p["droop_deg"])
    rings = []
    for t, front, back, h in [(0, .120, -.122, .043), (.035, .13, -.14, .045),
                              (.16, .125, -.131, .043), (.38, .101, -.101, .035),
                              (.61, .066, -.072, .025), (.85, .018, -.05, .016),
                              (.98, -.03, -.049, .006), (1, -.04, -.045, .002)]:
        ring = []
        for j in range(14):
            a = math.tau * j / 14
            z = lerp(back, front, .5 * (1 + math.cos(a))) - t * t * (.10 + .22 * sweep)
            ring.append(V(.54 * t * math.cos(droop), -.54 * t * math.sin(droop) + h * math.sin(a), z) * s)
        rings.append(ring)
    g.setup(finish="subsurf")
    g.slot("base")
    _closed_rings(g, rings)


def _vertical_foil(g, sections, size):
    rings = []
    for y, front, rear, width in sections:
        ring = []
        for j in range(14):
            a = math.tau * j / 14
            # Slightly forward maximum thickness gives the leading edge a round nose.
            x = width * math.sin(a) * (1 + .23 * math.cos(a))
            ring.append(V(x, y, lerp(rear, front, (1 + math.cos(a)) * .5)) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def fin_median(g, p):
    s, sweep = p["size"], p["sweep"]
    sign = -1 if round(p["ventral"]) else 1
    stations = [(-.018, .19, -.225, .039), (.004, .207, -.24, .041), (.041, .17, -.188, .037),
              (.12, .116, -.134, .031), (.22, .046, -.105, .024), (.33, -.022, -.091, .017),
              (.412, -.067, -.095, .009), (.44, -.096, -.101, .002)]
    sections = []
    for y, front, rear, width in stations:
        shift = (max(0, y) / .44)**1.6 * .14 * sweep
        sections.append((y * sign, front - shift, rear - shift, width))
    g.setup(finish="subsurf")
    g.slot("base")
    _vertical_foil(g, sections, s)


def tail_fin_heterocercal(g, p):
    s, ratio, fork = p["size"], p["upper_lobe"], p["fork"]
    upper = .25 * ratio
    # The inner fork follows the trailing contour; dorsal lobe carries the spine.
    stations = [(-.25, -.348, -.355, .003), (-.226, -.274, -.333, .012),
              (-.152, -.185, -.285, .019), (-.071, -.119, -.247, .028),
              (-.040, -.059, -.220, .034), (0, -.046, -.27 + .135 * fork, .041),
              (.040, -.060, -.217, .035), (.19 * upper, -.084, -.232, .030),
              (.46 * upper, -.205, -.323, .023), (.73 * upper, -.323, -.412, .016),
              (.92 * upper, -.421, -.469, .008), (upper, -.478, -.484, .002)]
    g.slot("base")
    g.setup(voxel=.0033 * s, detail=1.4)
    _vertical_foil(g, stations, s)
    # The peduncle flares into the base of both lobes.
    _tube(g, [(0, 0, .018), (0, 0, -.038), (0, 0, -.098), (0, .004, -.159)],
          [(.038, .046), (.035, .044), (.035, .058), (.026, .073)], s, sides=20)


def tail_feather_fan(g, p):
    s, count, angle = p["size"], round(p["feathers"]), math.radians(p["spread_deg"]) * .5
    g.setup(finish="subsurf")
    for layer, (n, length, depth) in enumerate([(count, .60, 0), (max(5, count // 2 + 1), .352, .013)]):
        g.slot("accent" if layer == 0 else "detail")
        for i in range(n):
            u = 2 * i / (n - 1) - 1
            a = u * angle
            d = V(math.sin(a), 0, -math.cos(a))
            start = V(u * .017, depth + .004 * (1 - u), 0)
            end = start + d * (length * (1 - .12 * u * u)) + UP * (.018 - .013 * u * u)
            # The terminal contour of a rectrix is rounded, unlike a primary.
            step = end - start
            widths = [.002, .013, .026, .039, .043, .031, .007]
            chord = (1 + .23 * (angle - .35)) * (1 if layer == 0 else .77)
            sections = [(w * chord, .009 if 0 < t < 1 else .0025)
                      for t, w in zip([0, .17, .4, .65, .86, .96, 1], widths)]
            # Subtle shingling keeps coincident fan surfaces apart.
            path = [start + step * t + UP * (.012 * math.sin(math.pi * t) + .015 * u * t)
                  for t in (0, .17, .4, .65, .86, .96, 1)]
            _tube(g, path, sections, s, sides=8, density=1)


def _tail_profile(p):
    paths = [V(x, y, z) for x, y, z in [(0, 0, 0), (.012, -.006, -.14), (.038, -.060, -.30),
                                     (.054, -.095, -.47), (.042, -.052, -.63), (.014, .032, -.80)]]
    radii = []
    for i in range(len(paths)):
        t = i / (len(paths) - 1)
        volume = .063 * (lerp(1, p["taper"], t) + .64 * p["brush"] * math.sin(math.pi * t)**.75)
        radii.append((volume * (1 - .59 * p["compress"]), volume * (1 + .30 * p["compress"])))
    return paths, radii


def tail_flexible(g, p):
    path, radii = _tail_profile(p)
    end = path[-1]
    ext = (end - path[-2]).normalized()
    w, h = radii[-1]
    g.slot("skin")
    g.setup(finish="subsurf")
    _tube(g, path + [end + ext * w * .65, end + ext * w * .87], radii + [(w * .66, h * .66), (w * .15, h * .15)],
          p["size"], sides=12, density=2)


def siphon(g, p):
    s = p["size"]
    a = math.radians(p["aim_deg"])
    # A single continuous surface runs along the exterior, over the lip, and
    # down the lumen. Both apertures remain open, also in the base cage.
    centers = [V(0, .015, -.015), V(0, .001, .012), V(0, -.024, .079), V(0, -.026, .140)]
    tangent = V(0, math.sin(a), math.cos(a))
    centers += [centers[-1] + (BACK + tangent).normalized() * .066,
                centers[-1] + (BACK + tangent).normalized() * .066 + tangent * .07]
    widths = [.099, .097, .066, .055, .048, .043]
    rings = []
    for i, (c, w) in enumerate(zip(centers, widths)):
        direction = (centers[min(i + 1, len(centers) - 1)] - centers[max(i - 1, 0)]).normalized()
        up = direction.cross(RIGHT)
        rings.append((c, up, w))
    order = [(i, w) for i, (_, _, w) in enumerate(rings)]
    order += [(i, .78 * w) for i, (_, _, w) in reversed(list(enumerate(rings)))]
    n = 16
    verts = []
    for i, w in order:
        c, up, _ = rings[i]
        for j in range(n):
            a = math.tau * j / n
            verts.append((c + RIGHT * w * math.cos(a) + up * w * math.sin(a)) * s)
    faces = []
    for i in range(len(order)):
        k = (i + 1) % len(order)
        for j in range(n):
            m = (j + 1) % n
            faces.append((i * n + j, i * n + m, k * n + m, k * n + j))
    g.setup(finish="subsurf")
    g.slot("base")
    g.current._add(verts, faces)


def web_interbrachial(g, p):
    depth, scallop, s = p["depth"], p["scallop"], p["size"]
    n = 96
    rings = []
    # The web hangs distal to the central mount, between the eight arm bases.
    # Radial ribs and intervening membrane share their vertices at the rim.
    radius = .32 + .22 * depth
    sections = [(.009, .054), (.09, .050), (.16, .039), (.23, .012), (.38, -.031), (.64, -.077),
              (.89, -.118), (1, -.131), (1, -.148), (.87, -.142), (.60, -.101),
              (.32, -.053), (.08, -.024), (.009, -.022)]
    for idx, (t, y) in enumerate(sections):
        ring = []
        for j in range(n):
            a = math.tau * j / n
            rib = (.5 + .5 * math.cos(8 * a))**6
            scalloped = (1 - rib**.35) * (.08 + .23 * scallop)
            r = radius * t * (1 - scalloped * t**2)
            lift = (.011 * rib * t if idx <= 7 else .005 * rib * t)
            ring.append(V(r * math.cos(a), y + lift, r * math.sin(a)) * s)
        rings.append(ring)
    g.slot("skin")
    g.setup(voxel=.004 * s, detail=1.4)
    _closed_rings(g, rings)
    for i in range(8):
        angle = math.tau * i / 8
        direction = V(math.cos(angle), 0, math.sin(angle))
        # Low muscular arm bases strengthen the narrow edge of each sector.
        spine = [direction * radius * t + UP * y for t, y in
                 ((.035, .015), (.18, .014), (.38, -.023), (.65, -.063), (.89, -.101), (1.025, -.111))]
        _tube(g, spine, [.037, .032, .023, .0175, .0175, .018], s, sides=12, density=2)


def bell_radial(g, p):
    s, count = p["size"], round(p["lobes"])
    radius = .40
    height = radius * p["dome"]
    # Clearer mesoglea has a thinner wall; a concave subumbrella and a
    # continuous coronal rim are present across the full thickness range.
    wall = lerp(.105, .052, p["translucent"])
    profile = [(.01, height), (.20, height * .985), (.43, height * .91), (.63, height * .77),
             (.79, height * .60), (.91, height * .36), (.987, height * .13), (1, .005),
             (.990, -.007), (.956, -.012), (.91, height * .13 - wall * .27),
             (.82, height * .42 - wall * .53), (.66, height * .67 - wall * .83),
             (.43, height * .87 - wall), (.20, height * .97 - wall), (.01, height - wall)]
    n = max(64, count * 8)
    rings = []
    for r, y in profile:
        ring = []
        for j in range(n):
            a = math.tau * j / n
            lobe = math.cos(count * a)
            rad = radius * r * (1 + .034 * lobe * r**4)
            rim_y = y - .029 * lobe * r**5
            ring.append(V(rad * math.cos(a), rim_y, rad * math.sin(a)) * s)
        rings.append(ring)
    g.setup(finish="subsurf")
    g.slot("skin")
    _closed_rings(g, rings)


def _chain(positions, radii, size, motion):
    return {"segments": [list((b - a) * size) for a, b in zip(positions, positions[1:])],
            "radii": [r * size for r in radii], "motion": motion}


def feathered_wing_preset(p):
    return _chain(_wing_frame(p), [.048, .045, .033, .021], p["size"], "auto")


def flexible_tail_preset(p):
    path, radii = _tail_profile(p)
    return _chain(path, [math.sqrt(w * h) for w, h in radii], p["size"], "tail")


BUILDERS = {build.__name__: build for build in (
    paw_padded, foot_webbed_long, foot_grasping, wing_feathered, elytron,
    wing_membrane_insect, fin_paired, fin_median, tail_fin_heterocercal,
    tail_feather_fan, tail_flexible, siphon, web_interbrachial, bell_radial,
)}
OVERRIDES = {
    "paw_padded": {"cap": "foot"},
    "foot_webbed_long": {"cap": "foot"},
    "foot_grasping": {"cap": "foot"},
    "wing_feathered": {"cap": "flap"},
    "wing_membrane_insect": {"cap": "flap"},
    "fin_paired": {"cap": "paddle"},
}
PRESETS = {"wing_feathered": feathered_wing_preset, "tail_flexible": flexible_tail_preset}
EXTRA_PARAMS = {"elytron": {"vault": (0.0, 1.0, 0.0)}}
