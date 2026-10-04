"""Deterministic native T5-to-T6 handoff bridge for reviewed Constraint candidates.

This module performs no I/O, registration, canonical promotion, ranking, or
external effects. It only maps the governed T5 proposal + temporal overlay
shapes into the existing candidate-only T6 handoff schema.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
from typing import Any

from .handoff import CANDIDATE_SCHEMA, HANDOFF_CONTRACT, HANDOFF_SCHEMA


PROPOSAL_SCHEMA = "hydra-constraint-first-slice-t5-candidate-proposals/v1"
OVERLAY_SCHEMA = "hydra-constraint-lily-owner-seam-reconciliation/v2"
PRODUCER_STAGE = "PIPELINE_T5_CONSTRAINT_FORMATION"
CONSUMER_STAGE = "PIPELINE_T6_CANONICAL_CANDIDATE_GOVERNANCE"

_PROPOSAL_KEYS = {
    "schema_version", "record_id", "as_of", "slice_id", "producer_namespace",
    "formation_mode", "canonicalization_performed", "candidates",
    "explicitly_not_formed_as_constraints",
}
_PROPOSAL_CANDIDATE_KEYS = {
    "constraint_candidate_id", "canonical_constraint_id", "constraint_class",
    "classification_status", "classification_candidates", "constraining_mechanism",
    "constrained_target", "material_scope", "semantic_temporal_state",
    "evidence_roles", "claim_ids", "ordinary_t6_eligible", "ineligibility_reasons",
}
_OVERLAY_CANDIDATE_KEYS = {
    "constraint_candidate_id", "available_at", "effective_from", "effective_to",
    "effective_state", "canonical_constraint_id", "canonical_identity_state",
    "lineage_state", "ordinary_t6_eligible", "source_ineligibility_reasons",
}


class NativeT5T6BridgeError(ValueError):
    """Raised when source records cannot be transported without semantic drift."""


def build_native_t5_t6_handoff(
    proposals: Mapping[str, Any],
    temporal_overlay: Mapping[str, Any],
    *,
    handoff_id: str,
    created_at: str,
) -> dict[str, Any]:
    """Build one deterministic candidate-only handoff from governed T5 records."""
    _require_nonempty(handoff_id, "handoff_id")
    created = _parse_zoned(created_at, "created_at")
    _validate_proposals(proposals)
    overlay_by_id = _validate_overlay(temporal_overlay, proposals)

    output_candidates: list[dict[str, Any]] = []
    for source in sorted(proposals["candidates"], key=lambda item: item["constraint_candidate_id"]):
        candidate_id = source["constraint_candidate_id"]
        overlay = overlay_by_id[candidate_id]
        available = _parse_zoned(overlay["available_at"], f"{candidate_id}.available_at")
        if available > created:
            raise NativeT5T6BridgeError(f"{candidate_id}: available_at cannot be after handoff created_at")
        if bool(source["ordinary_t6_eligible"]) != bool(overlay["ordinary_t6_eligible"]):
            raise NativeT5T6BridgeError(f"{candidate_id}: T5 and temporal overlay eligibility disagree")
        if sorted(source["ineligibility_reasons"]) != sorted(overlay["source_ineligibility_reasons"]):
            raise NativeT5T6BridgeError(f"{candidate_id}: ineligibility reasons drift across owner seam")
        if source["canonical_constraint_id"] is not None or overlay["canonical_constraint_id"] is not None:
            raise NativeT5T6BridgeError(f"{candidate_id}: preexisting canonical identity is outside this bridge")

        evidence: list[dict[str, str]] = []
        for role in sorted(source["evidence_roles"]):
            ids = source["evidence_roles"][role]
            if not isinstance(ids, list) or any(not isinstance(item, str) or not item for item in ids):
                raise NativeT5T6BridgeError(f"{candidate_id}: evidence role {role!r} is invalid")
            for evidence_id in sorted(set(ids)):
                evidence.append({"id": evidence_id, "role": role})
        if not evidence:
            raise NativeT5T6BridgeError(f"{candidate_id}: at least one evidence record is required")

        output_candidates.append(
            {
                "schema": CANDIDATE_SCHEMA,
                "candidate_id": candidate_id,
                "canonicality": "candidate_only",
                "statement": {
                    "mechanism": source["constraining_mechanism"],
                    "constrained_target": source["constrained_target"],
                },
                "evidence": evidence,
                "provenance": {
                    "proposal_record_id": proposals["record_id"],
                    "proposal_as_of": proposals["as_of"],
                    "formation_mode": proposals["formation_mode"],
                    "producer_stage": PRODUCER_STAGE,
                    "temporal_overlay_record_id": temporal_overlay["record_id"],
                },
                "temporal": {
                    "available_at": overlay["available_at"],
                    "effective_from": overlay["effective_from"],
                    "effective_to": overlay["effective_to"],
                    "effective_state": overlay["effective_state"],
                    "semantic_state": source["semantic_temporal_state"],
                },
                "trust": {
                    "classification_status": source["classification_status"],
                    "constraint_class": source["constraint_class"],
                    "conflicts": [],
                },
                "uncertainty": {
                    "classification_candidates": deepcopy(source["classification_candidates"]),
                    "ordinary_t6_eligible": bool(source["ordinary_t6_eligible"]),
                    "ineligibility_reasons": deepcopy(source["ineligibility_reasons"]),
                    "lineage_state": overlay["lineage_state"],
                },
                "relations": {
                    "claim_ids": deepcopy(source["claim_ids"]),
                    "material_scope": deepcopy(source["material_scope"]),
                },
                "beneficiaries": [],
                "forced_expenditures": [],
                "lifecycle_state": "handed_off",
                "lifecycle": [
                    {
                        "state": "handed_off",
                        "at": created_at,
                        "producer_stage": PRODUCER_STAGE,
                        "consumer_stage": CONSUMER_STAGE,
                    }
                ],
            }
        )

    return {
        "schema": HANDOFF_SCHEMA,
        "handoff_id": handoff_id,
        "created_at": created_at,
        "contract": HANDOFF_CONTRACT,
        "candidates": output_candidates,
    }


def _validate_proposals(value: Mapping[str, Any]) -> None:
    if set(value) != _PROPOSAL_KEYS:
        raise NativeT5T6BridgeError("proposal document fields do not match the reviewed T5 contract")
    if value["schema_version"] != PROPOSAL_SCHEMA:
        raise NativeT5T6BridgeError("proposal schema is unsupported")
    if value["producer_namespace"] != PRODUCER_STAGE:
        raise NativeT5T6BridgeError("proposal producer namespace is not the frozen T5 stage")
    if value["canonicalization_performed"] is not False:
        raise NativeT5T6BridgeError("bridge refuses T5 input that claims canonicalization")
    _require_nonempty(value["record_id"], "proposal.record_id")
    _require_nonempty(value["slice_id"], "proposal.slice_id")
    candidates = value["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise NativeT5T6BridgeError("proposal candidates must be a non-empty array")
    ids: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping) or set(candidate) != _PROPOSAL_CANDIDATE_KEYS:
            raise NativeT5T6BridgeError("proposal candidate fields do not match the reviewed T5 contract")
        candidate_id = candidate["constraint_candidate_id"]
        _require_nonempty(candidate_id, "constraint_candidate_id")
        _require_nonempty(candidate["constraining_mechanism"], f"{candidate_id}.constraining_mechanism")
        _require_nonempty(candidate["constrained_target"], f"{candidate_id}.constrained_target")
        ids.append(candidate_id)
        if not isinstance(candidate["classification_candidates"], list):
            raise NativeT5T6BridgeError(f"{candidate_id}: classification_candidates must be an array")
        if not isinstance(candidate["material_scope"], Mapping):
            raise NativeT5T6BridgeError(f"{candidate_id}: material_scope must be an object")
        if not isinstance(candidate["evidence_roles"], Mapping):
            raise NativeT5T6BridgeError(f"{candidate_id}: evidence_roles must be an object")
        if not isinstance(candidate["claim_ids"], list):
            raise NativeT5T6BridgeError(f"{candidate_id}: claim_ids must be an array")
        if not isinstance(candidate["ineligibility_reasons"], list):
            raise NativeT5T6BridgeError(f"{candidate_id}: ineligibility_reasons must be an array")
    if len(ids) != len(set(ids)):
        raise NativeT5T6BridgeError("proposal candidate ids must be unique")


def _validate_overlay(
    overlay: Mapping[str, Any],
    proposals: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    if overlay.get("schema_version") != OVERLAY_SCHEMA:
        raise NativeT5T6BridgeError("temporal overlay schema is unsupported")
    if overlay.get("slice_id") != proposals["slice_id"]:
        raise NativeT5T6BridgeError("temporal overlay slice does not match proposals")
    predecessor = overlay.get("predecessor")
    if not isinstance(predecessor, Mapping) or predecessor.get("record_id") != proposals["record_id"]:
        raise NativeT5T6BridgeError("temporal overlay predecessor does not bind the proposal record")
    bindings = overlay.get("current_authority_bindings")
    if not isinstance(bindings, Mapping):
        raise NativeT5T6BridgeError("temporal overlay authority bindings are missing")
    if bindings.get("t5_owner") != PRODUCER_STAGE or bindings.get("t6_owner") != CONSUMER_STAGE:
        raise NativeT5T6BridgeError("temporal overlay owner seam does not match the frozen stage pair")
    overlay_candidates = overlay.get("candidates")
    if not isinstance(overlay_candidates, list):
        raise NativeT5T6BridgeError("temporal overlay candidates must be an array")
    mapped: dict[str, Mapping[str, Any]] = {}
    for item in overlay_candidates:
        if not isinstance(item, Mapping) or set(item) != _OVERLAY_CANDIDATE_KEYS:
            raise NativeT5T6BridgeError("temporal overlay candidate fields do not match the reviewed contract")
        candidate_id = item["constraint_candidate_id"]
        _require_nonempty(candidate_id, "temporal_overlay.constraint_candidate_id")
        if candidate_id in mapped:
            raise NativeT5T6BridgeError("temporal overlay candidate ids must be unique")
        mapped[candidate_id] = item
    proposal_ids = {item["constraint_candidate_id"] for item in proposals["candidates"]}
    if set(mapped) != proposal_ids:
        raise NativeT5T6BridgeError("temporal overlay candidate set does not exactly match T5 proposals")
    return mapped


def _require_nonempty(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise NativeT5T6BridgeError(f"{label} must be a non-empty string")


def _parse_zoned(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise NativeT5T6BridgeError(f"{label} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NativeT5T6BridgeError(f"{label} is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise NativeT5T6BridgeError(f"{label} must include timezone information")
    return parsed
