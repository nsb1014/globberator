"""Draft locomotor and terminal anatomy. Native coordinates are metres, +Y up, +Z forward."""

import math

from ..kit import UP, V, lerp, rot
from . import Part
from .research_locomotion import _closed_rings


def _tail_sections(p):
    """Sample constant-length armor rings along a tapering ventral coiling arc."""
    size, curl = p["size"], p["curl"]
    count = 32
    center = V(0, 0, 0)
    sections = []
    for i in range(count + 1):
        t = i / count
        theta = .14 + curl * 8.7 * t ** 2.18
        radius = size * lerp(.075, .006, t ** .82)
        sections.append((center.copy(), theta, radius))
        middle = (i + .5) / count
        turn = .14 + curl * 8.7 * middle ** 2.18
        center += size * (.93 / count) * V(0, -math.cos(turn), math.sin(turn))
    return sections


def seahorse_chain(p):
    sections = _tail_sections(p)[::4]
    return {
        "segments": [tuple(b[0] - a[0]) for a, b in zip(sections, sections[1:])],
        "radii": [r for _, _, r in sections],
        "motion": "tail",
    }


def seahorse_grasping_tail(g, p):
    """One plated, four-faced tail with a continuous tapered terminal coil."""
    sections = _tail_sections(p)
    rings = []
    for (start, initial, width), (end, final, next_width) in zip(sections, sections[1:]):
        for t, relief in ((0., .94), (.25, 1.04), (.72, 1.00)):
            center, theta = start.lerp(end, t), lerp(initial, final, t)
            radial = V(0, math.sin(theta), math.cos(theta))
            radius = lerp(width, next_width, t) * relief
            ring = []
            for j in range(16):
                angle = math.tau * (j + .5) / 16
                x, q = math.cos(angle), math.sin(angle)
                ring.append(center + V(math.copysign(abs(x) ** .57, x) * radius, 0, 0)
                            + radial * (math.copysign(abs(q) ** .57, q) * radius * .89))
            rings.append(ring)
    center, theta, radius = sections[-1]
    radial = V(0, math.sin(theta), math.cos(theta))
    rings.append([center + V(radius * .50 * math.cos(math.tau * (j + .5) / 16), 0, 0)
                  + radial * (radius * .45 * math.sin(math.tau * (j + .5) / 16))
                  for j in range(16)])
    g.setup(finish="subsurf_low")
    g.slot("skin")
    _closed_rings(g, rings)


# Shoulder and elbow follow the stout leading half of the wing. The wrist lies
# within the continuous foil. A short root inset affords lateral thorax fitting.
_PENGUIN_JOINTS = ((0, 0, 0), (.163, -.006, .014), (.291, -.013, -.061),
                  (.455, -.025, -.145))
_PENGUIN_SECTIONS = (
    (-.036, .000, .035, -.026, .018), (-.017, .001, .046, -.041, .026),
    (.025, .000, .060, -.067, .024), (.085, -.001, .067, -.081, .022),
    (.153, -.005, .061, -.096, .019), (.205, -.008, .042, -.111, .017),
    (.264, -.013, .000, -.130, .013), (.325, -.016, -.036, -.151, .010),
    (.376, -.020, -.072, -.169, .007), (.417, -.022, -.109, -.175, .005),
    (.445, -.024, -.136, -.167, .003), (.455, -.025, -.149, -.157, .0015),
)


def penguin_flipper_chain(p):
    scale = V(p["size"], p["size"], p["size"] * p["chord"])
    points = [V(*point) for point in _PENGUIN_JOINTS]
    return {
        "segments": [tuple((b[i] - a[i]) * scale[i] for i in range(3))
                     for a, b in zip(points, points[1:])],
        "radii": [p["size"] * r for r in (.025, .019, .012, .002)],
    }


def avian_swim_flipper(g, p):
    """Sculpt a continuous swept foil, with an asymmetric cambered section."""
    rings = []
    for x, y, leading, trailing, depth in _PENGUIN_SECTIONS:
        ring = []
        for i in range(20):
            angle = math.tau * i / 20
            t = .5 + .5 * math.cos(angle)
            camber = .013 * t * (1 - t) * (1 - x / .51)
            thickness = depth * p["thickness"] * math.sin(angle) * (.70 + .60 * t)
            ring.append(V(x, y + camber + thickness, lerp(trailing, leading, t) * p["chord"]) * p["size"])
        rings.append(ring)
    g.setup(finish="sculpt")
    g.slot("skin")
    _closed_rings(g, rings)


# One right thoracic fan. Each ridge is part of the same closed membrane skin,
# and runs from one longitudinal thorax station to its own outer rim point.
_DRACO_RIBS = (
    (.335, .004, .334), (.294, .235, .302), (.239, .421, .205),
    (.132, .389, .061), (.030, .323, -.075), (-.080, .240, -.208),
    (-.174, .153, -.308), (-.258, .074, -.363), (-.339, .004, -.368),
)


