"""Reference-informed drafts for arthropod, pangolin and chiton anatomy.

Native frames use +Y dorsal and +Z anterior. The origin is the insertion
landmark except on the two chiton components, which share a body datum.
Pose controls are static comparison poses, not measured joint limits.
"""

import math

from ..kit import RIGHT, UP, V, rot
from . import Part
from .research_locomotion import _closed_rings


SIZE = (.5, 1.8, 1.)
UNIT = (0., 1., 0.)


def _loft(g, size, points, sections, *, up=UP, sides=24, density=5):
    g.loft([V(point) * size for point in points],
           [tuple(value * size for value in r) if isinstance(r, tuple) else r * size for r in sections],
           up=up, sides=sides, density=density)


def _station_strip(g, size, stations, transform, *, sides=32):
    """Close a series of transverse profiles along an authored midline."""
    rings = []
    for z, x, y, width, depth, rake in stations:
        ring = []
        for i in range(sides):
            phi = math.tau * i / sides
            lateral = math.cos(phi)
            ring.append(V(transform(V(x + width * lateral, y + depth * math.sin(phi),
                                      z + rake * lateral**2))) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def stomatopod_hammer_limb(g, p):
    """Right second maxilliped with merus, short carpus, propodus and dactyl."""
    g.setup(finish="direct")
    size = p["size"]
    # Longer, inflated merus. The shoulder seat is tucked up into the thorax.
    hinge = V(.020, -.143, .140)
    _loft(g, size, [(0, .032, -.055), (0, 0, -.026), (.004, -.043, .012),
                    (.014, -.086, .065), (.020, -.119, .114), hinge],
          [(.028, .023), (.047, .032), (.064, .040), (.062, .042), (.046, .036), (.027, .024)],
          up=RIGHT)
    pose = rot(RIGHT, -p["extend"] * math.radians(55))

    def pivot(point):
        return hinge + pose @ (V(point) - hinge)

    distal = (
        # Short carpus links the distal merus to the base of the returning propodus.
        ((.020, -.132, .129), (.026, -.151, .151), (.035, -.173, .155)),
        ((.029, -.160, .153), (.045, -.181, .138), (.053, -.194, .093),
         (.057, -.196, .035), (.057, -.184, -.016), (.052, -.166, -.041)),
        # Dactyl heel is proximal to its long recurved free tip.
        ((.052, -.169, -.037), (.055, -.199, -.043), (.057, -.226, -.022),
         (.057, -.236, .014), (.056, -.235, .064), (.049, -.228, .126),
         (.038, -.216, .174)),
    )
    sections = (
        ((.024, .021), (.029, .026), (.021, .018)),
        ((.023, .022), (.031, .025), (.032, .023), (.029, .018), (.023, .014), (.015, .012)),
        ((.019, .019), (.035, .035), (.041, .036), (.033, .026),
         (.021, .013), (.011, .008), (.0017, .002)),
    )
    for points, radii in zip(distal, sections):
        _loft(g, size, [pivot(point) for point in points], radii, up=RIGHT)
    # The dactyl's inner-edge teeth are small compared with the striking heel.
    for z, y in ((.074, -.225), (.115, -.218)):
        _loft(g, size, [pivot((.056, y - .012, z - .01)), pivot((.055, y + .001, z)),
                        pivot((.054, y + .009, z + .008))], [.008, .005, .0015], up=RIGHT, sides=12)


def crustacean_tail_fan(g, p):
    """A keeled terminal plate and two biramous uropods on abdominal somite six."""
    g.setup(finish="direct")
    size = p["size"]
    _station_strip(g, size, (
        (.037, 0, .002, .058, .017, -.012), (.006, 0, .002, .120, .024, -.017),
        (-.047, 0, .003, .164, .030, -.012), (-.130, 0, .004, .174, .031, .008),
        (-.210, 0, .002, .159, .028, .016), (-.265, 0, 0, .116, .019, .011),
        (-.289, 0, 0, .046, .012, .007), (-.304, 0, 0, .013, .005, 0),
    ), V)
    # Median crest and three paired dorsal carinae.
    for x, radius, reach in ((0, .014, -.301), (.037, .009, -.259), (.072, .008, -.243),
                             (.108, .007, -.213)):
        for side in ((-1, 1) if x else (1,)):
            _loft(g, size, [(side * x * .65, .027, -.026), (side * x, .035 - x * .1, -.082),
                            (side * x * 1.04, .034 - x * .10, reach + .035),
                            (side * x * .92, .018, reach)],
                  [radius * .40, radius, radius * .60, .002], sides=14)
    # The free telson margin ends in paired submedian, intermediate and
    # lateral teeth. Their anterior roots sit inside the plate shell.
    for side in (-1, 1):
        for x, z, tip_x, tip_z, radius in (
            (.035, -.248, .036, -.324, .022),
            (.087, -.232, .098, -.311, .020),
            (.131, -.195, .146, -.273, .018),
        ):
            _loft(g, size, [(side * x, .001, z),
                            (side * (.52 * x + .48 * tip_x), 0, .52 * z + .48 * tip_z),
                            (side * tip_x, -.003, tip_z)],
                  [(radius, .013), (radius * .74, .011), .0015], sides=14, density=4)
    for side in (-1, 1):
        root = V(.135, -.014, -.030)
        swing = rot(UP, -math.radians(25 * p["spread"]))

        def outer(point):
            point = root + swing @ (V(point) - root)
            return V(side * point.x, point.y, point.z)

        _loft(g, size, [outer(v) for v in ((.104, -.010, .016), root, (.169, -.015, -.087))],
              [(.026, .015), (.038, .021), (.022, .014)], sides=20)
        # Medial endopod, long proximal exopod article, then rounded distal article.
        for stations in (
            ((-.061, .151, -.020, .017, .010, 0), (-.116, .168, -.020, .037, .013, 0),
             (-.198, .187, -.021, .043, .010, .008), (-.261, .210, -.020, .025, .006, .002),
             (-.280, .215, -.020, .007, .003, 0)),
            ((-.067, .167, .001, .018, .012, 0), (-.119, .202, .005, .038, .016, -.013),
             (-.185, .240, .006, .049, .015, -.012), (-.236, .264, .006, .036, .011, -.008),
             (-.254, .271, .004, .020, .008, 0)),
            ((-.237, .265, .005, .014, .007, 0), (-.269, .273, .002, .038, .011, -.008),
             (-.308, .284, -.001, .036, .009, -.003), (-.334, .286, -.001, .016, .005, 0),
             (-.338, .282, -.001, .005, .003, 0)),
        ):
            _station_strip(g, size, stations, outer, sides=24)
        for i in range(10):
            t = i / 9
            x = .222 + .072 * t
            z = -.112 - .121 * t
            _loft(g, size, [outer((x, .007, z)), outer((x + .016, .009, z - .008)),
                            outer((x + .026, .007, z - .024))],
                  [(.007, .005), (.006, .004), .0013], sides=10, density=3)


def crustacean_swimmerets(g, p):
    """Five serial pairs of abdominal pleopods, each with two paddle rami."""
    g.setup(finish="direct")
    size = p["size"]
    # Spacing is a relative construction target from the published O. scyllarus G/L ratio.
    for row in range(5):
        for side in (-1, 1):
            fraction = row / 4
            socket = V(side * (.124 - .021 * fraction), 0, .133 - row * .067)
            # The downstroke uses posterior-to-anterior phase offsets.
            # In recovery these offsets close up toward common anterior reach.
            phase = p["stroke"]
            recovery = max(0., math.sin(math.tau * phase))
            swing_phase = phase + row * .14 * (1 - .9 * recovery)
            pitch = math.radians(-23 + 49 * math.sin(math.tau * swing_phase))
            sweep = rot(RIGHT, pitch)
            span = 1 - .20 * fraction

            def place(point):
                point = V(point) * span
                return socket + sweep @ V(side * point.x, point.y, point.z)

            _loft(g, size, [place(v) for v in ((0, .036, 0), (.009, -.023, -.006),
                                               (.014, -.066, -.022))], [(.025, .017), (.025, .017),
                                                                        (.031, .015)], up=RIGHT, sides=18, density=4)
            for points, sections in (
                (((.014, -.060, -.017), (.030, -.092, -.040), (.050, -.126, -.068),
                  (.063, -.154, -.090), (.061, -.166, -.099)),
                 ((.019, .007), (.036, .009), (.042, .008), (.028, .005), (.006, .002))),
                (((.010, -.058, -.021), (-.019, -.086, -.038), (-.036, -.108, -.068),
                  (-.041, -.121, -.090), (-.038, -.128, -.102)),
                 ((.017, .007), (.029, .008), (.034, .007), (.021, .004), (.005, .002))),
            ):
                _loft(g, size, [place(v) for v in points], sections, up=RIGHT, sides=18, density=4)


def centipede_forcipules(g, p):
    """Midline coxosternite and paired modified first trunk appendages."""
    g.setup(finish="direct")
    size = p["size"]
    _station_strip(g, size, (
        (-.101, 0, .021, .036, .011, 0), (-.085, 0, .012, .091, .027, -.009),
        (-.038, 0, .003, .138, .032, -.008), (.012, 0, -.001, .140, .033, -.011),
        (.052, 0, .001, .114, .029, -.008), (.076, 0, .006, .060, .023, -.003),
        (.084, 0, .010, .037, .008, -.003),
    ), V)
    for side in (-1, 1):
        hinge = V(.115, -.006, .006)
        turn = rot(UP, math.radians(27 * p["open"]))

        def place(point):
            point = hinge + turn @ (V(point) - hinge)
            return V(side * point.x, point.y, point.z)

        # The broad trochanteroprefemur narrows across two short articles.
        for path, radii in (
            (((.111, -.004, -.017), (.132, -.014, .014), (.151, -.025, .053),
              (.147, -.030, .087)), ((.033, .024), (.041, .025), (.037, .023), (.027, .020))),
            (((.150, -.030, .077), (.143, -.033, .101), (.135, -.036, .120)),
             ((.026, .018), (.025, .018), (.021, .015))),
            (((.138, -.036, .111), (.123, -.040, .139), (.092, -.045, .164),
              (.058, -.050, .170), (.028, -.052, .153), (.021, -.054, .136)),
             ((.027, .020), (.032, .023), (.027, .018), (.016, .013), (.008, .006), .0016)),
        ):
            _loft(g, size, [place(v) for v in path], radii)
        for i in range(4):
            x = side * (.012 + i * .011)
            _loft(g, size, [(x, -.005, .069), (x, -.007, .082), (x, -.008, .092 - .001 * i)],
                  [.009, .009, .002], sides=12, density=3)


def odonate_prehensile_labium(g, p):
    """Darner nymph flat mask with an unfolding postmentum and terminal palps."""
    g.setup(finish="direct")
    size = p["size"]
    deploy = p["extend"]
    proximal = rot(RIGHT, math.radians(166 - 135 * deploy))
    endpoint = V(0, 0, .161)
    knee = proximal @ endpoint
    distal = proximal @ rot(RIGHT, math.radians(-161 + 163 * deploy))
    _station_strip(g, size, (
        (-.017, 0, .010, .031, .013, 0), (0, 0, 0, .035, .017, 0),
        (.042, 0, 0, .032, .016, 0), (.102, 0, 0, .029, .013, 0),
        (.158, 0, 0, .034, .015, 0), (.173, 0, 0, .018, .009, 0),
    ), lambda v: proximal @ v)

    def place(point):
        return knee + distal @ V(point)

    _station_strip(g, size, (
        (-.009, 0, 0, .016, .008, 0), (.015, 0, 0, .029, .012, 0),
        (.052, 0, 0, .037, .013, 0), (.111, 0, -.002, .051, .015, 0),
        (.154, 0, -.004, .065, .015, -.005), (.180, 0, -.007, .068, .014, -.017),
        (.193, 0, -.008, .049, .009, -.019), (.198, 0, -.008, .015, .004, -.009),
    ), place)
    for side in (-1, 1):
        pivot = V(.054, -.004, .165)
        turn = rot(UP, math.radians(45 * p["spread"]))

        def palp(point):
            v = pivot + turn @ (V(point) - pivot)
            return place((side * v.x, v.y, v.z))

        _loft(g, size, [palp(v) for v in ((.051, -.003, .157), (.063, -.005, .174),
                                         (.068, -.007, .196), (.060, -.011, .217))],
              [(.013, .011), (.020, .013), (.017, .010), (.011, .006)])
        _loft(g, size, [palp(v) for v in ((.063, -.008, .193), (.068, -.010, .219),
                                         (.057, -.013, .243), (.035, -.015, .250),
                                         (.019, -.017, .240))],
              [(.012, .008), (.012, .008), (.010, .006), (.006, .005), .0015])
        for i in range(3):
            z = .190 + .009 * i
            x = .054 + .003 * i
            _loft(g, size, [palp((x, -.011, z)), palp((x - .010, -.012, z + .004)),
                            palp((x - .013, -.012, z + .009))], [.004, .003, .0009],
                  sides=10, density=3)


def sea_spider_ovigers(g, p):
    """Female Nymphon natans oviger with ten articles and one terminal claw."""
    g.setup(finish="direct")
    # Staples (2025), SAMA E9438. The published millimetre dimensions are
    # displayed at 10x natural scale. Poses and diameters are inferred.
    size = .010 * p["size"]
    lengths = (.16, .31, .39, 1.12, 1.31, .66, .37, .29, .24, .23)
    headings = (15, -31, -14, 4, -65, -138, -154, -170, -196, -222)
    radii = (.095, .116, .108, .110, .115, .092, .073, .065, .058, .053, .047)
    start = V(0, .08, 0)
    for index, (length, degrees, r0, r1) in enumerate(zip(lengths, headings, radii, radii[1:])):
        angle = math.radians(degrees)
        axis = V(.06, -math.cos(angle), math.sin(angle)).normalized()
        end = start + axis * length
        _loft(g, size, [start, start.lerp(end, .16), start.lerp(end, .76), end],
              [r0 * .70, r0, r1 * .94, r1 * .70], sides=18)
        if index >= 6:
            inward = RIGHT.cross(axis).normalized()
            count = (13, 10, 10, 9)[index - 6]
            for i in range(count):
                t = .13 + .78 * i / (count - 1)
                root = start.lerp(end, t)
                _loft(g, size, [root + inward * r1 * .54,
                                root + inward * r1 * 1.15 + axis * .006,
                                root + inward * r1 * 1.78 + axis * .022],
                      [r1 * .19, r1 * .15, r1 * .055], sides=8, density=2)
        start = end
    _loft(g, size, [start, start + V(0, .042, .026), start + V(-.015, .091, .058),
                    start + V(-.026, .111, .031)], [.043, .033, .022, .0035], sides=14)


def horseshoe_crab_telson_spike(g, p):
    """Rigid Limulus tail with subtriangular section and a single ball-joint root."""
    g.setup(finish="direct")
    # Shaft sections and 251 mm pivot-to-tip length follow the registered
    # Bicknell et al. adult female va.06 CT mesh. The cap fits the posterior seat.
    size = .30 * p["size"]
    rotate = rot(UP, math.radians(p["yaw"])) @ rot(RIGHT, math.radians(p["pitch"]))
    profile = ((0, 1), (.24, .86), (.86, -.34), (1, -.61), (.89, -.74),
               (.50, -.69), (0, -.57), (-.50, -.69), (-.89, -.74), (-1, -.61),
               (-.86, -.34), (-.24, .86))
    rings = []
    for z, w, h, keel, blend in (
        (.050, .006, .005, 0, 0), (.043, .025, .022, 0, 0),
        (.024, .044, .033, 0, .12), (.001, .047, .036, .001, .33),
        (-.029, .043, .039, .003, .80), (-.092, .0345, .037, -.013, 1),
        (-.215, .0267, .0343, -.0154, 1), (-.408, .0236, .0275, -.0186, 1),
        (-.568, .0209, .0241, -.0185, 1), (-.701, .0184, .0202, -.0164, 1),
        (-.751, .0170, .0184, -.0164, 1), (-.791, .013, .015, -.0157, 1),
        (-.811, .0085, .010, -.0135, 1), (-.8363, .001, .002, -.009, 1),
    ):
        ring = []
        for index, (x, y) in enumerate(profile):
            theta = math.tau * index / len(profile)
            section_x = (1 - blend) * math.sin(theta) + blend * x
            section_y = (1 - blend) * math.cos(theta) + blend * y
            ring.append(rotate @ V(section_x * w, keel + section_y * h, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def imbricated_scale_armor(g, p):
    """A staggered trunk-to-tail scale field on an analytic curved host patch."""
    g.setup(finish="direct")
    size = p["size"]
    span = p["wrap"]
    # Theta zero is dorsal. The longitudinal transition narrows to the tail.
    for row in range(10):
        t = row / 9
        count = (11, 10, 11, 10, 9, 8, 7, 6, 5, 4)[row]
        step = 2 * span / count
        for column in range(count):
            theta = (column + .5) * step - span
            rings = []
            for rear, breadth, offset, height in ((-.014, .36, -.009, .007), (0, .77, -.006, .011),
                                                   (.028, 1.10, .001, .013), (.070, 1.05, .010, .013),
                                                   (.102, .74, .015, .010), (.122, .27, .021, .007),
                                                   (.126, .07, .021, .003)):
                progress = min(1., max(0., t + rear * .86))
                taper = 1 - .64 * progress**2.15
                z = .46 - .091 * row - rear
                ring = []
                for i in range(14):
                    angle = math.tau * i / 14
                    beta = theta + .53 * step * breadth * math.cos(angle)
                    shell = offset + height * math.sin(angle)
                    radius_x = .218 * taper + shell
                    radius_y = .187 * taper + shell
                    ring.append(V(radius_x * math.sin(beta), radius_y * math.cos(beta) - .187, z) * size)
                rings.append(ring)
            _closed_rings(g, rings)


def _chiton_frame(z, curl):
    """Rigid transverse valve frame on the curved axial surface."""
    angle = z * curl
    if not curl:
        return V(0, 0, z), rot(RIGHT, 0)
    return V(0, (math.cos(angle) - 1) / curl, math.sin(angle) / curl), rot(RIGHT, angle)


def chiton_valved_dorsum(g, p):
    """Eight transverse valves arranged front-over-back on a low oval girdle bed."""
    g.setup(finish="direct")
    size, curl = p["size"], math.radians(p["curl"])
    for index, (center, width, length, height) in enumerate((
        (.423, .180, .158, .119), (.315, .232, .146, .134), (.197, .255, .151, .145),
        (.077, .270, .152, .153), (-.045, .269, .152, .153), (-.167, .251, .152, .145),
        (-.288, .222, .152, .129), (-.411, .169, .176, .110),
    )):
        root, basis = _chiton_frame(center, curl)
        # End valves are rounded caps. Intermediate valves have an anterior
        # insertion tongue and a broad, elevated posterior overhang.
        rows = (
            ((.52, .04, .30, 0), (.42, .62, .70, .05), (.22, .89, .87, .06),
             (0, 1, 1, .05), (-.24, .97, 1, .05), (-.48, .88, .83, .05), (-.56, .62, .54, .02))
            if index == 0 else
            ((.51, .64, .42, .04), (.37, .91, .62, .10), (.13, 1, .87, .13),
             (-.13, .94, 1, .10), (-.30, .77, .90, .06), (-.47, .42, .65, .03), (-.56, .05, .30, 0))
            if index == 7 else
            ((.55, .40, .51, -.04), (.44, .73, .68, .03), (.28, .93, .85, .09),
             (0, 1, .96, .16), (-.30, .97, 1, .20), (-.51, .90, .93, .22), (-.55, .78, .83, .19))
        )
        rings = []
        for station, span, arch, rake in rows:
            ring = []
            for i in range(32):
                angle = math.tau * i / 32
                lateral = math.cos(angle)
                dome = max(0, (1 - lateral**2))**.73
                v = V(width * span * lateral, .015 + height * arch * dome +
                      math.sin(angle) * .007 * arch, length * (station + rake * lateral**2))
                ring.append((root + basis @ v) * size)
            rings.append(ring)
        _closed_rings(g, rings)


def chiton_pedal_sole(g, p):
    """Continuous shallow sole lying within the pallial groove, with raised ends."""
    g.setup(finish="direct")
    size, width = p["size"], p["width"] * .82
    # Mounting surface remains at the shared chiton body datum (Y=0).
    _station_strip(g, size, (
        (.382, 0, -.033, .014 * width, .009, -.004), (.355, 0, -.052, .074 * width, .025, -.007),
        (.301, 0, -.061, .125 * width, .039, -.012), (.228, 0, -.062, .155 * width, .043, -.006),
        (.120, 0, -.065, .166 * width, .046, 0), (.010, 0, -.066, .167 * width, .045, 0),
        (-.110, 0, -.064, .165 * width, .045, 0), (-.223, 0, -.060, .153 * width, .043, .006),
        (-.321, 0, -.057, .113 * width, .039, .005), (-.373, 0, -.040, .063 * width, .023, .010),
        (-.396, 0, -.025, .014 * width, .009, .002),
    ), lambda v: V(v.x, -.066 + math.copysign(abs(v.y + .066)**.82 * .54, v.y + .066), .875 * v.z - .014))


PARTS = [
    Part("stomatopod_hammer_limb", "feeding", "Stomatopod second maxilliped with a folded dactyl club.",
         ["mantis shrimp", "stomatopod", "dactyl club"], {"size": SIZE, "extend": UNIT},
         stomatopod_hammer_limb, orient="native", symmetry="pair", mirror=True),
    Part("crustacean_tail_fan", "locomotion", "Keeled telson and paired biramous uropods.",
         ["mantis shrimp", "crustacean", "tail", "uropod", "telson"], {"size": SIZE, "spread": (.0, 1., .36)},
         crustacean_tail_fan, attach="tip", orient="native", symmetry="pair"),
    Part("crustacean_swimmerets", "locomotion", "Five paired biramous abdominal paddles on a series of ventral roots.",
         ["mantis shrimp", "pleopod", "swimming"], {"size": SIZE, "stroke": (0., 1., .28)},
         crustacean_swimmerets, orient="native", symmetry="pair"),
    Part("centipede_forcipules", "feeding", "Paired hooked forcipules joined by a midline coxosternite.",
         ["centipede", "myriapod", "forcipule"], {"size": SIZE, "open": UNIT}, centipede_forcipules,
         orient="native", symmetry="pair"),
    Part("odonate_prehensile_labium", "feeding", "Folding flat larval labium with opposed hooked palps.",
         ["dragonfly", "nymph", "labium", "labial mask"],
         {"size": SIZE, "extend": UNIT, "spread": UNIT}, odonate_prehensile_labium,
         orient="native", symmetry="center"),
    Part("sea_spider_ovigers", "manipulation", "Slender ten-article oviger with terminal grooming spines.",
         ["sea spider", "pycnogonid", "brooding", "oviger"], {"size": SIZE}, sea_spider_ovigers,
         orient="native", symmetry="pair", mirror=True),
    Part("horseshoe_crab_telson_spike", "locomotion", "Single tapered, approximately triangular telson.",
         ["horseshoe crab", "limulus", "righting", "telson"],
         # A conservative static range for the registered va.06 shield fixture.
         {"size": SIZE, "pitch": (-60., 20., 0.), "yaw": (-28., 28., 0.)}, horseshoe_crab_telson_spike,
         attach="tip", orient="native", symmetry="center"),
    Part("imbricated_scale_armor", "aesthetics", "Curved patch of staggered, overlapping pangolin scales.",
         ["pangolin", "scale", "armor", "imbrication"], {"size": SIZE, "wrap": (.95, 2.10, 1.62)},
         imbricated_scale_armor, orient="native", symmetry="repeated"),
    Part("chiton_valved_dorsum", "aesthetics", "Eight overlapping shell valves with rounded end caps.",
         ["chiton", "polyplacophoran", "valve", "girdle"], {"size": SIZE, "curl": (0., 85., 0.)},
         chiton_valved_dorsum, orient="native", symmetry="repeated"),
    Part("chiton_pedal_sole", "locomotion", "Broad continuous ventral foot with rounded toe and heel margins.",
         ["chiton", "polyplacophoran", "pedal sole", "muscular foot"], {"size": SIZE, "width": (.76, 1.24, 1.)},
         chiton_pedal_sole, orient="native", host="body_plan", symmetry="center"),
]


TRAITS = {
    "crustacean_tail_fan": {"function": "swim"},
    "crustacean_swimmerets": {"function": "swim"},
    "sea_spider_ovigers": {"function": "grasp"},
    "horseshoe_crab_telson_spike": {"function": "balance"},
    "imbricated_scale_armor": {"function": "protect"},
    "chiton_valved_dorsum": {"function": "protect"},
    "chiton_pedal_sole": {"function": "support"},
}
