"""Limb tips. Origin at the limb's end joint.
Feet: +Y up, +Z forward, sole below the origin. Hands: +Y along the arm, +Z forward."""
import math
from ..kit import V, UP, BACK, RIGHT, rot, curve_points, taper, lerp
from . import Part


def foot_paw(g, p):
    s = p["size"]
    t = max(p["toes"], 0.1)
    g.setup(voxel=0.003 * s)
    g.slot("skin")
    g.loft([V(0, 0.03 * s, -0.01 * s), V(0, -0.03 * s, 0.01 * s), V(0, -0.07 * s, 0.04 * s)], [(0.06 * s, 0.06 * s), (0.075 * s, 0.08 * s), (0.085 * s, 0.09 * s)], sides=22, up=BACK)
    g.oval(V(0, -0.068 * s, 0.045 * s), (0.092 * s, 0.045 * s, 0.1 * s))
    for i in range(4):
        x = (i - 1.5) * 0.045 * s
        z = 0.12 * s - abs(i - 1.5) * 0.015 * s
        g.oval(V(x, -0.075 * s, z), (0.03 * s * t, 0.034 * s * t, 0.036 * s * t), segs=18, rings=10)


def foot_hoof(g, p):
    """A rounded foot with a level sole and an optional cloven groove."""
    s, split = p["size"], p["split"]
    g.setup(slot_finish={"dark": "direct", "skin": "subsurf_low"})
    g.slot("dark")
    # Heights, outer walls, heels and toes. The rearward shift at the crown
    # slopes the dorsal wall while keeping the ground contact horizontal.
    sections = (
        (-.138, .097, -.069, .121), (-.134, .103, -.075, .130),
        (-.124, .107, -.077, .133), (-.101, .104, -.076, .124),
        (-.075, .097, -.072, .112), (-.054, .085, -.067, .092),
        (-.043, .077, -.063, .080), (-.035, .065, -.056, .068),
    )
    sides = 40
    lobe_roundness = min(split / .6, 1.0)
    # At zero, a single perimeter makes a closed toe and sole.
    for side in (-1, 1) if split else (0,):
        verts = []
        for y, outer, heel, toe in sections:
            for i in range(sides):
                a = math.tau * i / sides
                cx, cz = math.cos(a), math.sin(a)
                width = math.copysign(abs(cx) ** .67, cx)
                depth = .5 + .5 * math.copysign(abs(cz) ** .73, cz)
                wall = outer - .011 * depth ** 2
                if side:
                    cleft = min(.004, .04 * split) + split * (.003 + .014 * depth ** 1.7)
                    # Narrow grooves follow the closed toe outline. Widening
                    # the groove rounds the two lobes into the cloven profile.
                    across = lerp(max(0.0, width), .5 + .5 * width, lobe_roundness)
                    x = side * lerp(cleft, wall, across)
                else:
                    x = width * wall
                verts.append(V(x, y, lerp(heel, toe, depth)) * s)
        faces = [tuple(range(sides))]
        for row in range(len(sections) - 1):
            base = row * sides
            for i in range(sides):
                j = (i + 1) % sides
                faces.append((base + i, base + sides + i, base + sides + j, base + j))
        faces.append(tuple(reversed(range(len(verts) - sides, len(verts)))))
        g._add(verts, faces if side >= 0 else [tuple(reversed(face)) for face in faces])
    g.slot("skin")
    stations = [(0, .052, -.024), (0, .014, -.010), (0, -.017, -.002),
                (0, -.045, .004), (0, -.060, .012), (0, -.070, .014)]
    radii = [(.055, .063), (.059, .067), (.064, .073), (.080, .074), (.080, .072), (.067, .063)]
    g.loft([V(station) * s for station in stations],
           [(depth * s, width * s) for width, depth in radii], sides=32, up=RIGHT)


