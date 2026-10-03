#!/usr/bin/env python3
"""Materialize already-captured Batch026 semiconductor files into private T1 storage.

This tool performs NO network acquisition. Each queue item must already exist in
a private inbox together with a fail-closed capture sidecar.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

QUEUE_REL = "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
LOCATOR_OVERLAY_REL = "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH029_SEMICONDUCTOR_MICRON_CAPTURE_LOCATOR_REMEDIATION_V001_20260927.json"
SIDECAR_SCHEMA = "hydra-semiconductor-private-capture-sidecar/v1"
ALLOWED_HTML_TYPES = {"text/html", "multipart/related", "application/x-mimearchive"}


def fail(message: str) -> None:
    raise SystemExit(f"BATCH026_PRIVATE_T1_MATERIALIZATION=FAIL\nERROR={message}")


def parse_zoned(value: str, field: str) -> None:
    if not isinstance(value, str) or not value:
        fail(f"{field} missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        fail(f"{field} invalid: {exc}")
    if parsed.tzinfo is None:
        fail(f"{field} must be offset-aware")


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail(f"missing JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"JSON root must be object: {path}")
    return value


def load_remediations(path: Path) -> dict[str, dict[str, Any]]:
    doc = load_json(path)
    rows = doc.get("remediations")
    if not isinstance(rows, list):
        fail("locator remediation rows missing")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("source_id"), str):
            fail("invalid locator remediation row")
        result[row["source_id"]] = row
    return result


def locator_allowed(item: dict[str, Any], locator: str, remediation: dict[str, Any] | None) -> bool:
    if remediation is None:
        return locator == item["source_locator"]
    parsed = urlparse(locator)
    return (
        parsed.scheme.lower() == "https"
        and (parsed.hostname or "").lower() == "s25.q4cdn.com"
        and isinstance(remediation.get("required_path_prefix"), str)
        and parsed.path.startswith(remediation["required_path_prefix"])
    )


def sidecar_path(capture_path: Path) -> Path:
    return Path(str(capture_path) + ".capture.json")


def validate_sidecar(
    item: dict[str, Any],
    sidecar: dict[str, Any],
    remediation: dict[str, Any] | None,
) -> tuple[str, str, str]:
    required = {
        "schema_version", "capture_intent_id", "source_id", "source_version_id",
        "source_locator", "capture_completed_at", "content_type",
        "processing_disposition", "historical_backdating_authorized",
    }
    if set(sidecar) != required:
        fail(f"{item['source_id']}: sidecar field set invalid")
    if sidecar["schema_version"] != SIDECAR_SCHEMA:
        fail(f"{item['source_id']}: sidecar schema invalid")
    for field in ("capture_intent_id", "source_id", "source_version_id"):
        if sidecar[field] != item[field]:
            fail(f"{item['source_id']}: sidecar {field} mismatch")
    source_locator = sidecar["source_locator"]
    if not isinstance(source_locator, str) or not locator_allowed(item, source_locator, remediation):
        fail(f"{item['source_id']}: sidecar source_locator is not allowed by locator-remediation policy")
    if sidecar["processing_disposition"] != "ELIGIBLE":
        fail(f"{item['source_id']}: sidecar disposition must be ELIGIBLE")
    if sidecar["historical_backdating_authorized"] is not False:
        fail(f"{item['source_id']}: historical backdating is not authorized")
    timestamp = sidecar["capture_completed_at"]
    parse_zoned(timestamp, "capture_completed_at")
    content_type = sidecar["content_type"]
    if not isinstance(content_type, str) or not content_type:
        fail(f"{item['source_id']}: content_type missing")
    hint = item["content_type_hint"]
    if hint == "application/pdf" and content_type != "application/pdf":
        fail(f"{item['source_id']}: expected application/pdf")
    if hint == "text/html" and content_type not in ALLOWED_HTML_TYPES:
        fail(f"{item['source_id']}: expected HTML/MHTML content type")
    return timestamp, content_type, source_locator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--private-root", required=True)
    parser.add_argument("--inbox-root", required=True)
    parser.add_argument("--queue-path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    private_root = Path(args.private_root).expanduser().resolve()
    inbox_root = Path(args.inbox_root).expanduser().resolve()
    if inbox_root == repo_root or inbox_root.is_relative_to(repo_root):
        fail("private inbox must be outside public repository")

    queue_path = Path(args.queue_path).expanduser().resolve() if args.queue_path else repo_root / QUEUE_REL
    queue_doc = load_json(queue_path)
    queue = queue_doc.get("queue")
    if not isinstance(queue, list) or len(queue) != 41:
        fail("queue must contain exactly 41 capture intents")
    remediations = load_remediations(repo_root / LOCATOR_OVERLAY_REL)

    missing: list[str] = []
    prepared: list[tuple[dict[str, Any], Path, dict[str, Any], str, str, str]] = []
    for item in queue:
        capture_path = inbox_root / item["inbox_filename"]
        sc_path = sidecar_path(capture_path)
        if not capture_path.is_file():
            missing.append(f"FILE:{item['source_id']}:{capture_path}")
            continue
        if not sc_path.is_file():
            missing.append(f"SIDECAR:{item['source_id']}:{sc_path}")
            continue
        if capture_path.stat().st_size <= 0:
            fail(f"{item['source_id']}: capture file is empty")
        sidecar = load_json(sc_path)
        timestamp, content_type, source_locator = validate_sidecar(
            item,
            sidecar,
            remediations.get(item["source_id"]),
        )
        prepared.append((item, capture_path, sidecar, timestamp, content_type, source_locator))

    if missing:
        print("BATCH026_PRIVATE_T1_MATERIALIZATION=BLOCKED")
        print(f"EXPECTED=41")
        print(f"READY={len(prepared)}")
        print(f"MISSING={len(missing)}")
        for entry in missing:
            print(entry)
        return 1

    print("BATCH026_PRIVATE_CAPTURE_INBOX_VALIDATION=PASS")
    print("CAPTURE_FILES_READY=41")
    if args.dry_run:
        print("DRY_RUN=YES")
        return 0

    package_src = repo_root / "constraint-t1-raw-artifact-store" / "src"
    sys.path.insert(0, str(package_src))
    from hydra_constraint_t1_raw.store import RawArtifactStore, is_ordinary_t2_eligible

    store = RawArtifactStore(root=private_root, public_repo_root=repo_root)
    receipts = []
    for item, capture_path, sidecar, timestamp, content_type, source_locator in prepared:
        receipt = store.persist(
            raw_bytes=capture_path.read_bytes(),
            source_id=item["source_id"],
            source_version_id=item["source_version_id"],
            content_type=content_type,
            acquired_at=timestamp,
            available_at=timestamp,
            source_locator=source_locator,
            processing_disposition="ELIGIBLE",
        )
        issues = store.validate_receipt(receipt)
        if issues:
            fail(f"{item['source_id']}: persisted receipt invalid: {','.join(issues)}")
        receipts.append(receipt)

    release = store.write_release_manifest(
        release_id=queue_doc["release_id"],
        created_at=datetime.now(timezone.utc).isoformat(),
        receipts=receipts,
    )
    release_issues = store.validate_stored_release_manifest(release)
    if release_issues:
        fail("stored release invalid: " + ",".join(release_issues))

    eligible = sum(
        1 for receipt in receipts
        if is_ordinary_t2_eligible(receipt=receipt, release_manifest=release, store=store)
    )
    if eligible != 41:
        fail(f"ordinary T2 eligibility incomplete: {eligible}/41")

    print("BATCH026_PRIVATE_T1_MATERIALIZATION=PASS")
    print("VALID_T1_RECEIPTS=41")
    print("T1_RELEASE_ID=" + release["release_id"])
    print("T1_RELEASE_SHA256=" + release["release_sha256"])
    print("ORDINARY_T2_ELIGIBLE_SOURCES=41")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
