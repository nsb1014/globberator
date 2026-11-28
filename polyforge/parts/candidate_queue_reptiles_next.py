"""Isolated substrate, shielding and brood anatomy in the common part frame."""

import math

from ..kit import UP, V, lerp, smoothstep
from . import Part
from .research_locomotion import _closed_rings


SIZE = {"size": (.75, 1.35, 1.)}


def sand_fringe_digit(g, p):
    size, fringe = p["size"], p["fringe"]
    g.setup(finish="subsurf_low")
    g.loft([V(0, 0, z) * size for z in (-.003, .002, .012, .026, .036, .041)],
           [(w*size, h*size) for w,h in ((.002,.0018),(.0024,.0019),(.00215,.0015),
                                         (.0016,.0013),(.00115,.001),(.0003,.0005))],
           sides=16, density=3)
    for sign, n in ((-1, 11), (1, 13)):
        for i in range(n):
            t = i / (n-1)
            z = lerp(.004, .037, t)
            a = lerp(.0019,.00105,t)
            x = sign * a
            width = .0032 * fringe * (.66 + .34 * math.sin(math.pi*t))
            outline = [(x*.68,-.00065,z-.0011),(x*.82,-.00065,z+.00165),
                       (x+sign*width*.67,-.0011,z+.0024),(x+sign*width,-.0013,z+.0031),
                       (x+sign*width*.6,-.00088,z+.0001)]
            g.leaf([V(*point)*size for point in outline], UP, .00054*size, cup=.1)


def hindfoot_excavation_spade(g, p):
    size, curvature = p["size"], p["bevel"]
    g.setup(finish="subsurf_low")
    outline = ((-.006,.001,-.010),(.002,.001,-.010),(.010,.001,-.005),(.012,.001,.004),
               (.010,0,.008),(.004,-.001,.006),(.001,-.002,.001),(-.003,-.003,-.004),
               (-.008,-.005,-.007),(-.011,-.006,-.009))
    g.leaf([V(x, y * curvature, z)*size for x, y, z in outline],
           V(0, -1, 0), .0037*size, cup=.28)


def ventral_traction_scute_row(g, p):
    size, count = p["size"], int(p["count"])
    g.setup(finish="subsurf_low")
    for i in range(count):
        z = (i-(count-1)/2)*.012
        contour = [(-.025,.003,z-.004),(-.021,-.002,z-.0085),(-.010,-.006,z-.0088),
                   (.009,-.006,z-.0082),(.022,-.002,z-.007),(.027,.003,z-.004),
                   (.026,.004,z+.004),(.016,-.003,z+.006),(-.013,-.003,z+.006),
                   (-.025,.003,z+.004)]
        g.leaf([V(*point)*size for point in contour],V(0,-1,0),.0021*size,cup=.08)


def raised_trunk_annuli(g, p):
    size, bend = p["size"], p["bend"]
    g.setup(finish="direct")
    profile = []
    for i in range(13*5+1):
        phase, t = i%5, i/(13*5)
        outer = .0137 * (1. - .18*(t-.5)**2)
        radius = outer * (.91 if phase == 0 else .985 if phase in (1,4) else 1.0)
        profile.append((t,radius))
    profile += [(1.,.0107),(0.,.0107)]
    sides = 28
    verts = []
    for t,radius in profile:
        along = .15*(t-.5)
        center = V(bend*.032*(2*t-1)**2, 0, along)
        axis = V(bend*.128*(2*t-1),0,.150).normalized()
        lateral = V(axis.z,0,-axis.x)
        for j in range(sides):
            angle = math.tau * j / sides
            point = center + lateral * radius * math.cos(angle) + UP * .87 * radius * math.sin(angle)
            verts.append(point * size)
    faces = []
    for i in range(len(profile)):
        m = (i+1)%len(profile)
        for j in range(sides):
            k = (j+1)%sides
            faces.append((i*sides+j, i*sides+k,m*sides+k,m*sides+j))
    signed = sum(verts[f[0]].dot(verts[f[j]].cross(verts[f[j+1]])) for f in faces for j in (1,2))
    if signed < 0:
        faces = [face[::-1] for face in faces]
    g._add(verts,faces)


def dorsal_brood_cell_patch(g, p):
    size = p["size"]
    g.setup(voxel=.00093 * size, smooth=.25)
    g.oval(V(0,0,0),(.039*size,.009*size,.049*size),segs=36,rings=22)
    for row in range(-3,4):
        for column in range(-3,4):
            x = .0092 * (column + (row%2)*.49)
            z = .0114 * row
            ell = (x/.037)**2+(z/.046)**2
            if ell > .79:
                continue
            y = .009 * math.sqrt(max(0.,1.-ell))
            radius = .0039 + .00038 * math.sin(2.3*column+row)
            g.oval(V(x,y+.0009,z)*size,(1.23*radius*size,.0021*size,1.24*radius*size),
                   segs=12,rings=8)
            g.oval(V(x,y+.0038,z)*size,(radius*size,.0058*size,radius*size),
                   segs=16,rings=10,negative=True)


PARTS = [
    Part("sand_fringe_digit","locomotion","Long toe with two rows of individually pointed sand-fringe scales.",
         ["reptile","toe","sand","fringe"],{**SIZE,"fringe":(.55,1.22,1.)},
         sand_fringe_digit,attach="tip",orient="native",host="limb_end"),
    Part("hindfoot_excavation_spade","locomotion","Recurved medial metatarsal spade for backward excavation.",
         ["amphibian","heel","digging","spade"],{**SIZE,"bevel":(.62,1.25,1.)},
         hindfoot_excavation_spade,orient="surface",host="limb"),
    Part("ventral_traction_scute_row","locomotion","Overlapping broad belly plates arranged transverse to the trunk.",
         ["snake","traction","belly","scale"],{**SIZE,"count":(4,14,8)},
         ventral_traction_scute_row,orient="native",discrete=("count",),hint={"u":.5,"theta":-90.}),
    Part("raised_trunk_annuli","aesthetics","Continuous folded skin sleeve with shallow annular valleys.",
         ["worm lizard","annuli","skin"],{**SIZE,"bend":(-1.,1.,.25)},
         raised_trunk_annuli,orient="native",symmetry="center"),
    Part("dorsal_brood_cell_patch","aesthetics","Dorsal integument patch with distinct recessed brood-cell rims.",
         ["toad","skin","brood"],SIZE,dorsal_brood_cell_patch,orient="native",symmetry="center"),
]
