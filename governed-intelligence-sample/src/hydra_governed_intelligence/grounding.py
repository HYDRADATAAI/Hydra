"""Deterministic grounding validation for synthetic structured candidate output."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .context import (
    ContractError,
    Evidence,
    IntegrityError,
    _load_json_bytes,
    canonical_json_bytes,
    load_json_document_with_bytes,
    sha256_hex,
)
from .retrieval import (
    RetrievalPolicy,
    build_retrieval_decision,
    verify_retrieval_decision,
)


GROUNDING_POLICY_SCHEMA = "hydra-grounding-policy/v2"
CANDIDATE_SCHEMA = "hydra-synthetic-candidate-response/v1"
GROUNDING_RECEIPT_SCHEMA = "hydra-grounding-receipt/v1"
GROUNDING_SUITE_SCHEMA = "hydra-grounding-evaluation-suite/v1"
GROUNDING_REPORT_SCHEMA = "hydra-grounding-evaluation-report/v1"
GROUNDING_OUTPUT_MANIFEST_SCHEMA = "hydra-grounding-output-manifest/v1"
ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
FIELD_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
STATUS_PATTERN = re.compile(r"^[A-Z_]{1,32}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CITATION_FIELDS = {
    "artifact",
    "artifact_sha256",
    "record_id",
    "record_sha256",
}
GROUNDABLE_FIELDS = {
    "currency",
    "event_time_utc",
    "price",
    "source_system",
    "symbol",
    "venue",
    "volume",
}
GROUNDING_DISPOSITIONS = {"ABSTAIN", "ADMIT", "QUARANTINE", "REFUSE"}


@dataclass(frozen=True)
class GroundingPolicy:
    allowed_claim_fields: tuple[str, ...]
    max_claims: int
    min_claim_failures: int
    min_claim_passes: int
    required_case_ids: tuple[str, ...]
    required_dispositions: tuple[str, ...]
    sha256: str
    _source_bytes: bytes = field(default=b"", repr=False, compare=False)


def load_grounding_policy(path: str | Path) -> GroundingPolicy:
    policy_path = Path(path)
    document, policy_bytes = load_json_document_with_bytes(policy_path)
    return _grounding_policy_from_document(document, policy_bytes=policy_bytes)


def _grounding_policy_from_document(
    document: Any, *, policy_bytes: bytes
) -> GroundingPolicy:
    expected_fields = {
        "allowed_claim_fields",
        "external_actions_enabled",
        "max_claims",
        "min_claim_failures",
        "min_claim_passes",
        "model_execution_enabled",
        "required_case_ids",
        "required_dispositions",
        "schema_version",
    }
    if not isinstance(document, dict) or set(document) != expected_fields:
        raise ContractError("grounding policy fields do not match the v2 contract")
    if document["schema_version"] != GROUNDING_POLICY_SCHEMA:
        raise ContractError("unsupported grounding policy schema")
    if document["model_execution_enabled"] is not False:
        raise ContractError("grounding policy cannot enable model execution")
    if document["external_actions_enabled"] is not False:
        raise ContractError("grounding policy cannot enable external actions")

    fields = document["allowed_claim_fields"]
    if not isinstance(fields, list) or not fields:
        raise ContractError("allowed_claim_fields must be a non-empty list")
    if any(not isinstance(field, str) or not FIELD_PATTERN.fullmatch(field) for field in fields):
        raise ContractError("allowed_claim_fields contains an invalid field")
    if fields != sorted(set(fields)):
        raise ContractError("allowed_claim_fields must be sorted and unique")
    if set(fields) != GROUNDABLE_FIELDS:
        raise ContractError("allowed_claim_fields must match the v2 claim boundary")

    max_claims = document["max_claims"]
    if not isinstance(max_claims, int) or isinstance(max_claims, bool):
        raise ContractError("max_claims must be an integer")
    if not 1 <= max_claims <= 20:
        raise ContractError("max_claims must be between 1 and 20")

    minimums = {}
    for field in ("min_claim_failures", "min_claim_passes"):
        value = document[field]
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 20:
            raise ContractError(f"{field} must be an integer between 1 and 20")
        minimums[field] = value

    required_dispositions = document["required_dispositions"]
    if (
        not isinstance(required_dispositions, list)
        or required_dispositions != sorted(GROUNDING_DISPOSITIONS)
    ):
        raise ContractError("required_dispositions must contain every v2 disposition")
    required_case_ids = document["required_case_ids"]
    if (
        not isinstance(required_case_ids, list)
        or not required_case_ids
        or any(not isinstance(case_id, str) or not ID_PATTERN.fullmatch(case_id) for case_id in required_case_ids)
    ):
        raise ContractError("required_case_ids must be sorted, unique, valid identifiers")
    if required_case_ids != sorted(set(required_case_ids)):
        raise ContractError("required_case_ids must be sorted, unique, valid identifiers")

    return GroundingPolicy(
        allowed_claim_fields=tuple(fields),
        max_claims=max_claims,
        min_claim_failures=minimums["min_claim_failures"],
        min_claim_passes=minimums["min_claim_passes"],
        required_case_ids=tuple(required_case_ids),
        required_dispositions=tuple(required_dispositions),
        sha256=sha256_hex(policy_bytes),
        _source_bytes=policy_bytes,
    )


def build_grounding_receipt(
    *,
    retrieval_request: Mapping[str, Any],
    candidate: Mapping[str, Any],
    evidence: Evidence,
    retrieval_policy: RetrievalPolicy,
    grounding_policy: GroundingPolicy,
) -> dict[str, Any]:
    _validate_grounding_policy_instance(grounding_policy)
    try:
        candidate_snapshot = _json_copy(candidate)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"candidate must contain finite JSON values: {exc}") from exc
    _validate_candidate(
        candidate_snapshot,
        policy=grounding_policy,
        expected_artifact=evidence.normalized_filename,
    )
    retrieval = build_retrieval_decision(
        retrieval_request,
        evidence=evidence,
        policy=retrieval_policy,
    )
    verify_retrieval_decision(
        retrieval,
        evidence=evidence,
        policy=retrieval_policy,
    )
    candidate_reasons = _candidate_reasons(
        candidate_snapshot, retrieval_request_id=retrieval["request_id"]
    )
    claim_results, claim_reasons = _evaluate_claim_safety(
        candidate_snapshot,
        policy=grounding_policy,
    )
    aggregate_reasons = candidate_reasons + claim_reasons

    if retrieval["disposition"] == "REFUSE":
        return _receipt(
            candidate=candidate_snapshot,
            evidence=evidence,
            retrieval=retrieval,
            grounding_policy=grounding_policy,
            disposition="QUARANTINE" if aggregate_reasons else "REFUSE",
            reason_codes=aggregate_reasons + ["retrieval_refused"],
            claim_results=claim_results,
        )
    if retrieval["disposition"] != "ADMIT":
        return _receipt(
            candidate=candidate_snapshot,
            evidence=evidence,
            retrieval=retrieval,
            grounding_policy=grounding_policy,
            disposition="QUARANTINE" if aggregate_reasons else "ABSTAIN",
            reason_codes=aggregate_reasons + ["retrieval_not_admitted"],
            claim_results=claim_results,
        )

    if not candidate_snapshot["claims"]:
        aggregate_reasons.append("claims_required")

    context = retrieval["context"]
    records_by_id = {
        item["record"]["event_id"]: item["record"]
        for item in context["results"]
    }
    citations_by_id = {
        citation["record_id"]: citation for citation in retrieval["citations"]
    }
    for claim, claim_result in zip(candidate_snapshot["claims"], claim_results):
        reasons = claim_result["reason_codes"]
        record = records_by_id.get(claim["record_id"])
        if record is None:
            reasons.append("record_outside_retrieved_context")
        else:
            field = claim["field"]
            if field in grounding_policy.allowed_claim_fields and canonical_json_bytes(
                claim["value"]
            ) != canonical_json_bytes(record[field]):
                reasons.append("claim_value_mismatch")
            if claim["citation"] != citations_by_id.get(claim["record_id"]):
                reasons.append("citation_mismatch")

        for reason in reasons:
            if reason not in aggregate_reasons:
                aggregate_reasons.append(reason)
        claim_result["status"] = "FAIL" if reasons else "PASS"

    if aggregate_reasons:
        return _receipt(
            candidate=candidate_snapshot,
            evidence=evidence,
            retrieval=retrieval,
            grounding_policy=grounding_policy,
            disposition="QUARANTINE",
            reason_codes=aggregate_reasons,
            claim_results=claim_results,
        )

    unique_citations: list[dict[str, Any]] = []
    seen_record_ids: set[str] = set()
    for claim in candidate_snapshot["claims"]:
        if claim["record_id"] not in seen_record_ids:
            unique_citations.append(_json_copy(claim["citation"]))
            seen_record_ids.add(claim["record_id"])
    return _receipt(
        candidate=candidate_snapshot,
        evidence=evidence,
        retrieval=retrieval,
        grounding_policy=grounding_policy,
        disposition="ADMIT",
        reason_codes=["grounded_claims_verified"],
        claim_results=claim_results,
        citations=unique_citations,
        grounded_claims=[_json_copy(claim) for claim in candidate_snapshot["claims"]],
    )


def verify_grounding_receipt(
    receipt: Mapping[str, Any],
    *,
    retrieval_request: Mapping[str, Any],
    candidate: Mapping[str, Any],
    evidence: Evidence,
    retrieval_policy: RetrievalPolicy,
    grounding_policy: GroundingPolicy,
) -> None:
    if type(receipt) is not dict:
        raise IntegrityError("grounding receipt must be an object")
    _require_canonical_receipt_value(receipt)
    if receipt.get("schema_version") != GROUNDING_RECEIPT_SCHEMA:
        raise IntegrityError("grounding receipt schema is invalid")
    if receipt.get("model_execution") != {
        "authorized": False,
        "status": "NOT_EXECUTED",
    }:
        raise IntegrityError("grounding receipt must keep model execution disabled")
    if receipt.get("external_actions") != {
        "authorized": False,
        "status": "NOT_EXECUTED",
    }:
        raise IntegrityError("grounding receipt must keep external actions disabled")
    if _contains_exact_key(receipt, "raw_record"):
        raise IntegrityError("grounding receipt exposes a quarantined raw record")

    expected = build_grounding_receipt(
        retrieval_request=retrieval_request,
        candidate=candidate,
        evidence=evidence,
        retrieval_policy=retrieval_policy,
        grounding_policy=grounding_policy,
    )
    if canonical_json_bytes(receipt) != canonical_json_bytes(expected):
        raise IntegrityError("grounding receipt does not match governed recomputation")


def _require_canonical_receipt_value(value: Any) -> None:
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise IntegrityError("grounding receipt structure is invalid")
            _require_canonical_receipt_value(item)
        return
    if type(value) is list:
        for item in value:
            _require_canonical_receipt_value(item)
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise IntegrityError("grounding receipt structure is invalid")
        return
    if value is None or type(value) in {bool, int, str}:
        return
    raise IntegrityError("grounding receipt structure is invalid")


def run_grounding_evaluation(
    *,
    cases_path: str | Path,
    evidence: Evidence,
    retrieval_policy: RetrievalPolicy,
    grounding_policy: GroundingPolicy,
    output_dir: str | Path,
) -> dict[str, Any]:
    _validate_grounding_policy_instance(grounding_policy)
    suite_path = Path(cases_path)
    suite, suite_bytes = load_json_document_with_bytes(suite_path)
    if not isinstance(suite, dict) or set(suite) != {"cases", "schema_version"}:
        raise ContractError("grounding suite fields do not match the v1 contract")
    if suite["schema_version"] != GROUNDING_SUITE_SCHEMA:
        raise ContractError("unsupported grounding suite schema")
    cases = suite["cases"]
    if not isinstance(cases, list) or not cases:
        raise ContractError("grounding suite must contain cases")

    receipts: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    counts = {"ABSTAIN": 0, "ADMIT": 0, "QUARANTINE": 0, "REFUSE": 0}
    expectation_matches = 0
    integrity_passes = 0
    claim_passes = 0
    claim_failures = 0
    rejected_execution_claims = 0
    unauthorized_model_executions = 0
    unauthorized_external_actions = 0
    quarantined_raw_records_exposed = 0
    seen_case_ids: set[str] = set()

    for case in cases:
        case_id, request, candidate, expected = _validate_case(case)
        if case_id in seen_case_ids:
            raise ContractError(f"duplicate grounding case_id: {case_id}")
        seen_case_ids.add(case_id)

        receipt = build_grounding_receipt(
            retrieval_request=request,
            candidate=candidate,
            evidence=evidence,
            retrieval_policy=retrieval_policy,
            grounding_policy=grounding_policy,
        )
        verify_grounding_receipt(
            receipt,
            retrieval_request=request,
            candidate=candidate,
            evidence=evidence,
            retrieval_policy=retrieval_policy,
            grounding_policy=grounding_policy,
        )
        integrity_passes += 1
        counts[receipt["disposition"]] += 1
        claim_passes += sum(
            result["status"] == "PASS" for result in receipt["claim_results"]
        )
        claim_failures += sum(
            result["status"] == "FAIL" for result in receipt["claim_results"]
        )
        if "candidate_model_execution_claim_rejected" in receipt["reason_codes"]:
            rejected_execution_claims += 1
        if receipt["model_execution"] != {
            "authorized": False,
            "status": "NOT_EXECUTED",
        }:
            unauthorized_model_executions += 1
        if receipt["external_actions"] != {
            "authorized": False,
            "status": "NOT_EXECUTED",
        }:
            unauthorized_external_actions += 1
        if _contains_exact_key(receipt, "raw_record"):
            quarantined_raw_records_exposed += 1

        mismatches = []
        if receipt["disposition"] != expected["disposition"]:
            mismatches.append("disposition")
        if receipt["reason_codes"] != expected["reason_codes"]:
            mismatches.append("reason_codes")
        if len(receipt["grounded_claims"]) != expected["grounded_claim_count"]:
            mismatches.append("grounded_claim_count")
        if mismatches:
            failures.append({"case_id": case_id, "mismatch": ",".join(mismatches)})
        else:
            expectation_matches += 1
        receipts.append({"case_id": case_id, "receipt": receipt})

    required_disposition_count = sum(
        counts[disposition] > 0
        for disposition in grounding_policy.required_dispositions
    )
    required_case_count = sum(
        case_id in seen_case_ids for case_id in grounding_policy.required_case_ids
    )
    coverage_pass = (
        required_disposition_count == len(grounding_policy.required_dispositions)
        and required_case_count == len(grounding_policy.required_case_ids)
        and claim_passes >= grounding_policy.min_claim_passes
        and claim_failures >= grounding_policy.min_claim_failures
    )
    report = {
        "case_count": len(cases),
        "checks": {
            "candidate_execution_claim_rejected_count": rejected_execution_claims,
            "claim_fail_count": claim_failures,
            "claim_pass_count": claim_passes,
            "expectation_match_count": expectation_matches,
            "grounding_integrity_pass_count": integrity_passes,
            "quarantined_raw_records_exposed_count": quarantined_raw_records_exposed,
            "required_disposition_count": required_disposition_count,
            "required_disposition_total": len(grounding_policy.required_dispositions),
            "required_case_count": required_case_count,
            "required_case_total": len(grounding_policy.required_case_ids),
            "proof_coverage_status": "PASS" if coverage_pass else "FAIL",
            "unauthorized_external_action_count": unauthorized_external_actions,
            "unauthorized_model_execution_count": unauthorized_model_executions,
        },
        "disposition_counts": counts,
        "failures": failures,
        "input_binding": {
            "grounding_policy_sha256": grounding_policy.sha256,
            "grounding_suite_sha256": sha256_hex(suite_bytes),
            "pipeline_manifest_sha256": evidence.manifest_sha256,
            "retrieval_policy_sha256": retrieval_policy.sha256,
        },
        "schema_version": GROUNDING_REPORT_SCHEMA,
        "status": "PASS"
        if not failures
        and coverage_pass
        and unauthorized_model_executions == 0
        and unauthorized_external_actions == 0
        and quarantined_raw_records_exposed == 0
        else "FAIL",
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    receipts_path = output_root / "grounding_receipts.jsonl"
    report_path = output_root / "grounding_evaluation_report.json"
    manifest_path = output_root / "grounding_output_manifest.json"
    receipts_bytes = b"".join(canonical_json_bytes(item) + b"\n" for item in receipts)
    report_bytes = _pretty_json_bytes(report)
    receipts_path.write_bytes(receipts_bytes)
    report_path.write_bytes(report_bytes)
    manifest = {
        "input_binding": report["input_binding"],
        "outputs": {
            "grounding_evaluation_report": {
                "file": report_path.name,
                "sha256": sha256_hex(report_bytes),
            },
            "grounding_receipts_jsonl": {
                "file": receipts_path.name,
                "sha256": sha256_hex(receipts_bytes),
            },
        },
        "schema_version": GROUNDING_OUTPUT_MANIFEST_SCHEMA,
    }
    manifest_path.write_bytes(_pretty_json_bytes(manifest))
    return report


def _receipt(
    *,
    candidate: Mapping[str, Any],
    evidence: Evidence,
    retrieval: Mapping[str, Any],
    grounding_policy: GroundingPolicy,
    disposition: str,
    reason_codes: list[str],
    claim_results: list[dict[str, Any]] | None = None,
    citations: list[dict[str, Any]] | None = None,
    grounded_claims: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    candidate_binding = (
        {
            "sha256": sha256_hex(canonical_json_bytes(candidate)),
            "status": "DISCLOSED_AND_BOUND",
        }
        if disposition == "ADMIT"
        else {"status": "VERIFIED_IN_PROCESS_NOT_DISCLOSED"}
    )
    return {
        "candidate_response_id": candidate["response_id"] if disposition == "ADMIT" else None,
        "citations": citations or [],
        "claim_results": claim_results or [],
        "disposition": disposition,
        "external_actions": {"authorized": False, "status": "NOT_EXECUTED"},
        "grounded_claims": grounded_claims or [],
        "input_binding": {
            "candidate": candidate_binding,
            "grounding_policy_sha256": grounding_policy.sha256,
            "pipeline_manifest_sha256": evidence.manifest_sha256,
            "retrieval_decision_sha256": sha256_hex(
                canonical_json_bytes(retrieval)
            ),
        },
        "model_execution": {"authorized": False, "status": "NOT_EXECUTED"},
        "reason_codes": reason_codes,
        "request_id": retrieval["request_id"],
        "schema_version": GROUNDING_RECEIPT_SCHEMA,
    }


def _candidate_reasons(
    candidate: Mapping[str, Any], *, retrieval_request_id: str
) -> list[str]:
    reasons = []
    if candidate["request_id"] != retrieval_request_id:
        reasons.append("candidate_request_binding_mismatch")
    if candidate["producer"] != "synthetic_fixture":
        reasons.append("candidate_producer_not_allowed")
    if candidate["model_execution_status"] != "NOT_EXECUTED":
        reasons.append("candidate_model_execution_claim_rejected")
    if candidate["external_actions_requested"] is not False:
        reasons.append("external_actions_requested")
    return reasons


def _evaluate_claim_safety(
    candidate: Mapping[str, Any], *, policy: GroundingPolicy
) -> tuple[list[dict[str, Any]], list[str]]:
    seen_claim_ids: set[str] = set()
    claim_results: list[dict[str, Any]] = []
    aggregate_reasons: list[str] = []

    for claim_index, claim in enumerate(candidate["claims"], start=1):
        reasons: list[str] = []
        claim_id = claim["claim_id"]
        if claim_id in seen_claim_ids:
            reasons.append("duplicate_claim_id")
        seen_claim_ids.add(claim_id)

        if claim["field"] not in policy.allowed_claim_fields:
            reasons.append("field_not_allowed")

        for reason in reasons:
            if reason not in aggregate_reasons:
                aggregate_reasons.append(reason)
        claim_results.append(
            {
                "claim_index": claim_index,
                "reason_codes": reasons,
                "status": "FAIL" if reasons else "PASS",
            }
        )

    return claim_results, aggregate_reasons


def _validate_grounding_policy_instance(policy: GroundingPolicy) -> None:
    if type(policy) is not GroundingPolicy:
        raise ContractError("grounding policy must be loaded from the v2 contract")
    if (
        type(policy.allowed_claim_fields) is not tuple
        or any(type(item) is not str for item in policy.allowed_claim_fields)
        or type(policy.max_claims) is not int
        or type(policy.min_claim_failures) is not int
        or type(policy.min_claim_passes) is not int
        or type(policy.required_case_ids) is not tuple
        or any(type(item) is not str for item in policy.required_case_ids)
        or type(policy.required_dispositions) is not tuple
        or any(type(item) is not str for item in policy.required_dispositions)
        or type(policy.sha256) is not str
        or type(policy._source_bytes) is not bytes
    ):
        raise ContractError("grounding policy semantic controls are invalid")
    if not policy._source_bytes:
        raise ContractError("grounding policy must be loaded from the v2 contract")
    if sha256_hex(policy._source_bytes) != policy.sha256:
        raise ContractError("grounding policy source binding is invalid")
    try:
        document = _load_json_bytes(
            policy._source_bytes, Path("<grounding policy snapshot>")
        )
        expected = _grounding_policy_from_document(
            document, policy_bytes=policy._source_bytes
        )
    except (ContractError, UnicodeError, ValueError) as exc:
        raise ContractError(
            f"grounding policy source snapshot is invalid: {exc}"
        ) from exc
    if policy != expected:
        raise ContractError("grounding policy semantics do not match the loaded policy")
    if policy.allowed_claim_fields != tuple(sorted(GROUNDABLE_FIELDS)):
        raise ContractError("grounding policy claim boundary is invalid")
    if policy.required_dispositions != tuple(sorted(GROUNDING_DISPOSITIONS)):
        raise ContractError("grounding policy disposition coverage is invalid")
    if (
        not policy.required_case_ids
        or policy.required_case_ids != tuple(sorted(set(policy.required_case_ids)))
        or any(
            not isinstance(case_id, str) or not ID_PATTERN.fullmatch(case_id)
            for case_id in policy.required_case_ids
        )
    ):
        raise ContractError("grounding policy case coverage is invalid")
    if not 1 <= policy.max_claims <= 20:
        raise ContractError("grounding policy max_claims is invalid")
    if not 1 <= policy.min_claim_failures <= 20 or not 1 <= policy.min_claim_passes <= 20:
        raise ContractError("grounding policy claim coverage is invalid")
    if not SHA256_PATTERN.fullmatch(policy.sha256):
        raise ContractError("grounding policy digest is invalid")

def _json_copy(value: Any) -> Any:
    return json.loads(canonical_json_bytes(value))


def _validate_candidate(
    candidate: Mapping[str, Any],
    *,
    policy: GroundingPolicy,
    expected_artifact: str,
) -> None:
    expected_fields = {
        "claims",
        "external_actions_requested",
        "model_execution_status",
        "producer",
        "request_id",
        "response_id",
        "schema_version",
    }
    if not isinstance(candidate, Mapping) or set(candidate) != expected_fields:
        raise ContractError("candidate fields do not match the v1 contract")
    if candidate["schema_version"] != CANDIDATE_SCHEMA:
        raise ContractError("unsupported candidate schema")
    for field in ("request_id", "response_id"):
        if not isinstance(candidate[field], str) or not ID_PATTERN.fullmatch(candidate[field]):
            raise ContractError(f"candidate {field} is invalid")
    if (
        not isinstance(candidate["producer"], str)
        or not FIELD_PATTERN.fullmatch(candidate["producer"])
    ):
        raise ContractError("candidate producer is invalid")
    if (
        not isinstance(candidate["model_execution_status"], str)
        or not STATUS_PATTERN.fullmatch(candidate["model_execution_status"])
    ):
        raise ContractError("candidate model_execution_status is invalid")
    if not isinstance(candidate["external_actions_requested"], bool):
        raise ContractError("candidate external_actions_requested must be a boolean")

    claims = candidate["claims"]
    if not isinstance(claims, list) or len(claims) > policy.max_claims:
        raise ContractError(f"candidate claims must contain at most {policy.max_claims} items")
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {
            "citation",
            "claim_id",
            "field",
            "record_id",
            "value",
        }:
            raise ContractError("candidate claim fields do not match the v1 contract")
        if not isinstance(claim["claim_id"], str) or not ID_PATTERN.fullmatch(claim["claim_id"]):
            raise ContractError("candidate claim_id is invalid")
        if not isinstance(claim["record_id"], str) or not SHA256_PATTERN.fullmatch(
            claim["record_id"]
        ):
            raise ContractError("candidate claim record_id is invalid")
        if not isinstance(claim["field"], str) or not FIELD_PATTERN.fullmatch(claim["field"]):
            raise ContractError("candidate claim field is invalid")
        if type(claim["value"]) not in {bool, float, int, str}:
            raise ContractError("candidate claim value must be a JSON scalar")
        citation = claim["citation"]
        if not isinstance(citation, dict) or set(citation) != CITATION_FIELDS:
            raise ContractError("candidate citation fields do not match the v1 contract")
        if citation["artifact"] != expected_artifact:
            raise ContractError("candidate citation artifact is invalid")
        for field in ("artifact_sha256", "record_id", "record_sha256"):
            if not isinstance(citation[field], str) or not SHA256_PATTERN.fullmatch(
                citation[field]
            ):
                raise ContractError(f"candidate citation {field} is invalid")
        if citation["record_id"] != claim["record_id"]:
            raise ContractError("candidate claim and citation record_id differ")


def _validate_case(
    case: Any,
) -> tuple[str, Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    if not isinstance(case, dict) or set(case) != {
        "candidate",
        "case_id",
        "expected",
        "retrieval_request",
    }:
        raise ContractError("grounding case fields do not match the v1 contract")
    case_id = case["case_id"]
    if not isinstance(case_id, str) or not ID_PATTERN.fullmatch(case_id):
        raise ContractError("grounding case_id is invalid")
    request = case["retrieval_request"]
    candidate = case["candidate"]
    expected = case["expected"]
    if not isinstance(request, dict) or not isinstance(candidate, dict):
        raise ContractError(f"grounding case inputs must be objects: {case_id}")
    if not isinstance(expected, dict) or set(expected) != {
        "disposition",
        "grounded_claim_count",
        "reason_codes",
    }:
        raise ContractError(f"grounding expectation is invalid: {case_id}")
    if not isinstance(expected["disposition"], str) or expected["disposition"] not in {
        "ADMIT",
        "ABSTAIN",
        "QUARANTINE",
        "REFUSE",
    }:
        raise ContractError(f"grounding disposition is invalid: {case_id}")
    reasons = expected["reason_codes"]
    if not isinstance(reasons, list) or not reasons or any(
        not isinstance(reason, str) or not FIELD_PATTERN.fullmatch(reason)
        for reason in reasons
    ):
        raise ContractError(f"grounding reason_codes is invalid: {case_id}")
    grounded_count = expected["grounded_claim_count"]
    if (
        not isinstance(grounded_count, int)
        or isinstance(grounded_count, bool)
        or grounded_count < 0
    ):
        raise ContractError(f"grounding grounded_claim_count is invalid: {case_id}")
    return case_id, request, candidate, expected


def _pretty_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _contains_exact_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_exact_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_exact_key(item, key) for item in value)
    return False
