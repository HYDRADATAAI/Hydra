#!/usr/bin/env python3
"""Verify Batch026 semiconductor private T1 receipts and exact release membership."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

QUEUE_REL = "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"


def fail(message: str) -> None:
    print("BATCH026_PRIVATE_T1_VERIFICATION=FAIL")
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
    parser.add_argument("--queue-path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    private_root = Path(args.private_root).expanduser().resolve()
    queue_path = Path(args.queue_path).expanduser().resolve() if args.queue_path else repo_root / QUEUE_REL
    queue_doc = load_json(queue_path)
    queue = queue_doc.get("queue")
    if not isinstance(queue, list) or len(queue) != 41:
        fail("queue must contain exactly 41 capture intents")

    sys.path.insert(0, str(repo_root / "constraint-t1-raw-artifact-store" / "src"))
    from hydra_constraint_t1_raw.store import RawArtifactStore, is_ordinary_t2_eligible

    store = RawArtifactStore(root=private_root, public_repo_root=repo_root)
    receipts = []
    missing = []
    invalid = []

    for item in queue:
        receipt_path = private_root / "receipts" / item["source_id"] / f"{item['source_version_id']}.json"
        if not receipt_path.is_file():
            missing.append(item["source_id"])
            continue
        receipt = load_json(receipt_path)
        issues = store.validate_receipt(receipt)
        if issues:
            invalid.append((item["source_id"], ",".join(issues)))
            continue
        if receipt.get("source_locator") != item["source_locator"]:
            invalid.append((item["source_id"], "source_locator_mismatch"))
            continue
        if receipt.get("acquired_at") != receipt.get("available_at"):
            invalid.append((item["source_id"], "unexpected_historical_backdating"))
            continue
        if receipt.get("processing_disposition") != "ELIGIBLE":
            invalid.append((item["source_id"], "processing_disposition_not_eligible"))
            continue
        receipts.append(receipt)

    release_path = private_root / "releases" / f"{queue_doc['release_id']}.json"
    release = load_json(release_path) if release_path.is_file() else None
    release_issues = ("release_record_missing",) if release is None else store.validate_stored_release_manifest(release)

    expected_members = {
        (item["source_id"], item["source_version_id"]) for item in queue
    }
    actual_members = set()
    if release is not None:
        actual_members = {
            (member.get("source_id"), member.get("source_version_id"))
            for member in release.get("members", [])
        }

    eligible = 0
    if release is not None and not release_issues:
        for receipt in receipts:
            if is_ordinary_t2_eligible(receipt=receipt, release_manifest=release, store=store):
                eligible += 1

    print("BATCH026_PRIVATE_T1_VERIFICATION_SUMMARY")
    print(f"EXPECTED_RECEIPTS=41")
    print(f"VALID_RECEIPTS={len(receipts)}")
    print(f"MISSING_RECEIPTS={len(missing)}")
    print(f"INVALID_RECEIPTS={len(invalid)}")
    print(f"RELEASE_VALID={'YES' if not release_issues else 'NO'}")
    print(f"RELEASE_MEMBERS={len(actual_members)}")
    print(f"ORDINARY_T2_ELIGIBLE_SOURCES={eligible}")

    if missing:
        print("MISSING_SOURCE_IDS=" + ",".join(missing))
    if invalid:
        print("INVALID_SOURCE_IDS=" + ",".join(source for source, _ in invalid))
    if release_issues:
        print("RELEASE_ISSUES=" + ",".join(release_issues))
    if actual_members != expected_members:
        print("RELEASE_MEMBERSHIP_MISMATCH=YES")

    if (
        len(receipts) != 41
        or missing
        or invalid
        or release_issues
        or actual_members != expected_members
        or eligible != 41
    ):
        print("BATCH026_PRIVATE_T1_VERIFICATION=BLOCKED")
        return 1

    print("BATCH026_PRIVATE_T1_VERIFICATION=PASS")
    print("T1_RELEASE_ID=" + release["release_id"])
    print("T1_RELEASE_SHA256=" + release["release_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
