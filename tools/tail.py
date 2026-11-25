"""One tufted tail, shared by both body families and mounted by its root."""
import math

from mathutils import Quaternion, Vector

PROFILE = [(0,.34,2.10,.09,.093), (.10,.54,1.96,.086,.08), (.22,.71,1.69,.068,.068),
           (.41,.83,1.42,.056,.058), (.64,.83,1.22,.05,.05), (.79,.77,1.08,.042,.045)]
ROOT = Vector(PROFILE[0][:3])
SEGMENTS = ("Tail", "TailMid", "TailTip")
JOINTS = [Vector(PROFILE[i][:3]) for i in (0, 2, 4)] + [Vector((.834,.698,.788))]


def build(tube):
    ring_size = 22
    shaft = tube("Tail", PROFILE, "Tail{suffix}", sides=ring_size)
    # Each tube ring spans one path station. Interpolate skin influence through
    # the joint between consecutive segments; the tuft travels with the tip.
    groups = [shaft.vertex_groups.new(name=name+"{suffix}") for name in SEGMENTS]
    rings = len(shaft.data.vertices) // ring_size
    for ring in range(rings):
        station = ring * (len(PROFILE)-1) / (rings-1)
        influence = min(2., max(0., (station-1.)/2.))
        lower = int(influence)
        blend = influence-lower
        vertices = list(range(ring*ring_size, (ring+1)*ring_size))
        groups[lower].add(vertices, 1-blend, "REPLACE")
        if blend:
            groups[lower+1].add(vertices, blend, "REPLACE")
    for x,y,z,d in [(.79,.77,1.108,.107),(.81,.79,1.12,.073),(.76,.742,1.10,.066)]:
        tube("Tail tuft",[(x,y,z,.05,.048),(x+.066,y,z-.125,d,d*.74),
                          (x+.074,y-.035,z-.219,d*.75,d*.55),(x+.044,y-.072,z-.32,.005,.006)],"TailTip{suffix}")


def bone_name(name, side):
    return name if side == "C" else f"{name}.{side}"


def pose(placements, phase, walking):
    rotations = {}
    amplitude = .19 if walking else .08
    for side, mount in placements:
        # Reflection changes the sign of yaw, while preserving pitch.
        handedness = -1 if mount.to_3x3().determinant() < 0 else 1
        for i, name in enumerate(SEGMENTS):
            lag = phase - .48*i
            yaw = handedness * amplitude * (1 + .45*i) * math.sin(lag)
            pitch = .32 * amplitude * math.cos(lag)
            rotations[bone_name(name, side)] = (Quaternion((0,0,1), yaw)
                                                @ Quaternion((1,0,0), pitch))
    return rotations
