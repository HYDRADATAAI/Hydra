#!/usr/bin/env python3
"""Hostile mutations for Batch019 facility/material/equipment/qualification governance."""

from __future__ import annotations

import copy
import unittest

from validate_constraint_second_slice_batch019_facility_material_equipment import (
    ValidationFailure,
    load_documents,
    validate_documents,
)


class Batch019AdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = load_documents()

    def docs(self):
        return copy.deepcopy(self.base)

    def reject(self, docs, pattern: str) -> None:
        with self.assertRaisesRegex(ValidationFailure, pattern):
            validate_documents(docs)

    def test_baseline(self):
        result = validate_documents(self.base)
        self.assertEqual(3, result["facilities_added"])
        self.assertEqual(6, result["materials_added"])
        self.assertEqual(2, result["cases_covered"])

    def test_ap6_design_capacity_cannot_become_available_capacity(self):
        d = self.docs()
        d["population"]["facilities_added"][0]["available_capacity"] = 1000001
        self.reject(d, "AP6 design capacity promoted")

    def test_amkor_cleanroom_cannot_become_production_capacity(self):
        d = self.docs()
        fac = next(r for r in d["population"]["facilities_added"] if r["facility_id"] == "FAC-SEMI-AMKOR-VIETNAM-BAC-NINH")
        fac["production_capacity"] = 200000
        self.reject(d, "cleanroom area fabricated into production capacity")

    def test_raw_silica_cannot_become_semiconductor_grade(self):
        d = self.docs()
        mat = next(r for r in d["population"]["materials_added"] if r["material_id"] == "MAT-SILICA-QUARTZITE")
        mat["material_grade"] = "SEMICONDUCTOR_GRADE"
        self.reject(d, "raw silica promoted")

    def test_broad_china_silicon_share_cannot_become_semiconductor_grade_share(self):
        d = self.docs()
        edge = next(r for r in d["graph"]["edges_added"] if r["edge_id"] == "SEMI-B019-E025")
        edge["semantic_limit"] = "SEMICONDUCTOR_GRADE_SHARE"
        self.reject(d, "semiconductor-grade concentration")

    def test_partial_asml_policy_cannot_become_complete_cutoff(self):
        d = self.docs()
        edge = next(r for r in d["graph"]["edges_added"] if r["edge_id"] == "SEMI-B019-E016")
        edge["semantic_limit"] = "COMPLETE_CUTOFF"
        self.reject(d, "complete cutoff")

    def test_unknown_asml_effective_at_cannot_be_fabricated(self):
        d = self.docs()
        d["population"]["policy_events_added"][0]["effective_at"] = "2024-01-01T00:00:00Z"
        self.reject(d, "exact effective_at fabricated")

    def test_qualification_duration_cannot_be_fabricated(self):
        d = self.docs()
        q = next(r for r in d["population"]["qualification_observations"] if r["observation_id"] == "QUALOBS-NVIDIA-NEW-PRODUCT-2024-001")
        q["qualification_duration_days"] = 90
        self.reject(d, "duration fabricated numerically")

    def test_arizona_plan_cannot_be_rewritten_by_later_outcome(self):
        d = self.docs()
        d["outcome"]["outcomes"][0]["predecessor_plan"]["target_period"] = "2024-Q4"
        self.reject(d, "predecessor plan rewritten")

    def test_current_review_outcome_cannot_be_replay_eligible(self):
        d = self.docs()
        d["outcome"]["outcomes"][0]["historical_replay_eligible"] = True
        self.reject(d, "falsely replay eligible")

    def test_case_progress_cannot_be_claimed_as_coverage(self):
        d = self.docs()
        d["cases"]["covered_case_count_after"] = 6
        self.reject(d, "coverage falsely advanced")

    def test_master_cannot_promote_replay(self):
        d = self.docs()
        d["master"]["readiness"]["SECOND_SLICE_REPLAY_READY"]["status"] = "YES"
        self.reject(d, "replay falsely ready")

    def test_supported_edge_cannot_lose_evidence(self):
        d = self.docs()
        d["graph"]["edges_added"][0]["evidence_ids"] = []
        self.reject(d, "evidence missing")

    def test_source_cannot_become_raw_lineage_eligible(self):
        d = self.docs()
        d["sources"]["sources"][0]["ordinary_raw_lineage_eligible"] = True
        self.reject(d, "ordinary raw lineage falsely enabled")

    def test_manifest_cannot_claim_run_ready(self):
        d = self.docs()
        d["manifest"]["expected"]["first_semiconductor_run"] = "READY"
        self.reject(d, "manifest run gate drift")


if __name__ == "__main__":
    unittest.main()
