from __future__ import annotations

import unittest
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from hydra_t6_failclosed.authority import (
    AUTHORITY_SCHEMA,
    DECISION,
    OPERATION,
    REQUIRED_SCOPE,
    HMACSHA256Verifier,
    authority_signing_bytes,
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

    def test_non_mapping_authority_input_is_rejected(self) -> None:
        result = self._validate("{}")
        self.assertFalse(result.valid)
        self.assertIn("authority_input_invalid", {issue.code for issue in result.issues})

    def test_signed_authority_timestamp_utc_overflow_fails_closed(self) -> None:
        envelope = self._envelope()
        envelope["issued_at"] = "0001-01-01T00:00:00+23:59"
        self._resign(envelope)

        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertIn("authority_time_invalid", {issue.code for issue in result.issues})

    def test_authority_mapping_inspection_exceptions_fail_closed(self) -> None:
        class BrokenMapping(Mapping):
            def __getitem__(self, key):
                raise RuntimeError("mapping read failed")

            def __iter__(self):
                raise RuntimeError("mapping iteration failed")

            def __len__(self):
                return 1

        top_level = self._validate(BrokenMapping())
        self.assertFalse(top_level.valid)
        self.assertIn("authority_input_invalid", {issue.code for issue in top_level.issues})

        envelope = self._envelope()
        envelope["bindings"] = BrokenMapping()
        nested = self._validate(envelope)
        self.assertFalse(nested.valid)
        self.assertIn("authority_input_invalid", {issue.code for issue in nested.issues})

    def test_signed_authority_mapping_key_aliases_are_rejected(self) -> None:
        class AliasKey(str):
            def __new__(cls, value: str, expected: str):
                instance = super().__new__(cls, value)
                instance.expected = expected
                return instance

            def __eq__(self, other):
                return str(other) == self.expected

            __hash__ = lambda self: hash(self.expected)

            def __deepcopy__(self, memo):
                return AliasKey(str(self), self.expected)

        top_level = self._envelope()
        value = top_level.pop("schema_version")
        top_level[AliasKey("signed-as-other-field", "schema_version")] = value
        self._resign(top_level)
        self.assertTrue(
            self.verifier.verify(
                key_id=self.key_id,
                message=authority_signing_bytes(top_level),
                signature=top_level["signature"],
                method="HMAC-SHA256",
            )
        )
        top_level_result = self._validate(top_level)
        self.assertFalse(top_level_result.valid)
        self.assertIn("authority_field_missing", {issue.code for issue in top_level_result.issues})

        bindings_envelope = self._envelope()
        bindings = dict(bindings_envelope["bindings"])
        binding_value = bindings.pop("input_sha256")
        bindings[AliasKey("signed-as-other-digest", "input_sha256")] = binding_value
        bindings_envelope["bindings"] = bindings
        self._resign(bindings_envelope)
        bindings_result = self._validate(bindings_envelope)
        self.assertFalse(bindings_result.valid)
        self.assertIn("authority_bindings_invalid", {issue.code for issue in bindings_result.issues})

        revocation_envelope = self._envelope()
        revocation = revocation_envelope["revocation"]
        revocation_status = revocation.pop("status")
        revocation[AliasKey("signed-as-other-revocation-field", "status")] = revocation_status
        self._resign(revocation_envelope)
        revocation_result = self._validate(revocation_envelope)
        self.assertFalse(revocation_result.valid)
        self.assertIn("authority_revocation_invalid", {issue.code for issue in revocation_result.issues})

        supersession_envelope = self._envelope()
        supersession = supersession_envelope["supersession"]
        supersession_status = supersession.pop("status")
        supersession[AliasKey("signed-as-other-supersession-field", "status")] = supersession_status
        self._resign(supersession_envelope)
        supersession_result = self._validate(supersession_envelope)
        self.assertFalse(supersession_result.valid)
        self.assertIn("authority_supersession_invalid", {issue.code for issue in supersession_result.issues})

    def test_signed_split_view_authority_mapping_is_rejected(self) -> None:
        class SplitViewMapping(Mapping):
            def __init__(self, data):
                self.data = data

            def __getitem__(self, key):
                return self.data[key]

            def __iter__(self):
                return iter(self.data)

            def __len__(self):
                return len(self.data)

            def items(self):
                return [
                    (key, "TRADE" if key == "operation" else value)
                    for key, value in self.data.items()
                ]

        data = self._envelope()
        envelope = SplitViewMapping(data)
        data["signature"] = sign_hmac_sha256(envelope, key=self.key)
        self.assertTrue(
            self.verifier.verify(
                key_id=self.key_id,
                message=authority_signing_bytes(envelope),
                signature=data["signature"],
                method="HMAC-SHA256",
            )
        )

        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertIn("authority_signature_invalid", {issue.code for issue in result.issues})

    def test_signed_negative_int_subclass_sequence_is_rejected(self) -> None:
        class NegativeLyingInt(int):
            def __lt__(self, other):
                return False

        envelope = self._envelope()
        envelope["revocation"]["sequence"] = NegativeLyingInt(-1)
        self._resign(envelope)
        self.assertTrue(
            self.verifier.verify(
                key_id=self.key_id,
                message=authority_signing_bytes(envelope),
                signature=envelope["signature"],
                method="HMAC-SHA256",
            )
        )

        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertIn("authority_revocation_sequence_invalid", {issue.code for issue in result.issues})

    def test_valid_signed_authority_is_accepted(self) -> None:
        result = self._validate(self._envelope())
        self.assertTrue(result.valid)
        self.assertEqual(result.reason, "VALID")
        self.assertEqual(result.issues, ())


    def test_signed_mapping_string_subclasses_cannot_spoof_authority_literals(self) -> None:
        class EqualitySpoof(str):
            def __new__(cls, value: str, expected: str):
                instance = super().__new__(cls, value)
                instance.expected = expected
                return instance

            def __eq__(self, other):
                return str(other) == self.expected

            def __ne__(self, other):
                return not self.__eq__(other)

            __hash__ = str.__hash__

        envelope = self._envelope()
        envelope["schema_version"] = EqualitySpoof("wrong-schema", AUTHORITY_SCHEMA)
        envelope["decision"] = EqualitySpoof("wrong-decision", DECISION)
        envelope["operation"] = EqualitySpoof("wrong-operation", OPERATION)
        envelope["scopes"] = [EqualitySpoof("wrong-scope", REQUIRED_SCOPE)]
        envelope["bindings"] = {
            key: EqualitySpoof("0" * 64, value)
            for key, value in envelope["bindings"].items()
        }
        envelope["revocation"]["status"] = EqualitySpoof("wrong-status", "not_revoked")
        envelope["supersession"]["status"] = EqualitySpoof("wrong-status", "current")
        self._resign(envelope)

        self.assertTrue(
            self.verifier.verify(
                key_id=self.key_id,
                message=authority_signing_bytes(envelope),
                signature=envelope["signature"],
                method="HMAC-SHA256",
            )
        )
        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertTrue(result.issues)

    def test_missing_role_grants_deny_correctly_signed_authority(self) -> None:
        envelope = self._envelope()
        verifier = HMACSHA256Verifier({self.key_id: self.key})
        self.assertTrue(
            verifier.verify(
                key_id=self.key_id,
                message=authority_signing_bytes(envelope),
                signature=envelope["signature"],
                method="HMAC-SHA256",
            )
        )
        result = self._validate(envelope, verifier=verifier)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "AUTHORITY_INVALID")
        self.assertIn("authority_key_role_untrusted", {issue.code for issue in result.issues})

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
        self.assertIn("authority_verifier_error", {issue.code for issue in result.issues})

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
        self.assertIn("authority_key_role_untrusted", {issue.code for issue in result.issues})

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
        self.assertIn("authority_signature_invalid", codes)

    def test_signed_wrong_authority_role_is_rejected(self) -> None:
        envelope = self._envelope()
        envelope["authority_role"] = "trading_authority"
        self._resign(envelope)
        result = self._validate(envelope)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "AUTHORITY_INVALID")
        self.assertIn("authority_role_invalid", {issue.code for issue in result.issues})

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