def foot_claw(g, p):
    s, sp = p["size"], p["spread"]
    tal = max(p["talons"], 0.1)
    g.setup(voxel=0.0025 * s)
    g.slot("base")
    g.oval(V(0, -0.02 * s, 0.0), (0.04 * s, 0.03 * s, 0.045 * s), segs=18, rings=10)
    claws = []
    for i in range(4):
        a = (i - 1) * 0.45 * sp if i < 3 else math.pi
        d = V(math.sin(a), 0, math.cos(a))
        L = (0.16 if i < 3 else 0.075) * s
        base = V(0, -0.025 * s, 0)
        pts = [base, base + d * L * 0.45 + V(0, -0.012 * s, 0), base + d * L * 0.8 + V(0, -0.02 * s, 0), base + d * L + V(0, -0.022 * s, 0)]
        g.loft(pts, [0.026 * s, 0.021 * s, 0.019 * s, 0.016 * s], sides=14, up=UP)
        claws.append((pts[-1], d))
    g.slot("claw")
    for tip, d in claws:
        g.loft(curve_points(tip - d * 0.005 * s, d, V(0, -0.5, 0), 0.055 * s * tal, 4), [0.015 * s, 0.012 * s, 0.007 * s, 0.002 * s], sides=12, up=UP)


def foot_pad(g, p):
    s = p["size"]
    n = max(p["nails"], 0.1)
    g.slot("skin")
    g.loft([V(0, 0.03 * s, 0), V(0, -0.06 * s, 0), V(0, -0.12 * s, 0), V(0, -0.14 * s, 0)], [0.1 * s, 0.112 * s, 0.128 * s, 0.12 * s], sides=26, up=BACK, exponent=0.9)
    g.slot("detail")
    for i in range(3):
        a = (i - 1) * 0.55
        g.oval(V(math.sin(a) * 0.118 * s, -0.115 * s, math.cos(a) * 0.118 * s), (0.034 * s * n, 0.03 * s * n, 0.02 * s * n), rot(UP, a), segs=16, rings=10)


def foot_spike(g, p):
    s = p["size"]
    g.slot("dark")
    g.loft([V(0, 0.03 * s, 0), V(0, -0.03 * s, 0.003 * s), V(0, -0.09 * s, 0.006 * s), V(0, -0.12 * s, 0.004 * s)], [0.036 * s, 0.032 * s, 0.018 * s, 0.003 * s], sides=16, up=BACK)


def foot_webbed(g, p):
    s = p["size"]
    L = 0.22 * s * p["length"]
    g.setup(finish="subsurf")
    g.slot("accent")
    outline = [V(-0.03 * s, -0.03 * s, -0.01 * s), V(0.03 * s, -0.03 * s, -0.01 * s), V(0.075 * s, -0.035 * s, L * 0.6), V(0.105 * s, -0.035 * s, L),
               V(0.035 * s, -0.035 * s, L * 0.82), V(0, -0.035 * s, L * 0.95), V(-0.035 * s, -0.035 * s, L * 0.82), V(-0.105 * s, -0.035 * s, L), V(-0.075 * s, -0.035 * s, L * 0.6)]
    g.slab(outline, UP, 0.025 * s)
    g.use("self")
    g.slot("skin")
    g.slab([V(0.04 * s * math.cos(2 * math.pi * i / 8), 0.0, 0.04 * s * math.sin(2 * math.pi * i / 8)) for i in range(8)], UP, 0.05 * s)


