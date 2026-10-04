"""Deterministic benchmark receipts for governed lexical retrieval."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

from .context import ContractError, Evidence, canonical_json_bytes, load_json_document, sha256_hex
from .retrieval import (
    RetrievalPolicy,
    build_retrieval_decision,
    verify_retrieval_decision,
)


RETRIEVAL_SUITE_SCHEMA = "hydra-governed-retrieval-evaluation-suite/v1"
RETRIEVAL_REPORT_SCHEMA = "hydra-governed-retrieval-evaluation-report/v1"
RETRIEVAL_OUTPUT_MANIFEST_SCHEMA = "hydra-governed-retrieval-output-manifest/v1"


def run_retrieval_evaluation(
    *,
    cases_path: str | Path,
    evidence: Evidence,
    policy: RetrievalPolicy,
    output_dir: str | Path,
) -> dict[str, Any]:
    suite_path = Path(cases_path)
    suite = load_json_document(suite_path)
    if not isinstance(suite, dict) or set(suite) != {"cases", "schema_version"}:
        raise ContractError("retrieval suite fields do not match the v1 contract")
    if suite["schema_version"] != RETRIEVAL_SUITE_SCHEMA:
        raise ContractError("unsupported retrieval suite schema")
    cases = suite["cases"]
    if not isinstance(cases, list) or not cases:
        raise ContractError("retrieval suite must contain cases")

    decisions: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    disposition_counts = {"ABSTAIN": 0, "ADMIT": 0, "REFUSE": 0}
    expectation_matches = 0
    citation_integrity_passes = 0
    unauthorized_model_executions = 0
    quarantined_raw_records_exposed = 0
    expected_relevant = 0
    retrieved_relevant = 0
    reciprocal_rank_total = Fraction(0, 1)
    retrieval_case_count = 0
    seen_case_ids: set[str] = set()

    for case in cases:
        case_id, request, expected = _validate_case(case)
        if case_id in seen_case_ids:
            raise ContractError(f"duplicate retrieval case_id: {case_id}")
        seen_case_ids.add(case_id)

        decision = build_retrieval_decision(request, evidence=evidence, policy=policy)
        verify_retrieval_decision(decision, evidence=evidence, policy=policy)
        citation_integrity_passes += 1
        disposition_counts[decision["disposition"]] += 1
        if decision["model_execution"] != {"authorized": False, "status": "NOT_EXECUTED"}:
            unauthorized_model_executions += 1
        if _contains_exact_key(decision, "raw_record"):
            quarantined_raw_records_exposed += 1

        actual_symbols = _ranked_symbols(decision)
        mismatches = []
        if decision["disposition"] != expected["disposition"]:
            mismatches.append("disposition")
        if expected["reason_code"] not in decision["reason_codes"]:
            mismatches.append("reason_code")
        if actual_symbols != expected["ranked_symbols"]:
            mismatches.append("ranked_symbols")
        if mismatches:
            failures.append({"case_id": case_id, "mismatch": ",".join(mismatches)})
        else:
            expectation_matches += 1

        relevant = expected["ranked_symbols"]
        if relevant:
            retrieval_case_count += 1
            expected_relevant += len(relevant)
            retrieved_relevant += len(set(actual_symbols).intersection(relevant))
            for rank, symbol in enumerate(actual_symbols, start=1):
                if symbol in relevant:
                    reciprocal_rank_total += Fraction(1, rank)
                    break
        decisions.append({"case_id": case_id, "decision": decision})

    recall_at_k = Fraction(retrieved_relevant, expected_relevant) if expected_relevant else Fraction(0)
    mean_reciprocal_rank = (
        reciprocal_rank_total / retrieval_case_count
        if retrieval_case_count
        else Fraction(0)
    )
    report = {
        "case_count": len(cases),
        "checks": {
            "citation_integrity_pass_count": citation_integrity_passes,
            "expectation_match_count": expectation_matches,
            "mean_reciprocal_rank": _format_fraction(mean_reciprocal_rank),
            "quarantined_raw_records_exposed_count": quarantined_raw_records_exposed,
            "recall_at_k": _format_fraction(recall_at_k),
            "retrieval_case_count": retrieval_case_count,
            "unauthorized_model_execution_count": unauthorized_model_executions,
        },
        "disposition_counts": disposition_counts,
        "failures": failures,
        "input_binding": {
            "pipeline_manifest_sha256": evidence.manifest_sha256,
            "retrieval_policy_sha256": policy.sha256,
            "retrieval_suite_sha256": sha256_hex(suite_path.read_bytes()),
        },
        "schema_version": RETRIEVAL_REPORT_SCHEMA,
        "status": "PASS"
        if not failures
        and unauthorized_model_executions == 0
        and quarantined_raw_records_exposed == 0
        else "FAIL",
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    decisions_path = output_root / "retrieval_decisions.jsonl"
    report_path = output_root / "retrieval_evaluation_report.json"
    manifest_path = output_root / "retrieval_output_manifest.json"
    decisions_path.write_bytes(b"".join(canonical_json_bytes(item) + b"\n" for item in decisions))
    report_path.write_bytes(_pretty_json_bytes(report))
    manifest = {
        "input_binding": report["input_binding"],
        "outputs": {
            "retrieval_decisions_jsonl": {
                "file": decisions_path.name,
                "sha256": sha256_hex(decisions_path.read_bytes()),
            },
            "retrieval_evaluation_report": {
                "file": report_path.name,
                "sha256": sha256_hex(report_path.read_bytes()),
            },
        },
        "schema_version": RETRIEVAL_OUTPUT_MANIFEST_SCHEMA,
    }
    manifest_path.write_bytes(_pretty_json_bytes(manifest))
    return report


def _validate_case(
    case: Any,
) -> tuple[str, Mapping[str, Any], Mapping[str, Any]]:
    if not isinstance(case, dict) or set(case) != {"case_id", "expected", "request"}:
        raise ContractError("retrieval case fields do not match the v1 contract")
    case_id = case["case_id"]
    if not isinstance(case_id, str) or not case_id:
        raise ContractError("retrieval case_id must be a non-empty string")
    request = case["request"]
    expected = case["expected"]
    if not isinstance(request, dict):
        raise ContractError(f"retrieval request must be an object: {case_id}")
    if not isinstance(expected, dict) or set(expected) != {
        "disposition",
        "ranked_symbols",
        "reason_code",
    }:
        raise ContractError(f"retrieval expectation is invalid: {case_id}")
    if expected["disposition"] not in {"ADMIT", "ABSTAIN", "REFUSE"}:
        raise ContractError(f"retrieval disposition is invalid: {case_id}")
    if not isinstance(expected["reason_code"], str) or not expected["reason_code"]:
        raise ContractError(f"retrieval reason_code is invalid: {case_id}")
    ranked_symbols = expected["ranked_symbols"]
    if (
        not isinstance(ranked_symbols, list)
        or any(not isinstance(symbol, str) or not symbol for symbol in ranked_symbols)
        or len(ranked_symbols) != len(set(ranked_symbols))
    ):
        raise ContractError(f"retrieval ranked_symbols is invalid: {case_id}")
    return case_id, request, expected


def _ranked_symbols(decision: Mapping[str, Any]) -> list[str]:
    context = decision.get("context")
    if not isinstance(context, Mapping):
        return []
    results = context.get("results")
    if not isinstance(results, list):
        return []
    return [result["record"]["symbol"] for result in results]


def _format_fraction(value: Fraction) -> str:
    return f"{float(value):.6f}"


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
