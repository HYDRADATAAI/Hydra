"""Private, immutable T1 raw-artifact persistence.

This module performs no network access. Callers provide bytes captured through an
authorized acquisition path. Raw bytes are written only to a caller-supplied
private root outside the public repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


RECEIPT_SCHEMA = "hydra-t1-raw-artifact-receipt/v1"
RELEASE_SCHEMA = "hydra-t1-release-bundle/v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")
ELIGIBLE_DISPOSITION = "ELIGIBLE"
ALLOWED_DISPOSITIONS = {"ELIGIBLE", "QUARANTINED", "INELIGIBLE"}


class ArtifactIntegrityError(RuntimeError):
    pass


class ImmutableRecordError(RuntimeError):
    pass


class PublicRepositoryRootError(RuntimeError):
    pass


@dataclass(frozen=True)
class RawArtifactStore:
    root: Path
    public_repo_root: Path | None = None

    def __post_init__(self) -> None:
        root = self.root.expanduser().resolve()
        object.__setattr__(self, "root", root)
        if self.public_repo_root is not None:
            repo = self.public_repo_root.expanduser().resolve()
            object.__setattr__(self, "public_repo_root", repo)
            if root == repo or root.is_relative_to(repo):
                raise PublicRepositoryRootError(
                    "private raw-artifact root must be outside the public repository"
                )
        root.mkdir(parents=True, exist_ok=True)

    def persist(
        self,
        *,
        raw_bytes: bytes,
        source_id: str,
        source_version_id: str,
        content_type: str,
        acquired_at: str,
        available_at: str,
        source_locator: str,
        processing_disposition: str = ELIGIBLE_DISPOSITION,
    ) -> dict[str, Any]:
        if not isinstance(raw_bytes, bytes) or not raw_bytes:
            raise ValueError("raw_bytes must be non-empty bytes")
        _require_safe_id(source_id, "source_id")
        _require_safe_id(source_version_id, "source_version_id")
        _require_time(acquired_at, "acquired_at")
        _require_time(available_at, "available_at")
        if not isinstance(content_type, str) or not content_type.strip():
            raise ValueError("content_type must be a non-empty string")
        if not isinstance(source_locator, str) or not source_locator.strip():
            raise ValueError("source_locator must be a non-empty string")
        if processing_disposition not in ALLOWED_DISPOSITIONS:
            raise ValueError("processing_disposition is unsupported")

        artifact_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        artifact_relpath = Path(
            "objects", "sha256", artifact_sha256[:2], artifact_sha256[2:4], f"{artifact_sha256}.raw"
        )
        artifact_path = self.root / artifact_relpath
        _write_immutable_bytes(artifact_path, raw_bytes, expected_sha256=artifact_sha256)

        receipt: dict[str, Any] = {
            "schema_version": RECEIPT_SCHEMA,
            "source_id": source_id,
            "source_version_id": source_version_id,
            "artifact_sha256": artifact_sha256,
            "byte_length": len(raw_bytes),
            "content_type": content_type,
            "artifact_relpath": artifact_relpath.as_posix(),
            "source_locator": source_locator,
            "acquired_at": acquired_at,
            "available_at": available_at,
            "processing_disposition": processing_disposition,
            "immutable": True,
            "network_acquisition_performed_by_store": False,
            "public_repository_content_published": False,
        }
        receipt["receipt_sha256"] = _record_digest(receipt)

        receipt_relpath = Path("receipts", source_id, f"{source_version_id}.json")
        receipt_path = self.root / receipt_relpath
        encoded = _canonical_json(receipt)
        _write_immutable_bytes(
            receipt_path,
            encoded,
            expected_sha256=hashlib.sha256(encoded).hexdigest(),
        )
        return dict(receipt)

    def validate_receipt(self, receipt: Mapping[str, Any]) -> tuple[str, ...]:
        issues: list[str] = []
        required = {
            "schema_version", "source_id", "source_version_id", "artifact_sha256",
            "byte_length", "content_type", "artifact_relpath", "source_locator",
            "acquired_at", "available_at", "processing_disposition", "immutable",
            "network_acquisition_performed_by_store",
            "public_repository_content_published", "receipt_sha256",
        }
        if set(receipt) != required:
            issues.append("receipt_fields_invalid")
            return tuple(issues)
        if receipt.get("schema_version") != RECEIPT_SCHEMA:
            issues.append("receipt_schema_invalid")
        if not _is_safe_id(receipt.get("source_id")):
            issues.append("source_id_invalid")
        if not _is_safe_id(receipt.get("source_version_id")):
            issues.append("source_version_id_invalid")
        digest = receipt.get("artifact_sha256")
        if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
            issues.append("artifact_sha256_invalid")
        if not isinstance(receipt.get("byte_length"), int) or isinstance(receipt.get("byte_length"), bool) or receipt["byte_length"] <= 0:
            issues.append("byte_length_invalid")
        for field in ("content_type", "artifact_relpath", "source_locator"):
            if not isinstance(receipt.get(field), str) or not receipt[field]:
                issues.append(f"{field}_invalid")
        if not _is_zoned_time(receipt.get("acquired_at")):
            issues.append("acquired_at_invalid")
        if not _is_zoned_time(receipt.get("available_at")):
            issues.append("available_at_invalid")
        if receipt.get("processing_disposition") not in ALLOWED_DISPOSITIONS:
            issues.append("processing_disposition_invalid")
        if receipt.get("immutable") is not True:
            issues.append("immutable_flag_invalid")
        if receipt.get("network_acquisition_performed_by_store") is not False:
            issues.append("network_authority_escalation")
        if receipt.get("public_repository_content_published") is not False:
            issues.append("public_content_claim_invalid")
        if receipt.get("receipt_sha256") != _record_digest(receipt):
            issues.append("receipt_digest_invalid")
        if issues:
            return tuple(sorted(set(issues)))

        artifact_relpath = Path(str(receipt["artifact_relpath"]))
        if artifact_relpath.is_absolute() or ".." in artifact_relpath.parts:
            return ("artifact_relpath_unsafe",)
        artifact_path = (self.root / artifact_relpath).resolve()
        if not artifact_path.is_relative_to(self.root):
            return ("artifact_relpath_unsafe",)
        if not artifact_path.is_file():
            return ("artifact_missing",)
        raw = artifact_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != receipt["artifact_sha256"]:
            return ("artifact_digest_mismatch",)
        if len(raw) != receipt["byte_length"]:
            return ("artifact_length_mismatch",)
        return ()

    def write_release_manifest(
        self,
        *,
        release_id: str,
        created_at: str,
        receipts: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        manifest = build_release_manifest(
            release_id=release_id,
            created_at=created_at,
            receipts=receipts,
        )
        path = self.root / "releases" / f"{release_id}.json"
        encoded = _canonical_json(manifest)
        _write_immutable_bytes(path, encoded, expected_sha256=hashlib.sha256(encoded).hexdigest())
        return manifest


def build_release_manifest(
    *,
    release_id: str,
    created_at: str,
    receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    _require_safe_id(release_id, "release_id")
    _require_time(created_at, "created_at")
    if not receipts:
        raise ValueError("release must contain at least one receipt")
    members: list[dict[str, str]] = []
    seen_versions: set[str] = set()
    for receipt in receipts:
        source_version_id = receipt.get("source_version_id")
        source_id = receipt.get("source_id")
        artifact_sha256 = receipt.get("artifact_sha256")
        receipt_sha256 = receipt.get("receipt_sha256")
        if not _is_safe_id(source_version_id) or not _is_safe_id(source_id):
            raise ValueError("release receipt identity is invalid")
        if source_version_id in seen_versions:
            raise ValueError("source_version_id must be unique in a release")
        seen_versions.add(str(source_version_id))
        if not isinstance(artifact_sha256, str) or HEX64.fullmatch(artifact_sha256) is None:
            raise ValueError("release artifact digest is invalid")
        if not isinstance(receipt_sha256, str) or HEX64.fullmatch(receipt_sha256) is None:
            raise ValueError("release receipt digest is invalid")
        members.append({
            "source_id": str(source_id),
            "source_version_id": str(source_version_id),
            "artifact_sha256": artifact_sha256,
            "receipt_sha256": receipt_sha256,
        })
    members.sort(key=lambda item: (item["source_id"], item["source_version_id"]))
    manifest: dict[str, Any] = {
        "schema_version": RELEASE_SCHEMA,
        "release_id": release_id,
        "created_at": created_at,
        "members": members,
        "immutable": True,
    }
    manifest["release_sha256"] = _record_digest(manifest)
    return manifest


def validate_release_manifest(manifest: Mapping[str, Any]) -> tuple[str, ...]:
    required = {"schema_version", "release_id", "created_at", "members", "immutable", "release_sha256"}
    issues: list[str] = []
    if set(manifest) != required:
        return ("release_fields_invalid",)
    if manifest.get("schema_version") != RELEASE_SCHEMA:
        issues.append("release_schema_invalid")
    if not _is_safe_id(manifest.get("release_id")):
        issues.append("release_id_invalid")
    if not _is_zoned_time(manifest.get("created_at")):
        issues.append("release_created_at_invalid")
    if manifest.get("immutable") is not True:
        issues.append("release_immutable_flag_invalid")
    members = manifest.get("members")
    if not isinstance(members, list) or not members:
        issues.append("release_members_invalid")
    else:
        identities: set[tuple[str, str]] = set()
        for member in members:
            if not isinstance(member, Mapping):
                issues.append("release_member_invalid")
                continue
            if set(member) != {"source_id", "source_version_id", "artifact_sha256", "receipt_sha256"}:
                issues.append("release_member_fields_invalid")
                continue
            identity = (str(member.get("source_id", "")), str(member.get("source_version_id", "")))
            if identity in identities:
                issues.append("release_member_duplicate")
            identities.add(identity)
            if not _is_safe_id(member.get("source_id")) or not _is_safe_id(member.get("source_version_id")):
                issues.append("release_member_identity_invalid")
            for field in ("artifact_sha256", "receipt_sha256"):
                value = member.get(field)
                if not isinstance(value, str) or HEX64.fullmatch(value) is None:
                    issues.append("release_member_digest_invalid")
    if manifest.get("release_sha256") != _record_digest(manifest):
        issues.append("release_digest_invalid")
    return tuple(sorted(set(issues)))


def is_ordinary_t2_eligible(
    *,
    receipt: Mapping[str, Any],
    release_manifest: Mapping[str, Any],
    store: RawArtifactStore,
) -> bool:
    if store.validate_receipt(receipt):
        return False
    if validate_release_manifest(release_manifest):
        return False
    if receipt.get("processing_disposition") != ELIGIBLE_DISPOSITION:
        return False
    member = {
        "source_id": receipt.get("source_id"),
        "source_version_id": receipt.get("source_version_id"),
        "artifact_sha256": receipt.get("artifact_sha256"),
        "receipt_sha256": receipt.get("receipt_sha256"),
    }
    return member in release_manifest.get("members", [])


def _write_immutable_bytes(path: Path, payload: bytes, *, expected_sha256: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        if hashlib.sha256(existing).hexdigest() != expected_sha256 or existing != payload:
            raise ImmutableRecordError(f"immutable path already exists with different bytes: {path}")
        return
    fd, tmp_name = tempfile.mkstemp(prefix=".hydra-write-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        actual = hashlib.sha256(Path(tmp_name).read_bytes()).hexdigest()
        if actual != expected_sha256:
            raise ArtifactIntegrityError("temporary write digest mismatch")
        try:
            os.link(tmp_name, path)
        except FileExistsError:
            existing = path.read_bytes()
            if hashlib.sha256(existing).hexdigest() != expected_sha256 or existing != payload:
                raise ImmutableRecordError(f"immutable path raced with different bytes: {path}")
        finally:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _record_digest(record: Mapping[str, Any]) -> str:
    payload = {k: v for k, v in record.items() if k not in {"receipt_sha256", "release_sha256"}}
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _require_safe_id(value: Any, label: str) -> None:
    if not _is_safe_id(value):
        raise ValueError(f"{label} must contain only ASCII letters, digits, '.', '_' or '-'")


def _is_safe_id(value: Any) -> bool:
    return isinstance(value, str) and SAFE_ID.fullmatch(value) is not None


def _require_time(value: Any, label: str) -> None:
    if not _is_zoned_time(value):
        raise ValueError(f"{label} must be a timezone-aware ISO-8601 timestamp")


def _is_zoned_time(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None