def hand_basic(g, p):
    """Left hand with palm toward +Z, fingertips toward +Y and thumb on -X."""
    s = p["size"]
    length, curl = p["fingers"], p["curl"]
    g.setup(voxel=0.0020 * s, detail=12, smooth=.42)
    g.slot("skin")

    def loft(stations, radii, sides=20, exponent=1.0):
        g.loft([V(v) * s for v in stations], [(a * s, b * s) for a, b in radii],
               sides=sides, up=BACK, exponent=exponent)

    loft([(0, -.055, -.003), (0, -.015, -.002), (-.002, .013, -.001),
          (.002, .047, -.004), (.006, .074, -.004), (.003, .093, -.003), (.001, .104, 0)],
         [(.040, .047), (.029, .039), (.025, .037), (.025, .048),
          (.024, .055), (.019, .053), (.012, .041)], sides=32, exponent=.81)
    # Volumes for the thumb web and the ulnar pad leave a shallow palm hollow.
    g.oval(V(-.025, .045, .007) * s, V(.025, .038, .022) * s, rot(BACK, .28))
    g.oval(V(.032, .050, .004) * s, V(.020, .037, .019) * s, rot(BACK, -.14))
    for x, y, span, radius, splay in (
        (-.043, .087, .090, .0140, -.010), (-.014, .095, .100, .0140, -.002),
        (.015, .093, .090, .0125, .006), (.043, .084, .072, .0105, .014),
    ):
        reach = span * length
        flex = (.20 + curl * .53) * reach
        loft([(x, y, -.004), (x + splay * .28, y + reach * .29, -.004),
              (x + splay * .52, y + reach * .53, flex * .17),
              (x + splay * .75, y + reach * (.76 - .11 * curl), flex * .47),
              (x + splay, y + reach * (.97 - .32 * curl), flex * .92)],
             [(r * radius, w * radius) for r, w in
              ((1.04, 1.08), (.92, .90), (.94, .83), (.76, .69), (.61, .57))])
    loft([(-.027, .018, .010), (-.044, .033, .021), (-.058, .051, .029),
          (-.070, .064, .038), (-.077 + .007 * curl, .079, .053 + .012 * curl),
          (-.073 + .009 * curl, .083, .061 + .012 * curl)],
         [(.021, .019), (.021, .018), (.017, .014), (.015, .013),
          (.011, .010), (.007, .007)], sides=22)


def hand_claw(g, p):
    s = p["size"]
    cl = 0.12 * s * p["claw"]
    g.setup(voxel=0.0028 * s)
    g.slot("skin")
    g.oval(V(0, 0.045 * s, 0), (0.055 * s, 0.06 * s, 0.038 * s))
    tips = []
    for i in range(3):
        b = V((i - 1) * 0.033 * s, 0.09 * s, 0.008 * s)
        g.loft([b, b + V(0, 0.03 * s, 0.006 * s)], [0.018 * s, 0.016 * s], sides=14, up=BACK)
        tips.append(b + V(0, 0.03 * s, 0.006 * s))
    g.slot("claw")
    for t in tips:
        g.loft(curve_points(t, UP, V(0, -0.3, 0.9), cl, 5), taper(0.016 * s, 0.002, 5), sides=12, up=BACK)


def hand_pincer(g, p):
    s, bk = p["size"], p["bulk"]
    g.pivots["jaw"] = V(0.03 * s, 0.15 * s, 0)
    g.setup(voxel=0.003 * s)
    g.slot("accent")
    g.loft([V(0, 0.0, 0), V(0, 0.06 * s, 0), V(0, 0.13 * s, 0)], [(0.05 * bk * s, 0.04 * bk * s), (0.075 * bk * s, 0.055 * bk * s), (0.06 * bk * s, 0.045 * bk * s)], sides=24, up=BACK)
    g.loft(curve_points(V(-0.02 * s, 0.13 * s, 0), UP, V(0.35, 0, 0), 0.15 * s, 5), [0.032 * s * bk, 0.03 * s * bk, 0.022 * s * bk, 0.012 * s * bk, 0.003 * s], sides=18, up=BACK)
    g.use("jaw")
    g.setup(voxel=0.003 * s)
    g.slot("accent")
    g.loft(curve_points(V(0.035 * s, 0.14 * s, 0), UP, V(-0.4, 0, 0), 0.13 * s, 5), [0.026 * s * bk, 0.024 * s * bk, 0.018 * s * bk, 0.01 * s * bk, 0.003 * s], sides=18, up=BACK)


def hand_tentacle(g, p):
    s, c = p["size"], p["curl"]
    pts = []
    for i in range(9):
        a = (i / 8) * c * math.pi
        k = max(c * math.pi, 0.01)
        pts.append(V(0, math.sin(a) / k, (1 - math.cos(a)) / k) * 0.3 * s)
    g.slot("skin")
    g.loft(pts, taper(0.036 * s, 0.006, 9), sides=18, up=RIGHT)


