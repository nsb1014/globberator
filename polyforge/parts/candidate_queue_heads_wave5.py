"""Source-backed head attachment drafts for independent inspection."""

from math import cos, pi, radians, sin

from ..kit import BACK, RIGHT, UP, V, rot
from . import Part
from .anatomy import _loft
from .research_aesthetics import _closed_sections

SIZE = (.65, 1.65, 1.)
FRONT = {"u": .94, "theta": -90}
SIDE = {"u": .91, "theta": 0}


def _paired_sided_sections(g, sections, size):
    """Cap a sweep whose two strips meet along matching parametric edges."""
    count = len(sections[0])
    verts = [V(p) * size for section in sections for p in section]
    faces = []
    for row in range(len(sections) - 1):
        base = row * count
        for i in range(count):
            nxt = (i + 1) % count
            faces.append((base + i, base + count + i, base + count + nxt, base + nxt))
    end = (len(sections) - 1) * count
    for i in range(count // 2 - 1):
        face = (i, i + 1, count - 2 - i, count - 1 - i)
        faces.append(face)
        faces.append(tuple(end + index for index in reversed(face)))
    g._add(verts, faces)


def valved_dorsal_spiracle(g, p):
    """A dorsal spiracular inlet with a recessed hinged valve flap."""
    size, aperture, opening = p["size"], p["aperture"], p["open_deg"]
    stations = ((-.048, .023, .018), (-.037, .040, .028), (-.021, .052, .035),
                (-.006, .051, .034), (.007, .044, .026), (.011, .038, .021),
                (.009, .031, .017), (.001, .027, .016), (-.012, .025, .015),
                (-.029, .019, .010), (-.044, .012, .007))
    angles = [pi / 2 - 2 * pi * i / 52 for i in range(52)]
    g.setup(finish="direct")
    rings = []
    for index, (z, w, h) in enumerate(stations):
        a = aperture if index >= 5 else 1
        rings.append([(w * a * cos(t) - .18 * h * a * sin(t),
                       h * a * sin(t) * (1 - .17 * cos(t)),
                       z - .19 * w * cos(t))
                      for t in angles])
    _closed_sections(g, rings, (0, 0, -.052), (0, 0, -.047), size)

    pivot = V(.004, .014 * aperture, -.003)
    g.pivots["gate"] = pivot * size
    g.use("gate")
    g.setup(finish="subsurf_low")
    turn = rot(RIGHT, -radians(opening))
    profile = ((-.021, .013, -.003), (.014, .016, -.003), (.025, .006, -.004),
               (.021, -.006, -.005), (.008, -.014, -.005), (-.008, -.015, -.004),
               (-.022, -.010, -.004), (-.027, .000, -.004))
    rim = [size * (pivot + turn @ (V(x * aperture, y * aperture, z) - pivot))
           for x, y, z in profile]
    g.slab(rim, turn @ BACK, .006 * size, bulge=.48)


def paired_mobile_mandibular_rami(g, p):
    """Two bowed mandibular pieces with independent advances and an elastic bridge."""
    size, spread, advance = p["size"], p["spread_deg"], p["advance"]
    stations = ((-.071, .057, -.006, .017, .016), (-.043, .060, -.014, .017, .014),
                (.002, .054, -.023, .015, .013), (.045, .046, -.026, .013, .011),
                (.089, .038, -.023, .011, .009), (.135, .026, -.015, .009, .008),
                (.166, .015, -.008, .007, .006), (.178, .010, -.005, .004, .004))
    tips = []
    for side, bone in ((-1, "left_ramus"), (1, "right_ramus")):
        pivot = V(side * .058, -.006, -.066)
        g.pivots[bone] = pivot * size
        g.use(bone)
        g.setup(finish="direct")
        turn = rot(UP, side * radians(spread))

        def place(x, y, z):
            shift = .036 * advance * ((side + 1) / 2 + .12) * max(0, (z + .07) / .248)
            return pivot + turn @ (V(side * x, y, z + shift) - pivot)

        centerline = [place(x, y, z) for z, x, y, _, _ in stations]
        _loft(g, size, centerline, [(d, h) for _, _, _, d, h in stations], up=UP,
              sides=24, density=5, exponent=.78)
        tips.append(centerline[-1])
        for index in range(7):
            first = centerline[index]
            second = centerline[index + 1]
            for fraction in (.26, .75):
                seat = first.lerp(second, fraction) + V(0, .0085 - .00065 * index, 0)
                length = .012 - .00075 * index
                tip = seat + V(-side * .002, length, -.004)
                _loft(g, size, [seat - .004 * UP, seat + .42 * (tip - seat), tip],
                      [(.0028, .0024), (.0022, .0019), (.00065, .00070)], sides=8, density=1)
    g.use("self")
    g.setup(finish="direct")
    a, b = tips
    middle = (a + b) / 2 - V(0, .009, .002)
    _loft(g, size, [a - .002 * (b - a).normalized(), a.lerp(middle, .45),
                     middle, middle.lerp(b, .55), b + .002 * (b - a).normalized()],
          [(.0035, .0040), (.0035, .0032), (.0032, .0030), (.0035, .0032), (.0035, .0040)],
          up=UP, sides=14, density=5)


def oral_jet_nozzle(g, p):
    """Lengthwise palatal channel over the movable hyoid insert."""
    size, width, gape = p["size"], p["width"], p["gape"]
    stations = ((-.061, .025, .010, .010), (-.043, .032, .012, .009),
                (-.020, .041, .016, .008), (.008, .040, .015, .0065),
                (.030, .035, .010, .0055), (.055, .025, .008, .0045),
                (.074, .016, .005, .0042), (.084, .011, .003, .0038))
    sections = []
    for z, plate, reach, groove in stations:
        outer = []
        inner = []
        for i in range(37):
            x = -cos(pi * i / 36)
            y = .006 + .008 * max(0., 1 - x * x) ** .7
            channel = reach * max(0., 1 - (x * .45 * plate / groove) ** 2) ** 1.8
            outer.append((x * width * plate, y - .008 * x * x, z))
            inner.append((x * width * plate, -.010 + channel + .003 * x * x, z))
        sections.append(outer + list(reversed(inner)))
    g.setup(finish="subsurf_low")
    _paired_sided_sections(g, sections, size)

    g.pivots["basihyal"] = V(0, -.032, -.048) * size
    g.use("basihyal")
    g.setup(finish="direct")
    _loft(g, size, [(0, -.034, -.053), (0, -.032, -.035), (0, -.035, -.007),
                     (0, -.034, .020), (0, -.035, .047), (0, -.033, .065),
                     (0, -.029, .076)],
          [(.011, .008), (.022, .021), (.023, .014), (.019, .010),
           (.014, .009), (.009, .006), (.004, .004)],
          up=UP, sides=32, density=5, exponent=.73)
    for vertex in g.prims[-1].v:
        x, y, z = vertex / size
        vertex.y -= size * gape * max(0, z + .051)
        if y > -.026 and z > -.008:
            # Round off the oral-facing center of the receiving surface.
            vertex.y -= size * .006 * max(0, 1 - (x / .010) ** 2)


def externally_opening_cheek_pouch(g, p):
    """External cheek opening with a narrow neck and blind soft-tissue pocket."""
    size, fill, turn_out = p["size"], p["fill"], p["evert"]
    stations = ((-.103, .011, .009), (-.094, .025, .017), (-.079, .037, .028),
                (-.055, .044, .032), (-.030, .037, .027), (-.010, .025, .019),
                (.005, .020, .018), (.013, .017, .015), (.016, .013, .011),
                (.012, .010, .008), (-.010, .013, .011), (-.030, .022, .015),
                (-.051, .030, .021), (-.071, .027, .018), (-.089, .017, .012),
                (-.098, .007, .005))
    angles = [pi / 2 - 2 * pi * i / 56 for i in range(56)]
    # Past the aperture the pouch follows the lateral cheek, with optional
    # forward displacement as a simple inspection pose.
    def point(w, h, z, a):
        depth = max(0., -z / .103)
        broad = .72 + .28 * fill if z < -.010 else 1
        return (.062 * depth + w * broad * cos(a),
                -.025 * depth + h * broad * sin(a),
                z * (1 - .55 * turn_out) + .018 * depth * turn_out - .17 * w * cos(a))

    g.setup(finish="direct")
    rings = [[point(w, h, z, a) for a in angles] for z, w, h in stations]
    _closed_sections(g, rings, point(0, 0, -.107, 0), point(0, 0, -.100, 0), size)


def paired_nectar_trapping_tongue(g, p):
    """A bifid tongue with two open grooves and separate closing distal lamellae."""
    size, fork, open_tips = p["size"], p["fork"], p["tip_open"]
    g.setup(finish="direct")
    _loft(g, size, [(0, 0, -.049), (0, 0, -.039), (0, -.001, -.021),
                     (0, -.002, .002), (0, -.004, .028)],
          [(.007, .005), (.009, .006), (.010, .006), (.009, .005), (.006, .004)],
          up=UP, sides=20, density=4)
    positions = (.007, .021, .035, .051, .069, .087, .103, .114, .122)
    for side in (-1, 1):
        sections = []
        for z in positions:
            t = (z - .007) / .115
            x_mid = side * (.004 + fork * .018 * t)
            y_mid = -.003 + .004 * t ** 2
            radius = (.0055 - .0026 * t ** 2) * (1 - .33 * open_tips * t)
            angle = (.69 + .23 * t - .35 * open_tips * t) * pi
            a = [3 * pi / 2 + angle - 2 * angle * index / 22 for index in range(23)]
            surface = [(x_mid + cos(phi) * radius, y_mid + sin(phi) * radius, z) for phi in a]
            lining = [(x_mid + cos(phi) * (radius - .0012),
                        y_mid + sin(phi) * (radius - .0012), z) for phi in reversed(a)]
            sections.append(surface + lining)
        _paired_sided_sections(g, sections, size)
        for index in range(9):
            z = .079 + .0045 * index
            t = (z - .007) / .115
            x_mid = side * (.004 + fork * .018 * t)
            y_mid = -.003 + .004 * t * t
            radius = (.0055 - .0026 * t ** 2) * (1 - .33 * open_tips * t)
            angle = (.69 + .23 * t - .35 * open_tips * t) * pi
            for sign in (-1, 1):
                phi = 3 * pi / 2 + sign * angle
                x = x_mid + radius * cos(phi)
                y = y_mid + radius * sin(phi)
                _loft(g, size, [(x, y, z), (x + sign * .002, y + .003, z + .0010),
                                 (x + sign * (.006 * open_tips - .003), y + .0039, z + .0019)],
                      [(.00125, .0010), (.0011, .0007), (.00036, .00032)],
                      sides=7, density=2)


PARTS = [
    Part("valved_dorsal_spiracle", "sensory", "Dorsal inlet and recessed valve with an independent hinge.",
         ["skate", "spiracle", "respiration", "intake valve"],
         {"size": SIZE, "aperture": (.82, 1.22, 1.), "open_deg": (0., 36., 20.)},
         valved_dorsal_spiracle, orient="forward", mirror=True, hint=SIDE, symmetry="pair",
         bones=[{"name": "gate", "pivot": (.004, .014, -.003), "axis": (1, 0, 0), "angle": -16}]),
    Part("paired_mobile_mandibular_rami", "feeding", "Separate forward-swept jaw rami connected by a compliant anterior bridge.",
         ["snake", "python", "mandible", "mobile rami"],
         {"size": SIZE, "spread_deg": (0., 20., 7.), "advance": (0., 1., .30)},
         paired_mobile_mandibular_rami, orient="native", hint=FRONT, symmetry="center",
         bones=[{"name": "left_ramus", "pivot": (-.058, -.006, -.066), "axis": (0, 1, 0), "angle": -12},
                {"name": "right_ramus", "pivot": (.058, -.006, -.066), "axis": (0, 1, 0), "angle": 12}]),
    Part("oral_jet_nozzle", "feeding", "Narrow palatal groove opposing a raised movable basihyal.",
         ["archerfish", "palatal groove", "basihyal", "oral nozzle"],
         {"size": SIZE, "width": (.83, 1.18, 1.), "gape": (.02, .22, .10)},
         oral_jet_nozzle, orient="native", hint=FRONT, symmetry="center",
         bones=[{"name": "basihyal", "pivot": (0, -.032, -.048), "axis": (1, 0, 0), "angle": 8}]),
    Part("externally_opening_cheek_pouch", "feeding", "External cheek aperture leading to a blind storage pocket.",
         ["gopher", "cheek pouch", "food storage", "pocket"],
         {"size": SIZE, "fill": (0., 1., .65), "evert": (0., .78, .20)},
         externally_opening_cheek_pouch, orient="forward", mirror=True, hint=SIDE, symmetry="pair"),
    Part("paired_nectar_trapping_tongue", "feeding", "Bifid grooved tongue with a compliant distal lamellar fringe.",
         ["hummingbird", "tongue", "nectar", "lamellae"],
         {"size": SIZE, "fork": (.60, 1.27, 1.), "tip_open": (0., 1., .45)},
         paired_nectar_trapping_tongue, orient="native", hint=FRONT, symmetry="center"),
]
TRAITS = {
    "valved_dorsal_spiracle": {"function": "breathe", "construction": "rigid", "shape": "slanted inlet with a recessed valve"},
    "paired_mobile_mandibular_rami": {"function": "feed", "construction": "rigid", "shape": "separately moving jaw rami joined by a soft bridge"},
    "oral_jet_nozzle": {"function": "feed", "construction": "rigid", "shape": "palatal groove over a spaced basihyal"},
    "externally_opening_cheek_pouch": {"function": "feed", "construction": "deformable", "shape": "side opening and blind storage pocket"},
    "paired_nectar_trapping_tongue": {"function": "feed", "construction": "deformable", "shape": "paired C-section tongue grooves with fringed tips"},
}
