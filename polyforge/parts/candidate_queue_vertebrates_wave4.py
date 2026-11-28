"""Additional isolated limb and external contact parts in the native frame."""

import math

from ..kit import UP, V, lerp
from . import Part
from .research_locomotion import _closed_rings, _feather


def syndactyl_grooming_toes(g, p):
    """Marsupial digits II and III with one sheath and two free grooming claws."""
    size, flex = p["size"], p["flex"]
    g.setup(voxel=.00037 * size, smooth=.28, detail=3.75,
            slot_finish={"keratin": "subsurf_low"})
    g.slot("skin")
    g.loft([V(*point) * size for point in ((0., .004, -.010), (0., .001, .002),
             (0., -.002, .014), (0., -.003, .029), (0., -.004, .039))],
           [(w * size, h * size) for w, h in ((.0054, .0045), (.0069, .005),
             (.0071, .0042), (.0069, .0035), (.0058, .0028))],
           sides=18, density=3, exponent=.66)
    for side, offset in ((-1, .003), (1, 0.)):
        x = side * .0040
        bend = .003 + .004 * flex
        g.slot("skin")
        g.loft([V(*point) * size for point in ((x * .54, -.003, .028),
                 (x * .83, -.004, .037 + offset), (x, -.005, .044 + offset),
                 (x, -.003 - bend, .048 + offset))],
               [r * size for r in (.0035, .0035, .0028, .0018)], sides=12, density=3)
        g.slot("keratin")
        g.loft([V(*point) * size for point in ((x, -.004, .042 + offset),
                 (x * 1.04, -.003, .049 + offset), (x * 1.08, -.007, .055 + offset),
                 (x * 1.12, -.009 - bend, .057 + offset))],
               [(w * size, h * size) for w, h in ((.0028, .0021), (.0025, .0018),
                 (.0016, .0014), (.0004, .0005))],
               sides=12, density=3)


def partially_fused_perching_foot(g, p):
    """Kingfisher foot with a joined digit III–IV sleeve and free curled tips."""
    size, curl = p["size"], p["curl"]
    g.setup(voxel=.00042 * size, smooth=.24, detail=4.0, slot_finish={"keratin": "subsurf_low"})
    g.slot("skin")
    g.oval(V(0., -.003, 0.) * size, V(.0115, .0097, .0140) * size)
    g.loft([V(0, y, z) * size for y, z in ((.003, -.004), (.014, -.007), (.024, -.009))],
           [r * size for r in (.0079, .0084, .0077)], up=V(0, 0, 1), sides=16, density=3)
    for base, mid, tip, radius in (
        ((-.006, -.005, .005), (-.014, -.006, .027), (-.018, -.009, .041), .0036),
        ((.000, -.004, .005), (.002, -.005, .032), (.001, -.007, .055), .0041),
        ((.006, -.004, .005), (.009, -.005, .028), (.016, -.008, .045), .0037),
        ((-.003, -.003, -.005), (-.007, -.004, -.017), (-.009, -.008, -.029), .0035),
    ):
        first, middle, terminal = V(*base), V(*mid), V(*tip)
        terminal.y -= curl * (.009 if terminal.z > 0 else .006)
        reach = (terminal - middle).normalized()
        g.slot("skin")
        g.loft([v * size for v in (first, middle, terminal)],
               [r * radius * size for r in (1.1, 1., .57)], sides=14, density=4)
        g.slot("keratin")
        claw = terminal + reach * .007 + V(0., -.0038, 0.)
        g.loft([v * size for v in (terminal - reach * .003, terminal + reach * .003, claw)],
               [r * radius * size for r in (.75, .60, .14)], sides=11, density=3)
    g.slot("skin")
    g.loft([V(*point) * size for point in ((.003, -.004, .003), (.004, -.005, .014),
             (.005, -.005, .025), (.006, -.005, .032))],
           [(w * size, h * size) for w, h in ((.007, .0047), (.0076, .0039),
             (.0070, .0038), (.0049, .0034))], sides=16, density=3, exponent=.65)


def bark_bracing_rectrix_pair(g, p):
    """Two enlarged load-bearing rectrices with visible tapering shaft ribs."""
    size, brace = p["size"], p["brace"]
    g.setup(finish="subsurf_low")
    g.slot("vane")
    for side in (-1, 1):
        for index, reach in enumerate((.221, .187, .153, .120)):
            root = V(side * (.008 + .008 * index), .012 + .004 * index, .016)
            end = V(side * (.017 + index * .025), -.083 - .094 * brace + .024 * index,
                    -reach * (1. - .10 * brace))
            _feather(g, root, end, .018 - index * .0025, .0047 - index * .0007, size)
        g.slot("shaft")
        root = V(side * .010, .016, .017)
        middle = V(side * .015, -.024 - .064 * brace, -.108)
        tip = V(side * .017, -.083 - .094 * brace, -.221 * (1. - .10 * brace))
        g.loft([v * size for v in (root, middle, tip)],
               [(w * size, h * size) for w, h in ((.0053, .0057), (.0037, .0044), (.0007, .0011))],
               sides=12, density=3)
        g.slot("vane")


