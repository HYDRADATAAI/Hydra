"""Bind reviewed evidence records to exact ordinary-T2 source versions.

The binding is metadata-only. It connects existing reviewed evidence identities
to declared ordinary-T2 source-version lineage. Neither matching hashes nor
conservative timestamp arithmetic authenticates the input times.

This module does not inspect raw source bodies, re-interpret claim content,
promote evidence to canonical status, backdate availability, or authorize
strict historical replay.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from .ordinary_t2_lineage import (
    HISTORICAL_BLOCKER,
    OrdinaryT2LineageError,
    validate_ordinary_t2_lineage,
)

EVIDENCE_LINEAGE_SCHEMA = "hydra-constraint-ordinary-t2-evidence-lineage-binding/v1"
NO_LOOKAHEAD_RULE = "EVIDENCE_VISIBLE_IFF_ORDINARY_T2_AVAILABLE_AT_LTE_AS_OF"
EXCLUDED_SOURCE_REASON = "SOURCE_NOT_IN_ACTIVE_RELEASE"
EVIDENCE_RECORD_FIELDS = frozenset({
    "evidence_id", "source_id", "origin_artifact", "available_at",
    "evidence_role", "proposition", "scope", "semantic_limit",
})


class OrdinaryT2EvidenceLineageError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise OrdinaryT2EvidenceLineageError(message)


def _validate_input_fields(raw: Any, label: str) -> None:
    """Reject unsupported claims and malformed required metadata at every entry."""
    _require(isinstance(raw, Mapping), f"{label}: object required")
    _require(set(raw) <= EVIDENCE_RECORD_FIELDS, f"{label}: unsupported input fields")
    for field in ("evidence_id", "source_id", "origin_artifact"):
        value = raw.get(field)
        _require(
            isinstance(value, str) and value.strip(),
            f"{label}.{field}: nonblank string required",
        )


def _dt(value: Any, label: str) -> datetime:
    _require(isinstance(value, str), f"{label}: timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OrdinaryT2EvidenceLineageError(f"{label}: invalid timestamp") from exc
    _require(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        f"{label}: timezone-aware timestamp required",
    )
    return parsed


def _max_time(left: str | None, right: str) -> tuple[str, str, bool]:
    """Return conservative evidence availability and its provenance label."""
    right_dt = _dt(right, "source_version_available_at")
    if left is None:
        return right, "SOURCE_VERSION_AVAILABLE_AT_ONLY", True
    left_dt = _dt(left, "reviewed_evidence_available_at")
    if left_dt < right_dt:
        return right, "MAX_REVIEWED_EVIDENCE_AND_SOURCE_VERSION_AVAILABLE_AT", True
    return left, "MAX_REVIEWED_EVIDENCE_AND_SOURCE_VERSION_AVAILABLE_AT", False


def build_ordinary_t2_evidence_lineage(
    *,
    lineage_packet: Mapping[str, Any],
    source_records: Sequence[Mapping[str, Any]],
    evidence_records: Sequence[Mapping[str, Any]],
    expected_slice_id: str,
) -> dict[str, Any]:
    """Bind evidence IDs to exact eligible source versions and hashes."""
    _require(
        isinstance(expected_slice_id, str) and expected_slice_id.strip(),
        "expected_slice_id must be a nonblank string",
    )
    try:
        validate_ordinary_t2_lineage(
            packet=lineage_packet,
            source_records=source_records,
            expected_slice_id=expected_slice_id,
        )
    except OrdinaryT2LineageError as exc:
        raise OrdinaryT2EvidenceLineageError(str(exc)) from exc

    members = {
        row["source_id"]: row
        for row in lineage_packet["members"]
    }
    _require(members, "ordinary-T2 source-version lineage is empty")
    _require(
        isinstance(evidence_records, Sequence) and len(evidence_records) > 0,
        "evidence records required",
    )

    bindings: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen_evidence: set[str] = set()

    for index, raw in enumerate(evidence_records):
        _validate_input_fields(raw, f"evidence_records[{index}]")
        evidence_id = raw.get("evidence_id")
        source_id = raw.get("source_id")
        _require(
            isinstance(evidence_id, str) and evidence_id.strip(),
            f"evidence_records[{index}].evidence_id required",
        )
        _require(evidence_id not in seen_evidence, f"duplicate evidence_id: {evidence_id}")
        seen_evidence.add(evidence_id)
        origin_artifact = raw.get("origin_artifact")

        if source_id not in members:
            excluded.append({
                "evidence_id": evidence_id,
                "source_id": source_id,
                "origin_artifact": origin_artifact,
                "exclusion_reason": EXCLUDED_SOURCE_REASON,
            })
            continue

        member = members[source_id]
        reviewed_available = raw.get("available_at")
        if reviewed_available is not None:
            _require(
                isinstance(reviewed_available, str),
                f"{evidence_id}: reviewed available_at must be string or null",
            )
        ordinary_available, basis, adjusted = _max_time(
            reviewed_available,
            member["available_at"],
        )
        bindings.append({
            "evidence_id": evidence_id,
            "source_id": source_id,
            "source_version_id": member["source_version_id"],
            "artifact_sha256": member["artifact_sha256"],
            "receipt_sha256": member["receipt_sha256"],
            "source_locator": member["source_locator"],
            "origin_artifact": origin_artifact,
            "reviewed_evidence_available_at": reviewed_available,
            "source_version_available_at": member["available_at"],
            "ordinary_t2_available_at": ordinary_available,
            "availability_basis": basis,
            "availability_adjusted_to_source_version": adjusted,
            "ordinary_t2_source_version_eligible": True,
            "canonical_evidence_admitted": False,
        })

    bindings.sort(key=lambda row: (row["evidence_id"], row["source_id"]))
    excluded.sort(key=lambda row: (row["evidence_id"], row["source_id"]))

    bound_sources = {row["source_id"] for row in bindings}
    # Equivalent timestamp spellings share one logical boundary; preserve the
    # original literals in each binding and choose a stable existing boundary.
    boundary_times: dict[datetime, str] = {}
    for row in bindings:
        value = row["ordinary_t2_available_at"]
        instant = _dt(value, "ordinary_t2_available_at")
        boundary_times[instant] = min(value, boundary_times.get(instant, value))
    boundaries: list[dict[str, Any]] = []
    for cutoff, value in sorted(boundary_times.items()):
        visible = sorted(
            row["evidence_id"]
            for row in bindings
            if _dt(row["ordinary_t2_available_at"], f"{row['evidence_id']}.ordinary_t2_available_at")
            <= cutoff
        )
        boundaries.append({
            "as_of": value,
            "eligible_evidence_ids": visible,
        })

    packet: dict[str, Any] = {
        "schema_version": EVIDENCE_LINEAGE_SCHEMA,
        "slice_id": expected_slice_id,
        "source_lineage_release_id": lineage_packet["release_id"],
        "source_lineage_release_sha256": lineage_packet["release_sha256"],
        "input_evidence_record_count": len(evidence_records),
        "bound_evidence_count": len(bindings),
        "excluded_evidence_count": len(excluded),
        "active_source_count": len(members),
        "active_source_count_with_bound_evidence": len(bound_sources),
        "all_active_sources_have_bound_evidence": bound_sources == set(members),
        "ordinary_t2_evidence_lineage_complete_for_active_reviewed_evidence": True,
        "strict_historical_replay_ready": False,
        "historical_availability_backdated": False,
        "canonical_evidence_admission_promoted": False,
        "canonical_t5_t6_admission_promoted": False,
        "no_lookahead_rule": NO_LOOKAHEAD_RULE,
        "historical_replay_blocker": HISTORICAL_BLOCKER,
        "bindings": bindings,
        "excluded_evidence": excluded,
        "availability_boundaries": boundaries,
    }
    validate_ordinary_t2_evidence_lineage(
        packet=packet,
        lineage_packet=lineage_packet,
        source_records=source_records,
        evidence_records=evidence_records,
        expected_slice_id=expected_slice_id,
    )
    return packet


def validate_ordinary_t2_evidence_lineage(
    *,
    packet: Mapping[str, Any],
    lineage_packet: Mapping[str, Any],
    source_records: Sequence[Mapping[str, Any]],
    evidence_records: Sequence[Mapping[str, Any]],
    expected_slice_id: str,
) -> None:
    """Validate exact evidence-to-source-version lineage and fail-closed authority."""
    _require(isinstance(packet, Mapping), "evidence-lineage packet must be an object")
    _require(
        isinstance(expected_slice_id, str) and expected_slice_id.strip(),
        "expected_slice_id must be a nonblank string",
    )
    declared_slice_id = packet.get("slice_id")
    _require(
        isinstance(declared_slice_id, str) and declared_slice_id.strip(),
        "evidence-lineage slice_id must be a nonblank string",
    )
    _require(
        isinstance(evidence_records, Sequence)
        and not isinstance(evidence_records, (str, bytes, bytearray))
        and len(evidence_records) > 0,
        "evidence records required",
    )
    try:
        validate_ordinary_t2_lineage(
            packet=lineage_packet,
            source_records=source_records,
            expected_slice_id=expected_slice_id,
        )
    except OrdinaryT2LineageError as exc:
        raise OrdinaryT2EvidenceLineageError(str(exc)) from exc

    allowed = {
        "schema_version", "slice_id", "source_lineage_release_id",
        "source_lineage_release_sha256", "input_evidence_record_count",
        "bound_evidence_count", "excluded_evidence_count", "active_source_count",
        "active_source_count_with_bound_evidence",
        "all_active_sources_have_bound_evidence",
        "ordinary_t2_evidence_lineage_complete_for_active_reviewed_evidence",
        "strict_historical_replay_ready", "historical_availability_backdated",
        "canonical_evidence_admission_promoted", "canonical_t5_t6_admission_promoted",
        "no_lookahead_rule", "historical_replay_blocker", "bindings",
        "excluded_evidence", "availability_boundaries",
    }
    _require(set(packet) == allowed, "evidence-lineage field set invalid")
    _require(packet.get("schema_version") == EVIDENCE_LINEAGE_SCHEMA, "evidence-lineage schema invalid")
    _require(packet.get("slice_id") == expected_slice_id, "evidence-lineage slice mismatch")
    _require(packet.get("source_lineage_release_id") == lineage_packet["release_id"], "source-lineage release id drift")
    _require(packet.get("source_lineage_release_sha256") == lineage_packet["release_sha256"], "source-lineage release sha drift")
    input_count = packet.get("input_evidence_record_count")
    _require(
        type(input_count) is int and input_count == len(evidence_records),
        "input evidence count must be an integer matching evidence records",
    )
    active_source_count = packet.get("active_source_count")
    _require(
        type(active_source_count) is int
        and active_source_count == lineage_packet["source_count"],
        "active source count must be an integer matching source lineage",
    )
    _require(packet.get("ordinary_t2_evidence_lineage_complete_for_active_reviewed_evidence") is True, "active evidence lineage incomplete")
    _require(packet.get("strict_historical_replay_ready") is False, "strict historical replay promoted")
    _require(packet.get("historical_availability_backdated") is False, "historical availability backdated")
    _require(packet.get("canonical_evidence_admission_promoted") is False, "canonical evidence admission promoted")
    _require(packet.get("canonical_t5_t6_admission_promoted") is False, "canonical T5/T6 admission promoted")
    _require(packet.get("no_lookahead_rule") == NO_LOOKAHEAD_RULE, "evidence no-lookahead rule drift")
    _require(packet.get("historical_replay_blocker") == HISTORICAL_BLOCKER, "historical replay blocker drift")

    members = {row["source_id"]: row for row in lineage_packet["members"]}
    bindings = packet.get("bindings")
    excluded = packet.get("excluded_evidence")
    _require(isinstance(bindings, list), "bindings list required")
    _require(isinstance(excluded, list), "excluded evidence list required")
    bound_count = packet.get("bound_evidence_count")
    _require(
        type(bound_count) is int and bound_count == len(bindings),
        "bound evidence count must be an integer matching bindings",
    )
    excluded_count = packet.get("excluded_evidence_count")
    _require(
        type(excluded_count) is int and excluded_count == len(excluded),
        "excluded evidence count must be an integer matching exclusions",
    )
    _require(len(bindings) + len(excluded) == len(evidence_records), "evidence disposition count mismatch")

    input_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(evidence_records):
        _validate_input_fields(raw, f"evidence_records[{index}]")
        evidence_id = raw.get("evidence_id")
        _require(
            isinstance(evidence_id, str) and evidence_id.strip(),
            "input evidence_id invalid",
        )
        _require(evidence_id not in input_by_id, f"duplicate evidence_id: {evidence_id}")
        input_by_id[evidence_id] = raw

    seen: set[str] = set()
    bound_sources: set[str] = set()
    required_binding_fields = {
        "evidence_id", "source_id", "source_version_id", "artifact_sha256",
        "receipt_sha256", "source_locator", "origin_artifact",
        "reviewed_evidence_available_at", "source_version_available_at",
        "ordinary_t2_available_at", "availability_basis",
        "availability_adjusted_to_source_version",
        "ordinary_t2_source_version_eligible", "canonical_evidence_admitted",
    }
    for row in bindings:
        _require(isinstance(row, Mapping) and set(row) == required_binding_fields, "binding field set invalid")
        evidence_id = row["evidence_id"]
        _require(evidence_id in input_by_id and evidence_id not in seen, f"binding evidence identity drift: {evidence_id}")
        seen.add(evidence_id)
        raw = input_by_id[evidence_id]
        source_id = row["source_id"]
        _require(source_id == raw.get("source_id") and source_id in members, f"{evidence_id}: active source binding drift")
        member = members[source_id]
        for field in ("source_version_id", "artifact_sha256", "receipt_sha256", "source_locator"):
            _require(row[field] == member[field], f"{evidence_id}: {field} drift")
        _require(row["origin_artifact"] == raw.get("origin_artifact"), f"{evidence_id}: origin artifact drift")
        reviewed = raw.get("available_at")
        _require(row["reviewed_evidence_available_at"] == reviewed, f"{evidence_id}: reviewed availability drift")
        expected_available, expected_basis, expected_adjusted = _max_time(reviewed, member["available_at"])
        _require(row["source_version_available_at"] == member["available_at"], f"{evidence_id}: source availability drift")
        _require(row["ordinary_t2_available_at"] == expected_available, f"{evidence_id}: ordinary T2 availability drift")
        _require(row["availability_basis"] == expected_basis, f"{evidence_id}: availability basis drift")
        _require(row["availability_adjusted_to_source_version"] is expected_adjusted, f"{evidence_id}: availability-adjustment flag drift")
        _require(row["ordinary_t2_source_version_eligible"] is True, f"{evidence_id}: T2 source eligibility drift")
        _require(row["canonical_evidence_admitted"] is False, f"{evidence_id}: canonical evidence admitted")
        bound_sources.add(source_id)

    required_excluded_fields = {"evidence_id", "source_id", "origin_artifact", "exclusion_reason"}
    for row in excluded:
        _require(isinstance(row, Mapping) and set(row) == required_excluded_fields, "excluded evidence field set invalid")
        evidence_id = row["evidence_id"]
        _require(evidence_id in input_by_id and evidence_id not in seen, f"excluded evidence identity drift: {evidence_id}")
        seen.add(evidence_id)
        raw = input_by_id[evidence_id]
        _require(row["source_id"] == raw.get("source_id"), f"{evidence_id}: excluded source drift")
        _require(row["source_id"] not in members, f"{evidence_id}: active source incorrectly excluded")
        _require(row["origin_artifact"] == raw.get("origin_artifact"), f"{evidence_id}: excluded origin drift")
        _require(row["exclusion_reason"] == EXCLUDED_SOURCE_REASON, f"{evidence_id}: exclusion reason drift")
    _require(seen == set(input_by_id), "not all input evidence was dispositioned")
    bound_source_count = packet.get("active_source_count_with_bound_evidence")
    _require(
        type(bound_source_count) is int and bound_source_count == len(bound_sources),
        "bound active-source count must be an integer matching bound sources",
    )
    _require(packet.get("all_active_sources_have_bound_evidence") is (bound_sources == set(members)), "active-source coverage flag drift")

    boundaries = packet.get("availability_boundaries")
    _require(isinstance(boundaries, list) and boundaries, "evidence availability boundaries missing")
    previous: datetime | None = None
    boundary_instants: list[datetime] = []
    for index, boundary in enumerate(boundaries):
        _require(
            isinstance(boundary, Mapping)
            and set(boundary) == {"as_of", "eligible_evidence_ids"},
            f"availability_boundaries[{index}]: field set invalid",
        )
        instant = _dt(boundary["as_of"], f"availability_boundaries[{index}].as_of")
        _require(previous is None or instant > previous, "evidence boundaries must be strictly increasing")
        previous = instant
        boundary_instants.append(instant)
        expected_ids = sorted(
            row["evidence_id"]
            for row in bindings
            if _dt(row["ordinary_t2_available_at"], "ordinary_t2_available_at") <= instant
        )
        _require(boundary["eligible_evidence_ids"] == expected_ids, f"availability_boundaries[{index}]: visible evidence drift")
    _require(
        boundary_instants == sorted({
            _dt(row["ordinary_t2_available_at"], "ordinary_t2_available_at") for row in bindings
        }),
        "evidence availability boundary instants incomplete or unexpected",
    )
    _require(
        boundaries[-1]["eligible_evidence_ids"] == sorted(row["evidence_id"] for row in bindings),
        "final evidence boundary incomplete",
    )


def select_ordinary_t2_evidence(
    *,
    packet: Mapping[str, Any],
    lineage_packet: Mapping[str, Any],
    source_records: Sequence[Mapping[str, Any]],
    evidence_records: Sequence[Mapping[str, Any]],
    expected_slice_id: str,
    as_of: str,
) -> list[dict[str, Any]]:
    """Return bound evidence visible at a conservative ordinary-T2 cutoff."""
    validate_ordinary_t2_evidence_lineage(
        packet=packet,
        lineage_packet=lineage_packet,
        source_records=source_records,
        evidence_records=evidence_records,
        expected_slice_id=expected_slice_id,
    )
    cutoff = _dt(as_of, "as_of")
    return [
        dict(row)
        for row in packet["bindings"]
        if _dt(row["ordinary_t2_available_at"], f"{row['evidence_id']}.ordinary_t2_available_at")
        <= cutoff
    ]

