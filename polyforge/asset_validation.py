"""Independent measurements for registered reference views and evaluated surface sections."""

import math
import os
from collections import defaultdict
from itertools import product

import numpy as np


def _mask(source):
    if isinstance(source, (str, os.PathLike)):
        from PIL import Image

        with Image.open(source) as image:
            if "A" in image.getbands() or "transparency" in image.info:
                return np.asarray(image.convert("RGBA"))[:, :, 3] >= 128
            if image.mode in {"1", "L"}:
                return np.asarray(image.convert("L")) >= 128
            raise ValueError(f"{source}: expected a grayscale mask or image with transparency")
    array = np.asarray(source)
    if array.ndim != 2 or not np.isin(array, (0, 1)).all():
        raise ValueError("Expected a two-dimensional binary mask")
    return array.astype(bool)


def _point(value, dimensions):
    point = np.asarray(value, dtype=float)
    if point.shape != (dimensions,) or not np.isfinite(point).all():
        raise ValueError(f"Expected a finite {dimensions}D point or direction")
    return point


def _view_metrics(reference, rendered, name):
    ref_mask = reference.get("mask")
    scale = reference.get("landmark_scale")
    if ref_mask is not None:
        ref_mask = _mask(ref_mask)
        y, x = np.nonzero(ref_mask)
        if not len(x):
            raise ValueError(f"{name}: reference silhouette is empty")
        scale = int(max(np.ptp(x), np.ptp(y))) + 1
    landmarks = reference.get("landmarks", {})
    if landmarks and (scale is None or not math.isfinite(scale) or scale <= 0):
        raise ValueError(f"{name}: visible landmarks require a positive reference dimension")
    if ref_mask is None and not landmarks:
        raise ValueError(f"{name}: mark at least one measurable reference feature")

    iou = None
    if ref_mask is not None and rendered.get("mask") is not None:
        render_mask = _mask(rendered["mask"])
        if ref_mask.shape != render_mask.shape:
            raise ValueError(f"{name}: reference and render mask dimensions differ")
        iou = float(np.count_nonzero(ref_mask & render_mask) / np.count_nonzero(ref_mask | render_mask))

    errors = {}
    points = rendered.get("landmarks", {})
    for label, reference_point in landmarks.items():
        target = _point(reference_point, 2)
        proposed = points.get(label)
        errors[label] = None if proposed is None else float(np.linalg.norm(_point(proposed, 2) - target) / scale)
    mean = float(np.mean(list(errors.values()))) if errors and None not in errors.values() else None
    return {"silhouette_iou": iou, "landmark_errors": errors, "mean_landmark_error": mean}


def _review_checks(review, views):
    if review is None:
        return [], ["Independent visual review is pending"]
    pending = []
    if review.get("independent") is not True or not str(review.get("reviewer") or "").strip():
        pending.append("Independent visual review requires an identified reviewer")
    missing_views = set(views) - set(review.get("reviewed_views", ()))
    if missing_views:
        pending.append(f"Independent visual review is missing views: {', '.join(sorted(missing_views))}")
    findings = review.get("findings")
    if not isinstance(findings, list):
        return [], [*pending, "Independent visual review requires a findings list"]
    failures = []
    for index, finding in enumerate(findings, 1):
        severity = finding.get("severity")
        evidence = finding.get("evidence")
        view = finding.get("view")
        if (severity not in {"info", "minor", "moderate", "major", "critical"}
                or view not in views or not str(evidence or "").strip()):
            pending.append(f"Visual finding {index} requires a severity, held-out view and visible evidence")
        if severity in {"major", "critical"}:
            failures.append(f"{view}: {severity} visual finding: {evidence}")
    return failures, pending


def _status(failures, pending):
    if failures:
        return "failed"
    if pending:
        return "pending"
    return "passed"


