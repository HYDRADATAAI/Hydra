"""Deterministic lexical retrieval over integrity-checked accepted records."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .context import (
    ContractError,
    Evidence,
    IntegrityError,
    canonical_json_bytes,
    load_json_document,
    sha256_hex,
)


RETRIEVAL_POLICY_SCHEMA = "hydra-governed-retrieval-policy/v1"
RETRIEVAL_DECISION_SCHEMA = "hydra-governed-retrieval-decision/v1"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
POLICY_TERM_PATTERN = re.compile(r"^[a-z0-9]+$")
RETRIEVABLE_FIELDS = {"currency", "source_system", "symbol", "venue"}


@dataclass(frozen=True)
class RetrievalPolicy:
    field_weights: Mapping[str, int]
    max_results: int
    min_score: int
    prohibited_terms: tuple[str, ...]
    sha256: str


def load_retrieval_policy(path: str | Path) -> RetrievalPolicy:
    policy_path = Path(path)
    document = load_json_document(policy_path)
    expected_fields = {
        "field_weights",
        "max_results",
        "min_score",
        "model_execution_enabled",
        "prohibited_terms",
        "schema_version",
    }
    if not isinstance(document, dict) or set(document) != expected_fields:
        raise ContractError("retrieval policy fields do not match the v1 contract")
    if document["schema_version"] != RETRIEVAL_POLICY_SCHEMA:
        raise ContractError("unsupported retrieval policy schema")
    if document["model_execution_enabled"] is not False:
        raise ContractError("retrieval policy cannot enable model execution")

    field_weights = document["field_weights"]
    if not isinstance(field_weights, dict) or set(field_weights) != RETRIEVABLE_FIELDS:
        raise ContractError("retrieval field weights do not match the v1 contract")
    for field, weight in field_weights.items():
        if not isinstance(weight, int) or isinstance(weight, bool) or not 1 <= weight <= 20:
            raise ContractError(f"retrieval weight for {field} must be between 1 and 20")

    max_results = document["max_results"]
    min_score = document["min_score"]
    if not isinstance(max_results, int) or isinstance(max_results, bool):
        raise ContractError("max_results must be an integer")
    if not 1 <= max_results <= 10:
        raise ContractError("max_results must be between 1 and 10")
    if not isinstance(min_score, int) or isinstance(min_score, bool):
        raise ContractError("min_score must be an integer")
    if not 1 <= min_score <= 100:
        raise ContractError("min_score must be between 1 and 100")

    prohibited_terms = document["prohibited_terms"]
    if not isinstance(prohibited_terms, list) or not prohibited_terms:
        raise ContractError("prohibited_terms must be a non-empty list")
    if prohibited_terms != sorted(set(prohibited_terms)):
        raise ContractError("prohibited_terms must be sorted and unique")
    if any(
        not isinstance(term, str) or not POLICY_TERM_PATTERN.fullmatch(term)
        for term in prohibited_terms
    ):
        raise ContractError("prohibited_terms contains an invalid term")

    return RetrievalPolicy(
        field_weights=dict(sorted(field_weights.items())),
        max_results=max_results,
        min_score=min_score,
        prohibited_terms=tuple(prohibited_terms),
        sha256=sha256_hex(policy_path.read_bytes()),
    )


def build_retrieval_decision(
    request: Mapping[str, Any], *, evidence: Evidence, policy: RetrievalPolicy
) -> dict[str, Any]:
    _validate_request(request, policy=policy)
    query_terms = _tokenize(request["query"])
    if set(query_terms).intersection(policy.prohibited_terms):
        return _decision(
            request,
            evidence,
            policy,
            "REFUSE",
            "restricted_corpus_request",
            query_terms=query_terms,
        )

    ranked: list[tuple[int, Mapping[str, Any]]] = []
    for event in evidence.accepted_events:
        score = _score_event(event, query_terms=query_terms, policy=policy)
        if score >= policy.min_score:
            ranked.append((score, event))
    ranked.sort(key=lambda item: (-item[0], item[1]["event_id"]))

    if not ranked:
        return _decision(
            request,
            evidence,
            policy,
            "ABSTAIN",
            "no_governed_lexical_match",
            query_terms=query_terms,
        )

    selected = ranked[: request["top_k"]]
    results = [
        {"rank": rank, "record": dict(event), "score": score}
        for rank, (score, event) in enumerate(selected, start=1)
    ]
    citations = [
        {
            "artifact": "normalized_events.jsonl",
            "artifact_sha256": evidence.normalized_sha256,
            "record_id": event["event_id"],
            "record_sha256": sha256_hex(canonical_json_bytes(event)),
        }
        for _, event in selected
    ]
    context = {
        "accepted_record_count": len(evidence.accepted_events),
        "index_scope": "accepted_records_only",
        "matching_record_count": len(ranked),
        "query": request["query"],
        "query_terms": list(query_terms),
        "results": results,
        "truncated": len(ranked) > len(selected),
    }
    return _decision(
        request,
        evidence,
        policy,
        "ADMIT",
        "governed_lexical_matches",
        query_terms=query_terms,
        context=context,
        citations=citations,
    )


def verify_retrieval_decision(
    decision: Mapping[str, Any], *, evidence: Evidence, policy: RetrievalPolicy
) -> None:
    if not isinstance(decision, Mapping):
        raise IntegrityError("retrieval decision must be an object")
    if decision.get("schema_version") != RETRIEVAL_DECISION_SCHEMA:
        raise IntegrityError("retrieval decision schema is invalid")
    if decision.get("model_execution") != {
        "authorized": False,
        "status": "NOT_EXECUTED",
    }:
        raise IntegrityError("retrieval decision must keep model execution disabled")
    if _contains_exact_key(decision, "raw_record"):
        raise IntegrityError("retrieval decision exposes a quarantined raw record")

    request = {
        "query": decision.get("query"),
        "request_id": decision.get("request_id"),
        "top_k": decision.get("top_k"),
    }
    try:
        expected = build_retrieval_decision(request, evidence=evidence, policy=policy)
    except ContractError as exc:
        raise IntegrityError(f"retrieval decision request binding is invalid: {exc}") from exc
    if canonical_json_bytes(decision) != canonical_json_bytes(expected):
        raise IntegrityError("retrieval decision does not match governed recomputation")


def _decision(
    request: Mapping[str, Any],
    evidence: Evidence,
    policy: RetrievalPolicy,
    disposition: str,
    reason_code: str,
    *,
    query_terms: tuple[str, ...],
    context: Mapping[str, Any] | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "citations": citations or [],
        "context": dict(context) if context is not None else None,
        "disposition": disposition,
        "input_binding": {
            "pipeline_manifest_sha256": evidence.manifest_sha256,
            "pipeline_run_id": evidence.manifest["pipeline_run_id"],
            "retrieval_policy_sha256": policy.sha256,
        },
        "model_execution": {"authorized": False, "status": "NOT_EXECUTED"},
        "query": request["query"],
        "query_terms": list(query_terms),
        "reason_codes": [reason_code],
        "request_id": request["request_id"],
        "schema_version": RETRIEVAL_DECISION_SCHEMA,
        "top_k": request["top_k"],
    }


def _validate_request(
    request: Mapping[str, Any], *, policy: RetrievalPolicy
) -> None:
    if not isinstance(request, Mapping):
        raise ContractError("retrieval request must be an object")
    if set(request) != {"query", "request_id", "top_k"}:
        raise ContractError("retrieval request fields do not match the v1 contract")
    request_id = request["request_id"]
    if not isinstance(request_id, str) or not REQUEST_ID_PATTERN.fullmatch(request_id):
        raise ContractError("retrieval request_id is invalid")
    query = request["query"]
    if not isinstance(query, str) or not query.strip() or len(query) > 256:
        raise ContractError("retrieval query must contain 1 to 256 characters")
    terms = _tokenize(query)
    if not terms or len(terms) > 24:
        raise ContractError("retrieval query must contain 1 to 24 lexical terms")
    top_k = request["top_k"]
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise ContractError("retrieval top_k must be an integer")
    if not 1 <= top_k <= policy.max_results:
        raise ContractError(
            f"retrieval top_k must be between 1 and {policy.max_results}"
        )


def _score_event(
    event: Mapping[str, Any], *, query_terms: tuple[str, ...], policy: RetrievalPolicy
) -> int:
    document_terms: dict[str, int] = {}
    for field, weight in policy.field_weights.items():
        value = event.get(field)
        if not isinstance(value, str):
            raise IntegrityError(f"retrieval field {field} is not a string")
        for term in _tokenize(value):
            document_terms[term] = max(document_terms.get(term, 0), weight)
    return sum(document_terms.get(term, 0) for term in query_terms)


def _tokenize(value: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return tuple(sorted(set(TOKEN_PATTERN.findall(normalized))))


def _contains_exact_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_exact_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_exact_key(item, key) for item in value)
    return False
