"""Publication gate for the research candidates, usable without Blender."""

import json
import math
from pathlib import Path

STATUSES = ("qualified", "merged", "draft", "blocked")
GATES = ("structure", "fit", "motion", "likeness")
GATE_RESULTS = ("passed", "failed", "pending")


def remaining_work(record):
    """Separate observed failures from checks that still need evidence."""
    gates = record.get("gates", {})
    return {
        "needs_revision": [gate for gate in GATES if gates.get(gate) == "failed"],
        "needs_verification": [gate for gate in GATES if gates.get(gate, "pending") == "pending"],
    }


def records(directory=None):
    """Read the dispositions alongside the source or installed research spec."""
    if directory is None:
        package = Path(__file__).resolve().parent
        installed = package / "_data" / "research"
        directory = installed if installed.is_dir() else package.parent / "research"
    path = Path(directory) / "qualification.json"
    with path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    families = manifest.get("families")
    if (manifest.get("version") != 1 or not isinstance(families, dict)
            or not all(isinstance(row, dict) for row in families.values())):
        raise ValueError("Invalid qualification manifest")
    return families


def approved(record):
    """Draft evidence never qualifies a part for automatic selection."""
    if record.get("status") != "qualified":
        return False
    gates = record.get("gates") or {}
    if any(gates.get(gate) != "passed" for gate in GATES if gate != "motion"):
        return False
    if gates.get("motion") not in ("passed", "not_applicable"):
        return False
    review = record.get("review") or {}
    likeness = record.get("likeness") or {}
    views = likeness.get("views") or {}
    if not views or likeness.get("status") != "passed":
        return False
    measured_landmarks = False
    for metrics in views.values():
        candidate = metrics.get("candidate", {})
        iou = candidate.get("silhouette_iou")
        error = candidate.get("mean_landmark_error")
        if iou is None and error is None:
            return False
        if error is not None and (type(error) not in (int, float) or not math.isfinite(error)
                                  or not 0 <= error <= .05):
            return False
        if iou is not None and (type(iou) not in (int, float) or not math.isfinite(iou) or not .85 <= iou <= 1):
            return False
        measured_landmarks |= error is not None
    return bool(measured_landmarks and review.get("reviewer") and review.get("independent") is True
                and type(review.get("major_findings")) is int and review["major_findings"] == 0
                and review.get("evidence") and record.get("references"))
