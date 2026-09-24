"""Pure orchestration for fail-closed T6 validation."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .authority import SignatureVerifier, validate_authority
from .documents import parse_json_document
from .handoff import parse_handoff_document, validate_handoff
from .models import Issue
from .receipt import build_receipt, validate_receipt_schema_contract


BOUND_POLICY_SHA256 = "96efdde12ad9bdb6034659070ee0b9d3333f476376234f92a548bd886b601c57"
BOUND_OUTPUT_SCHEMA_SHA256 = "08b6f36814f773a6acd2e017a64ff18b0106cd3bc0601024e723c44177823c80"
BOUND_ORACLE_SHA256 = "9b8e3fa7e5e289debc29e0f263062444b9cef3ae751b921200c8255879abd5e1"


class FailClosedValidator:
    """Validates one candidate handoff without registration or external effects."""

    def __init__(self, *, verifier: SignatureVerifier | None) -> None:
        self._verifier = verifier

    def validate(
        self,
        *,
        handoff: bytes | bytearray | str | Mapping[str, Any] | None,
        authority: bytes | bytearray | str | Mapping[str, Any] | None,
        policy: bytes | bytearray | str | Mapping[str, Any],
        output_schema: bytes | bytearray | str | Mapping[str, Any],
        oracle: bytes | bytearray | str | Mapping[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        policy_doc = parse_json_document(policy, label="$.policy")
        schema_doc = parse_json_document(output_schema, label="$.output_schema")
        oracle_doc = parse_json_document(oracle, label="$.oracle")
        authority_doc = parse_json_document(authority, label="$.authority")
        handoff_doc = parse_handoff_document(handoff)

        if schema_doc.value is None:
            raise ValueError("a valid bound output schema is required to produce any receipt")
        if schema_doc.raw_sha256 != BOUND_OUTPUT_SCHEMA_SHA256:
            raise ValueError("output schema does not match the operator-authorized digest")
        validate_receipt_schema_contract(schema_doc.value)

        configuration_issues = [*policy_doc.issues, *oracle_doc.issues]
        if policy_doc.raw_sha256 != BOUND_POLICY_SHA256:
            configuration_issues.append(Issue("policy_digest_unauthorized", "policy does not match the operator-authorized digest", "$.policy"))
        if oracle_doc.raw_sha256 != BOUND_ORACLE_SHA256:
            configuration_issues.append(Issue("oracle_digest_unauthorized", "oracle does not match the operator-authorized digest", "$.oracle"))
        configuration_issues.extend(_validate_policy(policy_doc.value))
        configuration_issues.extend(_validate_oracle(oracle_doc.value))
        if configuration_issues:
            return build_receipt(
                implementation_status="AUTHORIZED_FAIL_CLOSED_VALIDATOR",
                policy_sha256=policy_doc.raw_sha256,
                authority_envelope_sha256=authority_doc.raw_sha256,
                input_sha256=handoff_doc.binding_sha256,
                outcome="QUARANTINE",
                reason="AUTHORITY_INVALID",
                candidate_ids=(),
                issues=configuration_issues,
                schema=schema_doc.value,
            )

        authority_result = validate_authority(
            authority_doc.value,
            verifier=self._verifier,
            now=now,
            input_sha256=handoff_doc.binding_sha256,
            policy_sha256=policy_doc.raw_sha256,
            output_schema_sha256=schema_doc.raw_sha256,
            oracle_sha256=oracle_doc.raw_sha256,
        )
        authority_issues = [*authority_doc.issues, *authority_result.issues]
        if authority_issues or not authority_result.valid:
            return build_receipt(
                implementation_status="AUTHORIZED_FAIL_CLOSED_VALIDATOR",
                policy_sha256=policy_doc.raw_sha256,
                authority_envelope_sha256=authority_doc.raw_sha256,
                input_sha256=handoff_doc.binding_sha256,
                outcome="QUARANTINE",
                reason=authority_result.reason,
                candidate_ids=(),
                issues=authority_issues,
                schema=schema_doc.value,
            )

        candidate_ids, handoff_issues = validate_handoff(handoff_doc.document.value)
        all_handoff_issues = (*handoff_doc.document.issues, *handoff_issues)
        if all_handoff_issues:
            outcome, reason = "QUARANTINE", "VALIDATION_OR_CONFLICT_FAILURE"
        elif len(candidate_ids) == 1:
            outcome, reason = "ABSTAIN", "NO_CANONICAL_PROMOTION_AUTHORITY"
        else:
            outcome, reason = "ABSTAIN", "NO_RANKING_AUTHORITY"
        return build_receipt(
            implementation_status="AUTHORIZED_FAIL_CLOSED_VALIDATOR",
            policy_sha256=policy_doc.raw_sha256,
            authority_envelope_sha256=authority_doc.raw_sha256,
            input_sha256=handoff_doc.binding_sha256,
            outcome=outcome,
            reason=reason,
            candidate_ids=candidate_ids,
            issues=all_handoff_issues,
            schema=schema_doc.value,
        )


def _validate_policy(policy: Mapping[str, Any] | None) -> list[Issue]:
    if policy is None:
        return [Issue("policy_invalid", "policy is not a parsed object", "$.policy")]
    expected = {
        "allowed_outcomes": ["ABSTAIN", "QUARANTINE"],
        "candidate_ranking": "NONE",
        "canonical_promotion": "PROHIBITED",
        "external_effect_authority": "NONE",
        "external_effects_authorized": False,
    }
    issues: list[Issue] = []
    for field, value in expected.items():
        if policy.get(field) != value:
            issues.append(Issue("policy_safety_invariant_failed", f"policy field {field} is not fail-closed", f"$.policy.{field}"))
    minimum = policy.get("minimum_evidence_policy")
    if not isinstance(minimum, Mapping) or minimum.get("at_least_one_evidence_record_required") is not True or minimum.get("candidate_only_canonicality_required") is not True or minimum.get("handed_off_lifecycle_required") is not True:
        issues.append(Issue("policy_minimum_evidence_invalid", "policy minimum-evidence gates are incomplete", "$.policy.minimum_evidence_policy"))
    return issues


def _validate_oracle(oracle: Mapping[str, Any] | None) -> list[Issue]:
    if oracle is None:
        return [Issue("oracle_invalid", "oracle is not a parsed object", "$.oracle")]
    fixtures = oracle.get("fixtures")
    if not isinstance(fixtures, list) or len(fixtures) != 8:
        return [Issue("oracle_fixture_count_invalid", "oracle must contain exactly eight fixtures", "$.oracle.fixtures")]
    issues: list[Issue] = []
    ids = []
    for index, fixture in enumerate(fixtures):
        path = f"$.oracle.fixtures[{index}]"
        if not isinstance(fixture, Mapping):
            issues.append(Issue("oracle_fixture_invalid", "oracle fixture must be an object", path))
            continue
        ids.append(fixture.get("id"))
        if fixture.get("expected_outcome") not in {"ABSTAIN", "QUARANTINE"}:
            issues.append(Issue("oracle_outcome_invalid", "oracle fixture outcome is unsafe", f"{path}.expected_outcome"))
        for field in (
            "expected_canonical_store_mutation_authorized", "expected_canonical_truth_selected",
            "expected_gamma_unfrozen", "expected_ml_training_authorized", "expected_trading_authorized",
        ):
            if fixture.get(field) is not False:
                issues.append(Issue("oracle_effect_invariant_failed", f"oracle field {field} must be false", f"{path}.{field}"))
        if fixture.get("expected_external_actions") != [] or fixture.get("expected_ranked_candidate_ids") != []:
            issues.append(Issue("oracle_action_invariant_failed", "oracle actions and rankings must be empty", path))
    if len(set(ids)) != 8 or any(not isinstance(item, str) or not item for item in ids):
        issues.append(Issue("oracle_fixture_ids_invalid", "oracle fixture identifiers must be unique", "$.oracle.fixtures"))
    return issues
