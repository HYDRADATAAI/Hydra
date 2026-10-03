#!/usr/bin/env python3
"""Hostile mutations for Batch020 policy/substitution/outcome case governance."""

from __future__ import annotations
import copy
import unittest

from validate_constraint_second_slice_batch020_policy_outcomes_cases import (
    ValidationFailure,
    load_documents,
    validate_documents,
)

class Batch020AdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_documents()

    def docs(self):
        return copy.deepcopy(self.base)

    def reject(self, docs, pattern: str):
        with self.assertRaisesRegex(ValidationFailure, pattern):
            validate_documents(docs)

    def test_baseline(self):
        r = validate_documents(self.base)
        self.assertEqual(5, r["covered"])
        self.assertEqual(1, r["false_beneficiaries"])
        self.assertEqual(0, r["qualified_substitutions"])

    def test_policy_effective_and_compliance_dates_cannot_collapse(self):
        d = self.docs()
        d["policy"]["events"][0]["hbm_compliance_at"] = "2024-12-02"
        self.reject(d, "HBM compliance date drift")

    def test_policy_known_at_cannot_be_backdated_to_effective_at(self):
        d = self.docs()
        d["policy"]["events"][0]["known_at"] = "2024-12-02"
        self.reject(d, "known/observed time drift")

    def test_policy_cannot_become_replay_eligible(self):
        d = self.docs()
        d["policy"]["events"][0]["ordinary_replay_eligible"] = True
        self.reject(d, "falsely ordinary-replay eligible")

    def test_original_arizona_target_cannot_be_rewritten(self):
        d = self.docs()
        d["ramp"]["timeline"][0]["target_production_period"] = "2025"
        self.reject(d, "original Arizona 2024 target rewritten")

    def test_original_20k_capacity_cannot_be_carried_into_actual(self):
        d = self.docs()
        actual = next(r for r in d["ramp"]["timeline"] if r["state_id"] == "ARIZONA-RAMP-2024-ACTUAL")
        actual["realized_capacity_value"] = 20000
        self.reject(d, "smuggled into realized capacity")

    def test_delay_state_cannot_be_deleted(self):
        d = self.docs()
        d["ramp"]["timeline"] = [d["ramp"]["timeline"][0], d["ramp"]["timeline"][2]]
        self.reject(d, "timeline count drift")

    def test_samsung_substitution_cannot_be_qualified(self):
        d = self.docs()
        d["substitution"]["evaluations"][0]["substitution_state"] = "QUALIFIED"
        d["substitution"]["qualified_substitution_count"] = 1
        self.reject(d, "substitution count/qualification drift")

    def test_samsung_spare_capacity_cannot_be_invented(self):
        d = self.docs()
        d["substitution"]["evaluations"][0]["unbooked_addressable_capacity_state"] = "PROVEN"
        self.reject(d, "spare capacity invented")

    def test_false_beneficiary_cannot_be_promoted(self):
        d = self.docs()
        d["beneficiary"]["relationships"][0]["eligibility_state"] = "QUALIFIED"
        d["beneficiary"]["qualified_relationship_count"] = 1
        self.reject(d, "qualified beneficiary falsely added")

    def test_false_beneficiary_capacity_lineage_cannot_be_invented(self):
        d = self.docs()
        d["beneficiary"]["relationships"][0]["evidence_lineage"]["capacity_or_availability"] = [
            "EV-SEMI-B020-SAMSUNG-HBM3E8H-MASS-PRODUCTION"
        ]
        self.reject(d, "capacity/availability invented")

    def test_case_10_cannot_be_marked_covered(self):
        d = self.docs()
        d["cases"]["covered_case_count_after"] = 6
        d["cases"]["updates"].append({
            "case_id":10,
            "name":"SUBSTITUTION",
            "predecessor_status":"GAP",
            "successor_status":"COVERED_REVIEWED_SHADOW_REAL_PRIMARY_BOUNDED",
        })
        self.reject(d, "case coverage drift")

    def test_case_12_cannot_be_marked_covered(self):
        d = self.docs()
        d["cases"]["remaining_gap_case_ids"].remove(12)
        self.reject(d, "remaining case gaps drift")

    def test_master_cannot_promote_replay(self):
        d = self.docs()
        d["master"]["readiness"]["SECOND_SLICE_REPLAY_READY"]["status"] = "YES"
        self.reject(d, "replay falsely ready")

    def test_manifest_cannot_promote_run(self):
        d = self.docs()
        d["manifest"]["expected"]["first_semiconductor_run"] = "READY"
        self.reject(d, "manifest run promotion")

if __name__ == "__main__":
    unittest.main()
