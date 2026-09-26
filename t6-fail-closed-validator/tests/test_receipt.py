from __future__ import annotations

import unittest
from copy import deepcopy

from hydra_t6_failclosed.models import Issue
from hydra_t6_failclosed.receipt import (
    ALLOWED_OUTCOMES,
    ALLOWED_REASONS,
    RECEIPT_SCHEMA_ID,
    RECEIPT_VERSION,
    ReceiptSchemaError,
    build_receipt,
    receipt_digest,
    validate_receipt_schema_contract,
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

    def test_schema_contract_rejects_relaxed_effect_guards(self) -> None:
        for field in (
            "canonical_store_mutation_authorized",
            "canonical_truth_selected",
            "gamma_unfrozen",
            "ml_training_authorized",
            "trading_authorized",
        ):
            schema = deepcopy(public_test_schema())
            schema["properties"][field]["const"] = True
            with self.subTest(field=field), self.assertRaises(ReceiptSchemaError):
                validate_receipt_schema_contract(schema)

        for field in ("external_actions", "ranked_candidate_ids"):
            schema = deepcopy(public_test_schema())
            schema["properties"][field]["maxItems"] = 1
            with self.subTest(field=field), self.assertRaises(ReceiptSchemaError):
                validate_receipt_schema_contract(schema)

    def test_schema_contract_rejects_relaxed_outcomes_and_reasons(self) -> None:
        schema = deepcopy(public_test_schema())
        schema["properties"]["outcome"]["enum"] = sorted(ALLOWED_OUTCOMES | {"PROMOTE"})
        with self.assertRaises(ReceiptSchemaError):
            validate_receipt_schema_contract(schema)

        schema = deepcopy(public_test_schema())
        schema["properties"]["reason"]["enum"] = sorted(ALLOWED_REASONS | {"RANKED"})
        with self.assertRaises(ReceiptSchemaError):
            validate_receipt_schema_contract(schema)

    def test_receipt_digest_detects_payload_change(self) -> None:
        schema = public_test_schema()
        receipt = build_receipt(
            implementation_status="AUTHORIZED_FAIL_CLOSED_VALIDATOR",
            policy_sha256="2" * 64,
            authority_envelope_sha256="3" * 64,
            input_sha256="1" * 64,
            outcome="ABSTAIN",
            reason="NO_RANKING_AUTHORITY",
            candidate_ids=["candidate-a"],
            issues=[],
            schema=schema,
        )
        original = receipt["receipt_sha256"]
        receipt["candidate_ids"] = ["candidate-b"]
        self.assertNotEqual(original, receipt_digest(receipt))


if __name__ == "__main__":
    unittest.main()
