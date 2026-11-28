"""External arthropod drafts with +Y dorsal and +Z anterior."""

import math

from ..kit import BACK, RIGHT, UP, V, rot
from . import Part
from .candidate_arthropod import _loft
from .candidate_queue_arthropods import SIZE, UNIT
from .research_locomotion import _closed_rings


def paired_labellar_sponge(g, p):
    """Housefly distal haustellum and two grooved labellar lobes."""
    g.setup(finish="direct")
    size = p["size"]
    _loft(g, size, (
        (0, .018, -.014), (0, 0, -.007), (0, -.030, .004),
        (0, -.061, .013), (0, -.082, .018),
    ), ((.023, .020), (.029, .022), (.023, .019), (.016, .013), (.018, .016)),
          up=RIGHT)
    tilt = rot(BACK, -math.radians(61 * (1 - p["spread"])))
    seat = V(.008, -.079, .017)
    for side in (-1, 1):
        rings = []
        for j in range(26):
            t = j / 25
            width = .013 + .057 * math.sin(math.pi * (.90 * t + .06))**.74
            height = .004 + .015 * math.sin(math.pi * (.94 * t + .03))**.76
            z_center = -.020 * t + .012 * math.sin(math.pi * t)
            ring = []
            for a in range(56):
                phi = a * math.tau / 56
                surface = math.sin(phi)
                z = z_center + width * math.cos(phi)
                # Grooves following the mouthward arc of the ventral contact face.
                rib_wave = math.sin((z - .016 * t**1.3) * 427)
                groove = max(0., -surface)**1.7 * .0033 * math.exp(-(rib_wave / .50)**2)
                y = height * surface + groove - .003 * t
                pos = seat + tilt @ V(.004 + .092 * t, y, z)
                ring.append(V(side * pos.x, pos.y, pos.z) * size)
            rings.append(ring)
        _closed_rings(g, rings)


def eversible_forked_osmeterium(g, p):
    """Black-swallowtail eversible fork with a common slit and curved tips."""
    g.setup(finish="direct")
    size, deploy = p["size"], p["deploy"]
    length = .063 + .937 * deploy
    spread = .30 + .70 * deploy
    junction = V(0, -.008 + .064 * deploy, .008 * deploy)
    _loft(g, size, ((0, -.019, -.003), (0, -.014, -.002),
                    junction * .65 + V(0, -.009, 0), junction),
          ((.017, .009), (.020, .012), (.017, .012), (.013, .010)), up=RIGHT)
    for side in (-1, 1):
        _loft(g, size, [junction + V(side * x * spread, y * length, z * length) for x, y, z in (
            (.005, -.003, .002), (.023, .025, .003), (.051, .059, .006),
            (.068, .102, .014), (.068, .142, .029), (.052, .170, .040),
            (.046, .173, .042),
        )], (.0118, .0126, .011, .009, .0065, .004, .0018), up=RIGHT,
              sides=20, density=5)


def clustered_articulated_spinnerets(g, p):
    """Three bilateral spinneret pairs clustered on the abdominal underside."""
    g.setup(finish="direct")
    size = p["size"]
    for side in (-1, 1):
        # Lateral front and rear pairs are broad. The medial pair is smaller
        # and nestles between the lateral bases rather than in a straight row.
        for root, reach, radius, bias in (
            ((.051, 0, .028), .083, .025, -.61),
            ((.023, -.004, -.008), .055, .013, .08),
            ((.060, .006, -.056), .088, .027, .50),
        ):
            x, y, z = root
            hinge = V(side * x, y, z)
            turn = rot(RIGHT, bias + .42 * (p["gather"] - .5))

            def place(v):
                a, b, c = v
                return hinge + turn @ V(side * a, reach * b, reach * c)

            _loft(g, size, [place(v) for v in (
                (0, .20, .06), (.004, .026, .00), (.008, -.18, -.053),
                (.010, -.42, -.110), (.008, -.54, -.192),
            )], ((radius * .69, radius * .57), (radius, radius * .88),
                 (radius * .92, radius * .78), (radius * .80, radius * .74),
                 (radius * .62, radius * .61)), up=RIGHT, sides=20)
            _loft(g, size, [place(v) for v in (
                (.008, -.48, -.173), (.007, -.65, -.225), (.003, -.85, -.288),
                (-.003, -.98, -.327), (-.005, -1.021, -.339),
            )], ((radius * .59, radius * .57), (radius * .73, radius * .68),
                 (radius * .69, radius * .64), (radius * .48, radius * .45),
                 (radius * .22, radius * .20)), up=RIGHT, sides=20)


