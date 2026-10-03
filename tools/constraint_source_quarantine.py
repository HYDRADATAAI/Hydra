#!/usr/bin/env python3
"""Fail-closed guards for superseded semiconductor source queues."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


class QuarantinePolicyError(RuntimeError):
    """Raised when a queue violates a quarantine or retirement rule."""


def reject_retired_batch026(repo_root: Path, queue: Any, *, operation: str) -> None:
    """Reject operational use of the historical Batch026 queue.

    Batch026 remains in the repository as immutable history. Its original 41-row
    queue includes the Batch030 Micron quarantine set and cannot be used for
    capture, materialization, verification, or handback.
    """
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
