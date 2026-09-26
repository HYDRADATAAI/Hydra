#!/usr/bin/env python3
"""Materialize the nine first-slice source bodies into the private T1 store.

This tool performs NO network access. A caller must stage exact captured source
bodies under --staging-root as <source_id>.raw. The tool then:
- verifies the canonical nine-source registry,
- preflights all staged bodies before any store write,
- persists deterministic source versions through RawArtifactStore,
- reuses exact existing persisted receipts idempotently,
- creates/reuses one exact persisted release manifest,
- writes a safe summary containing hashes/metadata only.

It never publishes raw source bodies to the public repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STORE_SRC = ROOT / "constraint-t1-raw-artifact-store" / "src"
sys.path.insert(0, str(STORE_SRC))

from hydra_constraint_t1_raw import RawArtifactStore  # noqa: E402

REGISTRY_DEFAULT = (
    ROOT
    / "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
    / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"
)
EXPECTED_SOURCE_COUNT = 9
RELEASE_PREFIX = "REL-AIDC-FIRST-SLICE"


class MaterializationError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MaterializationError(f"JSON root must be object: {path}")
    return value


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _expected_content_type(url: str) -> str:
    return "application/pdf" if url.lower().split("?", 1)[0].endswith(".pdf") else "text/html"


def _validate_body(raw: bytes, *, content_type: str, source_id: str) -> None:
    if len(raw) < 256:
        raise MaterializationError(f"{source_id}: staged source body is implausibly small")
    prefix = raw[:4096].lower()
    if content_type == "application/pdf":
        if not raw.startswith(b"%PDF-"):
            raise MaterializationError(f"{source_id}: expected PDF bytes but PDF signature is absent")
    else:
        if b"<html" not in prefix and b"<!doctype" not in prefix:
            raise MaterializationError(f"{source_id}: expected HTML source body")
    for marker in (b"access denied", b"captcha", b"403 forbidden", b"404 not found"):
        if marker in prefix:
            raise MaterializationError(f"{source_id}: staged body looks like an error/interstitial page")


def _source_version_id(raw: bytes) -> str:
    return "SV-" + hashlib.sha256(raw).hexdigest()[:24]


def _receipt_path(private_root: Path, source_id: str, source_version_id: str) -> Path:
    return private_root / "receipts" / source_id / f"{source_version_id}.json"


def _load_or_persist(
    store: RawArtifactStore,
    *,
    raw: bytes,
    source: dict[str, Any],
    acquired_at: str,
) -> dict[str, Any]:
    source_id = str(source["source_id"])
    version_id = _source_version_id(raw)
    receipt_path = _receipt_path(store.root, source_id, version_id)
    if receipt_path.is_file():
        receipt = _load_json(receipt_path)
        issues = store.validate_receipt(receipt)
        if issues:
            raise MaterializationError(
                f"{source_id}: existing persisted receipt failed validation: {','.join(issues)}"
            )
        if receipt.get("artifact_sha256") != hashlib.sha256(raw).hexdigest():
            raise MaterializationError(f"{source_id}: existing receipt does not match staged bytes")
        return receipt

    return store.persist(
        raw_bytes=raw,
        source_id=source_id,
        source_version_id=version_id,
        content_type=_expected_content_type(str(source["url"])),
        acquired_at=acquired_at,
        available_at=acquired_at,
        source_locator=str(source["url"]),
        processing_disposition="ELIGIBLE",
    )


def _release_id(receipts: list[dict[str, Any]]) -> str:
    payload = "\n".join(
        sorted(f"{r['source_id']}:{r['receipt_sha256']}" for r in receipts)
    ).encode("utf-8")
    return f"{RELEASE_PREFIX}-{hashlib.sha256(payload).hexdigest()[:20].upper()}"


def _release_path(private_root: Path, release_id: str) -> Path:
    return private_root / "releases" / f"{release_id}.json"


def _load_or_release(
    store: RawArtifactStore,
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    release_id = _release_id(receipts)
    path = _release_path(store.root, release_id)
    if path.is_file():
        manifest = _load_json(path)
        issues = store.validate_stored_release_manifest(manifest)
        if issues:
            raise MaterializationError(
                "existing persisted release failed validation: " + ",".join(issues)
            )
        return manifest

    created_at = max(str(r["acquired_at"]) for r in receipts)
    return store.write_release_manifest(
        release_id=release_id,
        created_at=created_at,
        receipts=receipts,
    )


def materialize(
    *,
    staging_root: Path,
    private_root: Path,
    public_repo_root: Path,
    registry_path: Path,
    summary_path: Path,
    acquired_at: str | None = None,
) -> dict[str, Any]:
    registry = _load_json(registry_path)
    sources = registry.get("sources")
    if not isinstance(sources, list) or len(sources) != EXPECTED_SOURCE_COUNT:
        raise MaterializationError(
            f"expected exactly {EXPECTED_SOURCE_COUNT} registered first-slice sources"
        )
    source_ids = [str(s.get("source_id", "")) for s in sources]
    if any(not sid for sid in source_ids) or len(set(source_ids)) != EXPECTED_SOURCE_COUNT:
        raise MaterializationError("source registry identities are missing or duplicated")

    # Full preflight before any private-store mutation.
    staged: list[tuple[dict[str, Any], bytes]] = []
    for source in sources:
        sid = str(source["source_id"])
        path = staging_root / f"{sid}.raw"
        if not path.is_file():
            raise MaterializationError(f"{sid}: exact staged body missing at {path}")
        raw = path.read_bytes()
        _validate_body(
            raw,
            content_type=_expected_content_type(str(source["url"])),
            source_id=sid,
        )
        staged.append((source, raw))

    capture_time = acquired_at or _iso_now()
    store = RawArtifactStore(private_root, public_repo_root=public_repo_root)

    receipts = [
        _load_or_persist(store, raw=raw, source=source, acquired_at=capture_time)
        for source, raw in staged
    ]
    for receipt in receipts:
        issues = store.validate_receipt(receipt)
        if issues:
            raise MaterializationError(
                f"{receipt['source_id']}: persisted receipt invalid: {','.join(issues)}"
            )

    release = _load_or_release(store, receipts)
    issues = store.validate_stored_release_manifest(release)
    if issues:
        raise MaterializationError("persisted release invalid: " + ",".join(issues))

    eligible = [
        receipt
        for receipt in receipts
        if store.validate_receipt(receipt) == ()
        and receipt["processing_disposition"] == "ELIGIBLE"
    ]
    if len(eligible) != EXPECTED_SOURCE_COUNT:
        raise MaterializationError("not all nine persisted source versions are eligible")

    summary = {
        "schema_version": "hydra-constraint-first-slice-private-materialization-summary/v1",
        "slice_id": registry.get("slice_id"),
        "source_count": len(receipts),
        "eligible_source_count": len(eligible),
        "raw_source_content_published": False,
        "historical_backdating_performed": False,
        "available_at_policy": "ACQUIRED_AT_CONSERVATIVE_CURRENT_CAPTURE",
        "release_id": release["release_id"],
        "release_sha256": release["release_sha256"],
        "release_member_count": len(release["members"]),
        "receipts": [
            {
                "source_id": r["source_id"],
                "source_version_id": r["source_version_id"],
                "artifact_sha256": r["artifact_sha256"],
                "receipt_sha256": r["receipt_sha256"],
                "byte_length": r["byte_length"],
                "content_type": r["content_type"],
                "acquired_at": r["acquired_at"],
                "available_at": r["available_at"],
                "processing_disposition": r["processing_disposition"],
            }
            for r in sorted(receipts, key=lambda row: row["source_id"])
        ],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--public-repo-root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=REGISTRY_DEFAULT)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument(
        "--acquired-at",
        help="Optional timezone-aware ISO-8601 capture time; defaults to current UTC.",
    )
    args = parser.parse_args()
    try:
        summary = materialize(
            staging_root=args.staging_root.resolve(),
            private_root=args.private_root.resolve(),
            public_repo_root=args.public_repo_root.resolve(),
            registry_path=args.registry.resolve(),
            summary_path=args.summary.resolve(),
            acquired_at=args.acquired_at,
        )
    except (MaterializationError, ValueError, OSError, json.JSONDecodeError) as exc:
        print("CONSTRAINT_FIRST_SLICE_PRIVATE_T1_MATERIALIZATION=BLOCKED")
        print(f"ERROR={exc}")
        return 1

    print("CONSTRAINT_FIRST_SLICE_PRIVATE_T1_MATERIALIZATION=PASS")
    print(f"MATERIALIZED_SOURCE_VERSIONS={summary['source_count']}")
    print(f"ELIGIBLE_SOURCE_VERSIONS={summary['eligible_source_count']}")
    print(f"RELEASE_ID={summary['release_id']}")
    print(f"RELEASE_SHA256={summary['release_sha256']}")
    print("RAW_SOURCE_CONTENT_PUBLISHED=NO")
    print("HISTORICAL_BACKDATING_PERFORMED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