def hand_mitt(g, p):
    s = p["size"]
    g.setup(voxel=0.003 * s)
    g.slot("skin")
    g.oval(V(0, 0.085 * s, 0), (0.07 * s, 0.095 * s, 0.048 * s))
    g.loft([V(0.04 * s, 0.05 * s, 0.015 * s), V(0.07 * s, 0.075 * s, 0.025 * s), V(0.075 * s, 0.1 * s, 0.03 * s)], [0.026 * s, 0.022 * s, 0.018 * s], sides=14, up=BACK)


T = dict(attach="tip")
PARTS = [
    Part("foot_paw", "foot", "Padded paw with four toe pads (cats, dogs, bears).", ["mammal", "cat", "dog", "bear", "cute"],
         {"size": (0.4, 3.0, 1.0), "toes": (0.0, 1.5, 1.0)}, foot_paw, cap="foot", **T),
    Part("foot_hoof", "foot", "Rounded hoof with adjustable groove width. Set split to 0 for a closed, boot-shaped toe.",
         ["bovine", "goat", "deer", "minotaur", "horse"],
         {"size": (0.4, 3.0, 1.0), "split": (0.0, 1.0, 0.6)}, foot_hoof,
         cap="foot", topology_changes=("split",), **T),
    Part("foot_claw", "foot", "Bird / raptor foot: three forward toes and one back toe with talons.", ["bird", "dinosaur", "raptor", "dragon"],
         {"size": (0.4, 3.0, 1.0), "spread": (0.3, 1.5, 1.0), "talons": (0.0, 2.0, 1.0)}, foot_claw, cap="foot", **T),
    Part("foot_pad", "foot", "Thick round column foot with toenails (elephants, sauropods, golems).", ["elephant", "sauropod", "heavy"],
         {"size": (0.4, 3.0, 1.0), "nails": (0.0, 1.5, 1.0)}, foot_pad, cap="foot", **T),
    Part("foot_spike", "foot", "Pointed leg tip (insects, spiders, crabs).", ["insect", "spider", "crab", "arthropod"],
         {"size": (0.4, 3.0, 1.0)}, foot_spike, cap="foot", **T),
    Part("foot_webbed", "foot", "Flat webbed foot or flipper (ducks, frogs, seals).", ["duck", "frog", "aquatic"],
         {"size": (0.4, 3.0, 1.0), "length": (0.5, 2.0, 1.0)}, foot_webbed, cap="foot", **T),
    Part("hand_basic", "hand", "Four-fingered hand with palm and thumb (humanoids, apes, minotaurs).", ["humanoid", "ape", "minotaur", "cartoon"],
         {"size": (0.4, 3.0, 1.0), "fingers": (0.5, 1.8, 1.0), "curl": (0.0, 1.0, 0.4)},
         hand_basic, cap="hand", orient="palm_in", **T),
    Part("hand_claw", "hand", "Clawed hand with three long curved talons (raptors, monsters, sloths).", ["monster", "raptor", "dragon", "menacing"],
         {"size": (0.4, 3.0, 1.0), "claw": (0.4, 2.5, 1.0)}, hand_claw, cap="hand", **T),
    Part("hand_pincer", "hand", "Crab / scorpion pincer with a hinged finger.", ["crab", "scorpion", "lobster", "arthropod"],
         {"size": (0.4, 3.0, 1.0), "bulk": (0.5, 2.0, 1.0)}, hand_pincer, cap="grasp",
         bones=[{"name": "jaw", "pivot": (0.03, 0.15, 0), "axis": (0, 0, 1), "angle": -30.0}], **T),
    Part("hand_tentacle", "hand", "Curling tentacle tip in place of a hand (octopus, aliens).", ["octopus", "alien", "aquatic", "creepy"],
         {"size": (0.4, 3.0, 1.0), "curl": (0.05, 1.5, 0.8)}, hand_tentacle, cap="hand", **T),
    Part("hand_mitt", "hand", "Simple rounded mitten hand with a thumb (cartoon, toy-like).", ["cartoon", "toy", "cute"],
         {"size": (0.4, 3.0, 1.0)}, hand_mitt, cap="hand", **T),
]
