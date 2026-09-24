"""Strict JSON document handling and deterministic encoding."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .models import Issue


MAX_DOCUMENT_BYTES = 4 * 1024 * 1024


class DuplicateKeyError(ValueError):
    pass


@dataclass(frozen=True)
class JSONDocument:
    raw: bytes
    raw_sha256: str
    value: Mapping[str, Any] | None
    issues: tuple[Issue, ...]


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def coerce_document_bytes(value: bytes | bytearray | str | Mapping[str, Any] | None) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, Mapping):
        return canonical_json_bytes(deepcopy(dict(value)))
    raise TypeError(f"document must be bytes, text, mapping, or None; got {type(value).__name__}")


def parse_json_document(
    value: bytes | bytearray | str | Mapping[str, Any] | None,
    *,
    label: str,
    max_bytes: int = MAX_DOCUMENT_BYTES,
) -> JSONDocument:
    try:
        raw = coerce_document_bytes(value)
    except (TypeError, ValueError) as exc:
        raw = b""
        return JSONDocument(raw, sha256_hex(raw), None, (Issue("document_type_invalid", str(exc), label),))
    digest = sha256_hex(raw)
    if not raw:
        return JSONDocument(raw, digest, None, (Issue("document_missing", f"{label} is missing", label),))
    if len(raw) > max_bytes:
        return JSONDocument(
            raw,
            digest,
            None,
            (Issue("document_too_large", f"{label} exceeds {max_bytes} bytes", label, evidence={"size_bytes": len(raw)}),),
        )
    try:
        text = raw.decode("utf-8", errors="strict")
        parsed = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError, ValueError) as exc:
        return JSONDocument(raw, digest, None, (Issue("document_json_invalid", f"{label} is invalid JSON: {exc}", label),))
    if not isinstance(parsed, Mapping):
        return JSONDocument(raw, digest, None, (Issue("document_root_invalid", f"{label} root must be an object", label),))
    return JSONDocument(raw, digest, deepcopy(dict(parsed)), ())


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is prohibited")
