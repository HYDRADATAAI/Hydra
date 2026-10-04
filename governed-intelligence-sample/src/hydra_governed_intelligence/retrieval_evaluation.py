"""Deterministic benchmark receipts for governed lexical retrieval."""

from __future__ import annotations

import json
import re
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

from .context import (
    ContractError,
    Evidence,
    canonical_json_bytes,
    load_json_document_with_bytes,
    sha256_hex,
)
from .retrieval import (
    RetrievalPolicy,
    build_retrieval_decision,
    verify_retrieval_decision,
)


RETRIEVAL_SUITE_SCHEMA = "hydra-governed-retrieval-evaluation-suite/v3"
RETRIEVAL_QRELS_SCHEMA = "hydra-governed-retrieval-qrels/v1"
RETRIEVAL_REPORT_SCHEMA = "hydra-governed-retrieval-evaluation-report/v3"
RETRIEVAL_OUTPUT_MANIFEST_SCHEMA = "hydra-governed-retrieval-output-manifest/v3"
CASE_GROUPS = {"HARD_NEGATIVE", "QUALITY", "SAFETY_CONTROL"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def run_retrieval_evaluation(
    *,
    cases_path: str | Path,
    qrels_path: str | Path,
    evidence: Evidence,
    policy: RetrievalPolicy,
    output_dir: str | Path,
) -> dict[str, Any]:
    suite_path = Path(cases_path)
    qrels_document_path = Path(qrels_path)
    cases, suite_bytes = _load_cases(suite_path)
    qrels, qrels_bytes = _load_qrels(qrels_document_path, evidence=evidence)

    quality_case_ids = {
        case_id for case_id, metric_group, _, _ in cases if metric_group == "QUALITY"
    }
    if set(qrels) != quality_case_ids:
        raise ContractError("qrels case IDs do not match quality cases")

    decisions: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    disposition_counts = {"ABSTAIN": 0, "ADMIT": 0, "REFUSE": 0}
    expectation_matches = 0
    decision_verification_passes = 0
    citation_applicable_cases = 0
    citation_integrity_pass_cases = 0
    verified_citations = 0
    citation_not_applicable_cases = 0
    unauthorized_model_executions = 0
    quarantined_raw_records_exposed = 0
    hard_negative_cases = 0
    hard_negative_false_admits = 0
    relevant_judgments = 0
    retrieved_relevant = 0
    macro_recall_total = Fraction(0, 1)
    reciprocal_rank_total = Fraction(0, 1)

    for case_id, metric_group, request, expected in cases:
        decision = build_retrieval_decision(request, evidence=evidence, policy=policy)
        verify_retrieval_decision(decision, evidence=evidence, policy=policy)
        decision_verification_passes += 1

        citations = decision["citations"]
        actual_record_ids = _ranked_record_ids(decision)
        if decision["disposition"] == "ADMIT":
            citation_applicable_cases += 1
            if not citations or len(citations) != len(actual_record_ids):
                raise ContractError("admitted retrieval citation count is invalid")
            citation_integrity_pass_cases += 1
            verified_citations += len(citations)
        else:
            citation_not_applicable_cases += 1

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

        if metric_group == "QUALITY":
            relevant = qrels[case_id]
            retrieved_for_case = len(set(actual_record_ids).intersection(relevant))
            relevant_judgments += len(relevant)
            retrieved_relevant += retrieved_for_case
            macro_recall_total += Fraction(retrieved_for_case, len(relevant))
            for rank, record_id in enumerate(actual_record_ids, start=1):
                if record_id in relevant:
                    reciprocal_rank_total += Fraction(1, rank)
                    break
        elif metric_group == "HARD_NEGATIVE":
            hard_negative_cases += 1
            if decision["disposition"] == "ADMIT":
                hard_negative_false_admits += 1

        decisions.append(
            {"case_id": case_id, "decision": decision, "metric_group": metric_group}
        )

    quality_case_count = len(quality_case_ids)
    micro_recall_at_k = (
        Fraction(retrieved_relevant, relevant_judgments)
        if relevant_judgments
        else Fraction(0)
    )
    macro_recall_at_k = (
        macro_recall_total / quality_case_count
        if quality_case_count
        else Fraction(0)
    )
    mean_reciprocal_rank = (
        reciprocal_rank_total / quality_case_count
        if quality_case_count
        else Fraction(0)
    )
    formatted_micro_recall = _format_fraction(micro_recall_at_k)
    report = {
        "case_count": len(cases),
        "checks": {
            "citation_applicable_case_count": citation_applicable_cases,
            "citation_integrity_pass_case_count": citation_integrity_pass_cases,
            "citation_not_applicable_case_count": citation_not_applicable_cases,
            "decision_verification_pass_count": decision_verification_passes,
            "expectation_match_count": expectation_matches,
            "hard_negative_case_count": hard_negative_cases,
            "hard_negative_false_admit_count": hard_negative_false_admits,
            "macro_recall_at_k": _format_fraction(macro_recall_at_k),
            "mean_reciprocal_rank": _format_fraction(mean_reciprocal_rank),
            "micro_recall_at_k": formatted_micro_recall,
            "quality_case_count": quality_case_count,
            "quarantined_raw_records_exposed_count": quarantined_raw_records_exposed,
            "recall_at_k": formatted_micro_recall,
            "relevant_judgment_count": relevant_judgments,
            "qrel_case_count": quality_case_count,
            "retrieved_relevant_count": retrieved_relevant,
            "unauthorized_model_execution_count": unauthorized_model_executions,
            "verified_citation_count": verified_citations,
        },
        "disposition_counts": disposition_counts,
        "failures": failures,
        "input_binding": {
            "normalized_events_sha256": evidence.normalized_sha256,
            "pipeline_manifest_sha256": evidence.manifest_sha256,
            "retrieval_policy_sha256": policy.sha256,
            "retrieval_qrels_sha256": sha256_hex(qrels_bytes),
            "retrieval_suite_sha256": sha256_hex(suite_bytes),
        },
        "schema_version": RETRIEVAL_REPORT_SCHEMA,
        "status": "PASS"
        if not failures
        and hard_negative_false_admits == 0
        and unauthorized_model_executions == 0
        and quarantined_raw_records_exposed == 0
        else "FAIL",
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    decisions_path = output_root / "retrieval_decisions.jsonl"
    report_path = output_root / "retrieval_evaluation_report.json"
    manifest_path = output_root / "retrieval_output_manifest.json"
    decisions_bytes = b"".join(canonical_json_bytes(item) + b"\n" for item in decisions)
    report_bytes = _pretty_json_bytes(report)
    decisions_path.write_bytes(decisions_bytes)
    report_path.write_bytes(report_bytes)
    manifest = {
        "input_binding": report["input_binding"],
        "outputs": {
            "retrieval_decisions_jsonl": {
                "file": decisions_path.name,
                "sha256": sha256_hex(decisions_bytes),
            },
            "retrieval_evaluation_report": {
                "file": report_path.name,
                "sha256": sha256_hex(report_bytes),
            },
        },
        "schema_version": RETRIEVAL_OUTPUT_MANIFEST_SCHEMA,
    }
    manifest_path.write_bytes(_pretty_json_bytes(manifest))
    return report


def _load_cases(
    suite_path: Path,
) -> tuple[
    list[tuple[str, str, Mapping[str, Any], Mapping[str, Any]]],
    bytes,
]:
    suite, suite_bytes = load_json_document_with_bytes(suite_path)
    if not isinstance(suite, dict) or set(suite) != {"cases", "schema_version"}:
        raise ContractError("retrieval suite fields do not match the v3 contract")
    if suite["schema_version"] != RETRIEVAL_SUITE_SCHEMA:
        raise ContractError("unsupported retrieval suite schema")
    raw_cases = suite["cases"]
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ContractError("retrieval suite must contain cases")

    cases = []
    seen_case_ids: set[str] = set()
    for case in raw_cases:
        validated = _validate_case(case)
        case_id = validated[0]
        if case_id in seen_case_ids:
            raise ContractError(f"duplicate retrieval case_id: {case_id}")
        seen_case_ids.add(case_id)
        cases.append(validated)
    return cases, suite_bytes


def _load_qrels(
    qrels_path: Path, *, evidence: Evidence
) -> tuple[dict[str, tuple[str, ...]], bytes]:
    document, qrels_bytes = load_json_document_with_bytes(qrels_path)
    if not isinstance(document, dict) or set(document) != {
        "corpus_binding",
        "judgments",
        "schema_version",
    }:
        raise ContractError("retrieval qrels fields do not match the v1 contract")
    if document["schema_version"] != RETRIEVAL_QRELS_SCHEMA:
        raise ContractError("unsupported retrieval qrels schema")

    binding = document["corpus_binding"]
    if not isinstance(binding, dict) or set(binding) != {
        "normalized_events_sha256",
        "pipeline_manifest_sha256",
        "record_ids",
    }:
        raise ContractError("qrels corpus binding fields do not match the v1 contract")
    for field in ("normalized_events_sha256", "pipeline_manifest_sha256"):
        if not isinstance(binding[field], str) or not SHA256_PATTERN.fullmatch(binding[field]):
            raise ContractError(f"qrels {field} is invalid")
    if binding["pipeline_manifest_sha256"] != evidence.manifest_sha256:
        raise ContractError("qrels pipeline manifest digest does not match evidence")
    if binding["normalized_events_sha256"] != evidence.normalized_sha256:
        raise ContractError("qrels normalized artifact digest does not match evidence")

    bound_record_ids = binding["record_ids"]
    if (
        not isinstance(bound_record_ids, list)
        or any(
            not isinstance(record_id, str) or not SHA256_PATTERN.fullmatch(record_id)
            for record_id in bound_record_ids
        )
        or bound_record_ids != sorted(set(bound_record_ids))
    ):
        raise ContractError("qrels corpus record IDs are invalid")
    evidence_record_ids = sorted(event["event_id"] for event in evidence.accepted_events)
    if bound_record_ids != evidence_record_ids:
        raise ContractError("qrels corpus record IDs do not match accepted evidence")

    raw_judgments = document["judgments"]
    if not isinstance(raw_judgments, list) or not raw_judgments:
        raise ContractError("retrieval qrels must contain judgments")
    judgments: dict[str, tuple[str, ...]] = {}
    accepted_ids = set(evidence_record_ids)
    for judgment in raw_judgments:
        if not isinstance(judgment, dict) or set(judgment) != {
            "case_id",
            "relevant_record_ids",
        }:
            raise ContractError("retrieval qrels judgment is invalid")
        case_id = judgment["case_id"]
        if not isinstance(case_id, str) or not case_id:
            raise ContractError("retrieval qrels case_id must be a non-empty string")
        if case_id in judgments:
            raise ContractError(f"duplicate retrieval qrels case_id: {case_id}")
        relevant_record_ids = judgment["relevant_record_ids"]
        if (
            not isinstance(relevant_record_ids, list)
            or not relevant_record_ids
            or any(
                not isinstance(record_id, str) or not SHA256_PATTERN.fullmatch(record_id)
                for record_id in relevant_record_ids
            )
            or relevant_record_ids != sorted(set(relevant_record_ids))
        ):
            raise ContractError(f"relevant record IDs are invalid: {case_id}")
        if not set(relevant_record_ids).issubset(accepted_ids):
            raise ContractError(f"relevant record IDs are outside the bound corpus: {case_id}")
        judgments[case_id] = tuple(relevant_record_ids)
    return judgments, qrels_bytes


def _validate_case(
    case: Any,
) -> tuple[str, str, Mapping[str, Any], Mapping[str, Any]]:
    if not isinstance(case, dict) or set(case) != {
        "case_id",
        "expected",
        "metric_group",
        "request",
    }:
        raise ContractError("retrieval case fields do not match the v3 contract")
    case_id = case["case_id"]
    if not isinstance(case_id, str) or not case_id:
        raise ContractError("retrieval case_id must be a non-empty string")
    metric_group = case["metric_group"]
    if not isinstance(metric_group, str) or metric_group not in CASE_GROUPS:
        raise ContractError(f"retrieval metric_group is invalid: {case_id}")
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
    if not isinstance(expected["disposition"], str) or expected["disposition"] not in {
        "ADMIT",
        "ABSTAIN",
        "REFUSE",
    }:
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
    return case_id, metric_group, request, expected


def _ranked_record_ids(decision: Mapping[str, Any]) -> list[str]:
    context = decision.get("context")
    if not isinstance(context, Mapping):
        return []
    results = context.get("results")
    if not isinstance(results, list):
        return []
    return [result["record"]["event_id"] for result in results]


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
