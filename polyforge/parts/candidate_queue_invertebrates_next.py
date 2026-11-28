"""Perforated shell, annelid fittings and exposed aquatic invertebrate surfaces."""

from collections import Counter
from math import cos, exp, pi, sin, tau

from ..kit import RIGHT, UP, V, lerp, smoothstep
from . import Part
from .candidate_invertebrate import _sized
from .research_locomotion import _closed_rings


def _thick_surface(g, upper, lower, surface_faces):
    """Connect opposed face sheets along their exposed outline and any holes."""
    count = len(upper)
    edge_uses = Counter(tuple(sorted((a, b))) for face in surface_faces
                        for a, b in zip(face, face[1:] + face[:1]))
    faces = list(surface_faces)
    faces.extend(tuple(count + index for index in reversed(face)) for face in surface_faces)
    for face in surface_faces:
        for a, b in zip(face, face[1:] + face[:1]):
            if edge_uses[tuple(sorted((a, b)))] == 1:
                faces.append((b, a, a + count, b + count))
    vertices = upper + lower
    volume = sum(vertices[a].dot(vertices[b].cross(vertices[c]))
                 for a, *tail in faces for b, c in zip(tail, tail[1:]))
    if volume < 0:
        faces = [tuple(reversed(face)) for face in faces]
    g._add(vertices, faces)


def perforated_shell_vent_row(g, p):
    vertices = []
    lower = []
    faces = []
    seen = {}
    # Build both shell skins around the same pore loops. Tile edges coincide
    # exactly so the vent section is a solid boundary with four through-holes.
    def vertex(x, z, lift=0.):
        key = (round(x, 9), round(z, 9))
        if key not in seen:
            seen[key] = len(vertices)
            curve = -p["curvature"] * (.26 * x + 3.5 * x * x + 1.3 * z * z)
            vertices.append(V(x, curve + lift, z))
            lower.append(V(x, curve - .0022 + .33 * lift, z))
        return seen[key]

    for pore, (start, end) in enumerate(zip((-.056, -.035, -.010, .017, .041, .061),
                                            (-.035, -.010, .017, .041, .061, .078))):
        center = (start + end) / 2
        base = None
        for radial, lift in ((1., 0.), (.76, .00055), (.48, .0024), (.36, .0017)):
            current = []
            for index in range(32):
                side, step = divmod(index, 8)
                t = step / 8
                edge_x, edge_z = ((1., lerp(-1., 1., t)), (lerp(1., -1., t), 1.),
                                  (-1., lerp(1., -1., t)), (lerp(-1., 1., t), -1.))[side]
                denominator = (edge_x**2 + edge_z**2) ** .5
                smoothing = 1. - smoothstep(.48, 1., radial)
                x = lerp(edge_x, edge_x / denominator, smoothing) * radial * .018
                z = center + lerp(edge_z, edge_z / denominator, smoothing) * radial * (end - start) / 2
                x += .002 * sin(18 * z) * (1 - radial)
                relief = lift * (1. if pore < 4 else .27)
                current.append(vertex(x, z, relief))
            if base is not None:
                faces.extend((base[i], base[(i + 1) % 32], current[(i + 1) % 32], current[i])
                             for i in range(32))
            base = current
        if pore > 3:
            faces.append(tuple(base))
    g.slot("shell")
    _thick_surface(g, vertices, lower, faces)


def stalked_tube_operculum(g, p):
    height = .016 * p["extension"]
    base = V(.0035 * p["extension"], height, 0)
    g.slot("peduncle")
    g.loft([V(0, -.002, 0), V(-.0015, height * .34, .0004), base],
           [.00105, .00093, .00135], sides=18)
    g.slot("stopper")
    rings = []
    for y, radius, relief in ((-.001, .0011, 0.), (0., .0016, 0.), (.0011, .0028, .06),
                              (.0023, .0045, .09), (.0034, .0057, .16), (.004, .0059, .21),
                              (.0040, .0055, .18), (.00335, .00455, .20), (.00245, .0032, .16),
                              (.00165, .00155, .06), (.00163, .00055, 0.)):
        ring = []
        for column in range(144):
            angle = tau * column / 144
            serration = (.5 + .5 * cos(36 * angle)) ** 1.25
            r = radius * p["rim"] * (1. - relief * .19 + relief * .24 * serration)
            ring.append(base + V(r * cos(angle), y + relief * .0018 * serration, r * sin(angle)))
        rings.append(ring)
    _closed_rings(g, rings)


