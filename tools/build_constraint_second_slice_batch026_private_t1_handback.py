#!/usr/bin/env python3
"""Build a private Batch026 T1 handback after exact verification succeeds."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEUE_REL = Path("docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json")
SCHEMA = "hydra-constraint-second-slice-private-t1-handback/v1"


def fail(message: str) -> None:
    print("BATCH026_PRIVATE_T1_HANDBACK=FAIL")
    print("ERROR=" + message)
    raise SystemExit(1)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail(f"missing JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"JSON root must be object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--private-root", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    private_root = Path(args.private_root).expanduser().resolve()
    output_path = Path(args.output_path).expanduser().resolve()

    if output_path == repo_root or output_path.is_relative_to(repo_root):
        fail("handback output must remain outside public repository")

    queue_doc = load_json(repo_root / QUEUE_REL)
    queue = queue_doc.get("queue")
    if not isinstance(queue, list) or len(queue) != 41:
        fail("queue must contain exactly 41 capture intents")
    sys.path.insert(0, str(repo_root / "tools"))
    from constraint_source_quarantine import QuarantinePolicyError, reject_retired_batch026
    try:
        reject_retired_batch026(repo_root, queue, operation="handback generation")
    except QuarantinePolicyError as exc:
        fail(str(exc))

    sys.path.insert(0, str(repo_root / "constraint-t1-raw-artifact-store" / "src"))
    from hydra_constraint_t1_raw.store import RawArtifactStore, is_ordinary_t2_eligible

    store = RawArtifactStore(root=private_root, public_repo_root=repo_root)
    release_path = private_root / "releases" / f"{queue_doc['release_id']}.json"
    release = load_json(release_path)
    release_issues = store.validate_stored_release_manifest(release)
    if release_issues:
        fail("release invalid: " + ",".join(release_issues))

    expected = {(row["source_id"], row["source_version_id"]) for row in queue}
    actual = {
        (row.get("source_id"), row.get("source_version_id"))
        for row in release.get("members", [])
    }
    if actual != expected:
        fail("release membership does not exactly match Batch026 queue")

    records = []
    for item in queue:
        receipt_path = private_root / "receipts" / item["source_id"] / f"{item['source_version_id']}.json"
        receipt = load_json(receipt_path)
        issues = store.validate_receipt(receipt)
        if issues:
            fail(f"{item['source_id']}: receipt invalid: {','.join(issues)}")
        if not is_ordinary_t2_eligible(receipt=receipt, release_manifest=release, store=store):
            fail(f"{item['source_id']}: not ordinary T2 eligible")
        if receipt["acquired_at"] != receipt["available_at"]:
            fail(f"{item['source_id']}: unexpected historical backdating")
        records.append({
            "source_id": receipt["source_id"],
            "source_version_id": receipt["source_version_id"],
            "artifact_sha256": receipt["artifact_sha256"],
            "receipt_sha256": receipt["receipt_sha256"],
            "byte_length": receipt["byte_length"],
            "content_type": receipt["content_type"],
            "registered_source_locator": item["source_locator"],
            "capture_source_locator": receipt["source_locator"],
            "acquired_at": receipt["acquired_at"],
            "available_at": receipt["available_at"],
            "processing_disposition": receipt["processing_disposition"],
        })

    handback = {
        "schema_version": SCHEMA,
        "record_id": "HYDRA_CONSTRAINT_SEMI_B026_PRIVATE_T1_HANDBACK_V001",
        "slice_id": "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queue_record_id": queue_doc["record_id"],
        "release_id": release["release_id"],
        "release_sha256": release["release_sha256"],
        "expected_source_count": 41,
        "valid_receipt_count": 41,
        "ordinary_t2_eligible_source_count": 41,
        "historical_backdating_used": False,
        "members": records,
        "next_action": "INGEST_BATCH026_PRIVATE_T1_HANDBACK_INTO_SEMICONDUCTOR_ORDINARY_REPLAY_LANE",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(handback, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("BATCH026_PRIVATE_T1_HANDBACK=PASS")
    print("OUTPUT_PATH=" + str(output_path))
    print("RELEASE_ID=" + release["release_id"])
    print("RELEASE_SHA256=" + release["release_sha256"])
    print("ORDINARY_T2_ELIGIBLE_SOURCES=41")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
