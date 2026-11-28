"""The ray-bearing variant of the continuous axial fin envelope."""

from math import atan2, cos, pi, tau

from scipy.interpolate import PchipInterpolator

from ..kit import smoothstep
from . import Part
from .candidate_aquatic import _axial_fin_envelope


_EEL_LENGTH = .126
_EEL_PROFILE = PchipInterpolator((0., .10, .24, .40, .56, .69, .80, .89, .95, 1.), (
    (.0190, .0340, -.0270), (.0178, .0320, -.0268), (.0159, .0275, -.0258),
    (.0133, .0258, -.0240), (.0108, .0234, -.0228), (.0084, .0211, -.0212),
    (.0060, .0160, -.0172), (.0038, .0104, -.0120), (.0022, .0064, -.0072),
    (.0007, .0019, -.0021),
))


def joined_terminal_median_fin_rim(g, p):
    """A laterally flexing axial membrane with dorsal, tip and ventral rays."""
    scale, bend, ray_relief = p["size"], p["bend"], p["ray_relief"]
    g.setup(finish="direct")
    sections = 129
    stations = [(.004 - _EEL_LENGTH * t, *_EEL_PROFILE(t))
                for t in (i / (sections - 1) for i in range(sections))]

    def relief(z, y):
        t = (.004 - z) / _EEL_LENGTH
        outer = smoothstep(.48, .85, abs(y))
        sweep = t - .125 * abs(y)
        strip = (.5 + .5 * cos(tau * 23 * sweep))**3
        # Terminal rays fan caudally from the last supports in the continuous rim.
        ray_angle = atan2(.022 * y * (1 - t)**.65, max(.001, .126 * (t - .81)))
        fan = (.5 + .5 * cos(16 * ray_angle + pi))**3
        turn = smoothstep(.73, .91, t)
        return .00135 * ray_relief * smoothstep(.02, .10, t) * (1 - smoothstep(.96, 1., t)) * (
            outer * (1 - turn) * strip + turn * fan)

    _axial_fin_envelope(g, stations, scale, bend, _EEL_LENGTH, relief=relief, sides=44)


PARTS = [
    Part("joined_terminal_median_fin_rim", "locomotion",
         "Continuous eel tail fin with dorsal and ventral rays sweeping into a terminal fan.",
         ["eel", "tail", "axial", "continuous", "median fin", "rayed"],
         {"size": (.6, 1.6, 1.), "bend": (-.72, .72, 0.), "ray_relief": (0., 1., .85)},
         joined_terminal_median_fin_rim, orient="native", symmetry="center",
         hint={"u": .08, "theta": 0.}),
]


TRAITS = {
    "joined_terminal_median_fin_rim": {
        "function": "swim",
        "shape": "continuous rayed axial membrane",
        "construction": "deformable",
    },
}
