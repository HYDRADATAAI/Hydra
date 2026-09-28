"""Ordinary-T2 evidence lineage binding.

This module binds already-reviewed evidence identities to exact ordinary-T2
source versions. It does not parse raw bodies, rewrite propositions, substitute
sources, infer historical availability, or promote canonical evidence/T5/T6.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

SCHEMA = "hydra-constraint-ordinary-t2-evidence-lineage-binding/v1"
NO_LOOKAHEAD_RULE = "EVIDENCE_VISIBLE_IFF_BOUND_SOURCE_AVAILABLE_AT_LTE_AS_OF"
UNBOUND_POLICY = "PRESERVE_UNBOUND_NO_IMPLICIT_SOURCE_SUBSTITUTION"


class EvidenceLineageBindingError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceLineageBindingError(message)


def _dt(value: Any, label: str) -> datetime:
    _require(isinstance(value, str), f"{label}: timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceLineageBindingError(f"{label}: invalid timestamp") from exc
    _require(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        f"{label}: timezone-aware timestamp required",
    )
    return parsed


def _source_members(lineage: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    _require(
        lineage.get("ordinary_current_source_set_ready") is True,
        "ordinary current source set must be ready",
    )
    _require(
        lineage.get("strict_historical_replay_ready") is False,
        "strict historical replay may not be promoted",
    )
    _require(
        lineage.get("historical_availability_backdated") is False,
        "historical availability may not be backdated",
    )
    _require(
        lineage.get("canonical_evidence_admission_promoted") is False,
        "canonical evidence may not already be promoted",
    )
    _require(
        lineage.get("canonical_t5_t6_admission_promoted") is False,
        "canonical T5/T6 may not already be promoted",
    )
    members = lineage.get("members")
    _require(isinstance(members, list) and members, "source lineage members required")
    out: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(members):
        _require(isinstance(row, Mapping), f"members[{index}]: object required")
        source_id = row.get("source_id")
        _require(
            isinstance(source_id, str) and source_id and source_id not in out,
            f"members[{index}]: unique source_id required",
        )
        _require(row.get("ordinary_t2_eligible") is True, f"{source_id}: ordinary T2 required")
        _require(row.get("processing_disposition") == "ELIGIBLE", f"{source_id}: ELIGIBLE required")
        _require(row.get("available_at") == row.get("acquired_at"), f"{source_id}: conservative availability drift")
        _dt(row.get("available_at"), f"{source_id}.available_at")
        for field in ("source_version_id", "artifact_sha256", "receipt_sha256"):
            value = row.get(field)
            _require(isinstance(value, str) and value, f"{source_id}: {field} required")
        out[source_id] = dict(row)
    _require(lineage.get("source_count") == len(out), "source lineage count drift")
    return out


def _reviewed_evidence(
    evidence_documents: Sequence[Mapping[str, Any]],
    *,
    expected_slice_id: str,
) -> list[tuple[str, Mapping[str, Any]]]:
    _require(
        isinstance(evidence_documents, Sequence) and len(evidence_documents) > 0,
        "evidence documents required",
    )
    rows: list[tuple[str, Mapping[str, Any]]] = []
    seen: set[str] = set()
    for doc_index, document in enumerate(evidence_documents):
        _require(isinstance(document, Mapping), f"evidence_documents[{doc_index}]: object required")
        _require(
            document.get("slice_id") == expected_slice_id,
            f"evidence_documents[{doc_index}]: slice mismatch",
        )
        record_id = document.get("record_id")
        _require(
            isinstance(record_id, str) and record_id,
            f"evidence_documents[{doc_index}]: record_id required",
        )
        evidence = document.get("evidence")
        _require(
            isinstance(evidence, list),
            f"{record_id}: evidence list required",
        )
        for evidence_index, item in enumerate(evidence):
            _require(isinstance(item, Mapping), f"{record_id}.evidence[{evidence_index}]: object required")
            evidence_id = item.get("evidence_id")
            source_id = item.get("source_id")
            _require(
                isinstance(evidence_id, str) and evidence_id,
                f"{record_id}.evidence[{evidence_index}]: evidence_id required",
            )
            _require(evidence_id not in seen, f"duplicate evidence_id: {evidence_id}")
            seen.add(evidence_id)
            _require(
                isinstance(source_id, str) and source_id,
                f"{evidence_id}: source_id required",
            )
            rows.append((record_id, item))
    return rows


def build_evidence_lineage_binding(
    *,
    source_lineage: Mapping[str, Any],
    evidence_documents: Sequence[Mapping[str, Any]],
    expected_slice_id: str,
) -> dict[str, Any]:
    sources = _source_members(source_lineage)
    reviewed = _reviewed_evidence(evidence_documents, expected_slice_id=expected_slice_id)

    bound: list[dict[str, Any]] = []
    unbound: list[dict[str, Any]] = []
    for origin_record_id, item in reviewed:
        evidence_id = str(item["evidence_id"])
        source_id = str(item["source_id"])
        if source_id in sources:
            source = sources[source_id]
            bound.append({
                "evidence_id": evidence_id,
                "evidence_origin_record_id": origin_record_id,
                "source_id": source_id,
                "source_version_id": source["source_version_id"],
                "artifact_sha256": source["artifact_sha256"],
                "receipt_sha256": source["receipt_sha256"],
                "source_available_at": source["available_at"],
                "binding_status": "BOUND_ACTIVE_SOURCE_VERSION",
            })
        else:
            unbound.append({
                "evidence_id": evidence_id,
                "evidence_origin_record_id": origin_record_id,
                "source_id": source_id,
                "binding_status": "UNBOUND_SOURCE_OUTSIDE_ACTIVE_LINEAGE",
            })

    bound.sort(key=lambda row: row["evidence_id"])
    unbound.sort(key=lambda row: row["evidence_id"])
    bound_source_ids = {row["source_id"] for row in bound}

    packet = {
        "schema_version": SCHEMA,
        "slice_id": expected_slice_id,
        "release_id": source_lineage.get("release_id"),
        "release_sha256": source_lineage.get("release_sha256"),
        "source_count": len(sources),
        "reviewed_evidence_record_count": len(reviewed),
        "bound_evidence_count": len(bound),
        "unbound_evidence_count": len(unbound),
        "bound_active_source_count": len(bound_source_ids),
        "active_source_coverage_complete": bound_source_ids == set(sources),
        "ordinary_t2_evidence_lineage_bound": True,
        "strict_historical_replay_ready": False,
        "historical_availability_backdated": False,
        "canonical_evidence_admission_promoted": False,
        "canonical_t5_t6_admission_promoted": False,
        "no_lookahead_rule": NO_LOOKAHEAD_RULE,
        "unbound_evidence_policy": UNBOUND_POLICY,
        "historical_replay_blocker": source_lineage.get("historical_replay_blocker"),
        "bound_evidence": bound,
        "unbound_evidence": unbound,
    }
    validate_evidence_lineage_binding(
        packet=packet,
        source_lineage=source_lineage,
        evidence_documents=evidence_documents,
        expected_slice_id=expected_slice_id,
    )
    return packet


def validate_evidence_lineage_binding(
    *,
    packet: Mapping[str, Any],
    source_lineage: Mapping[str, Any],
    evidence_documents: Sequence[Mapping[str, Any]],
    expected_slice_id: str,
) -> None:
    expected = build_evidence_lineage_binding_unchecked(
        source_lineage=source_lineage,
        evidence_documents=evidence_documents,
        expected_slice_id=expected_slice_id,
    )
    _require(dict(packet) == expected, "evidence lineage differs from deterministic rebuild")


def build_evidence_lineage_binding_unchecked(
    *,
    source_lineage: Mapping[str, Any],
    evidence_documents: Sequence[Mapping[str, Any]],
    expected_slice_id: str,
) -> dict[str, Any]:
    sources = _source_members(source_lineage)
    reviewed = _reviewed_evidence(evidence_documents, expected_slice_id=expected_slice_id)
    bound: list[dict[str, Any]] = []
    unbound: list[dict[str, Any]] = []
    for origin_record_id, item in reviewed:
        evidence_id = str(item["evidence_id"])
        source_id = str(item["source_id"])
        if source_id in sources:
            source = sources[source_id]
            bound.append({
                "evidence_id": evidence_id,
                "evidence_origin_record_id": origin_record_id,
                "source_id": source_id,
                "source_version_id": source["source_version_id"],
                "artifact_sha256": source["artifact_sha256"],
                "receipt_sha256": source["receipt_sha256"],
                "source_available_at": source["available_at"],
                "binding_status": "BOUND_ACTIVE_SOURCE_VERSION",
            })
        else:
            unbound.append({
                "evidence_id": evidence_id,
                "evidence_origin_record_id": origin_record_id,
                "source_id": source_id,
                "binding_status": "UNBOUND_SOURCE_OUTSIDE_ACTIVE_LINEAGE",
            })
    bound.sort(key=lambda row: row["evidence_id"])
    unbound.sort(key=lambda row: row["evidence_id"])
    bound_source_ids = {row["source_id"] for row in bound}
    return {
        "schema_version": SCHEMA,
        "slice_id": expected_slice_id,
        "release_id": source_lineage.get("release_id"),
        "release_sha256": source_lineage.get("release_sha256"),
        "source_count": len(sources),
        "reviewed_evidence_record_count": len(reviewed),
        "bound_evidence_count": len(bound),
        "unbound_evidence_count": len(unbound),
        "bound_active_source_count": len(bound_source_ids),
        "active_source_coverage_complete": bound_source_ids == set(sources),
        "ordinary_t2_evidence_lineage_bound": True,
        "strict_historical_replay_ready": False,
        "historical_availability_backdated": False,
        "canonical_evidence_admission_promoted": False,
        "canonical_t5_t6_admission_promoted": False,
        "no_lookahead_rule": NO_LOOKAHEAD_RULE,
        "unbound_evidence_policy": UNBOUND_POLICY,
        "historical_replay_blocker": source_lineage.get("historical_replay_blocker"),
        "bound_evidence": bound,
        "unbound_evidence": unbound,
    }


def select_bound_evidence(
    *,
    packet: Mapping[str, Any],
    source_lineage: Mapping[str, Any],
    evidence_documents: Sequence[Mapping[str, Any]],
    expected_slice_id: str,
    as_of: str,
) -> list[dict[str, Any]]:
    validate_evidence_lineage_binding(
        packet=packet,
        source_lineage=source_lineage,
        evidence_documents=evidence_documents,
        expected_slice_id=expected_slice_id,
    )
    cutoff = _dt(as_of, "as_of")
    return [
        dict(row)
        for row in packet["bound_evidence"]
        if _dt(row["source_available_at"], f"{row['evidence_id']}.source_available_at") <= cutoff
    ]
