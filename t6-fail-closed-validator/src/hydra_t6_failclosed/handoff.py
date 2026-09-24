"""Public T5-to-T6 handoff parsing and semantic validation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .documents import JSONDocument, canonical_json_bytes, parse_json_document, sha256_hex
from .models import Issue, sorted_issues


HANDOFF_SCHEMA = "t6-candidate-handoff.v1"
CANDIDATE_SCHEMA = "constraint-candidate.v2"
HANDOFF_CONTRACT = "T6 receives candidates for downstream adjudication; none are canonical truth."
HANDOFF_KEYS = {"schema", "handoff_id", "created_at", "contract", "candidates"}
CANDIDATE_KEYS = {
    "beneficiaries", "candidate_id", "canonicality", "evidence", "forced_expenditures",
    "lifecycle", "lifecycle_state", "provenance", "relations", "schema", "statement",
    "temporal", "trust", "uncertainty",
}
FORBIDDEN_FIELDS = {
    "accepted_as_truth", "authoritative_beneficiary", "canonical", "canonical_constraint",
    "canonical_store_mutation_authorized", "canonical_truth", "canonical_truth_selected",
    "execution_instruction", "external_actions", "external_effects_authorized", "final_constraint",
    "gamma_unfrozen", "implementation_authorized", "ml_training_authorized",
    "model_training_directive", "planner_action", "production_activation", "promotion_authorized",
    "ranked_candidate_ids", "ranking_authorized", "runtime_binding", "selected_beneficiary",
    "trade_permission", "trading_authorized", "truth_selected", "winner",
}
FORBIDDEN_VALUE_MARKERS = {
    "accepted_as_truth", "authoritative_beneficiary", "canonical_constraint", "canonical_truth",
    "execution_instruction", "external_effects_authorized", "final_constraint", "gamma_unfrozen",
    "model_training_directive", "planner_action", "production_activation", "runtime_binding",
    "selected_beneficiary", "trade_permission", "trading_authorized", "truth_selected", "winner",
}
INACTIVE_EVIDENCE_FLAGS = {"quarantined", "retracted", "stale", "superseded", "withdrawn"}


@dataclass(frozen=True)
class HandoffDocument:
    document: JSONDocument
    binding_sha256: str


def parse_handoff_document(value: bytes | bytearray | str | Mapping[str, Any] | None) -> HandoffDocument:
    document = parse_json_document(value, label="$.handoff")
    if document.value is None:
        return HandoffDocument(document, document.raw_sha256)
    normalized = deepcopy(dict(document.value))
    candidates = normalized.get("candidates")
    if isinstance(candidates, list) and all(isinstance(item, Mapping) for item in candidates):
        normalized["candidates"] = sorted(
            (deepcopy(dict(item)) for item in candidates),
            key=lambda item: str(item.get("candidate_id", "")),
        )
    return HandoffDocument(document, sha256_hex(canonical_json_bytes(normalized)))


def validate_handoff(value: Mapping[str, Any] | None) -> tuple[tuple[str, ...], tuple[Issue, ...]]:
    if value is None:
        return (), (Issue("handoff_invalid", "handoff is not a parsed object", "$.handoff"),)
    issues: list[Issue] = []
    missing = sorted(HANDOFF_KEYS - set(value))
    extra = sorted(set(value) - HANDOFF_KEYS)
    for field in missing:
        issues.append(Issue("handoff_field_missing", f"handoff field {field!r} is required", f"$.handoff.{field}"))
    for field in extra:
        issues.append(Issue("handoff_extra_field", f"handoff field {field!r} is unsupported", f"$.handoff.{field}"))
    if value.get("schema") != HANDOFF_SCHEMA:
        issues.append(Issue("handoff_schema_unsupported", "handoff schema is unsupported", "$.handoff.schema"))
    if not isinstance(value.get("handoff_id"), str) or not value.get("handoff_id"):
        issues.append(Issue("handoff_id_invalid", "handoff_id must be a non-empty string", "$.handoff.handoff_id"))
    if value.get("contract") != HANDOFF_CONTRACT:
        issues.append(Issue("handoff_contract_invalid", "handoff contract does not preserve candidate-only semantics", "$.handoff.contract"))
    if not _is_zoned_time(value.get("created_at")):
        issues.append(Issue("handoff_created_at_invalid", "created_at must be a timezone-aware ISO-8601 timestamp", "$.handoff.created_at"))

    candidates = value.get("candidates")
    if not isinstance(candidates, list):
        issues.append(Issue("handoff_candidates_invalid", "candidates must be an array", "$.handoff.candidates"))
        return (), sorted_issues(issues)
    if not candidates:
        issues.append(Issue("handoff_empty", "handoff must contain at least one candidate", "$.handoff.candidates"))
        return (), sorted_issues(issues)

    ordered_candidates = sorted(
        candidates,
        key=lambda item: (
            str(item.get("candidate_id", "")) if isinstance(item, Mapping) else "",
            canonical_json_bytes(item) if isinstance(item, Mapping) else canonical_json_bytes(str(item)),
        ),
    )
    candidate_ids: list[str] = []
    for index, candidate in enumerate(ordered_candidates):
        path = f"$.handoff.candidates[{index}]"
        if not isinstance(candidate, Mapping):
            issues.append(Issue("candidate_not_object", "candidate must be an object", path))
            continue
        candidate_id = candidate.get("candidate_id") if isinstance(candidate.get("candidate_id"), str) else ""
        if candidate_id:
            candidate_ids.append(candidate_id)
        issues.extend(_validate_candidate(candidate, path=path, candidate_id=candidate_id))
    seen: set[str] = set()
    for candidate_id in candidate_ids:
        if candidate_id in seen:
            issues.append(Issue("candidate_id_duplicate", "candidate_id must be unique within a handoff", "$.handoff.candidates", candidate_id))
        seen.add(candidate_id)
    return tuple(sorted(set(candidate_ids))), sorted_issues(issues)


def _validate_candidate(candidate: Mapping[str, Any], *, path: str, candidate_id: str) -> list[Issue]:
    issues: list[Issue] = []
    missing = sorted(CANDIDATE_KEYS - set(candidate))
    extra = sorted(set(candidate) - CANDIDATE_KEYS)
    for field in missing:
        issues.append(Issue("candidate_field_missing", f"candidate field {field!r} is required", f"{path}.{field}", candidate_id))
    for field in extra:
        issues.append(Issue("candidate_extra_field", f"candidate field {field!r} is unsupported", f"{path}.{field}", candidate_id))
    if not candidate_id:
        issues.append(Issue("candidate_id_invalid", "candidate_id must be a non-empty string", f"{path}.candidate_id"))
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        issues.append(Issue("candidate_schema_unsupported", "candidate schema is unsupported", f"{path}.schema", candidate_id))
    if candidate.get("canonicality") != "candidate_only":
        issues.append(Issue("candidate_canonicality_escalation", "candidate canonicality must be candidate_only", f"{path}.canonicality", candidate_id))
    if candidate.get("lifecycle_state") != "handed_off":
        issues.append(Issue("candidate_lifecycle_invalid", "candidate lifecycle_state must be handed_off", f"{path}.lifecycle_state", candidate_id))

    lifecycle = candidate.get("lifecycle")
    if not isinstance(lifecycle, list) or not lifecycle or not isinstance(lifecycle[-1], Mapping) or lifecycle[-1].get("state") != candidate.get("lifecycle_state"):
        issues.append(Issue("candidate_lifecycle_history_invalid", "final lifecycle event must match lifecycle_state", f"{path}.lifecycle", candidate_id))
    evidence = candidate.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        issues.append(Issue("candidate_evidence_missing", "candidate requires at least one evidence record", f"{path}.evidence", candidate_id))
    else:
        for evidence_index, record in enumerate(evidence):
            evidence_path = f"{path}.evidence[{evidence_index}]"
            if not isinstance(record, Mapping) or not isinstance(record.get("id"), str) or not record.get("id"):
                issues.append(Issue("candidate_evidence_id_invalid", "evidence record requires a non-empty id", evidence_path, candidate_id))
                continue
            active = record.get("active_context")
            if isinstance(active, Mapping) and any(active.get(flag) is True for flag in INACTIVE_EVIDENCE_FLAGS):
                issues.append(Issue("candidate_evidence_inactive", "candidate evidence contains an inactive state", f"{evidence_path}.active_context", candidate_id))

    for field in ("provenance", "trust", "uncertainty"):
        if not isinstance(candidate.get(field), Mapping):
            issues.append(Issue("candidate_context_invalid", f"candidate {field} must be an object", f"{path}.{field}", candidate_id))
    trust = candidate.get("trust")
    if isinstance(trust, Mapping):
        conflicts = trust.get("conflicts")
        if isinstance(conflicts, list) and conflicts:
            issues.append(Issue("candidate_trust_conflict", "candidate contains unresolved trust conflicts", f"{path}.trust.conflicts", candidate_id))
        if _has_nonempty_unresolved(trust.get("contradiction_context")):
            issues.append(Issue("candidate_contradiction_unresolved", "candidate contains unresolved contradictions", f"{path}.trust.contradiction_context", candidate_id))

    issues.extend(_scan_authority_smuggling(candidate, path=path, candidate_id=candidate_id))
    return issues


def _scan_authority_smuggling(value: Any, *, path: str, candidate_id: str) -> list[Issue]:
    issues: list[Issue] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_token(str(key))
            child_path = f"{path}.{key}"
            if normalized_key in FORBIDDEN_FIELDS:
                issues.append(Issue("candidate_authority_smuggling", f"forbidden authority field {key!r}", child_path, candidate_id))
            issues.extend(_scan_authority_smuggling(nested, path=child_path, candidate_id=candidate_id))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            issues.extend(_scan_authority_smuggling(nested, path=f"{path}[{index}]", candidate_id=candidate_id))
    elif isinstance(value, str):
        normalized_value = _normalize_token(value)
        for marker in FORBIDDEN_VALUE_MARKERS:
            if marker in normalized_value:
                issues.append(Issue("candidate_authority_smuggling", f"forbidden authority marker {marker!r}", path, candidate_id))
                break
    return issues


def _has_nonempty_unresolved(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key == "unresolved" and isinstance(nested, list) and nested:
                return True
            if _has_nonempty_unresolved(nested):
                return True
    elif isinstance(value, list):
        return any(_has_nonempty_unresolved(item) for item in value)
    return False


def _normalize_token(value: str) -> str:
    with_camel_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    separated = re.sub(r"[^0-9A-Za-z]+", "_", with_camel_boundaries)
    return "_".join(separated.casefold().split("_"))


def _is_zoned_time(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None
