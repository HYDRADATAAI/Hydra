from __future__ import annotations

import copy
import unittest

from validate_constraint_second_slice_batch018_first_population import (
    Batch018ValidationError,
    load_documents,
    validate_documents,
)


class Batch018AdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.docs = load_documents()

    def mutated(self):
        return copy.deepcopy(self.docs)

    def assertRejected(self, docs, pattern: str) -> None:
        with self.assertRaisesRegex(Batch018ValidationError, pattern):
            validate_documents(docs)

    def test_baseline_passes(self):
        result = validate_documents(self.docs)
        self.assertEqual("PASS_BATCH018_REVIEWED_SHADOW_FIRST_POPULATION", result["status"])
        self.assertEqual(24, result["edge_count"])
        self.assertEqual(0, result["required_cases_covered"])

    def test_source_cannot_fabricate_available_at(self):
        docs = self.mutated()
        docs["sources"]["sources"][0]["available_at"] = "2023-11-13T00:00:00Z"
        self.assertRejected(docs, "fabricated available_at")

    def test_source_cannot_claim_t1_materialization_without_custody(self):
        docs = self.mutated()
        docs["sources"]["sources"][0]["t1_materialized"] = True
        self.assertRejected(docs, "T1 materialization was claimed")

    def test_population_cannot_enter_ordinary_t3(self):
        docs = self.mutated()
        docs["population"]["ordinary_t3_eligible"] = True
        self.assertRejected(docs, "ordinary T3 eligibility")

    def test_supported_edge_requires_evidence(self):
        docs = self.mutated()
        docs["graph"]["edges"][0]["evidence_ids"] = []
        self.assertRejected(docs, "supported edge has no evidence")

    def test_samsung_development_cannot_be_promoted_to_volume(self):
        docs = self.mutated()
        edge = next(row for row in docs["graph"]["edges"] if row["edge_id"] == "S2-E006")
        edge["relation"] = "VOLUME_PRODUCES"
        self.assertRejected(docs, "development was promoted to production")

    def test_samsung_cannot_be_claimed_nvidia_qualified(self):
        docs = self.mutated()
        edge = next(row for row in docs["graph"]["edges"] if row["edge_id"] == "S2-E006")
        edge["qualification_state"] = "NVIDIA_QUALIFIED"
        self.assertRejected(docs, "qualification state was promoted")

    def test_tsmc_arizona_capacity_cannot_be_invented(self):
        docs = self.mutated()
        docs["population"]["facilities"][0]["available_capacity"] = 50000
        self.assertRejected(docs, "fabricated numeric available_capacity")

    def test_required_case_cannot_be_marked_covered(self):
        docs = self.mutated()
        docs["required_cases"]["covered_case_count"] = 1
        docs["required_cases"]["cases"][0]["status"] = "COVERED"
        self.assertRejected(docs, "falsely claimed case coverage")

    def test_status_cannot_promote_replay(self):
        docs = self.mutated()
        docs["status"]["results"]["HISTORICAL_REPLAY"] = "READY"
        self.assertRejected(docs, "historical replay escaped blocking gate")

    def test_master_cannot_authorize_full_run(self):
        docs = self.mutated()
        docs["master"]["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"] = "YES"
        docs["master"]["first_serious_constraint_run"] = "ALLOWED"
        self.assertRejected(docs, "first serious Constraint run escaped BLOCKED")

    def test_material_population_cannot_appear_without_batch018_evidence(self):
        docs = self.mutated()
        docs["population"]["material_records"] = [{
            "entity_id": "S2-MAT-INVENTED",
            "entity_type": "MATERIAL",
            "evidence_ids": ["EV-S2-NVIDIA-H200-HBM3E"],
            "source_version_ids": [],
            "available_at": None,
            "quarantine_state": "SHADOW_NOT_T1_MATERIALIZED",
        }]
        self.assertRejected(docs, "unsupported critical-material record")


if __name__ == "__main__":
    unittest.main()
