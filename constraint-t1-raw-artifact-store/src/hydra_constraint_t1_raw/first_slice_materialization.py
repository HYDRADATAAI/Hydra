"""Offline first-slice source-set materialization into the private T1 store.

This module performs no network access. It consumes a reviewed source registry
and a local capture plan whose input files already exist outside the public
repository. Historical availability is never inferred from publication dates:
this first materialization mode conservatively sets AVAILABLE_AT=ACQUIRED_AT.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Mapping

from .store import RawArtifactStore, build_release_manifest, is_ordinary_t2_eligible


CAPTURE_PLAN_SCHEMA = "hydra-constraint-first-slice-local-capture-plan/v1"
ATTESTATION_SCHEMA = "hydra-constraint-first-slice-private-materialization-attestation/v1"
CONSERVATIVE_MODE = "ACQUISITION_TIME_CONSERVATIVE"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_PUBLIC_ATTESTATION_KEYS = {
    "artifact_relpath", "input_file", "input_path", "private_root", "raw_bytes",
}


class FirstSliceMaterializationError(ValueError):
    pass


def _dt(value: str, label: str) -> datetime:
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise FirstSliceMaterializationError(f"{label}: invalid timestamp") from exc
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise FirstSliceMaterializationError(f"{label}: timezone-aware timestamp required")
    return ts


def _load_json(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise FirstSliceMaterializationError(f"unable to load JSON: {path}") from exc
    if not isinstance(value, dict):
        raise FirstSliceMaterializationError(f"top-level JSON object required: {path}")
    return value


def _registry_sources(registry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = registry.get("sources")
    if not isinstance(rows, list) or not rows:
        raise FirstSliceMaterializationError("registry.sources must be a non-empty list")
    out: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise FirstSliceMaterializationError(f"registry.sources[{index}]: object required")
        source_id = row.get("source_id")
        url = row.get("url")
        if not isinstance(source_id, str) or not source_id:
            raise FirstSliceMaterializationError(f"registry.sources[{index}].source_id required")
        if source_id in out:
            raise FirstSliceMaterializationError(f"duplicate registry source_id: {source_id}")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise FirstSliceMaterializationError(f"{source_id}: HTTPS registry URL required")
        out[source_id] = row
    return out


def _capture_rows(
    plan: Mapping[str, Any],
    *,
    registry_sources: Mapping[str, Mapping[str, Any]],
    public_repo_root: Path,
) -> list[dict[str, Any]]:
    if plan.get("schema_version") != CAPTURE_PLAN_SCHEMA:
        raise FirstSliceMaterializationError("unsupported capture-plan schema")
    if plan.get("availability_mode") != CONSERVATIVE_MODE:
        raise FirstSliceMaterializationError(
            "only ACQUISITION_TIME_CONSERVATIVE is allowed in this materializer"
        )

    rows = plan.get("captures")
    if not isinstance(rows, list) or not rows:
        raise FirstSliceMaterializationError("capture plan must contain captures")

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise FirstSliceMaterializationError(f"captures[{index}]: object required")
        source_id = raw.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise FirstSliceMaterializationError(f"captures[{index}].source_id required")
        if source_id in seen:
            raise FirstSliceMaterializationError(f"duplicate capture source_id: {source_id}")
        seen.add(source_id)
        if source_id not in registry_sources:
            raise FirstSliceMaterializationError(f"capture references unregistered source: {source_id}")

        registry_url = registry_sources[source_id]["url"]
        if raw.get("source_locator") != registry_url:
            raise FirstSliceMaterializationError(
                f"{source_id}: source_locator must exactly match registry URL"
            )

        input_file = raw.get("input_file")
        if not isinstance(input_file, str) or not input_file:
            raise FirstSliceMaterializationError(f"{source_id}: input_file required")
        resolved_input = Path(input_file).expanduser().resolve()
        if not resolved_input.is_file():
            raise FirstSliceMaterializationError(f"{source_id}: input_file does not exist")
        if resolved_input == public_repo_root or resolved_input.is_relative_to(public_repo_root):
            raise FirstSliceMaterializationError(
                f"{source_id}: raw input file must not live inside the public repository"
            )

        source_version_id = raw.get("source_version_id")
        content_type = raw.get("content_type")
        acquired_at = raw.get("acquired_at")
        disposition = raw.get("processing_disposition", "ELIGIBLE")
        if not isinstance(source_version_id, str) or not source_version_id:
            raise FirstSliceMaterializationError(f"{source_id}: source_version_id required")
        if not isinstance(content_type, str) or not content_type:
            raise FirstSliceMaterializationError(f"{source_id}: content_type required")
        if not isinstance(acquired_at, str):
            raise FirstSliceMaterializationError(f"{source_id}: acquired_at required")
        _dt(acquired_at, f"{source_id}.acquired_at")
        if "available_at" in raw:
            raise FirstSliceMaterializationError(
                f"{source_id}: available_at must not be supplied in conservative mode"
            )
        normalized.append({
            "source_id": source_id,
            "source_version_id": source_version_id,
            "input_path": resolved_input,
            "content_type": content_type,
            "source_locator": registry_url,
            "acquired_at": acquired_at,
            "available_at": acquired_at,
            "processing_disposition": disposition,
        })

    registry_ids = set(registry_sources)
    if seen != registry_ids:
        missing = sorted(registry_ids - seen)
        extra = sorted(seen - registry_ids)
        raise FirstSliceMaterializationError(
            f"capture source set must exactly match registry; missing={missing} extra={extra}"
        )
    return normalized


def materialize_capture_plan(
    *,
    registry: Mapping[str, Any],
    plan: Mapping[str, Any],
    private_root: str | Path,
    public_repo_root: str | Path,
) -> dict[str, Any]:
    public_repo = Path(public_repo_root).expanduser().resolve()
    registry_sources = _registry_sources(registry)
    rows = _capture_rows(
        plan,
        registry_sources=registry_sources,
        public_repo_root=public_repo,
    )

    release_id = plan.get("release_id")
    release_created_at = plan.get("release_created_at")
    slice_id = plan.get("slice_id")
    if not isinstance(release_id, str) or not release_id:
        raise FirstSliceMaterializationError("release_id required")
    if not isinstance(release_created_at, str):
        raise FirstSliceMaterializationError("release_created_at required")
    release_time = _dt(release_created_at, "release_created_at")
    if not isinstance(slice_id, str) or not slice_id:
        raise FirstSliceMaterializationError("slice_id required")
    registry_slice = registry.get("slice_id")
    if registry_slice != slice_id:
        raise FirstSliceMaterializationError(
            f"slice_id mismatch: plan={slice_id!r} registry={registry_slice!r}"
        )

    acquired_times = [_dt(row["acquired_at"], f"{row['source_id']}.acquired_at") for row in rows]
    if release_time < max(acquired_times):
        raise FirstSliceMaterializationError(
            "release_created_at cannot precede the latest source acquisition"
        )

    store = RawArtifactStore(Path(private_root), public_repo_root=public_repo)
    receipts: list[dict[str, Any]] = []
    for row in rows:
        receipts.append(store.persist(
            raw_bytes=row["input_path"].read_bytes(),
            source_id=row["source_id"],
            source_version_id=row["source_version_id"],
            content_type=row["content_type"],
            acquired_at=row["acquired_at"],
            available_at=row["available_at"],
            source_locator=row["source_locator"],
            processing_disposition=row["processing_disposition"],
        ))

    release = store.write_release_manifest(
        release_id=release_id,
        created_at=release_created_at,
        receipts=receipts,
    )

    members: list[dict[str, Any]] = []
    ordinary_count = 0
    for receipt in receipts:
        eligible = is_ordinary_t2_eligible(
            receipt=receipt,
            release_manifest=release,
            store=store,
        )
        ordinary_count += int(eligible)
        members.append({
            "source_id": receipt["source_id"],
            "source_version_id": receipt["source_version_id"],
            "artifact_sha256": receipt["artifact_sha256"],
            "receipt_sha256": receipt["receipt_sha256"],
            "byte_length": receipt["byte_length"],
            "content_type": receipt["content_type"],
            "acquired_at": receipt["acquired_at"],
            "available_at": receipt["available_at"],
            "processing_disposition": receipt["processing_disposition"],
            "ordinary_t2_eligible": eligible,
        })
    members.sort(key=lambda row: row["source_id"])

    return {
        "schema_version": ATTESTATION_SCHEMA,
        "slice_id": slice_id,
        "capture_mode": "OFFLINE_REVIEWED_LOCAL_BYTES",
        "availability_mode": CONSERVATIVE_MODE,
        "network_acquisition_performed_by_materializer": False,
        "public_raw_content_published": False,
        "release_id": release["release_id"],
        "release_sha256": release["release_sha256"],
        "release_created_at": release["created_at"],
        "registry_source_count": len(registry_sources),
        "materialized_source_count": len(receipts),
        "ordinary_t2_eligible_count": ordinary_count,
        "ordinary_t2_blocked_count": len(receipts) - ordinary_count,
        "all_registry_sources_materialized": len(receipts) == len(registry_sources),
        "all_sources_ordinary_t2_eligible": ordinary_count == len(receipts),
        "strict_historical_replay_promoted": False,
        "historical_availability_backdated": False,
        "members": members,
    }




def _forbidden_keys(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_PUBLIC_ATTESTATION_KEYS:
                found.append(child_path)
            found.extend(_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_keys(child, f"{path}[{index}]"))
    return found


def validate_public_materialization_attestation(
    *,
    attestation: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> None:
    """Validate a sanitized public proof without requiring private raw bytes."""
    registry_sources = _registry_sources(registry)
    if attestation.get("schema_version") != ATTESTATION_SCHEMA:
        raise FirstSliceMaterializationError("unsupported attestation schema")
    if attestation.get("slice_id") != registry.get("slice_id"):
        raise FirstSliceMaterializationError("attestation slice_id mismatch")
    if attestation.get("capture_mode") != "OFFLINE_REVIEWED_LOCAL_BYTES":
        raise FirstSliceMaterializationError("attestation capture mode invalid")
    if attestation.get("availability_mode") != CONSERVATIVE_MODE:
        raise FirstSliceMaterializationError("attestation availability mode invalid")
    if attestation.get("network_acquisition_performed_by_materializer") is not False:
        raise FirstSliceMaterializationError("attestation claims network acquisition authority")
    if attestation.get("public_raw_content_published") is not False:
        raise FirstSliceMaterializationError("attestation claims raw public content")
    if attestation.get("strict_historical_replay_promoted") is not False:
        raise FirstSliceMaterializationError("attestation improperly promotes strict historical replay")
    if attestation.get("historical_availability_backdated") is not False:
        raise FirstSliceMaterializationError("attestation backdates historical availability")

    leaked = _forbidden_keys(dict(attestation))
    if leaked:
        raise FirstSliceMaterializationError(
            "public attestation contains private/raw path fields: " + ",".join(leaked)
        )

    members = attestation.get("members")
    if not isinstance(members, list) or not members:
        raise FirstSliceMaterializationError("attestation members required")
    ids = [row.get("source_id") for row in members if isinstance(row, dict)]
    if len(ids) != len(members) or any(not isinstance(x, str) or not x for x in ids):
        raise FirstSliceMaterializationError("attestation source IDs invalid")
    if len(ids) != len(set(ids)):
        raise FirstSliceMaterializationError("attestation contains duplicate source IDs")
    if set(ids) != set(registry_sources):
        raise FirstSliceMaterializationError("attestation source set differs from registry")

    release_members = []
    ordinary_count = 0
    for index, member in enumerate(members):
        label = f"members[{index}]"
        source_version_id = member.get("source_version_id")
        artifact_sha256 = member.get("artifact_sha256")
        receipt_sha256 = member.get("receipt_sha256")
        acquired_at = member.get("acquired_at")
        available_at = member.get("available_at")
        if not isinstance(source_version_id, str) or not source_version_id:
            raise FirstSliceMaterializationError(f"{label}.source_version_id required")
        for field, value in (
            ("artifact_sha256", artifact_sha256),
            ("receipt_sha256", receipt_sha256),
        ):
            if not isinstance(value, str) or HEX64.fullmatch(value) is None:
                raise FirstSliceMaterializationError(f"{label}.{field} invalid")
        if not isinstance(acquired_at, str) or not isinstance(available_at, str):
            raise FirstSliceMaterializationError(f"{label}: acquisition/availability timestamps required")
        _dt(acquired_at, f"{label}.acquired_at")
        _dt(available_at, f"{label}.available_at")
        if available_at != acquired_at:
            raise FirstSliceMaterializationError(
                f"{label}: conservative attestation requires AVAILABLE_AT=ACQUIRED_AT"
            )
        if member.get("ordinary_t2_eligible") is True:
            ordinary_count += 1
            if member.get("processing_disposition") != "ELIGIBLE":
                raise FirstSliceMaterializationError(
                    f"{label}: ordinary eligibility conflicts with processing disposition"
                )
        release_members.append({
            "source_id": member["source_id"],
            "source_version_id": source_version_id,
            "artifact_sha256": artifact_sha256,
            "receipt_sha256": receipt_sha256,
        })

    if attestation.get("registry_source_count") != len(registry_sources):
        raise FirstSliceMaterializationError("registry_source_count drift")
    if attestation.get("materialized_source_count") != len(members):
        raise FirstSliceMaterializationError("materialized_source_count drift")
    if attestation.get("ordinary_t2_eligible_count") != ordinary_count:
        raise FirstSliceMaterializationError("ordinary_t2_eligible_count drift")
    if attestation.get("ordinary_t2_blocked_count") != len(members) - ordinary_count:
        raise FirstSliceMaterializationError("ordinary_t2_blocked_count drift")
    if attestation.get("all_registry_sources_materialized") is not True:
        raise FirstSliceMaterializationError("attestation does not cover all registry sources")
    if attestation.get("all_sources_ordinary_t2_eligible") != (ordinary_count == len(members)):
        raise FirstSliceMaterializationError("all_sources_ordinary_t2_eligible drift")

    release_id = attestation.get("release_id")
    release_created_at = attestation.get("release_created_at")
    release_sha256 = attestation.get("release_sha256")
    if not isinstance(release_id, str) or not release_id:
        raise FirstSliceMaterializationError("attestation release_id required")
    if not isinstance(release_created_at, str):
        raise FirstSliceMaterializationError("attestation release_created_at required")
    _dt(release_created_at, "attestation.release_created_at")
    expected = build_release_manifest(
        release_id=release_id,
        created_at=release_created_at,
        receipts=release_members,
    )
    if release_sha256 != expected["release_sha256"]:
        raise FirstSliceMaterializationError("attestation release SHA does not match members")


def materialize_files(
    *,
    registry_path: str | Path,
    plan_path: str | Path,
    private_root: str | Path,
    public_repo_root: str | Path,
) -> dict[str, Any]:
    return materialize_capture_plan(
        registry=_load_json(registry_path),
        plan=_load_json(plan_path),
        private_root=private_root,
        public_repo_root=public_repo_root,
    )
