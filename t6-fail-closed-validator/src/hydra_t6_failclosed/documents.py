"""Strict JSON document handling and deterministic encoding."""

from __future__ import annotations

import hashlib
import json
import math
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
    if isinstance(value, (bytes, bytearray)):
        view = memoryview(value)
        try:
            size = view.nbytes
            if size > max_bytes:
                raise _DocumentTooLargeError(size)
            return value if type(value) is bytes else view.tobytes()
        finally:
            view.release()
    if isinstance(value, str):
        _bounded_utf8_size(value, max_bytes=max_bytes)
        text = value if type(value) is str else str.__str__(value)
        return text.encode("utf-8")
    if isinstance(value, Mapping):
        snapshot, _size = _bounded_mapping_snapshot(value, max_bytes=max_bytes)
        return canonical_json_bytes(snapshot)
    raise TypeError(f"document must be bytes, text, mapping, or None; got {type(value).__name__}")




class _JSONPreflightLimitError(ValueError):
    def __init__(self, code: str, *, node_count: int | None = None):
        self.code = code
        self.node_count = node_count
        super().__init__(code)


class _JSONPreflightSyntaxError(ValueError):
    pass


def _preflight_json_limits(text: str) -> int:
    """Validate JSON structure and enforce limits before json.loads builds a tree.

    The root value is excluded, matching the root mapping contract. Every child
    object member value and array element counts as one node, including containers.
    This scanner deliberately does not decode or retain object keys; json.loads
    remains authoritative for duplicate-key detection and all value semantics.
    """
    position = 0
    nodes = 0
    length = len(text)

    def whitespace() -> None:
        nonlocal position
        while position < length and text[position] in " \t\n\r":
            position += 1

    def require(character: str) -> None:
        nonlocal position
        if position >= length or text[position] != character:
            raise _JSONPreflightSyntaxError("expected JSON delimiter")
        position += 1

    def scan_string() -> None:
        nonlocal position
        require('"')
        while position < length:
            character = text[position]
            position += 1
            codepoint = ord(character)
            if character == '"':
                return
            if codepoint < 0x20:
                raise _JSONPreflightSyntaxError("unescaped control character")
            if character == "\\":
                if position >= length:
                    raise _JSONPreflightSyntaxError("unfinished escape")
                escape = text[position]
                position += 1
                if escape in '"\\/bfnrt':
                    continue
                if escape != "u" or position + 4 > length:
                    raise _JSONPreflightSyntaxError("invalid escape")
                for _ in range(4):
                    if text[position] not in "0123456789abcdefABCDEF":
                        raise _JSONPreflightSyntaxError("invalid unicode escape")
                    position += 1
                continue
        raise _JSONPreflightSyntaxError("unterminated string")

    def scan_number() -> None:
        nonlocal position
        if position < length and text[position] == "-":
            position += 1
        if position >= length:
            raise _JSONPreflightSyntaxError("unfinished number")
        if text[position] == "0":
            position += 1
            if position < length and text[position].isdigit():
                raise _JSONPreflightSyntaxError("leading zero")
        elif "1" <= text[position] <= "9":
            while position < length and "0" <= text[position] <= "9":
                position += 1
        else:
            raise _JSONPreflightSyntaxError("invalid number")
        if position < length and text[position] == ".":
            position += 1
            start = position
            while position < length and "0" <= text[position] <= "9":
                position += 1
            if position == start:
                raise _JSONPreflightSyntaxError("fraction requires digits")
        if position < length and text[position] in "eE":
            position += 1
            if position < length and text[position] in "+-":
                position += 1
            start = position
            while position < length and "0" <= text[position] <= "9":
                position += 1
            if position == start:
                raise _JSONPreflightSyntaxError("exponent requires digits")

    def literal(token: str) -> None:
        nonlocal position
        end = position + len(token)
        if text[position:end] != token:
            raise _JSONPreflightSyntaxError("invalid literal")
        position = end

    def value(depth: int, *, count: bool) -> None:
        nonlocal nodes, position
        if depth > MAX_DOCUMENT_DEPTH:
            raise _JSONPreflightLimitError("document_too_deep")
        whitespace()
        if position >= length:
            raise _JSONPreflightSyntaxError("expected JSON value")
        if count:
            nodes += 1
            if nodes > MAX_DOCUMENT_NODES:
                raise _JSONPreflightLimitError(
                    "document_too_large", node_count=nodes
                )
        character = text[position]
        if character == "{":
            position += 1
            whitespace()
            if position < length and text[position] == "}":
                position += 1
                return
            while True:
                whitespace()
                scan_string()
                whitespace()
                require(":")
                value(depth + 1, count=True)
                whitespace()
                if position < length and text[position] == "}":
                    position += 1
                    return
                require(",")
        if character == "[":
            position += 1
            whitespace()
            if position < length and text[position] == "]":
                position += 1
                return
            while True:
                value(depth + 1, count=True)
                whitespace()
                if position < length and text[position] == "]":
                    position += 1
                    return
                require(",")
        if character == '"':
            scan_string()
            return
        if character == "t":
            literal("true")
            return
        if character == "f":
            literal("false")
            return
        if character == "n":
            literal("null")
            return
        scan_number()

    value(1, count=False)
    whitespace()
    if position != length:
        raise _JSONPreflightSyntaxError("trailing data")
    return nodes


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
        root_type = next((character for character in text if character not in " \t\n\r"), "")
        if root_type in "{[":
            try:
                _preflight_json_limits(text)
            except _JSONPreflightLimitError as exc:
                if root_type == "[":
                    return JSONDocument(
                        raw,
                        digest,
                        None,
                        (Issue("document_root_invalid", f"{label} root must be an object", label),),
                    )
                evidence = (
                    {"node_count": exc.node_count}
                    if exc.node_count is not None
                    else None
                )
                issue = Issue(
                    exc.code,
                    (
                        f"{label} exceeds maximum node count {MAX_DOCUMENT_NODES}"
                        if exc.code == "document_too_large"
                        else f"{label} exceeds maximum nesting depth {MAX_DOCUMENT_DEPTH}"
                    ),
                    label,
                    evidence=evidence or {},
                )
                return JSONDocument(raw, digest, None, (issue,))
            except _JSONPreflightSyntaxError:
                # Let json.loads report the canonical syntax error and preserve its
                # duplicate-key and parse_constant behavior for every non-overflow.
                pass
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
    node_count = _document_node_count(parsed, max_nodes=MAX_DOCUMENT_NODES)
    if node_count > MAX_DOCUMENT_NODES:
        return JSONDocument(
            raw,
            digest,
            None,
            (
                Issue(
                    "document_too_large",
                    f"{label} exceeds maximum node count {MAX_DOCUMENT_NODES}",
                    label,
                    evidence={"node_count": node_count},
                ),
            ),
        )
    try:
        normalized = dict(parsed)
    except RecursionError as exc:
        return JSONDocument(raw, digest, None, (Issue("document_json_invalid", f"{label} is too deeply nested: {exc}", label),))
    return JSONDocument(raw, digest, normalized, ())


def _document_depth_exceeds(value: Mapping[str, Any], *, max_depth: int) -> bool:
    """Check parsed depth without materializing sibling nodes on the stack."""
    stack = [(iter(value.values()), 2)]
    while stack:
        try:
            current = next(stack[-1][0])
        except StopIteration:
            stack.pop()
            continue
        depth = stack[-1][1]
        if depth > max_depth:
            return True
        if isinstance(current, Mapping):
            stack.append((iter(current.values()), depth + 1))
        elif isinstance(current, list):
            stack.append((iter(current), depth + 1))
    return False


def _document_node_count(value: Mapping[str, Any], *, max_nodes: int) -> int:
    """Count parsed values, excluding the root object, stopping at the limit."""
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
            return nodes
        if isinstance(current, Mapping):
            stack.append(iter(current.values()))
        elif isinstance(current, list):
            stack.append(iter(current))
    return nodes


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value!r} is prohibited")
