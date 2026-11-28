"""Draft echinoderm and suspension-feeding anatomy in the +Y-up part frame."""
import math

from scipy.interpolate import PchipInterpolator

from . import Part
from .research_feeding import _closed_sections
from ..kit import RIGHT, UP, V, lerp, smoothstep


def _radial(angle):
    return V(math.cos(angle), 0., math.sin(angle))


def _sized(sculpt):
    def build(g, p):
        g.setup(finish="direct")
        sculpt(g, p)
        for primitive in g.current.prims:
            primitive.v = [vertex * p["size"] for vertex in primitive.v]
    return build


# Five broadly based rays. Each station is (angle from a ray axis, radius).
_STAR_ANGLES = (0., 1.3, 2.7, 5., 10., 19., 28., 36.)
_STAR_RADIUS = (.520, .518, .506, .452, .342, .229, .174, .154)
_STAR_OUTLINE = PchipInterpolator(
    tuple(-angle for angle in reversed(_STAR_ANGLES[1:])) + _STAR_ANGLES,
    _STAR_RADIUS[:0:-1] + _STAR_RADIUS,
)
# Allocate angular samples near the ray axis for the tip and ambulacral relief.
_STAR_SAMPLES = (0., 1.3, 2.7, 4.2, 6., 8.2, 10.8, 14., 17.5, 21.6, 26.1, 31., 36.)
_STAR_SECTOR = tuple(-angle for angle in reversed(_STAR_SAMPLES[1:])) + _STAR_SAMPLES[:-1]


def _star_height(point, radius, ray_angle, fraction, upper):
    envelope = max(0., 1. - fraction ** 4.5) ** .54
    lateral = abs(radius * math.sin(math.radians(ray_angle)))
    along = radius * math.cos(math.radians(ray_angle))
    if upper:
        sieve_radius = ((point.x - .070) / .018) ** 2 + ((point.z - .052) / .014) ** 2
        sieve = .014 * math.exp(-sieve_radius ** 2)
        return (.057 - .034 * smoothstep(.08, .52, radius) + sieve) * envelope
    groove_width = lerp(.023, .012, smoothstep(.17, .51, along))
    groove = .021 * math.exp(-((lateral / groove_width) ** 4)) * smoothstep(.046, .088, along)
    mouth = .024 * math.exp(-(radius / .028) ** 6)
    mouth_lip = -.0068 * math.exp(-((radius - .034) / .008) ** 2)
    margin = -.008 * math.exp(-((lateral - groove_width * 1.38) / .009) ** 2) * smoothstep(.055, .105, along)
    return (-.038 + .011 * smoothstep(.12, .52, radius) + groove + mouth + mouth_lip + margin) * envelope


def _star_relief(primitive, spans):
    """Replace selected shell quads with integrated blunt ossicle relief."""
    columns = len(_STAR_SECTOR)
    sides = 5 * columns
    far_ring = 2 * spans - 2
    patches = {}
    for ray in range(5):
        offset = ray * columns
        for row in (2, 5, 8, 11, 14, 17, 20, 23, 26):
            for column in (6, 8, 11, 14, 17):
                stagger = (row + column + ray) % 2
                patches[(row + stagger) * sides + offset + column] = .0095
        for row in (6, 9, 12, 15, 18, 21, 24):
            for column in (8, 15):
                patches[(far_ring - row - 1) * sides + offset + column] = -.009
    vertices = primitive.v
    faces = []
    for index, face in enumerate(primitive.f):
        lift = patches.get(index)
        if lift is None:
            faces.append(face)
            continue
        corners = [vertices[corner] for corner in face]
        center = sum(corners, V(0, 0, 0)) / len(corners)
        along = ((corners[1] - corners[0]) + (corners[2] - corners[3])) / 2
        across = ((corners[3] - corners[0]) + (corners[2] - corners[1])) / 2
        breadth = min(along.length, across.length) / 2
        u, v = along.normalized() * breadth, across.normalized() * breadth
        roof = (-u - v, u - v, u + v, -u + v)
        lift *= min(1., breadth / .004)
        outer = face
        for radius, height in ((.65, .32), (.29, .78)):
            inner = tuple(range(len(vertices), len(vertices) + 4))
            vertices.extend(center + corner * radius + UP * lift * height for corner in roof)
            for edge in range(4):
                following = (edge + 1) % 4
                faces.append((outer[edge], outer[following], inner[following], inner[edge]))
            outer = inner
        tip = len(vertices)
        vertices.append(center + UP * lift)
        faces.extend((outer[edge], outer[(edge + 1) % 4], tip) for edge in range(4))
    primitive.f = faces


