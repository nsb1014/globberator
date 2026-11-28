"""Validate the evidence ledger and derive the anatomy coverage report without Blender."""

import ast
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from polyforge import qualification

RESEARCH = ROOT / "research"
ID = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
CATEGORIES = ("locomotion", "sensory", "feeding", "manipulation", "aesthetics")
KINDS = ("limb", "tip", "surface", "core")
SYMMETRIES = ("pair", "centre", "radial", "repeated", "asymmetric")
LANDMARKS = ("root", "extent", "profile")
CONFIDENCE = ("low", "medium", "high")
RANKS = ("species", "genus", "family", "order", "class", "phylum")


def load(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def url(value):
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"https", "http"} and bool(parsed.hostname)


def present(value):
    return isinstance(value, str) and bool(value.strip())


def part_literals(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.args[0].value: {
            "category": node.args[1].value if isinstance(node.args[1], ast.Constant) else None,
            "runtime_attachment": next(
                (kw.value.value for kw in node.keywords if kw.arg == "attach" and isinstance(kw.value, ast.Constant)),
                "surface",
            ),
        }
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Part"
        and len(node.args) >= 2 and isinstance(node.args[0], ast.Constant)
    }


def active_families(spec, dispositions):
    catalog = ROOT / "polyforge" / "catalog.py"
    tree = ast.parse(catalog.read_text(encoding="utf-8"), filename=str(catalog))
    complementary = next(
        ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "COMPLEMENTARY" for target in node.targets)
    )
    folders = ROOT / "polyforge" / "parts"
    legacy = {}
    for name in ("head", "face", "body", "tips"):
        legacy.update(part_literals(folders / (name + ".py")))
    families = {
        part["id"]: {"origin": "derived", "category": part["category"], "kind": part["kind"],
                     "symmetry": part["symmetry"], "legacy_sources": part["sources"]}
        for part in spec["parts"]
    }
    if len(families) != len(spec["parts"]):
        raise ValueError("duplicate derived family id")
    for identifier in complementary:
        if identifier in families:
            raise ValueError(f"duplicate active family {identifier}")
        families[identifier] = {"origin": "complementary", **legacy[identifier], "legacy_sources": []}
    # Audit literal Part definitions without importing Blender.
    for module in ("anatomy", "pilots"):
        part_path = folders / (module + ".py")
        if not part_path.exists() or not any(
            isinstance(node, ast.Name) and node.id == module for node in ast.walk(tree)
        ):
            continue
        for identifier, data in part_literals(part_path).items():
            if identifier in families:
                raise ValueError(f"duplicate active family {identifier}")
            families[identifier] = {"origin": "pilot" if module == "pilots" else "anatomy",
                                    **data, "legacy_sources": []}
    drafts = {}
    for path in sorted(folders.glob("candidate_*.py")):
        for identifier, data in part_literals(path).items():
            if identifier in families or identifier in drafts:
                raise ValueError(f"duplicate research candidate {identifier}")
            drafts[identifier] = data
    for identifier, data in drafts.items():
        if qualification.approved(dispositions.get(identifier, {})):
            families[identifier] = {"origin": "qualification", **data, "legacy_sources": []}
    return families, drafts


def keyed(rows, label, errors):
    out = {}
    if not isinstance(rows, list):
        errors.append(f"{label}: expected a list")
        return out
    for row in rows:
        identifier = row.get("id") if isinstance(row, dict) else None
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            errors.append(f"{label}: invalid id {identifier!r}")
        elif identifier in out:
            errors.append(f"{label}: duplicate id {identifier}")
        else:
            out[identifier] = row
    return out


def text_fields(row, fields, label, errors):
    for field in fields:
        if not present(row.get(field)):
            errors.append(f"{label}: missing {field}")


def references(row, field, available, label, errors):
    refs = row.get(field)
    if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) for ref in refs):
        errors.append(f"{label}: {field} must be a nonempty id list")
        return []
    if len(refs) != len(set(refs)) or set(refs) - available.keys():
        errors.append(f"{label}: duplicate or unknown {field}")
    return [ref for ref in refs if ref in available]


