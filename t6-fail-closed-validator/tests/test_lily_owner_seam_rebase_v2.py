from __future__ import annotations

import copy
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
    "temporal_identity_overlay": SLICE / "HYDRA_CONSTRAINT_LILY_OWNER_SEAM_RECONCILIATION_T5_CANDIDATE_TEMPORAL_IDENTITY_OVERLAY_V002_20260926.json",
    "typed_confidence": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_AI_DATA_CENTER_POWER_INFRASTRUCTURE_TYPED_CONFIDENCE_OVERLAY_V001_20260925.json",
    "batch13": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_AI_DATA_CENTER_POWER_INFRASTRUCTURE_EATON_TRANSFORMER_PREQUALIFICATION_OVERLAY_V001_20260925.json",
    "batch16": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class LilyOwnerSeamRebaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = {name: load(path) for name, path in FILES.items()}

    def validate(self, docs=None):
        source = self.docs if docs is None else docs
        return validate_owner_seams(
            claims=source["claims"],
            candidates=source["candidates"],
            beneficiaries=source["beneficiaries"],
            temporal_identity_overlay=source["temporal_identity_overlay"],
            typed_confidence=source["typed_confidence"],
            batch13_beneficiary_overlay=source["batch13"],
            batch16_strict_gate=source["batch16"],
        )

    def mutated(self):
        return copy.deepcopy(self.docs)

    def test_current_owner_seams_pass(self):
        result = self.validate()
        self.assertEqual("PASS_CURRENT_FAIL_CLOSED_OWNER_SEAMS", result["status"])
        self.assertEqual(3, result["candidate_count"])
        self.assertEqual(4, result["beneficiary_relationship_count"])
        self.assertEqual(0, result["canonical_constraint_count"])
        self.assertEqual(0, result["qualified_beneficiary_count"])

    def test_temporal_overlay_cannot_backdate_candidate(self):
        docs = self.mutated()
        docs["temporal_identity_overlay"]["candidates"][0]["available_at"] = "2026-09-25T00:00:00Z"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "backdates availability"):
            self.validate(docs)

    def test_temporal_overlay_cannot_invent_effective_interval(self):
        docs = self.mutated()
        docs["temporal_identity_overlay"]["candidates"][0]["effective_from"] = "2025-01-01T00:00:00Z"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "fabricated candidate effective interval"):
            self.validate(docs)

    def test_temporal_overlay_cannot_mint_canonical_constraint(self):
        docs = self.mutated()
        docs["temporal_identity_overlay"]["candidates"][0]["canonical_constraint_id"] = "K-UNAUTHORIZED"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "minted canonical constraint ID"):
            self.validate(docs)

    def test_canonical_identity_must_remain_not_evaluated(self):
        docs = self.mutated()
        docs["temporal_identity_overlay"]["candidates"][0]["canonical_identity_state"] = "DISTINCT"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "canonical identity state"):
            self.validate(docs)

    def test_batch015_candidate_confidence_cannot_be_invented(self):
        docs = self.mutated()
        docs["typed_confidence"]["candidate_confidence"][0]["measurement_state"] = "MEASURED"
        docs["typed_confidence"]["candidate_confidence"][0]["value"] = 0.9
        with self.assertRaisesRegex(OwnerSeamConformanceError, "explicit unknown"):
            self.validate(docs)

    def test_beneficiary_confidence_cannot_inherit_numeric_score(self):
        docs = self.mutated()
        docs["typed_confidence"]["beneficiary_confidence"][0]["value"] = 0.9
        with self.assertRaisesRegex(OwnerSeamConformanceError, "numeric beneficiary confidence"):
            self.validate(docs)

    def test_t5_candidate_cannot_smuggle_beneficiary(self):
        docs = self.mutated()
        docs["candidates"]["candidates"][0]["beneficiary"] = "ENTITY-EATON-PLC"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "authoritative beneficiary"):
            self.validate(docs)

    def test_t6_beneficiary_cannot_qualify_blocked_parent(self):
        docs = self.mutated()
        docs["beneficiaries"]["relationships"][0]["qualification_state"] = "QUALIFIED"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "ineligible beneficiary evaluation"):
            self.validate(docs)

    def test_batch016_implementation_gate_cannot_be_promoted(self):
        docs = self.mutated()
        docs["batch16"]["dimensions"]["IMPLEMENTATION_ADMITTED"]["status"] = "READY"
        with self.assertRaisesRegex(OwnerSeamConformanceError, "implementation admission"):
            self.validate(docs)

    def test_overlay_must_not_duplicate_confidence_or_custody(self):
        docs = self.mutated()
        docs["temporal_identity_overlay"]["result"]["confidence_semantics_reimplemented"] = True
        with self.assertRaisesRegex(OwnerSeamConformanceError, "duplicated Batch015 confidence"):
            self.validate(docs)

    def test_candidate_references_must_resolve_in_known_namespace(self):
        for value in ("UNRESOLVED-NOT-A-REFERENCE", "EV-NONEXISTENT", "CLM-NONEXISTENT"):
            with self.subTest(value=value):
                docs = self.mutated()
                docs["candidates"]["candidates"][0]["evidence_roles"]["demand_context"].append(value)
                with self.assertRaises(OwnerSeamConformanceError):
                    self.validate(docs)

    def test_candidate_claim_lineage_rejects_duplicate_references(self):
        docs = self.mutated()
        refs = docs["candidates"]["candidates"][0]["claim_ids"]
        refs.append(refs[0])
        with self.assertRaisesRegex(OwnerSeamConformanceError, "claim_ids: duplicate references"):
            self.validate(docs)

    def test_candidate_evidence_role_rejects_duplicate_known_references(self):
        docs = self.mutated()
        refs = docs["candidates"]["candidates"][0]["evidence_roles"]["constraint_support"]
        refs.append(refs[0])
        with self.assertRaisesRegex(OwnerSeamConformanceError, "constraint_support: duplicate references"):
            self.validate(docs)

    def test_candidate_claim_can_also_appear_in_distinct_evidence_role(self):
        docs = self.mutated()
        candidate = docs["candidates"]["candidates"][1]
        self.assertIn("CLM-AIDC-005", candidate["claim_ids"])
        self.assertIn("CLM-AIDC-005", candidate["evidence_roles"]["relief"])
        self.assertEqual("PASS_CURRENT_FAIL_CLOSED_OWNER_SEAMS", self.validate(docs)["status"])

    def test_beneficiary_role_allows_duplicate_known_references(self):
        docs = self.mutated()
        refs = docs["beneficiaries"]["relationships"][0]["evidence_lineage"]["entity_connection"]
        refs.append(refs[0])
        result = self.validate(docs)
        self.assertEqual("PASS_CURRENT_FAIL_CLOSED_OWNER_SEAMS", result["status"])
        self.assertEqual(0, result["qualified_beneficiary_count"])

    def test_candidate_role_mapping_cannot_disappear(self):
        for value in (None, [], {}, ""):
            with self.subTest(value=value):
                docs = self.mutated()
                docs["candidates"]["candidates"][0]["evidence_roles"] = value
                with self.assertRaisesRegex(OwnerSeamConformanceError, "evidence-role mapping"):
                    self.validate(docs)

    def test_lineage_rejects_malformed_members_without_raw_type_errors(self):
        for value in (None, True, 17, {}, [], "", " ", " EV-DOE-LPT-SUPPLY"):
            with self.subTest(value=value):
                docs = self.mutated()
                docs["candidates"]["candidates"][0]["evidence_roles"]["demand_context"].append(value)
                with self.assertRaises(OwnerSeamConformanceError):
                    self.validate(docs)

    def test_beneficiary_role_collections_cannot_masquerade_as_empty_lists(self):
        fields = ("constraint_evidence", "entity_connection", "advantage_mechanism",
                  "capacity_or_availability", "economic_or_strategic_capture", "disconfirming_or_blocking")
        for field in fields:
            for value in ("", {}, None):
                with self.subTest(field=field, value=value):
                    docs = self.mutated()
                    docs["beneficiaries"]["relationships"][0]["evidence_lineage"][field] = value
                    with self.assertRaisesRegex(OwnerSeamConformanceError, "list required"):
                        self.validate(docs)

    def test_beneficiary_blocker_references_must_resolve(self):
        for value in ("EV-NONEXISTENT", "CLM-NONEXISTENT"):
            with self.subTest(value=value):
                docs = self.mutated()
                docs["beneficiaries"]["relationships"][0]["evidence_lineage"]["disconfirming_or_blocking"].append(value)
                with self.assertRaisesRegex(OwnerSeamConformanceError, "unknown"):
                    self.validate(docs)

    def test_known_blocker_references_and_historical_notes_remain_valid(self):
        docs = self.mutated()
        docs["beneficiaries"]["relationships"][0]["evidence_lineage"]["disconfirming_or_blocking"].extend(
            ["EV-DOE-LPT-SUPPLY", "CLM-AIDC-001"]
        )
        result = self.validate(docs)
        self.assertEqual(0, result["qualified_beneficiary_count"])

    def test_claim_evidence_requires_a_list_not_iterable_mapping(self):
        docs = self.mutated()
        refs = docs["claims"]["claims"][0]["support_evidence_ids"]
        docs["claims"]["claims"][0]["support_evidence_ids"] = dict.fromkeys(refs)
        with self.assertRaisesRegex(OwnerSeamConformanceError, "list required"):
            self.validate(docs)

    def test_non_object_candidate_row_fails_with_domain_error(self):
        docs = self.mutated()
        docs["candidates"]["candidates"][0] = None
        with self.assertRaisesRegex(OwnerSeamConformanceError, "object required"):
            self.validate(docs)


if __name__ == "__main__":
    unittest.main()
