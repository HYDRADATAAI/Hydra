"""Strict JSON document handling and deterministic encoding."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from copy import deepcopy
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
    def __init__(self, size_bytes: int):
        self.size_bytes = size_bytes
        super().__init__("normalized document exceeds configured byte limit")


def _bounded_mapping_snapshot(value: Mapping[str, Any], *, max_bytes: int) -> tuple[dict[str, Any], int]:
    """Copy JSON-compatible mapping data within its canonical UTF-8 byte budget."""
    active: set[int] = set()
    total = 0
    nodes = 0

    def consume(size: int) -> None:
        nonlocal total
        if size < 0 or size > max_bytes - total:
            raise _DocumentTooLargeError(total + max(size, 0))
        total += size

    def string_size(text: str) -> int:
        # Callers pass exact str objects, so hostile subclass iteration cannot
        # undercount the value that json.dumps will later encode.
        remaining = max_bytes - total
        size = 2
        if size > remaining:
            raise _DocumentTooLargeError(total + size)
        length = str.__len__(text)
        if length > remaining - size:
            raise _DocumentTooLargeError(total + size + length)
        for index in range(length):
            char = str.__getitem__(text, index)
            codepoint = ord(char)
            if codepoint in (0x22, 0x5C):  # quote or backslash
                size += 2
            elif codepoint < 0x20:
                size += 2 if codepoint in (0x08, 0x09, 0x0A, 0x0C, 0x0D) else 6
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
            if size > remaining:
                raise _DocumentTooLargeError(total + size)
        return size

    def normalize_key(key: Any) -> Any:
        if isinstance(key, str):
            return key if type(key) is str else str.__str__(key)
        if key is None or key is True or key is False:
            return key
        if isinstance(key, int):
            return key if type(key) is int else int.__index__(key)
        if isinstance(key, float):
            return key if type(key) is float else float.__float__(key)
        raise TypeError("mapping keys must be JSON scalar types")

    def key_size(key: Any) -> int:
        if isinstance(key, str):
            return string_size(key)
        if key is None:
            return 6  # quoted "null"
        if key is True:
            return 6  # quoted "true"; check bool before integer
        if key is False:
            return 7  # quoted "false"; check bool before integer
        if isinstance(key, int):
            bit_length = int.bit_length(key)
            if bit_length > (max_bytes + 2) * 4:
                raise _DocumentTooLargeError(max_bytes + 1)
            integer = key if type(key) is int else int.__index__(key)
            return len(str(integer)) + 2
        if isinstance(key, float):
            number = key if type(key) is float else float.__float__(key)
            if not math.isfinite(number):
                raise ValueError("non-finite mapping key")
            return len(repr(number)) + 2
        raise TypeError("mapping keys must be JSON scalar types")

    def json_member_name(key: Any) -> str:
        if type(key) is str:
            return key
        if key is None:
            return "null"
        if key is True:
            return "true"
        if key is False:
            return "false"
        if type(key) is int:
            return str(key)
        if type(key) is float:
            if not math.isfinite(key):
                raise ValueError("non-finite mapping key")
            return repr(key)
        raise TypeError("mapping keys must be JSON scalar types")

    def copy_json(item: Any, depth: int = 1) -> Any:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_DOCUMENT_NODES or depth > MAX_DOCUMENT_DEPTH:
            raise _DocumentTooLargeError(max_bytes + 1)
        if item is None:
            consume(4)
            return None
        if item is True:
            consume(4)
            return True
        if item is False:
            consume(5)
            return False
        if isinstance(item, str):
            size = string_size(item)
            consume(size)
            return item if type(item) is str else str.__str__(item)
        if isinstance(item, int):
            bit_length = int.bit_length(item)
            if bit_length > (max_bytes + 2) * 4:
                raise _DocumentTooLargeError(max_bytes + 1)
            normalized = item if type(item) is int else int.__index__(item)
            consume(len(str(normalized)))
            return normalized
        if isinstance(item, float):
            normalized = item if type(item) is float else float.__float__(item)
            if not math.isfinite(normalized):
                raise ValueError("non-finite JSON number")
            consume(len(repr(normalized)))
            return normalized
        if isinstance(item, (list, tuple)):
            identity = id(item)
            if identity in active:
                raise ValueError("circular reference")
            active.add(identity)
            try:
                iterator = list.__iter__(item) if isinstance(item, list) else tuple.__iter__(item)
                consume(2)
                result = []
                first = True
                for child in iterator:
                    if not first:
                        consume(1)
                    result.append(copy_json(child, depth + 1))
                    first = False
                return result
            finally:
                active.remove(identity)
        if isinstance(item, dict):
            identity = id(item)
            if identity in active:
                raise ValueError("circular reference")
            active.add(identity)
            try:
                consume(2)
                result = {}
                seen_member_names: set[str] = set()
                first = True
                for original_key, child in dict.items(item):
                    if not first:
                        consume(1)
                    member_key_size = key_size(original_key)
                    consume(member_key_size + 1)
                    key = normalize_key(original_key)
                    member_name = json_member_name(key)
                    if member_name in seen_member_names or key in result:
                        raise ValueError("duplicate normalized mapping key")
                    result[key] = copy_json(child, depth + 1)
                    seen_member_names.add(member_name)
                    first = False
                return result
            finally:
                active.remove(identity)
        raise TypeError(f"unsupported JSON value type: {type(item).__name__}")

    identity = id(value)
    active.add(identity)
    try:
        consume(2)
        snapshot: dict[Any, Any] = {}
        seen_member_names: set[str] = set()
        first = True
        for original_key in value.keys():
            if not first:
                consume(1)
            member_key_size = key_size(original_key)
            consume(member_key_size + 1)
            key = normalize_key(original_key)
            member_name = json_member_name(key)
            if member_name in seen_member_names or key in snapshot:
                raise ValueError("duplicate normalized mapping key")
            snapshot[key] = copy_json(value[original_key], 2)
            seen_member_names.add(member_name)
            first = False
        return snapshot, total
    finally:
        active.remove(identity)


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _bounded_utf8_size(text: str, *, max_bytes: int) -> int:
    size = 0
    length = str.__len__(text)
    if length > max_bytes:
        raise _DocumentTooLargeError(length)
    for index in range(length):
        char = str.__getitem__(text, index)
        codepoint = ord(char)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise UnicodeEncodeError("utf-8", text, 0, 1, "surrogates not allowed")
        if codepoint < 0x80:
            size += 1
        elif codepoint < 0x800:
            size += 2
        elif codepoint < 0x10000:
            size += 3
        else:
            size += 4
        if size > max_bytes:
            raise _DocumentTooLargeError(size)
    return size


def coerce_document_bytes(
    value: bytes | bytearray | str | Mapping[str, Any] | None,
    *,
    max_bytes: int = MAX_DOCUMENT_BYTES,
) -> bytes:
    if value is None:
        return b""
    if type(value) is bytes:
        if len(value) > max_bytes:
            raise _DocumentTooLargeError(len(value))
        return value
    if type(value) is bytearray:
        if len(value) > max_bytes:
            raise _DocumentTooLargeError(len(value))
        return bytes(value)
    if isinstance(value, str):
        _bounded_utf8_size(value, max_bytes=max_bytes)
        text = value if type(value) is str else str.__str__(value)
        return text.encode("utf-8")
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
            (Issue("document_too_large", f"{label} exceeds {max_bytes} bytes", label, evidence={"size_bytes": exc.size_bytes}),),
        )
    except Exception:
        raw = b""
        return JSONDocument(
            raw,
            sha256_hex(raw),
            None,
            (Issue("document_type_invalid", f"{label} could not be safely converted to JSON", label),),
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
        normalized = deepcopy(dict(parsed))
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
