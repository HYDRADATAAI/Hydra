"""Deterministic evaluation receipts for governed context decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .context import (
    ContractError,
    Evidence,
    Policy,
    build_decision,
    canonical_json_bytes,
    load_json_document,
    sha256_hex,
    verify_decision,
)


EVALUATION_SCHEMA = "hydra-governed-intelligence-evaluation-suite/v1"
REPORT_SCHEMA = "hydra-governed-intelligence-evaluation-report/v1"
OUTPUT_MANIFEST_SCHEMA = "hydra-governed-intelligence-output-manifest/v1"


def run_evaluation(
    *,
    cases_path: str | Path,
    evidence: Evidence,
    policy: Policy,
    output_dir: str | Path,
) -> dict[str, Any]:
    suite_path = Path(cases_path)
    suite = load_json_document(suite_path)
    if not isinstance(suite, dict) or set(suite) != {"schema_version", "cases"}:
        raise ContractError("evaluation suite fields do not match the v1 contract")
    if suite["schema_version"] != EVALUATION_SCHEMA:
        raise ContractError("unsupported evaluation suite schema")
    cases = suite["cases"]
    if not isinstance(cases, list) or not cases:
        raise ContractError("evaluation suite must contain cases")

    failures: list[dict[str, str]] = []
    decisions: list[dict[str, Any]] = []
    disposition_counts = {"ABSTAIN": 0, "ADMIT": 0, "REFUSE": 0}
    disposition_matches = 0
    citation_integrity_passes = 0
    unauthorized_model_executions = 0
    quarantined_raw_records_exposed = 0
    seen_case_ids: set[str] = set()

    for case in cases:
        case_id, request, expected = _validate_case(case)
        if case_id in seen_case_ids:
            raise ContractError(f"duplicate evaluation case_id: {case_id}")
        seen_case_ids.add(case_id)

        decision = build_decision(request, evidence=evidence, policy=policy)
        verify_decision(decision, evidence=evidence, policy=policy)
        citation_integrity_passes += 1
        disposition_counts[decision["disposition"]] += 1
        if decision["model_execution"] != {"authorized": False, "status": "NOT_EXECUTED"}:
            unauthorized_model_executions += 1
        if _contains_exact_key(decision, "raw_record"):
            quarantined_raw_records_exposed += 1

        mismatches = []
        if decision["disposition"] != expected["disposition"]:
            mismatches.append("disposition")
        if expected["reason_code"] not in decision["reason_codes"]:
            mismatches.append("reason_code")
        if len(decision["citations"]) != expected["citation_count"]:
            mismatches.append("citation_count")
        if mismatches:
            failures.append({"case_id": case_id, "mismatch": ",".join(mismatches)})
        else:
            disposition_matches += 1
        decisions.append({"case_id": case_id, "decision": decision})

    report = {
        "case_count": len(cases),
        "checks": {
            "citation_integrity_pass_count": citation_integrity_passes,
            "disposition_match_count": disposition_matches,
            "quarantined_raw_records_exposed_count": quarantined_raw_records_exposed,
            "unauthorized_model_execution_count": unauthorized_model_executions,
        },
        "disposition_counts": disposition_counts,
        "failures": failures,
        "input_binding": {
            "evaluation_suite_sha256": sha256_hex(suite_path.read_bytes()),
            "pipeline_manifest_sha256": evidence.manifest_sha256,
            "policy_sha256": policy.sha256,
        },
        "schema_version": REPORT_SCHEMA,
        "status": "PASS"
        if not failures
        and unauthorized_model_executions == 0
        and quarantined_raw_records_exposed == 0
        else "FAIL",
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    decisions_path = output_root / "decisions.jsonl"
    report_path = output_root / "evaluation_report.json"
    manifest_path = output_root / "output_manifest.json"
    decisions_path.write_bytes(b"".join(canonical_json_bytes(item) + b"\n" for item in decisions))
    report_path.write_bytes(_pretty_json_bytes(report))
    output_manifest = {
        "input_binding": report["input_binding"],
        "outputs": {
            "decisions_jsonl": {
                "file": decisions_path.name,
                "sha256": sha256_hex(decisions_path.read_bytes()),
            },
            "evaluation_report": {
                "file": report_path.name,
                "sha256": sha256_hex(report_path.read_bytes()),
            },
        },
        "schema_version": OUTPUT_MANIFEST_SCHEMA,
    }
    manifest_path.write_bytes(_pretty_json_bytes(output_manifest))
    return report


def _validate_case(
    case: Any,
) -> tuple[str, Mapping[str, Any], Mapping[str, Any]]:
    if not isinstance(case, dict) or set(case) != {"case_id", "request", "expected"}:
        raise ContractError("evaluation case fields do not match the v1 contract")
    case_id = case["case_id"]
    if not isinstance(case_id, str) or not case_id:
        raise ContractError("evaluation case_id must be a non-empty string")
    request = case["request"]
    expected = case["expected"]
    if not isinstance(request, dict):
        raise ContractError(f"evaluation request must be an object: {case_id}")
    if not isinstance(expected, dict) or set(expected) != {
        "disposition",
        "reason_code",
        "citation_count",
    }:
        raise ContractError(f"evaluation expectation is invalid: {case_id}")
    if expected["disposition"] not in {"ADMIT", "ABSTAIN", "REFUSE"}:
        raise ContractError(f"evaluation disposition is invalid: {case_id}")
    if not isinstance(expected["reason_code"], str) or not expected["reason_code"]:
        raise ContractError(f"evaluation reason_code is invalid: {case_id}")
    if (
        not isinstance(expected["citation_count"], int)
        or isinstance(expected["citation_count"], bool)
        or expected["citation_count"] < 0
    ):
        raise ContractError(f"evaluation citation_count is invalid: {case_id}")
    return case_id, request, expected


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
