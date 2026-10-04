"""Strict JSON document handling and deterministic encoding."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .models import Issue


MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
MAX_DOCUMENT_DEPTH = 128
MAX_DOCUMENT_NODES = 100_000


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



class _DocumentTooLargeError(ValueError):
    def __init__(self, size_bytes: int | None, *, limit: str = "bytes"):
        self.size_bytes = size_bytes
        self.limit = limit
        super().__init__("normalized document exceeds configured limit")


def _bounded_mapping_snapshot(value: Mapping[str, Any], *, max_bytes: int) -> tuple[dict[str, Any], int]:
    """Copy JSON-compatible mapping data while measuring its canonical UTF-8 size."""
    active: set[int] = set()
    nodes = 0

    def plain_string(text: str) -> str:
        # Bypass overridden subclass iteration and comparison behavior.
        return text if type(text) is str else str.__str__(text)

    def plain_int(number: int) -> int:
        return number if type(number) is int else int.__index__(number)

    def plain_float(number: float) -> float:
        return number if type(number) is float else float.__float__(number)

    def plain_key(key: Any) -> Any:
        if isinstance(key, str):
            return plain_string(key)
        if key is True or key is False:
            return key
        if isinstance(key, int):
            return plain_int(key)
        if isinstance(key, float):
            return plain_float(key)
        return key

    def string_size(text: str) -> int:
        text = plain_string(text)
        size = 2  # JSON quotes
        for char in text:
            codepoint = ord(char)
            if char in ('"', "\\"):
                size += 2
            elif codepoint < 0x20:
                size += 2 if codepoint in (8, 9, 10, 12, 13) else 6
            elif codepoint < 0x80:
                size += 1
            elif codepoint < 0x800:
                size += 2
            elif 0xD800 <= codepoint <= 0xDFFF:
                raise UnicodeEncodeError("utf-8", text, 0, 1, "surrogates not allowed")
            elif codepoint < 0x10000:
                size += 3
            else:
                size += 4
            if size > max_bytes:
                raise _DocumentTooLargeError(size)
        return size

    def key_size(key: Any) -> int:
        if isinstance(key, str):
            return string_size(plain_string(key))
        if key is None:
            return 6  # "null"
        if key is True:
            return 6  # "true"
        if key is False:
            return 7  # "false"
        if isinstance(key, int):
            number = plain_int(key)
            # Avoid converting an enormous integer to decimal text.
            if number.bit_length() > (max_bytes + 2) * 4:
                raise _DocumentTooLargeError(max_bytes + 1)
            return len(json.dumps(number, allow_nan=False).encode("ascii")) + 2
        if isinstance(key, float):
            return len(json.dumps(plain_float(key), allow_nan=False).encode("ascii")) + 2
        raise TypeError("mapping keys must be JSON scalar types")

    def copy_json(item: Any, depth: int = 1) -> tuple[Any, int]:
        nonlocal nodes
        nodes += 1
        if nodes > min(max_bytes, MAX_DOCUMENT_NODES):
            raise _DocumentTooLargeError(None, limit="nodes")
        if depth > MAX_DOCUMENT_DEPTH:
            raise _DocumentTooLargeError(None, limit="depth")
        if item is None:
            return None, 4
        if item is True:
            return True, 4
        if item is False:
            return False, 5
        if isinstance(item, str):
            normalized = plain_string(item)
            return normalized, string_size(normalized)
        if isinstance(item, int):
            number = plain_int(item)
            if number.bit_length() > (max_bytes + 2) * 4:
                raise _DocumentTooLargeError(max_bytes + 1)
            encoded_size = len(json.dumps(number, allow_nan=False).encode("ascii"))
            return number, encoded_size
        if isinstance(item, float):
            number = plain_float(item)
            encoded_size = len(json.dumps(number, allow_nan=False).encode("ascii"))
            return number, encoded_size
        if isinstance(item, (list, tuple)):
            identity = id(item)
            if identity in active:
                raise ValueError("circular reference")
            active.add(identity)
            try:
                iterator = list.__iter__(item) if isinstance(item, list) else tuple.__iter__(item)
                result = []
                size = 2
                for child in iterator:
                    copied, child_size = copy_json(child, depth + 1)
                    if result:
                        size += 1
                    size += child_size
                    if size > max_bytes:
                        raise _DocumentTooLargeError(size)
                    result.append(copied)
                return result, size
            finally:
                active.remove(identity)
        if isinstance(item, dict):
            identity = id(item)
            if identity in active:
                raise ValueError("circular reference")
            active.add(identity)
            try:
                result = {}
                size = 2
                for key, child in dict.items(item):
                    normalized_key = plain_key(key)
                    child_key_size = key_size(normalized_key)
                    copied, child_size = copy_json(child, depth + 1)
                    if result:
                        size += 1
                    size += child_key_size + 1 + child_size
                    if size > max_bytes:
                        raise _DocumentTooLargeError(size)
                    result[normalized_key] = copied
                return result, size
            finally:
                active.remove(identity)
        raise TypeError(f"unsupported JSON value type: {type(item).__name__}")

    identity = id(value)
    active.add(identity)
    try:
        snapshot: dict[str, Any] = {}
        size = 2
        if size > max_bytes:
            raise _DocumentTooLargeError(size)
        for key in value.keys():
            value_for_key = value[key]
            normalized_key = plain_key(key)
            child_key_size = key_size(normalized_key)
            copied, child_size = copy_json(value_for_key, 2)
            if snapshot:
                size += 1
            size += child_key_size + 1 + child_size
            if size > max_bytes:
                raise _DocumentTooLargeError(size)
            snapshot[normalized_key] = copied
        return snapshot, size
    finally:
        active.remove(identity)


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def coerce_document_bytes(
    value: bytes | bytearray | str | Mapping[str, Any] | None,
    *,
    max_bytes: int = MAX_DOCUMENT_BYTES,
) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, Mapping):
        snapshot, _size = _bounded_mapping_snapshot(value, max_bytes=max_bytes)
        return canonical_json_bytes(snapshot)
    raise TypeError(f"document must be bytes, text, mapping, or None; got {type(value).__name__}")


def parse_json_document(
    value: bytes | bytearray | str | Mapping[str, Any] | None,
    *,
    label: str,
    max_bytes: int = MAX_DOCUMENT_BYTES,
) -> JSONDocument:
    if type(label) is not str:
        label = "$.document"
    try:
        raw = coerce_document_bytes(value, max_bytes=max_bytes)
    except _DocumentTooLargeError as exc:
        raw = b""
        return JSONDocument(
            raw,
            sha256_hex(raw),
            None,
            (
                Issue(
                    "document_too_large",
                    f"{label} exceeds {max_bytes} bytes" if exc.size_bytes is not None else f"{label} exceeds bounded normalization limits",
                    label,
                    evidence={"size_bytes": exc.size_bytes} if exc.size_bytes is not None else {"normalization_limit": exc.limit},
                ),
            ),
        )
    except Exception:
        raw = b""
        return JSONDocument(
            raw,
            sha256_hex(raw),
            None,
            (Issue("document_type_invalid", "document could not be safely normalized", label),),
        )
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
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError, ValueError, RecursionError) as exc:
        return JSONDocument(raw, digest, None, (Issue("document_json_invalid", f"{label} is invalid JSON: {exc}", label),))
    if not isinstance(parsed, Mapping):
        return JSONDocument(raw, digest, None, (Issue("document_root_invalid", f"{label} root must be an object", label),))
    if _document_depth_exceeds(parsed, max_depth=MAX_DOCUMENT_DEPTH):
        return JSONDocument(
            raw,
            digest,
            None,
            (Issue("document_too_deep", f"{label} exceeds maximum nesting depth {MAX_DOCUMENT_DEPTH}", label),),
        )
    try:
        normalized = dict(parsed)
    except RecursionError as exc:
        return JSONDocument(raw, digest, None, (Issue("document_json_invalid", f"{label} is too deeply nested: {exc}", label),))
    return JSONDocument(raw, digest, normalized, ())


def _document_depth_exceeds(value: Any, *, max_depth: int) -> bool:
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            return True
        if isinstance(current, Mapping):
            stack.extend((nested, depth + 1) for nested in current.values())
        elif isinstance(current, list):
            stack.extend((nested, depth + 1) for nested in current)
    return False


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is prohibited")
