"""Isolated arthropod anatomy. Native frames use +Y dorsal and +Z anterior."""

import math

from ..kit import RIGHT, UP, V, rot
from . import Part
from .candidate_arthropod import SIZE, _loft, _station_strip
from .research_locomotion import _closed_rings


def split_waterline_compound_eye(g, p):
    """Two independent corneae wrap the dorsal and ventral sides of one seat."""
    g.setup(finish="direct")
    size = p["size"]
    # The cuticle is one continuous backing across the interocular bridge.
    rings = []
    for x, width, height, rake in (
        (-.100, .076, .080, -.009), (-.081, .123, .124, -.017),
        (-.039, .151, .148, -.019), (.010, .147, .148, -.016),
        (.049, .117, .121, -.010), (.071, .079, .083, -.006),
        (.079, .025, .034, 0.),
    ):
        ring = []
        for i in range(44):
            angle = math.tau * i / 44
            y = height * math.sin(angle)
            z = width * math.cos(angle) + rake * math.sin(angle)
            ring.append(V(x, y, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)
    for center, axes, lower in (
        ((.029, .076, .026), (.075, .088, .112), False),
        ((.038, -.078, -.030), (.113, .090, .130), True),
    ):
        cx, cy, cz = center
        wx, hy, dz = axes
        rings = []
        for step in range(1, 22):
            latitude = math.pi * step / 22
            x = cx - wx * .49 * math.cos(latitude)
            radial = math.sin(latitude)
            ring = []
            for index in range(48):
                angle = math.tau * index / 48
                y = cy + (hy + .012 * math.cos(angle)) * radial * math.cos(angle)
                z = cz + dz * radial * math.sin(angle)
                # Raise the corneal crown away from the interruption by the rim.
                crown = max(0, -math.cos(latitude)) ** 2
                x_shell = x + wx * .50 * crown
                y += (-1 if lower else 1) * hy * .35 * crown
                lobe_side = -1 if lower else 1
                y = lobe_side * max(.024 + .012 * max(0., math.sin(angle)), lobe_side * y)
                # The broad dome carries a low-relief faceted corneal surface.
                ripple = .00155 * crown * radial**2 * math.cos(index * math.tau / 3) * math.cos(step * math.tau / 3)
                ring.append(V(x_shell + ripple, y, z) * size)
            rings.append(ring)
        _closed_rings(g, rings)


def vertical_fang_chelicera(g, p):
    """A swollen basal segment surrounds the fold of a separately hinged fang."""
    g.setup(finish="direct")
    size = p["size"]
    rings = []
    for z, yc, breadth, depth, channel in (
        (-.103, .035, .038, .044, 0), (-.081, .033, .065, .070, .012),
        (-.035, .028, .078, .082, .034), (.029, .020, .081, .092, .046),
        (.093, .005, .074, .084, .049), (.146, -.003, .059, .064, .022),
        (.173, -.006, .040, .043, .002), (.184, -.006, .016, .027, 0),
    ):
        ring = []
        for index in range(40):
            angle = math.tau * index / 40
            v = math.sin(angle)
            x = breadth * math.cos(angle)
            y = yc + depth * v + (channel * (-v)**15 if v < 0 else 0.)
            ring.append(V(x, y, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)
    for side in (-1, 1):
        for i, z in enumerate((-.039, -.019, .002, .024, .046, .069, .093)):
            x = side * (.034 + .006 * math.sin(i * .6))
            y = -.047 - .018 * i / 6
            width = .0074 + .0018 * i / 6
            _loft(g, size, ((x, y + .009, z), (x * 1.05, y, z),
                            (x * .89, y - .008, z - .001)),
                  (width, width * .87, .0017), up=RIGHT, sides=11, density=3)
    pivot = V(0, -.048, .149)
    opening = rot(RIGHT, -math.radians(91 * p["open"]))
    _loft(g, size, [pivot + opening @ V(v) for v in (
        (0, .004, .022), (0, -.014, .010), (0, -.030, -.016),
        (0, -.035, -.050), (0, -.025, -.085), (0, -.007, -.125),
        (0, .009, -.154), (0, .019, -.166),
    )], ((.025, .026), (.026, .025), (.025, .023), (.021, .018),
         (.016, .013), (.010, .008), (.0049, .0038), (.0008, .0007)),
          up=RIGHT)


def sliding_sabre_ovipositor(g, p):
    """A narrow incurved blade has visible longitudinal valvulae on both sides."""
    g.setup(finish="direct")
    size = p["size"]
    _station_strip(g, size, (
        (.024, 0, -.006, .032, .041, 0), (-.009, 0, -.002, .046, .054, .002),
        (-.037, 0, 0, .045, .047, .004), (-.086, 0, .003, .026, .036, .009),
        (-.120, 0, .006, .016, .029, .008),
    ), V)
    levels = (
        (.014, .002, .045, .018), (-.040, -.002, .043, .023),
        (-.124, -.014, .035, .018), (-.233, -.012, .028, .015),
        (-.359, .003, .023, .013), (-.461, .022, .018, .010),
        (-.540, .044, .013, .007), (-.585, .061, .008, .004),
        (-.615, .073, .0015, .0016),
    )
    for side in (-1, 1):
        for valve, (vertical, width, outer) in enumerate((
            (.48, .57, .45), (-.48, .50, .34), (0., .43, .75),
        )):
            slip = (valve - 1) * p["slide"] * .023
            _station_strip(g, size, [
                (z + slip, side * depth * outer, y + height * vertical,
                 depth * width, height * (.61 if valve < 2 else .30), side * .001)
                for z, y, height, depth in levels
            ], V, sides=22)


def lateral_abdominal_display_flaps(g, p):
    """Thin bilateral display membranes unfurl from a rounded abdominal plate."""
    g.setup(finish="direct")
    size = p["size"]
    pitch = rot(RIGHT, math.radians(69))
    _station_strip(g, size, (
        (.030, 0, -.007, .026, .018, 0), (.004, 0, .006, .069, .028, .005),
        (-.044, 0, .016, .104, .036, -.005), (-.110, 0, .015, .117, .038, -.005),
        (-.174, 0, .011, .114, .035, -.004), (-.229, 0, .007, .097, .025, -.002),
        (-.266, 0, .003, .048, .015, -.005), (-.276, 0, .002, .012, .008, -.001),
    ), lambda v: pitch @ v)
    fold = rot(V(0, 0, 1), -math.radians(154 * (1 - p["spread"])))
    for side in (-1, 1):
        root_x = .101
        rings = []
        for x, y, z, chord, thick, curl in (
            (.077, -.006, -.132, .084, .010, -.005),
            (.106, .013, -.130, .109, .010, -.009),
            (.140, .006, -.143, .114, .008, -.008),
            (.171, .001, -.150, .103, .006, -.009),
            (.198, -.005, -.154, .083, .005, -.010),
            (.217, -.012, -.158, .060, .004, -.008),
            (.229, -.015, -.161, .036, .003, -.003),
            (.234, -.016, -.162, .014, .002, -.001),
            (.235, -.016, -.163, .004, .0012, 0),
        ):
            ring = []
            for i in range(32):
                phase = math.tau * i / 32
                point = V(x - root_x, y + thick * math.sin(phase) + curl * math.cos(phase)**2,
                          z + chord * math.cos(phase))
                point = fold @ point + V(root_x, 0, 0)
                ring.append((pitch @ V(side * point.x, point.y, point.z)) * size)
            rings.append(ring)
        _closed_rings(g, rings)


def _aperture_plate(g, size, rim, side, angle):
    center = V(sum(x for x, _, _ in rim) / len(rim),
               sum(y for _, y, _ in rim) / len(rim),
               sum(z for _, _, z in rim) / len(rim))
    hinge = V(max(x for x, _, _ in rim), -.018, 0)
    tilt = rot(V(0, 0, 1), -angle)
    rings = []
    for fraction, crown in ((.10, -.018), (.73, -.015), (.98, -.007), (1., 0),
                            (.94, .009), (.74, .018), (.45, .025), (.10, .029)):
        ring = []
        for coordinate in rim:
            point = center.lerp(V(coordinate), fraction) + V(0, crown, 0)
            point = hinge + tilt @ (point - hinge)
            ring.append(V(side * point.x, point.y, point.z) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def paired_shell_aperture_valves(g, p):
    """Each side of the lid has a large rostral scutum and a hooked tergum."""
    g.setup(finish="direct")
    size = p["size"]
    for side in (-1, 1):
        _loft(g, size, [(side * x, y, z) for x, y, z in (
            (.025, -.034, -.178), (.081, -.036, -.140), (.111, -.038, -.075),
            (.125, -.039, 0), (.111, -.037, .083), (.069, -.034, .153), (.024, -.034, .202),
        )], ((.010, .013), (.016, .018), (.019, .020), (.020, .021),
              (.019, .020), (.016, .018), (.009, .012)), up=UP)
        angle = math.radians(56 * p["open"])
        _aperture_plate(g, size, (
            (.005, .019, .193), (.043, .008, .161), (.083, -.001, .117),
            (.109, -.004, .065), (.124, -.004, .025), (.116, -.004, -.018),
            (.084, .008, -.029), (.061, .011, -.045), (.036, .021, -.030),
            (.005, .027, -.026), (.004, .030, .061), (.004, .029, .136),
        ), side, angle)
        _aperture_plate(g, size, (
            (.005, .027, -.034), (.038, .022, -.038), (.059, .010, -.053),
            (.087, .008, -.038), (.113, -.004, -.026), (.109, -.007, -.063),
            (.090, -.009, -.104), (.067, -.013, -.119), (.055, -.010, -.155),
            (.026, .002, -.181), (.006, .010, -.171), (.005, .018, -.105),
        ), side, angle)


def multicirral_filter_fan(g, p):
    """Six opposing pairs of biramous thoracic limbs form a coarse setose cup."""
    g.setup(finish="direct")
    size, extension = p["size"], p["extend"]
    _loft(g, size, ((0, -.057, -.119), (0, -.024, -.106), (0, -.007, -.038),
                    (0, -.005, .039), (0, -.013, .092)),
          ((.026, .019), (.041, .030), (.049, .034), (.045, .029), (.025, .018)))
    for side in (-1, 1):
        for pair in range(6):
            z = .077 - .032 * pair
            reach = (.091, .117, .163, .267, .311, .345)[pair]
            width = (.022, .022, .018, .015, .014, .012)[pair]
            base = V(side * (.027 + .0022 * pair), -.008, z)
            spread = .28 + .72 * extension
            fork = base + V(side * reach * .18 * spread, reach * .38 * spread, -.010)
            _loft(g, size, [base, base.lerp(fork, .42), fork],
                  (width * .70, width * .82, width * .59), up=RIGHT, sides=14, density=3)
            for branch in (-1, 1):
                def point(t):
                    bend = math.sin(t * math.pi * .63)
                    return fork + V(side * reach * spread * (.30 * bend - .12 * t**3),
                                    reach * (.60 * spread * bend - .12 * t**3),
                                    reach * (.48 * t**2 + branch * .115 * t))
                stations = [point(i / 8) for i in range(9)]
                _loft(g, size, stations, [width * (.57 - .50 * i / 8) for i in range(9)],
                      up=RIGHT, sides=10, density=2)
                for i in range(1, 8):
                    t = i / 8
                    root = point(t)
                    arc = reach * (.21 - .12 * t) * spread
                    _loft(g, size, (root, root + V(-side * arc * .47, .007, arc * .32),
                                    root + V(-side * arc, .005, arc * .83)),
                          (width * .13, width * .081, .00045), up=UP, sides=6, density=1)


def nested_antennal_shovels(g, p):
    """The fourth antennal article seats under a wide free distal plate."""
    g.setup(finish="direct")
    size = p["size"]
    steer = rot(UP, math.radians(p["yaw"]))
    _loft(g, size, [steer @ V(v) for v in (
        (-.010, -.022, -.043), (0, -.015, -.012), (.005, -.005, .024), (.008, 0., .062),
    )], ((.026, .020), (.049, .032), (.055, .031), (.056, .022)))
    for stations in (
        ((.034, .005, -.005, .046, .028, -.012), (.069, .005, .003, .078, .037, -.008),
         (.125, .011, .010, .089, .037, -.016), (.171, .020, .019, .083, .030, -.028),
         (.197, .025, .018, .067, .023, -.031), (.216, .024, .012, .032, .013, -.024)),
        ((.155, .019, .036, .038, .016, -.005), (.183, .020, .044, .060, .025, -.008),
         (.221, .023, .047, .075, .022, -.010), (.258, .018, .041, .083, .017, -.013),
         (.285, .016, .034, .071, .012, -.018), (.300, .008, .032, .047, .008, -.012),
         (.306, -.004, .031, .017, .004, -.003)),
    ):
        _station_strip(g, size, stations, lambda v: steer @ v)
    # The lateral hook belongs to the proximal plate and rises above its edge.
    _loft(g, size, [steer @ V(v) for v in (
        (.078, .010, .098), (.101, .012, .115), (.114, .021, .143),
        (.112, .040, .163), (.100, .054, .174),
    )], ((.028, .018), (.025, .018), (.016, .013), (.009, .009), (.0017, .002)),
          up=UP, sides=17)


PARTS = [
    Part("split_waterline_compound_eye", "sensory", "A shared head seat separates exposed dorsal and ventral corneae.",
         ["whirligig beetle", "compound eye", "interocular bridge"], {"size": SIZE},
         split_waterline_compound_eye, orient="native", symmetry="pair"),
    Part("vertical_fang_chelicera", "feeding", "A sagittal fang tucks into the groove of a heavy basal chelicera.",
         ["tarantula", "chelicera", "fang", "groove"], {"size": SIZE, "open": (0., 1., .48)},
         vertical_fang_chelicera, orient="native", symmetry="pair"),
    Part("sliding_sabre_ovipositor", "manipulation", "Longitudinal valvulae pack into a narrow curved blade.",
         ["katydid", "ovipositor", "valvulae", "sabre"], {"size": SIZE, "slide": (0., 1., 0.)},
         sliding_sabre_ovipositor, orient="native", symmetry="centre"),
    Part("lateral_abdominal_display_flaps", "aesthetics", "Paired thin flaps wrap a raised abdominal display plate.",
         ["peacock spider", "courtship", "abdominal flaps", "opisthosomal fan"],
         {"size": SIZE, "spread": (0., 1., 1.)}, lateral_abdominal_display_flaps,
         orient="native", symmetry="centre"),
    Part("paired_shell_aperture_valves", "aesthetics", "Two scuta and two terga close along a shared opercular seam.",
         ["barnacle", "operculum", "scutum", "tergum"], {"size": SIZE, "open": (0., 1., .06)},
         paired_shell_aperture_valves, orient="native", symmetry="centre"),
    Part("multicirral_filter_fan", "feeding", "Six mirrored pairs of biramous cirri form a cupped setal fan.",
         ["barnacle", "cirri", "filter feeding", "setae"], {"size": SIZE, "extend": (0., 1., .94)},
         multicirral_filter_fan, orient="native", symmetry="centre"),
    Part("nested_antennal_shovels", "sensory", "Overlapping, flattened antenna articles form one broad shovel.",
         ["slipper lobster", "scyllarid", "antenna", "shovel"], {"size": SIZE, "yaw": (-27., 27., 0.)},
         nested_antennal_shovels, orient="native", symmetry="pair"),
]
