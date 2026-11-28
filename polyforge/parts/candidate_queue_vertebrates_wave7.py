"""Localized defensive, caudal and tarsal external morphology drafts."""

import math

from ..kit import UP, V, lerp
from . import Part
from .research_locomotion import _closed_rings


def contractile_defense_skirt(g, p):
    """Rounded dorsal shell envelope turning inward into a continuous ventral rim."""
    size, close = p["size"], p["close"]
    stations = ((.064, .29, .28), (.062, .54, .57), (.048, .80, .80),
                (.025, .96, .96), (-.001, 1., 1.), (-.030, .966, .973),
                (-.053, .858, .941), (-.068, .740, .884),
                (-.074, .680, .831), (-.069, .610, .762),
                (-.056, .550, .703), (-.025, .412, .511), (-.006, .220, .241))
    rings = []
    for index, (y, width, length) in enumerate(stations):
        taper = min(1., max(0., (index - 4) / 4.)) * close
        ring = []
        for j in range(44):
            angle = math.tau * j / 44
            x, z = math.cos(angle), math.sin(angle)
            draw = .11 * taper * (1. - abs(z) * .57)
            ring.append(V(.115 * width * x * (1. - .37 * taper),
                          y + taper * (draw * .24 + .011 * z * z),
                          .152 * length * z * (1. - .26 * taper)) * size)
        rings.append(ring)
    g.setup(finish="subsurf_low")
    g.slot("skin")
    _closed_rings(g, rings)
    g.slot("spines")
    for row, (y, width, length, count) in enumerate(((.046, .078, .107, 22),
                                                    (.022, .106, .133, 28),
                                                    (-.004, .116, .151, 30),
                                                    (-.027, .108, .143, 26))):
        for i in range(count):
            angle = (i + row * .29) * math.tau / count
            x, z = math.cos(angle), math.sin(angle)
            point = V(width * x, y, length * z)
            outward = V(x * (.66 + .15 * row), (1.0 - .21 * row), z * .70).normalized()
            sweep = V(.004 * z, .003, -.005)
            reach = .016 + .0032 * math.sin(i * 2.62 + row)
            g.loft([v * size for v in (point - outward * .006, point + outward * (.49 * reach),
                                       point + outward * reach + sweep)],
                   [r * size for r in (.0023, .0017, .00039)], sides=8, density=2)


def posterior_burrow_plug(g, p):
    """Broad caudal pelvis patch with a single uninterrupted rear contact envelope."""
    size, tuck = p["size"], p["tuck"]
    stations = (
        (.100, .108, -.106, .105), (.076, .133, -.126, .135),
        (.034, .155, -.144, .153), (-.013, .169, -.147, .160),
        (-.058, .168, -.141, .151), (-.087, .156, -.120, .134),
        (-.104, .127, -.092, .113), (-.115, .084, -.051, .087),
        (-.120, .034, -.009, .049),
    )
    rings = []
    for z, width, bottom, top in stations:
        ring = []
        lower = tuck * (.022 + .010 * max(0., -z / .12))
        for i in range(38):
            angle = math.tau * i / 38
            x, v = math.cos(angle), math.sin(angle)
            spread = math.copysign(abs(x) ** .73, x)
            edge = math.copysign(abs(v) ** .82, v)
            y = lerp(bottom, top, .5 + .5 * edge)
            y += lower * max(0., -v) ** 1.2 * (abs(x) + .65)
            ring.append(V(width * spread * (1. - .08 * v), y,
                          z + .020 * (1. + v) * abs(x) ** 2.8) * size)
        rings.append(ring)
    g.setup(finish="subsurf_low")
    g.slot("skin")
    _closed_rings(g, rings)


def hollow_quill_rattle(g, p):
    """A distal tail patch with bell-ended quills on slender individual peduncles."""
    size, spread = p["size"], p["spread"]
    g.setup(finish="subsurf_low")
    g.slot("skin")
    g.loft([V(*v) * size for v in ((0., .002, .022), (0., 0., .006),
                                 (0., -.002, -.011), (0., -.004, -.018))],
           [(w * size, h * size) for w, h in ((.015, .013), (.019, .016),
             (.016, .010), (.009, .005))], sides=18, density=3)
    g.slot("quills")
    for i in range(8):
        angle = i * math.tau / 8
        skew = spread * (.19 + .11 * (i % 3))
        root = V(.0085 * math.cos(angle), -.003 + .0062 * math.sin(angle), -.010)
        direction = V(skew * math.cos(angle), skew * math.sin(angle), -1.).normalized()
        across = UP.cross(direction).normalized()
        upright = direction.cross(across).normalized()
        length = .030 + .0033 * (i % 3)
        width = .0039 + .00048 * (i % 3)
        stations = ((-.10, .16), (.03, .18), (.25, .24), (.43, .42),
                    (.58, .76), (.78, 1.), (.98, .89), (1., .82),
                    (.97, .66), (.78, .79), (.62, .55), (.51, .29), (.49, .12))
        rings = []
        for t, radius in stations:
            point = root + direction * (length * t) + upright * (.0035 * t * t)
            rings.append([
                (point + width * radius * (math.cos(j * math.tau / 16) * across
                          + math.sin(j * math.tau / 16) * upright * .87)) * size
                for j in range(16)
            ])
        _closed_rings(g, rings)


