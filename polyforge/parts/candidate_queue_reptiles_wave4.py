"""Expandable cervical hood in a vertical local neck frame."""

import math

from scipy.interpolate import PchipInterpolator

from ..kit import V
from . import Part


_HALF_WIDTH = PchipInterpolator((0., .11, .30, .51, .69, .85, 1.),
                                 (.026,.031,.060,.080,.088,.068,.027))


def cervical_rib_hood(g, p):
    g.setup(finish="direct")
    opening, size = p["spread"], p["size"]
    slices, sides = 40, 40
    sections = [(i/slices,False) for i in range(slices+1)]
    sections += [(1.,True),(0.,True)]
    vertices = []
    for t, interior in sections:
        y = -.125 + .29*t
        thickness = .0205 + .006*math.sin(math.pi*t)
        center = .013*(t-.40)**2
        spread = .024 + opening*(float(_HALF_WIDTH(t))-.024)
        for j in range(sides):
            azimuth = math.tau*j/sides
            c,d = math.cos(azimuth),math.sin(azimuth)
            if interior:
                vertices.append(V(.017*c,y,center+.0148*d)*size)
            else:
                depth = thickness*(.56+.44*(1-c*c))
                curve = -.012*opening*math.sin(math.pi*t)*(abs(c)**2)
                ribs = .0011*opening*(abs(c)**2)*math.sin(math.tau*12*t)
                vertices.append(V(spread*c,y,center + depth*d + curve + ribs*d)*size)
    faces = []
    for i in range(len(sections)):
        n = (i+1)%len(sections)
        for j in range(sides):
            k = (j+1)%sides
            faces.append((i*sides+j,n*sides+j,n*sides+k,i*sides+k))
    volume = sum(vertices[f[0]].dot(vertices[f[j]].cross(vertices[f[j+1]]))
                 for f in faces for j in (1,2))
    if volume < 0:
        faces = [face[::-1] for face in faces]
    g._add(vertices,faces)


PARTS = [
    Part("cervical_rib_hood","aesthetics","One tapered cervical collar with a continuous spread hood.",
         ["snake","hood","rib supported","display"],{"size":(.64,1.5,1.),"spread":(.12,1.,.84)},
         cervical_rib_hood,orient="native",symmetry="center",hint={"u":.84,"theta":90.}),
]
TRAITS={"cervical_rib_hood":{"function":"display","construction":"deformable"}}
