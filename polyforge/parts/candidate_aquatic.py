"""Aquatic anatomy studies in metres, with +Y dorsal and +Z rostral.

Paired surface detail is authored on +X unless the discriminator needs a
continuous midline or eight rows on a common host.
"""
from math import cos, exp, pi, sin, tau

from scipy.interpolate import PchipInterpolator

from ..kit import RIGHT, UP, V, lerp, smoothstep
from . import Part
from .pilots import _foil_ring
from .research_locomotion import _closed_rings


# The three nautilus parts share the aperture at the origin. The numerical
# cross sections belong to the shell; the moving parts use them for clearance.
_NAUTILUS_WHORL = (
    (0., .019, .0014, .004), (.065, .031, .0013, .009),
    (.16, .045, .0011, .017), (.25, .066, .001, .026),
    (.38, .064, .0008, .030), (.52, .075, .0008, .034),
    (.65, .089, .0009, .039), (.75, .106, .0011, .044),
    (.86, .120, .0015, .048), (1., .127, .0038, .054),
)
_NAUTILUS_PROFILE = PchipInterpolator([t for t, *_ in _NAUTILUS_WHORL],
                                      [values for _, *values in _NAUTILUS_WHORL])
_NAUTILUS_APERTURE_ANGLE = .47
_NAUTILUS_APERTURE_HINT = {"u": 1., "theta": 90.}
_NAUTILUS_DEPLOYMENT = (0., 1., .85)
_NAUTILUS_CENTER_RADIUS = (_NAUTILUS_WHORL[-1][1] + _NAUTILUS_WHORL[-1][2]) / 2
_NAUTILUS_OUT = V(0, sin(_NAUTILUS_APERTURE_ANGLE), cos(_NAUTILUS_APERTURE_ANGLE))


def _nautilus_chamber_point(t, lateral, outward, hollow):
    """Sample a chamber cross section in its curved aperture frame."""
    outer, inner, width = _NAUTILUS_PROFILE(t)
    angle = _NAUTILUS_APERTURE_ANGLE - (1 - t) * tau
    radius = (outer + inner) / 2
    depth = (outer - inner) / 2 - hollow
    center_y = _NAUTILUS_CENTER_RADIUS * cos(_NAUTILUS_APERTURE_ANGLE)
    center_z = -_NAUTILUS_CENTER_RADIUS * sin(_NAUTILUS_APERTURE_ANGLE)
    flare = smoothstep(.86, 1., t)
    radial = radius + depth * outward
    # The peristome advances along the lateral cheeks. The older whorl
    # overhangs the middle of the dorsal margin.
    lifted = .036 * flare * max(0., -outward)**.6 * abs(lateral)**.85
    advanced = .025 * flare * lateral**2
    return V((width - hollow) * lateral, center_y - radial * cos(angle) + lifted,
             center_z + radial * sin(angle) + advanced)


def nautilus_coiled_shell(g, p):
    """An expanding whorl with a turned aperture lip and a blind living chamber."""
    size = p["size"]
    g.setup(finish="direct")

    def ring(t, hollow=0.):
        return [_nautilus_chamber_point(t, sin(a), cos(a), hollow) * size
                for a in (tau * j / 48 for j in range(48))]

    # Coarse side envelope from PRI 70573. Interior cross sections are inferred.
    exterior = [ring(i / 140) for i in range(141)]
    # Reverse the inner skin so the aperture is a true opening. Finish in a
    # rounded blind end, leaving the older internal chamber walls unmodeled.
    rim = [ring(1, .001), ring(1, .003)]
    cavity = [ring(t, .0042) for t in (1 - i * .004 for i in range(1, 61))]
    end = cavity[-1]
    center = sum(end, V(0, 0, 0)) / len(end)
    end = [center.lerp(vertex, .36) + V(0, 0, -.003) * size for vertex in end]
    _closed_rings(g, exterior + rim + cavity + [end])


