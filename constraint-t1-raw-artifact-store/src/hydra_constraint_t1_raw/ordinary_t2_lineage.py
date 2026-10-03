"""Generic ordinary-T2 source-version lineage normalization.

This module consumes a sanitized public T1 materialization attestation plus the
authoritative source records that define the active release scope. It produces
deterministic source-version lineage metadata only.

It does not read raw source bodies, parse evidence claims, infer historical
availability, authorize replay before AVAILABLE_AT, admit T5/T6 outputs, or
promote canonical constraints/beneficiaries.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Mapping, Sequence

ORDINARY_T2_LINEAGE_SCHEMA = "hydra-constraint-ordinary-t2-source-version-lineage/v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CONSERVATIVE_AVAILABILITY = "ACQUISITION_TIME_CONSERVATIVE"
NO_LOOKAHEAD_RULE = "SOURCE_VISIBLE_IFF_AVAILABLE_AT_LTE_AS_OF"
HISTORICAL_BLOCKER = "PRE_ACQUISITION_HISTORICAL_VERSION_AVAILABILITY_NOT_ESTABLISHED"

# v1 accepts only its existing metadata fields. No timestamp proof extension is
# approved here: rejecting an unsupported claim prevents normalization from
# silently discarding it. These allowlists do not authenticate legacy values.
SOURCE_RECORD_FIELDS = frozenset({
    "source_id", "source_version_id", "source_locator", "processing_disposition",
    "historical_backdating_authorized", "capture_intent_id", "content_type_hint",
    "inbox_filename", "ordinal", "preferred_capture_representation",
    "publication_date", "publisher", "receipt_acquired_at_policy",
    "receipt_available_at_policy", "roles", "source_family", "title",
})
ATTESTATION_FIELDS = frozenset({
    "schema_version", "record_id", "slice_id", "as_of", "release_id",
    "release_sha256", "release_record_file_sha256", "availability_mode",
    "materialized_source_count", "valid_receipt_count", "ordinary_t2_eligible_count",
    "all_sources_ordinary_t2_eligible", "historical_availability_backdated",
    "strict_historical_replay_promoted", "public_raw_content_published",
    "private_paths_published", "members", "next_action",
    "predecessor_private_handback_record_id", "provider_exclusion_policy",
    "queue_record_id", "remaining_replay_boundary",
})
ATTESTATION_MEMBER_FIELDS = frozenset({
    "source_id", "source_version_id", "source_locator", "artifact_sha256",
    "receipt_sha256", "content_type", "byte_length", "acquired_at", "available_at",
    "ordinary_t2_eligible", "processing_disposition",
})


class OrdinaryT2LineageError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise OrdinaryT2LineageError(message)


def _dt(value: Any, label: str) -> datetime:
    _require(isinstance(value, str), f"{label}: timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OrdinaryT2LineageError(f"{label}: invalid timestamp") from exc
    _require(
        parsed.tzinfo is not None and parsed.utcoffset() is not None,
        f"{label}: timezone-aware timestamp required",
    )
    return parsed


def _source_scope(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    _require(isinstance(records, Sequence) and len(records) > 0, "source records required")
    out: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records):
        _require(isinstance(record, Mapping), f"source_records[{index}]: object required")
        _require(set(record) <= SOURCE_RECORD_FIELDS, f"source_records[{index}]: unsupported input fields")
        source_id = record.get("source_id")
        source_version_id = record.get("source_version_id")
        source_locator = record.get("source_locator")
        _require(isinstance(source_id, str) and source_id, f"source_records[{index}].source_id required")
        _require(source_id not in out, f"duplicate source_id: {source_id}")
        _require(
            isinstance(source_version_id, str) and source_version_id,
            f"{source_id}: source_version_id required",
        )
        _require(
            isinstance(source_locator, str) and source_locator.startswith("https://"),
            f"{source_id}: HTTPS source_locator required",
        )
        if "processing_disposition" in record:
            _require(
                record.get("processing_disposition") == "ELIGIBLE",
                f"{source_id}: source record must remain ELIGIBLE",
            )
        if "historical_backdating_authorized" in record:
            _require(
                record.get("historical_backdating_authorized") is False,
                f"{source_id}: historical backdating may not be authorized",
            )
        out[source_id] = {
            "source_id": source_id,
            "source_version_id": source_version_id,
            "source_locator": source_locator,
        }
    versions = [row["source_version_id"] for row in out.values()]
    _require(len(versions) == len(set(versions)), "duplicate source_version_id in source scope")
    return out


def _attestation_members(
    attestation: Mapping[str, Any],
    *,
    source_scope: Mapping[str, Mapping[str, Any]],
    expected_slice_id: str,
) -> list[dict[str, Any]]:
    _require(isinstance(attestation, Mapping), "attestation: object required")
    _require(set(attestation) <= ATTESTATION_FIELDS, "attestation: unsupported input fields")
    _require(attestation.get("slice_id") == expected_slice_id, "attestation slice_id mismatch")
    _require(
        attestation.get("availability_mode") == CONSERVATIVE_AVAILABILITY,
        "attestation availability mode must remain conservative",
    )
    _require(
        attestation.get("historical_availability_backdated") is False,
        "attestation historical availability was backdated",
    )
    _require(
        attestation.get("strict_historical_replay_promoted") is False,
        "attestation improperly promotes strict historical replay",
    )
    _require(
        attestation.get("public_raw_content_published") is False,
        "attestation claims public raw source content",
    )
    if "private_paths_published" in attestation:
        _require(
            attestation.get("private_paths_published") is False,
            "attestation claims private filesystem paths are public",
        )
    _require(
        attestation.get("all_sources_ordinary_t2_eligible") is True,
        "attestation does not establish all sources ordinary-T2 eligible",
    )

    release_id = attestation.get("release_id")
    release_sha256 = attestation.get("release_sha256")
    _require(isinstance(release_id, str) and release_id, "attestation release_id required")
    _require(
        isinstance(release_sha256, str) and HEX64.fullmatch(release_sha256) is not None,
        "attestation release_sha256 invalid",
    )

    members = attestation.get("members")
    _require(isinstance(members, list), "attestation members missing")
    _require(
        attestation.get("ordinary_t2_eligible_count") == len(source_scope),
        "ordinary-T2 eligible count incomplete",
    )
    _require(
        attestation.get("materialized_source_count") == len(source_scope),
        "materialized source count incomplete",
    )
    _require(len(members) == len(source_scope), "attestation member count differs from source scope")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, member in enumerate(members):
        _require(isinstance(member, Mapping), f"members[{index}]: object required")
        _require(set(member) <= ATTESTATION_MEMBER_FIELDS, f"members[{index}]: unsupported input fields")
        if "processing_disposition" in member:
            _require(member["processing_disposition"] == "ELIGIBLE",
                     f"members[{index}]: member must remain ELIGIBLE")
        source_id = member.get("source_id")
        _require(
            isinstance(source_id, str) and source_id in source_scope,
            f"members[{index}]: source identity outside active scope",
        )
        _require(source_id not in seen, f"duplicate attestation source_id: {source_id}")
        seen.add(source_id)
        source = source_scope[source_id]
        _require(
            member.get("source_version_id") == source["source_version_id"],
            f"{source_id}: source_version_id mismatch",
        )
        if "source_locator" in member:
            _require(
                member.get("source_locator") == source["source_locator"],
                f"{source_id}: source_locator mismatch",
            )
        _require(
            member.get("ordinary_t2_eligible") is True,
            f"{source_id}: ordinary-T2 eligibility required",
        )
        artifact_sha = member.get("artifact_sha256")
        receipt_sha = member.get("receipt_sha256")
        _require(
            isinstance(artifact_sha, str) and HEX64.fullmatch(artifact_sha) is not None,
            f"{source_id}: artifact_sha256 invalid",
        )
        _require(
            isinstance(receipt_sha, str) and HEX64.fullmatch(receipt_sha) is not None,
            f"{source_id}: receipt_sha256 invalid",
        )
        acquired_at = member.get("acquired_at")
        available_at = member.get("available_at")
        _dt(acquired_at, f"{source_id}.acquired_at")
        _dt(available_at, f"{source_id}.available_at")
        _require(
            available_at == acquired_at,
            f"{source_id}: conservative AVAILABLE_AT must equal ACQUIRED_AT",
        )
        content_type = member.get("content_type")
        byte_length = member.get("byte_length")
        _require(
            isinstance(content_type, str) and content_type,
            f"{source_id}: content_type required",
        )
        _require(
            isinstance(byte_length, int) and not isinstance(byte_length, bool) and byte_length > 0,
            f"{source_id}: byte_length invalid",
        )
        normalized.append({
            "source_id": source_id,
            "source_version_id": source["source_version_id"],
            "artifact_sha256": artifact_sha,
            "receipt_sha256": receipt_sha,
            "source_locator": source["source_locator"],
            "content_type": content_type,
            "byte_length": byte_length,
            "acquired_at": acquired_at,
            "available_at": available_at,
            "processing_disposition": "ELIGIBLE",
            "ordinary_t2_eligible": True,
        })
    _require(seen == set(source_scope), "attestation source set differs from active source scope")
    return normalized


def build_ordinary_t2_lineage(
    *,
    attestation: Mapping[str, Any],
    source_records: Sequence[Mapping[str, Any]],
    expected_slice_id: str,
) -> dict[str, Any]:
    """Normalize declared custody metadata; this does not verify timestamp authority."""
    scope = _source_scope(source_records)
    members = _attestation_members(
        attestation,
        source_scope=scope,
        expected_slice_id=expected_slice_id,
    )
    members.sort(
        key=lambda row: (
            _dt(row["available_at"], f"{row['source_id']}.available_at"),
            row["source_id"],
            row["source_version_id"],
        )
    )

    boundaries: list[dict[str, Any]] = []
    for available_at in sorted(
        {row["available_at"] for row in members},
        key=lambda value: _dt(value, "available_at"),
    ):
        visible = [
            row["source_id"]
            for row in members
            if _dt(row["available_at"], f"{row['source_id']}.available_at")
            <= _dt(available_at, "boundary.available_at")
        ]
        boundaries.append({
            "as_of": available_at,
            "eligible_source_ids": sorted(visible),
        })

    packet: dict[str, Any] = {
        "schema_version": ORDINARY_T2_LINEAGE_SCHEMA,
        "slice_id": expected_slice_id,
        "release_id": attestation["release_id"],
        "release_sha256": attestation["release_sha256"],
        "availability_mode": CONSERVATIVE_AVAILABILITY,
        "source_count": len(members),
        "normalized_source_version_count": len(members),
        "ordinary_source_version_hash_lineage_complete": True,
        "ordinary_current_source_set_ready": True,
        "strict_historical_replay_ready": False,
        "historical_availability_backdated": False,
        "canonical_evidence_admission_promoted": False,
        "canonical_t5_t6_admission_promoted": False,
        "no_lookahead_rule": NO_LOOKAHEAD_RULE,
        "historical_replay_blocker": HISTORICAL_BLOCKER,
        "members": members,
        "availability_boundaries": boundaries,
    }
    validate_ordinary_t2_lineage(
        packet=packet,
        source_records=source_records,
        expected_slice_id=expected_slice_id,
    )
    return packet


def validate_ordinary_t2_lineage(
    *,
    packet: Mapping[str, Any],
    source_records: Sequence[Mapping[str, Any]],
    expected_slice_id: str,
) -> None:
    """Validate deterministic T2 source-version lineage without authority escalation."""
    allowed = {
        "schema_version", "slice_id", "release_id", "release_sha256",
        "availability_mode", "source_count", "normalized_source_version_count",
        "ordinary_source_version_hash_lineage_complete",
        "ordinary_current_source_set_ready", "strict_historical_replay_ready",
        "historical_availability_backdated", "canonical_evidence_admission_promoted",
        "canonical_t5_t6_admission_promoted", "no_lookahead_rule",
        "historical_replay_blocker", "members", "availability_boundaries",
    }
    _require(set(packet) == allowed, "ordinary-T2 lineage field set invalid")
    scope = _source_scope(source_records)
    _require(packet.get("schema_version") == ORDINARY_T2_LINEAGE_SCHEMA, "ordinary-T2 lineage schema invalid")
    _require(packet.get("slice_id") == expected_slice_id, "ordinary-T2 lineage slice mismatch")
    _require(packet.get("availability_mode") == CONSERVATIVE_AVAILABILITY, "ordinary-T2 availability mode drift")
    _require(packet.get("source_count") == len(scope), "ordinary-T2 source_count drift")
    _require(
        packet.get("normalized_source_version_count") == len(scope),
        "ordinary-T2 normalized source-version count drift",
    )
    _require(packet.get("ordinary_source_version_hash_lineage_complete") is True, "ordinary source-version lineage incomplete")
    _require(packet.get("ordinary_current_source_set_ready") is True, "ordinary current source set not ready")
    _require(packet.get("strict_historical_replay_ready") is False, "strict historical replay promoted")
    _require(packet.get("historical_availability_backdated") is False, "historical availability backdated")
    _require(packet.get("canonical_evidence_admission_promoted") is False, "canonical evidence admission promoted")
    _require(packet.get("canonical_t5_t6_admission_promoted") is False, "canonical T5/T6 admission promoted")
    _require(packet.get("no_lookahead_rule") == NO_LOOKAHEAD_RULE, "no-lookahead rule drift")
    _require(packet.get("historical_replay_blocker") == HISTORICAL_BLOCKER, "historical replay blocker drift")
    _require(
        isinstance(packet.get("release_id"), str) and packet["release_id"],
        "ordinary-T2 release_id required",
    )
    _require(
        isinstance(packet.get("release_sha256"), str)
        and HEX64.fullmatch(packet["release_sha256"]) is not None,
        "ordinary-T2 release_sha256 invalid",
    )

    members = packet.get("members")
    _require(isinstance(members, list) and len(members) == len(scope), "ordinary-T2 member count drift")
    ids: list[str] = []
    previous: tuple[datetime, str, str] | None = None
    required_member_fields = {
        "source_id", "source_version_id", "artifact_sha256", "receipt_sha256",
        "source_locator", "content_type", "byte_length", "acquired_at", "available_at",
        "processing_disposition", "ordinary_t2_eligible",
    }
    for index, row in enumerate(members):
        _require(isinstance(row, Mapping), f"members[{index}]: object required")
        _require(set(row) == required_member_fields, f"members[{index}]: field set invalid")
        source_id = row["source_id"]
        _require(source_id in scope, f"members[{index}]: source outside active scope")
        source = scope[source_id]
        _require(row["source_version_id"] == source["source_version_id"], f"{source_id}: version drift")
        _require(row["source_locator"] == source["source_locator"], f"{source_id}: locator drift")
        _require(row["processing_disposition"] == "ELIGIBLE", f"{source_id}: disposition drift")
        _require(row["ordinary_t2_eligible"] is True, f"{source_id}: T2 eligibility drift")
        _require(row["available_at"] == row["acquired_at"], f"{source_id}: conservative availability drift")
        available = _dt(row["available_at"], f"{source_id}.available_at")
        key = (available, source_id, row["source_version_id"])
        _require(previous is None or previous <= key, "ordinary-T2 members are not deterministically sorted")
        previous = key
        for field in ("artifact_sha256", "receipt_sha256"):
            _require(
                isinstance(row[field], str) and HEX64.fullmatch(row[field]) is not None,
                f"{source_id}: {field} invalid",
            )
        _require(isinstance(row["content_type"], str) and row["content_type"], f"{source_id}: content_type invalid")
        _require(
            isinstance(row["byte_length"], int)
            and not isinstance(row["byte_length"], bool)
            and row["byte_length"] > 0,
            f"{source_id}: byte_length invalid",
        )
        ids.append(source_id)
    _require(len(ids) == len(set(ids)) and set(ids) == set(scope), "ordinary-T2 source set drift")

    boundaries = packet.get("availability_boundaries")
    _require(isinstance(boundaries, list) and boundaries, "availability boundaries missing")
    last: datetime | None = None
    for index, boundary in enumerate(boundaries):
        _require(isinstance(boundary, Mapping), f"availability_boundaries[{index}]: object required")
        _require(set(boundary) == {"as_of", "eligible_source_ids"}, f"availability_boundaries[{index}]: field set invalid")
        instant = _dt(boundary["as_of"], f"availability_boundaries[{index}].as_of")
        _require(last is None or instant > last, "availability boundaries must be strictly increasing")
        last = instant
        visible = sorted(
            row["source_id"]
            for row in members
            if _dt(row["available_at"], "member.available_at") <= instant
        )
        _require(boundary["eligible_source_ids"] == visible, f"availability_boundaries[{index}]: visible set drift")
    _require(boundaries[-1]["eligible_source_ids"] == sorted(scope), "final boundary does not expose full current source set")


def select_ordinary_t2_members(
    *,
    packet: Mapping[str, Any],
    source_records: Sequence[Mapping[str, Any]],
    expected_slice_id: str,
    as_of: str,
) -> list[dict[str, Any]]:
    """Return exact source versions visible at a conservative as-of cutoff."""
    validate_ordinary_t2_lineage(
        packet=packet,
        source_records=source_records,
        expected_slice_id=expected_slice_id,
    )
    cutoff = _dt(as_of, "as_of")
    return [
        dict(row)
        for row in packet["members"]
        if _dt(row["available_at"], f"{row['source_id']}.available_at") <= cutoff
    ]


def canonical_json(value: Any) -> str:
    """Stable JSON helper for deterministic fixture generation."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
