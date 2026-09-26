"""Build a sanitized repo-safe status from a validated private T1 attestation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .first_slice_materialization import (
    ATTESTATION_SCHEMA,
    FirstSliceMaterializationError,
    validate_public_materialization_attestation,
)


PUBLIC_STATUS_SCHEMA = "hydra-constraint-first-slice-post-capture-public-status/v1"


class PostCaptureStatusError(ValueError):
    pass


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def build_public_status(
    *,
    attestation: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        validate_public_materialization_attestation(
            attestation=attestation,
            registry=registry,
        )
    except FirstSliceMaterializationError as exc:
        raise PostCaptureStatusError(str(exc)) from exc

    members = attestation.get("members")
    if not isinstance(members, list) or len(members) != 9:
        raise PostCaptureStatusError("post-capture closure requires exactly nine attested sources")

    if attestation.get("registry_source_count") != 9:
        raise PostCaptureStatusError("registry_source_count must equal nine")
    if attestation.get("materialized_source_count") != 9:
        raise PostCaptureStatusError("materialized_source_count must equal nine")
    if attestation.get("ordinary_t2_eligible_count") != 9:
        raise PostCaptureStatusError("all nine sources must be ordinary T1->T2 eligible")
    if attestation.get("ordinary_t2_blocked_count") != 0:
        raise PostCaptureStatusError("ordinary_t2_blocked_count must be zero")
    if attestation.get("all_registry_sources_materialized") is not True:
        raise PostCaptureStatusError("all registry sources must be materialized")
    if attestation.get("all_sources_ordinary_t2_eligible") is not True:
        raise PostCaptureStatusError("all sources must be ordinary T1->T2 eligible")

    for index, member in enumerate(members):
        if member.get("processing_disposition") != "ELIGIBLE":
            raise PostCaptureStatusError(f"members[{index}] is not ELIGIBLE")
        if member.get("ordinary_t2_eligible") is not True:
            raise PostCaptureStatusError(f"members[{index}] is not ordinary T1->T2 eligible")

    sanitized_members = [
        {
            "source_id": member["source_id"],
            "source_version_id": member["source_version_id"],
            "artifact_sha256": member["artifact_sha256"],
            "receipt_sha256": member["receipt_sha256"],
            "byte_length": member["byte_length"],
            "content_type": member["content_type"],
            "acquired_at": member["acquired_at"],
            "available_at": member["available_at"],
            "processing_disposition": member["processing_disposition"],
            "ordinary_t2_eligible": member["ordinary_t2_eligible"],
        }
        for member in members
    ]
    sanitized_members.sort(key=lambda row: row["source_id"])

    attestation_sha256 = hashlib.sha256(_canonical_json(dict(attestation))).hexdigest()

    return {
        "schema_version": PUBLIC_STATUS_SCHEMA,
        "slice_id": attestation["slice_id"],
        "source_attestation_schema": ATTESTATION_SCHEMA,
        "source_attestation_sha256": attestation_sha256,
        "release_id": attestation["release_id"],
        "release_sha256": attestation["release_sha256"],
        "release_created_at": attestation["release_created_at"],
        "source_count": 9,
        "materialized_source_count": 9,
        "ordinary_t2_eligible_count": 9,
        "public_raw_content_published": False,
        "private_paths_published": False,
        "historical_backdating_performed": False,
        "strict_historical_replay_promoted": False,
        "canonical_admission_promoted": False,
        "native_signed_t5_t6_receipt_present": False,
        "closure": {
            "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION": "CLOSED_BY_VALIDATED_PRIVATE_T1_ATTESTATION",
            "ORDINARY_SOURCE_VERSION_HASHES": "COMPLETE_FOR_CAPTURED_SOURCE_VERSIONS",
            "PERSISTED_T1_T2_CURRENT_CUSTODY": "COMPLETE",
        },
        "still_blocked": {
            "ORDINARY_POINT_IN_TIME_REPLAY_READY": "NO",
            "HISTORICAL_AVAILABLE_AT_BEFORE_CAPTURE": "UNPROVEN",
            "ORDINARY-POINT-IN-TIME-REPLAY-SOURCE-VERSION-HASHES-INCOMPLETE": "HASH_COMPONENT_COMPLETE_HISTORICAL_AS_OF_COMPONENT_REMAINS_BLOCKED",
            "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT": "OPEN",
            "CANONICAL-T5-T6-CONSTRAINT-AND-BENEFICIARY-ADMISSION-NOT-AUTHORIZED": "OPEN",
        },
        "members": sanitized_members,
    }


def build_public_status_file(
    *,
    attestation_path: str | Path,
    registry_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    try:
        attestation = json.loads(Path(attestation_path).read_text(encoding="utf-8"))
        registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise PostCaptureStatusError("unable to load attestation or registry JSON") from exc

    if not isinstance(attestation, dict) or not isinstance(registry, dict):
        raise PostCaptureStatusError("attestation and registry must be JSON objects")

    status = build_public_status(attestation=attestation, registry=registry)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return status
