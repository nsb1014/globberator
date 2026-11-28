"""Distal bill flexure on a probing shorebird's narrow, opposed bill."""

import math

from ..kit import V, smoothstep
from . import Part
from .research_locomotion import _closed_rings


STATIONS = (
    (0., .0084, .0076), (.10, .0064, .0056), (.28, .0048, .0043),
    (.53, .0032, .0031), (.69, .0027, .0025), (.81, .0025, .0021),
    (.90, .0030, .00245), (.97, .0021, .00185), (1., .00065, .00065),
)


def distal_bill_flexure(g, p):
    g.setup(finish="subsurf_low")
    for upper in (True, False):
        rings = []
        for t, width, depth in STATIONS:
            distal = smoothstep(.60, 1., t)
            flex = .019 * p["flex"] * distal if upper else 0.
            gape = .024 * p["gape"] * t if not upper else 0.
            direction = 1. if upper else -1.
            curvature = -.011 * t + flex - gape
            ring = []
            for j in range(16):
                theta = math.tau * j / 16
                s = math.sin(theta)
                height = depth * (s if s > 0 else .14 * s)
                ring.append(V(width * math.cos(theta), curvature + direction * (.0011 + height),
                              .119 * t) * p["size"])
            rings.append(ring if upper else list(reversed(ring)))
        _closed_rings(g, rings)


PARTS = [
    Part("distal_bill_flexure", "feeding", "Slender probing bill with independent upper-tip flex and lower-jaw gape.",
         ["snipe", "shorebird", "rhynchokinesis", "probe bill"],
         {"size": (.7, 1.45, 1.), "flex": (0., 1., .53), "gape": (0., 1., .59)},
         distal_bill_flexure, orient="native", symmetry="center", hint={"u": .96, "theta": 0.}),
]
TRAITS = {"distal_bill_flexure": {"function": "feed", "construction": "deformable"}}
