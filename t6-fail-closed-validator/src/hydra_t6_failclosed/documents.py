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



def _bounded_utf8_size(text: str, *, max_bytes: int) -> int:
    """Measure input text without allocating its encoded byte string."""
    size = 0
    for index in range(str.__len__(text)):
        codepoint = ord(str.__getitem__(text, index))
        if 0xD800 <= codepoint <= 0xDFFF:
            raise UnicodeEncodeError("utf-8", text, index, index + 1, "surrogates not allowed")
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

    def json_key_name(key: Any) -> str:
        if isinstance(key, str):
            return plain_string(key)
        if key is None:
            return "null"
        if key is True:
            return "true"
        if key is False:
            return "false"
        if isinstance(key, int):
            return json.dumps(plain_int(key), allow_nan=False)
        if isinstance(key, float):
            return json.dumps(plain_float(key), allow_nan=False)
        raise TypeError("mapping keys must be JSON scalar types")

    def string_size(text: str) -> int:
        size = 2  # JSON quotes
        if size > max_bytes:
            raise _DocumentTooLargeError(size)
        for index in range(str.__len__(text)):
            char = str.__getitem__(text, index)
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
                raise UnicodeEncodeError("utf-8", text, index, index + 1, "surrogates not allowed")
            elif codepoint < 0x10000:
                size += 3
            else:
                size += 4
            if size > max_bytes:
                raise _DocumentTooLargeError(size)
        return size

    def key_size(key: Any) -> int:
        if isinstance(key, str):
            return string_size(key)
        if key is None:
            return 6  # "null"
        if key is True:
            return 6  # "true"
        if key is False:
            return 7  # "false"
        if isinstance(key, int):
            # Read the base integer magnitude before making an exact-int copy.
            if int.bit_length(key) > (max_bytes + 2) * 4:
                raise _DocumentTooLargeError(max_bytes + 1)
            number = plain_int(key)
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
            encoded_size = string_size(item)
            return plain_string(item), encoded_size
        if isinstance(item, int):
            if int.bit_length(item) > (max_bytes + 2) * 4:
                raise _DocumentTooLargeError(max_bytes + 1)
            number = plain_int(item)
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
                seen_key_names: set[str] = set()
                size = 2
                for key, child in dict.items(item):
                    child_key_size = key_size(key)
                    normalized_key = plain_key(key)
                    key_name = json_key_name(normalized_key)
                    if key_name in seen_key_names or normalized_key in result:
                        raise DuplicateKeyError(f"duplicate normalized key {key_name!r}")
                    seen_key_names.add(key_name)
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
        seen_key_names: set[str] = set()
        size = 2
        if size > max_bytes:
            raise _DocumentTooLargeError(size)
        for key in value.keys():
            child_key_size = key_size(key)
            normalized_key = plain_key(key)
            key_name = json_key_name(normalized_key)
            if key_name in seen_key_names or normalized_key in snapshot:
                raise DuplicateKeyError(f"duplicate normalized key {key_name!r}")
            seen_key_names.add(key_name)
            value_for_key = value[key]
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
    if isinstance(value, (bytes, bytearray)):
        view = memoryview(value)
        raw_size = view.nbytes
        if raw_size > max_bytes:
            raise _DocumentTooLargeError(raw_size)
        if type(value) is bytes:
            return value
        return view.tobytes()
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
    if not raw:
        digest = sha256_hex(raw)
        return JSONDocument(raw, digest, None, (Issue("document_missing", f"{label} is missing", label),))
    raw_size = len(raw)
    if raw_size > max_bytes:
        raw = b""
        return JSONDocument(
            raw,
            sha256_hex(raw),
            None,
            (Issue("document_too_large", f"{label} exceeds {max_bytes} bytes", label, evidence={"size_bytes": raw_size}),),
        )
    digest = sha256_hex(raw)
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
    if _document_node_count_exceeds(parsed, max_nodes=MAX_DOCUMENT_NODES):
        return JSONDocument(
            raw,
            digest,
            None,
            (
                Issue(
                    "document_too_large",
                    f"{label} exceeds bounded normalization limits",
                    label,
                    evidence={"normalization_limit": "nodes"},
                ),
            ),
        )
    try:
        normalized = dict(parsed)
    except RecursionError as exc:
        return JSONDocument(raw, digest, None, (Issue("document_json_invalid", f"{label} is too deeply nested: {exc}", label),))
    return JSONDocument(raw, digest, normalized, ())


def _document_depth_exceeds(value: Any, *, max_depth: int) -> bool:
    """Check nesting depth with iterator-frame storage bounded by nesting depth."""
    stack = [(iter(value.values()), 1)] if isinstance(value, Mapping) else [(iter(value), 1)] if isinstance(value, list) else []
    while stack:
        try:
            current = next(stack[-1][0])
        except StopIteration:
            stack.pop()
            continue
        depth = stack[-1][1] + 1
        if depth > max_depth:
            return True
        if isinstance(current, Mapping):
            stack.append((iter(current.values()), depth))
        elif isinstance(current, list):
            stack.append((iter(current), depth))
    return False


def _document_node_count_exceeds(value: Mapping[str, Any], *, max_nodes: int) -> bool:
    """Count normalized mapping values with bounded iterator-frame storage."""
    stack = [iter(value.values())]
    nodes = 0
    while stack:
        try:
            current = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        nodes += 1
        if nodes > max_nodes:
            return True
        if isinstance(current, Mapping):
            stack.append(iter(current.values()))
        elif isinstance(current, list):
            stack.append(iter(current))
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