def compare_held_out(reference_views, candidate_views, incumbent_views=None, review=None, *,
                     min_iou=.85, max_mean_landmark_error=.05, require_incumbent=True):
    """Score matched held-out views in a fixed, predeclared image coordinate frame.

    Each view maps to ``mask`` (binary array or grayscale/alpha PNG) and
    ``landmarks`` (visible named pixel points). Omit the reference mask for a
    cropped view and supply ``landmark_scale`` as its full reference dimension.
    A visible full silhouette supplies its own longest bounding-box dimension.
    Review evidence includes ``reviewer``, ``independent``, ``reviewed_views``
    and ``findings`` with ``view``, ``severity`` and ``evidence`` for each finding.
    Set ``require_incumbent=False`` for a distinct family with no equivalent.
    """
    if not reference_views:
        raise ValueError("At least one held-out reference view is required")
    if not 0 <= min_iou <= 1 or not math.isfinite(max_mean_landmark_error) or max_mean_landmark_error < 0:
        raise ValueError("Invalid silhouette or landmark threshold")

    failures, pending = _review_checks(review, reference_views)
    views = {}
    for name, reference in reference_views.items():
        candidate = _view_metrics(reference, candidate_views.get(name, {}), name)
        baseline = _view_metrics(reference, (incumbent_views or {}).get(name, {}), name)
        silhouette_delta = None
        if reference.get("mask") is not None:
            iou = candidate["silhouette_iou"]
            incumbent_iou = baseline["silhouette_iou"]
            if iou is None:
                failures.append(f"{name}: candidate silhouette is missing")
            elif iou < min_iou:
                failures.append(f"{name}: silhouette IoU {iou:.4f} is below {min_iou:.4f}")
            if incumbent_iou is None and require_incumbent:
                pending.append(f"{name}: paired incumbent silhouette is missing")
            if incumbent_iou is not None and iou is not None:
                silhouette_delta = iou - incumbent_iou
                if silhouette_delta < -1e-12:
                    failures.append(f"{name}: silhouette IoU {iou:.4f} regresses from incumbent {incumbent_iou:.4f}")
        if reference.get("landmarks"):
            missing = [label for label, error in candidate["landmark_errors"].items() if error is None]
            mean = candidate["mean_landmark_error"]
            if missing:
                failures.append(f"{name}: candidate landmarks are missing: {', '.join(missing)}")
            elif mean > max_mean_landmark_error:
                failures.append(f"{name}: mean landmark error {mean:.4f} exceeds {max_mean_landmark_error:.4f}")
        views[name] = {"candidate": candidate, "incumbent": baseline, "silhouette_iou_delta": silhouette_delta}
    return {"status": _status(failures, pending), "views": views, "failures": failures, "pending": pending}


def _unit(vector):
    length = np.linalg.norm(vector)
    if length < 1e-12:
        raise ValueError("Section direction must have a nonzero length")
    return vector / length


def _section_segments(vertices, triangles, origin, normal, basis, epsilon):
    distances = (vertices - origin) @ normal
    offset = 0.0
    if np.any(np.abs(distances) <= epsilon / 8):
        # Move a section that lands exactly on vertices a few weld tolerances
        # along its normal so every cut triangle contributes just one edge.
        offset = 0.0
        for index in range(1, len(distances) + 2):
            offset = index * epsilon
            if np.all(np.abs(distances - offset) > epsilon / 8):
                break
        distances -= offset
    signs = distances[triangles] > 0
    spans = (signs[:, 0] != signs[:, 1]) | (signs[:, 1] != signs[:, 2])
    faces = triangles[spans]
    following = np.roll(faces, -1, axis=1)
    a, b = distances[faces], distances[following]
    crossing = (a > 0) != (b > 0)
    start, end = faces[crossing], following[crossing]
    fractions = a[crossing] / (a[crossing] - b[crossing])
    points = vertices[start] + (vertices[end] - vertices[start]) * fractions[:, None]
    return ((points - origin) @ basis.T).reshape(-1, 2, 2), offset


