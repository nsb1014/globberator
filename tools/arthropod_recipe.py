"""Machine-readable controls shared by the preset description and Blender builder."""
import re

PARTS = {"body":"segmented_arachnid","jaws":"chelicera","limbs":"jointed_appendage"}
SHAPE_LIMITS = {name:(.75,1.25) for name in ("abdomen_length","abdomen_width","jaw_width")}
MOUNT_LIMITS = {"socket_y":(-1.05,.18), "sweep":(-78,65), "reach":(1.4,2.7)}
ID_PATTERN = r"[A-Za-z][A-Za-z0-9]{0,20}"
ROLES = {"foot":"planted walk contact", "feeler":"slender raised sensory leg", "palp":"raised palp with a terminal pad"}


def describe(preset):
    return {"preset":"solifuge", "default_recipe":preset, "shape_ranges":SHAPE_LIMITS,
            "mount_ranges":MOUNT_LIMITS, "leg_count_range":[0,8], "roles":ROLES, "mount_id_pattern":ID_PATTERN,
            "coordinates":"Blender +Z up, -Y forward. Sweep is in degrees from the outward lateral axis."}


def validate(recipe):
    if recipe["version"] != 1 or recipe["rest_pose"] != "neutral":
        raise ValueError("Expected a version 1 neutral recipe")
    if recipe["parts"] != PARTS:
        raise ValueError("Unknown arachnid part")
    def bounded(value, low, high):
        return type(value) in (int,float) and low <= value <= high
    shape = recipe["shape"]
    if set(shape) != set(SHAPE_LIMITS) or not all(
            bounded(value,*SHAPE_LIMITS[key]) for key,value in shape.items()):
        raise ValueError("Shape controls must be between 0.75 and 1.25")
    mounts = recipe["mounts"]
    if not isinstance(mounts,list):
        raise ValueError("Expected a list of mounts")
    legs = sum((1 if m.get("center") else 2) for m in mounts if m["role"] == "foot")
    if legs > 8:
        raise ValueError("At most eight walking legs are supported")
    ids = set()
    for m in mounts:
        if not re.fullmatch(ID_PATTERN,m["id"]) or m["id"] in ids:
            raise ValueError("Supply a unique short identifier for each mount")
        ids.add(m["id"])
        if "center" in m and (type(m["center"]) != bool or (m["center"] and m["role"] != "foot")):
            raise ValueError("A center mount must be a walking leg")
        if m["role"] not in ROLES or not all(bounded(m[k],*limits) for k,limits in MOUNT_LIMITS.items()):
            raise ValueError(f"Invalid appendage settings for {m['id']}")

def configure_legs(recipe,count):
    """Select walking sockets for a count study; glide and hop expose the body support."""
    if type(count) is not int or not 0 <= count <= 8:
        raise ValueError("Walking leg count must be an integer from zero to eight")
    feet = [m for m in recipe["mounts"] if m["role"] == "foot" and not m.get("center")]
    pairs = count//2
    if len(feet) < pairs:
        raise ValueError("The preset needs more paired sockets")
    if pairs == 1:
        selected = [feet[len(feet)//2]]
    else:
        selected = [feet[round(i*(len(feet)-1)/(pairs-1))] for i in range(pairs)]
    mounts = [m for m in recipe["mounts"] if m["role"] != "foot" or m in selected]
    if count < 2:
        mounts = []
    if count%2:
        mounts.append({"id":"Midleg","role":"foot","center":True,"socket_y":-.05,"reach":1.55,"sweep":0})
    recipe["mounts"] = mounts
