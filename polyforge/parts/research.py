"""Turns the audited research spec and its model implementations into parts."""
import json
from pathlib import Path

from . import Part

PREVIEW_ANGLES = {
    "leg_arthropod": (58, 12), "leg_digitigrade": (70, 12), "leg_plantigrade": (53, 12),
    "leg_sprawling": (55, 16), "leg_jumping": (70, 16), "leg_bird": (60, 12),
    "paw_padded": (12, -62), "foot_grasping": (-30, 38), "foot_webbed_long": (-30, 63),
    "foot_hoof": (32, 12), "hand_basic": (18, 14),
    "wing_feathered": (146, 73), "elytron": (8, 60), "wing_membrane_insect": (110, 67),
    "fin_paired": (42, 50), "fin_median": (90, 6), "tail_fin_heterocercal": (90, 8),
    "tail_feather_fan": (140, 62), "tail_flexible": (80, 12), "siphon": (-65, 25),
    "web_interbrachial": (17, 58), "bell_radial": (20, 28), "suckers": (40, 62),
    "gill_slits": (76, 14), "stinger": (88, 12), "tail_segmented": (80, 18),
}


def load_parts(modules):
    installed = Path(__file__).resolve().parents[1] / "_data" / "research"
    source = Path(__file__).resolve().parents[2] / "research"
    with ((installed if installed.is_dir() else source) / "part_library.json").open() as file:
        spec = json.load(file)
    builders = {name: fn for module in modules for name, fn in module.BUILDERS.items()}
    presets = {name: fn for module in modules for name, fn in getattr(module, "PRESETS", {}).items()}
    overrides = {name: data for module in modules for name, data in getattr(module, "OVERRIDES", {}).items()}
    extra_params = {name: data for module in modules for name, data in getattr(module, "EXTRA_PARAMS", {}).items()}
    expected = {entry["id"] for entry in spec["parts"]}
    if set(builders) != expected:
        raise ValueError(f"Research models missing {expected - builders.keys()}, unexpected {builders.keys() - expected}")

    parts = []
    for entry in spec["parts"]:
        name, kind, category = entry["id"], entry["kind"], entry["category"]
        _, y, z = entry["attach_pos_normalized"]
        position = {"u": max(.03, min(.97, z + .5)), "theta": 30.0 if y >= .5 else -35.0}
        if entry["symmetry"] in ("centre", "radial"):
            position["theta"] = 90.0 if y >= .5 else -90.0
        if kind == "limb" and name not in presets:
            raise ValueError(f"No rig chain defined for {name}")
        params = {"size": (.4, 3.0, 1.0)}
        params.update({key: tuple(item[field] for field in ("min", "max", "default"))
                       for key, item in entry["params"]["shape"].items()})
        params.update(extra_params.get(name, {}))
        discrete = {key for key, (lo, hi, default) in params.items()
                    if all(type(v) is int for v in (lo, hi, default))}
        options = {
            "attach": kind, "hint": position, "host": entry["attach_to"],
            "symmetry": entry["symmetry"], "preset": presets.get(name),
            "orient": "forward" if category in ("sensory", "feeding") else "native",
            "cap": "foot" if name.startswith("leg_") else "",
            "discrete": discrete,
        }
        if name in ("pectines", "tail_fin_heterocercal"):
            options["orient"] = "native"
        options.update(overrides.get(name, {}))
        parts.append(Part(name, category, entry["description"], entry["species"], params, builders[name], **options))
    return parts
