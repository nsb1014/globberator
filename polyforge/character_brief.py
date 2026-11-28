"""Validate the image classification consumed by the deterministic compiler."""
import math
import re


LEGACY_SCHEMA = {
    "type": "object",
    "properties": {
        "body_plan": {"type": "string", "enum": ["humanoid", "unsupported"]},
        "style": {"type": "string", "enum": ["chibi", "cartoon", "standard"]},
        "head_fraction": {"type": "number", "description": "Estimated head height divided by figure height, excluding hair and props"},
        "face": {"type": "string", "enum": ["round", "oval", "square"]},
        "eyes": {"type": "string", "enum": ["round", "angled", "small"]},
        "hair": {"type": "string", "enum": ["bald", "short", "swept", "spiky"]},
        "feet": {"type": "string", "enum": ["bare", "shoes", "boots"]},
    },
    "required": ["body_plan", "style", "head_fraction", "face", "eyes", "hair", "feet"],
    "additionalProperties": False,
}

BODY_PLANS = ("humanoid", "biped", "quadruped", "hexapod", "octopod", "bird",
              "winged", "swimmer", "serpent", "radial", "blob", "unsupported")
MOTION_PROFILES = ("ground", "crawl", "axial_vertical", "axial_lateral", "paddling", "flight")
HOSTS = ("body", "limb", "limb_end", "body_plan")
FUNCTIONS = ("support", "jump", "swim", "fly", "locomotion", "balance", "sense", "feed",
             "breathe", "grasp", "protect", "display", "bulk")
PROPORTIONS = {
    "width": (.06, 1.20, "maximum torso width divided by longitudinal body length"),
    "depth": (.06, 1.20, "maximum cross-section depth divided by longitudinal body length"),
    "head": (.06, .75, "head length divided by longitudinal body length"),
    "taper": (.05, 1.00, "rear cross-section width divided by torso width"),
}
FEATURE_CONTROLS = {
    "u": (0, 1, "landmark along the centerline: rear or hips 0, front or crown 1"),
    "theta": (-180, 180, "angle: 0 side, 90 dorsal, -90 ventral; for upright bodies -90 faces forward"),
    "scale": (.2, 4, "multiplier on the family model, in a two-unit-long core"),
    "offset": (-.6, .6, "surface-normal distance, with negative values seating a part in the skin"),
}

SCHEMA = {
    "type": "object",
    "properties": {
        "version": {"type": "integer", "enum": [2]},
        "subject": {"type": "string"},
        "body_plan": {"type": "string", "enum": list(BODY_PLANS)},
        "locomotion": {"type": "string", "enum": list(MOTION_PROFILES)},
        "proportions": {"type": "object", "properties": {
            key: {"type": "number", "description": desc} for key, (_, _, desc) in PROPORTIONS.items()},
            "required": list(PROPORTIONS), "additionalProperties": False},
        "features": {"type": "array", "items": {
            "type": "object", "properties": {
                "id": {"type": "string", "description": "Unique lowercase name with digits or underscores"},
                "host": {"type": "string", "enum": list(HOSTS)},
                "host_feature": {"type": "string", "description": "Limb feature ID for limb and limb_end hosts, else empty"},
                "function": {"type": "string", "enum": list(FUNCTIONS)},
                "shape": {"type": "string", "description": "Concise visible shape, such as webbed foot, rounded paw, membrane wing or hooked beak"},
                "query": {"type": "string", "description": "Optional alternative plain-language anatomical term or empty"},
                **{key: {"type": "number", "description": desc} for key, (_, _, desc) in FEATURE_CONTROLS.items()},
                "rot": {"type": "array", "items": {"type": "number"}, "description": "Optional three local rotation angles in degrees"},
            },
            "required": ["id", "host", "function", "shape"],
            "additionalProperties": False,
        }},
        "uncertainties": {"type": "array", "items": {"type": "string"}, "description": "Anatomy hidden or ambiguous from the image"},
    },
    "required": ["version", "subject", "body_plan", "locomotion", "proportions", "features", "uncertainties"],
    "additionalProperties": False,
}


