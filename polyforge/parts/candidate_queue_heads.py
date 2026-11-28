"""Isolated vertebrate oral, respiratory, sensory and display anatomy drafts."""

from math import cos, pi, sin, radians

from ..kit import BACK, RIGHT, UP, V, rot
from . import Part
from .anatomy import _loft
from .research_aesthetics import _closed_sections

SIZE = (.65, 1.65, 1.)
FRONT = {"u": .91, "theta": -90}
SIDE = {"u": .91, "theta": 0}
CROWN = {"u": .99, "theta": 90}


def hinged_gill_cover(g, p):
    """One arched cheek plate with its anterior edge fixed at the hinge."""
    scale, spread = p["size"], p["width"]
    # Viewed along the anatomical lateral axis, anterior is toward +Z.
    perimeter = ((-.006, .101, .042), (.025, .092, -.018), (.062, .066, -.087),
                 (.066, .065, -.115), (.069, .053, -.139), (.068, .037, -.140),
                 (.063, .026, -.119), (.058, .012, -.113), (.048, -.018, -.100),
                 (.033, -.057, -.083), (.015, -.090, -.044), (-.005, -.086, .019),
                 (-.009, -.061, .037), (-.008, -.021, .043), (-.008, .036, .043),
                 (-.007, .079, .043))
    pivot = V(-.010, 0, .041)
    g.pivots["operculum"] = pivot * scale
    g.setup(finish="direct")
    g.oval(V(-.014, .001, .039) * scale, (.012 * scale, .080 * scale, .012 * scale),
           segs=26, rings=16)
    g.use("operculum")
    g.setup(finish="subsurf_low")
    rotate = rot(UP, -radians(p["open_deg"]))
    outline = [scale * (pivot + rotate @ (V(x, y, pivot.z + (z - pivot.z) * spread) - pivot))
               for x, y, z in perimeter]
    g.slab(outline, rotate @ RIGHT, .018 * scale, bulge=.82)


def bill_edge_filter(g, p):
    """Short opposing jaw rims bearing staggered coarse marginal lamellae."""
    scale, count, gape = p["size"], round(p["lamellae"]), p["gape"]
    rail = ((.046, .022, -.052), (.058, .018, -.021), (.061, .008, .020),
            (.056, -.009, .060), (.047, -.025, .098), (.032, -.036, .126),
            (.021, -.041, .145))
    for bone, up in (("self", 1), ("jaw", -1)):
        g.use(bone)
        g.setup(finish="direct")
        g.pivots["jaw"] = V(0, 0, -.052) * scale
        for side in (-1, 1):
            _loft(g, scale, [(side * x, y + up * (.014 + gape * (z + .06)), z) for x, y, z in rail],
                  [(k, .61 * k) for k in (.007, .012, .014, .014, .013, .011, .005)],
                  up=UP, sides=16, density=4)
            step = (len(rail) - 1) / (count + 1)
            for index in range(count):
                t = (index + (1.2 if up > 0 else .68)) * step
                station = int(t)
                a, b = V(rail[station]), V(rail[station + 1])
                x, y, z = a.lerp(b, t - station)
                base = y + up * (.011 + gape * (z + .06))
                height = (.010 + .009 * sin(pi * t / 6)) * (1 if up > 0 else .75)
                outline = [(side * x, base + up * .004, z), (side * (x + .005), base - up * .003, z),
                           (side * (x + .005), base - up * height * .75, z + .0012),
                           (side * (x + .001), base - up * height, z + .0021),
                           (side * (x - .004), base - up * height * .75, z + .001),
                           (side * (x - .005), base + up * .004, z)]
                g.slab([V(point) * scale for point in outline], BACK, .0024 * scale, bulge=.25)


