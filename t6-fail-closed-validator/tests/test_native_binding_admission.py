from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from hydra_t6_failclosed import HMACSHA256Verifier
from hydra_t6_failclosed.documents import canonical_json_bytes
from hydra_t6_failclosed.native_binding_admission import (
    ADMISSION_AUTHORITY_ROLE,
    ADMISSION_DECISION,
    ADMISSION_OPERATION,
    ADMISSION_RECEIPT_SCHEMA,
    ADMISSION_SCOPE,
    CONSUMER_STAGE,
    IMPLEMENTATION_MANIFEST_SCHEMA,
    PRODUCER_STAGE,
    sign_native_binding_admission,
    validate_native_binding_admission,
)


class NativeT5T6AdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 9, 25, 22, 0, tzinfo=UTC)
        self.key = b"native-binding-public-test-key"
        self.key_id = "native-binding-test-key"
        self.verifier = HMACSHA256Verifier({self.key_id: self.key})

    def manifest(self) -> dict[str, object]:
        return {
            "schema_version": IMPLEMENTATION_MANIFEST_SCHEMA,
            "implementation_id": "native-t5-t6-test-001",
            "implementation_version": "test-v1",
            "artifact_sha256": "a" * 64,
            "test_evidence_sha256": "b" * 64,
            "producer_stage": PRODUCER_STAGE,
            "consumer_stage": CONSUMER_STAGE,
            "handoff_schema": "t6-candidate-handoff.v1",
            "candidate_schema": "constraint-candidate.v2",
            "semantic_authority_pins": {
                "thread1": "LILY_THREAD_1_CORE_ENGINE_SEAMS:BATCH11",
                "thread2": "LILY_THREAD_2_BATCH_06_FINAL_CLOSURE:a0faf1074ff7aaa5db6546d16076bfff0acf024548be21bd0eacc558ea5ce38e",
                "thread3": "LILY_THREAD_3_MASTER_CLOSURE:ab7e4c05c9210a90256b8cdea89eeb9f3bb551453dfe13ebfe44616f750cb366",
            },
            "runtime_activation_requested": False,
            "canonical_promotion_requested": False,
            "live_source_requested": False,
        }

    def receipt(self, manifest: dict[str, object]) -> dict[str, object]:
        import hashlib

        manifest_sha = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
        receipt: dict[str, object] = {
            "schema_version": ADMISSION_RECEIPT_SCHEMA,
            "admission_id": "native-t5-t6-admission-test-001",
            "authority_role": ADMISSION_AUTHORITY_ROLE,
            "decision": ADMISSION_DECISION,
            "operation": ADMISSION_OPERATION,
            "scopes": [ADMISSION_SCOPE],
            "implementation_id": manifest["implementation_id"],
            "bindings": {
                "manifest_sha256": manifest_sha,
                "artifact_sha256": manifest["artifact_sha256"],
                "test_evidence_sha256": manifest["test_evidence_sha256"],
            },
            "producer_stage": PRODUCER_STAGE,
            "consumer_stage": CONSUMER_STAGE,
            "issued_at": (self.now - timedelta(minutes=10)).isoformat(),
            "expires_at": (self.now + timedelta(hours=1)).isoformat(),
            "revocation": {
                "status": "not_revoked",
                "checked_at": (self.now - timedelta(minutes=1)).isoformat(),
                "source_id": "native-binding-test-revocation",
                "sequence": 1,
            },
            "supersession": {
                "status": "current",
                "predecessor_id": None,
                "successor_id": None,
                "chain": [],
            },
            "limitations": {
                "runtime_activation_authorized": False,
                "canonical_promotion_authorized": False,
                "live_source_authorized": False,
                "model_training_authorized": False,
                "trading_authorized": False,
            },
            "key_id": self.key_id,
            "signature_method": "HMAC-SHA256",
            "signature": "",
        }
        receipt["signature"] = sign_native_binding_admission(receipt, key=self.key)
        return receipt

    def resign(self, receipt: dict[str, object]) -> None:
        receipt["signature"] = sign_native_binding_admission(receipt, key=self.key)

    def validate(self, manifest, receipt, *, verifier=None, now=None):
        return validate_native_binding_admission(
            implementation_manifest=manifest,
            admission_receipt=receipt,
            verifier=self.verifier if verifier is None else verifier,
            now=self.now if now is None else now,
        )

    def test_missing_admission_receipt_fails_closed(self) -> None:
        result = self.validate(self.manifest(), None)
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "BLOCKED_AUTHORITY_RECEIPT_ABSENT")
        self.assertFalse(result.runtime_activation_authorized)
        self.assertFalse(result.canonical_promotion_authorized)
        self.assertFalse(result.live_source_authorized)
        self.assertFalse(result.model_training_authorized)
        self.assertFalse(result.trading_authorized)
        self.assertFalse(result.to_dict()["model_training_authorized"])
        self.assertFalse(result.to_dict()["trading_authorized"])

    def test_exact_signed_receipt_admits_only_the_implementation_artifact(self) -> None:
        manifest = self.manifest()
        result = self.validate(manifest, self.receipt(manifest))
        self.assertTrue(result.admitted)
        self.assertEqual(result.reason, "ADMITTED_EXACT_ARTIFACT")
        self.assertFalse(result.runtime_activation_authorized)
        self.assertFalse(result.canonical_promotion_authorized)
        self.assertFalse(result.live_source_authorized)
        self.assertFalse(result.model_training_authorized)
        self.assertFalse(result.trading_authorized)
        self.assertFalse(result.to_dict()["model_training_authorized"])
        self.assertFalse(result.to_dict()["trading_authorized"])

    def test_tampered_manifest_is_not_admitted_by_old_receipt(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        manifest["artifact_sha256"] = "c" * 64
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "BLOCKED_AUTHORITY_RECEIPT_INVALID")
        self.assertIn("admission_receipt_binding_mismatch", {issue.code for issue in result.issues})

    def test_receipt_cannot_smuggle_runtime_or_canonical_authority(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        receipt["limitations"]["canonical_promotion_authorized"] = True  # type: ignore[index]
        receipt["signature"] = sign_native_binding_admission(receipt, key=self.key)
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertIn("admission_receipt_scope_escalation", {issue.code for issue in result.issues})

    def test_manifest_cannot_request_live_or_runtime_activation(self) -> None:
        manifest = self.manifest()
        manifest["live_source_requested"] = True
        result = self.validate(manifest, None)
        self.assertFalse(result.admitted)
        self.assertEqual(result.reason, "BLOCKED_IMPLEMENTATION_MANIFEST_INVALID")
        self.assertIn("implementation_manifest_scope_escalation", {issue.code for issue in result.issues})

    def test_wrong_stage_pair_is_rejected(self) -> None:
        manifest = self.manifest()
        manifest["consumer_stage"] = "PIPELINE_T5_CONSTRAINT_FORMATION"
        result = self.validate(manifest, None)
        self.assertFalse(result.admitted)
        self.assertIn("implementation_manifest_consumer_invalid", {issue.code for issue in result.issues})

    def test_empty_admission_id_is_rejected(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        receipt["admission_id"] = ""
        self.resign(receipt)
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertIn("admission_receipt_identity_invalid", {issue.code for issue in result.issues})

    def test_expired_admission_receipt_is_rejected(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        receipt["expires_at"] = (self.now - timedelta(minutes=1)).isoformat()
        self.resign(receipt)
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertIn("admission_expired", {issue.code for issue in result.issues})

    def test_revoked_admission_receipt_is_rejected(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        receipt["revocation"]["status"] = "revoked"  # type: ignore[index]
        self.resign(receipt)
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertIn("admission_revoked_or_ambiguous", {issue.code for issue in result.issues})

    def test_stale_revocation_evidence_is_rejected(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        receipt["issued_at"] = (self.now - timedelta(hours=26)).isoformat()
        receipt["expires_at"] = (self.now + timedelta(hours=1)).isoformat()
        receipt["revocation"]["checked_at"] = (self.now - timedelta(hours=25)).isoformat()  # type: ignore[index]
        self.resign(receipt)
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertIn("admission_revocation_stale", {issue.code for issue in result.issues})

    def test_revocation_evidence_cannot_predate_receipt_issue(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        receipt["revocation"]["checked_at"] = (self.now - timedelta(minutes=20)).isoformat()  # type: ignore[index]
        self.resign(receipt)
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertIn("admission_revocation_predates_issue", {issue.code for issue in result.issues})

    def test_supersession_chain_cannot_contain_current_admission_id(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        admission_id = receipt["admission_id"]
        receipt["supersession"]["predecessor_id"] = admission_id  # type: ignore[index]
        receipt["supersession"]["chain"] = [admission_id]  # type: ignore[index]
        self.resign(receipt)
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertIn("admission_supersession_cycle", {issue.code for issue in result.issues})

    def test_missing_verifier_is_rejected(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        result = validate_native_binding_admission(
            implementation_manifest=manifest,
            admission_receipt=receipt,
            verifier=None,
            now=self.now,
        )
        self.assertFalse(result.admitted)
        self.assertIn("admission_verifier_missing", {issue.code for issue in result.issues})

    def test_invalid_signature_is_rejected(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        receipt["signature"] = "0" * 64
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertIn("admission_signature_invalid", {issue.code for issue in result.issues})

    def test_resigned_binding_tamper_is_still_rejected(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        receipt["bindings"]["artifact_sha256"] = "c" * 64  # type: ignore[index]
        self.resign(receipt)
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertIn("admission_receipt_binding_mismatch", {issue.code for issue in result.issues})

    def test_extra_receipt_claim_is_rejected(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        receipt["runtime_activation_authorized"] = True
        self.resign(receipt)
        result = self.validate(manifest, receipt)
        self.assertFalse(result.admitted)
        self.assertIn("admission_receipt_extra_field", {issue.code for issue in result.issues})

    def test_naive_now_is_rejected(self) -> None:
        manifest = self.manifest()
        receipt = self.receipt(manifest)
        result = validate_native_binding_admission(
            implementation_manifest=manifest,
            admission_receipt=receipt,
            verifier=self.verifier,
            now=self.now.replace(tzinfo=None),
        )
        self.assertFalse(result.admitted)
        self.assertIn("admission_now_naive", {issue.code for issue in result.issues})


if __name__ == "__main__":
    unittest.main()
