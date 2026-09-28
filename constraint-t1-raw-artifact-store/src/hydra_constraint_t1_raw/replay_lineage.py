"""Deterministic replay-lineage derivation from a sanitized T1 attestation.

No raw bytes or private paths are required. This module proves only which exact
persisted source versions are eligible at a requested as-of time. It does not
promote strict historical replay, T5/T6 admission, canonical constraints, or
beneficiary qualification.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping, Sequence

from .first_slice_materialization import (
    FirstSliceMaterializationError,
    validate_public_materialization_attestation,
)
from .store import build_release_manifest


REPLAY_LINEAGE_SCHEMA = "hydra-constraint-first-slice-replay-lineage-packet/v1"
HEX64 = __import__("re").compile(r"^[0-9a-f]{64}$")


class ReplayLineageError(FirstSliceMaterializationError):
    pass


def _dt(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ReplayLineageError(f"{label}: timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReplayLineageError(f"{label}: invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReplayLineageError(f"{label}: timezone-aware timestamp required")
    return parsed


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _packet_digest(packet: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in packet.items() if key != "packet_sha256"}
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _registry_ids(registry: Mapping[str, Any]) -> set[str]:
    rows = registry.get("sources")
    if not isinstance(rows, list) or not rows:
        raise ReplayLineageError("registry.sources must be a non-empty list")
    ids: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ReplayLineageError(f"registry.sources[{index}]: object required")
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise ReplayLineageError(f"registry.sources[{index}].source_id required")
        ids.append(source_id)
    if len(ids) != len(set(ids)):
        raise ReplayLineageError("registry source IDs must be unique")
    return set(ids)


def build_replay_lineage_packet(
    *,
    attestation: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a deterministic, sanitized as-of membership packet."""
    validate_public_materialization_attestation(
        attestation=attestation,
        registry=registry,
    )

    registry_ids = _registry_ids(registry)
    members = attestation.get("members")
    if not isinstance(members, list):
        raise ReplayLineageError("attestation members missing")
    if attestation.get("all_registry_sources_materialized") is not True:
        raise ReplayLineageError("all registry sources must be materialized")
    if attestation.get("all_sources_ordinary_t2_eligible") is not True:
        raise ReplayLineageError("all sources must be ordinary-T2 eligible")
    if attestation.get("ordinary_t2_eligible_count") != len(registry_ids):
        raise ReplayLineageError("ordinary-T2 eligible source count incomplete")

    replay_members: list[dict[str, Any]] = []
    for index, member in enumerate(members):
        if not isinstance(member, Mapping):
            raise ReplayLineageError(f"members[{index}]: object required")
        if member.get("ordinary_t2_eligible") is not True:
            raise ReplayLineageError(
                f"members[{index}]: ordinary-T2 eligibility required"
            )
        if member.get("processing_disposition") != "ELIGIBLE":
            raise ReplayLineageError(
                f"members[{index}]: ELIGIBLE disposition required"
            )
        replay_members.append({
            "source_id": member["source_id"],
            "source_version_id": member["source_version_id"],
            "artifact_sha256": member["artifact_sha256"],
            "receipt_sha256": member["receipt_sha256"],
            "acquired_at": member["acquired_at"],
            "available_at": member["available_at"],
        })

    replay_members.sort(
        key=lambda row: (
            _dt(row["available_at"], f"{row['source_id']}.available_at"),
            row["source_id"],
            row["source_version_id"],
        )
    )

    boundaries: list[dict[str, Any]] = []
    eligible_ids: set[str] = set()
    grouped: dict[str, list[str]] = {}
    for row in replay_members:
        grouped.setdefault(row["available_at"], []).append(row["source_id"])
    for available_at in sorted(grouped, key=lambda value: _dt(value, "available_at")):
        eligible_ids.update(grouped[available_at])
        boundaries.append({
            "as_of": available_at,
            "eligible_source_ids": sorted(eligible_ids),
        })

    packet: dict[str, Any] = {
        "schema_version": REPLAY_LINEAGE_SCHEMA,
        "slice_id": attestation.get("slice_id"),
        "release_id": attestation.get("release_id"),
        "release_sha256": attestation.get("release_sha256"),
        "release_created_at": attestation.get("release_created_at"),
        "availability_mode": attestation.get("availability_mode"),
        "source_count": len(replay_members),
        "ordinary_source_version_hash_lineage_complete": True,
        "ordinary_current_source_set_ready": True,
        "strict_historical_replay_ready": False,
        "historical_availability_backdated": False,
        "no_lookahead_rule": "SOURCE_VISIBLE_IFF_AVAILABLE_AT_LTE_AS_OF",
        "historical_replay_blocker": (
            "CONSERVATIVE_FIRST_CAPTURE_DOES_NOT_PROVE_PRE_CAPTURE_AVAILABILITY"
        ),
        "members": replay_members,
        "availability_boundaries": boundaries,
    }
    packet["packet_sha256"] = _packet_digest(packet)
    validate_replay_lineage_packet(packet=packet, registry=registry)
    return packet


