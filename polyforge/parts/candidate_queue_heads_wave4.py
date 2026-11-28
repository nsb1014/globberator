"""Additional isolated amphibian and reptile head attachments."""

from math import cos, exp, pi, sin

from ..kit import BACK, UP, V
from . import Part
from .anatomy import _loft
from .research_aesthetics import _closed_sections

SIZE = (.65, 1.65, 1.)
FRONT = {"u": .94, "theta": -90}
SIDE = {"u": .91, "theta": 0}


def tadpole_scraping_oral_disc(g, p):
    """Elliptical larval lip, transverse labial tooth rows and two jaw sheaths."""
    size, width, gape = p["size"], p["width"], p["gape"]
    angles = [pi / 2 - 2 * pi * i / 52 for i in range(52)]
    stations = ((-.026, .025, .016), (-.018, .038, .021), (-.006, .051, .030),
                (.006, .060, .036), (.017, .063, .038), (.023, .061, .036),
                (.022, .053, .030), (.017, .042, .022), (.011, .028, .014),
                (.007, .016, .007), (.006, .007, .004))
    g.setup(finish="direct")
    rings = [[(width * w * cos(a), h * sin(a), z - .18 * h * sin(a)) for a in angles]
             for z, w, h in stations]
    _closed_sections(g, rings, (0, 0, -.030), (0, 0, .006), size)
    for sign in (1, -1):
        root_y = sign * (.006 + .005 * gape)
        _loft(g, size,
              [(-.028 * width, root_y, .012), (-.021 * width, root_y + sign * .002, .017),
               (0, root_y + sign * .002, .021), (.021 * width, root_y + sign * .002, .017),
               (.028 * width, root_y, .012)],
              [(.0014, .002), (.0022, .0035), (.0026, .0040), (.0022, .0035), (.0014, .002)],
              up=UP, sides=15, density=4, exponent=.70)
        for row in range(2 if sign > 0 else 3):
            span = width * (.033 + .007 * row)
            for tooth in range(-11, 12):
                if sign > 0 and row == 1 and abs(tooth) <= 1:
                    continue
                t = tooth / 11
                x = span * t
                y = sign * (.011 + .007 * row + .007 * t * t)
                z = .012 + .004 * row + .004 * t * t
                _loft(g, size, [(x, y, z - .004), (x, y, z + .003), (x, y - sign * .001, z + .0045)],
                      [(.0011, .0013), (.001, .00095), (.00032, .00031)],
                      up=UP, sides=6, density=1)
    for index, a in enumerate(angles):
        if sin(a) > .53:  # a quiet outer margin above the anterior tooth rows
            continue
        tip_y = .040 * sin(a)
        x = .061 * width * cos(a)
        z = .020 - .12 * tip_y
        g.oval(V(x, tip_y, z) * size, (.0018 * size, .0026 * size,
                                     (.0031 + .0004 * (index % 2)) * size), segs=9, rings=6)


def retractile_chemosensory_tentacle(g, p):
    """A retractile facial tentacle seated through a small rimmed canal."""
    size, reach, curl = p["size"], p["reach"], p["curl"]
    stations = ((-.030, .014, .012), (-.021, .023, .018), (-.008, .029, .022),
                (.002, .026, .019), (.008, .019, .013), (.010, .013, .009),
                (.011, .008, .006), (.009, .006, .004), (.003, .005, .003),
                (-.005, .004, .003), (-.013, .002, .002))
    angles = [pi / 2 - 2 * pi * i / 44 for i in range(44)]
    g.setup(finish="direct")
    rings = [[(w * cos(a), h * sin(a) + .13 * w * cos(a), z) for a in angles]
             for z, w, h in stations]
    _closed_sections(g, rings, (0, 0, -.035), (0, 0, -.015), size)
    passage = .007 + .056 * reach
    side_bend = .014 * curl
    _loft(g, size, [(0, 0, -.009), (.001, 0, .002),
                     (.001 + .18 * reach * side_bend, -.001, .006 + passage * .25),
                     (.001 + .44 * reach * side_bend, -.004 * reach, .006 + passage * .63),
                     (.001 + reach * side_bend, -.010 * reach, .006 + passage)],
          [(.0038, .0035), (.0043, .0038), (.0044, .004), (.0039, .0034), (.0022, .002)],
          up=UP, sides=17, density=5)


