from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from hydra_t6_failclosed.authority import (
    AUTHORITY_SCHEMA,
    DECISION,
    OPERATION,
    REQUIRED_SCOPE,
    HMACSHA256Verifier,
    sign_hmac_sha256,
    validate_authority,
)


class AuthorityEnvelopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 9, 24, 18, 0, tzinfo=UTC)
        self.key = b"public-test-key"
        self.key_id = "test-key"
        self.verifier = HMACSHA256Verifier({self.key_id: self.key})
        self.input_sha256 = "1" * 64
        self.policy_sha256 = "2" * 64
        self.output_schema_sha256 = "3" * 64
        self.oracle_sha256 = "4" * 64

    def _envelope(self, *, expires_at: datetime | None = None) -> dict[str, object]:
        issued_at = self.now - timedelta(minutes=10)
        expires_at = expires_at or self.now + timedelta(hours=1)
        envelope: dict[str, object] = {
            "schema_version": AUTHORITY_SCHEMA,
            "authority_id": "authority-test-001",
            "authority_name": "public-test-authority",
            "authority_role": "validator_authority",
            "decision": DECISION,
            "operation": OPERATION,
            "scopes": [REQUIRED_SCOPE],
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "bindings": {
                "input_sha256": self.input_sha256,
                "oracle_sha256": self.oracle_sha256,
                "output_schema_sha256": self.output_schema_sha256,
                "policy_sha256": self.policy_sha256,
            },
            "revocation": {
                "status": "not_revoked",
                "checked_at": (self.now - timedelta(minutes=1)).isoformat(),
                "source_id": "public-test-revocation-source",
                "sequence": 1,
            },
            "supersession": {
                "status": "current",
                "predecessor_id": None,
                "successor_id": None,
                "chain": [],
            },
            "key_id": self.key_id,
            "signature_method": "HMAC-SHA256",
            "signature": "",
        }
        envelope["signature"] = sign_hmac_sha256(envelope, key=self.key)
        return envelope

    def _validate(self, envelope: dict[str, object]):
        return validate_authority(
            envelope,
            verifier=self.verifier,
            now=self.now,
            input_sha256=self.input_sha256,
            policy_sha256=self.policy_sha256,
            output_schema_sha256=self.output_schema_sha256,
            oracle_sha256=self.oracle_sha256,
        )

    def _resign(self, envelope: dict[str, object]) -> None:
        envelope["signature"] = sign_hmac_sha256(envelope, key=self.key)

    def test_valid_signed_authority_is_accepted(self) -> None:
        result = self._validate(self._envelope())
        self.assertTrue(result.valid)
        self.assertEqual(result.reason, "VALID")
        self.assertEqual(result.issues, ())

    def test_expired_authority_is_rejected_fail_closed(self) -> None:
        result = self._validate(
            self._envelope(expires_at=self.now - timedelta(minutes=1))
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "POLICY_EXPIRED")
        self.assertIn("authority_expired", {issue.code for issue in result.issues})

    def test_tampered_signature_is_rejected(self) -> None:
        envelope = self._envelope()
        envelope["signature"] = "0" * 64
        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "AUTHORITY_INVALID")
        self.assertIn("authority_signature_invalid", {issue.code for issue in result.issues})

    def test_revoked_authority_is_rejected_fail_closed(self) -> None:
        envelope = self._envelope()
        revocation = envelope["revocation"]
        self.assertIsInstance(revocation, dict)
        revocation["status"] = "revoked"
        self._resign(envelope)
        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "POLICY_REVOKED")
        self.assertIn("authority_revoked", {issue.code for issue in result.issues})

    def test_stale_revocation_evidence_is_rejected(self) -> None:
        envelope = self._envelope()
        revocation = envelope["revocation"]
        self.assertIsInstance(revocation, dict)
        revocation["checked_at"] = (self.now - timedelta(hours=25)).isoformat()
        self._resign(envelope)
        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertIn("authority_revocation_stale", {issue.code for issue in result.issues})

    def test_each_bound_digest_mismatch_is_rejected(self) -> None:
        for field in ("input_sha256", "policy_sha256", "output_schema_sha256", "oracle_sha256"):
            envelope = self._envelope()
            bindings = envelope["bindings"]
            self.assertIsInstance(bindings, dict)
            bindings[field] = "f" * 64
            self._resign(envelope)
            result = self._validate(envelope)
            with self.subTest(field=field):
                self.assertFalse(result.valid)
                self.assertIn("authority_binding_mismatch", {issue.code for issue in result.issues})

    def test_missing_signature_verifier_is_rejected(self) -> None:
        envelope = self._envelope()
        result = validate_authority(
            envelope,
            verifier=None,
            now=self.now,
            input_sha256=self.input_sha256,
            policy_sha256=self.policy_sha256,
            output_schema_sha256=self.output_schema_sha256,
            oracle_sha256=self.oracle_sha256,
        )
        self.assertFalse(result.valid)
        self.assertIn("authority_verifier_missing", {issue.code for issue in result.issues})

    def test_future_authority_is_rejected(self) -> None:
        envelope = self._envelope()
        envelope["issued_at"] = (self.now + timedelta(minutes=5)).isoformat()
        envelope["expires_at"] = (self.now + timedelta(hours=1)).isoformat()
        revocation = envelope["revocation"]
        self.assertIsInstance(revocation, dict)
        revocation["checked_at"] = (self.now + timedelta(minutes=5)).isoformat()
        self._resign(envelope)
        result = self._validate(envelope)
        self.assertFalse(result.valid)
        codes = {issue.code for issue in result.issues}
        self.assertIn("authority_not_yet_valid", codes)
        self.assertIn("authority_revocation_future", codes)

    def test_superseded_authority_is_rejected(self) -> None:
        envelope = self._envelope()
        supersession = envelope["supersession"]
        self.assertIsInstance(supersession, dict)
        supersession["status"] = "superseded"
        supersession["successor_id"] = "authority-test-002"
        self._resign(envelope)
        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertIn("authority_superseded", {issue.code for issue in result.issues})


if __name__ == "__main__":
    unittest.main()
