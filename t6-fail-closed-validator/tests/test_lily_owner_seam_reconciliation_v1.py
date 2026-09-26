from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from hydra_t6_failclosed.owner_seam_conformance import (
    OwnerSeamConformanceError,
    validate_owner_seams,
)


ROOT = Path(__file__).resolve().parents[2]
SLICE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"

FILES = {
    "claims": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_CLAIM_REGISTRY_V001_20260925.json",
    "candidates": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_T5_CANDIDATE_PROPOSALS_V001_20260925.json",
    "beneficiaries": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BENEFICIARY_EVALUATIONS_V001_20260925.json",
    "overlay": SLICE / "HYDRA_CONSTRAINT_LILY_OWNER_SEAM_RECONCILIATION_T5_CANDIDATE_TEMPORAL_IDENTITY_OVERLAY_V001_20260926.json",
    "batch13": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_AI_DATA_CENTER_POWER_INFRASTRUCTURE_EATON_TRANSFORMER_PREQUALIFICATION_OVERLAY_V001_20260925.json",
    "batch14": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class LilyOwnerSeamReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = {name: load(path) for name, path in FILES.items()}

    def validate(self, docs=None):
        source = self.docs if docs is None else docs
        return validate_owner_seams(
            claims=source["claims"],
            candidates=source["candidates"],
            beneficiaries=source["beneficiaries"],
            overlay=source["overlay"],
            batch13_beneficiary_overlay=source["batch13"],
            batch14_strict_gate=source["batch14"],
        )

    def mutated(self):
        return copy.deepcopy(self.docs)

    def test_committed_owner_seams_pass_fail_closed(self):
        result = self.validate()
        self.assertEqual("PASS_FAIL_CLOSED_OWNER_SEAMS", result["status"])
        self.assertEqual(10, result["claim_count"])
        self.assertEqual(3, result["candidate_count"])
        self.assertEqual(4, result["beneficiary_relationship_count"])
        self.assertEqual(0, result["qualified_beneficiary_count"])
        self.assertEqual(0, result["canonical_constraint_count"])

    def test_overlay_pins_exact_unchanged_batch010_candidate_blob(self):
        pin = self.docs["overlay"]["predecessor"]["git_blob_sha"]
        self.assertEqual(pin, git_blob_sha(FILES["candidates"]))
        self.assertEqual("NONE", self.docs["overlay"]["predecessor"]["mutation"])

    def test_t5_cannot_mint_canonical_constraint_id(self):
        docs = self.mutated()
        docs["candidates"]["candidates"][0]["canonical_constraint_id"] = "constraint:smuggled"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "canonical constraint ID"):
            self.validate(docs)

    def test_successor_overlay_cannot_backdate_candidate_availability(self):
        docs = self.mutated()
        docs["overlay"]["candidates"][1]["available_at"] = "2026-09-25T00:00:00Z"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "backdates availability"):
            self.validate(docs)

    def test_missing_formation_confidence_stays_not_evaluated(self):
        docs = self.mutated()
        docs["overlay"]["candidates"][0]["formation_confidence_state"] = "HIGH"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "NOT_EVALUATED"):
            self.validate(docs)

    def test_overlay_cannot_invent_effective_interval(self):
        docs = self.mutated()
        docs["overlay"]["candidates"][0]["effective_from"] = "2025-01-01T00:00:00Z"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "fabricated candidate effective interval"):
            self.validate(docs)

    def test_t5_candidate_cannot_smuggle_authoritative_beneficiary(self):
        docs = self.mutated()
        docs["candidates"]["candidates"][0]["beneficiary"] = "ENTITY-EATON-PLC"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "authoritative beneficiary"):
            self.validate(docs)

    def test_t6_beneficiary_cannot_qualify_against_ineligible_parent(self):
        docs = self.mutated()
        relation = docs["beneficiaries"]["relationships"][0]
        relation["qualification_state"] = "QUALIFIED"
        relation["beneficiary_confidence"] = 0.9
        with self.assertRaisesRegex(OwnerSeamConformanceError, "ineligible beneficiary evaluation"):
            self.validate(docs)

    def test_beneficiary_constraint_evidence_must_come_from_parent_constraint_support(self):
        docs = self.mutated()
        docs["beneficiaries"]["relationships"][0]["evidence_lineage"]["constraint_evidence"] = [
            "EV-LBNL-QUEUE-2024"
        ]
        with self.assertRaisesRegex(OwnerSeamConformanceError, "not inherited from parent"):
            self.validate(docs)

    def test_batch13_prequalification_cannot_fabricate_economic_capture(self):
        docs = self.mutated()
        docs["batch13"]["evidence_roles"]["economic_capture"] = ["CLM-AIDC-005"]
        with self.assertRaisesRegex(OwnerSeamConformanceError, "fabricated economic capture"):
            self.validate(docs)

    def test_strict_gate_cannot_turn_shadow_candidate_coverage_into_formation_pass(self):
        docs = self.mutated()
        docs["batch14"]["dimensions"]["IMPLEMENTATION_ADMITTED"]["status"] = "READY"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "constraint-formation gate"):
            self.validate(docs)

    def test_strict_gate_cannot_turn_blocked_beneficiary_evaluation_into_pass(self):
        docs = self.mutated()
        docs["batch14"]["dimensions"]["IMPLEMENTATION_ADMITTED"]["blockers"].remove(
            "CANONICAL-T5-T6-CONSTRAINT-AND-BENEFICIARY-ADMISSION-NOT-AUTHORIZED"
        )
        with self.assertRaisesRegex(OwnerSeamConformanceError, "beneficiary gate"):
            self.validate(docs)


    def test_mainline_gate_rejects_identity_and_shape_smuggling(self):
        mutations = [
            ("schema_version", "other/v1"),
            ("record_id", "forged"),
            ("slice_id", "OTHER_SLICE"),
            ("dimensions", None),
            ("gates", {}),
            ("overall_result", "BLOCKED"),
            ("overall_status", "READY"),
            ("full_constraint_run_allowed", True),
            ("full_constraint_run_allowed", 0),
            ("first_serious_constraint_run", "READY"),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                docs = self.mutated()
                docs["batch14"][field] = value
                with self.assertRaises(OwnerSeamConformanceError):
                    self.validate(docs)

    def test_mainline_gate_cannot_drop_native_admission_blocker(self):
        docs = self.mutated()
        docs["batch14"]["dimensions"]["IMPLEMENTATION_ADMITTED"]["blockers"].remove(
            "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT"
        )
        with self.assertRaisesRegex(OwnerSeamConformanceError, "native admission blocker"):
            self.validate(docs)

if __name__ == "__main__":
    unittest.main()
