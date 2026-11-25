"""Solve a two-link limb to a target while preserving its rest bending plane."""
import math


def aim_leg(hip,knee,ankle,posed_hip,target):
    axis = target-posed_hip
    reach = axis.length
    upper,lower = knee-hip,ankle-knee
    if reach < 1e-7 or reach > upper.length+lower.length+1e-5 or reach < abs(upper.length-lower.length)-1e-5:
        raise ValueError("Foot target exceeds limb reach")
    axis.normalize()
    along = (upper.length_squared-lower.length_squared+reach*reach)/(2*reach)
    pole = (upper-axis*upper.dot(axis)).normalized()
    bend = posed_hip+axis*along+pole*math.sqrt(max(0.,upper.length_squared-along*along))
    return upper.rotation_difference(bend-posed_hip),lower.rotation_difference(target-bend)