def nautilus_protective_hood(g, p):
    """Sculpt the muscular cover from a seated margin to a draped forward flap."""
    size, deploy = p["size"], p["deployment"]
    g.setup(finish="subsurf_low")
    reference_normal = _NAUTILUS_OUT.lerp(UP, smoothstep(0., 1., deploy)).normalized()
    outline = []
    for j in range(48):
        a = tau * j / 48
        lateral, outward = sin(a), cos(a)
        closed = _nautilus_chamber_point(1., lateral, outward, .0007) + _NAUTILUS_OUT * .0012
        # A broad two-sided free margin, which sags beyond the dorsal root.
        width = .044 - .006 * outward
        y = .041 - .030 * outward - .004 * lateral**2
        z = .024 + .045 * outward + .006 * lateral**2
        emerged = V(width * lateral, y, z)
        outline.append(closed.lerp(emerged, deploy))

    center = sum(outline, V(0, 0, 0)) / len(outline)
    rings = []
    for fraction, surface_offset in ((.12, -.007), (.57, -.006), (.88, -.004), (.983, -.0019),
                                     (1., .0005), (.982, .0025), (.88, .005),
                                     (.59, .008), (.31, .008), (.10, .008)):
        ring = []
        for vertex in outline:
            point = center.lerp(vertex, fraction)
            crease = .003 * exp(-(point.x / .008)**2) * (1 - fraction**2)
            dorsal_face = smoothstep(-.003, .005, surface_offset)
            crease *= dorsal_face
            # In the emerged pose, the posterior hood forms a muscular
            # saddle continuous with the soft head beneath its free flap.
            root_fullness = deploy * exp(-((point.z - .011) / .029)**2 - (point.x / .031)**2)
            thickness = root_fullness * lerp(-.008, .003, dorsal_face) * (1 - fraction**3)
            ring.append((point + reference_normal * (surface_offset + thickness - crease)) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def nautilus_digital_tentacles(g, p):
    """Route each annular sheath within the chamber until its cirrus is clear."""
    size, deploy = p["size"], p["deployment"]
    advance = deploy**1.65
    g.setup(finish="direct")
    for side in (-1, 1):
        for i in range(18):
            a = lerp(-1.15, 1.40, i / 17)
            lateral = side * (.18 + .39 * cos(a))
            outward = .30 + .36 * sin(a)

            def center(t):
                return _nautilus_chamber_point(t, lateral, outward, .0042)

            root = center(lerp(.908, .950, advance))
            neck = center(lerp(.934, .982, advance))
            throat = center(lerp(.953, 1., advance))
            throat += (_NAUTILUS_OUT * .025 - UP * .008) * advance
            g.loft([point * size for point in (root, neck, throat)],
                   [size * r for r in (.0025, .0019, .0012)], sides=10, density=2)

            reach = (.019 + .031 * (.5 + .5 * sin(i * 3.11 + side))) * advance
            forward = _NAUTILUS_OUT.lerp(V(0, -.20, 1), deploy).normalized()
            splay = V(side * (.18 + .24 * cos(a)), -.10 - .18 * sin(a), 0)
            anchor = throat.lerp(neck, .16)
            middle = throat + forward * (reach * .48 - .0013) + splay * (reach * .30)
            tip = throat + forward * (reach - .0005) + splay * reach
            tip.y += .12 * reach * cos(i * 2.13)
            g.loft([point * size for point in (anchor, middle, tip)],
                   [size * r for r in (.0010, .0007, .00032)], sides=10, density=4)


def ray_cephalic_lobes(g, p):
    """One head-rooted ribbon that rolls along its longitudinal axis."""
    roll = p["roll"]
    length = p["length"]
    g.setup(finish="subsurf_low")
    rings = []
    for z, width, drop, spread in (
        (-.025, .077, 0., 0.), (.015, .085, -.012, 0.),
        (.095, .100, -.045, .012), (.22, .108, -.100, .028),
        (.36, .102, -.146, .033), (.49, .082, -.178, .020),
        (.565, .050, -.180, -.004), (.592, .014, -.176, -.010),
    ):
        reach = max(0., z / .592)
        bend = roll * lerp(.32, 5.45, min(1., reach * 1.9))
        ring = []
        for j in range(36):
            a = tau * j / 36
            u = cos(a)
            if bend < .0001:
                x, y = width * u, 0.
            else:
                x = 2 * width / bend * sin(bend * u / 2)
                y = 2 * width / bend * (cos(bend * u / 2) - 1)
            # Two skins stay joined along the soft longitudinal edges.
            y += .020 * sin(a) * (1 - .78 * reach)
            ring.append(V(x + spread * (1 - roll), y + drop * (1 - .68 * roll), z * length))
        rings.append(ring)
    _closed_rings(g, rings)


def ray_continuous_pectoral_disc(g, p):
    """One muscular core with a full-length pectoral transition and swept tips."""
    g.slot("skin")
    g.setup(finish="subsurf_low")
    span, sweep = p["span"], p["tip_lift"]
    stations = (
        (0., 0., .215, -.292, .080), (.075, 0., .215, -.282, .079),
        (.155, 0., .225, -.259, .070), (.235, -.005, .198, -.221, .056),
        (.330, -.014, .133, -.186, .045), (.445, -.021, .092, -.170, .033),
        (.590, -.026, .035, -.161, .022), (.728, -.019, -.035, -.161, .014),
        (.856, -.005, -.098, -.173, .009), (.950, .006, -.149, -.184, .006),
        (1., .016, -.187, -.194, .002),
    )
    half = [_foil_ring(x * span / 2, (y + sweep * x**2.6) * span, front * span, rear * span, h * span)
            for x, y, front, rear, h in stations]
    _closed_rings(g, [[V(-v.x, v.y, v.z) for v in ring] for ring in reversed(half[1:])] + half)


def paired_branchial_plumes(g, p):
    """One branchial bank with three unequal rami and trailing gill filaments."""
    s, flare = p["size"], p["flare"]
    g.setup(finish="direct")
    for root, end, count, width in (
        ((-.007, .007, .012), (.038, .045, -.018), 18, .0060),
        ((-.008, .000, .000), (.047, .021, -.033), 21, .0068),
        ((-.007, -.009, -.010), (.036, -.007, -.045), 17, .0051),
    ):
        base, tip = V(root), V(end)
        tip.x *= flare
        bend = base.lerp(tip, .43) + V(.006, -.004, .004)
        g.loft([v * s for v in (base, bend, tip)],
               [s * r for r in (width * .66, width * .43, .001)], sides=12, density=8)
        along = (tip - base).normalized()
        trailing = along.cross(V(.15, 1., 0.)).normalized()
        if trailing.z > 0:
            trailing = -trailing
        for i in range(count):
            u = lerp(.23, .98, i / (count - 1))
            at = base.lerp(bend, u / .43) if u < .43 else bend.lerp(tip, (u - .43) / .57)
            for bank in (-1, 1):
                spread = trailing + UP * (.29 * bank - .16)
                length = width * (.70 + 1.55 * sin(pi * (u - .11))) * (1. if bank > 0 else .79)
                start = at + UP * (.0011 * bank)
                end = start + spread * length + along * (.004 + .19 * length)
                mid = start.lerp(end, .57) - along * .002
                g.loft([v * s for v in (start, mid, end)],
                       [s * r for r in (.00076, .00052, .00020)], sides=8, density=3)


def salamander_axial_fin(g, p):
    """Continuous upper and lower fin margins around a laterally thin tail core."""
    s, flex = p["size"], p["bend"]
    g.setup(finish="subsurf_low")
    stations = (
        (.016, .022, .018, -.014), (0., .021, .024, -.016),
        (-.029, .019, .036, -.022), (-.053, .018, .046, -.028),
        (-.083, .015, .045, -.028), (-.112, .012, .039, -.026),
        (-.142, .010, .030, -.021), (-.167, .006, .020, -.015),
        (-.187, .004, .011, -.009), (-.199, .002, .004, -.003),
        (-.202, .0009, .001, -.001),
    )
    _axial_fin_envelope(g, stations, s, flex, .202)


def _axial_fin_envelope(g, stations, size, bend, bend_length, *, relief=None, sides=32):
    """Loft one shared axial core and edge, with optional surface ray relief."""
    rings = []
    for z, width, upper, lower in stations:
        bend_x = bend * max(0., -z) ** 2 / bend_length
        ring = []
        for j in range(sides):
            angle = tau * j / sides
            y = cos(angle)
            taper = .12 + .88 * (1 - abs(y))**2.7
            ray = relief(z, y) if relief is not None else 0.
            ring.append(V(bend_x + width * sin(angle) * taper + ray * sin(angle),
                          y * (upper if y > 0 else -lower), z) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def goby_pelvic_disc(g, p):
    """Continuous ventral contact rim with a recessed adhesion face."""
    size, cup = p["size"], p["cup"]
    g.setup(finish="subsurf_low")
    rings = []
    for r, y in ((.06, .008), (.38, .008), (.62, .006), (.82, .001),
                 (.94, -.004), (1., -.007), (.99, -.010), (.94, -.012),
                 (.88, -.012), (.78, -.007 - .003 * (1 - cup)),
                 (.56, -.002 - .007 * (1 - cup)), (.18, 0. - .009 * (1 - cup)),
                 (.06, 0. - .009 * (1 - cup))):
        ring = []
        for j in range(48):
            a = tau * j / 48
            # Slightly flattened anterior rim and fine bilateral ray corrugation.
            width = .023 * (1. - .09 * cos(a))
            z = .025 * cos(a) - .005 * cos(a)**4
            relief = .0009 * sin(a * 16)**2 * sin(pi * r)**2
            ring.append(V(width * sin(a) * r, y - relief, z * r) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def ctenophore_comb_tracks(g, p):
    """Eight meridional rows of individual ctenes with two different track runs."""
    s, phase = p["size"], p["phase"] * tau
    g.setup(finish="direct")
    for quadrant in range(4):
        for longer, offset in ((False, .31), (True, 1.20)):
            angle = quadrant * pi / 2 + offset
            longitudinal = (.20, .83, 27) if longer else (.21, .62, 21)
            start, end, count = longitudinal
            for i in range(count):
                t = lerp(start, end, i / (count - 1))
                radial = sin(pi * t * .77)
                location = V(.029 * cos(angle) * radial, .043 - .085 * t, .021 * sin(angle) * radial)
                across = V(-.029 * sin(angle), 0, .021 * cos(angle)).normalized()
                normal = UP.cross(across)
                tilt = .00075 * sin(phase + i * .58)
                reach = .0014 + .0006 * sin(pi * i / (count - 1))
                width = .0031 * radial
                root = location - normal * .00065
                tip = location + normal * reach + UP * tilt
                outline = [root - across * width, root + across * width,
                           tip + across * width * .88 + UP * .00045,
                           tip - across * width * .88 + UP * .00045]
                g.slab([v * s for v in outline], normal.cross(across), .00055 * s, bulge=.18)


def ctenophore_oral_lobes(g, p):
    """One broad gelatinous lobe cupped toward the companion across the mouth."""
    s, opening = p["size"], p["opening"]
    g.setup(finish="subsurf_low")
    rings = []
    for y, x, width, thickness in (
        (.012, .012, .006, .002), (.006, .017, .013, .003),
        (-.004, .022, .019, .004), (-.019, .028, .024, .004),
        (-.035, .032, .025, .0035), (-.047, .033, .021, .0027),
        (-.056, .031, .013, .002), (-.060, .028, .005, .0012),
        (-.061, .026, .001, .0006),
    ):
        ring = []
        for j in range(28):
            a = tau * j / 28
            across = cos(a)
            shift = max(0., -y) * opening * .28
            cup = width * .32 * across**2
            ring.append(V(x + shift + thickness * sin(a) - cup,
                          y + width * .08 * across, width * across) * s)
        rings.append(ring)
    _closed_rings(g, rings)


def mussel_mantle_lure(g, p):
    """Mantle flap with a fleshy snout and the flattened split distal streamer."""
    s, deploy = p["size"], p["deployment"]
    g.setup(finish="subsurf_low")
    outline = (
        (-.002, -.003, .010), (.000, .001, .012), (.001, .006, .010),
        (.002, .009, .003), (.002, .009, -.005), (.000, .008, -.012),
        (-.001, .012, -.021), (-.002, .013, -.024), (-.002, .010, -.0245),
        (0., .005, -.018), (.001, .003, -.015), (.002, .000, -.022),
        (.002, -.001, -.022), (.000, .000, -.014), (-.001, .002, -.009),
        (-.002, .002, -.002), (-.002, -.001, .003), (-.002, -.004, .004),
    )
    g.leaf([V(x, y * deploy, z * (.47 + .53 * deploy)) * s for x, y, z in outline],
           RIGHT, .0038 * s, cup=.22)


SIZE = {"size": (.6, 1.6, 1.)}
PARTS = [
    Part("nautilus_coiled_shell", "aesthetics", "Planispiral shell wrapping an open anterior living chamber.",
         ["nautilus", "coiled", "shell", "aperture"], SIZE, nautilus_coiled_shell,
         orient="native", symmetry="center", hint=_NAUTILUS_APERTURE_HINT),
    Part("nautilus_protective_hood", "aesthetics", "Two-lobed muscular cover above the nautilus aperture.",
         ["nautilus", "aperture", "hood"], {**SIZE, "deployment": _NAUTILUS_DEPLOYMENT},
         nautilus_protective_hood, orient="native", symmetry="center", hint=_NAUTILUS_APERTURE_HINT),
    Part("nautilus_digital_tentacles", "manipulation", "Bilateral outer buccal sheaths with thin retractile cirri.",
         ["nautilus", "buccal", "sheath", "tentacle"], {**SIZE, "deployment": _NAUTILUS_DEPLOYMENT},
         nautilus_digital_tentacles, orient="native", symmetry="center", hint=_NAUTILUS_APERTURE_HINT),
    Part("ray_cephalic_lobes", "feeding", "One rollable cephalic feeding ribbon rooted beside the mouth.",
         ["manta", "ray", "cephalic", "lobe"], {"length": (.55, 1.4, 1.), "roll": (0., 1., .28)},
         ray_cephalic_lobes, orient="native", symmetry="pair", hint={"u": .84, "theta": 0.}),
    Part("ray_continuous_pectoral_disc", "locomotion", "Whole ray core and pectoral disc with a continuous leading edge.",
         ["manta", "ray", "batoid", "disc"], {"span": (.8, 8., 4.2), "tip_lift": (-.12, .16, .015)},
         ray_continuous_pectoral_disc, attach="core", orient="native", symmetry="center"),
    Part("paired_branchial_plumes", "aesthetics", "One branchial bank of three rami and trailing filaments.",
         ["axolotl", "salamander", "external", "gill", "ramus", "filament"],
         {**SIZE, "flare": (.65, 1.35, 1.)}, paired_branchial_plumes,
         orient="native", symmetry="pair", hint={"u": .8, "theta": 0.}),
    Part("salamander_axial_fin", "locomotion", "Continuous dorsal and ventral tail membrane over a tapered axial core.",
         ["axolotl", "salamander", "caudal", "membrane", "tail"], {**SIZE, "bend": (-.65, .65, 0.)},
         salamander_axial_fin, orient="native", symmetry="center", hint={"u": .12, "theta": 90.}),
    Part("goby_pelvic_disc", "locomotion", "Ventral fused pelvic-fin sucker with one recessed contact surface.",
         ["goby", "holdfast", "pelvic", "adhesion", "sucker"], {**SIZE, "cup": (.05, 1., .75)},
         goby_pelvic_disc, orient="native", symmetry="center", hint={"u": .58, "theta": -90.}),
    Part("ctenophore_comb_tracks", "locomotion", "Eight meridional rows of separate ciliary comb plates.",
         ["ctenophore", "comb jelly", "ctene", "cilia"], {**SIZE, "phase": (0., 1., 0.)},
         ctenophore_comb_tracks, orient="native", symmetry="center"),
    Part("ctenophore_oral_lobes", "feeding", "One broad cupped oral lobe of a lobate comb jelly.",
         ["ctenophore", "comb jelly", "lobate", "oral"], {**SIZE, "opening": (0., 1., .55)},
         ctenophore_oral_lobes, orient="native", symmetry="pair", hint={"u": .84, "theta": 0.}),
    Part("mussel_mantle_lure", "aesthetics", "A broad mantle extension with a narrow bifurcate distal streamer.",
         ["lampmussel", "bivalve", "mantle", "lure"], {**SIZE, "deployment": (.15, 1., 1.)},
         mussel_mantle_lure, orient="native", hint={"u": .6, "theta": -90.}),
]

TRAITS = {
    "nautilus_coiled_shell": {"function": "protect", "shape": "coil aperture"},
    "nautilus_protective_hood": {"function": "protect", "shape": "muscular aperture hood"},
    "nautilus_digital_tentacles": {"function": "grasp", "shape": "many slender sheathed cirri"},
    "ray_cephalic_lobes": {"function": "feed", "shape": "rollable ribbon"},
    "ray_continuous_pectoral_disc": {"function": "swim", "shape": "flat triangular disc"},
    "paired_branchial_plumes": {"function": "breathe", "shape": "three feathered rami"},
    "salamander_axial_fin": {"function": "swim", "shape": "long median membrane"},
    "goby_pelvic_disc": {"function": "adhere", "shape": "recessed flattened rim"},
    "ctenophore_comb_tracks": {"function": "swim", "shape": "eight parallel meridional rows"},
    "ctenophore_oral_lobes": {"function": "feed", "shape": "cupped flat lobe"},
    "mussel_mantle_lure": {"function": "display", "shape": "flap split streamer"},
}