def annular_suction_mouth(g, p):
    """An annular flaring oral cup with circlet teeth and a recessed center."""
    scale, flare, depth = p["size"], p["flare"], p["depth"]
    stations = ((-.057, .023), (-.047, .045), (-.026, .062), (-.009, .079),
                (.012, .101), (.041, .123), (.063, .137), (.072, .138),
                (.079, .129), (.074, .118), (.064, .105), (.052, .081),
                (.032, .053), (.016, .035), (.010, .023), (.010, .010))

    def oral_position(radius, z, a):
        # The disc is slightly oval and lower rim projects farther in profile.
        return (flare * radius * cos(a), flare * radius * 1.06 * sin(a),
                depth * (z - .10 * radius * sin(a)))

    angles = [pi / 2 - 2 * pi * i / 64 for i in range(64)]
    g.setup(finish="direct")
    rings = [[oral_position(radius, z, a) for a in angles] for z, radius in stations]
    _closed_sections(g, rings, (0, 0, -.063 * depth), (0, 0, .010 * depth), scale)
    for radius, bed, count, length in ((.036, .018, 9, .016), (.061, .037, 15, .017),
                                       (.087, .055, 23, .012), (.107, .065, 33, .008)):
        for index in range(count):
            a = 2 * pi * (index + .3) / count
            base = V(oral_position(radius, bed, a))
            inward = V(-cos(a), -sin(a), 0)
            _loft(g, scale, [base, base + .36 * length * (BACK + .24 * inward),
                             base + length * (.85 * BACK + .45 * inward)],
                  [(length * .22, length * .24), (length * .18, length * .16),
                   (length * .035, length * .033)], sides=7, density=1)
    for index in range(46):
        a = 2 * pi * (index + .5) / 46
        radial = V(cos(a), sin(a), 0)
        base = V(oral_position(.130, .075, a))
        _loft(g, scale, [base - .003 * BACK, base + .002 * (radial + BACK),
                         base + .005 * (.7 * radial + BACK)],
              [(.0019, .0019), (.0016, .0014), (.00055, .00065)], sides=6, density=1)


def crossed_bill_tips(g, p):
    """Opposing curved ramphothecae with lateral overlap in the closed pose."""
    scale, twist, gape = p["size"], p["crossing"], p["gape_deg"]
    upper = ((-.017, 0, .020, .027, .018), (0, 0, .022, .036, .021),
             (.027, .002, .021, .030, .019), (.057, .009, .019, .022, .015),
             (.078, .024, .006, .013, .011), (.098, .028, -.014, .008, .007),
             (.111, .027, -.044, .0035, .0033), (.113, .028, -.048, .0012, .0014))
    lower = ((-.017, 0, -.022, .028, .018), (0, 0, -.025, .031, .018),
             (.031, -.002, -.022, .027, .015), (.050, -.009, -.022, .021, .013),
             (.074, -.022, -.008, .012, .008), (.090, -.028, .012, .007, .005),
             (.102, -.026, .029, .0028, .0026), (.104, -.027, .032, .0011, .0012))
    jaw = V(0, -.015, -.016)
    g.pivots["jaw"] = jaw * scale
    for name, stations in (("self", upper), ("jaw", lower)):
        g.use(name)
        g.setup(finish="direct")
        rotation = rot(RIGHT, radians(gape) if name == "jaw" else 0)
        _loft(g, scale, [jaw + rotation @ (V(x * twist, y, z) - jaw) for z, x, y, _, _ in stations],
              [(w, d) for _, _, _, w, d in stations], up=UP, sides=28, density=5, exponent=.77)


def deployable_feather_crown(g, p):
    """Paired overlapping, forward-curving crown feathers with sweep control."""
    scale, raised, reach = p["size"], p["deploy"], p["reach"]
    g.setup(finish="direct")
    roots = ((.010, -.004, -.052, .084, 3), (.014, .001, -.033, .118, -5),
             (.020, .006, -.014, .146, -15), (.023, .004, .006, .124, -23))
    feather = ((0, -.010, 0), (.021, .10, -.038), (.034, .36, -.064),
               (.034, .65, -.008), (.027, .85, .104), (.012, .98, .207), (.006, 1, .234))
    for side in (-1, 1):
        for root_x, root_y, root_z, length, fan in roots:
            root = V(root_x * side, root_y, root_z)
            rotation = rot(RIGHT, -radians(77 - raised * (67 - fan)))
            _loft(g, scale,
                  [root + rotation @ (V(side * x, y, z) * length * reach) for x, y, z in feather],
                  [(length * reach * w, length * reach * d) for w, d in
                   ((.041, .021), (.079, .022), (.097, .025), (.085, .023), (.058, .018),
                    (.022, .011), (.007, .005))],
                  up=BACK, sides=18, density=5, exponent=.77)


