"""Additional isolated vertebrate cranial and cervical attachments."""

from math import cos, exp, pi, sin

from ..kit import V, smoothstep
from . import Part
from .research_aesthetics import _closed_sections

SIZE = (.65, 1.65, 1.)
FRONT = {"u": .94, "theta": -90}


def radial_acoustic_face_disc(g, p):
    """Continuous shallow facial ruff with a radial fringe and lateral recesses."""
    size, spread, cup = p["size"], p["spread"], p["cup"]
    angles = [2 * pi * i / 100 for i in range(100)]
    # The crest notch above the eyes and the pointed medial lower seam are
    # part of a single heart-shaped perimeter.
    outline = [(.1504 * (.78 * sin(a) ** 3 + .22 * sin(a)) * spread,
                .0094 * (13.7 * cos(a) - 3.4 * cos(2 * a) - 1.3 * cos(3 * a) - .65 * cos(4 * a)) + .014)
               for a in angles]
    sections = ((.18, -.032), (.38, -.025), (.65, -.016), (.86, -.005), (.97, .005),
                (1., .017), (.984, .031), (.934, .035), (.86, .030), (.77, .015),
                (.63, .001), (.47, -.002), (.29, -.004), (.11, -.004))
    rings = []
    for index, (r, height) in enumerate(sections):
        points = []
        for a, (x, y) in zip(angles, outline):
            xx, yy = x * r, y * r
            relief = sin(36 * a + 6 * r) * .0018 * max(0, 1 - abs(r - .866) / .27)
            asym_offset = .015 if xx >= 0 else -.015
            ear = exp(-((abs(xx) - .094 * spread) / .027) ** 2 - ((yy - asym_offset) / .031) ** 2)
            z = height if index < 6 else height * cup + relief - .009 * ear
            points.append((xx, yy, z))
        rings.append(points)
    g.setup(finish="direct")
    _closed_sections(g, rings, (0, 0, -.035), (0, 0, -.004), size)


