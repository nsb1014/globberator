"""Claude calls for the image -> recipe workflow.

Two calls, both with structured outputs so the reply is always parseable:
  draft()    reference image + part catalog -> feature analysis + first recipe
  critique() reference + renders of the current recipe -> per-feature scores + edit ops
"""
import base64
import io
import json
import os

import anthropic
from PIL import Image

MODEL = os.environ.get("POLYFORGE_MODEL", "claude-opus-5-5")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_client = None


def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def image_block(path, max_side=1024):
    im = Image.open(path).convert("RGB")
    s = max_side / max(im.size)
    if s < 1:
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.standard_b64encode(buf.getvalue()).decode()}}


RECIPE_GUIDE = """\
# PolyForge recipe format (JSON)
Coordinates: +Y up, +Z is the creature's forward (head direction), +X its left/right side. Units ~ meters.
The builder places feet on the ground automatically.
- "spine": 2-16 vertebrae ordered REAR (tail tip) to FRONT (head). Each {"y","z","w","h"}: the vertebra
  sits at x=0, height y, forward position z, with cross-section half-width w and half-height h.
  The body is a smooth tube through them with rounded end caps. The last vertebrae form the neck and head;
  a thin tapering run of rear vertebrae makes a tail. A vertical run of vertebrae makes an upright biped torso.
- Surface coordinates: u in [0,1] runs along the body from the rear tip (0) to the front tip (1);
  theta (degrees) goes around the cross-section: 0 = +X side, 90 = top/back, -90 = belly, 180 = -X side.
  For an upright spine, theta 90 faces backward and -90 faces forward.
- "limbs": [{"uid","u","theta","segments":[[dx,dy,dz],...],"radii":[...],"tip": part id or "","tip_params":{},"mirror":true}]
  segments are joint-to-joint offsets starting at the attachment (1-5 segments); radii has segments+1 entries.
  A limb with a foot tip becomes a walking leg (it must reach the ground), a hand/pincer tip makes an arm,
  no tip makes a free appendage. mirror=true duplicates it on the other side (author the +X side).
- "parts": [{"uid","part","on":"body" or limb uid,"u","theta","offset","rot":[x,y,z] deg,"scale","params":{},"mirror":bool}]
  Eyes/mouths/noses sit on the head cap (u 0.9-1.0). Tail tips go at u near 0. Horns/ears around u 0.85-0.95.
- "paint": {"base","accent","detail": "#rrggbb", "pattern": none|stripes|spots|patches|gradient, "pattern_scale", "belly": bool}
  base = main skin, accent = pattern/horn-ish secondary areas (also fins, plates, shells), detail = belly, muzzle, inner ears.
Values outside allowed ranges are clamped (that is the style tolerance): the library's look wins over exact likeness.
"""


def _system(catalog, examples):
    parts = []
    for p in catalog["parts"]:
        parts.append({"id": p["id"], "category": p["category"], "attach": p["attach"], "desc": p["desc"],
                      "params": {k: [v["min"], v["max"], v["default"]] for k, v in p["params"].items()},
                      "hint": p["hint"], "mirror_default": p["mirror_default"]})
    return (
        "You build stylized low-poly 3D creatures for PolyForge, a Spore-like creature builder, by writing recipes.\n"
        "Your goal is recognizability within the part library's style: match silhouette, proportions, the most "
        "distinctive features and the main colors. Exact detail is not expected.\n\n"
        + RECIPE_GUIDE
        + "\n# Part library\n" + json.dumps(parts, separators=(",", ":"))
        + "\n\n# Recipe ops (for edits)\n" + json.dumps(catalog.get("ops", {}), separators=(",", ":"))
        + "\n\n# Example recipes\n" + "\n".join(json.dumps(e, separators=(",", ":")) for e in examples)
    )


DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "body_plan": {"type": "string", "enum": ["biped", "quadruped", "hexapod", "octopod", "serpent", "bird", "blob", "other"]},
        "view_yaw": {"type": "number", "description": "camera yaw in degrees: 0 = facing the creature's face, 90 = its +X side, -90 its -X side, 180 = from behind"},
        "view_pitch": {"type": "number", "description": "camera elevation in degrees (0 = level, positive = looking down)"},
        "features": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "importance": {"type": "integer", "enum": [1, 2, 3]},
            "part": {"type": "string", "description": "library part id used for it, 'body', 'limb', 'paint', or 'none' if the library cannot express it"},
            "note": {"type": "string"}}, "required": ["name", "importance", "part", "note"], "additionalProperties": False}},
        "recipe_json": {"type": "string", "description": "the complete recipe as a JSON object string"},
    },
    "required": ["subject", "body_plan", "view_yaw", "view_pitch", "features", "recipe_json"],
    "additionalProperties": False,
}

CRITIQUE_SCHEMA = {
    "type": "object",
    "properties": {
        "feature_checks": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "score": {"type": "number", "description": "0 = missing/wrong, 0.5 = partly, 1 = clearly matches (within the library style)"},
            "issue": {"type": "string"}}, "required": ["name", "score", "issue"], "additionalProperties": False}},
        "ops_json": {"type": "string", "description": "JSON array of recipe ops to apply next (may be empty)"},
        "library_gaps": {"type": "array", "items": {"type": "string"}, "description": "features the library cannot express within its ranges"},
        "done": {"type": "boolean", "description": "true if further edits would not improve recognizability"},
    },
    "required": ["feature_checks", "ops_json", "library_gaps", "done"],
    "additionalProperties": False,
}


def _call(system, content, schema, effort="high"):
    resp = client().beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        cache_control={"type": "ephemeral"},
        system=system,
        messages=[{"role": "user", "content": content}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("model declined: %s" % (resp.stop_details.explanation if resp.stop_details else ""))
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("response hit max_tokens")
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text), resp.usage


def draft(ref_image, catalog, examples, sheet=None):
    content = [{"type": "text", "text": "Reference image:"}, image_block(ref_image)]
    if sheet:
        content += [{"type": "text", "text": "Thumbnails of the library parts (labelled by id):"}, image_block(sheet, 1600)]
    content.append({"type": "text", "text":
        "Identify the subject and list its distinguishing features by importance (3 = defines the subject). "
        "Estimate the camera view. Then write a complete recipe that captures it with this library, choosing "
        "the best part for each feature and setting params/scales/positions to match proportions. "
        "Ignore clothing, props and background."})
    return _call(_system(catalog, examples), content, DRAFT_SCHEMA)


def critique(ref_image, renders, analysis, recipe, scores, warnings, catalog, examples):
    content = [{"type": "text", "text": "Reference image:"}, image_block(ref_image)]
    for label, path in renders:
        content += [{"type": "text", "text": "Current build, %s:" % label}, image_block(path, 512)]
    content.append({"type": "text", "text": json.dumps({
        "features": analysis["features"], "current_recipe": recipe, "scores": scores,
        "normalizer_warnings": warnings[:30]}, separators=(",", ":"))})
    content.append({"type": "text", "text":
        "Score each feature against the reference (judge recognizability within the library style). "
        "Then propose ops that most improve the weakest high-importance features; prefer part swaps and "
        "placement fixes over tiny numeric tweaks (proportions are also fitted numerically afterwards). "
        "List features the library cannot express as library_gaps."})
    return _call(_system(catalog, examples), content, CRITIQUE_SCHEMA)
