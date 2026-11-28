"""External arthropod drafts with +Y dorsal and +Z anterior."""

import math

from ..kit import RIGHT, UP, V, rot
from . import Part
from .candidate_arthropod import _loft
from .candidate_queue_arthropods import SIZE, UNIT
from .research_locomotion import _closed_rings


def overlapping_acoustic_tegmina(g, p):
    """Paired cricket tegmina with local file, plectrum, harp and mirror."""
    g.setup(finish="direct")
    size, sweep = p["size"], p["sweep"]
    for side in (-1, 1):
        offset = V(side * .071, .014 if side == 1 else -.009, 0)
        swing = rot(UP, math.radians(-side * 27 * sweep))
        pitch = rot(RIGHT, math.radians(22 * p["raise"]))

        def place(x, y, z):
            return offset + pitch @ (swing @ V(side * x, y, z))

        rings = []
        for z, xc, width, camber, depth in (
            (.018, -.006, .027, .003, .008), (0, -.008, .036, .005, .009),
            (-.028, -.005, .061, .013, .008), (-.069, -.004, .085, .017, .009),
            (-.109, .000, .091, .021, .007), (-.158, .009, .088, .020, .006),
            (-.215, .014, .073, .014, .005), (-.268, .014, .050, .011, .0035),
            (-.323, .007, .033, .007, .003), (-.352, .000, .012, .002, .0016),
        ):
            rings.append([place(xc + width * math.cos(a * math.tau / 28),
                                camber * math.sin(a * math.tau / 28)**2
                                + depth * math.sin(a * math.tau / 28), z) * size for a in range(28)])
        _closed_rings(g, rings)
        for path in (
            ((-.064, .018, -.056), (-.025, .030, -.075), (.026, .027, -.096),
             (.006, .033, -.142), (-.030, .029, -.157), (-.064, .018, -.056)),
            ((-.044, .027, -.092), (-.009, .035, -.113), (.010, .032, -.125)),
            ((-.036, .028, -.115), (-.015, .035, -.127), (.003, .033, -.137)),
            ((.007, .031, -.156), (.049, .024, -.151), (.064, .018, -.183),
             (.054, .018, -.218), (.025, .023, -.228), (.007, .026, -.215),
             (.007, .030, -.157)),
        ):
            _loft(g, size, [place(*v) for v in path], [.0024] * len(path), up=UP, sides=10, density=3)
        if side == 1:
            for i in range(19):
                t = i / 18
                x, z = -.075 + .142 * t, -.074 - .030 * t
                _loft(g, size, [place(x, y, z + shift) for y, shift in
                                ((.003, -.006), (-.004, -.002), (-.007, .003), (-.004, .006))],
                      (.0030, .0036, .0027, .001), up=UP, sides=8, density=2)
        else:
            _loft(g, size, [place(*v) for v in [
                (-.072, .000, -.064), (-.080, .005, -.081), (-.089, .008, -.097),
                (-.086, .008, -.117), (-.083, .003, -.122),
            ]], ((.008, .004), (.009, .005), (.009, .007), (.006, .005),
                  (.002, .002)), up=UP, sides=14)


def rolling_overlap_tergite_row(g, p):
    """Three arched woodlouse tergites with backward lips and lateral epimera."""
    g.setup(finish="direct")
    size, bend = p["size"], 6.7 * p["curl"]
    for index in range(3):
        s = .018 + .088 * index
        angle = s * bend
        hinge = rot(RIGHT, -angle)
        root = V(0, (math.cos(angle) - 1) / bend, -math.sin(angle) / bend) if bend else V(0, 0, -s)
        rings = []
        for z, width, height, edge, depth in (
            (.061, .94, .94, .000, .0035), (.045, .99, 1, -.004, .007),
            (.018, 1.00, 1, -.007, .011), (-.016, 1.02, 1.02, -.018, .012),
            (-.046, 1.02, .99, -.028, .010), (-.061, .99, .96, -.039, .0045),
        ):
            edges = []
            for sample in range(30):
                theta = math.radians(-109 + 218 * sample / 29)
                lateral = math.sin(theta)
                dome = math.cos(theta)
                x = .162 * width * lateral * (1 - .027 * index)
                y = .140 * height * dome - .062 + edge * abs(lateral)**4
                edges.append((x, y, z + .026 * abs(lateral)**2, lateral, dome))
            ring = []
            for rim in (edges, list(reversed(edges))):
                thickness = depth if rim is edges else 0.
                for x, y, axial, lateral, dome in rim:
                    v = V(x + thickness * lateral, y + thickness * dome, axial)
                    ring.append((root + hinge @ v) * size)
            rings.append(ring)
        _closed_rings(g, rings)