def _finite(value, low, high):
    return type(value) in (int, float) and low <= value <= high


def _validate_legacy(brief):
    if not isinstance(brief, dict) or brief.keys() != LEGACY_SCHEMA["properties"].keys():
        raise ValueError("legacy character brief must contain exactly: " + ", ".join(LEGACY_SCHEMA["required"]))
    for key, field in LEGACY_SCHEMA["properties"].items():
        if "enum" in field and brief[key] not in field["enum"]:
            raise ValueError(f"unsupported {key}: {brief[key]!r}")
    ratio = brief["head_fraction"]
    if type(ratio) not in (float, int) or not math.isfinite(ratio) or not 0 < ratio < 1:
        raise ValueError("head_fraction must be a finite fraction between 0 and 1")
    if brief["body_plan"] != "humanoid":
        raise ValueError("legacy character briefs support upright humanoids")
    return brief


def validate(brief):
    if not isinstance(brief, dict) or "version" not in brief:
        return _validate_legacy(brief)
    if brief.keys() != SCHEMA["properties"].keys() or type(brief["version"]) is not int or brief["version"] != 2:
        raise ValueError("version 2 character brief must contain exactly: " + ", ".join(SCHEMA["required"]))
    if brief["body_plan"] not in BODY_PLANS or brief["body_plan"] == "unsupported":
        raise ValueError(f"unsupported body plan: {brief['body_plan']!r}")
    if brief["locomotion"] not in MOTION_PROFILES:
        raise ValueError(f"unknown locomotion profile: {brief['locomotion']!r}")
    if not isinstance(brief["subject"], str) or not brief["subject"].strip():
        raise ValueError("subject must name the classified figure")
    dimensions = brief["proportions"]
    if not isinstance(dimensions, dict) or dimensions.keys() != PROPORTIONS.keys():
        raise ValueError("proportions must contain exactly: " + ", ".join(PROPORTIONS))
    for key, (lo, hi, _) in PROPORTIONS.items():
        if not _finite(dimensions[key], lo, hi):
            raise ValueError(f"proportions.{key} must be between {lo} and {hi}")

    features = brief["features"]
    if not isinstance(features, list) or len(features) > 60:
        raise ValueError("features must be a list of up to 60 anatomical features")
    fields = SCHEMA["properties"]["features"]["items"]
    ids = set()
    for item in features:
        if not isinstance(item, dict) or not set(fields["required"]) <= item.keys() <= fields["properties"].keys():
            raise ValueError("invalid character feature fields")
        uid = item["id"]
        if not isinstance(uid, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,47}", uid) or uid in ids:
            raise ValueError(f"feature ID must be unique lowercase letters, digits or underscores: {uid!r}")
        ids.add(uid)
        if item["host"] not in HOSTS or item["function"] not in FUNCTIONS:
            raise ValueError(f"{uid}: unknown host or function")
        if not isinstance(item["shape"], str) or not item["shape"].strip():
            raise ValueError(f"{uid}: shape must describe a visible form")
        for key in ("query", "host_feature"):
            if key in item and not isinstance(item[key], str):
                raise ValueError(f"{uid}: {key} must be text")
        for key, (lo, hi, _) in FEATURE_CONTROLS.items():
            if key in item and not _finite(item[key], lo, hi):
                raise ValueError(f"{uid}: {key} must be between {lo} and {hi}")
        if "rot" in item and (not isinstance(item["rot"], list) or len(item["rot"]) != 3
                              or not all(_finite(value, -360, 360) for value in item["rot"])):
            raise ValueError(f"{uid}: rot must contain three angles between -360 and 360")
    for item in features:
        host = item.get("host_feature")
        if item["host"] in ("limb", "limb_end"):
            if host not in ids or host == item["id"]:
                raise ValueError(f"{item['id']}: host_feature must name a different feature")
        elif host:
            raise ValueError(f"{item['id']}: host_feature is only available for limb attachments")
    notes = brief["uncertainties"]
    if not isinstance(notes, list) or not all(isinstance(note, str) for note in notes):
        raise ValueError("uncertainties must be a list of observations")
    return brief
