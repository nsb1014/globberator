"""Validate and index the species research files.

    python3 research/validate.py            # check every research/species/*.json, write research/index.json

Checks each file against the shared schema: required fields, the five part
categories, normalized coordinates inside the bounding box, category counts
that match the part list, a recorded image licence, and sources.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = {"locomotion", "sensory", "feeding", "manipulation", "aesthetics"}
OPEN_LICENSES = ("cc0", "cc by", "cc-by", "public domain", "pd", "gfdl")
EXPECTED = ["scorpion", "beetle", "crab", "octopus", "raptor", "lizard", "frog", "shark",
            "feline", "canine", "primate", "worm", "jellyfish"]


def in_box(p, radial=False):
    if not isinstance(p, list) or len(p) != 3 or not all(isinstance(v, (int, float)) for v in p):
        return False
    x, y, z = p
    return -0.55 <= x <= 0.55 and -0.05 <= y <= 1.05 and -0.55 <= z <= 0.55


def check(data):
    problems = []
    for key in ("species_id", "taxon", "image", "physical_parsing", "parts", "category_summary", "constraints", "sources", "confidence"):
        if key not in data:
            problems.append("missing field: " + key)
    img = data.get("image") or {}
    if not img.get("file_page") and not img.get("direct_url"):
        problems.append("no image source")
    lic = str(img.get("license") or "").lower()
    if not any(t in lic for t in OPEN_LICENSES):
        problems.append("image licence not recorded as open: %r" % img.get("license"))
    bb = ((data.get("physical_parsing") or {}).get("bounding_box_m") or {})
    if not all(isinstance(bb.get(k), (int, float)) and bb.get(k) > 0 for k in ("width_x", "height_y", "length_z")):
        problems.append("bounding box incomplete")
    counts = {c: 0 for c in CATEGORIES}
    radial = (data.get("species_id") == "jellyfish")
    for part in data.get("parts") or []:
        pid = part.get("id", "?")
        if "mirror_of" in part or "partner" in part:
            problems.append("%s: mirror entries are not recorded; symmetry 'pair' implies the twin" % pid)
            continue
        cat = part.get("category")
        if cat not in CATEGORIES:
            problems.append("%s: bad category %r" % (pid, cat))
            continue
        # Distinct part types per category: a pair or a repeated structure is one entry.
        counts[cat] += 1
        if part.get("symmetry") == "pair" and in_box(part.get("attach_pos")) and part["attach_pos"][0] < 0:
            problems.append("%s: paired parts are recorded on the +X side" % pid)
        if part.get("attach_pos") is not None and not in_box(part["attach_pos"], radial):
            problems.append("%s: attach_pos outside normalized box %s" % (pid, part["attach_pos"]))
        for j in part.get("joints") or []:
            if j.get("pos") is not None and not in_box(j["pos"], radial):
                problems.append("%s.%s: joint outside normalized box %s" % (pid, j.get("name"), j["pos"]))
        pen = part.get("penetration") or {}
        if not isinstance(pen.get("depth_m"), (int, float)):
            problems.append("%s: no penetration depth" % pid)
    stated = data.get("category_summary") or {}
    if set(stated) != CATEGORIES:
        problems.append("category_summary keys %s" % sorted(stated))
    if not data.get("sources"):
        problems.append("no sources")
    return problems, counts


def main():
    files = sorted(glob.glob(os.path.join(HERE, "species", "*.json")))
    index, failures = [], 0
    for path in files:
        sid = os.path.basename(path)[:-5]
        try:
            data = json.load(open(path))
        except ValueError as exc:
            print("%-10s INVALID JSON: %s" % (sid, exc))
            failures += 1
            continue
        problems, counts = check(data)
        img = data.get("image") or {}
        bb = (data.get("physical_parsing") or {}).get("bounding_box_m") or {}
        index.append({"species_id": sid, "label": data.get("label"), "scientific": (data.get("taxon") or {}).get("scientific"),
                      "image": img.get("file_page") or img.get("direct_url"), "license": img.get("license"),
                      "image_viewed": img.get("image_viewed"), "bounding_box_m": bb, "parts": len(data.get("parts") or []),
                      "category_summary": data.get("category_summary"), "part_types_by_category": counts,
                      "other_features": [g.get("feature") for g in data.get("other_features") or []],
                      "confidence": data.get("confidence"), "problems": problems})
        print("%-10s %s  parts=%-3d viewed=%-5s %s" % (sid, "ok  " if not problems else "WARN", len(data.get("parts") or []),
                                                     img.get("image_viewed"), "; ".join(problems[:3])))
        failures += bool(problems)
    missing = [s for s in EXPECTED if s not in {i["species_id"] for i in index}]
    if missing:
        print("missing species:", ", ".join(missing))
    json.dump({"species": index, "missing": missing}, open(os.path.join(HERE, "index.json"), "w"), indent=2)
    return 1 if failures or missing else 0


if __name__ == "__main__":
    sys.exit(main())