def sea_star_rayed_core(g, p):
    g.slot("skin")
    rings = []
    spans = 31
    for upper, sections in ((True, range(1, spans + 1)), (False, range(spans - 1, 0, -1))):
        for step in sections:
            fraction = math.sin(math.pi * step / (2 * spans))
            ring = []
            for ray in range(5):
                axis = math.pi / 2 - math.tau * ray / 5
                tangent = UP.cross(_radial(axis))
                for ray_angle in _STAR_SECTOR:
                    direction = _radial(axis - math.radians(ray_angle))
                    extent = lerp(.154, float(_STAR_OUTLINE(ray_angle)), p["reach"])
                    radius = extent * fraction
                    skew = .018 * math.sin(2.4 * ray + .7) * smoothstep(.15, .52, radius)
                    point = direction * radius + tangent * skew
                    point.y = _star_height(point, radius, ray_angle, fraction, upper)
                    ring.append(point)
            rings.append(ring)
    _closed_sections(g, rings, (0, .057, 0), (0, -.014, 0))
    _star_relief(g.current.prims[-1], spans)


def ambulacral_tube_feet(g, p):
    # This is an oral groove segment. Two rows lie either side of its midline.
    # +Z follows the arm distally; retraction changes travel below the root plane.
    for row, x in enumerate((-.035, -.012, .012, .035)):
        for step in range(7):
            z = -.134 + step * .040 + (row % 2) * .018
            root = V(x * (1.0 - .18 * z / .134), 0, z)
            length = p["extension"] * (.086 + .011 * math.sin(step * 2.064 + row))
            reach = V(math.copysign(.14 * length, x), -length,
                      .14 * length * math.sin(step * 1.63 + row))
            # One connected column with a flattened flaring end, including its contact face.
            g.loft([root + UP * .006, root + reach * .21, root + reach * .66,
                    root + reach * .90, root + reach * .96, root + reach],
                   [.0067, .0057, .0044, .0040, .0089, .0091],
                   sides=14, up=RIGHT, density=3)
            # Flatten the loft cap into the contact face.
            g.current.prims[-1].v[-1] = root + reach * 1.003


def asteroid_pedicellaria(g, p):
    # The crossed type forms the wreath. The larger, scattered straight type
    # is a separate skeletal shape. One spine, whose insertion is at origin,
    # can be placed inside this wreath by the host.
    for index in range(10):
        direction = _radial(math.tau * index / 10)
        tangent = UP.cross(direction)
        root = direction * (.020 + .0016 * math.cos(index * 1.89))
        stem = UP * (.010 + .003 * math.sin(index * 2.06)) + direction * .006
        g.loft([root - UP * .004, root + stem * .44, root + stem],
               [.0025, .0022, .0027], sides=10, up=RIGHT, density=2)
        hinge = root + stem
        for side in (-1., 1.):
            # Cross the blades in projection, with each valve on its own
            # radial side of the hinge. Both distal hooks turn toward the gap.
            points = [
                hinge + tangent * (-side * .003) + direction * (side * .0021) - UP * .002,
                hinge + tangent * (side * .0024) + direction * (side * .0023) + UP * .0026,
                hinge + tangent * (side * .0072 * p["gape"]) + UP * .0067,
                hinge + tangent * (side * .0067 * p["gape"]) + UP * .0107,
                hinge + tangent * (side * .0041 * p["gape"]) + UP * .0122,
            ]
            g.loft([hinge + .70 * (point - hinge) for point in points],
                   [(.0014, .0011), (.0016, .0011), (.0017, .00085),
                    (.0010, .00057), (.00032, .00028)], sides=10, up=direction, density=3)