def hinged_book_gill_stack(g, p):
    """Left branchial appendage with an exopod, endopod and layered hemibranch."""
    g.setup(finish="direct")
    size = p["size"]
    hinge = rot(RIGHT, math.radians(39 * p["stroke"]))

    def place(pos):
        return hinge @ V(pos)

    _loft(g, size, [place(v) for v in (
        (.008, 0, .020), (.050, 0, -.012), (.083, -.005, -.054),
        (.134, -.015, -.106), (.169, -.022, -.151), (.184, -.027, -.173),
        (.190, -.030, -.180),
    )], ((.024, .013), (.050, .017), (.088, .018), (.100, .016),
         (.078, .013), (.049, .009), (.015, .005)), up=RIGHT)
    _loft(g, size, [place(v) for v in (
        (.012, .002, .012), (.016, -.007, -.038), (.021, -.016, -.089),
        (.032, -.024, -.138), (.065, -.028, -.174),
    )], ((.022, .011), (.025, .012), (.028, .010), (.024, .009), (.009, .004)),
          up=RIGHT, sides=20)

    for index in range(21):
        t = index / 20
        root = V(.044 + .104 * t, .008 + .005 * t, -.042 - .064 * t)
        scale = .51 + .49 * math.sin(math.pi * (.66 * t + .28))
        # Each free page originates on the plate and bows dorsoposteriorly.
        # Adjacent pages are vertically stepped so that their faces stay separate.
        rings = []
        for z, span, lift, depth, offset in (
            (.004, .013, 0, .0016, .002), (-.015, .044, .009, .0019, .002),
            (-.040, .063, .025, .0019, .005), (-.072, .071, .039, .0017, .010),
            (-.100, .056, .051, .0016, .013), (-.121, .038, .056, .0014, .016),
            (-.131, .017, .060, .0011, .018), (-.134, .004, .061, .0008, .018),
        ):
            rings.append([place(root + V((offset + span * math.cos(a * math.tau / 18)) * scale,
                                         lift + depth * math.sin(a * math.tau / 18) + t * .067,
                                         z * scale)) * size for a in range(18)])
        _closed_rings(g, rings)
        # Narrow elevated web connects the page root to its operculate carrier.
        _loft(g, size, [place(root + v) for v in
                        (V(0, -.015, 0), V(0, t * .033, -.002), V(0, t * .067, 0))],
              (.0052, .0045, .0031), up=RIGHT, sides=10, density=2)


PARTS = [
    Part("paired_labellar_sponge", "feeding", "Two soft labellar lobes unfold to expose grooved ventral faces.",
         ["housefly", "labella", "sponge", "pseudotracheae"], {"size": SIZE, "spread": (0., 1., .9)},
         paired_labellar_sponge, orient="native", symmetry="center"),
    Part("eversible_forked_osmeterium", "aesthetics", "A soft fork deploys above the larval prothorax.",
         ["swallowtail", "osmeterium", "eversible organ", "caterpillar"], {"size": SIZE, "deploy": (0., 1., .88)},
         eversible_forked_osmeterium, orient="native", symmetry="center"),
    Part("clustered_articulated_spinnerets", "manipulation", "Three paired spinnerets articulate around the abdominal tip.",
         ["orb-weaver", "spider", "spinneret", "silk"], {"size": SIZE, "gather": (0., 1., .5)},
         clustered_articulated_spinnerets, orient="native", symmetry="center"),
    Part("hinged_book_gill_stack", "locomotion", "A broad horseshoe-crab branchial appendage hinges with a dorsal stack of thin pages.",
         ["horseshoe crab", "book gill", "lamella", "branchial appendage"], {"size": SIZE, "stroke": (0., 1., .18)},
         hinged_book_gill_stack, orient="native", symmetry="pair"),
]

TRAITS = {
    "paired_labellar_sponge": {"function": "feed"},
    "eversible_forked_osmeterium": {"function": "display"},
    "clustered_articulated_spinnerets": {"function": "silk"},
    "hinged_book_gill_stack": {"function": "breathe"},
}
