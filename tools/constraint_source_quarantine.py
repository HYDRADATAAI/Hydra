#!/usr/bin/env python3
"""Fail-closed guards for superseded semiconductor source queues."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

MICRON_QUARANTINE_RELATIVE_PATH = Path(
    "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/"
    "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001_20260927.json"
)
EXPECTED_MICRON_QUARANTINED_SOURCE_IDS = (
    "SRC-SEMI-MICRON-Q2FY25-REMARKS-2025-03-20",
    "SRC-SEMI-B021-MICRON-Q1FY26-REMARKS-2025-12-17",
    "SRC-SEMI-B021-MICRON-Q3FY24-REMARKS-2024-06-26",
    "SRC-SEMI-B021-MICRON-Q3FY25-REMARKS-2025-06-25",
    "SRC-SEMI-B021-MICRON-Q4FY25-REMARKS-2025-09-23",
    "SRC-SEMI-B022-GLOBENEWSWIRE-MICRON-HBM3E-2024-02-26",
    "SRC-SEMI-B022-MICRON-HBM3E-VOLUME-2024-02-26",
    "SRC-SEMI-B023-MICRON-Q1FY24-REMARKS-2023-12-20",
    "SRC-SEMI-B023-MICRON-Q2FY26-MARKET-OUTLOOK-2026-03-18",
)
BATCH026_QUEUE_RELATIVE_PATH = Path(
    "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/"
    "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
)
EXPECTED_BATCH026_QUEUE_SCHEMA = "hydra-constraint-second-slice-private-t1-capture-queue/v1"
EXPECTED_BATCH026_QUEUE_RECORD_ID = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001"
EXPECTED_BATCH026_QUEUE_SLICE_ID = "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
EXPECTED_BATCH026_QUEUE_COUNT = 41
EXPECTED_QUARANTINED_ROW_PROJECTION_SHA256 = "999623e86ebc75ec2f2f4e69c7a4ffc3b81c1f45c45487981e250444f6b6913a"
CAPTURE_IDENTITY_FIELDS = (
    "source_id",
    "source_version_id",
    "capture_intent_id",
    "source_locator",
    "inbox_filename",
)
FORBIDDEN_CAPTURE_PROVIDER_DOMAINS = ("micron.com", "globenewswire.com")
FORBIDDEN_SPECIAL_SCHEME_AUTHORITY_CHARACTERS = ("\\", "%")


class QuarantinePolicyError(RuntimeError):
    """Raised when a queue violates a quarantine or retirement rule."""


def load_validated_micron_quarantine_ids(repo_root: Path) -> set[str]:
    """Load the canonical Batch030 manifest and require its exact fixed policy."""
    root = Path(repo_root).expanduser().resolve()
    manifest_path = root / MICRON_QUARANTINE_RELATIVE_PATH
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QuarantinePolicyError(f"unable to load Batch030 quarantine manifest: {exc}") from exc

    if not isinstance(manifest, dict):
        raise QuarantinePolicyError("Batch030 quarantine manifest must be an object")
    if manifest.get("schema_version") != "hydra-constraint-second-slice-source-quarantine/v1":
        raise QuarantinePolicyError("Batch030 Micron quarantine schema drift")
    if manifest.get("record_id") != "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001":
        raise QuarantinePolicyError("Batch030 Micron quarantine record drift")
    if manifest.get("slice_id") != "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1":
        raise QuarantinePolicyError("Batch030 Micron quarantine slice drift")
    if manifest.get("predecessor_artifacts_mutated") is not False or manifest.get("retry_authorized") is not False:
        raise QuarantinePolicyError("Batch030 Micron quarantine mutation/retry policy drift")

    quarantined = manifest.get("quarantined")
    expected = set(EXPECTED_MICRON_QUARANTINED_SOURCE_IDS)
    if (
        not isinstance(quarantined, list)
        or len(quarantined) != len(expected)
        or any(not isinstance(source_id, str) or not source_id for source_id in quarantined)
        or len(set(quarantined)) != len(expected)
        or set(quarantined) != expected
    ):
        raise QuarantinePolicyError("Batch030 Micron quarantine source-ID set drift")

    return expected


def load_validated_quarantined_batch026_rows(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Load the canonical 41-row B026 queue and pin the exact quarantined identities."""
    quarantined_ids = load_validated_micron_quarantine_ids(repo_root)
    queue_path = Path(repo_root).expanduser().resolve() / BATCH026_QUEUE_RELATIVE_PATH
    try:
        queue_doc = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise QuarantinePolicyError(f"unable to load canonical Batch026 capture queue: {exc}") from exc

    if not isinstance(queue_doc, dict):
        raise QuarantinePolicyError("canonical Batch026 capture queue must be an object")
    if queue_doc.get("schema_version") != EXPECTED_BATCH026_QUEUE_SCHEMA:
        raise QuarantinePolicyError("canonical Batch026 capture queue schema drift")
    if queue_doc.get("record_id") != EXPECTED_BATCH026_QUEUE_RECORD_ID:
        raise QuarantinePolicyError("canonical Batch026 capture queue record drift")
    if queue_doc.get("slice_id") != EXPECTED_BATCH026_QUEUE_SLICE_ID:
        raise QuarantinePolicyError("canonical Batch026 capture queue slice drift")
    rows = queue_doc.get("queue")
    if queue_doc.get("source_count") != EXPECTED_BATCH026_QUEUE_COUNT or not isinstance(rows, list) or len(rows) != EXPECTED_BATCH026_QUEUE_COUNT:
        raise QuarantinePolicyError("canonical Batch026 capture queue must contain exactly 41 rows")

    seen: dict[str, set[str]] = {field: set() for field in CAPTURE_IDENTITY_FIELDS}
    by_source_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise QuarantinePolicyError(f"canonical Batch026 capture queue row {index} must be an object")
        if row.get("ordinal") != index + 1:
            raise QuarantinePolicyError("canonical Batch026 capture queue ordinal drift")
        for field in CAPTURE_IDENTITY_FIELDS:
            value = row.get(field)
            if not isinstance(value, str) or not value:
                raise QuarantinePolicyError(f"canonical Batch026 capture queue row {index} has invalid {field}")
            if value in seen[field]:
                raise QuarantinePolicyError(f"canonical Batch026 capture queue has duplicate {field}")
            seen[field].add(value)
        if not row["source_locator"].startswith("https://"):
            raise QuarantinePolicyError("canonical Batch026 capture queue locator must be HTTPS")
        if Path(row["inbox_filename"]).name != row["inbox_filename"]:
            raise QuarantinePolicyError("canonical Batch026 capture queue filename must be a basename")
        by_source_id[row["source_id"]] = row

    if set(quarantined_ids) - set(by_source_id):
        raise QuarantinePolicyError("canonical Batch026 capture queue is missing quarantined source IDs")
    quarantined_rows = {source_id: by_source_id[source_id] for source_id in quarantined_ids}
    projection = [
        {field: row[field] for field in CAPTURE_IDENTITY_FIELDS}
        for _, row in sorted(quarantined_rows.items())
    ]
    projection_bytes = json.dumps(
        projection,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    digest = hashlib.sha256(projection_bytes).hexdigest()
    if digest != EXPECTED_QUARANTINED_ROW_PROJECTION_SHA256:
        raise QuarantinePolicyError("canonical Batch026 quarantined-row identity projection drift")
    return quarantined_rows


def _forbidden_capture_provider(locator: Any) -> str | None:
    if not isinstance(locator, str) or not locator:
        return None
    try:
        parts = urlsplit(locator)
    except ValueError as exc:
        raise QuarantinePolicyError("capture locator has an invalid hostname") from exc
    scheme = parts.scheme.lower()
    if scheme in {"http", "https"}:
        scheme_prefix = f"{scheme}://"
        if locator[: len(scheme_prefix)].lower() != scheme_prefix:
            raise QuarantinePolicyError(
                "SUPERSEDED_BY_BATCH030_QUARANTINE: capture locator has a noncanonical HTTP(S) authority"
            )
        raw_authority = locator[len(scheme_prefix) :].split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        if (
            not parts.netloc
            or not parts.hostname
            or any(marker in raw_authority for marker in FORBIDDEN_SPECIAL_SCHEME_AUTHORITY_CHARACTERS)
            or any(ord(character) <= 0x20 or ord(character) == 0x7F for character in raw_authority)
        ):
            raise QuarantinePolicyError(
                "SUPERSEDED_BY_BATCH030_QUARANTINE: capture locator has ambiguous HTTP(S) authority syntax"
            )
    hostname = parts.hostname
    if not hostname:
        return None
    try:
        normalized_host = hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise QuarantinePolicyError("capture locator hostname is invalid") from exc
    for domain in FORBIDDEN_CAPTURE_PROVIDER_DOMAINS:
        if normalized_host == domain or normalized_host.endswith("." + domain):
            return domain
    return None


def reject_forbidden_capture_locator(locator: Any, *, operation: str) -> None:
    """Reject provider hosts and URL authorities parsed differently by browsers."""
    provider = _forbidden_capture_provider(locator)
    if provider is not None:
        raise QuarantinePolicyError(
            f"SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 {operation} is closed; "
            f"locator resolves to forbidden provider domain {provider}"
        )


def reject_quarantined_capture_item(
    repo_root: Path,
    item: Mapping[str, Any],
    capture_locator: str | None,
    *,
    operation: str,
) -> None:
    """Reject an exact quarantined row or any copy retaining one of its identity markers."""
    if not isinstance(item, Mapping):
        raise QuarantinePolicyError("capture item must be an object")
    rows = load_validated_quarantined_batch026_rows(repo_root)
    candidate_markers = {
        "source_id": item.get("source_id"),
        "source_version_id": item.get("source_version_id"),
        "capture_intent_id": item.get("capture_intent_id"),
        "source_locator": item.get("source_locator"),
        "inbox_filename": item.get("inbox_filename"),
        "capture_locator": capture_locator,
    }
    for locator_field in ("source_locator", "capture_locator"):
        try:
            reject_forbidden_capture_locator(
                candidate_markers[locator_field], operation=operation
            )
        except QuarantinePolicyError as exc:
            if locator_field not in str(exc):
                raise QuarantinePolicyError(f"{exc}; rejected {locator_field}") from exc
            raise
    for quarantined_source_id, row in rows.items():
        for marker, value in candidate_markers.items():
            row_field = "source_locator" if marker == "capture_locator" else marker
            if isinstance(value, str) and value and value == row[row_field]:
                raise QuarantinePolicyError(
                    f"SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 {operation} is closed; "
                    f"{marker} matches quarantined source {quarantined_source_id}"
                )


def reject_retired_batch026(repo_root: Path, queue: Any, *, operation: str) -> None:
    """Reject operational use of the historical Batch026 queue.

    Batch026 remains in the repository as immutable history. Its original 41-row
    queue includes the Batch030 Micron quarantine set and cannot be used for
    capture, materialization, verification, or handback.
    """
    expected = set(load_validated_quarantined_batch026_rows(repo_root))

    if not isinstance(queue, list):
        raise QuarantinePolicyError("Batch026 historical queue must be a list")
    queue_ids: set[str] = set()
    for index, item in enumerate(queue):
        if not isinstance(item, dict) or not isinstance(item.get("source_id"), str) or not item["source_id"]:
            raise QuarantinePolicyError(f"Batch026 historical queue[{index}] has no valid source_id")
        if item["source_id"] in queue_ids:
            raise QuarantinePolicyError("Batch026 historical queue contains duplicate source IDs")
        queue_ids.add(item["source_id"])
    if not expected.issubset(queue_ids):
        raise QuarantinePolicyError("Batch026 historical queue no longer contains the exact Batch030 quarantine set")

    raise QuarantinePolicyError(
        f"SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 {operation} is closed; "
        f"{len(expected)} quarantined source IDs remain in its historical queue"
    )
