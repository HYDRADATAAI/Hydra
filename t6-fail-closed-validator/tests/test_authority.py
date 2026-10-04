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
        self.verifier = HMACSHA256Verifier(
            {self.key_id: self.key},
            trusted_key_roles={self.key_id: {"validator_authority"}},
        )
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

    def _validate(self, envelope: dict[str, object], *, verifier=None):
        return validate_authority(
            envelope,
            verifier=self.verifier if verifier is None else verifier,
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

    def test_signed_unmapped_role_is_rejected(self) -> None:
        envelope = self._envelope()
        envelope["authority_role"] = "unmapped_role"
        self._resign(envelope)
        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertIn("authority_key_role_untrusted", {issue.code for issue in result.issues})

    def test_role_mapped_to_another_role_is_rejected(self) -> None:
        verifier = HMACSHA256Verifier(
            {self.key_id: self.key}, trusted_key_roles={self.key_id: {"other_role"}}
        )
        result = self._validate(self._envelope(), verifier=verifier)
        self.assertFalse(result.valid)
        self.assertIn("authority_key_role_untrusted", {issue.code for issue in result.issues})

    def test_missing_role_check_fails_closed(self) -> None:
        class VerifyOnly:
            def verify(self, **kwargs):
                return True

        result = self._validate(self._envelope(), verifier=VerifyOnly())
        self.assertFalse(result.valid)
        self.assertIn("authority_key_role_untrusted", {issue.code for issue in result.issues})

    def test_nonliteral_true_role_check_fails_closed(self) -> None:
        class MalformedRoleVerifier:
            def allows_role(self, key_id, role):
                return 1

            def verify(self, **kwargs):
                return True

        result = self._validate(self._envelope(), verifier=MalformedRoleVerifier())
        self.assertFalse(result.valid)
        self.assertIn("authority_key_role_untrusted", {issue.code for issue in result.issues})

    def test_role_check_exception_fails_closed(self) -> None:
        class RaisingRoleVerifier:
            def allows_role(self, key_id, role):
                raise RuntimeError("role lookup failed")

        result = self._validate(self._envelope(), verifier=RaisingRoleVerifier())
        self.assertFalse(result.valid)
        self.assertIn("authority_key_role_untrusted", {issue.code for issue in result.issues})

    def test_truthy_nonboolean_signature_result_fails_closed(self) -> None:
        class MalformedSignatureVerifier:
            def allows_role(self, key_id, role):
                return True

            def verify(self, **kwargs):
                return 1

        result = self._validate(self._envelope(), verifier=MalformedSignatureVerifier())
        self.assertFalse(result.valid)
        self.assertIn("authority_signature_invalid", {issue.code for issue in result.issues})

    def test_signature_exception_fails_closed(self) -> None:
        class RaisingSignatureVerifier:
            def allows_role(self, key_id, role):
                return True

            def verify(self, **kwargs):
                raise RuntimeError("signature verifier unavailable")

        result = self._validate(self._envelope(), verifier=RaisingSignatureVerifier())
        self.assertFalse(result.valid)
        self.assertIn("authority_signature_invalid", {issue.code for issue in result.issues})

    def test_missing_signature_method_fails_closed(self) -> None:
        class MissingSignatureMethod:
            def allows_role(self, key_id, role):
                return True

        result = self._validate(self._envelope(), verifier=MissingSignatureMethod())
        self.assertFalse(result.valid)
        self.assertIn("authority_signature_invalid", {issue.code for issue in result.issues})

    def test_noncallable_signature_method_fails_closed(self) -> None:
        class NonCallableSignatureMethod:
            allows_role = staticmethod(lambda key_id, role: True)
            verify = 1

        result = self._validate(self._envelope(), verifier=NonCallableSignatureMethod())
        self.assertFalse(result.valid)
        self.assertIn("authority_signature_invalid", {issue.code for issue in result.issues})

    def test_invalid_role_configuration_fails(self) -> None:
        invalid = (
            ({" ": self.key}, {" ": {"validator_authority"}}),
            ({1: self.key}, None),
            ({self.key_id: self.key}, {self.key_id: "validator_authority"}),
            ({self.key_id: self.key}, {self.key_id: {""}}),
            ({self.key_id: self.key}, {self.key_id: {1}}),
            ({self.key_id: self.key}, {self.key_id: {"validator_authority": True}}),
            ({self.key_id: self.key}, {"unknown": {"validator_authority"}}),
        )
        for keys, roles in invalid:
            with self.subTest(keys=keys, roles=roles):
                with self.assertRaises(ValueError):
                    HMACSHA256Verifier(keys, trusted_key_roles=roles)

    def test_string_subclass_key_id_cannot_alias_trusted_key(self) -> None:
        class AliasKeyId(str):
            def __str__(self):
                return "test-key"

        envelope = self._envelope()
        envelope["key_id"] = AliasKeyId("untrusted-key")
        self._resign(envelope)
        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertIn("authority_identity_invalid", {issue.code for issue in result.issues})

    def test_string_subclass_signature_method_is_rejected(self) -> None:
        class AliasMethod(str):
            def __str__(self):
                return "HMAC-SHA256"

        envelope = self._envelope()
        envelope["signature_method"] = AliasMethod("OTHER")
        self._resign(envelope)
        result = self._validate(envelope)
        self.assertFalse(result.valid)
        codes = {issue.code for issue in result.issues}
        self.assertIn("authority_signature_method_invalid", codes)
        self.assertIn("authority_signature_invalid", codes)

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
