"""Regression checks for the offline evidence ledger."""

from copy import deepcopy
from unittest import TestCase, mock

from research import build_library, coverage
from polyforge import qualification


class CoverageTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = coverage.load(coverage.RESEARCH / "coverage_plan.json")
        cls.ledger = coverage.load(coverage.RESEARCH / "observations.json")
        cls.spec = build_library.make_spec()
        cls.species = coverage.load(coverage.RESEARCH / "index.json")["species"]

    def report(self, ledger):
        with mock.patch.object(coverage, "load", side_effect=[self.plan, ledger]):
            return coverage.build_report(self.spec, self.species)

    def test_candidates_and_merges_are_not_active(self):
        report, errors = self.report(self.ledger)
        self.assertEqual(errors, [])
        active = set(report["active_family_audit"])
        self.assertEqual(report["active_families"], len(active))
        self.assertTrue(report["pending_candidates"])
        self.assertTrue(report["merge_dispositions"])
        self.assertTrue(active.isdisjoint(report["pending_candidates"]))
        self.assertTrue(active.isdisjoint(report["merge_dispositions"]))
        self.assertEqual(report["active_by_origin"]["derived"], len(self.spec["parts"]))
        self.assertEqual(report["remaining_to_target"], max(0, report["target_families"] - len(active)))

    def test_every_candidate_is_accounted_for(self):
        dispositions = qualification.records()
        nominated = {p["id"] for p in self.ledger["proposals"] if p["status"] == "candidate"}
        self.assertEqual(set(dispositions), nominated)
        report, errors = self.report(self.ledger)
        self.assertEqual(errors, [])
        self.assertEqual(sum(report["qualification_counts"].values()), len(nominated))
        self.assertEqual(set(report["qualification_work"]),
                         {key for key, row in dispositions.items() if row["status"] == "draft"})

    def test_part_gaps_reference_the_catalog_without_counting_as_families(self):
        report, errors = self.report(self.ledger)
        self.assertEqual(errors, [])
        self.assertEqual(report["part_gaps"], self.plan["part_gaps"])
        without_gaps = {**self.plan, "part_gaps": []}
        with mock.patch.object(coverage, "load", side_effect=[without_gaps, self.ledger]):
            baseline, errors = coverage.build_report(self.spec, self.species)
        self.assertEqual(errors, [])
        self.assertEqual(report["active_families"], baseline["active_families"])
        self.assertEqual(report["pending_candidates"], baseline["pending_candidates"])
        queued = [key for batch in report["part_gap_workstreams"].values() for key in batch]
        self.assertEqual(len(queued), report["queued_part_gaps"])
        self.assertEqual(len(queued), len(set(queued)))
        self.assertEqual(report["planning_total"] - baseline["planning_total"], len(queued))

        invalid = deepcopy(self.plan)
        invalid["part_gaps"][0]["compare_to"] = ["missing_part"]
        with mock.patch.object(coverage, "load", side_effect=[invalid, self.ledger]):
            report, errors = coverage.build_report(self.spec, self.species)
        self.assertIsNone(report)
        self.assertIn("hinged_gill_cover: duplicate or unknown compare_to", errors)

    def test_adopted_gap_stays_in_history_without_reentering_queue(self):
        adopted = {**self.plan["part_gaps"][0], "id": "urchin_test"}
        plan = {**self.plan, "part_gaps": [adopted]}
        with mock.patch.object(coverage, "load", side_effect=[plan, self.ledger]):
            report, errors = coverage.build_report(self.spec, self.species)
        self.assertEqual(errors, [])
        self.assertEqual(report["part_gaps"], [adopted])
        self.assertEqual(report["queued_part_gaps"], 0)
        self.assertEqual(report["part_gap_workstreams"], {})

    def test_remaining_work_distinguishes_failures_and_missing_evidence(self):
        record = {"gates": {"structure": "passed", "fit": "pending", "motion": "not_applicable",
                            "likeness": "failed"}}
        self.assertEqual(qualification.remaining_work(record),
                         {"needs_revision": ["likeness"], "needs_verification": ["fit"]})

    def test_structure_does_not_publish_without_likeness(self):
        record = {"status": "qualified", "gates": dict.fromkeys(qualification.GATES, "passed"),
                  "references": ["fixture"], "review": {"reviewer": "fixture", "independent": True,
                                                       "major_findings": 0, "evidence": "fixture"}}
        self.assertFalse(qualification.approved(record))
        record["likeness"] = {"status": "passed", "views": {"side": {"candidate": {
            "silhouette_iou": .86, "mean_landmark_error": .04}}}}
        self.assertTrue(qualification.approved(record))
        record["likeness"]["views"]["front"] = {"candidate": {"silhouette_iou": .91}}
        self.assertTrue(qualification.approved(record))
        side = record["likeness"]["views"].pop("side")
        self.assertFalse(qualification.approved(record))
        record["likeness"]["views"]["side"] = side
        record["gates"]["motion"] = "pending"
        self.assertFalse(qualification.approved(record))
        record["gates"]["motion"] = "not_applicable"
        self.assertTrue(qualification.approved(record))
        record["review"]["major_findings"] = 1
        self.assertFalse(qualification.approved(record))

    def test_bad_evidence_fails(self):
        ledger = deepcopy(self.ledger)
        ledger["sources"][0]["rights_url"] = ""
        obs = ledger["observations"][0]
        obs["landmarks"].pop("root")
        obs["landmark_basis"] = "measured"
        obs["inference"]["confidence"] = "high"
        obs["sources"] = ["absent_source"]
        report, errors = self.report(ledger)
        self.assertIsNone(report)
        for message in ("rights URL", "missing root", "supporting measurements",
                        "unknown sources", "geometry confidence"):
            self.assertTrue(any(message in error for error in errors), errors)

    def test_double_counting_is_rejected(self):
        ledger = deepcopy(self.ledger)
        proposal = deepcopy(ledger["proposals"][0])
        proposal["id"] = "duplicate_family"
        ledger["proposals"].append(proposal)
        report, errors = self.report(ledger)
        self.assertIsNone(report)
        self.assertTrue(any("counted in multiple proposals" in error for error in errors), errors)

    def test_a_merge_cannot_point_to_a_merge(self):
        ledger = deepcopy(self.ledger)
        merges = [row for row in ledger["proposals"] if row["status"] == "merge"]
        merges[0]["merge_into"] = merges[-1]["id"]
        report, errors = self.report(ledger)
        self.assertIsNone(report)
        self.assertTrue(any("merge_into must name" in error for error in errors), errors)