def free_climbing_wing_digits(g, p):
    """Hoatzin nestling wrist, shortened pinfeather edge and two free clawed rays."""
    size, grip = p["size"], p["grip"]
    g.setup(voxel=.00062 * size, smooth=.27, detail=4.8,
            slot_finish={"keratin": "subsurf_low", "pinfeathers": "subsurf_low"})
    g.slot("skin")
    g.loft([V(*point) * size for point in ((-.052, .002, -.029), (-.024, -.001, -.018),
             (0., 0., 0.), (.041, -.003, .008), (.060, -.006, -.004))],
           [(w * size, h * size) for w, h in ((.0150, .013), (.019, .013),
             (.024, .014), (.019, .010), (.009, .008))],
           sides=20, density=3, exponent=.76)
    for start, middle, head, size_weight in (
        ((-.004, .001, .005), (.007, .006, .032), (.024, .004, .042), 1.),
        ((.029, -.001, .005), (.056, .001, .019), (.073, -.004, .022), .79),
    ):
        root, mid, end = V(*start), V(*middle), V(*head)
        end.y -= grip * .010
        g.slot("skin")
        g.loft([v * size for v in (root, mid, end)],
               [r * size_weight * size for r in (.0065, .0059, .0042)], sides=14, density=3)
        axis = (end - mid).normalized()
        g.slot("keratin")
        points = (end - axis * .005, end + axis * .006,
                  end + axis * .010 + V(0., -.005, 0.),
                  end + axis * .008 + V(0., -.010 - .006 * grip, 0.))
        g.loft([v * size for v in points],
               [r * size_weight * size for r in (.0047, .0040, .0029, .00065)],
               sides=12, density=3)
    g.slot("pinfeathers")
    for i in range(5):
        root = V(-.039 + .017 * i, .001, -.020 + .002 * i)
        end = root + V(.009 + .003 * i, -.004, -.026 - .003 * i)
        _feather(g, root, end, .0054, .0028, size)


def ventral_brooding_drape(g, p):
    """Abdominal skin fold with a scalloped free rim over the foot platform."""
    size, cover = p["size"], p["cover"]
    g.setup(finish="subsurf_low")
    g.slot("skin")
    rings = []
    for station in (-1., -.88, -.68, -.45, -.21, 0., .21, .45, .68, .88, 1.):
        x = .139 * station
        center = max(0., 1. - station * station) ** .70
        stations = [
            (lerp(.034, .073, center), -.037, .011),
            (.022 + .030 * center, -.010, .019),
            (-.009 - .005 * center, .038 + .054 * center, .018),
            (-.037 - (.014 + .039 * cover) * center, .059 + .063 * center, .010),
            (-.049 - (.018 + .049 * cover) * center, .058 + .057 * center, .006),
        ]
        spread = max(.12, center)
        skin = [V(x, y, z + direction * thick * spread) * size
                for direction, points in ((1, stations), (-1, reversed(stations)))
                for y, z, thick in points]
        rings.append(skin)
    _closed_rings(g, rings)


PARTS = [
    Part("syndactyl_grooming_toes", "locomotion", "Draft marsupial grooming toe pair within a shared sheath.",
         ["wallaby", "toes", "grooming", "syndactyl"], {"size": (.45, 2., 1.), "flex": (0., 1., .37)},
         syndactyl_grooming_toes, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("partially_fused_perching_foot", "locomotion", "Draft perching foot with a partially joined forward toe pair.",
         ["kingfisher", "foot", "perch", "syndactyl"], {"size": (.45, 2., 1.), "curl": (0., 1., .43)},
         partially_fused_perching_foot, attach="tip", orient="native", cap="foot", symmetry="pair"),
    Part("bark_bracing_rectrix_pair", "locomotion", "Draft structural tail with two long bark-contact rectrices.",
         ["woodpecker", "rectrix", "tail", "bark", "prop"], {"size": (.45, 2., 1.), "brace": (0., 1., .72)},
         bark_bracing_rectrix_pair, orient="native", host="body", symmetry="center", hint={"u": .08, "theta": 90.}),
    Part("free_climbing_wing_digits", "locomotion", "Draft nestling wing hand with two free climbing digits.",
         ["hoatzin", "wing", "nestling", "claw"], {"size": (.45, 2., 1.), "grip": (0., 1., .56)},
         free_climbing_wing_digits, orient="native", host="limb", symmetry="pair"),
    Part("ventral_brooding_drape", "aesthetics", "Draft ventral abdominal fold forming a cover over the feet.",
         ["penguin", "incubation", "brood", "drape"], {"size": (.45, 2., 1.), "cover": (0., 1., .75)},
         ventral_brooding_drape, orient="native", host="body", symmetry="center", hint={"u": .37, "theta": -90.}),
]
