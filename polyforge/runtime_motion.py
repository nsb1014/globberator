"""Export role bindings and dimensionless pose rules for the game controller."""
import json

from mathutils import Matrix, Vector


POSE_RULES = {
    "walk": {"ground_relative": True, "period": .92, "duty": .62, "stride": .56,
             "lift": [[0, 0], [.25, .065], [.5, .11], [.75, .065], [1, 0]], "arm_sweep": .18},
    "run": {"ground_relative": True, "period": .64, "duty": .43, "stride": .78,
            "lift": [[0, 0], [.25, .1], [.5, .17], [.75, .1], [1, 0]], "arm_sweep": .28},
    "reach": {"space": "world", "fallback_local": [.3, 0, .52], "transition_seconds": .20},
    "secondary": {"spring": 26.0, "damping": 8.0, "drag": .035, "max_deflection": .24},
}

HOOFED_WALK = {**POSE_RULES["walk"], "period": 2.0, "duty": .69, "stride": .82,
               "lift": [[0, 0, 0], [.24, .13, .24], [.43, .16, 0], [.72, .095, -.30], [1, 0, 0]],
               "pelvis_dip": .032, "pelvis_dip_delay": .045, "knee_reserve": .30,
               "arm_sweep": .105, "arm_clearance": .09, "arm_flex": .035}


def sample_lift(keys, phase):
    for a, b in zip(keys, keys[1:]):
        if phase <= b[0]:
            width = b[0] - a[0]
            t = (phase - a[0]) / width
            blend = t * t * (3 - 2 * t)
            return (a[1] + (b[1] - a[1]) * blend
                    + width * t * (1 - t) * ((1 - t) * a[2] - t * b[2]))
    return keys[-1][1]


def manifest(rig):
    names = rig["names"]
    limbs = []
    for limb in rig["limbs"]:
        if limb["length"] <= 0:
            continue
        sole = Vector(limb["sole_local"]) / limb["length"]
        binding = {"id": limb["name"], "group": limb["uid"], "role": limb["role"], "side": limb["side"],
                   "body_position": limb["u"], "joints": [names[i] for i in limb["bones"]],
                   "sole_per_length": list(sole)}
        if limb["role"] == "leg" and "toe_local" in limb:
            binding["hoofed"] = True
            binding["toe_per_length"] = list(Vector(limb["toe_local"]) / limb["length"])
        if limb.get("joint_support"):
            binding["joint_support"] = [names[i] for i in limb["joint_support"]]
        limbs.append(binding)
    parts = []
    for part in rig["parts"]:
        role = part["cap"] or ("look" if part["part"] == "eye_camera" else "")
        if not role and not part["jaws"]:
            continue
        frame = Matrix(part["frame"])
        sign = -1 if frame.determinant() < 0 else 1
        hinges = [{"joint": names[h["bone"]], "axis": list((frame @ Vector(h["axis"])) * sign),
                   "degrees": h["angle"]} for h in part["jaws"]]
        parts.append({"id": part["uid"], "role": role, "joint": names[part["bone"]], "hinges": hinges})
    legs = [limb for limb in limbs if limb["role"] == "leg"]
    hoofed_biped = len(legs) == 2 and all(limb.get("hoofed") for limb in legs)
    poses = {**POSE_RULES, "walk": HOOFED_WALK} if hoofed_biped else POSE_RULES
    return {"version": 1, "axes": "+Y up, +Z forward", "profile": rig.get("gait", "creature"),
            "spine": [names[i] for i in rig["spine"]], "hub": names[rig["spine"][rig["hub"]]],
            "limbs": limbs, "parts": parts, "poses": poses}


def save(rig, path):
    with open(path, "w") as file:
        json.dump(manifest(rig), file, indent=2)
        file.write("\n")