# This truncated profile describes the wall of the empty Arbacia test. It
# starts beside the aboral aperture and ends on the margin of the peristome.
_TEST_MERIDIAN = (
    (.054, .256), (.096, .255), (.161, .238), (.235, .205), (.305, .146),
    (.357, .066), (.378, -.016), (.366, -.094), (.327, -.156),
    (.289, -.179), (.251, -.198), (.212, -.196),
)
_TEST_PROFILE = PchipInterpolator(tuple(range(len(_TEST_MERIDIAN))), _TEST_MERIDIAN)
_TEST_TANGENT = _TEST_PROFILE.derivative()


def _test_position(angle, t, height):
    radius, y = _TEST_PROFILE(t * (len(_TEST_MERIDIAN) - 1))
    lobe_phase = 5 * angle
    radius *= 1.0 - .020 * math.cos(lobe_phase)
    radius += .015 * smoothstep(.86, 1., t) * (math.cos(lobe_phase) + .28 * math.cos(2 * lobe_phase))
    apical_rim = 1.0 - smoothstep(0., .085, t)
    radius *= 1.0 + apical_rim * (.09 * math.cos(2 * angle) - .055 * math.sin(3 * angle))
    direction = _radial(angle)
    point = direction * float(radius)
    point.y = float(y) * height
    dr, dy = _TEST_TANGENT(t * (len(_TEST_MERIDIAN) - 1))
    normal = (direction * float(-dy) + UP * float(dr / height)).normalized()
    return point, normal


_TEST_COLUMNS = 80
_TEST_ROWS = 52
_BOSS_ROWS = tuple(range(8, 49, 5))


