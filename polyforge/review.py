"""Visual review identity for a normalized creature recipe."""
import hashlib
import json

from . import recipe


def signature(src):
    normalized, _ = recipe.normalize(src)
    return hashlib.sha256(recipe.to_json(normalized).encode()).hexdigest()


def record(src, decision, note):
    return {"recipe_hash": signature(src), "accepted": decision, "note": note}


def require(src, review):
    if not review.get("accepted") or review.get("recipe_hash") != signature(src):
        raise ValueError("Inspect front, side and head views of this recipe and accept its visual review first.")