def bifid_proboscis_gutter(g, p):
    upper = []
    lower = []
    index_by_station = {}
    faces = []
    split = 23
    for side in (1, -1):
        grid = []
        for station in range(43):
            t = station / 42
            row = []
            for column in range(15):
                across = column / 14
                seam = station <= split and column == 0
                key = (station, column, 0 if seam else side)
                if key not in index_by_station:
                    index_by_station[key] = len(upper)
                    z = lerp(-.006, .169, t)
                    crest = smoothstep(.45, .69, t)
                    flare = crest * (.013 + .020 * sin(pi * max(0., (t - .45) / .55)))
                    split_extent = .031 * smoothstep(split / 42, .83, t) * p["splay"]
                    width = lerp(.005, flare, crest) * (1. - .96 * smoothstep(.83, 1., t))
                    x = side * (split_extent + width * across)
                    z -= .019 * (split_extent / .031) ** 1.4
                    base_y = .010 * t**2 + .006 * crest * across**2
                    wall = .0012 + .0016 * (1 - across**2) * (1. - .76 * crest)
                    gutter_line = lerp(.87, .51, crest)
                    trough = .0016 * exp(-((across - gutter_line) / .18) ** 2) * (1 - .83 * smoothstep(.92, 1., t))
                    upper.append(V(x, base_y + wall, z))
                    lower.append(V(x, base_y - wall + trough, z))
                row.append(index_by_station[key])
            grid.append(row)
        for base, tip in zip(grid, grid[1:]):
            for column in range(14):
                face = (base[column], tip[column], tip[column + 1], base[column + 1])
                faces.append(face if side > 0 else tuple(reversed(face)))
    g.slot("proboscis")
    _thick_surface(g, upper, lower, faces)


def septate_coral_polyp_cup(g, p):
    rings = []
    sections = (
        (.008, -.002, 0.), (.011, 0., 0.), (.012, .003, 0.), (.011, .006, 0.),
        (.015, .011, 0.), (.019, .018, 0.), (.021, .023, 0.), (.0213, .025, 0.),
        (.0201, .0253, .0003), (.0189, .0257, .0027), (.0181, .0247, .0056),
        (.0173, .0220, .0120), (.0160, .0169, .0110), (.0133, .011, .0093),
        (.0086, .0067, .0068), (.0046, .0065, .0020), (.0019, .0088, .0004),
    )
    for radius, height, reach in sections:
        ring = []
        for index in range(288):
            theta = tau * index / 288
            stripe = (.5 + .5 * cos(48 * theta)) ** 8
            cycle = .68 + .21 * cos(24 * theta) + .10 * cos(12 * theta)
            outside = 1. - smoothstep(.0001, .001, reach)
            r = radius * (1. + .019 * cos(48 * theta) * outside)
            r -= p["septa"] * reach * cycle * stripe
            y = height + .00035 * cos(3 * theta) + .00064 * stripe * smoothstep(.002, .007, reach)
            ring.append(V(1.10 * r * cos(theta), y, r * sin(theta)))
        rings.append(ring)
    g.slot("corallite")
    _closed_rings(g, rings)


