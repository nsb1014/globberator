"""Sculpted parts and a membrane wing for the aquatic and flight pilots."""

import math

from ..kit import UP, V, lerp
from . import Part
from .research_locomotion import _closed_rings


def _foil_ring(x, y, front, rear, half_depth):
    return [
        V(x, y + half_depth * math.sin(angle) * (1 + .18 * math.cos(angle)),
          lerp(rear, front, (1 + math.cos(angle)) * .5))
        for angle in (math.tau * j / 16 for j in range(16))
    ]


def flukes_cetacean(g, p):
    """Transverse swept flukes with a shared root and a central trailing notch."""
    half_span, chord = p["span"] * .5, p["chord"]
    stations = (
        (0, .020, .58, -.26, .146), (.07, .016, .58, -.43, .14),
        (.19, .006, .51, -.54, .112), (.38, -.006, .34, -.64, .086),
        (.57, -.007, .09, -.73, .060), (.73, -.003, -.23, -.84, .042),
        (.86, .003, -.55, -.96, .028), (.96, .013, -.86, -1.05, .014),
        (1, .018, -1.042, -1.065, .004),
    )
    rings = [_foil_ring(x * half_span, y, front * chord, rear * chord, depth * chord)
             for x, y, front, rear, depth in stations]
    g.setup(finish="subsurf")
    _closed_rings(g, [[V(-v.x, v.y, v.z) for v in ring] for ring in reversed(rings[1:])] + rings)


def dolphin_gape(g, p):
    """A shallow tapered lip line on one side of a closed dolphin rostrum."""
    size = p["size"]
    points = ((.025, .021, -.080), (-.009, -.015, -.019), (-.044, -.042, .053),
              (-.063, -.047, .139), (-.076, -.030, .243), (-.097, -.022, .335),
              (-.108, -.014, .387), (-.127, -.010, .431))
    g.loft([V(*point) * size for point in points],
           [size * r for r in (.003, .0055, .0065, .006, .005, .004, .003, .001)],
           sides=10, density=4, up=UP)


def dolphin_dorsal(g, p):
    """Bottlenose dorsal foil with a broad buried base and a concave rear edge."""
    size = p["size"]
    stations = (
        (-.092, .297, -.294, .045), (-.052, .307, -.292, .050),
        (.023, .256, -.218, .040), (.071, .186, -.175, .034),
        (.147, .124, -.150, .026), (.225, .019, -.153, .019),
        (.294, -.075, -.177, .013), (.351, -.152, -.204, .008),
        (.388, -.208, -.226, .003), (.397, -.224, -.231, .001),
    )
    rings = [[V(v.y, v.x, v.z) * size for v in _foil_ring(y, 0, front, rear, depth)]
             for y, front, rear, depth in stations]
    g.setup(finish="subsurf")
    _closed_rings(g, rings)


# Right wing, relative to the glenohumeral joint. +X is span, +Z is anterior.
BAT_JOINTS = (
    (0, 0, 0), (.31, .009, -.175), (.63, .025, .075),
    (1.06, .012, .100), (1.48, -.027, -.042),
)
BAT_RADII = (.076, .052, .039, .021, .003)


def bat_wing_chain(p):
    size = p["size"]
    span_scale = V(size, size, size * p["chord"])
    points = [V(*point) for point in BAT_JOINTS]
    return {
        "segments": [tuple((b[i] - a[i]) * span_scale[i] for i in range(3))
                     for a, b in zip(points, points[1:])],
        "radii": [r * size for r in BAT_RADII],
    }


def _curve_value(edge, x):
    """Evaluate a smooth clipped curve through monotone edge stations."""
    span = next(i for i in range(len(edge) - 1) if x <= edge[i + 1][0])
    x0, y0 = edge[span]
    x1, y1 = edge[span + 1]
    prev_x, prev_y = edge[max(span - 1, 0)]
    next_x, next_y = edge[min(span + 2, len(edge) - 1)]
    width = x1 - x0
    m0 = (y1 - prev_y) / (x1 - prev_x)
    m1 = (next_y - y0) / (next_x - x0)
    t = (x - x0) / width
    return (y0 * (1 + 2 * t) * (1 - t) ** 2 + y1 * t ** 2 * (3 - 2 * t)
            + width * t * (1 - t) * (m0 * (1 - t) - m1 * t))