def _section_curves(segments, tolerance):
    points, edges = [], []
    cells, adjacency = defaultdict(list), defaultdict(list)
    neighbors = list(product((-1, 0, 1), repeat=2))

    def index(point):
        x, y = np.floor(point / tolerance).astype(int)
        for dx, dy in neighbors:
            for found in cells[x + dx, y + dy]:
                if np.linalg.norm(points[found] - point) <= tolerance:
                    return found
        cells[x, y].append(len(points))
        points.append(point)
        return len(points) - 1

    for start, end in segments:
        a, b = index(start), index(end)
        if a != b:
            adjacency[a].append(b)
            adjacency[b].append(a)
            edges.append((a, b))

    remaining = set(adjacency)
    loops = []
    open_vertices = set()
    while remaining:
        start = remaining.pop()
        component = {start}
        stack = [start]
        while stack:
            nearest = set(adjacency[stack.pop()]) & remaining
            remaining.difference_update(nearest)
            component.update(nearest)
            stack.extend(nearest)
        if len(component) < 3 or any(len(adjacency[i]) != 2 for i in component):
            open_vertices.update(component)
            continue
        order, previous, current = [start], start, adjacency[start][0]
        while current != start:
            order.append(current)
            first, second = adjacency[current]
            previous, current = current, second if first == previous else first
        loops.append(np.asarray([points[i] for i in order]))

    open_edges = np.asarray([(points[a], points[b]) for a, b in edges if a in open_vertices]).reshape(-1, 2, 2)
    return loops, open_edges


def _line_crossings(loop, angle):
    cosine, sine = math.cos(angle), math.sin(angle)
    x, y = loop @ (cosine, sine), loop @ (-sine, cosine)
    next_x, next_y = np.roll(x, -1), np.roll(y, -1)
    crossing = (y > 0) != (next_y > 0)
    return x[crossing] - y[crossing] * (next_x[crossing] - x[crossing]) / (next_y[crossing] - y[crossing])


def _contains(loop, point, tolerance):
    return np.count_nonzero(_line_crossings(loop - point, 0) > tolerance) % 2