def _test_bosses(rows):
    sector_width = _TEST_COLUMNS // 5
    for sector in range(5):
        for column in (-6, -3, 3, 6):
            for row in rows:
                yield (row + (column % 2), sector * sector_width + sector_width // 2 + column)


# Two narrow pore channels and four raised spine seats per sector. The
# wider cells between the bands reserve geometry for individually sculpted bosses.
_TEST_SECTOR_ANGLES = (0., 3.65, 4.75, 6.1, 11.9, 17.5, 27.5, 34.2, 37.8,
                       44.5, 54.5, 60.1, 65.9, 67.25, 68.35)
_TEST_BOSS_SECTORS = (3, 5, 9, 11)
_TEST_PORE_SECTORS = (1, 13)
_TEST_PORE_COUNT = 42


def _test_rows():
    dense = [0.]
    suture = [0.]
    interval = .871 / _TEST_PORE_COUNT
    for index in range(_TEST_PORE_COUNT):
        center = .083 + (index + .5) * interval
        dense.extend((center - .18 * interval, center + .18 * interval))
        suture.append(center)
    dense.append(1.)
    suture.append(1.)
    coarse = [0., .036, .074, .10]
    tubercle_cells = {}
    for row in _BOSS_ROWS:
        center = (row + .5) / _TEST_ROWS
        coarse.append(center - .033)
        tubercle_cells[len(coarse) - 1] = row
        coarse.append(center + .033)
    coarse.extend((.972, 1.))
    return dense, suture, coarse, tubercle_cells


def _test_boss(vertices, faces, panel, center, normal, high):
    a, b, c, d = (vertices[index] for index in panel)
    across = ((b - a) + (c - d)) * .5
    along = ((d - a) + (c - b)) * .5
    width = min(across.length * .43, along.length * .31, .0165)
    sideways = (across - normal * normal.dot(across)).normalized()
    meridional = normal.cross(sideways).normalized()
    rise = width * (.72 if high else .52) + .003
    ring = len(vertices)
    crown_segments = 8 if high else 4
    levels = ((8, 1., .21), (crown_segments, .64, .93))
    for count, radius, elevation in levels:
        for step in range(count):
            angle = math.pi * 1.25 + math.tau * step / count
            direction = sideways * math.cos(angle) + meridional * math.sin(angle)
            vertices.append(center + direction * (width * radius) + normal * (rise * elevation))
    cap = len(vertices)
    vertices.append(center + normal * rise)
    inner = ring + 8
    for step, corner in enumerate(panel):
        next_corner = panel[(step + 1) % 4]
        left, middle, right = (ring + (2 * step + offset) % 8 for offset in range(3))
        faces.extend(((corner, next_corner, middle), (corner, middle, left),
                      (next_corner, right, middle)))
    if high:
        for step in range(8):
            following = (step + 1) % 8
            faces.append((ring + step, ring + following, inner + following, inner + step))
    else:
        for step in range(4):
            following = (step + 1) % 4
            left, middle, right = (ring + (2 * step + offset) % 8 for offset in range(3))
            faces.extend(((left, middle, inner + step), (middle, right, inner + following),
                          (middle, inner + following, inner + step)))
    for step in range(crown_segments):
        following = (step + 1) % crown_segments
        faces.append((inner + step, inner + following, cap))


def urchin_test(g, p):
    g.slot("skin")
    dense, suture, coarse, tubercle_cells = _test_rows()
    sector_width = len(_TEST_SECTOR_ANGLES)
    columns = 5 * sector_width
    collar_columns = {column + offset for column in _TEST_PORE_SECTORS for offset in (0, 1)}
    stations = []
    for column in range(columns):
        sector, local_index = divmod(column, sector_width)
        local = _TEST_SECTOR_ANGLES[local_index]
        meridian = dense if local_index in collar_columns else suture if not local_index else coarse
        stations.append((sector * 72. + local, local, meridian))
    vertices = []
    lines = []
    for inside in (False, True):
        for bearing, local, meridian in stations:
            if not inside:
                lines.append(len(vertices))
            for row, progress in enumerate(meridian):
                # The alternating height of the two podial rows is a small
                # fraction of one pore spacing. Keep both end rims unshifted.
                phase = (.005 * (math.exp(-((local - 4.2) / 3.5) ** 2)
                                 - math.exp(-((local - 67.8) / 3.5) ** 2)))
                t = progress + phase * math.sin(math.pi * progress) ** .45
                point, normal = _test_position(math.radians(bearing), t, p["height"])
                if inside:
                    point -= normal * lerp(.014, .008, smoothstep(.84, 1., t))
                else:
                    axis = min(local, 72. - local)
                    channel = math.exp(-((axis - 4.2) / 2.3) ** 2)
                    relief = .0038 * channel - .0009 * math.exp(-(axis / 1.75) ** 2)
                    relief *= smoothstep(.045, .14, t) * (1. - smoothstep(.94, 1., t))
                    seam = .0013 if axis > 6. and (row in tubercle_cells or row - 1 in tubercle_cells) else 0.
                    point += normal * (relief - seam)
                vertices.append(point)
    wall_size = len(vertices) // 2
    faces = []
    for column, (_, local, left) in enumerate(stations):
        next_column = (column + 1) % columns
        _, next_local, right = stations[next_column]
        first, second = lines[column], lines[next_column]
        local_index = column % sector_width
        faces.append((second, first, first + wall_size, second + wall_size))
        i = j = 0
        while i + 1 < len(left) or j + 1 < len(right):
            u = left[i + 1] if i + 1 < len(left) else math.inf
            v = right[j + 1] if j + 1 < len(right) else math.inf
            a, b = first + i, second + j
            row = i
            if u == v:
                i, j = i + 1, j + 1
                panel = (a, b, second + j, first + i)
            elif u < v:
                i += 1
                panel = (a, b, first + i)
            else:
                j += 1
                panel = (a, b, second + j)
            if local_index in _TEST_PORE_SECTORS and row % 2:
                for step, edge in enumerate(panel):
                    following = panel[(step + 1) % len(panel)]
                    faces.append((edge, following, following + wall_size, edge + wall_size))
                continue

            faces.append(tuple(index + wall_size for index in reversed(panel)))
            if local_index in _TEST_BOSS_SECTORS and row in tubercle_cells:
                sector = column // sector_width
                bearing = math.radians(sector * 72. + .5 * (local + next_local))
                anchor_row = tubercle_cells[row] + (local_index in (5, 9))
                center, normal = _test_position(bearing, anchor_row / _TEST_ROWS, p["height"])
                _test_boss(vertices, faces, panel, center, normal, local_index in (3, 11))
            else:
                faces.append(panel)
        a, b = first + i, second + j
        faces.append((a, b, b + wall_size, a + wall_size))
    g._add(vertices, faces)


def urchin_radial_spines(g, p):
    g.slot("spines")
    # The larger primary spines seat on the raised interambulacral tubercles.
    # Each lower oral row is shorter, rounder-tipped and biased outward.
    for row, column in _test_bosses(_BOSS_ROWS):
        angle = math.tau * column / _TEST_COLUMNS
        t = row / _TEST_ROWS
        seat, normal = _test_position(angle, t, p["height"])
        radial = _radial(angle)
        tangent = UP.cross(radial)
        direction = (normal + tangent * (.17 * math.sin(column * .77 + row))
                     + radial * (.38 * smoothstep(.69, .86, t))).normalized()
        primary = 1.0 - .65 * smoothstep(.62, .86, t)
        if (row - column % 2 - _BOSS_ROWS[0]) % 10 == 0:
            primary *= .56 + .11 * math.sin(column * 2.07 + row) ** 2
        length = (.403 + .11 * math.sin(column * 1.17 + row) ** 2) * primary * p["length"]
        width = .0115 * primary ** .35
        oral = smoothstep(.73, .86, t)
        start = seat + normal * .0045
        bend = tangent * (.038 * math.sin(column + row) * length)
        g.loft([start, start + direction * .012, start + direction * .029,
                start + direction * (length * .41), start + direction * (length * .78) + bend,
                start + direction * length + bend],
               [width * .67, width, width * .77, width * .65,
                (width * .38, width * (.38 + .23 * oral)),
                (width * (.06 + .12 * oral), width * (.06 + .42 * oral))],
               sides=9, up=tangent, density=1)


def echinoid_oral_teeth(g, p):
    g.slot("teeth")
    # Oral-facing wedges converge at the lumen; the internal lantern
    # pyramids and the roots of the long teeth are inside the host.
    tip_radius = .009 + .015 * p["gape"]
    for index in range(5):
        angle = math.tau * index / 5
        radial = _radial(angle)
        points = [radial * r + UP * y for r, y in (
            (.074, .025), (.060, .010), (.043, -.007),
            (tip_radius + .009, -.021), (tip_radius, -.023))]
        g.loft(points, [(.016, .006), (.018, .007), (.015, .0058),
                        (.009, .0038), (.007, .0018)],
               sides=16, up=UP, exponent=.67, density=4)


def _collar(g, sections):
    """Closed annular collar whose bore remains open through both ends."""
    sides = 48
    vertices = [(_radial(math.tau * i / sides) * radius) + UP * y
                for radius, y in sections for i in range(sides)]
    faces = []
    for row in range(len(sections)):
        link = (row + 1) % len(sections)
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((row * sides + i, link * sides + i, link * sides + j, row * sides + j))
    g._add(vertices, faces)


def zooid_lophophore_crown(g, p):
    _collar(g, ((.029, -.017), (.039, -.004), (.046, .011), (.040, .021),
                (.031, .019), (.025, .009), (.023, -.015)))
    g.slot("tentacles")
    for index in range(12):
        angle = math.tau * index / 12
        radial = _radial(angle)
        tangent = UP.cross(radial)
        bow = p["flare"] * (1. + .04 * math.sin(index * 3.14 / 6))
        reach = .192 + .009 * math.sin(index * 1.17)
        points = [radial * (.039 + radius * bow) + UP * (y * reach)
                  + tangent * (.005 * y * y * math.sin(index + .65))
                  for radius, y in ((0, .05), (.013, .25), (.042, .52),
                                    (.080, .80), (.108, .94), (.119, 1.))]
        g.loft(points, [.0062, .0060, .0053, .0047, .0033, .0016],
               sides=12, up=radial, density=4)


def _pinnule(g, seat, bend, tip, up):
    # Seven vertices describe a short curved branch: two triangular
    # sections and a point. Smooth shading keeps the tiny taper legible.
    axis = (tip - seat).normalized()
    side = up.cross(axis).normalized()
    up = axis.cross(side)
    vertices = []
    for point, radius in ((seat, .00175), (bend, .00115)):
        for step in range(3):
            angle = math.tau * step / 3
            vertices.append(point + radius * (side * math.cos(angle) + up * math.sin(angle)))
    faces = [(2, 1, 0)]
    for index in range(3):
        next_index = (index + 1) % 3
        faces.extend(((index, next_index, next_index + 3, index + 3),
                      (index + 3, next_index + 3, 6)))
    g._add([*vertices, tip], faces)


def _branchial_lobe(g, p, start, sweep, inner):
    count = 17 if inner else 29
    roots = []
    for index in range(count):
        t = index / (count - 1)
        angle = start + sweep * t
        root_radius = lerp(.048, .024, t) if not inner else .035
        root = _radial(angle) * root_radius
        roots.append(root - UP * .005)
        reach = (.250 + .025 * math.sin(math.pi * t)) * (1. if inner else 1.17)
        spread = p["spread"] * (.152 if inner else lerp(.224, .116, t))

        def along(s):
            turn = (.26 if inner else .39) * s * s
            radial = _radial(angle + turn)
            return radial * (root_radius + spread * s ** 1.13) + UP * (
                reach * math.sin(math.pi * s * .62) + .010 * s)

        g.slot("radioles")
        heights = (0., .15, .31, .48, .65, .82, .94, 1.)
        g.loft([along(s) for s in heights], [.0052 * (1. - .87 * s) for s in heights],
               sides=6, up=_radial(angle), density=1)
        g.slot("pinnules")
        for branch in range(15):
            s = .17 + .052 * branch
            seat = along(s)
            distal = (along(s + .055) - seat).normalized()
            side_axis = distal.cross(_radial(angle)).normalized()
            inward = side_axis.cross(distal).normalized()
            length = (.035 if inner else .043) * math.sin(math.pi * s) ** .85
            for side in (-1., 1.):
                wing = side_axis * side * length
                bend = inward * (.60 * length) + distal * (.55 * length)
                _pinnule(g, seat, seat + .53 * wing + .25 * bend, seat + wing + bend, inward)
    g.slot("base")
    g.loft(roots, [.0065] * count, sides=6, up=UP, density=1)


def sabellid_radiolar_crown(g, p):
    # A Sabella spallanzanii-style asymmetrical crown. One lateral support
    # follows a deep spiral; the other stays a single short arc.
    _branchial_lobe(g, p, math.pi * .1, -math.pi * .91, True)
    _branchial_lobe(g, p, math.pi * .13, math.pi * 2.58, False)


_SIZE = {"size": (.6, 1.6, 1.)}
PARTS = [
    Part("sea_star_rayed_core", "locomotion", "Continuous five-rayed sea star core with oral grooves.",
         ["asterias", "echinoderm", "radial", "sea star"], {**_SIZE, "reach": (.85, 1.15, 1.)},
         _sized(sea_star_rayed_core), attach="core", orient="native", symmetry="radial"),
    Part("ambulacral_tube_feet", "locomotion", "Four staggered rows of padded tube feet for an oral groove.",
         ["asterias", "podium", "ambulacrum"], {**_SIZE, "extension": (.38, 1.12, 1.)},
         _sized(ambulacral_tube_feet), orient="native", symmetry="center", host="body"),
    Part("asteroid_pedicellaria", "manipulation", "Wreath of crossed-valve pedicellariae around a sea star spine.",
         ["asterias", "forceps", "wreath"], {**_SIZE, "gape": (.67, 1.15, 1.)},
         _sized(asteroid_pedicellaria), orient="native", host="body"),
    Part("urchin_test", "aesthetics", "Hollow sea urchin test with openings, foot pores, and skeletal tubercles.",
         ["arbacia", "echinoderm", "test"], {**_SIZE, "height": (.77, 1.08, .89)},
         _sized(urchin_test), attach="core", orient="native", symmetry="radial"),
    Part("urchin_radial_spines", "locomotion", "Tapered spine field for an oblate sea urchin test.",
         ["arbacia", "echinoderm", "spine"], {**_SIZE, "height": (.77, 1.08, .89), "length": (.74, 1.14, 1.)},
         _sized(urchin_radial_spines), orient="native", symmetry="radial", host="body"),
    Part("echinoid_oral_teeth", "feeding", "Five exposed tooth tips surrounding the sea urchin oral lumen.",
         ["arbacia", "echinoderm", "aristotle's lantern"], {**_SIZE, "gape": (.24, 1.0, .42)},
         _sized(echinoid_oral_teeth), orient="native", symmetry="radial", host="body"),
    Part("zooid_lophophore_crown", "feeding", "Single funnel of ciliated feeding tentacles on an oral collar.",
         ["hypophorella", "bryozoan", "zooid"], {**_SIZE, "flare": (.68, 1.17, 1.)},
         _sized(zooid_lophophore_crown), orient="native", symmetry="radial", host="body"),
    Part("sabellid_radiolar_crown", "feeding", "Paired fan-worm lobes with pinnulated and spirally arranged radioles.",
         ["sabellidae", "sabellid", "feather duster worm"], {**_SIZE, "spread": (.71, 1.12, 1.)},
         _sized(sabellid_radiolar_crown), orient="native", symmetry="radial", host="body"),
]


TRAITS = {
    "sea_star_rayed_core": {"shape": "five continuous tapered rays around a flattened disc",
                           "construction": "deformable", "regions": {"skin": "deformable"}},
    "ambulacral_tube_feet": {"shape": "four staggered rows of padded extensible podia",
                             "construction": "deformable", "regions": {"base": "deformable"}},
    "asteroid_pedicellaria": {"shape": "wreath of tiny crossed valves around one aboral spine",
                             "function": "protect"},
    "urchin_test": {"shape": "oblate plated enclosure with paired meridional pore rows",
                    "function": "protect", "regions": {"skin": "rigid"}},
    "urchin_radial_spines": {"shape": "radial field with stout pivot bases and shorter oral spines",
                             "regions": {"spines": "rigid"}},
    "echinoid_oral_teeth": {"shape": "five scraping tips around an oral aperture",
                            "regions": {"teeth": "rigid"}},
    "zooid_lophophore_crown": {"shape": "one open funnel of 12 simple tentacles around an oral collar",
                               "construction": "deformable"},
    "sabellid_radiolar_crown": {"shape": "two unequal lobes of curved, pinnulated radioles",
                                "construction": "deformable"},
}
