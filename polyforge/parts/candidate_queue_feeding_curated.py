"""Isolated soft vestibule and specialized opposing dental surfaces."""

import math

from ..kit import RIGHT, UP, V, lerp
from . import Part
from .research_locomotion import _closed_rings


SIZE = {"size": (.70, 1.45, 1.)}


def pendulous_nasal_vestibule(g, p):
    size, hang = p["size"], p["hang"]
    g.setup(finish="subsurf_low")
    stations = ((.015,-.055,.035,.035),(.012,-.030,.040,.045),
                (-.010,.002,.046,.049),(-.043,.031,.049,.042),
                (-.074,.047,.043,.031),(-.091,.047,.032,.020),(-.100,.044,.012,.009))
    rings = []
    for y,z,w,depth in stations:
        rings.append([V(w*math.cos(math.tau*j/20), y*hang, z+depth*math.sin(math.tau*j/20))*size
                      for j in range(20)])
    _closed_rings(g,rings)
    skin = g.current.prims[-1]
    faces = []
    for face in skin.f:
        if set(face) not in ({82,83,102,103}, {86,87,106,107}):
            faces.append(face)
            continue
        corners = [skin.v[i] for i in face]
        center = sum(corners,V(0,0,0)) / 4
        last = face
        for width, depth in ((.84,.001),(.62,.007),(.42,.013)):
            ring = tuple(range(len(skin.v),len(skin.v)+4))
            skin.v.extend(center.lerp(corner,width)+V(0,0,-depth*size) for corner in corners)
            faces.extend((last[j],last[(j+1)%4],ring[(j+1)%4],ring[j]) for j in range(4))
            last=ring
        faces.append(last)
    skin.f=faces


def interdigitating_sieve_teeth(g, p):
    g.setup(finish="subsurf_low")
    size, gap = p["size"], p["gape"]
    for upper in (False,True):
        direction = -1 if upper else 1
        y = (.020+gap*.012)*(-direction)
        for tooth in range(4):
            width = .017*(1.07-.11*tooth)
            start = .021*tooth + (.007 if upper else 0)
            outline = ((0.,0.),(.04,.17),(.16,.39),(.22,.26),(.33,.60),
                       (.44,.43),(.57,1.),(.65,.57),(.77,.70),(.85,.33),
                       (.94,.43),(1.,.09),(1.,-.14),(.55,-.21),(0.,-.14))
            points = [V(.004*math.sin(tooth*.80),y + direction*.018*h*(1-.08*tooth),start+width*u)*size
                      for u,h in outline]
            g.leaf(points, RIGHT, .0067*size,cup=.05)


def radial_crushing_tooth_plates(g, p):
    g.setup(finish="subsurf_low")
    size, gap = p["size"], p["opening"]
    for upper in (False,True):
        sign = 1 if upper else -1
        y = sign*(.008+gap*.015)
        corners = ((-.025,.015),(-.023,-.008),(-.012,-.021),
                   (.002,-.021),(.024,-.013),(.036,.002),
                   (.028,.022),(.010,.030),(-.004,.022),(-.013,.022))
        g.leaf([V(x,y,z)*size for x,z in corners], UP*sign, .006*size,cup=.12)
        root=V(-.018,y,-.004)
        for i in range(6):
            turn = lerp(-.47,1.15,i/5) + (.05 if upper else 0.)
            d=V(math.cos(turn),0,math.sin(turn))
            extent=.041-.004*abs(i-2.8)
            ridge=UP*(-sign)
            g.loft([v*size for v in (root+d*.004,root+d*(extent*.35)+ridge*.0045,
                                      root+d*(extent*.72)+ridge*.0048,
                                      root+d*extent+ridge*.002)],
                   [r*size for r in (.0022,.0036,.0032,.00055)],
                   sides=12,density=2,up=UP)


PARTS = [
    Part("pendulous_nasal_vestibule","sensory","Broad pendulous vestibule with two separately rimmed nasal passages.",
         ["saiga","nose","vestibule"],{**SIZE,"hang":(.68,1.18,1.)},pendulous_nasal_vestibule,
         orient="native",symmetry="center",hint={"u":.94,"theta":90.}),
    Part("interdigitating_sieve_teeth","feeding","Opposing postcanine rows with tall center cusps and smaller lobes.",
         ["seal","dentition","sieve"],{**SIZE,"gape":(0.,1.,.30)},interdigitating_sieve_teeth,
         orient="native",symmetry="pair",hint={"u":.89,"theta":0.}),
    Part("radial_crushing_tooth_plates","feeding","Two dense dental plates with radiating ridges and free grooves.",
         ["lungfish","tooth plate","crushing"],{**SIZE,"opening":(.02,1.,.38)},radial_crushing_tooth_plates,
         orient="native",symmetry="pair",hint={"u":.87,"theta":0.}),
]
TRAITS={"pendulous_nasal_vestibule":{"function":"breathe","construction":"deformable"},
        "interdigitating_sieve_teeth":{"function":"feed"},"radial_crushing_tooth_plates":{"function":"feed"}}
