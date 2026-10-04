from __future__ import annotations

import hashlib
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from hydra_t6_failclosed.authority import (
    AUTHORITY_SCHEMA,
    DECISION,
    OPERATION,
    REQUIRED_SCOPE,
    HMACSHA256Verifier,
    authority_signing_bytes,
    sign_hmac_sha256,
)
from hydra_t6_failclosed.documents import canonical_json_bytes
from hydra_t6_failclosed.handoff import parse_handoff_document
from hydra_t6_failclosed.service import FailClosedValidator


def public_test_schema() -> dict[str, object]:
    """Return a safe, self-contained receipt schema for this service test."""
    properties: dict[str, object] = {
        "authority_envelope_sha256": {"type": "string"},
        "candidate_ids": {"type": "array", "uniqueItems": True},
        "canonical_store_mutation_authorized": {"type": "boolean", "const": False},
        "canonical_truth_selected": {"type": "boolean", "const": False},
        "external_actions": {"type": "array", "maxItems": 0},
        "gamma_unfrozen": {"type": "boolean", "const": False},
        "implementation_status": {"type": "string"},
        "input_sha256": {"type": "string"},
        "ml_training_authorized": {"type": "boolean", "const": False},
        "outcome": {"type": "string", "enum": sorted(ALLOWED_OUTCOMES)},
        "policy_sha256": {"type": "string"},
        "ranked_candidate_ids": {"type": "array", "maxItems": 0},
        "reason": {"type": "string", "enum": sorted(ALLOWED_REASONS)},
        "receipt_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "schema_version": {"type": "string", "const": RECEIPT_VERSION},
        "trading_authorized": {"type": "boolean", "const": False},
        "violations": {"type": "array"},
    }
    return {
        "$id": RECEIPT_SCHEMA_ID,
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
from hydra_t6_failclosed.receipt import (
    ALLOWED_OUTCOMES,
    ALLOWED_REASONS,
    RECEIPT_SCHEMA_ID,
    RECEIPT_VERSION,
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _policy() -> dict[str, object]:
    return {
        "allowed_outcomes": ["ABSTAIN", "QUARANTINE"],
        "candidate_ranking": "NONE",
        "canonical_promotion": "PROHIBITED",
        "external_effect_authority": "NONE",
        "external_effects_authorized": False,
        "minimum_evidence_policy": {
            "at_least_one_evidence_record_required": True,
            "candidate_only_canonicality_required": True,
            "handed_off_lifecycle_required": True,
        },
    }


def _oracle() -> dict[str, object]:
    fixture: dict[str, object] = {
        "expected_outcome": "ABSTAIN",
        "expected_canonical_store_mutation_authorized": False,
        "expected_canonical_truth_selected": False,
        "expected_gamma_unfrozen": False,
        "expected_ml_training_authorized": False,
        "expected_trading_authorized": False,
        "expected_external_actions": [],
        "expected_ranked_candidate_ids": [],
    }
    return {"fixtures": [{"id": f"public-test-{i}", **fixture} for i in range(8)]}


class ServiceAuthorityRoleTests(unittest.TestCase):
    def test_valid_hmac_with_ungranted_role_is_quarantined(self) -> None:
        key_id = "public-test-key"
        key = b"public synthetic service test key"
        verifier = HMACSHA256Verifier(
            {key_id: key},
            trusted_key_roles={key_id: {"validator_authority"}},
        )
        now = datetime(2026, 9, 25, 22, 0, tzinfo=UTC)

        # These local synthetic inputs isolate the authority-role check. Patch
        # the service's pinned digests only for this test invocation.
        handoff = b"{}"
        policy = canonical_json_bytes(_policy())
        output_schema = canonical_json_bytes(public_test_schema())
        oracle = canonical_json_bytes(_oracle())
        input_digest = parse_handoff_document(handoff).binding_sha256
        policy_digest = _sha256(policy)
        schema_digest = _sha256(output_schema)
        oracle_digest = _sha256(oracle)

        authority: dict[str, object] = {
            "schema_version": AUTHORITY_SCHEMA,
            "authority_id": "public-wrong-role-test",
            "authority_name": "public synthetic authority",
            "authority_role": "UNGRANTED_ROLE",
            "decision": DECISION,
            "operation": OPERATION,
            "scopes": [REQUIRED_SCOPE],
            "issued_at": "2026-09-25T21:00:00+00:00",
            "expires_at": "2026-09-25T23:00:00+00:00",
            "bindings": {
                "input_sha256": input_digest,
                "oracle_sha256": oracle_digest,
                "output_schema_sha256": schema_digest,
                "policy_sha256": policy_digest,
            },
            "revocation": {
                "status": "not_revoked",
                "checked_at": "2026-09-25T21:59:00+00:00",
                "source_id": "public-test-revocation-source",
                "sequence": 1,
            },
            "supersession": {
                "status": "current",
                "predecessor_id": None,
                "successor_id": None,
                "chain": [],
            },
            "key_id": key_id,
            "signature_method": "HMAC-SHA256",
            "signature": "",
        }
        authority["signature"] = sign_hmac_sha256(authority, key=key)
        self.assertIs(
            verifier.verify(
                key_id=key_id,
                message=authority_signing_bytes(authority),
                signature=authority["signature"],
                method="HMAC-SHA256",
            ),
            True,
        )

        with (
            patch("hydra_t6_failclosed.service.BOUND_POLICY_SHA256", policy_digest),
            patch("hydra_t6_failclosed.service.BOUND_OUTPUT_SCHEMA_SHA256", schema_digest),
            patch("hydra_t6_failclosed.service.BOUND_ORACLE_SHA256", oracle_digest),
        ):
            result = FailClosedValidator(verifier=verifier).validate(
                handoff=handoff,
                authority=canonical_json_bytes(authority),
                policy=policy,
                output_schema=output_schema,
                oracle=oracle,
                now=now,
            )

        self.assertEqual(result["outcome"], "QUARANTINE")
        self.assertEqual(result["reason"], "AUTHORITY_INVALID")
        self.assertEqual(result["candidate_ids"], [])
        self.assertTrue(
            any(
                violation["code"] == "authority_key_role_untrusted"
                and violation["path"] == "$.authority.authority_role"
                for violation in result["violations"]
            )
        )


if __name__ == "__main__":
    unittest.main()
