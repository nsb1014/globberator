"""Claude calls for the image -> recipe workflow.

Two calls, both with structured outputs so the reply is always parseable:
  draft()    reference image + part catalog -> feature analysis + first recipe
  critique() reference + renders of the current recipe -> per-feature scores + edit ops
"""
import base64
import io
import json
import os

from PIL import Image

MODEL = os.environ.get("GLOBBERATOR_MODEL", os.environ.get("POLYFORGE_MODEL", "claude-haiku-4-5"))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_client = None


def client():
    global _client
    if _client is None:
        import anthropic
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


RECIPE_GUIDE = """Write version 2 JSON. +Y up, +Z forward. spine: 2-16 rear-to-front
{y,z,w,h} rings (w,h are half-extents). limbs: {uid,u,theta,segments:[[dx,dy,dz],...],
radii:[root,...,tip],tip,tip_params}. motion:"tail" makes a flexible non-supporting chain.
parts: {uid,part,u,theta,params,scale,rot:[degrees],on:"body" or limb uid}.
u runs from rear tip (0) to nose (1); theta=0 at the side, +90 at the back/top, -90 at belly.
Place once: midline single, side paired. Scale and rotation fit a local shape on the animal.
The builder manages ring bindings. Never author bind or a mirror flag.
paint: {base,accent,detail} hex colors, pattern none/stripes/spots/patches/gradient.
Keep the torso on the spine. Author tails as separate motion:"tail" chains; put tail ornaments on that chain.
Choose broad masses and silhouette before details. Use defaults when unsure."""


def _system(catalog):
    groups = {}
    for part in catalog["parts"]:
        groups.setdefault(part["category"], []).append(part["id"])
    return RECIPE_GUIDE + "\nAvailable families: " + json.dumps(groups, separators=(",", ":"))


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
        "anatomy_pass": {"type":"boolean","description":"All visible relative placements and attachment seams pass visual inspection against the reference"},
        "anatomy_note": {"type":"string","description":"Describe observed landmark relationships, including eyes, jaw, horns and wing roots where present"},
        "feature_checks": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "score": {"type": "number", "description": "0 = missing/wrong, 0.5 = partly, 1 = clearly matches (within the library style)"},
            "issue": {"type": "string"}}, "required": ["name", "score", "issue"], "additionalProperties": False}},
        "ops_json": {"type": "string", "description": "JSON array of recipe ops to apply next (may be empty)"},
        "library_gaps": {"type": "array", "items": {"type": "string"}, "description": "features the library cannot express within its ranges"},
        "done": {"type": "boolean", "description": "true if further edits would not improve recognizability"},
    },
    "required": ["anatomy_pass", "anatomy_note", "feature_checks", "ops_json", "library_gaps", "done"],
    "additionalProperties": False,
}


def _call(system, content, schema, effort="high", max_tokens=8192):
    resp = client().messages.create(
        model=MODEL, max_tokens=max_tokens,
        output_config={"format": {"type": "json_schema", "schema": schema}},
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


def character_brief(image):
    from polyforge.character_brief import SCHEMA

    return _call(
        "Classify the main figure for a neutral-clay game character. An upright human-shaped "
        "figure has two arms and two legs, regardless of stylization. Mark other body plans unsupported. "
        "Judge the figure itself, excluding keychain hardware, stands, handheld objects and background. "
        "Estimate its proportions in a neutral standing pose. Infer occluded anatomy conservatively. "
        "Ignore paint, patterns and facial markings.",
        [image_block(image, 768), {"type": "text", "text": "Return only the character classification."}],
        SCHEMA, max_tokens=384,
    )


def draft(ref_image, catalog):
    content = [{"type": "text", "text": "Reference image:"}, image_block(ref_image)]
    content.append({"type": "text", "text":
        "Identify the subject and list its distinguishing features by importance (3 = defines the subject). "
        "Estimate the camera view. Then write a complete recipe that captures it with this library, choosing "
        "the best part for each feature and setting params/scales/positions to match proportions. "
        "Ignore clothing, props and background."})
    return _call(_system(catalog), content, DRAFT_SCHEMA)


def critique(ref_image, renders, analysis, recipe, scores, warnings, catalog):
    content = [{"type": "text", "text": "Reference image:"}, image_block(ref_image)]
    for label, path in renders:
        content += [{"type": "text", "text": "Current build, %s:" % label}, image_block(path, 512)]
    content.append({"type": "text", "text": json.dumps({
        "features": analysis["features"], "current_recipe": public_recipe(recipe), "available_edits": catalog["ops"], "scores": scores,
        "normalizer_warnings": warnings[:30]}, separators=(",", ":"))})
    content.append({"type": "text", "text":
        "Score each feature against the reference (judge recognizability within the library style). "
        "Then propose ops that most improve the weakest high-importance features; prefer part swaps and "
        "placement fixes over tiny numeric tweaks (proportions are also fitted numerically afterwards). "
        "List features the library cannot express as library_gaps."})
    return _call(_system(catalog), content, CRITIQUE_SCHEMA)

def public_recipe(recipe):
    r = dict(recipe)
    r["spine"] = [{k: v for k, v in ring.items() if k != "id"} for ring in recipe["spine"]]
    for key in ("parts", "limbs"):
        r[key] = [{k: v for k, v in item.items() if k != "bind"} for item in recipe[key]]
    return r


def refine_shape(reference, views, shape, controls):
    schema = {"type": "object", "properties": {"accept": {"type": "boolean"},
              "shape_json": {"type": "string"}}, "required": ["accept", "shape_json"], "additionalProperties": False}
    content = [image_block(reference)] + [image_block(path, 384) for path in views]
    content.append({"type": "text", "text": json.dumps({"shape": shape, "controls": controls})})
    return _call("Compare the selected part in the reference with the isolated front and side views. "
                 "Accept its silhouette or return the revised local shape JSON. Preserve the part or tip type. "
                 "Only edit params, segments, radii or tip_params; placement is handled separately.", content, schema)