def _annular_sheath(g, rings):
    """Join the last inner ring to the outer near-side lip, leaving a real bore."""
    sides = len(rings[0])
    verts = [v for ring in rings for v in ring]
    faces = []
    for i in range(len(rings)):
        next_ring = (i + 1) % len(rings)
        for j in range(sides):
            k = (j + 1) % sides
            faces.append((i * sides + j, i * sides + k, next_ring * sides + k,
                          next_ring * sides + j))
    volume = sum(verts[a].dot(verts[b].cross(verts[c])) + verts[a].dot(verts[c].cross(verts[d]))
                 for a, b, c, d in faces)
    if volume < 0:
        faces = [tuple(reversed(face)) for face in faces]
    g.current._add(verts, faces)


def tarsal_spur_socket(g, p):
    """Caudomedial tarsal socket, bony core and surrounding keratin sheath."""
    size, length = p["size"], p["length"]
    g.setup(finish="subsurf_low")
    g.slot("skin")
    g.loft([V(*pt) * size for pt in ((0., -.041, .005), (0., -.020, .003),
             (.002, .004, .001), (.004, .027, -.001), (.005, .042, -.002))],
           [(w * size, h * size) for w, h in ((.009, .010), (.011, .011),
            (.012, .011), (.011, .010), (.010, .009))],
           sides=16, density=3, up=V(0, 0, 1))
    g.slot("spur_core")
    root = V(-.004, -.011, -.004)
    direction = V(-.78, .10, -.61).normalized()
    across = UP.cross(direction).normalized()
    upright = direction.cross(across).normalized()
    for end, width, height in ((.15, .0067, .0092), (.72, .0038, .0048)):
        start = root + direction * (-.003 if end < .2 else .002)
        tip = root + direction * (.032 * length * end) + upright * (.004 * end)
        g.loft([v * size for v in (start, start.lerp(tip, .6), tip)],
               [(width * k * size, height * k * size) for k in (.80, 1., .27)],
               sides=14, density=3, up=upright)
    g.slot("sheath")
    rings = []
    stations = ((.06, .95), (.15, 1.), (.32, .87), (.58, .71),
                (.81, .47), (1., .17), (1.03, .09), (.96, .045),
                (.57, .43), (.34, .66), (.10, .74), (.062, .72))
    for t, width in stations:
        point = root + direction * (.033 * length * t) + upright * (.008 * t * t)
        rings.append([
            (point + .0072 * width * (math.cos(i * math.tau / 16) * across
                + math.sin(i * math.tau / 16) * upright * 1.06)) * size for i in range(16)
        ])
    _annular_sheath(g, rings)


PARTS = [
    Part("contractile_defense_skirt", "aesthetics", "Draft spiny dorsal skirt with a contracting ventral lip.",
         ["hedgehog", "skirt", "spines", "roll"], {"size": (.45, 2., 1.), "close": (0., 1., .74)},
         contractile_defense_skirt, orient="native", host="body", symmetry="center"),
    Part("posterior_burrow_plug", "aesthetics", "Draft rounded wombat rump shield with a tucked underside.",
         ["wombat", "rump", "caudal", "shield", "burrow"], {"size": (.45, 2., 1.), "tuck": (0., 1., .48)},
         posterior_burrow_plug, orient="native", host="body", symmetry="center", hint={"u": .08, "theta": 90.}),
    Part("hollow_quill_rattle", "aesthetics", "Draft tail patch with hollow quill bells on independent stalks.",
         ["porcupine", "quill", "rattle", "tail"], {"size": (.45, 2., 1.), "spread": (.15, 1., .68)},
         hollow_quill_rattle, orient="native", host="body", symmetry="center", hint={"u": .06, "theta": 90.}),
    Part("tarsal_spur_socket", "aesthetics", "Draft tarsal segment with caudomedial spur core and sheath.",
         ["chicken", "fowl", "tarsal", "spur", "sheath"], {"size": (.45, 2., 1.), "length": (.70, 1.25, 1.)},
         tarsal_spur_socket, orient="native", host="limb", symmetry="pair"),
]
