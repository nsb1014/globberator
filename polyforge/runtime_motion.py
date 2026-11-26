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


def manifest(rig):
    names = rig["names"]
    limbs = []
    for limb in rig["limbs"]:
        if limb["length"] <= 0:
            continue
        sole = Vector(limb["sole_local"]) / limb["length"]
        limbs.append({"id": limb["name"], "group": limb["uid"], "role": limb["role"], "side": limb["side"],
                      "body_position": limb["u"], "joints": [names[i] for i in limb["bones"]],
                      "sole_per_length": list(sole)})
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
    return {"version": 1, "axes": "+Y up, +Z forward", "profile": rig.get("gait", "creature"),
            "spine": [names[i] for i in rig["spine"]], "hub": names[rig["spine"][rig["hub"]]],
            "limbs": limbs, "parts": parts, "poses": POSE_RULES}


def save(rig, path):
    with open(path, "w") as file:
        json.dump(manifest(rig), file, indent=2)
        file.write("\n")
