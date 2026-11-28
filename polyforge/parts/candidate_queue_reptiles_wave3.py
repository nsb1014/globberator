"""Local protective, respiratory and gliding surface parts."""

import math

from ..kit import BACK, UP, V, lerp, smoothstep
from . import Part
from .research_locomotion import _closed_rings


SIZE = {"size": (.65, 1.5, 1.)}


def spiny_tail_whorls(g, p):
    size, count = p["size"], int(p["rings"])
    g.setup(finish="direct")
    rings = []
    for i in range(21):
        t = i / 20
        r = lerp(.028,.014,t)
        z = -.16*t
        rings.append([V(r*math.cos(math.tau*j/28),r*.84*math.sin(math.tau*j/28),z)*size
                      for j in range(28)])
    _closed_rings(g,rings)
    for row in range(count):
        t = (row+.5)/count
        z = -.16*t
        base = lerp(.028,.014,t)
        for j in range(11):
            angle = math.tau*j/11
            x, y = math.cos(angle), math.sin(angle)
            radial = V(x,.84*y,0)
            root = radial*base + V(0,0,z)
            spine = (.006 + .005*max(0,y))*(1.-.29*t)
            small = (.0065-.0023*t)
            g.loft([v*size for v in (root-radial*.0024+V(0,0,.005),
                                       root+radial*(spine*.52),root+radial*spine+BACK*.009)],
                   [size*r for r in (small,small*.66,.00028)],sides=12,density=2)


def flank_spike_fringe(g, p):
    size, reach = p["size"], p["reach"]
    g.setup(finish="subsurf_low")
    g.loft([V(0,0,z)*size for z in (-.080,-.050,0,.050,.080)],
           [(a*size,b*size) for a,b in ((.003,.002),(.008,.005),(.011,.006),
                                        (.008,.005),(.003,.002))],sides=16,density=3)
    for side, rise, spread in ((1,.004,.009),(-1,.008,.006)):
        for i in range(12):
            t = (i+.45)/12
            z = -.075+.15*t + side*.0017
            length = reach*spread*(.62+.38*math.sin(math.pi*t))
            root = V(side*.0035,.0018,z)
            g.loft([v*size for v in (root, root+V(side*length*.52,rise*.54,-.002),
                                      root+V(side*length,rise,-.0058))],
                   [r*size for r in (.0041,.0028,.00017)],sides=9,density=2)


def passive_lateral_glide_fringe(g, p):
    size, spread = p["size"], p["spread"]
    g.setup(finish="subsurf_low")
    margin = [
        (-.003,.000,-.047),(.002,.001,-.043),(.010,.003,-.038),
        (.021,.003,-.032),(.026,.002,-.019),(.024,.001,-.009),
        (.023,.001,0.),(.029,.000,.014),(.021,-.002,.026),
        (.012,-.001,.034),(.004,.001,.044),(-.003,.001,.047),
        (-.005,0,.016),(-.005,0,-.017),
    ]
    g.leaf([V(x*spread,y-.012*x/.03*(1.-spread),z)*size for x,y,z in margin],
           UP,.0024*size,cup=.42)


def vascular_flank_filaments(g, p):
    size, length = p["size"], p["reach"]
    g.setup(finish="direct")
    g.oval(V(0,0,0),(.031*size,.007*size,.051*size),segs=26,rings=14)
    for row in range(-3,4):
        for column in range(-4,5):
            x = .0063*(column+.45*(row%2))
            z = .0108*row
            rel = (x/.030)**2+(z/.048)**2
            if rel > .80:
                continue
            root = V(x,.0068*math.sqrt(1.-rel),z)
            reach = length*(.0092+.0041*(.5+.5*math.sin(1.7*column+1.9*row)))
            curl = V(.32*x/.03,.46,-.83)
            g.loft([v*size for v in (root-UP*.002, root+curl*(reach*.52)+UP*.0018,
                                     root+curl*reach+BACK*.0022)],
                   [size*r for r in (.0012,.00080,.00014)],sides=8,density=2)


PARTS = [
    Part("spiny_tail_whorls","aesthetics","Backward-pointing scale whorls seated around a tapering tail section.",
         ["agama","armor","tail","spines"],{**SIZE,"rings":(4,10,7)},spiny_tail_whorls,
         orient="native",symmetry="center",discrete=("rings",),hint={"u":.04,"theta":90.}),
    Part("flank_spike_fringe","aesthetics","Offset paired rows of lateral flank fringe scales.",
         ["lizard","fringe","spines","armor"],{**SIZE,"reach":(.54,1.28,1.)},flank_spike_fringe,
         orient="surface",symmetry="pair",hint={"u":.50,"theta":0.}),
    Part("passive_lateral_glide_fringe","locomotion","Shallow compliant skin fringe without projecting rib spars.",
         ["gecko","glide","skin membrane"],{**SIZE,"spread":(.28,1.,.88)},passive_lateral_glide_fringe,
         orient="native",symmetry="pair",hint={"u":.48,"theta":0.}),
    Part("vascular_flank_filaments","aesthetics","Tapered outer skin papillae on a curved local flank patch.",
         ["frog","respiration","flank","filaments"],{**SIZE,"reach":(.55,1.3,1.)},vascular_flank_filaments,
         orient="surface",symmetry="pair",hint={"u":.3,"theta":20.}),
]
TRAITS={"passive_lateral_glide_fringe":{"function":"fly","construction":"deformable"},
        "vascular_flank_filaments":{"function":"breathe","construction":"deformable"}}
