"""Public T5-to-T6 handoff parsing and semantic validation."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator, Mapping
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
FORBIDDEN_FIELDS_BY_COMPACT = {marker.replace("_", ""): marker for marker in FORBIDDEN_FIELDS}
FORBIDDEN_FIELDS_ORDERED = tuple(sorted(FORBIDDEN_FIELDS))
FORBIDDEN_VALUE_MARKERS_ORDERED = tuple(
    sorted(FORBIDDEN_VALUE_MARKERS, key=lambda marker: (-len(marker.replace("_", "")), marker))
)
_CONFUSABLE_TRIGRAM_INDEX: dict[str, list[tuple[str, int]]] = {}
for _marker in sorted(FORBIDDEN_FIELDS | FORBIDDEN_VALUE_MARKERS):
    _compact_marker = _marker.replace("_", "")
    for _offset in range(len(_compact_marker) - 2):
        _CONFUSABLE_TRIGRAM_INDEX.setdefault(_compact_marker[_offset:_offset + 3], []).append((_marker, _offset))
_CONFUSABLE_TRIGRAM_PATTERN = re.compile(
    "(?=(" + "|".join(re.escape(trigram) for trigram in sorted(_CONFUSABLE_TRIGRAM_INDEX)) + "))"
)
_MAX_FORBIDDEN_MARKER_LENGTH = max(
    len(marker.replace("_", "")) for marker in FORBIDDEN_FIELDS | FORBIDDEN_VALUE_MARKERS
)
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
            if "active_context" in record and not isinstance(active, Mapping):
                issues.append(Issue("candidate_evidence_context_invalid", "evidence active_context must be an object", f"{evidence_path}.active_context", candidate_id))
            elif isinstance(active, Mapping) and any(flag in active and not isinstance(active[flag], bool) for flag in INACTIVE_EVIDENCE_FLAGS):
                issues.append(Issue("candidate_evidence_context_invalid", "evidence activity flags must be boolean", f"{evidence_path}.active_context", candidate_id))
            elif isinstance(active, Mapping) and any(active.get(flag) is True for flag in INACTIVE_EVIDENCE_FLAGS):
                issues.append(Issue("candidate_evidence_inactive", "candidate evidence contains an inactive state", f"{evidence_path}.active_context", candidate_id))

    for field in ("provenance", "trust", "uncertainty"):
        if not isinstance(candidate.get(field), Mapping):
            issues.append(Issue("candidate_context_invalid", f"candidate {field} must be an object", f"{path}.{field}", candidate_id))
    trust = candidate.get("trust")
    if isinstance(trust, Mapping):
        conflicts = trust.get("conflicts")
        if "conflicts" in trust and not isinstance(conflicts, list):
            issues.append(Issue("candidate_trust_context_invalid", "trust conflicts must be an array", f"{path}.trust.conflicts", candidate_id))
        elif isinstance(conflicts, list) and conflicts:
            issues.append(Issue("candidate_trust_conflict", "candidate contains unresolved trust conflicts", f"{path}.trust.conflicts", candidate_id))
        contradiction_context = trust.get("contradiction_context")
        if "contradiction_context" in trust and not isinstance(contradiction_context, Mapping):
            issues.append(Issue("candidate_trust_context_invalid", "trust contradiction_context must be an object", f"{path}.trust.contradiction_context", candidate_id))
        elif isinstance(contradiction_context, Mapping):
            unresolved, invalid = _unresolved_state(contradiction_context)
            if invalid:
                issues.append(Issue("candidate_trust_context_invalid", "trust unresolved fields must be arrays", f"{path}.trust.contradiction_context", candidate_id))
            elif unresolved:
                issues.append(Issue("candidate_contradiction_unresolved", "candidate contains unresolved contradictions", f"{path}.trust.contradiction_context", candidate_id))

    issues.extend(_scan_authority_smuggling(candidate, path=path, candidate_id=candidate_id))
    return issues


def _scan_authority_smuggling(value: Any, *, path: str, candidate_id: str) -> list[Issue]:
    issues: list[Issue] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            child_path = f"{path}.{key}"
            if _forbidden_field_marker(str(key)) is not None:
                issues.append(Issue("candidate_authority_smuggling", f"forbidden authority field {key!r}", child_path, candidate_id))
            issues.extend(_scan_authority_smuggling(nested, path=child_path, candidate_id=candidate_id))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            issues.extend(_scan_authority_smuggling(nested, path=f"{path}[{index}]", candidate_id=candidate_id))
    elif isinstance(value, str):
        marker = _forbidden_value_marker(value)
        if marker is not None:
            issues.append(Issue("candidate_authority_smuggling", f"forbidden authority marker {marker!r}", path, candidate_id))
    return issues


def _unresolved_state(value: Any) -> tuple[bool, bool]:
    unresolved = False
    invalid = False
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key == "unresolved":
                if not isinstance(nested, list):
                    invalid = True
                elif nested:
                    unresolved = True
            child_unresolved, child_invalid = _unresolved_state(nested)
            unresolved = unresolved or child_unresolved
            invalid = invalid or child_invalid
    elif isinstance(value, list):
        for item in value:
            child_unresolved, child_invalid = _unresolved_state(item)
            unresolved = unresolved or child_unresolved
            invalid = invalid or child_invalid
    return unresolved, invalid


def _normalize_token(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    compatible = "".join(character for character in decomposed if not unicodedata.combining(character))
    with_acronym_boundaries = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", compatible)
    with_camel_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", with_acronym_boundaries)
    separated = re.sub(r"[^0-9A-Za-z]+", "_", with_camel_boundaries)
    return "_".join(separated.casefold().split("_"))


def _forbidden_field_marker(value: str) -> str | None:
    normalized = _normalize_token(value)
    if normalized in FORBIDDEN_FIELDS:
        return normalized
    marker = FORBIDDEN_FIELDS_BY_COMPACT.get(normalized.replace("_", ""))
    return marker if marker is not None else _confusable_marker(value, FORBIDDEN_FIELDS_ORDERED)


def _forbidden_value_marker(value: str) -> str | None:
    normalized = _normalize_token(value)
    compact = normalized.replace("_", "")
    for marker in FORBIDDEN_VALUE_MARKERS_ORDERED:
        if marker in normalized or marker.replace("_", "") in compact:
            return marker
    return _confusable_marker(value, FORBIDDEN_VALUE_MARKERS_ORDERED)


def _confusable_marker(value: str, markers: tuple[str, ...]) -> str | None:
    skeleton = _identifier_skeleton(value)
    if "?" not in skeleton:
        return None
    allowed_markers = set(markers)
    examined: set[tuple[str, int]] = set()
    for region_start, region_end in _confusable_regions(skeleton):
        region = skeleton[region_start:region_end]
        for match in _CONFUSABLE_TRIGRAM_PATTERN.finditer(region):
            trigram = match.group(1)
            trigram_start = region_start + match.start()
            for marker, offset in _CONFUSABLE_TRIGRAM_INDEX[trigram]:
                if marker not in allowed_markers:
                    continue
                start = trigram_start - offset
                identity = (marker, start)
                if identity in examined:
                    continue
                examined.add(identity)
                compact_marker = marker.replace("_", "")
                if start < 0 or start + len(compact_marker) > len(skeleton):
                    continue
                window = skeleton[start:start + len(compact_marker)]
                unknown_characters = window.count("?")
                if unknown_characters == 0 or unknown_characters * 4 > len(compact_marker):
                    continue
                if all(actual == expected or actual == "?" for actual, expected in zip(window, compact_marker)):
                    return marker
    return None


def _confusable_regions(skeleton: str) -> Iterator[tuple[int, int]]:
    region_start: int | None = None
    region_end = 0
    for match in re.finditer(r"\?+", skeleton):
        start = max(0, match.start() - _MAX_FORBIDDEN_MARKER_LENGTH + 1)
        end = min(len(skeleton), match.end() + _MAX_FORBIDDEN_MARKER_LENGTH - 1)
        if region_start is None:
            region_start, region_end = start, end
        elif start <= region_end:
            region_end = max(region_end, end)
        else:
            yield region_start, region_end
            region_start, region_end = start, end
    if region_start is not None:
        yield region_start, region_end


def _identifier_skeleton(value: str) -> str:
    skeleton: list[str] = []
    for character in unicodedata.normalize("NFKD", value):
        if unicodedata.combining(character):
            continue
        folded = character.casefold()
        if folded and all(item.isascii() and item.isalnum() for item in folded):
            skeleton.extend(folded)
        elif character.isalnum():
            skeleton.append("?")
    return "".join(skeleton)


def _is_zoned_time(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None
