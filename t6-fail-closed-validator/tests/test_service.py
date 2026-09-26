from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from hydra_t6_failclosed.authority import (
    AUTHORITY_SCHEMA,
    DECISION,
    OPERATION,
    REQUIRED_SCOPE,
    HMACSHA256Verifier,
    sign_hmac_sha256,
)
from hydra_t6_failclosed.documents import canonical_json_bytes, sha256_hex
from hydra_t6_failclosed.handoff import (
    CANDIDATE_SCHEMA,
    HANDOFF_CONTRACT,
    HANDOFF_SCHEMA,
    parse_handoff_document,
)
from hydra_t6_failclosed.receipt import (
    ALLOWED_OUTCOMES,
    ALLOWED_REASONS,
    RECEIPT_SCHEMA_ID,
    RECEIPT_VERSION,
    ReceiptSchemaError,
)
from hydra_t6_failclosed.service import FailClosedValidator


def receipt_schema() -> dict[str, object]:
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


class FailClosedServiceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 9, 25, 22, 0, tzinfo=UTC)
        self.key = b"service-integration-public-test-key"
        self.key_id = "service-integration-test-key"
        self.verifier = HMACSHA256Verifier({self.key_id: self.key})
        self.validator = FailClosedValidator(verifier=self.verifier)

    def candidate(self, candidate_id: str) -> dict[str, object]:
        return {
            "beneficiaries": [],
            "candidate_id": candidate_id,
            "canonicality": "candidate_only",
            "evidence": [{"id": f"evidence-{candidate_id}"}],
            "forced_expenditures": [],
            "lifecycle": [{"state": "handed_off"}],
            "lifecycle_state": "handed_off",
            "provenance": {"createdByStage": "T5"},
            "relations": [],
            "schema": CANDIDATE_SCHEMA,
            "statement": "synthetic infrastructure candidate",
            "temporal": {},
            "trust": {"conflicts": [], "contradiction_context": {"unresolved": []}},
            "uncertainty": {},
        }

    def handoff(self, *candidate_ids: str) -> dict[str, object]:
        return {
            "schema": HANDOFF_SCHEMA,
            "handoff_id": "public-service-handoff-001",
            "created_at": self.now.isoformat(),
            "contract": HANDOFF_CONTRACT,
            "candidates": [self.candidate(candidate_id) for candidate_id in candidate_ids],
        }

    def policy(self) -> dict[str, object]:
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

    def oracle(self) -> dict[str, object]:
        fixtures = []
        for index in range(8):
            fixtures.append({
                "id": f"public-fixture-{index + 1}",
                "expected_outcome": "ABSTAIN" if index % 2 == 0 else "QUARANTINE",
                "expected_canonical_store_mutation_authorized": False,
                "expected_canonical_truth_selected": False,
                "expected_gamma_unfrozen": False,
                "expected_ml_training_authorized": False,
                "expected_trading_authorized": False,
                "expected_external_actions": [],
                "expected_ranked_candidate_ids": [],
            })
        return {"fixtures": fixtures}

    def authority(
        self,
        *,
        handoff: dict[str, object],
        policy: dict[str, object],
        schema: dict[str, object],
        oracle: dict[str, object],
    ) -> dict[str, object]:
        handoff_sha = parse_handoff_document(handoff).binding_sha256
        envelope: dict[str, object] = {
            "schema_version": AUTHORITY_SCHEMA,
            "authority_id": "public-service-authority-001",
            "authority_name": "public-service-test-authority",
            "authority_role": "validator_authority",
            "decision": DECISION,
            "operation": OPERATION,
            "scopes": [REQUIRED_SCOPE],
            "issued_at": (self.now - timedelta(minutes=10)).isoformat(),
            "expires_at": (self.now + timedelta(hours=1)).isoformat(),
            "bindings": {
                "input_sha256": handoff_sha,
                "oracle_sha256": sha256_hex(canonical_json_bytes(oracle)),
                "output_schema_sha256": sha256_hex(canonical_json_bytes(schema)),
                "policy_sha256": sha256_hex(canonical_json_bytes(policy)),
            },
            "revocation": {
                "status": "not_revoked",
                "checked_at": (self.now - timedelta(minutes=1)).isoformat(),
                "source_id": "public-service-revocation-source",
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

    def validate(self, handoff, *, authority_mutator=None, policy_mutator=None):
        policy = self.policy()
        schema = receipt_schema()
        oracle = self.oracle()
        if policy_mutator is not None:
            policy_mutator(policy)
        authority = self.authority(
            handoff=handoff,
            policy=policy,
            schema=schema,
            oracle=oracle,
        )
        if authority_mutator is not None:
            authority_mutator(authority)

        with (
            patch(
                "hydra_t6_failclosed.service.BOUND_POLICY_SHA256",
                sha256_hex(canonical_json_bytes(policy)),
            ),
            patch(
                "hydra_t6_failclosed.service.BOUND_OUTPUT_SCHEMA_SHA256",
                sha256_hex(canonical_json_bytes(schema)),
            ),
            patch(
                "hydra_t6_failclosed.service.BOUND_ORACLE_SHA256",
                sha256_hex(canonical_json_bytes(oracle)),
            ),
        ):
            return self.validator.validate(
                handoff=handoff,
                authority=authority,
                policy=policy,
                output_schema=schema,
                oracle=oracle,
                now=self.now,
            )

    def assert_inert(self, receipt: dict[str, object]) -> None:
        self.assertFalse(receipt["canonical_store_mutation_authorized"])
        self.assertFalse(receipt["canonical_truth_selected"])
        self.assertFalse(receipt["gamma_unfrozen"])
        self.assertFalse(receipt["ml_training_authorized"])
        self.assertFalse(receipt["trading_authorized"])
        self.assertEqual(receipt["external_actions"], [])
        self.assertEqual(receipt["ranked_candidate_ids"], [])

    def test_single_candidate_composes_to_inert_abstain(self) -> None:
        receipt = self.validate(self.handoff("candidate-a"))
        self.assertEqual(receipt["outcome"], "ABSTAIN")
        self.assertEqual(receipt["reason"], "NO_CANONICAL_PROMOTION_AUTHORITY")
        self.assertEqual(receipt["candidate_ids"], ["candidate-a"])
        self.assertEqual(receipt["violations"], [])
        self.assert_inert(receipt)

    def test_multiple_candidates_compose_to_inert_no_ranking_abstain(self) -> None:
        receipt = self.validate(self.handoff("candidate-b", "candidate-a"))
        self.assertEqual(receipt["outcome"], "ABSTAIN")
        self.assertEqual(receipt["reason"], "NO_RANKING_AUTHORITY")
        self.assertEqual(receipt["candidate_ids"], ["candidate-a", "candidate-b"])
        self.assert_inert(receipt)

    def test_candidate_authority_smuggling_composes_to_quarantine(self) -> None:
        handoff = self.handoff("candidate-a")
        handoff["candidates"][0]["provenance"]["canonicalTruthSelected"] = True
        receipt = self.validate(handoff)
        self.assertEqual(receipt["outcome"], "QUARANTINE")
        self.assertEqual(receipt["reason"], "VALIDATION_OR_CONFLICT_FAILURE")
        self.assertIn(
            "candidate_authority_smuggling",
            {violation["code"] for violation in receipt["violations"]},
        )
        self.assert_inert(receipt)

    def test_invalid_authority_signature_composes_to_quarantine(self) -> None:
        def mutate(authority: dict[str, object]) -> None:
            authority["signature"] = "0" * 64

        receipt = self.validate(self.handoff("candidate-a"), authority_mutator=mutate)
        self.assertEqual(receipt["outcome"], "QUARANTINE")
        self.assertEqual(receipt["reason"], "AUTHORITY_INVALID")
        self.assertEqual(receipt["candidate_ids"], [])
        self.assertIn(
            "authority_signature_invalid",
            {violation["code"] for violation in receipt["violations"]},
        )
        self.assert_inert(receipt)

    def test_unsafe_but_digest_bound_policy_still_quarantines(self) -> None:
        def mutate(policy: dict[str, object]) -> None:
            policy["candidate_ranking"] = "ENABLED"

        receipt = self.validate(self.handoff("candidate-a"), policy_mutator=mutate)
        self.assertEqual(receipt["outcome"], "QUARANTINE")
        self.assertEqual(receipt["reason"], "AUTHORITY_INVALID")
        self.assertEqual(receipt["candidate_ids"], [])
        self.assertIn(
            "policy_safety_invariant_failed",
            {violation["code"] for violation in receipt["violations"]},
        )
        self.assert_inert(receipt)

    def test_unbound_output_schema_refuses_to_emit_receipt(self) -> None:
        handoff = self.handoff("candidate-a")
        policy = self.policy()
        schema = receipt_schema()
        oracle = self.oracle()
        authority = self.authority(
            handoff=handoff,
            policy=policy,
            schema=schema,
            oracle=oracle,
        )

        with (
            patch(
                "hydra_t6_failclosed.service.BOUND_POLICY_SHA256",
                sha256_hex(canonical_json_bytes(policy)),
            ),
            patch(
                "hydra_t6_failclosed.service.BOUND_OUTPUT_SCHEMA_SHA256",
                "f" * 64,
            ),
            patch(
                "hydra_t6_failclosed.service.BOUND_ORACLE_SHA256",
                sha256_hex(canonical_json_bytes(oracle)),
            ),
            self.assertRaises(ValueError),
        ):
            self.validator.validate(
                handoff=handoff,
                authority=authority,
                policy=policy,
                output_schema=schema,
                oracle=oracle,
                now=self.now,
            )

    def test_digest_bound_but_unsafe_output_schema_refuses_receipt(self) -> None:
        handoff = self.handoff("candidate-a")
        policy = self.policy()
        schema = receipt_schema()
        oracle = self.oracle()
        schema["properties"]["canonical_store_mutation_authorized"]["const"] = True
        authority = self.authority(
            handoff=handoff,
            policy=policy,
            schema=schema,
            oracle=oracle,
        )

        with (
            patch(
                "hydra_t6_failclosed.service.BOUND_POLICY_SHA256",
                sha256_hex(canonical_json_bytes(policy)),
            ),
            patch(
                "hydra_t6_failclosed.service.BOUND_OUTPUT_SCHEMA_SHA256",
                sha256_hex(canonical_json_bytes(schema)),
            ),
            patch(
                "hydra_t6_failclosed.service.BOUND_ORACLE_SHA256",
                sha256_hex(canonical_json_bytes(oracle)),
            ),
            self.assertRaises(ReceiptSchemaError),
        ):
            self.validator.validate(
                handoff=handoff,
                authority=authority,
                policy=policy,
                output_schema=schema,
                oracle=oracle,
                now=self.now,
            )


if __name__ == "__main__":
    unittest.main()
