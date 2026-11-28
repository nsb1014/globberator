"""Vertebrate jaw, oral and swallowing mechanisms in isolation."""

from math import cos, exp, pi, radians, sin

from ..kit import BACK, RIGHT, UP, V, rot
from . import Part
from .anatomy import _loft
from .research_aesthetics import _closed_sections

SIZE = (.65, 1.65, 1.)
FRONT = {"u": .94, "theta": -90}


def projectile_tongue_skeleton(g, p):
    """Long tongue projectile carrying distal pad and paired skeletal struts."""
    size, reach, lift = p["size"], p["reach"], p["lift"]
    tip_z = .046 + .211 * reach
    tip_y = .010 + .035 * lift * reach
    g.setup(finish="direct")
    # Tapering muscular tether follows the deployable skeleton into the mouth.
    _loft(g, size,
          [(0, -.010, -.036), (0, -.011, -.016), (0, -.012, .012),
           (0, -.011 + .006 * reach, .37 * tip_z),
           (0, .33 * tip_y - .006, .69 * tip_z), (0, tip_y, tip_z)],
          [(.019, .015), (.017, .011), (.012, .008), (.008, .006), (.006, .005), (.004, .004)],
          up=UP, sides=24, density=6)
    g.slot("projectile_skeleton")
    for side in (-1, 1):
        _loft(g, size,
              [(side * .010, -.010, -.017 + .38 * tip_z),
               (side * .010, -.007 + .18 * tip_y, .49 * tip_z),
               (side * .008, -.007 + .36 * tip_y, .71 * tip_z),
               (side * .004, -.002 + .82 * tip_y, .92 * tip_z)],
              [(.0028, .0024), (.0028, .0024), (.0024, .0020), (.0013, .0013)],
              up=UP, sides=10, density=4)
    g.slot("adhesive_pad")
    _loft(g, size,
          [(0, tip_y - .001, tip_z - .014), (0, tip_y, tip_z - .004),
           (0, tip_y + .002, tip_z + .007), (0, tip_y + .004, tip_z + .018),
           (0, tip_y + .004, tip_z + .025)],
          [(.010, .0058), (.021, .009), (.023, .009), (.018, .007), (.007, .004)],
          up=UP, sides=24, density=5, exponent=.74)


def gape_interlocking_mandibular_tusks(g, p):
    """Flattened mandibular teeth wrap up, back and over the upper rostrum."""
    size, rise, curl = p["size"], p["rise"], p["curl"]
    g.setup(finish="direct")
    stations = ((.058, -.030, .016, .013, .010), (.060, -.011, .015, .017, .010),
                (.064, .015, .003, .018, .008), (.064, .045, -.017, .018, .007),
                (.055, .069, -.037, .017, .006), (.041, .085, -.057, .015, .005),
                (.021, .094, -.071, .011, .004), (.004, .094, -.080, .006, .003),
                (-.003, .097, -.084, .0025, .0015))
    for side in (-1, 1):
        def position(x, y, z):
            # Full-height tips pass at different dorsal positions.
            end = max(0, (y - .034) / .063)
            return V(side * (.063 + (x - .063) * (1 + (curl - 1) * end)),
                     y * rise + .004 * side * end, z + .012 * side * end)

        _loft(g, size, [position(x, y, z) for x, y, z, _, _ in stations],
              [(w, t) for _, _, _, w, t in stations], up=RIGHT,
              sides=28, density=5, exponent=.69)
        x, y, z, _, _ = stations[7]
        point = position(x, y, z)
        _loft(g, size, [point - .003 * UP, point + .002 * UP,
                         point + V(side * .001, .008, -.003)],
              [(.005, .003), (.0037, .0025), (.0008, .0008)],
              sides=14, density=4)