def validate_replay_lineage_packet(
    *,
    packet: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> None:
    registry_ids = _registry_ids(registry)
    if packet.get("schema_version") != REPLAY_LINEAGE_SCHEMA:
        raise ReplayLineageError("unsupported replay-lineage schema")
    if packet.get("slice_id") != registry.get("slice_id"):
        raise ReplayLineageError("replay-lineage slice_id mismatch")
    if packet.get("availability_mode") != "ACQUISITION_TIME_CONSERVATIVE":
        raise ReplayLineageError("replay-lineage availability mode invalid")
    if packet.get("ordinary_source_version_hash_lineage_complete") is not True:
        raise ReplayLineageError("ordinary source-version hash lineage incomplete")
    if packet.get("ordinary_current_source_set_ready") is not True:
        raise ReplayLineageError("ordinary current source set not ready")
    if packet.get("strict_historical_replay_ready") is not False:
        raise ReplayLineageError("strict historical replay was improperly promoted")
    if packet.get("historical_availability_backdated") is not False:
        raise ReplayLineageError("historical availability was backdated")
    if packet.get("no_lookahead_rule") != "SOURCE_VISIBLE_IFF_AVAILABLE_AT_LTE_AS_OF":
        raise ReplayLineageError("no-lookahead rule drifted")
    if packet.get("historical_replay_blocker") != (
        "CONSERVATIVE_FIRST_CAPTURE_DOES_NOT_PROVE_PRE_CAPTURE_AVAILABILITY"
    ):
        raise ReplayLineageError("historical replay blocker drifted")
    if packet.get("packet_sha256") != _packet_digest(packet):
        raise ReplayLineageError("replay-lineage packet digest mismatch")

    members = packet.get("members")
    if not isinstance(members, list) or len(members) != len(registry_ids):
        raise ReplayLineageError("replay-lineage member count drifted")
    ids: list[str] = []
    release_members: list[dict[str, str]] = []
    previous_key: tuple[datetime, str, str] | None = None
    for index, row in enumerate(members):
        if not isinstance(row, Mapping):
            raise ReplayLineageError(f"members[{index}]: object required")
        required = {
            "source_id", "source_version_id", "artifact_sha256",
            "receipt_sha256", "acquired_at", "available_at",
        }
        if set(row) != required:
            raise ReplayLineageError(f"members[{index}]: field set invalid")
        source_id = row["source_id"]
        source_version_id = row["source_version_id"]
        if not isinstance(source_id, str) or source_id not in registry_ids:
            raise ReplayLineageError(f"members[{index}]: source identity invalid")
        if not isinstance(source_version_id, str) or not source_version_id:
            raise ReplayLineageError(f"members[{index}]: source-version identity invalid")
        for field in ("artifact_sha256", "receipt_sha256"):
            value = row[field]
            if not isinstance(value, str) or HEX64.fullmatch(value) is None:
                raise ReplayLineageError(f"members[{index}].{field} invalid")
        acquired = _dt(row["acquired_at"], f"members[{index}].acquired_at")
        available = _dt(row["available_at"], f"members[{index}].available_at")
        if row["available_at"] != row["acquired_at"]:
            raise ReplayLineageError(
                f"members[{index}]: conservative AVAILABLE_AT must equal ACQUIRED_AT"
            )
        key = (available, source_id, source_version_id)
        if previous_key is not None and key < previous_key:
            raise ReplayLineageError("replay-lineage members are not deterministically sorted")
        previous_key = key
        ids.append(source_id)
        release_members.append({
            "source_id": source_id,
            "source_version_id": source_version_id,
            "artifact_sha256": row["artifact_sha256"],
            "receipt_sha256": row["receipt_sha256"],
        })

    if set(ids) != registry_ids or len(ids) != len(set(ids)):
        raise ReplayLineageError("replay-lineage source set differs from registry")
    if packet.get("source_count") != len(members):
        raise ReplayLineageError("replay-lineage source_count drifted")

    release_id = packet.get("release_id")
    release_created_at = packet.get("release_created_at")
    if not isinstance(release_id, str) or not release_id:
        raise ReplayLineageError("release_id required")
    if not isinstance(release_created_at, str):
        raise ReplayLineageError("release_created_at required")
    _dt(release_created_at, "release_created_at")
    expected_release = build_release_manifest(
        release_id=release_id,
        created_at=release_created_at,
        receipts=release_members,
    )
    if packet.get("release_sha256") != expected_release["release_sha256"]:
        raise ReplayLineageError("release SHA does not match replay-lineage members")

    boundaries = packet.get("availability_boundaries")
    if not isinstance(boundaries, list) or not boundaries:
        raise ReplayLineageError("availability boundaries missing")
    cumulative: set[str] = set()
    last_time: datetime | None = None
    for index, boundary in enumerate(boundaries):
        if not isinstance(boundary, Mapping):
            raise ReplayLineageError(f"availability_boundaries[{index}]: object required")
        if set(boundary) != {"as_of", "eligible_source_ids"}:
            raise ReplayLineageError(
                f"availability_boundaries[{index}]: field set invalid"
            )
        instant = _dt(boundary["as_of"], f"availability_boundaries[{index}].as_of")
        if last_time is not None and instant <= last_time:
            raise ReplayLineageError("availability boundaries are not strictly increasing")
        last_time = instant
        cumulative = {
            row["source_id"]
            for row in members
            if _dt(row["available_at"], "member.available_at") <= instant
        }
        if boundary["eligible_source_ids"] != sorted(cumulative):
            raise ReplayLineageError(
                f"availability_boundaries[{index}]: eligible source set drifted"
            )

    if boundaries[-1]["eligible_source_ids"] != sorted(registry_ids):
        raise ReplayLineageError("final availability boundary does not expose full source set")


def select_replay_members(
    *,
    packet: Mapping[str, Any],
    registry: Mapping[str, Any],
    as_of: str,
) -> list[dict[str, Any]]:
    validate_replay_lineage_packet(packet=packet, registry=registry)
    cutoff = _dt(as_of, "as_of")
    return [
        dict(row)
        for row in packet["members"]
        if _dt(row["available_at"], f"{row['source_id']}.available_at") <= cutoff
    ]