def suspended_thermal_pit(g, p):
    """Loreal pit aperture with a recessed membrane separating chamber volumes."""
    size, opening, depth = p["size"], p["opening"], p["depth"]
    stations = ((-.040, .015, .010), (-.030, .026, .015), (-.014, .036, .023),
                (.002, .035, .022), (.012, .030, .017), (.016, .023, .014),
                (.018, .018, .010), (.014, .015, .0085), (.005, .013, .0078),
                (-.009, .012, .0070), (-.018, .011, .0060), (-.027, .007, .004))
    angles = [pi / 2 - 2 * pi * i / 52 for i in range(52)]
    rings = []
    for index, (z, w, h) in enumerate(stations):
        factor = opening if index >= 6 else 1
        axial = z * depth if index >= 8 else z
        rings.append([(factor * w * cos(a) - .18 * factor * h * sin(a),
                       factor * h * sin(a) * (1 - .24 * cos(a)), axial + .19 * factor * w * cos(a))
                      for a in angles])
    g.setup(finish="direct")
    _closed_sections(g, rings, (0, 0, -.044), (0, 0, -.030 * depth), size)
    g.slot("membrane")
    g.oval(V(0, 0, -.017 * depth) * size,
           (.0136 * opening * size, .0078 * opening * size, .0019 * size), segs=36, rings=14)


def gular_palatal_seal(g, p):
    """Opposing posterior oral folds that can separate at the free contact edge."""
    size, width, opening = p["size"], p["width"], p["opening"]
    angles = [pi / 2 + 2 * pi * i / 44 for i in range(44)]
    # Width, dorsoventral reach, anteroposterior thickness and center height.
    upper = ((0., .031, .013, .021), (.026, .029, .014, .022), (.050, .026, .015, .024),
             (.072, .021, .013, .026), (.094, .012, .009, .028), (.103, .004, .004, .032))
    lower = ((0., .019, .016, -.027), (.026, .019, .019, -.026), (.049, .017, .019, -.019),
             (.072, .014, .017, -.009), (.096, .009, .012, .007), (.103, .003, .005, .025))
    g.pivots["lower_fold"] = V(0, -.034, -.058) * size
    for bone, stations in (("self", upper), ("lower_fold", lower)):
        g.use(bone)
        g.setup(finish="direct")
        full = [(-x, h, d, center) for x, h, d, center in reversed(stations[1:])] + list(stations)
        is_lower = bone == "lower_fold"
        rings = []
        for x, h, d, center in full:
            gap = .052 * opening * (1 - .32 * abs(x) / .103) if is_lower else 0.
            z_mid = (.014 if is_lower else 0.) - .014 * (x / .103) ** 2
            rings.append([(x * width, center - gap + h * sin(a),
                           z_mid + d * cos(a) - .31 * h * sin(a)) for a in angles])
        pole_y = stations[-1][3] - (.036 * opening if is_lower else 0)
        pole_z = -.015 + (.014 if is_lower else 0)
        _closed_sections(g, rings, (-.106 * width, pole_y, pole_z),
                         (.106 * width, pole_y, pole_z), size)


PARTS = [
    Part("tadpole_scraping_oral_disc", "feeding", "Shallow larval oral disc with transverse scraper rows and jaw sheaths.",
         ["tadpole", "labial teeth", "oral disc", "grazing"],
         {"size": SIZE, "width": (.80, 1.24, 1.), "gape": (.25, 1., .55)},
         tadpole_scraping_oral_disc, orient="forward", hint=FRONT, symmetry="center"),
    Part("retractile_chemosensory_tentacle", "sensory", "Short eversible facial tentacle in a recessed aperture.",
         ["caecilian", "chemosense", "tentacle", "sensory pit"],
         {"size": SIZE, "reach": (0., 1., .68), "curl": (-1., 1., .25)},
         retractile_chemosensory_tentacle, orient="forward", mirror=True, hint=SIDE, symmetry="pair"),
    Part("suspended_thermal_pit", "sensory", "Loreal chamber with a free-sided internal sensor membrane.",
         ["rattlesnake", "pit organ", "loreal", "infrared"],
         {"size": SIZE, "opening": (.77, 1.23, 1.), "depth": (.70, 1.30, 1.)},
         suspended_thermal_pit, orient="forward", mirror=True, hint=SIDE, symmetry="pair"),
    Part("gular_palatal_seal", "feeding", "Two opposed posterior oral folds across the pharyngeal opening.",
         ["alligator", "gular valve", "palate", "pharynx"],
         {"size": SIZE, "width": (.79, 1.22, 1.), "opening": (0., 1., .64)},
         gular_palatal_seal, orient="native", hint=FRONT, symmetry="center",
         bones=[{"name": "lower_fold", "pivot": (0., -.034, -.058), "axis": (1, 0, 0), "angle": 7}]),
]
TRAITS = {
    "tadpole_scraping_oral_disc": {"function": "feed", "construction": "deformable", "shape": "oral disc with transverse labial teeth"},
    "retractile_chemosensory_tentacle": {"function": "sense", "construction": "deformable", "shape": "facial canal and eversible tentacle"},
    "suspended_thermal_pit": {"function": "sense", "construction": "rigid", "shape": "recessed loreal pit with a membrane"},
    "gular_palatal_seal": {"function": "feed", "construction": "deformable", "shape": "paired transverse folds across the pharynx"},
}