def paired_antennal_breathing_tube(g, p):
    """Two opposed, setose Corystes antennae with a basal respiratory channel."""
    g.setup(finish="direct")
    size, separation = p["size"], p["separate"]
    for side in (-1, 1):
        seat = V(.019, 0, .012)
        turn = rot(UP, math.radians(30 * separation))

        def place(pos):
            v = seat + turn @ V(pos)
            return V(side * v.x, v.y, v.z)

        _loft(g, size, [place(v) for v in (
            (.009, .003, -.027), (.012, .004, -.007), (.014, .004, .022),
            (.012, .005, .051), (.008, .006, .079),
        )], ((.017, .019), (.020, .022), (.016, .019), (.014, .017),
              (.013, .014)), up=UP)
        rings = []
        for i in range(41):
            t = i / 40
            z = .059 + .297 * t
            yc = .006 + .028 * t**1.8
            radius = .022 - .013 * t
            seam = 1 - (.12 if i % 4 == 0 else 0)
            rows = []
            for outer in (True, False):
                angles = range(15) if outer else range(14, -1, -1)
                r = radius * seam * (1.18 if outer else .83)
                for a in angles:
                    theta = math.radians(-88 + 176 * a / 14)
                    rows.append(place((.002 + r * math.cos(theta), yc + r * math.sin(theta), z)) * size)
            rings.append(rows)
        _closed_rings(g, rings)
        for upper in (-1, 1):
            for i in range(24):
                t = i / 23
                z = .067 + .282 * t
                root = V(.003, .006 + .028 * t**1.8 + upper * (.022 - .013 * t), z)
                length = .024 - .008 * t
                _loft(g, size, [place(root + v) for v in (
                    V(.001, 0, -.003), V(-.45 * length, upper * .002, .002),
                    V(-length, upper * .002, .007),
                )], (.00215, .0014, .00042), up=UP, sides=8, density=2)


def subchelate_palm_fold(g, p):
    """Oval amphipod propodus and feeding-side folding dactyl."""
    g.setup(finish="direct")
    size = p["size"]
    _loft(g, size, ((0, .039, -.061), (0, .020, -.039), (0, 0, -.019), (0, -.008, .013)),
          ((.020, .026), (.027, .034), (.033, .036), (.034, .032)), up=RIGHT)
    _loft(g, size, ((0, -.009, -.005), (0, -.018, .014), (0, -.026, .044),
                    (0, -.036, .080), (0, -.037, .114), (0, -.024, .153),
                    (0, -.003, .174), (0, .015, .180)),
          ((.024, .024), (.039, .045), (.061, .061), (.071, .072),
           (.064, .066), (.040, .054), (.024, .034), (.014, .016)), up=RIGHT)
    pivot = V(.009, .008, .168)
    hinge = rot(RIGHT, -math.radians(86 * p["open"]))

    def point(v):
        return pivot + hinge @ V(v)

    _loft(g, size, [point(v) for v in (
        (-.001, -.013, -.004), (.002, -.023, .016), (.002, -.051, .019),
        (.001, -.082, .004), (0, -.104, -.022), (-.001, -.109, -.054),
        (-.002, -.104, -.080), (-.004, -.095, -.087),
    )], ((.011, .012), (.015, .015), (.014, .014), (.012, .011),
          (.009, .008), (.007, .006), (.004, .003), (.0008, .0012)), up=RIGHT, sides=20)
    _loft(g, size, ((.007, -.075, .039), (.008, -.097, .057), (.007, -.102, .074),
                    (.006, -.087, .090)), ((.017, .012), (.019, .013),
                    (.014, .011), (.009, .008)), up=RIGHT, sides=17)