def reptile_rib_patagium(g, p):
    """A cambered lateral membrane, with six ribs continuous with the thorax."""
    size, spread = p["size"], p["spread"]
    rings = []
    for i, (root, span, edge) in enumerate(_DRACO_RIBS):
        stations = [(root, span, edge, 1. if 2 <= i <= 7 else 0.)]
        if i < len(_DRACO_RIBS) - 1:
            next_root, next_span, next_edge = _DRACO_RIBS[i + 1]
            for t in (.32, .68):
                stations.append((lerp(root, next_root, t),
                                 lerp(span, next_span, t) * (1 - .022 * math.sin(math.pi * t)),
                                 lerp(edge, next_edge, t), .03))
        for z, width, margin, ridge in stations:
            ring = []
            for j in range(24):
                angle = math.tau * j / 24
                q = .5 - .5 * math.cos(angle)
                x = -.024 + (width * spread + .024) * q
                bend = math.sin(math.pi * q)
                y = width * (.085 * bend - .043 * q ** 2)
                y -= .064 * (1 - spread) * q
                depth = min(width, .20) * .014 + .001
                y += math.sin(angle) * depth
                y += max(0, math.sin(angle)) * ridge * .015 * bend
                sweep = (1 - spread) * .41 * q * (width / .43)
                ring.append(V(x, y, lerp(z, margin, q) - sweep) * size)
            rings.append(ring)
    g.setup(finish="subsurf_low")
    _closed_rings(g, rings)


def toad_stellate_digit_organs(g, p):
    """One fore-digit tip. Four primary lobes each terminate in four short lobules."""
    size, spread = p["size"], p["spread"]
    g.setup(voxel=.00082 * size, detail=4.2, smooth=.31)
    g.loft([V(0, y, 0) * size for y in (-.014, -.007, .004, .013)],
           [size * r for r in (.010, .013, .014, .011)], sides=16, density=3, up=V(0, 0, 1))
    for i in range(4):
        angle = math.pi * (.14 + i * .5)
        direction = V(math.cos(angle), 0, math.sin(angle))
        across = UP.cross(direction)
        span = spread * (.024 if i % 2 else .027)
        root = UP * .005 + direction * .006
        lobe = UP * .017 + direction * span * .73
        g.loft([v * size for v in (root, root.lerp(lobe, .53), lobe)],
               [size * r for r in (.0088, .0081, .0058)], sides=12, density=3)
        for daughter in (-1, 1):
            split = lobe + across * (.0038 * daughter) + direction * .003 + UP * .0028
            g.loft([v * size for v in (lobe, split)], [size * r for r in (.0049, .0033)],
                   sides=12, density=4)
            for lobule in (-1, 1):
                lateral = .0059 * daughter + .0030 * lobule
                tip = UP * (.024 + .002 * daughter * lobule) + direction * (span + .0015 * lobule)
                tip += across * lateral
                rounded_end = tip + (tip - split).normalized() * .0015
                g.loft([v * size for v in (split, tip, rounded_end)], [size * r for r in (.0034, .0019, .0007)],
                       sides=10, density=4)


def annelid_terminal_holdfast_discs(g, p):
    """One ventrally facing endpiece. An anterior instance includes an oral recess."""
    size, anterior = p["size"], round(p["anterior"])
    width = .074 if anterior else .095
    direction = 1 if anterior else -1
    contact = p["contact"]
    center_z = direction * .026
    rings = []
    # Surface of revolution from the buried upper neck to the ventral inside
    # face. Keeping the inner wall continuous leaves a chamber closed dorsally.
    profile = (
        (.25, .034), (.48, .024), (.70, .011), (.90, -.014), (1., -.032),
        (1.01, -.042), (.95, -.047), (.83, -.047), (.73, -.040), (.60, -.031),
        (.39, -.025), (.16, -.023 if anterior else -.022), (.05, -.014 if anterior else -.022),
    )
    for radius, height in profile:
        ring = []
        for i in range(32):
            angle = math.tau * i / 32
            x, z = math.cos(angle), math.sin(angle)
            h = height - contact * .009 * min(1, max(0, radius - .74) / .25)
            if anterior and radius < .75:
                h += .006 * (1 - radius) * math.cos(3 * angle) * min(1., 7 * radius)
            ring.append(V(width * radius * x, h, center_z + width * radius * z * (.80 if anterior else .89)) * size)
        rings.append(ring)
    g.setup(finish="sculpt_low")
    g.slot("skin")
    _closed_rings(g, rings)