def bill_supported_hollow_casque(g, p):
    """Pneumatized casque shell with a broad underside seat on the bill."""
    size, height, length = p["size"], p["height"], p["length"]
    stations = ((-.094, .028, -.011, .037), (-.073, .047, -.009, .060),
                (-.039, .059, -.006, .083), (.001, .064, -.003, .098),
                (.040, .069, -.004, .107), (.079, .065, -.009, .110),
                (.112, .061, -.018, .107), (.141, .056, -.024, .101),
                (.159, .049, -.028, .096), (.169, .040, -.028, .089))
    angles = [pi - pi * i / 38 for i in range(39)]
    rings = []
    for z, width, base, top in stations:
        outer = []
        inner = []
        end_wall = max(.82 * (1 - smoothstep(-.094, -.039, z)), smoothstep(.124, .169, z))
        for a in angles:
            # The roof is asymmetric in profile and has two subtle raised shoulders.
            shoulder = .014 * (abs(cos(a)) ** 2) * sin(a) * max(0, (z + .045) / .22)
            forward_concavity = .018 * exp(-((z - .164) / .027) ** 2) * sin(a) ** 4
            roof = (top - base) * sin(a) ** .53 + shoulder
            x, y = width * cos(a), base + height * roof
            outer.append((x, y, length * (z - forward_concavity)))
            inside_roof = height * roof * (1 - end_wall)
            inner.append((x * .84, base + inside_roof - .009 - .006 * sin(a),
                          length * (z - forward_concavity)))
        rings.append(outer + inner[::-1])

    count = len(rings[0])
    points = [V(point) * size for ring in rings for point in ring]
    faces = []
    for ring in range(len(rings) - 1):
        start = ring * count
        for i in range(count):
            nxt = (i + 1) % count
            faces.append((start + i, start + count + i, start + count + nxt, start + nxt))
    back = (len(rings) - 1) * count
    for i in range(count // 2 - 1):
        cap = (i, i + 1, count - 2 - i, count - 1 - i)
        faces.append(cap)
        faces.append(tuple(back + index for index in reversed(cap)))
    g.setup(finish="subsurf_low")
    g._add(points, faces)


def paired_cervical_display_sacs(g, p):
    """Two separately rimmed throat membranes with a preserved medial gap."""
    size, inflate, broad = p["size"], p["inflate"], p["broad"]
    angles = [pi / 2 - 2 * pi * i / 52 for i in range(52)]
    levels = ((.21, -.018), (.48, -.016), (.69, -.012), (.87, -.007),
              (.97, -.002), (1.0, 0.), (.977, .003), (.915, .012),
              (.80, .027), (.63, .044), (.44, .055), (.19, .064))
    g.setup(finish="direct")
    for side in (-1, 1):
        rings = []
        for r, z in levels:
            depth = z * (.17 + .83 * inflate) if z > .004 else z
            outline = []
            for a in angles:
                x = .068 + (.046 + .006 * inflate) * broad * r * cos(a)
                y = .066 * r * sin(a) + .018 * r * cos(a)
                outline.append((side * x, y, depth - .18 * (x - .068)))
            rings.append(outline if side > 0 else outline[::-1])
        _closed_sections(g, rings, (side * .068, 0, -.0185),
                         (side * .068, 0, .065 * (.17 + .83 * inflate)), size)


def ventral_protrusible_suction_mouth(g, p):
    """Constricted throat collar extending down to a flattened oral lip ring."""
    size, reach, flare = p["size"], p["reach"], p["flare"]
    stations = ((-.036, .036, .022), (-.022, .046, .025), (-.009, .050, .025), (.006, .045, .022),
                (.022, .040, .019), (.040, .049, .022), (.052, .058, .027), (.060, .063, .028),
                (.067, .061, .026), (.071, .051, .018), (.066, .042, .012), (.057, .037, .009),
                (.043, .029, .008), (.027, .020, .007), (.017, .008, .004))
    angles = [pi / 2 - 2 * pi * i / 56 for i in range(56)]
    # Local opening normal is slightly forward of strictly ventral.
    def position(x, y, z):
        return (x, -.935 * z + .355 * y, .355 * z + .935 * y)

    rings = []
    for z, w, height in stations:
        flared = 1 + (flare - 1) * min(1., max(0., z / .052))
        extension = z * (.37 + .63 * reach) if z > 0 else z
        rings.append([position(w * flared * cos(a), height * flared * sin(a),
                               extension + .008 * (1 - reach) * cos(2 * a))
                      for a in angles])
    g.setup(finish="direct")
    _closed_sections(g, rings, position(0, 0, -.041), position(0, 0, .015 * (.37 + .63 * reach)), size)


PARTS = [
    Part("radial_acoustic_face_disc", "sensory", "Continuous heart-shaped facial ruff with a radial feather wall.",
         ["barn owl", "facial disc", "ruff", "directional hearing"],
         {"size": SIZE, "spread": (.87, 1.19, 1.), "cup": (.75, 1.26, 1.)},
         radial_acoustic_face_disc, orient="forward", hint=FRONT, symmetry="center"),
    Part("bill_supported_hollow_casque", "aesthetics", "Hollow casque shell spanning the forehead and upper bill.",
         ["great hornbill", "casque", "bill saddle", "cranial display"],
         {"size": SIZE, "height": (.78, 1.24, 1.), "length": (.76, 1.21, 1.)},
         bill_supported_hollow_casque, orient="native", hint={"u": .95, "theta": 90}, symmetry="center"),
    Part("paired_cervical_display_sacs", "aesthetics", "Paired cervical membranes inflate through separate openings.",
         ["sage grouse", "air sac", "display", "neck"],
         {"size": SIZE, "inflate": (0., 1., .82), "broad": (.83, 1.13, 1.)},
         paired_cervical_display_sacs, orient="forward", hint={"u": .8, "theta": -90}, symmetry="center"),
    Part("ventral_protrusible_suction_mouth", "feeding", "Elliptical ventral mouth with a protruding collar.",
         ["sturgeon", "suction", "mouth", "protrusion"],
         {"size": SIZE, "reach": (0., 1., .82), "flare": (.78, 1.20, 1.)},
         ventral_protrusible_suction_mouth, orient="native", hint={"u": .95, "theta": -90}, symmetry="center"),
]
TRAITS = {
    "radial_acoustic_face_disc": {"function": "sense", "construction": "deformable", "shape": "heart-shaped radial ruff and lateral recesses"},
    "bill_supported_hollow_casque": {"function": "display", "construction": "rigid", "shape": "arched shell across the upper bill"},
    "paired_cervical_display_sacs": {"function": "display", "construction": "deformable", "shape": "paired volume-changing throat membranes"},
    "ventral_protrusible_suction_mouth": {"function": "feed", "construction": "deformable", "shape": "ventral oral collar with flared tube"},
}
