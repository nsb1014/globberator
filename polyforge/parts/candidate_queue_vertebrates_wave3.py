"""Equine hoof, segmented xenarthran armor, and suspensory sloth manus drafts."""

import math

from ..kit import UP, V, lerp
from . import Part
from .research_locomotion import _closed_rings


def hoof_frog_heel_assembly(g, p):
    """Sole cup with a bearing rim, paired heel buttresses and a central frog."""
    size, cup = p["size"], p["cup"]
    rings = []
    levels = ((.025, .038, .037, -.025), (.003, .051, .055, -.015),
              (-.033, .058, .069, -.008), (-.074, .065, .080, -.002),
              (-.103, .070, .086, .003), (-.114, .068, .084, .004),
              (-.114, .062, .077, .004), (-.105, .054, .068, .004),
              (-.102, .039, .055, .005), (-.100, .021, .032, .010),
              (-.100, .008, .014, .010))
    for n, (y, width, length, z_center) in enumerate(levels):
        ring = []
        for j in range(36):
            angle = math.tau * j / 36
            x, z = math.cos(angle), math.sin(angle)
            heel = max(0., -z) ** 8
            toe_width = 1. + .085 * z
            sole_recess = max(0, n - 6) / 4. * cup * .016
            y_local = y + heel * .013 * min(1., n / 4.) + sole_recess
            ring.append(V(width * x * toe_width, y_local, length * z + z_center) * size)
        rings.append(ring)
    g.setup(finish="subsurf_low")
    g.slot("keratin")
    _closed_rings(g, rings)
    g.slot("frog")
    g.loft([V(0., y, z) * size for y, z in ((-.090, -.070), (-.100, -.061),
             (-.103, -.040), (-.105, -.018), (-.107, .020), (-.105, .041))],
           [(w * size, d * size) for w, d in ((.016, .009), (.023, .012),
            (.017, .013), (.012, .010), (.006, .007), (.0015, .003))],
           sides=16, density=3, exponent=.70)
    for side in (-1, 1):
        g.loft([V(side * x, y, z) * size for x, y, z in ((.036, -.094, -.068),
                 (.040, -.105, -.061), (.046, -.104, -.043))],
               [(w * size, d * size) for w, d in ((.014, .008), (.014, .010), (.009, .006))],
               sides=14, density=3)


def _armored_panel(g, stations, width, depth, closure, size):
    """Close a hollow cross section along an independent, pre-curved shell plate."""
    rings = []
    curve = .10 + closure * 4.6
    for z, breadth, arch, band_step in stations:
        flex = z * curve
        center_z = math.sin(flex) / curve
        center_y = (math.cos(flex) - 1.) / curve
        ring = []
        for side in (1, -1):
            samples = range(25) if side == 1 else reversed(range(25))
            for i in samples:
                angle = math.pi * (i / 24 - .5) * .94
                x = math.sin(angle) * width * breadth
                y = math.cos(angle) * depth * arch + band_step + side * .0032
                ring.append(V(x, center_y + y * math.cos(flex),
                              center_z + y * math.sin(flex)) * size)
        rings.append(ring)
    _closed_rings(g, rings)


def rolling_trunk_band_armor(g, p):
    """Thoracic and pelvic shields framing three overlapping transverse bands."""
    size, curl = p["size"], p["curl"]
    g.setup(finish="subsurf_low")
    g.slot("shields")
    thoracic = ((.077, 1., 1., -.004), (.095, 1.03, 1., .002), (.123, 1.05, .95, .002),
                (.174, .93, .83, 0.), (.223, .76, .66, 0.), (.252, .52, .50, -.002))
    pelvic = ((-.261, .56, .49, -.002), (-.230, .80, .66, 0.), (-.179, .97, .89, 0.),
              (-.126, 1.05, 1., .003), (-.102, 1.01, 1.01, .007), (-.084, .99, 1., .004))
    for section in (thoracic, pelvic):
        _armored_panel(g, section, .151, .128, curl, size)
    g.slot("belt")
    for offset in (-.060, -.004, .052):
        stations = tuple((offset + z, width, depth, step)
                         for z, width, depth, step in ((-.038, .969, 1.01, .001),
                             (-.031, .999, 1.03, .010), (-.010, 1.02, 1.04, .013),
                             (.017, 1.013, 1.01, .007), (.030, .993, .978, .000),
                             (.038, .972, .965, -.003)))
        _armored_panel(g, stations, .151, .128, curl, size)


def suspensory_hook_manus(g, p):
    """Three long hook tips carried by a narrow climbing manus."""
    size, curl = p["size"], p["curl"]
    g.setup(voxel=.00071 * size, smooth=.26, detail=3.9, slot_finish={"keratin": "subsurf_low"})
    g.slot("skin")
    g.loft([V(0., y, z) * size for y, z in ((.029, -.015), (.008, -.009),
             (-.014, .001), (-.027, .020), (-.028, .045), (-.028, .058))],
           [(w * size, d * size) for w, d in ((.014, .012), (.018, .015),
            (.020, .015), (.022, .014), (.022, .012), (.018, .010))],
           sides=20, density=3, exponent=.72)
    for i, (x, end_z, radius) in enumerate(((-.016, .067, .027), (0., .072, .030), (.016, .065, .027))):
        shift = .001 * i
        g.slot("skin")
        g.loft([V(x * q, -.026 + shift + y, z) * size for q, y, z in
                ((.81, 0., .039), (.96, 0., .052), (1., .001, .061), (1., .003, end_z))],
               [(w * size, h * size) for w, h in ((.008, .009), (.008, .008),
                (.0068, .006), (.0055, .005))], sides=14, density=3)
        g.slot("keratin")
        points = []
        radii = []
        for j in range(13):
            t = j / 12.
            angle = math.radians(136. + 29. * curl) * t
            y = -.023 + shift + radius * (1. - math.cos(angle))
            z = end_z - .005 + radius * math.sin(angle)
            points.append(V(x + x * .17 * t, y, z) * size)
            radii.append((lerp(.0062, .00064, t ** .80) * size,
                          lerp(.0071, .00068, t ** .84) * size))
        g.loft(points, radii, sides=12, density=2)


PARTS = [
    Part("hoof_frog_heel_assembly", "locomotion", "Draft hoof with one concave sole, heel buttresses and central frog.",
         ["horse", "hoof", "frog", "heel", "sole"], {"size": (.45, 2., 1.), "cup": (.25, 1., .67)},
         hoof_frog_heel_assembly, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("rolling_trunk_band_armor", "aesthetics", "Draft two fixed trunk shields with three overlapping waist bands.",
         ["armadillo", "shield", "shell", "band", "roll"], {"size": (.45, 2., 1.), "curl": (0., 1., .35)},
         rolling_trunk_band_armor, orient="native", host="body", symmetry="center"),
    Part("suspensory_hook_manus", "locomotion", "Draft suspensory manus with three parallel branch hooks.",
         ["sloth", "manus", "hook", "claw", "hang"], {"size": (.45, 2., 1.), "curl": (.10, 1., .60)},
         suspensory_hook_manus, attach="tip", orient="native", cap="foot", symmetry="pair"),
]
