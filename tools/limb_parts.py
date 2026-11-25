"""Socket-local geometry and rig for one ungulate limb, authored on the animal's left."""
from mathutils import Vector


SEGMENTS = ("Upper", "Lower", "Cannon", "Pastern", "Foot")


def ungulate_leg(profile, fullness=0.0):
    """Return the joint chain and cross sections of one leg in its mount frame."""
    if not 0 <= fullness <= 1:
        raise ValueError("Leg fullness must be between 0 and 1")
    if profile == "fore":
        offsets = [(0,0,0),(.0132,.26,-.55),(.0232,-.05,-1.19),
                   (.0282,.04,-1.74),(.0332,-.06,-1.865)]
        cap = Vector((-.0968,.26,.63))
        radii = [(.14,.20),(.27,.37),(.29,.37),(.23,.28),(.18,.23),(.16,.20)]
    elif profile == "hind":
        offsets = [(0,0,0),(.05,-.32,-.67),(.07,.27,-1.42),
                   (.075,.15,-1.93),(.08,.05,-2.055)]
        cap = Vector((-.06,.06,.44))
        radii = [(.14,.20),(.31,.42),(.33,.45),(.29,.36),(.235,.27),(.18,.22)]
    else:
        raise ValueError(f"Unknown ungulate leg profile {profile!r}")
    joints = [Vector(point) for point in offsets]
    start,hinge,knee,fetlock,foot = joints
    centers = [cap,cap.lerp(start,.52),start,start.lerp(hinge,.50),hinge,
               hinge.lerp(knee,.38),knee,knee.lerp(fetlock,.43),fetlock,foot,
               foot+Vector((0,-.032,-.068))]
    radii += [(.125,.135),(.090,.10),(.105,.122),(.127,.142),(.128,.133)]
    if fullness:
        # Give the upper leg a broad sweep and a distinct waist above the lower swell.
        # These stations are interpolated in the same part for both attachments.
        centers[7:8] = [knee.lerp(fetlock,t) for t in (.15,.48,.76)]
        radii[7:8] = [(.115,.124),(.090,.100),(.094,.108)]
        extra = [(0,0),(.039,.040),(.072,.073),(.091,.079),(.118,.104),(.115,.095),
                 (.049,.047),(.014,.016),(.079,.065),(.043,.034),(.016,.012),(.004,.004),(0,0)]
        radii = [(w+fullness*dw,d+fullness*dd) for (w,d),(dw,dd) in zip(radii,extra,strict=True)]
    rings = [(*point,w,d) for point,(w,d) in zip(centers,radii,strict=True)]
    return joints,rings


CATALOG = {"ungulate_leg": ungulate_leg}
