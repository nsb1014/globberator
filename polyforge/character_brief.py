"""The image model classifies a character. Blender owns the geometry and rig."""
import math


SCHEMA = {
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


def validate(brief):
    if not isinstance(brief, dict) or brief.keys() != SCHEMA["properties"].keys():
        raise ValueError("character brief must contain exactly: " + ", ".join(SCHEMA["required"]))
    for key, field in SCHEMA["properties"].items():
        if "enum" in field and brief[key] not in field["enum"]:
            raise ValueError(f"unsupported {key}: {brief[key]!r}")
    ratio = brief["head_fraction"]
    if type(ratio) not in (float, int) or not math.isfinite(ratio) or not 0 < ratio < 1:
        raise ValueError("head_fraction must be a finite fraction between 0 and 1")
    if brief["body_plan"] != "humanoid":
        raise ValueError("one-shot character generation currently supports upright humanoids")
    return brief
