from __future__ import annotations

import unittest
from copy import deepcopy
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

    def _resign(self, envelope: dict[str, object]) -> dict[str, object]:
        envelope["signature"] = sign_hmac_sha256(envelope, key=self.key)
        return envelope

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

    def test_untrusted_key_is_rejected(self) -> None:
        result = validate_authority(
            self._envelope(),
            verifier=HMACSHA256Verifier({"other-key": b"other-public-test-key"}),
            now=self.now,
            input_sha256=self.input_sha256,
            policy_sha256=self.policy_sha256,
            output_schema_sha256=self.output_schema_sha256,
            oracle_sha256=self.oracle_sha256,
        )

        self.assertFalse(result.valid)
        self.assertIn("authority_signature_invalid", {issue.code for issue in result.issues})

    def test_missing_and_extra_claims_are_rejected(self) -> None:
        missing = self._envelope()
        del missing["authority_role"]
        extra = self._envelope()
        extra["promotion_authorized"] = True

        cases = [
            ("missing", missing, "authority_field_missing"),
            ("extra", extra, "authority_extra_claim"),
        ]
        for label, envelope, expected_code in cases:
            with self.subTest(case=label):
                result = self._validate(envelope)
                self.assertFalse(result.valid)
                self.assertIn(expected_code, {issue.code for issue in result.issues})

    def test_claim_and_binding_mismatches_are_rejected(self) -> None:
        cases: list[tuple[str, dict[str, object], str]] = []

        wrong_schema = self._envelope()
        wrong_schema["schema_version"] = "unsupported"
        cases.append(("schema", self._resign(wrong_schema), "authority_schema_unsupported"))

        wrong_decision = self._envelope()
        wrong_decision["decision"] = "AUTHORIZE_CANONICAL_PROMOTION"
        cases.append(("decision", self._resign(wrong_decision), "authority_decision_mismatch"))

        wrong_operation = self._envelope()
        wrong_operation["operation"] = "hydra.t6.promote"
        cases.append(("operation", self._resign(wrong_operation), "authority_operation_mismatch"))

        wrong_scope = self._envelope()
        wrong_scope["scopes"] = [REQUIRED_SCOPE, "t6.promote"]
        cases.append(("scope", self._resign(wrong_scope), "authority_scope_invalid"))

        binding_mismatch = self._envelope()
        mismatch_bindings = binding_mismatch["bindings"]
        assert isinstance(mismatch_bindings, dict)
        mismatch_bindings["input_sha256"] = "f" * 64
        cases.append(("binding_mismatch", self._resign(binding_mismatch), "authority_binding_mismatch"))

        bindings_missing = self._envelope()
        incomplete_bindings = bindings_missing["bindings"]
        assert isinstance(incomplete_bindings, dict)
        del incomplete_bindings["oracle_sha256"]
        cases.append(("bindings_missing", self._resign(bindings_missing), "authority_bindings_invalid"))

        for label, envelope, expected_code in cases:
            with self.subTest(case=label):
                result = self._validate(envelope)
                self.assertFalse(result.valid)
                self.assertEqual(result.reason, "AUTHORITY_INVALID")
                self.assertIn(expected_code, {issue.code for issue in result.issues})

    def test_revocation_failures_are_rejected(self) -> None:
        cases: list[tuple[str, dict[str, object], str, str]] = []

        revoked = self._envelope()
        revoked_evidence = revoked["revocation"]
        assert isinstance(revoked_evidence, dict)
        revoked_evidence["status"] = "revoked"
        cases.append(("revoked", self._resign(revoked), "authority_revoked", "POLICY_REVOKED"))

        stale = self._envelope()
        stale_evidence = stale["revocation"]
        assert isinstance(stale_evidence, dict)
        stale_evidence["checked_at"] = (self.now - timedelta(hours=25)).isoformat()
        cases.append(("stale", self._resign(stale), "authority_revocation_stale", "AUTHORITY_INVALID"))

        future = self._envelope()
        future_evidence = future["revocation"]
        assert isinstance(future_evidence, dict)
        future_evidence["checked_at"] = (self.now + timedelta(minutes=1)).isoformat()
        cases.append(("future", self._resign(future), "authority_revocation_future", "AUTHORITY_INVALID"))

        ambiguous = self._envelope()
        ambiguous_evidence = ambiguous["revocation"]
        assert isinstance(ambiguous_evidence, dict)
        ambiguous_evidence["status"] = "unknown"
        cases.append(("ambiguous", self._resign(ambiguous), "authority_revocation_ambiguous", "AUTHORITY_INVALID"))

        for label, envelope, expected_code, expected_reason in cases:
            with self.subTest(case=label):
                result = self._validate(envelope)
                self.assertFalse(result.valid)
                self.assertEqual(result.reason, expected_reason)
                self.assertIn(expected_code, {issue.code for issue in result.issues})

    def test_supersession_failures_are_rejected(self) -> None:
        superseded = self._envelope()
        superseded["supersession"] = {
            "status": "superseded",
            "predecessor_id": "authority-previous",
            "successor_id": "authority-next",
            "chain": ["authority-previous"],
        }

        cycle = self._envelope()
        cycle["supersession"] = {
            "status": "current",
            "predecessor_id": "authority-test-001",
            "successor_id": None,
            "chain": ["authority-test-001"],
        }

        ambiguous = self._envelope()
        ambiguous["supersession"] = {
            "status": "current",
            "predecessor_id": "authority-previous",
            "successor_id": None,
            "chain": [],
        }

        cases = [
            ("superseded", self._resign(superseded), "authority_superseded"),
            ("cycle", self._resign(cycle), "authority_supersession_cycle"),
            ("ambiguous", self._resign(ambiguous), "authority_supersession_chain_ambiguous"),
        ]
        for label, envelope, expected_code in cases:
            with self.subTest(case=label):
                result = self._validate(envelope)
                self.assertFalse(result.valid)
                self.assertIn(expected_code, {issue.code for issue in result.issues})

    def test_missing_verifier_and_naive_clock_are_rejected(self) -> None:
        envelope = self._envelope()
        missing_verifier = validate_authority(
            envelope,
            verifier=None,
            now=self.now,
            input_sha256=self.input_sha256,
            policy_sha256=self.policy_sha256,
            output_schema_sha256=self.output_schema_sha256,
            oracle_sha256=self.oracle_sha256,
        )
        naive_clock = validate_authority(
            deepcopy(envelope),
            verifier=self.verifier,
            now=self.now.replace(tzinfo=None),
            input_sha256=self.input_sha256,
            policy_sha256=self.policy_sha256,
            output_schema_sha256=self.output_schema_sha256,
            oracle_sha256=self.oracle_sha256,
        )

        self.assertFalse(missing_verifier.valid)
        self.assertIn("authority_verifier_missing", {issue.code for issue in missing_verifier.issues})
        self.assertFalse(naive_clock.valid)
        self.assertIn("authority_now_naive", {issue.code for issue in naive_clock.issues})


if __name__ == "__main__":
    unittest.main()