def anuran_terminal_adhesive_pads(g, p):
    """One terminal toe disc with a low plantar face and a narrow joining neck."""
    rings = []
    size, width, thickness = p["size"], p["width"], p["thickness"]
    # Tips use +Y as the distal direction and +Z as their local plantar normal.
    profile = (
        (-.024, .006, -.006, .004), (-.020, .012, -.011, .009),
        (-.010, .015, -.012, .013), (.000, .017, -.010, .017),
        (.010, .023, -.005, .021), (.023, .033, .001, .022),
        (.034, .035, .004, .022), (.047, .031, .006, .022),
        (.058, .019, .007, .020), (.064, .004, .010, .013),
    )
    for y, w, dorsal, plantar in profile:
        ring = []
        flex = min(1., max(0., y / .027))
        rotation = rot((1, 0, 0), math.radians(p["flex"]) * flex)
        for i in range(24):
            angle = math.tau * i / 24
            x, z = math.cos(angle), math.sin(angle)
            half_depth = .5 * (plantar - dorsal)
            depth_center = .5 * (plantar + dorsal)
            swelling = min(1., max(0., (y + .007) / .027))
            exponent = lerp(.7, .30, swelling) if z >= 0 else .82
            point = V(x * w * lerp(1., width, swelling), y,
                      depth_center + math.copysign(abs(z) ** exponent, z) * half_depth * thickness)
            ring.append((rotation @ point) * size)
        rings.append(ring)
    g.setup(finish="sculpt")
    g.slot("skin")
    _closed_rings(g, rings)


PARTS = [
    Part("seahorse_grasping_tail", "manipulation", "Draft tapered four-faced armored tail with ventral coiling.",
         ["seahorse", "prehensile", "holdfast"], {"size": (.4, 2., 1.), "curl": (0., 1.08, .91)},
         seahorse_grasping_tail, attach="limb", orient="native", preset=seahorse_chain,
         symmetry="center", hint={"u": .08, "theta": 90.}),
    Part("reptile_rib_patagium", "locomotion", "Draft thoracic membrane carried by six elongated rib ridges.",
         ["draco", "lizard", "glide", "patagium", "rib", "membrane"],
         {"size": (.45, 2., 1.), "spread": (.16, 1., 1.)}, reptile_rib_patagium,
         orient="native", symmetry="pair", hint={"u": .58, "theta": 0.}),
    Part("avian_swim_flipper", "locomotion", "Draft continuous penguin swimming foil with an avian joint chain.",
         ["penguin", "flipper", "swimming", "avian", "hydrofoil"],
         {"size": (.45, 2., 1.), "chord": (.72, 1.28, 1.), "thickness": (.65, 1.35, 1.)},
         avian_swim_flipper, attach="limb", orient="native", cap="paddle", preset=penguin_flipper_chain,
         symmetry="pair", hint={"u": .68, "theta": 0.}),
    Part("toad_stellate_digit_organs", "sensory", "Draft Pipa fore-digit tip with four tactile lobes bearing sixteen lobules.",
         ["pipa", "surinam", "amphibian", "foredigit", "star", "sensory"],
         {"size": (.4, 2., 1.), "spread": (.85, 1.2, 1.)}, toad_stellate_digit_organs,
         attach="tip"),
    Part("annelid_terminal_holdfast_discs", "locomotion", "Draft ventral end sucker with anterior and posterior profiles.",
         ["leech", "annelid", "sucker", "holdfast", "terminal", "disc"],
         {"size": (.45, 2., 1.), "anterior": (0, 1, 0), "contact": (0., 1., .35)},
         annelid_terminal_holdfast_discs, attach="tip", orient="native", symmetry="center",
         discrete=("anterior",)),
    Part("anuran_terminal_adhesive_pads", "locomotion", "Draft expanded adhesive disc at the end of one treefrog digit.",
         ["treefrog", "frog", "toe", "adhesive", "plantar", "disc"],
         {"size": (.4, 2., 1.), "width": (.77, 1.28, 1.), "thickness": (.7, 1.3, 1.),
          "flex": (-18., 26., 0.)}, anuran_terminal_adhesive_pads, attach="tip", orient="plantar"),
]

TRAITS = {
    "seahorse_grasping_tail": {"function": "grasp", "construction": "deformable", "chain_skinning": "smooth",
                              "shape": "prehensile plated ringed coiling tail"},
    "reptile_rib_patagium": {"function": "fly", "shape": "lateral thoracic rib fan gliding membrane"},
    "avian_swim_flipper": {"function": "swim", "construction": "deformable", "chain_skinning": "smooth",
                          "shape": "compact swept continuous penguin flipper foil"},
    "toad_stellate_digit_organs": {"function": "sense", "shape": "branched stellate tactile forefinger tip"},
    "annelid_terminal_holdfast_discs": {"function": "support", "shape": "ventral anterior posterior leech sucker"},
    "anuran_terminal_adhesive_pads": {"function": "support", "shape": "expanded individual treefrog toe adhesive disc"},
}