def erectile_nectar_brush_tongue(g, p):
    """Distal tongue with a dense movable field of filamentous papillae."""
    size, extension, erect = p["size"], p["length"], p["erect"]
    g.setup(finish="direct")
    _loft(g, size,
          [(0, -.004, z * extension) for z in (-.067, -.052, -.025, .006, .041, .069, .094, .109)],
          [(.012, .010), (.014, .011), (.014, .012), (.016, .013), (.016, .014),
           (.014, .012), (.010, .009), (.005, .004)],
          up=UP, sides=32, density=5)
    for row in range(12):
        z = .019 + row * .0069
        width = .016 - .008 * (row / 11) ** 2.7
        count = 12
        for i in range(count):
            a = (-.27 + 1.54 * i / (count - 1)) * pi
            radial = V(cos(a), .78 * sin(a), 0)
            setback = .013 - .005 * (row / 11)
            base = V(0, -.004, z * extension) + width * radial
            tip = base + (.004 + .016 * erect) * radial - setback * (1 - .72 * erect) * BACK
            mid = base.lerp(tip, .52) - .002 * BACK
            _loft(g, size, [base - .0025 * radial, mid, tip],
                  [(.00108, .00092), (.00074, .00066), (.00022, .00022)],
                  up=UP, sides=6, density=1)


def postincisor_oral_seal(g, p):
    """Upper and lower postincisor folds paired with external digging incisors."""
    size, gape, projection = p["size"], p["gape"], p["projection"]
    stations = ((-.055, .006), (-.047, .009), (-.028, .012), (0, .015),
                (.028, .012), (.047, .009), (.055, .006))
    g.pivots["jaw"] = V(0, -.010, -.053) * size
    for side, bone in ((1, "self"), (-1, "jaw")):
        g.use(bone)
        g.setup(finish="direct")
        lip_y = side * .014 - (.034 * gape if side < 0 else 0)
        _loft(g, size, [(x, lip_y + side * .003 * (x / .055) ** 2, -.005 - .017 * (x / .055) ** 2)
                         for x, _ in stations],
              [(h, 1.08 * h) for _, h in stations], up=UP, sides=24, density=5)
        for x in (-.010, .010):
            y = .034 * side - (.018 * gape if side < 0 else 0)
            _loft(g, size, [(x, y, -.035), (x, y, -.015), (x, y + side * .002, .008),
                             (x, y - side * .007, .030 * projection),
                             (x, y - side * .015, .045 * projection),
                             (x, y - side * .022, .051 * projection)],
                  [(.007, .009), (.008, .009), (.0085, .0085), (.0085, .007),
                   (.008, .004), (.007, .002)], up=UP, sides=20, density=5, exponent=.48)


def intracranial_jaw_hinge(g, p):
    """Divided neurocranium with an anterior cranial sector on a second hinge."""
    size, breadth, angle = p["size"], p["breadth"], p["elevate_deg"]
    rear = ((-.143, .016, .033, .019), (-.124, .022, .053, .036),
            (-.087, .027, .062, .041), (-.047, .033, .060, .043),
            (-.018, .037, .052, .039), (-.006, .033, .044, .033))
    front = ((.003, .037, .044, .033), (.018, .040, .046, .035),
             (.044, .037, .044, .035), (.075, .034, .037, .031),
             (.109, .029, .029, .026), (.133, .023, .025, .022),
             (.151, .019, .017, .016), (.160, .017, .008, .008))
    pivot = V(0, .012, -.006)
    g.pivots["ethmosphenoid"] = pivot * size
    for side in (-1, 1):
        g.setup(finish="direct")
        g.oval(V(side * .036 * breadth, .011, -.007) * size,
               (.014 * size, .018 * size, .020 * size), segs=24, rings=14)
    for bone, blocks in (("self", rear), ("ethmosphenoid", front)):
        g.use(bone)
        g.setup(finish="direct")
        rotation = rot(RIGHT, -radians(angle) if bone == "ethmosphenoid" else 0.)
        points = [pivot + rotation @ (V(0, y, z) - pivot) for z, y, _, _ in blocks]
        _loft(g, size, points, [(x * breadth, h) for _, _, x, h in blocks],
              up=UP, sides=34, density=5, exponent=.73)


