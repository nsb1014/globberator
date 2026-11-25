"""Machine-readable controls shared by the preset description and Blender builder."""
import re

PARTS = {"body":"segmented_arachnid","jaws":"chelicera","limbs":"jointed_appendage"}
SHAPE_LIMITS = {name:(.75,1.25) for name in ("abdomen_length","abdomen_width","jaw_width")}
MOUNT_LIMITS = {"socket_y":(-1.05,.18), "sweep":(-78,65), "reach":(1.4,2.7)}
ID_PATTERN = r"[A-Za-z][A-Za-z0-9]{0,20}"
ROLES = {"foot":"planted walk contact", "feeler":"slender raised sensory leg", "palp":"raised palp with a terminal pad"}


def describe(preset):
    return {"preset":"solifuge", "default_recipe":preset, "shape_ranges":SHAPE_LIMITS,
            "mount_ranges":MOUNT_LIMITS, "roles":ROLES, "mount_id_pattern":ID_PATTERN,
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
    if not mounts or not any(m["role"] == "foot" for m in mounts):
        raise ValueError("The walking rig needs weight-bearing mounts")
    ids = set()
    for m in mounts:
        if not re.fullmatch(ID_PATTERN,m["id"]) or m["id"] in ids:
            raise ValueError("Supply a unique short identifier for each mount")
        ids.add(m["id"])
        if m["role"] not in ROLES or not all(bounded(m[k],*limits) for k,limits in MOUNT_LIMITS.items()):
            raise ValueError(f"Invalid appendage settings for {m['id']}")
