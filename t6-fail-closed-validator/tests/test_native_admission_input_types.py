"""Receipt shape tests; the stub performs no signing or cryptographic verification."""

from __future__ import annotations

import hashlib
import unittest
from datetime import UTC, datetime

from hydra_t6_failclosed.documents import canonical_json_bytes
from hydra_t6_failclosed.native_binding_admission import (
    ADMISSION_AUTHORITY_ROLE, ADMISSION_DECISION, ADMISSION_OPERATION,
    ADMISSION_RECEIPT_SCHEMA, ADMISSION_SCOPE, CONSUMER_STAGE,
    IMPLEMENTATION_MANIFEST_SCHEMA, PRODUCER_STAGE,
    validate_native_binding_admission,
)


class ShapeOnlyVerifier:
    """Test double, deliberately not an authority or a signature verifier."""

    def verify(self, **kwargs):
        return True


class NativeAdmissionInputTypesTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 25, 22, tzinfo=UTC)
        self.manifest = {
            "schema_version": IMPLEMENTATION_MANIFEST_SCHEMA,
            "implementation_id": "shape-test-only",
            "implementation_version": "test-only",
            "artifact_sha256": "a" * 64,
            "test_evidence_sha256": "b" * 64,
            "producer_stage": PRODUCER_STAGE,
            "consumer_stage": CONSUMER_STAGE,
            "handoff_schema": "t6-candidate-handoff.v1",
            "candidate_schema": "constraint-candidate.v2",
            "semantic_authority_pins": {key: "shape-test-only" for key in ("thread1", "thread2", "thread3")},
            "runtime_activation_requested": False,
            "canonical_promotion_requested": False,
            "live_source_requested": False,
        }
        self.receipt = {
            "schema_version": ADMISSION_RECEIPT_SCHEMA,
            "admission_id": "shape-test-receipt-only",
            "authority_role": ADMISSION_AUTHORITY_ROLE,
            "decision": ADMISSION_DECISION,
            "operation": ADMISSION_OPERATION,
            "scopes": [ADMISSION_SCOPE],
            "implementation_id": self.manifest["implementation_id"],
            "bindings": {
                "manifest_sha256": hashlib.sha256(canonical_json_bytes(self.manifest)).hexdigest(),
                "artifact_sha256": self.manifest["artifact_sha256"],
                "test_evidence_sha256": self.manifest["test_evidence_sha256"],
            },
            "producer_stage": PRODUCER_STAGE,
            "consumer_stage": CONSUMER_STAGE,
            "issued_at": "2026-09-25T21:50:00+00:00",
            "expires_at": "2026-09-25T23:00:00+00:00",
            "revocation": {"status": "not_revoked", "checked_at": "2026-09-25T21:59:00+00:00", "source_id": "shape-test-only", "sequence": 1},
            "supersession": {"status": "current", "predecessor_id": None, "successor_id": None, "chain": []},
            "limitations": {key: False for key in LIMITATIONS},
            "key_id": "not-a-trusted-key",
            "signature_method": "SHAPE-TEST-STUB-NOT-CRYPTOGRAPHY",
            "signature": "not-a-signature",
        }

    def validate(self):
        # Exercise JSON parsing too; all hostile inputs are representable in JSON.
        return validate_native_binding_admission(
            implementation_manifest=canonical_json_bytes(self.manifest),
            admission_receipt=canonical_json_bytes(self.receipt),
            verifier=ShapeOnlyVerifier(), now=self.now,
        )

    def assert_rejected(self, code):
        result = self.validate()
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "BLOCKED_AUTHORITY_RECEIPT_INVALID")
        self.assertIn(code, {issue.code for issue in result.issues})
        self.assertFalse(result.runtime_activation_authorized)
        self.assertFalse(result.canonical_promotion_authorized)
        self.assertFalse(result.live_source_authorized)

    def test_literal_false_and_valid_empty_chain_control(self):
        self.assertTrue(self.validate().admitted)  # Only the test double accepts this.

    def test_valid_nonempty_chain_control(self):
        self.receipt["supersession"].update(predecessor_id="prior", chain=["prior"])
        self.assertTrue(self.validate().admitted)

    def test_missing_receipt_stays_blocked(self):
        result = validate_native_binding_admission(
            implementation_manifest=self.manifest, admission_receipt=None,
            verifier=ShapeOnlyVerifier(), now=self.now,
        )
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "BLOCKED_AUTHORITY_RECEIPT_ABSENT")

    def test_stub_receipt_without_verifier_stays_blocked(self):
        result = validate_native_binding_admission(
            implementation_manifest=self.manifest, admission_receipt=self.receipt,
            verifier=None, now=self.now,
        )
        self.assertFalse(result.admitted)
        self.assertIn("admission_verifier_missing", {issue.code for issue in result.issues})

    def test_extra_limitation_rejected(self):
        self.receipt["limitations"]["extra"] = False
        self.assert_rejected("admission_receipt_scope_escalation")

    def test_missing_limitation_rejected(self):
        del self.receipt["limitations"][LIMITATIONS[0]]
        self.assert_rejected("admission_receipt_scope_escalation")


LIMITATIONS = (
    "runtime_activation_authorized", "canonical_promotion_authorized",
    "live_source_authorized", "model_training_authorized", "trading_authorized",
)


def limitation_case(field, invalid):
    def test(self):
        self.receipt["limitations"][field] = invalid
        self.assert_rejected("admission_receipt_scope_escalation")
    return test


for field in LIMITATIONS:
    for label, invalid in (("integer_zero", 0), ("float_zero", 0.0), ("null", None), ("true", True), ("string_false", "false")):
        setattr(NativeAdmissionInputTypesTests, "test_" + field + "_" + label, limitation_case(field, invalid))


def chain_case(invalid):
    def test(self):
        self.receipt["supersession"].update(predecessor_id="prior", chain=invalid)
        self.assert_rejected("admission_supersession_chain_invalid")
    return test


for label, invalid in (("object", {"entry": "prior"}), ("integer", 42), ("boolean", True), ("null", None), ("string", "prior"), ("nested_list", [["prior"]])):
    setattr(NativeAdmissionInputTypesTests, "test_chain_" + label, chain_case(invalid))


if __name__ == "__main__":
    unittest.main()