def asymmetric_shell_holdfast(g, p):
    """Right-coiling Pagurus abdominal tip with unequal rasp-bearing uropods."""
    g.setup(finish="direct")
    size, curl = p["size"], p["curl"]
    turn = rot(UP, math.radians(22 + 42 * curl))
    anchor = V(.074, -.022, -.168)
    _loft(g, size, ((-.009, .011, .024), (0, .005, -.006), (.008, -.003, -.054),
                    (.019, -.010, -.104), (.045, -.017, -.145), anchor),
          ((.047, .035), (.053, .043), (.051, .041), (.042, .031),
           (.036, .026), (.027, .021)), up=UP)
    _loft(g, size, [anchor + turn @ V(v) for v in (
        (-.005, 0, .020), (.006, -.005, -.003), (.025, -.007, -.029),
        (.037, -.008, -.052),
    )], ((.027, .017), (.030, .019), (.026, .015), (.010, .008)), up=UP)
    for side, scale in ((-1, 1.), (1, .67)):
        for outer in (True, False):
            length = .096 * scale * (1.0 if outer else .65)
            x = .020 if outer else .013
            root = anchor + turn @ V(side * x, -.005 + (.005 if outer else -.003), -.021)

            def place(v):
                a, b, c = v
                return root + turn @ V(side * a * scale, b, c * length)

            _loft(g, size, [place(v) for v in (
                (-.005, 0, .08), (.009, -.004, -.13), (.028, -.009, -.33),
                (.044, -.010, -.56), (.050, -.004, -.82), (.045, .009, -.97),
                (.039, .014, -1.02),
            )], [(r * scale, d) for r, d in
                  ((.010, .009), (.016, .010), (.026, .014), (.032, .013),
                   (.031, .010), (.018, .008), (.005, .004))], up=UP, sides=20)
            for row in range(4 if outer else 3):
                for i in range(6 if outer else 4):
                    progress = .29 + .105 * i
                    x = .020 + .027 * progress + .007 * row
                    _loft(g, size, [place((x, -.012, -progress)), place((x, -.017, -progress - .026)),
                                    place((x - .003, -.018, -progress - .053))],
                          (.0045, .0033, .001), up=UP, sides=8, density=2)


PARTS = [
    Part("overlapping_acoustic_tegmina", "aesthetics", "Two raised cricket forewings seat a file and an opposing scraper beside acoustic panels.",
         ["field cricket", "stridulation", "tegmen", "file", "plectrum"],
         {"size": SIZE, "sweep": (0., 1., .25), "raise": (0., 1., .35)},
         overlapping_acoustic_tegmina, orient="native", symmetry="center"),
    Part("rolling_overlap_tergite_row", "aesthetics", "Three overlapping arch plates curl with the trunk joints of a pill woodlouse.",
         ["woodlouse", "pillbug", "tergite", "conglobation"], {"size": SIZE, "curl": (0., 1., .36)},
         rolling_overlap_tergite_row, orient="native", symmetry="center"),
    Part("paired_antennal_breathing_tube", "sensory", "Two opposed hairy antennae close into a breathing channel.",
         ["masked crab", "antenna", "respiration", "sand"], {"size": SIZE, "separate": (0., 1., 0.)},
         paired_antennal_breathing_tube, orient="native", symmetry="center"),
    Part("subchelate_palm_fold", "manipulation", "An amphipod dactyl folds along the short convex rim of a large palm.",
         ["amphipod", "beachflea", "gnathopod", "subchelate"], {"size": SIZE, "open": (0., 1., .24)},
         subchelate_palm_fold, orient="native", symmetry="pair"),
    Part("asymmetric_shell_holdfast", "manipulation", "Unequal rasp-bearing uropods seat at the curled end of a hermit crab abdomen.",
         ["hermit", "uropod", "holdfast", "rasp"], {"size": SIZE, "curl": (0., 1., .4)},
         asymmetric_shell_holdfast, orient="native", symmetry="center"),
]

TRAITS = {
    "overlapping_acoustic_tegmina": {"function": "sound"},
    "rolling_overlap_tergite_row": {"function": "protect"},
    "paired_antennal_breathing_tube": {"function": "breathe"},
    "subchelate_palm_fold": {"function": "grasp"},
    "asymmetric_shell_holdfast": {"function": "anchor"},
}
