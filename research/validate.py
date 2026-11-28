"""Validate species, evidence and anatomy coverage, then regenerate research/index.json."""
import argparse
import glob
import json
import math
import os
import sys
from pathlib import Path

if __package__:
    from . import build_library, coverage
else:
    import build_library
    import coverage

HERE = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = coverage.CATEGORIES
OPEN_LICENSES = ("cc0", "cc by", "cc-by", "public domain", "pd", "gfdl")
EXPECTED = ["scorpion", "beetle", "crab", "octopus", "raptor", "lizard", "frog", "shark",
            "feline", "canine", "primate", "worm", "jellyfish"]


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def in_box(p):
    if not isinstance(p, list) or len(p) != 3 or not all(finite_number(v) for v in p):
        return False
    x, y, z = p
    return -0.55 <= x <= 0.55 and -0.05 <= y <= 1.05 and -0.55 <= z <= 0.55


def check(data):
    problems = []
    for key in ("species_id", "taxon", "image", "physical_parsing", "parts", "category_summary", "constraints", "sources", "confidence"):
        if key not in data:
            problems.append("missing field: " + key)
    img = data.get("image") or {}
    if not any(coverage.url(img.get(field)) for field in ("file_page", "direct_url")):
        problems.append("no image source")
    lic = str(img.get("license") or "").lower()
    if not any(t in lic for t in OPEN_LICENSES):
        problems.append("image licence not recorded as open: %r" % img.get("license"))
    if not coverage.present(img.get("author")) or type(img.get("image_viewed")) is not bool:
        problems.append("image attribution or viewing status missing")
    if not finite_number(data.get("confidence")) or not 0 <= data["confidence"] <= 1:
        problems.append("confidence outside [0, 1]")
    bb = ((data.get("physical_parsing") or {}).get("bounding_box_m") or {})
    if not all(finite_number(bb.get(k)) and bb.get(k) > 0 for k in ("width_x", "height_y", "length_z")):
        problems.append("bounding box incomplete")
    counts = {c: 0 for c in CATEGORIES}
    part_ids = set()
    for part in data.get("parts") or []:
        pid = part.get("id", "?")
        if not coverage.present(pid) or pid == "?" or pid in part_ids:
            problems.append(f"invalid or duplicate part id: {pid!r}")
        part_ids.add(pid)
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
        if part.get("attach_pos") is not None and not in_box(part["attach_pos"]):
            problems.append("%s: attach_pos outside normalized box %s" % (pid, part["attach_pos"]))
        for j in part.get("joints") or []:
            if j.get("pos") is not None and not in_box(j["pos"]):
                problems.append("%s.%s: joint outside normalized box %s" % (pid, j.get("name"), j["pos"]))
        for key in ("length_m", "root_radius_m"):
            value = part.get(key)
            if value is not None and (not finite_number(value) or value < 0):
                problems.append(f"{pid}: invalid {key}")
        pen = part.get("penetration") or {}
        depth = pen.get("depth_m")
        if not finite_number(depth) or depth < 0:
            problems.append("%s: invalid penetration depth" % pid)
    stated = data.get("category_summary") or {}
    if set(stated) != set(CATEGORIES):
        problems.append("category_summary keys %s" % sorted(stated))
    elif any(type(value) is not int or value < 0 for value in stated.values()):
        problems.append("category_summary counts must be nonnegative integers")
    if not data.get("sources"):
        problems.append("no anatomy source notes")
    return problems, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed generated files without writing")
    args = parser.parse_args()
    files = sorted(glob.glob(os.path.join(HERE, "species", "*.json")))
    index, failures = [], 0
    for path in files:
        sid = os.path.basename(path)[:-5]
        try:
            data = coverage.load(Path(path))
        except (OSError, ValueError) as exc:
            print("%-10s INVALID JSON: %s" % (sid, exc))
            failures += 1
            continue
        problems, counts = check(data)
        if data.get("species_id") != sid:
            problems.append("species_id must match filename")
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
    if failures or missing:
        return 1
    try:
        spec = build_library.make_spec()
        report, errors = coverage.build_report(spec, index)
    except (KeyError, OSError, StopIteration, TypeError, ValueError) as exc:
        print(f"Coverage validation failed: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if not generated_file("part_library.json", spec, args.check):
        print("Run python3 research/build_library.py to regenerate the library spec.", file=sys.stderr)
        return 1
    if not generated_file("index.json", {"species": index, "missing": missing, "coverage": report}, args.check):
        print("Run python3 research/validate.py to regenerate the index.", file=sys.stderr)
        return 1
    print(f'{report["active_families"]} active families, {len(report["pending_candidates"])} candidates, '
          f'{len(report["merge_dispositions"])} merges, {report["new_observations"]} new observations')
    print(f'{report["queued_part_gaps"]} part-first leads across {len(report["part_gap_workstreams"])} workstreams')
    print(f'{report["planning_total"]} total including active families, drafts and unverified research leads')
    return 0


def generated_file(filename, data, check_only):
    path = Path(HERE) / filename
    generated = json.dumps(data, indent=2) + "\n"
    if check_only or filename == "part_library.json":
        return path.is_file() and path.read_text(encoding="utf-8") == generated
    path.write_text(generated, encoding="utf-8")
    return True


if __name__ == "__main__":
    sys.exit(main())
