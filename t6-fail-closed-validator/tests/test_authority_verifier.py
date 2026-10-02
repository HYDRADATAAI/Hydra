from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from typing import Any

from hydra_t6_failclosed.authority import (
    AUTHORITY_SCHEMA,
    DECISION,
    OPERATION,
    REQUIRED_SCOPE,
    sign_hmac_sha256,
    validate_authority,
)


class RaisingVerifier:
    def verify(self, **kwargs: Any) -> bool:
        del kwargs
        raise RuntimeError("verifier backend unavailable")


class TruthyNonBooleanVerifier:
    def verify(self, **kwargs: Any) -> Any:
        del kwargs
        return "verified"


class AuthorityVerifierFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 9, 24, 18, 0, tzinfo=UTC)
        self.key = b"public-test-key"
        self.digests = {
            "input_sha256": "1" * 64,
            "oracle_sha256": "4" * 64,
            "output_schema_sha256": "3" * 64,
            "policy_sha256": "2" * 64,
        }

    def _envelope(self) -> dict[str, object]:
        envelope: dict[str, object] = {
            "schema_version": AUTHORITY_SCHEMA,
            "authority_id": "authority-test-001",
            "authority_name": "public-test-authority",
            "authority_role": "validator_authority",
            "decision": DECISION,
            "operation": OPERATION,
            "scopes": [REQUIRED_SCOPE],
            "issued_at": (self.now - timedelta(minutes=10)).isoformat(),
            "expires_at": (self.now + timedelta(hours=1)).isoformat(),
            "bindings": dict(self.digests),
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
            "key_id": "test-key",
            "signature_method": "HMAC-SHA256",
            "signature": "",
        }
        envelope["signature"] = sign_hmac_sha256(envelope, key=self.key)
        return envelope

    def _validate(self, verifier: Any):
        return validate_authority(
            self._envelope(),
            verifier=verifier,
            now=self.now,
            **self.digests,
        )

    def test_verifier_exception_is_rejected_fail_closed(self) -> None:
        result = self._validate(RaisingVerifier())

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "AUTHORITY_INVALID")
        self.assertEqual({issue.code for issue in result.issues}, {"authority_verifier_error"})

    def test_truthy_non_boolean_result_is_not_accepted(self) -> None:
        result = self._validate(TruthyNonBooleanVerifier())

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "AUTHORITY_INVALID")
        self.assertEqual({issue.code for issue in result.issues}, {"authority_signature_invalid"})


if __name__ == "__main__":
    unittest.main()