def validate_source(row, label, errors):
    text_fields(row, ("title", "publisher", "locator", "rights"), label, errors)
    if not all(url(row.get(key)) for key in ("url", "rights_url")):
        errors.append(f"{label}: invalid source or rights URL")
    try:
        date.fromisoformat(row.get("accessed"))
    except (ValueError, TypeError):
        errors.append(f"{label}: accessed must be an ISO date")
    if row.get("material") not in {"text", "diagram", "photo", "scan"}:
        errors.append(f"{label}: invalid material")
    if row.get("reuse") not in {"facts_only", "licensed_media"}:
        errors.append(f"{label}: invalid reuse")
    if row.get("reuse") == "licensed_media":
        text_fields(row, ("creator", "license"), label, errors)
        if not url(row.get("asset_url")) or row.get("license") not in {
            "CC0-1.0", "PDM-1.0", "CC-BY-3.0", "CC-BY-4.0", "CC-BY-SA-3.0", "CC-BY-SA-4.0",
        }:
            errors.append(f"{label}: licensed media must have an asset URL and an open license")


def validate_observation(row, groups, sources, label, errors):
    text_fields(row, ("scientific_name", "stage", "feature", "anatomy"), label, errors)
    if row.get("group") not in groups:
        errors.append(f"{label}: unknown coverage group")
    refs = references(row, "sources", sources, label, errors)
    landmarks = row.get("landmarks")
    if isinstance(landmarks, dict):
        text_fields(landmarks, LANDMARKS, f"{label} landmarks", errors)
    else:
        errors.append(f"{label}: landmarks must name root, extent and profile")
    if row.get("anatomy_confidence") not in CONFIDENCE:
        errors.append(f"{label}: invalid anatomy_confidence")
    basis = row.get("landmark_basis")
    if basis not in {"text", "viewed", "measured", "inferred"}:
        errors.append(f"{label}: invalid landmark_basis")
    if row.get("taxonomic_rank") not in RANKS:
        errors.append(f"{label}: invalid taxonomic_rank")
    if basis == "viewed" and not any(sources[ref].get("material") in {"diagram", "photo", "scan"} for ref in refs):
        errors.append(f"{label}: viewed landmarks must cite an image, diagram or scan")
    measurements = row.get("measurements", [])
    if not isinstance(measurements, list) or (basis == "measured" and not measurements):
        errors.append(f"{label}: measured landmarks must record supporting measurements")
    elif any(
        not isinstance(item, dict) or not all(present(item.get(key)) for key in ("landmark", "unit", "method"))
        or type(item.get("value")) not in (int, float) or not 0 <= item["value"] < float("inf")
        or item.get("source") not in refs for item in measurements
    ):
        errors.append(f"{label}: invalid measurement or measurement source")
    inference = row.get("inference")
    if not isinstance(inference, dict):
        errors.append(f"{label}: inference must record geometry assumptions and confidence")
    else:
        text_fields(inference, ("geometry", "missing_evidence"), f"{label} inference", errors)
        if inference.get("confidence") not in {"low", "medium"}:
            errors.append(f"{label}: unverified geometry confidence must be low or medium")


def validate_proposal(row, proposals, observations, active, label, errors):
    text_fields(row, ("name", "discriminator", "next_review"), label, errors)
    references(row, "observations", observations, label, errors)
    for key, choices in (("category", CATEGORIES), ("kind", KINDS), ("symmetry", SYMMETRIES)):
        if row.get(key) not in choices:
            errors.append(f"{label}: invalid {key}")
    if row["id"] in active and active[row["id"]]["origin"] != "qualification":
        errors.append(f"{label}: id already exists in the active catalog")
    closest = row.get("closest_active")
    if not isinstance(closest, str) or closest not in active:
        errors.append(f"{label}: closest_active must name an active family")
    if row.get("status") == "merge":
        target = row.get("merge_into")
        if not isinstance(target, str) or (
            target not in active and proposals.get(target, {}).get("status") != "candidate"
        ):
            errors.append(f"{label}: merge_into must name an active family or a candidate")
    elif row.get("status") != "candidate" or "merge_into" in row:
        errors.append(f"{label}: expected status candidate, or merge with merge_into")


