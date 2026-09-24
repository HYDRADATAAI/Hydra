from __future__ import annotations

import unittest

from hydra_t6_failclosed.models import Issue
from hydra_t6_failclosed.receipt import (
    ALLOWED_OUTCOMES,
    ALLOWED_REASONS,
    RECEIPT_SCHEMA_ID,
    RECEIPT_VERSION,
    ReceiptSchemaError,
    build_receipt,
    receipt_digest,
)


def public_test_schema() -> dict[str, object]:
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


class ReceiptContractTests(unittest.TestCase):
    def test_receipt_is_deterministic_and_inert(self) -> None:
        schema = public_test_schema()
        issues = [
            Issue("z_issue", "later"),
            Issue("a_issue", "earlier"),
        ]
        left = build_receipt(
            implementation_status="AUTHORIZED_FAIL_CLOSED_VALIDATOR",
            policy_sha256="2" * 64,
            authority_envelope_sha256="3" * 64,
            input_sha256="1" * 64,
            outcome="ABSTAIN",
            reason="NO_RANKING_AUTHORITY",
            candidate_ids=["candidate-b", "candidate-a", "candidate-a"],
            issues=issues,
            schema=schema,
        )
        right = build_receipt(
            implementation_status="AUTHORIZED_FAIL_CLOSED_VALIDATOR",
            policy_sha256="2" * 64,
            authority_envelope_sha256="3" * 64,
            input_sha256="1" * 64,
            outcome="ABSTAIN",
            reason="NO_RANKING_AUTHORITY",
            candidate_ids=["candidate-a", "candidate-b"],
            issues=list(reversed(issues)),
            schema=schema,
        )

        self.assertEqual(left, right)
        self.assertEqual(left["candidate_ids"], ["candidate-a", "candidate-b"])
        self.assertFalse(left["canonical_store_mutation_authorized"])
        self.assertFalse(left["canonical_truth_selected"])
        self.assertFalse(left["ml_training_authorized"])
        self.assertFalse(left["trading_authorized"])
        self.assertEqual(left["external_actions"], [])
        self.assertEqual(left["ranked_candidate_ids"], [])
        self.assertEqual(left["receipt_sha256"], receipt_digest(left))

    def test_unsafe_outcome_is_rejected(self) -> None:
        with self.assertRaises(ReceiptSchemaError):
            build_receipt(
                implementation_status="AUTHORIZED_FAIL_CLOSED_VALIDATOR",
                policy_sha256="2" * 64,
                authority_envelope_sha256="3" * 64,
                input_sha256="1" * 64,
                outcome="PROMOTE",
                reason="NO_RANKING_AUTHORITY",
                candidate_ids=[],
                issues=[],
                schema=public_test_schema(),
            )


if __name__ == "__main__":
    unittest.main()
