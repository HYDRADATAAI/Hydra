from __future__ import annotations

import hashlib
import json
import unittest
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from hydra_t6_failclosed.handoff import validate_handoff
from hydra_t6_failclosed.native_t5_t6_bridge import (
    NativeT5T6BridgeError,
    build_native_t5_t6_handoff,
)
from hydra_t6_failclosed.native_binding_admission import validate_native_binding_admission


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"
IMPLEMENTATION = ROOT / "t6-fail-closed-validator" / "src" / "hydra_t6_failclosed" / "native_t5_t6_bridge.py"
TEST_EVIDENCE = Path(__file__).resolve()
MANIFEST = ROOT / "docs" / "constraint" / "implementation" / "HYDRA_CONSTRAINT_FIRST_SLICE_NATIVE_T5_T6_IMPLEMENTATION_MANIFEST_V001_20260928.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class NativeT5T6BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proposals = load(BASE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_T5_CANDIDATE_PROPOSALS_V001_20260925.json")
        cls.overlay = load(BASE / "HYDRA_CONSTRAINT_LILY_OWNER_SEAM_RECONCILIATION_T5_CANDIDATE_TEMPORAL_IDENTITY_OVERLAY_V002_20260926.json")

    def build(self, proposals=None, overlay=None):
        return build_native_t5_t6_handoff(
            self.proposals if proposals is None else proposals,
            self.overlay if overlay is None else overlay,
            handoff_id="AIDC-FIRST-SLICE-NATIVE-T5-T6-20260928",
            created_at="2026-09-28T18:30:00Z",
        )

    def test_real_first_slice_inputs_map_to_valid_t6_handoff(self):
        handoff = self.build()
        ids, issues = validate_handoff(handoff)
        self.assertEqual(issues, ())
        self.assertEqual(
            ids,
            (
                "T5C-AIDC-AMER-SWITCHGEAR-LEADTIME-001",
                "T5C-AIDC-US-INTERCONNECTION-THROUGHPUT-001",
                "T5C-AIDC-US-TRANSFORMER-SUPPLY-001",
            ),
        )
        self.assertTrue(all(candidate["canonicality"] == "candidate_only" for candidate in handoff["candidates"]))
        self.assertTrue(all(candidate["lifecycle_state"] == "handed_off" for candidate in handoff["candidates"]))
        self.assertTrue(all(candidate["beneficiaries"] == [] for candidate in handoff["candidates"]))

    def test_mapping_is_deterministic_under_input_order_changes(self):
        left = self.build()
        proposals = deepcopy(self.proposals)
        overlay = deepcopy(self.overlay)
        proposals["candidates"].reverse()
        overlay["candidates"].reverse()
        right = self.build(proposals, overlay)
        self.assertEqual(left, right)

    def test_ambiguity_unknown_effective_interval_and_blockers_are_preserved(self):
        handoff = self.build()
        candidate = next(item for item in handoff["candidates"] if item["candidate_id"].endswith("INTERCONNECTION-THROUGHPUT-001"))
        self.assertEqual(candidate["trust"]["classification_status"], "AMBIGUOUS")
        self.assertIsNone(candidate["trust"]["constraint_class"])
        self.assertEqual({"CAPACITY", "REGULATORY"}, set(candidate["uncertainty"]["classification_candidates"]))
        self.assertFalse(candidate["uncertainty"]["ordinary_t6_eligible"])
        self.assertIn("PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION", candidate["uncertainty"]["ineligibility_reasons"])
        self.assertIsNone(candidate["temporal"]["effective_from"])
        self.assertIsNone(candidate["temporal"]["effective_to"])
        self.assertEqual("UNRESOLVED_NOT_FABRICATED", candidate["temporal"]["effective_state"])

    def test_candidate_set_drift_is_rejected(self):
        overlay = deepcopy(self.overlay)
        overlay["candidates"].pop()
        with self.assertRaisesRegex(NativeT5T6BridgeError, "candidate set"):
            self.build(overlay=overlay)

    def test_eligibility_disagreement_is_rejected(self):
        overlay = deepcopy(self.overlay)
        overlay["candidates"][0]["ordinary_t6_eligible"] = True
        with self.assertRaisesRegex(NativeT5T6BridgeError, "eligibility disagree"):
            self.build(overlay=overlay)

    def test_ineligibility_reason_drift_is_rejected(self):
        overlay = deepcopy(self.overlay)
        overlay["candidates"][0]["source_ineligibility_reasons"] = ["invented"]
        with self.assertRaisesRegex(NativeT5T6BridgeError, "ineligibility reasons drift"):
            self.build(overlay=overlay)

    def test_claimed_t5_canonicalization_is_rejected(self):
        proposals = deepcopy(self.proposals)
        proposals["canonicalization_performed"] = True
        with self.assertRaisesRegex(NativeT5T6BridgeError, "claims canonicalization"):
            self.build(proposals=proposals)

    def test_non_null_canonical_identity_is_rejected(self):
        proposals = deepcopy(self.proposals)
        proposals["candidates"][0]["canonical_constraint_id"] = "SHOULD-NOT-EXIST"
        with self.assertRaisesRegex(NativeT5T6BridgeError, "canonical identity"):
            self.build(proposals=proposals)

    def test_manifest_binds_exact_artifact_and_test_evidence(self):
        manifest = load(MANIFEST)
        self.assertEqual(hashlib.sha256(IMPLEMENTATION.read_bytes()).hexdigest(), manifest["artifact_sha256"])
        self.assertEqual(hashlib.sha256(TEST_EVIDENCE.read_bytes()).hexdigest(), manifest["test_evidence_sha256"])
        result = validate_native_binding_admission(
            implementation_manifest=manifest,
            admission_receipt=None,
            verifier=None,
            now=datetime(2026, 9, 28, 18, 30, tzinfo=UTC),
        )
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "BLOCKED_AUTHORITY_RECEIPT_ABSENT")
        self.assertEqual(result.issues[0].code, "native_binding_admission_receipt_missing")


if __name__ == "__main__":
    unittest.main()
