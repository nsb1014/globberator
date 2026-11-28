"""Reptile queue drafts in the standard +Y dorsal, +Z forward part frame."""

import math

from scipy.interpolate import PchipInterpolator

from ..kit import RIGHT, UP, V, rot, smoothstep
from . import Part
from .research_locomotion import _closed_rings


SIZE = {"size": (.65, 1.5, 1.)}


def lamellar_climbing_digit(g, p):
    g.setup(finish="direct")
    # Pad occupies most of the digit, with a narrow recurved claw beyond it.
    size, peel = p["size"], p["release"]
    widths = PchipInterpolator((0., .11, .28, .52, .73, .87, .97, 1.),
                              (.0021, .0025, .0041, .0038, .0031, .0022, .0011, .0005))
    rings = []
    for i in range(85):
        t = i / 84
        z = -.002 + .024 * t
        y = .010 * peel * smoothstep(.38, 1., t)
        x = -.0025 * t**1.7
        envelope = smoothstep(.12, .29, t) * (1. - smoothstep(.84, .98, t))
        ring = []
        for j in range(20):
            a = math.tau * j / 20
            c, d = math.cos(a), math.sin(a)
            lamella = max(0., math.cos(math.tau * (21 * t - .42 * c * c)))**3
            edge = .00070 * envelope * max(0., -d)**2 * lamella
            ring.append(V(x + c * float(widths(t)), y + .0016 * d - edge, z) * size)
        rings.append(ring)
    _closed_rings(g, rings)
    g.loft([V(-.0023, .010 * peel + y, z) * size for y, z in
            ((.0003, .0199), (.0008, .0222), (.0006, .0234), (-.0005, .024), (-.0012, .0241))],
           [size * radius for radius in (.0009, .00073, .00049, .00024, .00006)],
           sides=14, density=2)


def opposed_toe_bundles(g, p):
    size, grip = p["size"], p["grip"]
    g.setup(finish="voxel", voxel=.00062, smooth=.30)
    g.oval(V(0., 0., .003) * size, (.0070 * size, .0038 * size, .0089 * size),
           segs=24, rings=14)
    for side, lengths in ((-1, (.019, .023, .0195)), (1, (.020, .0165))):
        # Fused interdigital tissue spans each bundle. A true cleft stays between them.
        for i, length in enumerate(lengths):
            rank = i - (len(lengths) - 1) / 2
            base = V(side * (.0028 + rank * .0020), -.0008, .0064 + rank * .0027)
            middle = base + V(side * length * (.58 - .25 * grip), -.004 - .004 * grip, length * .43)
            tip = base + V(side * length * (.76 - .52 * grip), -.008 - .009 * grip, length * .68 + rank*.0061)
            g.loft([point * size for point in (base, middle, tip)], [
                (.0041 * size, .0037 * size), (.0037 * size, .0028 * size),
                (.0021 * size, .00185 * size)], sides=18, density=4)
    # Claws are separate regions. They remain readable against the soft fused base.
    g.slot("claws")
    g.setup(slot_finish={"claws": "direct"})
    for side, lengths in ((-1, (.019, .023, .0195)), (1, (.020, .0165))):
        for i, length in enumerate(lengths):
            rank = i - (len(lengths) - 1) / 2
            base = V(side * (.0028 + rank * .0020), -.0008, .0064 + rank * .0027)
            tip = base + V(side * length * (.76 - .52 * grip), -.008 - .009 * grip, length * .68 + rank*.0061)
            g.loft([point * size for point in (tip + V(0,.001,-.002), tip + V(0,-.001,.003),
                                               tip + V(-side * .001,-.004,.005))],
                   [radius * size for radius in (.00142,.00092,.00011)], sides=12, density=3)


def interlocking_caudal_rattle(g, p):
    size, count = p["size"], int(p["count"])
    g.setup(finish="subsurf_low")
    # Per-segment wall loops preserve the open proximal and distal lips.
    # Captive joint play is a separate validation task.
    side_count = 20
    for i in range(count):
        center = -.0081 * i
        taper = 1. - .42 * i / max(count - 1, 1)
        profile = ((-.0048,.72),(-.0039, .99),(-.0015,1.06),(.0016,.98),(.0045,.72),
                   (.0045,.55),(.0014,.77),(-.0014,.84),(-.0041,.57),(-.0048,.56))
        verts = []
        for shift, factor in profile:
            for j in range(side_count):
                a = math.tau * j / side_count
                width = .0092 * taper * factor * (1. -.095 * math.sin(a)**6)
                height = .0056 * taper * factor
                verts.append(V(width * math.cos(a), height * math.sin(a) + .00024 * i**1.25,
                               center + shift) * size)
        faces = []
        for ring in range(len(profile)):
            following = (ring + 1) % len(profile)
            for j in range(side_count):
                k = (j + 1) % side_count
                faces.append((ring * side_count+j, following*side_count+j,
                              following*side_count+k,ring*side_count+k))
        # The profile runs from distal exterior to proximal interior.
        signed = sum(verts[face[0]].dot(verts[face[j]].cross(verts[face[j+1]]))
                     for face in faces for j in (1,2))
        if signed < 0:
            faces = [face[::-1] for face in faces]
        g._add(verts, faces)
        if i == count - 1:
            # Leave the preceding segment sockets hollow and close the visible tip.
            g.oval(V(0, .00024 * i**1.25, center - .0039) * size,
                   (.0068*taper*size, .0043*taper*size, .0019*size), segs=20, rings=9)