def swallowing_orbit_plunger(g, p):
    """Globe and moving oral contact pad in a continuous orbital collar."""
    size, retract, oval = p["size"], p["retract"], p["oval"]
    profile = ((-.052, .019, .017), (-.044, .034, .031), (-.026, .046, .042),
               (-.010, .051, .044), (.004, .044, .039), (.006, .035, .031),
               (.003, .030, .027), (-.013, .029, .026), (-.033, .025, .023),
               (-.043, .019, .016))
    angles = [pi / 2 - 2 * pi * i / 56 for i in range(56)]
    g.setup(finish="direct")
    # Shape the collar around the movable eyeball opening.
    rings = [[(oval * w * cos(a), h * sin(a) + .08 * w * cos(a), z) for a in angles]
             for z, w, h in profile]
    _closed_sections(g, rings, (0, 0, -.054), (0, 0, -.046), size)
    g.slot("orbit_globe")
    globe_depth = .001 - .029 * retract
    g.oval(V(0, 0, globe_depth) * size,
           (.033 * oval * size, .031 * size, .027 * size), segs=40, rings=23)
    for vertex in g.prims[-1].v:
        x, y, z = vertex / size
        aperture = exp(-((x / .012) ** 4 + (y / .0048) ** 4))
        front = max(0., (z - globe_depth) / .027) ** 4
        vertex.z -= .0025 * size * front * aperture
    g.slot("palatal_contact")
    g.oval(V(0, -.003, -.044 - .020 * retract) * size,
           (.029 * oval * size, .026 * size, (.010 + .005 * retract) * size),
           segs=34, rings=18)


PARTS = [
    Part("projectile_tongue_skeleton", "feeding", "Ballistic tongue pad on an extended skeletal and soft-tissue tether.",
         ["ensatina", "ballistic", "tongue", "feeding"],
         {"size": SIZE, "reach": (.03, 1., .81), "lift": (-.38, .76, .28)},
         projectile_tongue_skeleton, orient="native", hint=FRONT, symmetry="center"),
    Part("gape_interlocking_mandibular_tusks", "feeding", "Mandibular strap tusks curve backward and inward above the rostrum.",
         ["strapped teeth", "beaked whale", "mandible", "display"],
         {"size": SIZE, "rise": (.75, 1.27, 1.), "curl": (.78, 1.18, 1.)},
         gape_interlocking_mandibular_tusks, orient="native", hint=FRONT, symmetry="center"),
    Part("erectile_nectar_brush_tongue", "feeding", "Distal brush with erectable filamentous papillae.",
         ["nectar bat", "tongue", "papillae", "brush"],
         {"size": SIZE, "length": (.78, 1.24, 1.), "erect": (0., 1., .72)},
         erectile_nectar_brush_tongue, orient="native", hint=FRONT, symmetry="center"),
    Part("postincisor_oral_seal", "feeding", "Lips seat behind teeth that protrude for substrate contact.",
         ["mole rat", "incisors", "oral folds", "digging"],
         {"size": SIZE, "gape": (0., 1., .48), "projection": (.76, 1.24, 1.)},
         postincisor_oral_seal, orient="native", hint=FRONT, symmetry="center",
         bones=[{"name": "jaw", "pivot": (0, -.010, -.053), "axis": (1, 0, 0), "angle": 9}]),
    Part("intracranial_jaw_hinge", "feeding", "Anterior cranial sector articulates independently of the posterior braincase.",
         ["coelacanth", "cranial joint", "ethmosphenoid", "feeding"],
         {"size": SIZE, "breadth": (.79, 1.22, 1.), "elevate_deg": (0., 16., 7.)},
         intracranial_jaw_hinge, orient="native", hint=FRONT, symmetry="center",
         bones=[{"name": "ethmosphenoid", "pivot": (0, .012, -.006), "axis": (1, 0, 0), "angle": -7}]),
    Part("swallowing_orbit_plunger", "feeding", "An orbital globe retracts toward a soft palate contact pad.",
         ["leopard frog", "orbit", "eye retraction", "swallow"],
         {"size": SIZE, "retract": (0., 1., .35), "oval": (.83, 1.18, 1.)},
         swallowing_orbit_plunger, orient="forward", mirror=True, hint={"u": .94, "theta": 20}, symmetry="pair"),
]
TRAITS = {
    "projectile_tongue_skeleton": {"function": "feed", "construction": "deformable", "shape": "skeletal projectile tether and broad pad"},
    "gape_interlocking_mandibular_tusks": {"function": "display", "construction": "rigid", "shape": "paired backward-curving strap teeth"},
    "erectile_nectar_brush_tongue": {"function": "feed", "construction": "deformable", "shape": "cylindrical distal tongue with brush papillae"},
    "postincisor_oral_seal": {"function": "feed", "construction": "deformable", "shape": "external incisors and separate recessed lip folds"},
    "intracranial_jaw_hinge": {"function": "feed", "construction": "rigid", "shape": "anterior and posterior cranial sectors with a hinge"},
    "swallowing_orbit_plunger": {"function": "feed", "construction": "deformable", "shape": "orbital collar with a retractile globe and oral pad"},
}