def rotating_ocular_turret(g, p):
    """A co-rotating round eyelid with a small forward eye aperture."""
    scale, yaw, pitch = p["size"], p["yaw_deg"], p["pitch_deg"]
    g.setup(finish="direct")
    # Fixed basal collar keeps the attachment invariant while the visible lid turns.
    g.oval(V(0, 0, -.010) * scale, (.058 * scale, .052 * scale, .031 * scale),
           segs=38, rings=22)
    pivot = V(0, 0, -.009)
    g.pivots["turret"] = pivot * scale
    g.use("turret")
    g.setup(finish="direct")
    stations = ((-.043, .013), (-.039, .032), (-.029, .046), (-.011, .054),
                (.011, .052), (.029, .043), (.044, .032), (.051, .025), (.055, .020),
                (.057, .0145), (.055, .0105), (.050, .0094), (.051, .0086), (.056, .006),
                (.059, .003))
    angles = [pi / 2 - 2 * pi * i / 48 for i in range(48)]
    rotate = rot(UP, radians(yaw)) @ rot(RIGHT, -radians(pitch))

    def turn(x, y, z):
        return pivot + rotate @ (V(x, y, z) - pivot)

    rings = [[turn(radius * cos(a), .94 * radius * sin(a), z) for a in angles] for z, radius in stations]
    _closed_sections(g, rings, turn(0, 0, -.049), turn(0, 0, .060), scale)


PARTS = [
    Part("hinged_gill_cover", "sensory", "Arched opercular plate on an anterior hinge with a free rear edge.",
         ["operculum", "bluegill", "gill", "respiration"],
         {"size": SIZE, "width": (.78, 1.19, 1.), "open_deg": (0., 23., 5.)}, hinged_gill_cover,
         orient="native", mirror=True, hint=SIDE, symmetry="pair",
         bones=[{"name": "operculum", "pivot": (-.010, 0, .041), "axis": (0, 1, 0), "angle": -15}]),
    Part("bill_edge_filter", "feeding", "Opposing bill margins with staggered hooked lamellar rows.",
         ["flamingo", "bill", "filter", "lamellae"],
         {"size": SIZE, "lamellae": (16, 34, 24), "gape": (.02, .16, .065)}, bill_edge_filter,
         orient="native", hint=FRONT, symmetry="center", discrete=("lamellae",),
         bones=[{"name": "jaw", "pivot": (0, 0, -.052), "axis": (1, 0, 0), "angle": 8}]),
    Part("annular_suction_mouth", "feeding", "Rimmed suction disc with a deep oral bowl and circlet teeth.",
         ["lamprey", "sucking disc", "annular", "oral teeth"],
         {"size": SIZE, "flare": (.78, 1.22, 1.), "depth": (.72, 1.2, 1.)}, annular_suction_mouth,
         orient="forward", hint=FRONT, symmetry="center"),
    Part("crossed_bill_tips", "feeding", "Thin opposing bill tips that sweep laterally past each other.",
         ["bill", "crossbill", "cone", "feeding"],
         {"size": SIZE, "crossing": (.86, 1.25, 1.), "gape_deg": (0., 19., 3.)}, crossed_bill_tips,
         orient="native", hint=FRONT, symmetry="center",
         bones=[{"name": "jaw", "pivot": (0, -.015, -.016), "axis": (1, 0, 0), "angle": 14}]),
    Part("deployable_feather_crown", "aesthetics", "Paired curved crest feathers folding toward the nape.",
         ["crest", "display", "cockatoo", "feathers"],
         {"size": SIZE, "deploy": (0., 1., .85), "reach": (.75, 1.25, 1.)}, deployable_feather_crown,
         orient="native", hint=CROWN, symmetry="center"),
    Part("rotating_ocular_turret", "sensory", "Rotating ocular skin turret with an inset eye aperture.",
         ["eye", "chameleon", "turret", "orbit"],
         {"size": SIZE, "yaw_deg": (-32., 32., 12.), "pitch_deg": (-24., 24., 5.)}, rotating_ocular_turret,
         orient="forward", mirror=True, hint=SIDE, symmetry="pair",
         bones=[{"name": "turret", "pivot": (0, 0, -.009), "axis": (0, 1, 0), "angle": 22}]),
]
TRAITS = {
    "hinged_gill_cover": {"function": "breathe", "construction": "rigid", "shape": "anterior hinge and curved gill cover"},
    "bill_edge_filter": {"function": "feed", "construction": "rigid", "shape": "opposing rails with hooked lamellae"},
    "annular_suction_mouth": {"function": "feed", "construction": "deformable", "shape": "annular oral cup with circumoral teeth"},
    "crossed_bill_tips": {"function": "feed", "construction": "rigid", "shape": "opposed bills with a lateral overcross"},
    "deployable_feather_crown": {"function": "display", "construction": "deformable", "shape": "folding paired crown feathers"},
    "rotating_ocular_turret": {"function": "sense", "construction": "rigid", "shape": "orbital turret with a small aperture"},
}