def hinged_plastral_lobe(g, p):
    size = p["size"]
    hinge = rot(RIGHT, math.radians(p["opening"]))
    g.setup(finish="subsurf_low")
    profile = ((-.002,.063,.0033),(.001,.065,.0036),(.013,.067,.0046),
                (.035,.067,.0062),(.055,.056,.0055),(.070,.037,.0042),
                (.079,.014,.0029),(.081,.003,.0015))
    widths = PchipInterpolator([p[0] for p in profile], [p[1] for p in profile])
    depths = PchipInterpolator([p[0] for p in profile], [p[2] for p in profile])
    sections = [(z, float(widths(z)), float(depths(z))) for z in
                (-.002,.001,*[.004 + .0025*i for i in range(30)],.079,.081)]
    rings = []
    for z, width, thickness in sections:
        ring = []
        for i in range(28):
            a = math.tau * i / 28
            c,d = math.cos(a),math.sin(a)
            x = width*c
            dome = .006 * (1.-c*c) * smoothstep(.005,.036,z)
            scutes = math.exp(-((z-.028-.14*abs(x))/.0027)**2)
            scutes += .85*math.exp(-((z-.056+.15*abs(x))/.0027)**2)
            seam = .0015 * (math.exp(-(x/.0032)**2)+scutes) * max(0.,-d)
            ring.append(hinge @ (V(x, dome + thickness*d + seam, z)*size))
        rings.append(ring)
    _closed_rings(g, rings)


def flattened_leaf_tail(g, p):
    g.setup(finish="subsurf_low")
    size, width = p["size"], p["width"]
    # Deliberate unequal margin bites on the adult male leaf blade.
    left = ((0.,.0036),(.013,.0046),(.021,.012),(.028,.019),(.038,.023),
            (.046,.025),(.051,.0205),(.056,.023),(.064,.0185),(.072,.016),
            (.077,.0115),(.080,.009),(.093,.0008))
    right = ((0.,.0034),(.013,.0042),(.021,.009),(.029,.017),(.035,.014),
             (.041,.021),(.050,.023),(.058,.021),(.064,.015),(.068,.017),
             (.076,.010),(.084,.005),(.093,.0008))
    perimeter = [V(-w*width,.0018*math.sin(math.pi*z/.093),-z-.010*smoothstep(.002,.022,z))*size for z,w in left]
    perimeter += [V(w*width,.0028*math.sin(math.pi*z/.093),-z-.010*smoothstep(.002,.022,z))*size for z,w in reversed(right)]
    g.leaf(perimeter, UP, .0041 * size, cup=.12)


PARTS = [
    Part("lamellar_climbing_digit","manipulation","Single broad adhesive digit with transverse lamellae and tip claw.",
         ["reptile","gecko","adhesion","digit"], {**SIZE,"release":(0.,1.,.15)},
         lamellar_climbing_digit,attach="tip",orient="native",host="limb_end"),
    Part("opposed_toe_bundles","manipulation","Five chameleon toes arranged in opposed three- and two-digit bundles.",
         ["reptile","chameleon","branch","grip"], {**SIZE,"grip":(.05,.78,.27)},
         opposed_toe_bundles,attach="tip",orient="native",host="limb_end"),
    Part("interlocking_caudal_rattle","aesthetics","Tapered series of hollow terminal keratin segment walls.",
         ["snake","rattle","tail"], {**SIZE,"count":(3,10,7)},interlocking_caudal_rattle,
         orient="native",symmetry="center",discrete=("count",),hint={"u":.02,"theta":90.}),
    Part("hinged_plastral_lobe","aesthetics","Anterior plastron door with transverse pivot edge and broad thin plate.",
         ["shell","turtle","underside","plastron"], {**SIZE,"opening":(0.,40.,12.)},
         hinged_plastral_lobe,orient="native",symmetry="center",hint={"u":.68,"theta":-90.}),
    Part("flattened_leaf_tail","aesthetics","Thin caudal leaf with irregular margins and a narrow stem.",
         ["tail","gecko","leaf","camouflage"], {**SIZE,"width":(.72,1.24,1.)},
         flattened_leaf_tail,orient="native",symmetry="center",hint={"u":.04,"theta":90.}),
]

TRAITS = {
    "lamellar_climbing_digit": {"function":"grasp","construction":"deformable"},
    "opposed_toe_bundles": {"function":"grasp","construction":"deformable"},
    "interlocking_caudal_rattle": {"function":"display"},
    "hinged_plastral_lobe": {"function":"protect"},
    "flattened_leaf_tail": {"function":"display","construction":"deformable"},
}