def bat_flight_wing(g, p):
    """One soft wing with a curved thin membrane and the forearm/hand spars."""
    size, chord = p["size"], p["chord"]

    def place(v):
        return V(v.x * size, v.y * size, v.z * size * chord)

    leading = (
        (-.13, -.01), (0, .047), (.15, -.01), (.30, -.121), (.47, -.032),
        (.63, .100), (.83, .140), (1.06, .124), (1.24, .079),
        (1.41, .007), (1.478, -.043),
    )
    # Distal digit tips alternate with the shallower curved interdigit bays.
    trailing = (
        (-.13, -.230), (-.048, -.529), (.08, -.605), (.25, -.585),
        (.45, -.495), (.58, -.481), (.70, -.586), (.84, -.540),
        (.92, -.459), (1.005, -.549), (1.12, -.449), (1.20, -.343),
        (1.30, -.398), (1.39, -.161), (1.478, -.046),
    )
    stations = sorted({x for x, _ in leading + trailing}
                      | {lerp(-.13, 1.478, i / 66) for i in range(1, 66)})
    rings = []
    for x in stations:
        front = _curve_value(leading, x)
        rear = _curve_value(trailing, x)
        center_y = .021 * math.sin(max(0, x) * math.pi / 1.5) - .019 * x * x
        depth = min(.017 * p["thickness"], (front - rear) * .22)
        rings.append([place(v) for v in _foil_ring(x, center_y, front, rear, depth)])
    g.setup(finish="subsurf_low")
    _closed_rings(g, rings)

    shoulder, elbow, wrist, knuckle, tip = [V(*point) for point in BAT_JOINTS]
    spar_points = (
        V(-.128, 0, -.027), shoulder, shoulder.lerp(elbow, .5),
        elbow, elbow.lerp(wrist, .5), wrist,
        wrist.lerp(knuckle, .5), knuckle, knuckle.lerp(tip, .54), tip,
    )
    g.loft([place(v) for v in spar_points],
           [size * r for r in (.047, .069, .049, .044, .032, .043, .028, .020, .012, .002)],
           sides=16, density=4, up=UP)
    for x, z, bend, radius in ((1.30, -.398, .095, .023),
                                (1.005, -.549, .095, .022),
                                (.70, -.586, -.065, .019)):
        end = V(x, .021 * math.sin(x * math.pi / 1.5) - .019 * x * x, z + .006)
        midpoint = wrist.lerp(end, .52) + V(bend, .010, -.025)
        g.loft([place(v) for v in (wrist, midpoint, end)],
               [size * r for r in (radius, radius * .76, .003)],
               sides=12, density=4, up=UP)
    g.loft([place(v) for v in (wrist, V(.582, .052, .153), V(.575, .061, .187),
                             V(.604, .060, .187))],
           [size * r for r in (.028, .021, .012, .003)], sides=12, density=4, up=UP)


def bat_tail_membrane(g, p):
    """Thin uropatagium between the splayed legs, centered on its short tail."""
    size = p["size"]
    stations = (
        (-.276, -.016, -.101, -.114, .002), (-.197, -.017, -.040, -.138, .007),
        (-.121, -.020, .085, -.173, .010), (-.060, -.027, .140, -.215, .012),
        (0, -.032, .157, -.270, .017), (.060, -.027, .140, -.215, .012),
        (.121, -.020, .085, -.173, .010), (.197, -.017, -.040, -.138, .007),
        (.276, -.016, -.101, -.114, .002),
    )
    g.setup(finish="subsurf")
    _closed_rings(g, [[vertex * size for vertex in _foil_ring(*station)] for station in stations])


def bat_hindfoot(g, p):
    """Tiny heel and five curved toes at the distal end of a bat hindlimb."""
    size = p["size"]
    g.oval(V(0, 0, -.019) * size, (.021 * size, .014 * size, .031 * size))
    for toe in (-2, -1, 0, 1, 2):
        span = abs(toe)
        path = (
            V(.007 * toe, -.003, -.033), V(.012 * toe, -.004, -.055 + .006 * span),
            V(.014 * toe, -.010, -.069 + .006 * span), V(.014 * toe, -.021, -.068 + .006 * span),
        )
        g.loft([v * size for v in path], [size * r for r in (.007, .006, .004, .001)],
               sides=10, density=3, up=UP)


PARTS = [
    Part("flukes_cetacean", "tail", "Paired horizontal swept flukes with a medial notch.",
         ["cetacean", "whale", "dolphin", "swimming", "fluke"],
         {"span": (.3, 2.4, 1.05), "chord": (.09, .55, .29)}, flukes_cetacean,
         orient="native", symmetry="center", hint={"u": .015, "theta": 90.0}),
    Part("dolphin_gape", "mouth", "Shallow lip seam for a closed bottlenose rostrum.",
         ["cetacean", "dolphin", "lip", "rostrum"], {"size": (.45, 1.6, 1)},
         dolphin_gape, orient="native", symmetry="pair", hint={"u": .86, "theta": -16.0}),
    Part("dolphin_dorsal", "locomotion", "Falcate bottlenose dorsal fin with a wide base.",
         ["cetacean", "dolphin", "dorsal", "fin"], {"size": (.5, 1.8, 1)},
         dolphin_dorsal, orient="native", symmetry="center", hint={"u": .49, "theta": 90.0}),
    Part("bat_flight_wing", "wing", "Jointed mammalian membrane with tapered digit spars and a free thumb.",
         ["bat", "chiroptera", "membrane", "flight"], {"size": (.35, 2.4, 1),
         "chord": (.65, 1.4, 1), "thickness": (.65, 1.6, 1)}, bat_flight_wing,
         attach="limb", orient="native", cap="flap", preset=bat_wing_chain, symmetry="pair",
         hint={"u": .68, "theta": 4.0}),
    Part("bat_tail_membrane", "tail", "Triangular uropatagium between the splayed hindlimbs.",
         ["bat", "membrane", "uropatagium"], {"size": (.5, 1.8, 1)}, bat_tail_membrane,
         orient="native", symmetry="center", hint={"u": .06, "theta": -90.0}),
    Part("bat_hindfoot", "foot", "Small bat foot with five curled toes.", ["bat", "chiroptera"],
         {"size": (.6, 1.5, 1)}, bat_hindfoot, attach="tip", orient="native"),
]