def build_report(spec, species_index):
    plan = load(RESEARCH / "coverage_plan.json")
    ledger = load(RESEARCH / "observations.json")
    errors = []
    if plan.get("version") != 1 or ledger.get("version") != 1:
        errors.append("coverage plan and evidence ledger must have version 1")
    groups = keyed(plan.get("groups"), "coverage groups", errors)
    sources = keyed(ledger.get("sources"), "sources", errors)
    observations = keyed(ledger.get("observations"), "observations", errors)
    proposals = keyed(ledger.get("proposals"), "proposals", errors)
    dispositions = qualification.records(RESEARCH)
    active, drafts = active_families(spec, dispositions)
    nominated = {key for key, row in proposals.items() if row["status"] == "candidate"}
    if dispositions.keys() != nominated:
        errors.append("qualification manifest must give each research candidate one disposition")
    qualified_merges = {key for key, row in dispositions.items() if row.get("status") == "merged"}
    merge_targets = (active.keys() | nominated) - qualified_merges
    for identifier in sorted(drafts.keys() - nominated):
        errors.append(f"{identifier}: candidate model has no research proposal")
    for identifier, row in dispositions.items():
        status = row.get("status")
        if status not in qualification.STATUSES or not present(row.get("reason")):
            errors.append(f"{identifier}: qualification status and reason required")
        elif status == "qualified" and (identifier not in drafts or not qualification.approved(row)):
            errors.append(f"{identifier}: qualified family lacks a model or passing evidence")
        elif status == "draft" and identifier not in drafts:
            errors.append(f"{identifier}: draft family lacks a model")
        elif status == "merged" and row.get("merge_into") not in merge_targets:
            errors.append(f"{identifier}: merge must point to another researched or active family")
        if status in ("draft", "qualified"):
            gates = row.get("gates", {})
            for gate in qualification.GATES:
                allowed = qualification.GATE_RESULTS + (("not_applicable",) if gate == "motion" else ())
                if gates.get(gate) not in allowed:
                    errors.append(f"{identifier}: invalid or missing {gate} gate result")
    legacy_groups = plan.get("legacy_groups", {})
    known_species = {item["species_id"] for item in species_index}
    if set(legacy_groups) != known_species or set(legacy_groups.values()) - groups.keys():
        errors.append("coverage plan must assign every legacy species to one known group")

    for identifier, row in groups.items():
        text_fields(row, ("label", "gap", "next_sources"), identifier, errors)
    part_gaps = keyed(plan.get("part_gaps", []), "part gaps", errors)
    available_parts = active | drafts
    for identifier, row in part_gaps.items():
        text_fields(row, ("function", "gap", "reference_animal", "model_scope", "local_fixture"),
                    identifier, errors)
        if "reference_url" in row and not url(row["reference_url"]):
            errors.append(f"{identifier}: invalid reference lead URL")
        if "reference_url" not in row and not present(row.get("reference_query")):
            errors.append(f"{identifier}: part gap requires a reference URL or specimen search brief")
        workstream = row.get("workstream")
        if not isinstance(workstream, str) or not ID.fullmatch(workstream):
            errors.append(f"{identifier}: part gap requires a workstream ID")
        references(row, "compare_to", available_parts, identifier, errors)
    for identifier, row in sources.items():
        validate_source(row, identifier, errors)
    for identifier, row in observations.items():
        validate_observation(row, groups, sources, identifier, errors)
    for identifier, row in proposals.items():
        validate_proposal(row, proposals, observations, active, identifier, errors)

    assigned = Counter(ref for row in proposals.values()
                       for ref in references(row, "observations", observations, row["id"], []))
    for identifier in sorted(observations.keys() - assigned.keys()):
        errors.append(f"{identifier}: observation has no candidate or merge disposition")
    for identifier, count in sorted(assigned.items()):
        if count > 1:
            errors.append(f"{identifier}: observation is counted in multiple proposals")
    identities = set()
    for identifier, row in observations.items():
        identity_fields = (row.get("scientific_name"), row.get("stage"), row.get("feature"))
        if all(present(value) for value in identity_fields):
            identity = tuple(" ".join(value.casefold().split()) for value in identity_fields)
            if identity in identities:
                errors.append(f"{identifier}: duplicate taxon, stage and feature")
            identities.add(identity)

    target = plan.get("target_families")
    if type(target) is not int or target < 1:
        errors.append("target_families must be a positive integer")
    if errors:
        return None, errors

    evidence_by_active = {}
    for row in proposals.values():
        status = dispositions.get(row["id"], {})
        evidence_target = row.get("merge_into") or status.get("merge_into")
        if row["id"] in active and status.get("status") == "qualified":
            evidence_target = row["id"]
        if evidence_target in active:
            evidence_by_active.setdefault(evidence_target, []).extend(row["observations"])
    for identifier, family in active.items():
        family["observations"] = sorted(evidence_by_active.get(identifier, []))
        family["status"] = "active"
        family["evidence"] = (
            "legacy_numeric_spec" if family["legacy_sources"]
            else "linked_observations" if family["observations"]
            else "unlinked"
        )
    coverage = {}
    for identifier, row in groups.items():
        group_obs = [key for key, obs in observations.items() if obs["group"] == identifier]
        group_proposals = sorted(key for key, value in proposals.items()
                                 if set(value["observations"]).intersection(group_obs))
        coverage[identifier] = {
            **row,
            "legacy_species": sorted(sid for sid, group in legacy_groups.items() if group == identifier),
            "new_taxa": sorted({observations[oid]["scientific_name"] for oid in group_obs}),
            "observations": sorted(group_obs),
            "candidates": [key for key in group_proposals if dispositions.get(key, {}).get("status") in ("draft", "blocked")],
            "merges": [key for key in group_proposals
                       if proposals[key]["status"] == "merge" or key in qualified_merges],
        }
    # A lead keeps its provenance when adopted, but cannot be counted twice.
    queued = [row for key, row in part_gaps.items() if key not in available_parts and key not in proposals]
    qualification_counts = Counter(row["status"] for row in dispositions.values())
    workstreams = {}
    for gap in queued:
        workstreams.setdefault(gap["workstream"], []).append(gap["id"])
    return {
        "target_families": target,
        "active_by_origin": dict(sorted(Counter(row["origin"] for row in active.values()).items())),
        "active_families": len(active),
        "remaining_to_target": max(0, target - len(active)),
        "active_family_audit": dict(sorted(active.items())),
        "legacy_mapped_observations": len({ref for row in active.values() for ref in row["legacy_sources"]}),
        "legacy_excluded_observations": len(spec["excluded"]),
        "new_sources": len(sources),
        "new_observations": len(observations),
        "new_taxa": len({row["scientific_name"] for row in observations.values()}),
        "new_taxa_by_rank": dict(sorted(Counter(
            rank for _, rank in {(row["scientific_name"], row["taxonomic_rank"]) for row in observations.values()}
        ).items())),
        "candidate_categories": {category: sum(row["status"] == "candidate" and row["category"] == category
                                               for row in proposals.values()) for category in CATEGORIES},
        "pending_candidates": sorted(key for key, row in dispositions.items() if row["status"] in ("draft", "blocked")),
        "qualification_work": {key: qualification.remaining_work(row)
                               for key, row in sorted(dispositions.items()) if row["status"] == "draft"},
        "part_gaps": list(part_gaps.values()),
        "queued_part_gaps": len(queued),
        "part_gap_workstreams": workstreams,
        "planning_total": len(active) + qualification_counts["draft"] + len(queued),
        "qualification_counts": {state: qualification_counts[state] for state in qualification.STATUSES},
        "qualified_candidates": sorted(key for key, row in dispositions.items() if row["status"] == "qualified"),
        "merge_dispositions": sorted(qualified_merges | {key for key, row in proposals.items()
                                                         if row["status"] == "merge"}),
        "taxonomy_coverage": coverage,
    }, []