def _cross(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _segments_intersect(a, b, other, tolerance):
    c, d = other[:, 0], other[:, 1]
    lower = np.maximum(np.minimum(a, b), np.minimum(c, d))
    upper = np.minimum(np.maximum(a, b), np.maximum(c, d))
    in_bounds = np.all(lower <= upper + tolerance, axis=1)
    c, d = c[in_bounds], d[in_bounds]
    own_side = _cross(b - a, c - a) * _cross(b - a, d - a)
    other_side = _cross(d - c, a - c) * _cross(d - c, b - c)
    return bool(np.any((own_side <= tolerance ** 4) & (other_side <= tolerance ** 4)))


def _section_profile(loops, open_edges, tolerance):
    centered = [loop for loop in loops if _contains(loop, np.zeros(2), tolerance)]
    if len(centered) != 1:
        return None, None, f"Expected one closed contour around section origin, found {len(centered)}"
    primary = centered[0]
    edges = np.stack((primary, np.roll(primary, -1, axis=0)), axis=1)
    extras = [np.stack((loop, np.roll(loop, -1, axis=0)), axis=1) for loop in loops if loop is not primary]
    others = np.concatenate([open_edges, *extras])
    for index, (a, b) in enumerate(edges):
        end = -1 if index == 0 else len(edges)
        if _segments_intersect(a, b, edges[index + 2:end], tolerance):
            return None, None, "Section contour self-intersects"
        if _segments_intersect(a, b, others, tolerance):
            return None, None, "Section contour intersects another contour or open edge"
    if any(_contains(primary, other[0, 0], tolerance) for other in extras):
        return None, None, "Section contour encloses an additional boundary"
    if any(_contains(primary, edge[0], tolerance) for edge in open_edges):
        return None, None, "Section contour encloses an open edge"

    thicknesses = []
    for angle in np.linspace(0, math.pi, 180, endpoint=False):
        intersections = _line_crossings(primary, angle)
        near = intersections[intersections < -tolerance]
        far = intersections[intersections > tolerance]
        if not len(near) or not len(far) or np.any(np.abs(intersections) <= tolerance):
            return None, None, "Section origin lacks an unbroken chord through the contour"
        thicknesses.append(float(far.min() - near.max()))
    area = abs(float(_cross(edges[:, 0], edges[:, 1]).sum())) / 2
    return area, min(thicknesses), None


def _shell_section_profile(loops, open_edges, tolerance):
    """Measure the occupied union of an incumbent assembled from rigid shells."""
    extents = []
    for angle in np.linspace(0, math.pi, 180, endpoint=False):
        intervals = []
        for loop in loops:
            crossings = sorted(_line_crossings(loop, angle))
            intervals.extend(zip(crossings[::2], crossings[1::2]))
        merged = []
        for low, high in sorted(intervals):
            if merged and low <= merged[-1][1] + tolerance:
                merged[-1] = (merged[-1][0], max(merged[-1][1], high))
            else:
                merged.append((low, high))
        center = next((pair for pair in merged if pair[0] < -tolerance and pair[1] > tolerance), None)
        if center is None:
            return None, None, "No closed shell interval contains the section origin"
        extents.append(center)
    # Only the central occupied region is comparable to the new skin. Details
    # elsewhere in the cut may have boundaries of their own.
    thickness = min(high - low for low, high in extents)
    area = math.pi / (2 * len(extents)) * sum(low * low + high * high for low, high in extents)
    return area, thickness, None


def measure_sections(vertices, triangles, sections, *, shell_union=False):
    """Measure closed section area and sampled minimum centerline thickness.

    Sections map names to ``origin``, ``normal`` and in-plane ``direction``.
    Coordinates and lengths use the mesh's units. Minimum thickness samples
    center chords on the supplied direction and every degree around the origin.
    """
    vertices = np.asarray(vertices, dtype=float)
    triangles = np.asarray(triangles, dtype=int)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("Expected finite 3D vertices")
    if (triangles.ndim != 2 or triangles.shape[1] != 3 or not len(triangles)
            or triangles.min() < 0 or triangles.max() >= len(vertices)):
        raise ValueError("Expected nonempty indexed triangles")

    tolerance = max(float(np.ptp(vertices, axis=0).max()) * 1e-8, 1e-12)
    result = {}
    for name, section in sections.items():
        origin = _point(section["origin"], 3)
        normal = _unit(_point(section["normal"], 3))
        direction = _point(section["direction"], 3)
        x = _unit(direction - normal * (normal @ direction))
        basis = np.array([x, np.cross(normal, x)])
        segments, offset = _section_segments(vertices, triangles, origin, normal, basis, 4 * tolerance)
        loops, open_edges = _section_curves(segments, tolerance)
        profile = _shell_section_profile if shell_union else _section_profile
        area, thickness, defect = profile(loops, open_edges, tolerance)
        result[name] = {"continuous": defect is None, "area": area, "min_thickness": thickness,
                        "defect": defect, "plane_offset": offset, "closed_contours": len(loops),
                        "open_edges": len(open_edges)}
    return result


def measure_evaluated_sections(objects, sections, depsgraph=None, *, shell_union=False, bone_groups=None):
    """Read Blender modifiers, armature deformation and transforms in world space."""
    if depsgraph is None:
        import bpy

        depsgraph = bpy.context.evaluated_depsgraph_get()
    coordinates, indices, owners = [], [], []
    vertex_offset = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
            triangles = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
            mesh.vertices.foreach_get("co", vertices)
            mesh.loop_triangles.foreach_get("vertices", triangles)
            matrix = np.array(evaluated.matrix_world, dtype=float)
            coordinates.append(vertices.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3])
            indices.append(triangles.reshape(-1, 3) + vertex_offset)
            if bone_groups:
                owners.extend(obj.vertex_groups[max(v.groups, key=lambda group: group.weight).group].name
                              if v.groups else "" for v in mesh.vertices)
            vertex_offset += len(mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    if not indices:
        raise ValueError("Expected at least one evaluated mesh")
    vertices = np.concatenate(coordinates)
    triangles = np.concatenate(indices)
    if not bone_groups:
        return measure_sections(vertices, triangles, sections, shell_union=shell_union)
    result = {}
    for name, spec in sections.items():
        groups = bone_groups.get(name)
        selected = triangles
        if groups:
            permitted = np.isin(owners, list(groups))
            selected = triangles[np.all(permitted[triangles], axis=1)]
        if len(selected):
            result.update(measure_sections(vertices, selected, {name: spec}, shell_union=shell_union))
    return result


def evaluate_section_gate(rest, posed, crease_sections, midspan_sections, *, incumbent=None,
                          min_crease_retention=.60, max_midspan_area_change=.05):
    """Gate one pose against registered rest stations and a paired incumbent pose."""
    if not (crease_sections or midspan_sections):
        raise ValueError("Specify at least one crease or midspan section")
    if not 0 < min_crease_retention <= 1 or not 0 <= max_midspan_area_change < 1:
        raise ValueError("Invalid crease or midspan threshold")
    failures, pending, values = [], [], {}
    for names, quantity in ((crease_sections, "min_thickness"), (midspan_sections, "area")):
        for name in names:
            rest_section, posed_section = rest.get(name), posed.get(name)
            for label, section in (("rest", rest_section), ("posed", posed_section)):
                if section is None:
                    failures.append(f"{name}: {label} section is missing")
                elif not section["continuous"]:
                    failures.append(f"{name}: {label} section is discontinuous: {section['defect']}")
            if not all(section and section["continuous"] for section in (rest_section, posed_section)):
                continue
            original, current = rest_section[quantity], posed_section[quantity]
            if any(value is None or not math.isfinite(value) or value <= 0 for value in (original, current)):
                failures.append(f"{name}: expected positive, finite {quantity} in rest and posed sections")
                continue
            retention = current / original
            values[name] = {"quantity": quantity, "rest": original, "posed": current, "retention": retention}
            if quantity == "area":
                if abs(retention - 1) > max_midspan_area_change + 1e-12:
                    failures.append(f"{name}: midspan area retention {retention:.2%} is outside "
                                    f"{1 - max_midspan_area_change:.2%}–{1 + max_midspan_area_change:.2%}")
                continue
            if retention < min_crease_retention - 1e-12:
                failures.append(f"{name}: crease thickness retention {retention:.2%} is below "
                                f"{min_crease_retention:.2%}")
            baseline = (incumbent or {}).get(name, {}).get(quantity)
            values[name]["incumbent"] = baseline
            if baseline is None:
                pending.append(f"{name}: paired incumbent crease thickness is missing")
            elif not math.isfinite(baseline) or baseline < 0:
                pending.append(f"{name}: paired incumbent crease thickness is invalid")
            elif current < baseline - abs(baseline) * 1e-12:
                failures.append(f"{name}: crease thickness {current:.6g} regresses from incumbent {baseline:.6g}")
    return {"status": _status(failures, pending), "sections": values, "failures": failures, "pending": pending}


def main(argv=None):
    """Read a held-out JSON specification and emit an acceptance report."""
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("spec", type=Path, help="JSON with reference, candidate, incumbent and review")
    parser.add_argument("--out", type=Path, help="write report JSON to this file instead of standard output")
    args = parser.parse_args(argv)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))

    def resolve(views):
        return {name: {**view, "mask": args.spec.parent / view["mask"]} if view.get("mask") else view
                for name, view in (views or {}).items()}

    result = compare_held_out(resolve(spec["reference"]), resolve(spec["candidate"]),
                              resolve(spec.get("incumbent")), spec.get("review"),
                              require_incumbent=spec.get("require_incumbent", True))
    report = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return {"passed": 0, "failed": 1, "pending": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
