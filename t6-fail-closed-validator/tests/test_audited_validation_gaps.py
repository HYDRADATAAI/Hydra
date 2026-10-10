from __future__ import annotations

import hashlib
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from hydra_t6_failclosed.documents import canonical_json_bytes
from hydra_t6_failclosed.handoff import CANDIDATE_SCHEMA, HANDOFF_CONTRACT, HANDOFF_SCHEMA
from hydra_t6_failclosed.receipt import (
    ALLOWED_OUTCOMES,
    ALLOWED_REASONS,
    RECEIPT_SCHEMA_ID,
    RECEIPT_VERSION,
)
from hydra_t6_failclosed.service import FailClosedValidator


def _public_test_schema() -> dict[str, object]:
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


def _oracle(
    *, first_id: object = "public-test-0", first_outcome: object = "ABSTAIN"
) -> dict[str, object]:
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
    fixtures = [{"id": f"public-test-{i}", **fixture} for i in range(8)]
    fixtures[0]["id"] = first_id
    fixtures[0]["expected_outcome"] = first_outcome
    return {"fixtures": fixtures}


def _handoff() -> dict[str, object]:
    candidate = {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": "candidate-001",
        "statement": {"mechanism": "Synthetic mechanism", "constrained_target": "Synthetic target"},
        "canonicality": "candidate_only",
        "lifecycle_state": "handed_off",
        "lifecycle": [{"state": "created"}, {"state": "handed_off"}],
        "evidence": [{"id": "evidence-001", "active_context": {}}],
        "provenance": {"created_by_stage": "T5"},
        "trust": {"conflicts": [], "contradiction_context": {"unresolved": []}},
        "uncertainty": {"confidence": "medium"},
        "beneficiaries": [],
        "forced_expenditures": [],
        "relations": {"claim_ids": [], "material_scope": {}},
        "temporal": {"observed_at": "2026-09-24T11:00:00Z"},
    }
    return {
        "schema": HANDOFF_SCHEMA,
        "handoff_id": "handoff-001",
        "created_at": "2026-09-24T12:00:00Z",
        "contract": HANDOFF_CONTRACT,
        "candidates": [candidate],
    }


def _service_result(handoff: dict[str, object], oracle_value: dict[str, object]) -> dict[str, object]:
    policy = canonical_json_bytes(_policy())
    schema = canonical_json_bytes(_public_test_schema())
    oracle = canonical_json_bytes(oracle_value)
    policy_digest = hashlib.sha256(policy).hexdigest()
    schema_digest = hashlib.sha256(schema).hexdigest()
    oracle_digest = hashlib.sha256(oracle).hexdigest()
    with (
        patch("hydra_t6_failclosed.service.BOUND_POLICY_SHA256", policy_digest),
        patch("hydra_t6_failclosed.service.BOUND_OUTPUT_SCHEMA_SHA256", schema_digest),
        patch("hydra_t6_failclosed.service.BOUND_ORACLE_SHA256", oracle_digest),
        patch(
            "hydra_t6_failclosed.service.validate_authority",
            return_value=SimpleNamespace(valid=True, issues=(), reason="AUTHORITY_VALID"),
        ),
    ):
        return FailClosedValidator(verifier=None).validate(
            handoff=canonical_json_bytes(handoff),
            authority=b"{}",
            policy=policy,
            output_schema=schema,
            oracle=oracle,
            now=datetime(2026, 1, 1, tzinfo=UTC),
        )


class AuditedValidationGapTests(unittest.TestCase):
    def test_list_valued_oracle_fixture_id_quarantines_without_type_error(self) -> None:
        result = _service_result(
            _handoff(),
            _oracle(first_id=["not", "hashable"]),
        )
        self.assertEqual(result["outcome"], "QUARANTINE")
        self.assertEqual(result["reason"], "AUTHORITY_INVALID")
        self.assertTrue(any(
            item["code"] == "oracle_fixture_ids_invalid"
            and item["path"] == "$.oracle.fixtures"
            for item in result["violations"]
        ))


    def test_unhashable_oracle_outcome_quarantines_without_type_error(self) -> None:
        result = _service_result(
            _handoff(),
            _oracle(first_outcome=["ABSTAIN"]),
        )
        self.assertEqual(result["outcome"], "QUARANTINE")
        self.assertEqual(result["reason"], "AUTHORITY_INVALID")
        self.assertTrue(any(
            item["code"] == "oracle_outcome_invalid"
            and item["path"] == "$.oracle.fixtures[0].expected_outcome"
            for item in result["violations"]
        ))


if __name__ == "__main__":
    unittest.main()