def sheathed_tentacle_with_tentilla(g, p):
    rings = []
    for z, radius in ((-.004, .0034), (-.0027, .0037), (0., .0033), (.0014, .0026),
                      (.0017, .0017), (.0011, .00125), (-.0027, .00105), (-.003, .00072)):
        rings.append([V(radius * cos(a), radius * .86 * sin(a), z)
                      for a in (tau * i / 24 for i in range(24))])
    g.slot("sheath_margin")
    _closed_rings(g, rings)

    out = p["extension"]

    def center(t):
        return V(.022 * (1 - cos(.85 * pi * t)) + .012 * t, .013 * sin(pi * t), lerp(-.002, .153, t) * out)

    g.slot("tentacle")
    steps = [i / 12 for i in range(13)]
    g.loft([center(t) for t in steps],
           [lerp(.0010, .00017, t) for t in steps], sides=12, density=2)
    g.slot("tentilla")
    for row in range(23):
        t = .115 + .036 * row
        seat = center(t)
        tangent = (center(t + .02) - seat).normalized()
        seat += tangent * .00025
        length = out * (.005 + .026 * sin(pi * t) ** 1.2)
        reach = V(.48, -.82, 0) * length
        base = seat.lerp(center(t - .015), .15)
        g.loft([base, seat + .48 * reach, seat + reach + tangent * (.35 * length)],
               [.00044 * (1. - .58 * t), .00030 * (1. - .55 * t), .00010],
               sides=8, up=RIGHT, density=3)


_SIZE = {"size": (.65, 1.50, 1.)}
PARTS = [
    Part("perforated_shell_vent_row", "aesthetics", "Curved abalone shell sector with a line of open and sealed vent collars.",
         ["abalone", "shell", "gill", "vent", "aperture"], {**_SIZE, "curvature": (.65, 1.45, 1.)},
         _sized(perforated_shell_vent_row), orient="native", host="body"),
    Part("stalked_tube_operculum", "aesthetics", "Stalk-borne serrated funnel that seats against a tubeworm tube opening.",
         ["serpulid", "tubeworm", "operculum", "closure", "peduncle"], {**_SIZE, "extension": (.43, 1.13, 1.), "rim": (.80, 1.24, 1.)},
         _sized(stalked_tube_operculum), orient="native", host="body"),
    Part("bifid_proboscis_gutter", "feeding", "Spoon-worm proboscis with a forked distal ribbon and surface particle grooves.",
         ["spoon worm", "echiurid", "bonellia", "proboscis", "gutter"], {**_SIZE, "splay": (.70, 1.32, 1.)},
         _sized(bifid_proboscis_gutter), orient="native", host="body", symmetry="center"),
    Part("septate_coral_polyp_cup", "aesthetics", "Cup coral skeleton with a thick wall and inward radial septa.",
         ["coral", "corallite", "septa", "polyp", "cup"], {**_SIZE, "septa": (.68, 1.18, 1.)},
         _sized(septate_coral_polyp_cup), orient="native", host="body", symmetry="center"),
    Part("sheathed_tentacle_with_tentilla", "feeding", "Comb jelly sheath outlet supporting a fine filament with a row of tentilla.",
         ["ctenophore", "comb jelly", "sea gooseberry", "sheath", "tentilla"], {**_SIZE, "extension": (.60, 1.25, 1.)},
         _sized(sheathed_tentacle_with_tentilla), orient="native", host="body"),
]

TRAITS = {
    "perforated_shell_vent_row": {"shape": "curved shell band with capped and open raised pores", "function": "breathe"},
    "stalked_tube_operculum": {"shape": "annulated funnel plug carried on a curved peduncle", "function": "protect",
                              "regions": {"peduncle": "deformable", "stopper": "rigid"}},
    "bifid_proboscis_gutter": {"shape": "forked ribbon with marginal feeding grooves", "construction": "deformable"},
    "septate_coral_polyp_cup": {"shape": "deep cup with inward radial septa on an attachment base", "function": "protect"},
    "sheathed_tentacle_with_tentilla": {"shape": "threadlike tentacle with lateral branches emerging from a sheath collar",
                                      "construction": "deformable"},
}
