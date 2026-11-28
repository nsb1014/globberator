"""Isolated marsupial, rhinoceros and emu external morphology drafts."""

import math

from ..kit import V, lerp
from . import Part
from .research_locomotion import _closed_rings


def ventral_pouch_opening(g, p):
    """Continuous abdominal surface, tract lip and recessed pouch wall."""
    size, opening = p["size"], p["opening"]
    aperture = .019 + .024 * opening
    stations = (
        (.015, .019, .026, 0.), (.015, .065, .092, 0.), (.007, .080, .107, 0.),
        (-.006, .079, .105, 0.), (-.015, .068, .090, .002),
        (-.027, aperture + .020, .068, .002),
        (-.044, aperture + .006, .059, .004),
        (-.046, aperture, .057, .004),
        (-.040, aperture - .004, .054, .005),
        (-.029, aperture + .001, .057, .006),
        (-.017, aperture + .011, .065, .010),
        (-.009, aperture + .004, .058, .010),
        (-.005, aperture * .71, .039, .008), (-.004, .011, .015, .008),
    )
    rings = []
    for index, (y, width, length, shift) in enumerate(stations):
        ring = []
        rim = max(0., 1. - abs(index - 7) * .23)
        for j in range(36):
            angle = math.tau * j / 36
            x, z = math.cos(angle), math.sin(angle)
            lip_roll = rim * (.006 * abs(x) - .003 * z)
            x_lateral = width * x * (1 - .18 * z * z)
            ring.append(V(x_lateral, y + lip_roll, shift + length * z) * size)
        rings.append(ring)
    g.setup(finish="subsurf_low")
    g.slot("skin")
    _closed_rings(g, rings)


def ventral_tail_contact_strip(g, p):
    """Tapered tail with a continuous flattened contact arc along the distal underside."""
    size, coil = p["size"], p["coil"]
    rings = []
    center = V(0., 0., .014)
    count = 40
    step = .346 / count
    for index in range(count + 1):
        t = index / count
        angle = .09 + .19 * t + 5.12 * coil * t ** 2.21
        inward = V(0., -math.cos(angle), math.sin(angle))
        radius = lerp(.0153, .0021, t ** .87)
        reveal = min(1., max(0., (t - .46) / .16))
        ring = []
        for j in range(36):
            theta = math.tau * j / 36
            x, q = math.cos(theta), math.sin(theta)
            # The contact arc flattens to a continuous strip inside the coil.
            pad = max(0., (q - .70) / .30)
            contact = q - .13 * reveal * pad * pad
            shoulder = .06 * reveal * math.exp(-((q - .78) / .070) ** 2)
            offset = V(x * radius * (1. + shoulder), 0., 0.)
            ring.append((center + offset + inward * (contact * radius)) * size)
        rings.append(ring)
        midpoint = t + .5 / count
        turn = .09 + .19 * midpoint + 5.12 * coil * midpoint ** 2.21
        center += step * V(0., -math.sin(turn), -math.cos(turn))
    g.setup(finish="subsurf_low")
    g.slot("skin")
    _closed_rings(g, rings)


def limb_girdle_skin_fold(g, p):
    """One local shoulder skin patch with an overhanging lip and deep adjacent crease."""
    size, stride = p["size"], p["stride"]
    rings = []
    profile = (
        (-.155, -.022), (-.139, -.007), (-.080, .012), (-.047, .030),
        (-.025, .058), (.003, .082), (.022, .082), (.031, .061),
        (.034, .031), (.013, .016), (.010, .005), (.032, -.004),
        (.057, .007), (.089, .013), (.140, .003), (.164, -.016),
        (.159, -.031), (.075, -.040), (-.026, -.040), (-.128, -.037),
    )
    for y, width, strength, curve in ((-.330, .45, .23, .040), (-.280, .66, .52, .022),
                                   (-.203, .89, .77, .001), (-.10, .99, 1., -.021),
                                   (.015, 1., 1.04, -.013), (.125, .94, .91, .013),
                                   (.240, .80, .70, .053), (.337, .55, .46, .091),
                                   (.391, .35, .22, .095)):
        excursion = stride * .13 * max(0., -y + .05)
        ring = [V(x * strength + .031 * math.cos(y * 3.6) + max(0., .03 - z) * excursion,
                  y, z * width + curve + excursion) * size for z, x in profile]
        rings.append(ring)
    g.setup(finish="subsurf_low")
    g.slot("skin")
    _closed_rings(g, rings)


def _emu_axis(t, side, height, split):
    return V(side * (split * t + .006 * t * t),
             (.0045 if side < 0 else .010) * math.sin(math.pi * t) + .003 * t,
             .008 + height * t)


def paired_shaft_contour_feather(g, p):
    """Emu contour feather, with two vane-bearing shafts from the same calamus."""
    size, split = p["size"], p["separation"] * .019
    g.setup(finish="subsurf_low")
    g.slot("calamus")
    g.loft([V(0., y, z) * size for y, z in ((-.002, -.013), (0., -.004), (0., .007), (0., .012))],
           [r * size for r in (.00145, .00212, .00200, .00166)], sides=11, density=2)
    for side, height in ((-1, .091), (1, .104)):
        g.slot("rachis")
        axis = [_emu_axis(i / 10, side, height, split) * size for i in range(11)]
        g.loft(axis, [lerp(.00155, .00027, i / 10) * size for i in range(11)],
               sides=10, density=1)
        g.slot("barbs")
        for j in range(18):
            t = .13 + .81 * j / 17
            start = _emu_axis(t, side, height, split)
            envelope = math.sin(math.pi * (t - .03)) ** .72
            for sign in (-1, 1):
                reach = .016 * envelope * (1 + .12 * sign * side)
                sweep = .0070 + .0036 * (1 - t)
                mid = start + V(sign * reach * .57, .0008 * sign, sweep * .36)
                tip = start + V(sign * reach, .0006 - .0016 * t, sweep)
                g.loft([v * size for v in (start, mid, tip)],
                       [r * size for r in (.00049, .00035, .00011)], sides=8, density=1)


PARTS = [
    Part("ventral_pouch_opening", "aesthetics", "Draft abdominal pouch lip and recessed cavity.",
         ["marsupial", "pouch", "marsupium", "abdomen"], {"size": (.45, 2., 1.), "opening": (0., 1., .70)},
         ventral_pouch_opening, orient="native", host="body", symmetry="center", hint={"u": .34, "theta": -90.}),
    Part("ventral_tail_contact_strip", "locomotion", "Draft tapered prehensile tail with a continuous ventral contact band.",
         ["possum", "tail", "climb", "grip", "prehensile"], {"size": (.45, 2., 1.), "coil": (0., 1., .84)},
         ventral_tail_contact_strip, orient="native", host="body", symmetry="center", hint={"u": .08, "theta": 90.}),
    Part("limb_girdle_skin_fold", "aesthetics", "Draft shoulder skin patch with a sculpted overhang and flex crease.",
         ["rhinoceros", "skin", "fold", "girdle", "shoulder"], {"size": (.45, 2., 1.), "stride": (-1., 1., .0)},
         limb_girdle_skin_fold, orient="native", host="body", symmetry="pair", hint={"u": .70, "theta": 0.}),
    Part("paired_shaft_contour_feather", "aesthetics", "Draft double-shaft feather with loose individual vane barbs.",
         ["emu", "feather", "aftershaft", "rachis", "contour"], {"size": (.45, 2., 1.), "separation": (.3, 1., .80)},
         paired_shaft_contour_feather, orient="native", host="body", symmetry="center"),
]
