"""Run with standard unittest discovery or Blender -b -P on this file."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from polyforge.asset_validation import (compare_held_out, evaluate_section_gate, main,
                                        measure_evaluated_sections, measure_sections)


def extruded_profile(profiles, *, open_side=False):
    """Build a capped, triangulated profile with one ring at each integer height."""
    count = len(profiles[0])
    vertices = [(x, y, z) for z, profile in enumerate(profiles) for x, y in profile]
    triangles = []
    for level in range(len(profiles) - 1):
        for side in range(1 if open_side else 0, count):
            a = level * count + side
            b = level * count + (side + 1) % count
            triangles.extend(((a, b, a + count), (b, b + count, a + count)))
    top = (len(profiles) - 1) * count
    for side in range(1, count - 1):
        triangles.extend(((0, side + 1, side), (top, top + side, top + side + 1)))
    return vertices, triangles


def rectangle(half_x=1, half_y=1):
    return [(-half_x, -half_y), (half_x, -half_y), (half_x, half_y), (-half_x, half_y)]


def station(height, y=0):
    return {"origin": (0, y, height), "normal": (0, 0, 1), "direction": (1, 0, 0)}


class HeldOutGateTests(unittest.TestCase):
    def setUp(self):
        mask = np.zeros((40, 50), dtype=bool)
        mask[10:30, 5:45] = True
        self.reference = {"front": {"mask": mask, "landmarks": {"left": (5, 15), "right": (44, 15)}}}
        # Synthetic reviewer data exercises the gate without certifying any asset.
        self.fixture_review = {"independent": True, "reviewer": "fixture", "reviewed_views": ["front"],
                               "findings": []}

    def test_fails_valid_unrecognizable_silhouette(self):
        # A connected, filled silhouette from a closed solid could have the
        # wrong shape and dimensions while remaining geometrically valid.
        wrong_shape = np.zeros((40, 50), dtype=bool)
        wrong_shape[5:35, 18:32] = True
        candidate = {"front": {"mask": wrong_shape, "landmarks": {"left": (18, 15), "right": (31, 15)}}}
        report = compare_held_out(self.reference, candidate, self.reference, self.fixture_review)
        self.assertEqual(report["status"], "failed")
        self.assertAlmostEqual(report["views"]["front"]["candidate"]["mean_landmark_error"], .325)
        self.assertTrue(any("silhouette IoU" in entry for entry in report["failures"]))

    def test_fails_regression_above_absolute_iou_threshold(self):
        reference = self.reference["front"]
        smaller = reference["mask"].copy()
        smaller[:, 5:8] = False
        candidate = {"front": {**reference, "mask": smaller}}
        report = compare_held_out(self.reference, candidate, self.reference, self.fixture_review)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(len(report["failures"]), 1)
        self.assertIn("regresses from incumbent", report["failures"][0])

    def test_requires_independent_review_and_flags_major_findings(self):
        without_review = compare_held_out(self.reference, self.reference, self.reference)
        without_incumbent = compare_held_out(self.reference, self.reference, review=self.fixture_review)
        self.assertEqual(without_review["status"], "pending")
        self.assertEqual(without_incumbent["status"], "pending")
        novel = compare_held_out(self.reference, self.reference, review=self.fixture_review,
                                  require_incumbent=False)
        self.assertEqual(novel["status"], "passed")
        report = compare_held_out(self.reference, self.reference, self.reference, self.fixture_review)
        self.assertEqual(report["status"], "passed")
        major = {"view": "front", "severity": "major", "evidence": "Required face relief is missing"}
        review = {**self.fixture_review, "findings": [major]}
        report = compare_held_out(self.reference, self.reference, self.reference, review)
        self.assertEqual(report["status"], "failed")
        self.assertIn(major["evidence"], report["failures"][0])

    def test_cropped_view_scores_only_visible_landmarks(self):
        reference = {"front": {"landmarks": {"brow": (12, 8)}, "landmark_scale": 40}}
        candidate = {"front": {"landmarks": {"brow": (14, 8)}}}
        report = compare_held_out(reference, candidate, review=self.fixture_review)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["views"]["front"]["candidate"]["mean_landmark_error"], .05)
        report = compare_held_out(reference, {}, review=self.fixture_review)
        self.assertEqual(report["status"], "failed")
        self.assertIn("brow", report["failures"][0])

    def test_cli_reads_masks_relative_to_specification(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = self.reference["front"]
            alpha = reference["mask"].astype(np.uint8) * 255
            rgb = np.full((*alpha.shape, 3), 120, dtype=np.uint8)
            Image.fromarray(np.dstack((rgb, alpha))).save(root / "mask.png")
            views = {"front": {"mask": "mask.png", "landmarks": reference["landmarks"]}}
            spec = {"reference": views, "candidate": views, "incumbent": views, "review": self.fixture_review}
            (root / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
            report = root / "results" / "report.json"
            exit_code = main([str(root / "spec.json"), "--out", str(report)])
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["status"], "passed")


class SectionGateTests(unittest.TestCase):
    sections = {"crease": station(1), "midspan": station(3)}

    def setUp(self):
        self.rest = measure_sections(*extruded_profile([rectangle()] * 5), self.sections)

    def evaluate(self, posed, incumbent=None):
        return evaluate_section_gate(self.rest, posed, ("crease",), ("midspan",), incumbent=incumbent)

    def test_accepts_continuous_sections_and_coplanar_rings(self):
        self.assertAlmostEqual(self.rest["crease"]["min_thickness"], 2)
        self.assertAlmostEqual(self.rest["crease"]["area"], 4)
        self.assertGreater(self.rest["crease"]["plane_offset"], 0)
        self.assertEqual(self.evaluate(self.rest)["status"], "pending")
        self.assertEqual(self.evaluate(self.rest, self.rest)["status"], "passed")

    def test_rejects_thin_closed_crease_and_shrunken_midspan(self):
        mesh = extruded_profile([rectangle(), rectangle(.5), rectangle(), rectangle(.9), rectangle()])
        posed = measure_sections(*mesh, self.sections)
        self.assertTrue(all(section["continuous"] for section in posed.values()))
        report = self.evaluate(posed, self.rest)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("crease thickness retention" in failure for failure in report["failures"]))
        self.assertTrue(any("midspan area retention" in failure for failure in report["failures"]))
        self.assertTrue(any("regresses from incumbent" in failure for failure in report["failures"]))

    def test_rejects_open_or_self_intersecting_section(self):
        open_mesh = extruded_profile([rectangle()] * 5, open_side=True)
        posed = measure_sections(*open_mesh, self.sections)
        self.assertFalse(posed["crease"]["continuous"])
        self.assertGreater(posed["crease"]["open_edges"], 0)
        self.assertEqual(self.evaluate(posed, self.rest)["status"], "failed")
        crossed = [(-3, -2), (3, 2), (-3, 2), (3, -2)]
        section = measure_sections(*extruded_profile([crossed] * 3), {"crease": station(.33, 1)})["crease"]
        self.assertFalse(section["continuous"])
        self.assertIn("self-intersects", section["defect"])

    def test_compares_incumbent_overlapping_shell_occupancy(self):
        vertices, faces = extruded_profile([rectangle()] * 5)
        shifted = [(x + .75, y, z) for x, y, z in vertices]
        assembly = [*vertices, *shifted], [*faces, *(tuple(i + len(vertices) for i in f) for f in faces)]
        self.assertFalse(measure_sections(*assembly, self.sections)["crease"]["continuous"])
        result = measure_sections(*assembly, self.sections, shell_union=True)["crease"]
        self.assertTrue(result["continuous"], result)
        self.assertAlmostEqual(result["min_thickness"], 2)

    def test_reads_evaluated_blender_modifier_in_world_space(self):
        try:
            import bpy
        except ImportError:
            self.skipTest("Run with Blender to check evaluated mesh data")

        vertices, faces = extruded_profile([rectangle()] * 3)
        mesh = bpy.data.meshes.new("Section gate fixture")
        mesh.from_pydata(vertices, [], faces)
        obj = bpy.data.objects.new("Evaluated section fixture", mesh)
        bpy.context.scene.collection.objects.link(obj)
        try:
            obj.location = (2, 3, 4)
            obj.scale = (1, 2, 1)
            modifier = obj.modifiers.new("Evaluated copy", "ARRAY")
            modifier.use_relative_offset = False
            modifier.use_constant_offset = True
            modifier.constant_offset_displace = (4, 0, 0)
            section = {**station(5), "origin": (6, 3, 5)}
            result = measure_evaluated_sections([obj], {"world": section})["world"]
            self.assertTrue(result["continuous"], result)
            self.assertAlmostEqual(result["area"], 8)
            self.assertAlmostEqual(result["min_thickness"], 2)
        finally:
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(mesh)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
