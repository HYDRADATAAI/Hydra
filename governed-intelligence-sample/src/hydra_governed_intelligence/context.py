"""Integrity-checked evidence loading and policy-bound context decisions."""

from __future__ import annotations

import csv
import ctypes
import hashlib
import io
import json
import math
import os
import re
import stat
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

if os.name == "nt":
    import msvcrt
    from ctypes import wintypes

from .pipeline_replay import (
    PIPELINE_MANIFEST_SCHEMA,
    RESOLVED_ALIASES_SCHEMA,
    SOURCE_CSV_SCHEMA,
    ReplayContractError,
    replay_pipeline,
)


POLICY_SCHEMA = "hydra-governed-intelligence-policy/v1"
DECISION_SCHEMA = "hydra-governed-intelligence-decision/v1"
PIPELINE_RUN_SCHEMA = "hydra-market-pipeline-run/v1"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
TASK_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")
SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,15}$")
VENUE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,15}$")
PRICE_PATTERN = re.compile(r"^(?:0|[1-9]\d*)\.\d{6}$")
WINDOWS_DEVICE_PATTERN = re.compile(
    r"^(?:con|prn|aux|nul|clock\$|conin\$|conout\$|"
    r"(?:com|lpt)(?:[1-9]|\u00b9|\u00b2|\u00b3))$",
    re.IGNORECASE,
)
WINDOWS_FORBIDDEN_FILENAME_CHARS = frozenset('<>:"/\\|?*')
UTC_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"
)
MANIFEST_FIELDS = {
    "accepted_rows",
    "aliases_sha256",
    "inputs",
    "outputs",
    "pipeline_run_id",
    "quarantined_rows",
    "schema_version",
    "source_file_sha256",
    "source_rows",
    "transform_version",
}
INPUT_DESCRIPTORS = {
    "source_csv": (
        "source_snapshot.csv",
        SOURCE_CSV_SCHEMA,
    ),
    "resolved_aliases_json": (
        "resolved_symbol_aliases.json",
        RESOLVED_ALIASES_SCHEMA,
    ),
}
OUTPUT_FILENAMES = {
    "normalized_events_csv": "normalized_events.csv",
    "normalized_events_jsonl": "normalized_events.jsonl",
    "quarantine_records_jsonl": "quarantine_records.jsonl",
}
EVENT_FIELDS = {
    "currency",
    "event_id",
    "event_time_utc",
    "price",
    "raw_record_sha256",
    "source_file_sha256",
    "source_record_id",
    "source_row_number",
    "source_system",
    "symbol",
    "transform_version",
    "venue",
    "volume",
}
EVENT_STRING_FIELDS = {
    "currency",
    "event_id",
    "event_time_utc",
    "price",
    "raw_record_sha256",
    "source_file_sha256",
    "source_record_id",
    "source_system",
    "symbol",
    "transform_version",
    "venue",
}
NORMALIZED_CSV_COLUMNS = (
    "event_id",
    "source_system",
    "source_record_id",
    "symbol",
    "event_time_utc",
    "price",
    "volume",
    "currency",
    "venue",
    "source_file_sha256",
    "raw_record_sha256",
    "source_row_number",
    "transform_version",
)
NORMALIZED_EVENT_TRANSFORM_VERSION = "hydra-market-normalizer/v2"
ALLOWED_SOURCE_SYSTEMS = frozenset({"SYNTH_A", "SYNTH_B", "SYNTH_VENDOR"})
QUARANTINE_FIELDS = {
    "errors",
    "quarantine_id",
    "raw_record",
    "raw_record_sha256",
    "source_row_number",
    "stage",
    "validation_messages",
}
RAW_RECORD_FIELDS = {
    "currency",
    "event_time",
    "price",
    "source_record_id",
    "source_system",
    "symbol",
    "venue",
    "volume",
}
QUARANTINE_ERROR_MESSAGES = {
    "currency_invalid": "currency must be exactly three alphabetic characters",
    "duplicate_normalized_event": (
        "normalized symbol, UTC timestamp, and venue already appeared earlier in the file"
    ),
    "event_time_invalid": "event_time must be a valid ISO-8601 timestamp",
    "event_time_missing": "event_time is required",
    "event_time_timezone_missing": "event_time must include a timezone offset",
    "price_invalid": "price must be a decimal value",
    "price_missing": "price is required",
    "price_non_finite": "price must be finite",
    "price_non_positive": "price must be greater than zero",
    "price_scale_exceeds_6": "price may not have more than six fractional digits",
    "row_extra_values": "row contains values beyond the required CSV columns",
    "source_record_id_missing": "source_record_id is required",
    "source_system_invalid": (
        "source_system is not in the allowed public synthetic source list"
    ),
    "source_system_missing": "source_system is required",
    "symbol_invalid": "symbol must normalize to an allowed uppercase market symbol",
    "symbol_missing": "symbol is required",
    "venue_invalid": "venue must be a non-empty uppercase venue identifier",
    "volume_invalid": "volume must be an integer",
    "volume_missing": "volume is required",
    "volume_negative": "volume must be greater than or equal to zero",
}
IMMUTABLE_MAPPING_TYPE = type(MappingProxyType({}))
_OPEN_SUPPORTS_DIR_FD = os.open in os.supports_dir_fd
_STAT_SUPPORTS_DIR_FD = os.stat in os.supports_dir_fd
_STAT_SUPPORTS_NOFOLLOW = os.stat in os.supports_follow_symlinks


class ContractError(ValueError):
    """Raised when a request, policy, or document violates its contract."""


class IntegrityError(ValueError):
    """Raised when an artifact no longer matches its pinned digest or counts."""


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def _absolute_path(path: str | Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _stable_regular_file_bytes(
    handle: io.BufferedReader,
    label: str,
) -> tuple[bytes, os.stat_result, os.stat_result]:
    before = os.fstat(handle.fileno())
    if not stat.S_ISREG(before.st_mode):
        raise IntegrityError(f"{label}: opened descriptor is not a regular file")
    payload = handle.read()
    after = os.fstat(handle.fileno())
    if not stat.S_ISREG(after.st_mode) or not os.path.samestat(before, after):
        raise IntegrityError(f"{label}: file identity changed while reading")
    if not (
        before.st_size == after.st_size == len(payload)
        and before.st_mtime_ns == after.st_mtime_ns
    ):
        raise IntegrityError(f"{label}: file metadata changed while reading")
    return payload, before, after


def _snapshot_regular_file_posix(path: Path, root: Path, label: str) -> bytes:
    required_flags = ("O_DIRECTORY", "O_NOFOLLOW")
    if any(not hasattr(os, name) for name in required_flags):
        raise IntegrityError(
            f"{label}: platform cannot provide descriptor-relative no-follow opens"
        )
    if not (_OPEN_SUPPORTS_DIR_FD and _STAT_SUPPORTS_DIR_FD):
        raise IntegrityError(
            f"{label}: platform cannot provide descriptor-relative traversal"
        )
    if not _STAT_SUPPORTS_NOFOLLOW:
        raise IntegrityError(f"{label}: platform cannot inspect a leaf without following")

    directory_flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    leaf_flags = (
        os.O_RDONLY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    root_descriptor: int | None = None
    leaf_descriptor: int | None = None
    try:
        parts = root.parts
        if not root.anchor or not parts:
            raise IntegrityError(f"{label}: evidence root is not absolute")
        root_descriptor = os.open(root.anchor, directory_flags)
        for component in parts[1:]:
            next_descriptor = os.open(
                component,
                directory_flags,
                dir_fd=root_descriptor,
            )
            opened = os.fstat(next_descriptor)
            if not stat.S_ISDIR(opened.st_mode):
                os.close(next_descriptor)
                raise IntegrityError(f"{label}: root component is not a directory")
            os.close(root_descriptor)
            root_descriptor = next_descriptor

        root_before = os.fstat(root_descriptor)
        if not stat.S_ISDIR(root_before.st_mode):
            raise IntegrityError(f"{label}: evidence root is not a directory")
        leaf_before = os.stat(
            path.name,
            dir_fd=root_descriptor,
            follow_symlinks=False,
        )
        if _is_link_or_reparse(leaf_before) or not stat.S_ISREG(leaf_before.st_mode):
            raise IntegrityError(f"{label}: missing regular no-follow file")

        leaf_descriptor = os.open(
            path.name,
            leaf_flags,
            dir_fd=root_descriptor,
        )
        with os.fdopen(leaf_descriptor, "rb") as handle:
            leaf_descriptor = None
            descriptor_before = os.fstat(handle.fileno())
            if not os.path.samestat(leaf_before, descriptor_before):
                raise IntegrityError(f"{label}: file identity changed while opening")
            payload, _, descriptor_after = _stable_regular_file_bytes(handle, label)
            leaf_after = os.stat(
                path.name,
                dir_fd=root_descriptor,
                follow_symlinks=False,
            )
            if (
                _is_link_or_reparse(leaf_after)
                or not stat.S_ISREG(leaf_after.st_mode)
                or not os.path.samestat(descriptor_after, leaf_after)
            ):
                raise IntegrityError(f"{label}: file identity changed while reading")

        root_after = os.fstat(root_descriptor)
        if not (
            stat.S_ISDIR(root_after.st_mode)
            and os.path.samestat(root_before, root_after)
        ):
            raise IntegrityError(f"{label}: root identity changed while reading")
        return payload
    except IntegrityError:
        raise
    except OSError as exc:
        raise IntegrityError(f"{label}: unable to snapshot file: {exc}") from exc
    finally:
        for descriptor in (leaf_descriptor, root_descriptor):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


if os.name == "nt":
    _WINDOWS_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _WINDOWS_FILE_READ_ATTRIBUTES = 0x00000080
    _WINDOWS_GENERIC_READ = 0x80000000
    _WINDOWS_FILE_SHARE_READ = 0x00000001
    _WINDOWS_FILE_SHARE_WRITE = 0x00000002
    _WINDOWS_OPEN_EXISTING = 3
    _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _WINDOWS_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _WINDOWS_FILE_TYPE_DISK = 0x0001
    _WINDOWS_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class _WindowsFileInformation(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]

    class _WindowsUnicodeString(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.USHORT),
            ("MaximumLength", wintypes.USHORT),
            ("Buffer", wintypes.LPWSTR),
        ]

    class _WindowsObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.ULONG),
            ("RootDirectory", wintypes.HANDLE),
            ("ObjectName", ctypes.POINTER(_WindowsUnicodeString)),
            ("Attributes", wintypes.ULONG),
            ("SecurityDescriptor", wintypes.LPVOID),
            ("SecurityQualityOfService", wintypes.LPVOID),
        ]

    class _WindowsIoStatusBlock(ctypes.Structure):
        _fields_ = [
            ("StatusOrPointer", ctypes.c_void_p),
            ("Information", ctypes.c_size_t),
        ]

    _WINDOWS_KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _WINDOWS_CREATE_FILE = _WINDOWS_KERNEL32.CreateFileW
    _WINDOWS_CREATE_FILE.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _WINDOWS_CREATE_FILE.restype = wintypes.HANDLE
    _WINDOWS_CLOSE_HANDLE = _WINDOWS_KERNEL32.CloseHandle
    _WINDOWS_CLOSE_HANDLE.argtypes = [wintypes.HANDLE]
    _WINDOWS_CLOSE_HANDLE.restype = wintypes.BOOL
    _WINDOWS_GET_FILE_INFORMATION = _WINDOWS_KERNEL32.GetFileInformationByHandle
    _WINDOWS_GET_FILE_INFORMATION.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_WindowsFileInformation),
    ]
    _WINDOWS_GET_FILE_INFORMATION.restype = wintypes.BOOL
    _WINDOWS_GET_FILE_TYPE = _WINDOWS_KERNEL32.GetFileType
    _WINDOWS_GET_FILE_TYPE.argtypes = [wintypes.HANDLE]
    _WINDOWS_GET_FILE_TYPE.restype = wintypes.DWORD
    _WINDOWS_GET_FINAL_PATH = _WINDOWS_KERNEL32.GetFinalPathNameByHandleW
    _WINDOWS_GET_FINAL_PATH.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    _WINDOWS_GET_FINAL_PATH.restype = wintypes.DWORD
    _WINDOWS_NTDLL = ctypes.WinDLL("ntdll", use_last_error=True)
    _WINDOWS_NT_CREATE_FILE = _WINDOWS_NTDLL.NtCreateFile
    _WINDOWS_NT_CREATE_FILE.argtypes = [
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.ULONG,
        ctypes.POINTER(_WindowsObjectAttributes),
        ctypes.POINTER(_WindowsIoStatusBlock),
        ctypes.c_void_p,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        ctypes.c_void_p,
        wintypes.ULONG,
    ]
    _WINDOWS_NT_CREATE_FILE.restype = wintypes.LONG
    _WINDOWS_NT_STATUS_TO_DOS_ERROR = _WINDOWS_NTDLL.RtlNtStatusToDosError
    _WINDOWS_NT_STATUS_TO_DOS_ERROR.argtypes = [wintypes.LONG]
    _WINDOWS_NT_STATUS_TO_DOS_ERROR.restype = wintypes.ULONG


def _windows_api_path(path: Path) -> str:
    value = os.fspath(path)
    if value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    return "\\\\?\\" + value


def _windows_normalized_path(value: str | Path) -> str:
    text = os.fspath(value)
    if text.startswith("\\\\?\\UNC\\"):
        text = "\\\\" + text[8:]
    elif text.startswith("\\\\?\\"):
        text = text[4:]
    return os.path.normcase(os.path.normpath(text))


def _windows_open_handle(path: Path, *, directory: bool) -> int:
    if os.name != "nt":
        raise OSError("Windows handle APIs are unavailable")
    desired_access = _WINDOWS_FILE_READ_ATTRIBUTES
    if directory:
        desired_access |= 0x00000020
    else:
        desired_access |= _WINDOWS_GENERIC_READ
    share_mode = _WINDOWS_FILE_SHARE_READ
    if directory:
        share_mode |= _WINDOWS_FILE_SHARE_WRITE
    flags = _WINDOWS_FILE_FLAG_OPEN_REPARSE_POINT
    if directory:
        flags |= _WINDOWS_FILE_FLAG_BACKUP_SEMANTICS
    handle = _WINDOWS_CREATE_FILE(
        _windows_api_path(path),
        desired_access,
        share_mode,
        None,
        _WINDOWS_OPEN_EXISTING,
        flags,
        None,
    )
    if handle == _WINDOWS_INVALID_HANDLE_VALUE:
        error = ctypes.get_last_error()
        raise OSError(error, ctypes.FormatError(error), os.fspath(path))
    return int(handle)


def _windows_open_relative_leaf(root_handle: int, name: str) -> int:
    if os.name != "nt":
        raise OSError("Windows handle APIs are unavailable")
    name_buffer = ctypes.create_unicode_buffer(name)
    name_bytes = name.encode("utf-16-le")
    unicode_name = _WindowsUnicodeString(
        len(name_bytes),
        len(name_bytes) + 2,
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    object_attributes = _WindowsObjectAttributes(
        ctypes.sizeof(_WindowsObjectAttributes),
        wintypes.HANDLE(root_handle),
        ctypes.pointer(unicode_name),
        0x00000040,
        None,
        None,
    )
    io_status = _WindowsIoStatusBlock()
    handle = wintypes.HANDLE()
    status = _WINDOWS_NT_CREATE_FILE(
        ctypes.byref(handle),
        _WINDOWS_GENERIC_READ | 0x00100000,
        ctypes.byref(object_attributes),
        ctypes.byref(io_status),
        None,
        0,
        _WINDOWS_FILE_SHARE_READ,
        0x00000001,
        0x00000020 | 0x00000040 | 0x00200000,
        None,
        0,
    )
    if status < 0:
        error = int(_WINDOWS_NT_STATUS_TO_DOS_ERROR(status))
        raise OSError(error, ctypes.FormatError(error), name)
    return int(handle.value)


def _windows_close_handle(handle: int) -> None:
    if os.name == "nt":
        _WINDOWS_CLOSE_HANDLE(wintypes.HANDLE(handle))


def _windows_handle_information(handle: int) -> tuple[int, int, int]:
    if os.name != "nt":
        raise OSError("Windows handle APIs are unavailable")
    information = _WindowsFileInformation()
    if not _WINDOWS_GET_FILE_INFORMATION(
        wintypes.HANDLE(handle),
        ctypes.byref(information),
    ):
        error = ctypes.get_last_error()
        raise OSError(error, ctypes.FormatError(error))
    file_index = (information.nFileIndexHigh << 32) | information.nFileIndexLow
    return (
        information.dwFileAttributes,
        information.dwVolumeSerialNumber,
        file_index,
    )


def _windows_final_path(handle: int) -> str:
    if os.name != "nt":
        raise OSError("Windows handle APIs are unavailable")
    required = _WINDOWS_GET_FINAL_PATH(wintypes.HANDLE(handle), None, 0, 0)
    if required == 0:
        error = ctypes.get_last_error()
        raise OSError(error, ctypes.FormatError(error))
    buffer = ctypes.create_unicode_buffer(required + 1)
    written = _WINDOWS_GET_FINAL_PATH(
        wintypes.HANDLE(handle),
        buffer,
        len(buffer),
        0,
    )
    if written == 0 or written >= len(buffer):
        error = ctypes.get_last_error()
        raise OSError(error, ctypes.FormatError(error))
    return _windows_normalized_path(buffer.value)


def _snapshot_regular_file_windows(path: Path, root: Path, label: str) -> bytes:
    root_handle: int | None = None
    leaf_handle: int | None = None
    descriptor: int | None = None
    try:
        root_handle = _windows_open_handle(root, directory=True)
        root_information = _windows_handle_information(root_handle)
        if root_information[0] & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT:
            raise IntegrityError(f"{label}: evidence root is a reparse point")
        if not root_information[0] & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY:
            raise IntegrityError(f"{label}: evidence root is not a directory")
        if _WINDOWS_GET_FILE_TYPE(wintypes.HANDLE(root_handle)) != _WINDOWS_FILE_TYPE_DISK:
            raise IntegrityError(f"{label}: evidence root is not a disk directory")

        root_final_path = _windows_final_path(root_handle)
        if root_final_path != _windows_normalized_path(root):
            raise IntegrityError(
                f"{label}: evidence root resolves through a reparse point or alias"
            )

        leaf_handle = _windows_open_relative_leaf(root_handle, path.name)
        leaf_information = _windows_handle_information(leaf_handle)
        if leaf_information[0] & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT:
            raise IntegrityError(f"{label}: evidence leaf is a reparse point")
        if leaf_information[0] & _WINDOWS_FILE_ATTRIBUTE_DIRECTORY:
            raise IntegrityError(f"{label}: missing regular file")
        if _WINDOWS_GET_FILE_TYPE(wintypes.HANDLE(leaf_handle)) != _WINDOWS_FILE_TYPE_DISK:
            raise IntegrityError(f"{label}: evidence leaf is not a disk file")

        leaf_final_path = _windows_final_path(leaf_handle)
        if (
            leaf_information[1] != root_information[1]
            or os.path.dirname(leaf_final_path) != root_final_path
        ):
            raise IntegrityError(
                f"{label}: opened file is not physically contained by the evidence root"
            )

        descriptor = msvcrt.open_osfhandle(
            leaf_handle,
            os.O_RDONLY | getattr(os, "O_BINARY", 0),
        )
        leaf_handle = None
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            payload, _, _ = _stable_regular_file_bytes(handle, label)
            os_handle = msvcrt.get_osfhandle(handle.fileno())
            leaf_after = _windows_handle_information(os_handle)
            leaf_path_after = _windows_final_path(os_handle)
            if leaf_after != leaf_information or leaf_path_after != leaf_final_path:
                raise IntegrityError(f"{label}: file identity changed while reading")

        root_after = _windows_handle_information(root_handle)
        if (
            root_after != root_information
            or _windows_final_path(root_handle) != root_final_path
        ):
            raise IntegrityError(f"{label}: root identity changed while reading")
        return payload
    except IntegrityError:
        raise
    except OSError as exc:
        raise IntegrityError(f"{label}: unable to snapshot file: {exc}") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if leaf_handle is not None:
            _windows_close_handle(leaf_handle)
        if root_handle is not None:
            _windows_close_handle(root_handle)


def _snapshot_regular_file(path: Path, root: Path, label: str) -> bytes:
    """Capture stable bytes from one direct child of a pinned evidence root."""

    intended_root = _absolute_path(root)
    intended_path = _absolute_path(path)
    if intended_path.parent != intended_root:
        raise IntegrityError(f"{label}: path escapes the evidence root")
    if os.name == "nt":
        return _snapshot_regular_file_windows(intended_path, intended_root, label)
    return _snapshot_regular_file_posix(intended_path, intended_root, label)


def _is_safe_manifest_filename(filename: Any) -> bool:
    if type(filename) is not str or not filename or filename in {".", ".."}:
        return False
    if filename != filename.strip() or filename.endswith((".", " ")):
        return False
    if any(
        ord(character) < 32
        or 127 <= ord(character) <= 159
        or character in WINDOWS_FORBIDDEN_FILENAME_CHARS
        for character in filename
    ):
        return False

    device_stem = filename.split(".", 1)[0].rstrip(" .")
    return WINDOWS_DEVICE_PATTERN.fullmatch(device_stem) is None


@dataclass(frozen=True)
class Policy:
    allowed_tasks: tuple[str, ...]
    abstained_tasks: tuple[str, ...]
    refused_tasks: tuple[str, ...]
    max_context_records: int
    sha256: str
    _source_bytes: bytes = field(repr=False, compare=False)


@dataclass(frozen=True)
class Evidence:
    directory: Path
    manifest: Mapping[str, Any]
    manifest_sha256: str
    accepted_events: tuple[Mapping[str, Any], ...]
    normalized_filename: str
    normalized_sha256: str
    quarantine_sha256: str
    _manifest_bytes: bytes = field(repr=False, compare=False)
    _output_snapshots: tuple[tuple[str, bytes], ...] = field(
        repr=False, compare=False
    )
    _input_snapshots: tuple[tuple[str, bytes], ...] = field(
        repr=False, compare=False
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _json_value(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def load_json_document(path: Path) -> Any:
    document, _ = load_json_document_with_bytes(path)
    return document


def load_json_document_with_bytes(path: Path) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ContractError(f"invalid JSON document {path}: {exc}") from exc
    return _load_json_bytes(raw, path), raw


def _load_json_bytes(raw: bytes, path: Path) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError, ContractError) as exc:
        raise ContractError(f"invalid JSON document {path}: {exc}") from exc


def load_policy(path: str | Path) -> Policy:
    policy_path = Path(path)
    document, policy_bytes = load_json_document_with_bytes(policy_path)
    return _policy_from_document(document, policy_bytes)


def _policy_from_document(document: Any, policy_bytes: bytes) -> Policy:
    if not isinstance(document, dict):
        raise ContractError("policy root must be an object")

    expected_fields = {
        "schema_version",
        "allowed_tasks",
        "abstained_tasks",
        "refused_tasks",
        "max_context_records",
        "model_execution_enabled",
    }
    if set(document) != expected_fields:
        raise ContractError("policy fields do not match the v1 contract")
    if document["schema_version"] != POLICY_SCHEMA:
        raise ContractError("unsupported policy schema")
    if document["model_execution_enabled"] is not False:
        raise ContractError("this sample prohibits model execution")
    if not isinstance(document["max_context_records"], int) or isinstance(
        document["max_context_records"], bool
    ):
        raise ContractError("max_context_records must be an integer")
    if not 1 <= document["max_context_records"] <= 20:
        raise ContractError("max_context_records must be between 1 and 20")

    task_groups = {}
    for field in ("allowed_tasks", "abstained_tasks", "refused_tasks"):
        values = document[field]
        if not isinstance(values, list) or not values:
            raise ContractError(f"{field} must be a non-empty list")
        if any(not isinstance(value, str) or not TASK_PATTERN.fullmatch(value) for value in values):
            raise ContractError(f"{field} contains an invalid task name")
        if values != sorted(set(values)):
            raise ContractError(f"{field} must be sorted and unique")
        task_groups[field] = tuple(values)

    combined = [value for values in task_groups.values() for value in values]
    if len(combined) != len(set(combined)):
        raise ContractError("policy task groups must be disjoint")
    if set(task_groups["allowed_tasks"]) != {
        "accepted_observation_summary",
        "quality_status",
    }:
        raise ContractError("v1 allowed task set changed")

    return Policy(
        allowed_tasks=task_groups["allowed_tasks"],
        abstained_tasks=task_groups["abstained_tasks"],
        refused_tasks=task_groups["refused_tasks"],
        max_context_records=document["max_context_records"],
        sha256=sha256_hex(policy_bytes),
        _source_bytes=policy_bytes,
    )


def _validate_policy_binding(policy: Policy) -> None:
    if type(policy) is not Policy or type(policy._source_bytes) is not bytes:
        raise IntegrityError("policy semantic binding is invalid")
    if (
        type(policy.allowed_tasks) is not tuple
        or type(policy.abstained_tasks) is not tuple
        or type(policy.refused_tasks) is not tuple
        or any(
            type(task) is not str
            for group in (
                policy.allowed_tasks,
                policy.abstained_tasks,
                policy.refused_tasks,
            )
            for task in group
        )
        or type(policy.max_context_records) is not int
        or type(policy.sha256) is not str
    ):
        raise IntegrityError("policy semantic binding is invalid")
    try:
        document = _load_json_bytes(policy._source_bytes, Path("<policy snapshot>"))
        expected = _policy_from_document(document, policy._source_bytes)
        actual_binding = canonical_json_bytes(_policy_semantic_document(policy))
        expected_binding = canonical_json_bytes(_policy_semantic_document(expected))
    except (ContractError, TypeError, ValueError) as exc:
        raise IntegrityError(f"policy semantic binding is invalid: {exc}") from exc
    if actual_binding != expected_binding:
        raise IntegrityError("policy semantic binding is invalid")


def _policy_semantic_document(policy: Policy) -> dict[str, Any]:
    return {
        "abstained_tasks": list(policy.abstained_tasks),
        "allowed_tasks": list(policy.allowed_tasks),
        "max_context_records": policy.max_context_records,
        "refused_tasks": list(policy.refused_tasks),
        "sha256": policy.sha256,
    }


def load_evidence(directory: str | Path) -> Evidence:
    root = _absolute_path(directory)
    manifest_path = root / "manifest.json"
    manifest_bytes = _snapshot_regular_file(
        manifest_path,
        root,
        "pipeline manifest",
    )
    manifest = _load_json_bytes(manifest_bytes, manifest_path)
    _, resolved_outputs, _, resolved_inputs = _validated_manifest_artifacts(
        manifest, root
    )

    output_bytes: dict[str, bytes] = {}
    for key, path in resolved_outputs.items():
        output_bytes[key] = _snapshot_regular_file(
            path,
            root,
            f"manifest output {key}",
        )

    input_bytes: dict[str, bytes] = {}
    for key, path in resolved_inputs.items():
        input_bytes[key] = _snapshot_regular_file(
            path,
            root,
            f"manifest input {key}",
        )

    return _evidence_from_snapshots(
        root,
        manifest,
        manifest_bytes,
        output_bytes,
        resolved_outputs,
        input_bytes,
        resolved_inputs,
    )


def _validated_manifest_artifacts(
    manifest: Any, root: Path
) -> tuple[
    dict[str, Any],
    dict[str, Path],
    dict[str, Any],
    dict[str, Path],
]:
    if type(manifest) is not dict:
        raise ContractError("pipeline manifest root must be an object")
    if manifest.get("schema_version") == "hydra-market-pipeline-manifest/v1":
        raise ContractError(
            "pipeline manifest v1 is non-replayable; v2 input snapshots are required"
        )
    if set(manifest) != MANIFEST_FIELDS:
        raise ContractError("pipeline manifest fields do not match the v2 contract")
    if manifest["schema_version"] != PIPELINE_MANIFEST_SCHEMA:
        raise ContractError("unsupported pipeline manifest schema")
    if manifest["transform_version"] != NORMALIZED_EVENT_TRANSFORM_VERSION:
        raise ContractError("pipeline transform_version is invalid")

    for field in (
        "aliases_sha256",
        "pipeline_run_id",
        "source_file_sha256",
    ):
        value = manifest[field]
        if type(value) is not str or not SHA256_PATTERN.fullmatch(value):
            raise ContractError(f"pipeline {field} is invalid")
    for field in ("accepted_rows", "quarantined_rows", "source_rows"):
        value = manifest[field]
        if type(value) is not int or value < 0:
            raise ContractError(f"pipeline {field} must be a non-negative integer")
    if manifest["source_rows"] != (
        manifest["accepted_rows"] + manifest["quarantined_rows"]
    ):
        raise IntegrityError("pipeline row counts do not sum to source_rows")

    expected_run_id = sha256_hex(
        canonical_json_bytes(
            {
                "aliases_sha256": manifest["aliases_sha256"],
                "run_schema": PIPELINE_RUN_SCHEMA,
                "source_file_sha256": manifest["source_file_sha256"],
                "transform_version": manifest["transform_version"],
            }
        )
    )
    if manifest["pipeline_run_id"] != expected_run_id:
        raise IntegrityError("pipeline_run_id does not match the manifest inputs")

    outputs = manifest["outputs"]
    if type(outputs) is not dict or set(outputs) != set(OUTPUT_FILENAMES):
        raise ContractError("pipeline manifest output set changed")

    inputs = manifest["inputs"]
    if type(inputs) is not dict or set(inputs) != set(INPUT_DESCRIPTORS):
        raise ContractError("pipeline manifest input set changed")

    resolved_inputs: dict[str, Path] = {}
    seen_filenames: set[str] = set()
    for key, (expected_filename, expected_schema) in INPUT_DESCRIPTORS.items():
        descriptor = inputs[key]
        if type(descriptor) is not dict or set(descriptor) != {
            "file",
            "schema_version",
            "sha256",
        }:
            raise ContractError(
                f"manifest input {key} fields do not match the v2 contract"
            )
        filename = descriptor["file"]
        digest = descriptor["sha256"]
        if filename != expected_filename or not _is_safe_manifest_filename(filename):
            raise ContractError(f"manifest input {key} has an invalid file name")
        if descriptor["schema_version"] != expected_schema:
            raise ContractError(f"manifest input {key} has an invalid schema")
        if type(digest) is not str or not SHA256_PATTERN.fullmatch(digest):
            raise ContractError(f"manifest input {key} has an invalid digest")
        seen_filenames.add(filename.casefold())
        path = root / filename
        if path.parent != root:
            raise ContractError(f"manifest input {key} escapes the artifact directory")
        resolved_inputs[key] = path

    if inputs["source_csv"]["sha256"] != manifest["source_file_sha256"]:
        raise IntegrityError("source snapshot digest does not match the manifest")
    if inputs["resolved_aliases_json"]["sha256"] != manifest["aliases_sha256"]:
        raise IntegrityError("resolved aliases digest does not match the manifest")

    resolved_outputs: dict[str, Path] = {}
    for key, descriptor in outputs.items():
        if type(descriptor) is not dict:
            raise ContractError(f"manifest output {key} must be an object")
        expected_fields = {"file", "sha256"}
        if key == "normalized_events_csv":
            expected_fields.add("schema")
        if set(descriptor) != expected_fields:
            raise ContractError(
                f"manifest output {key} fields do not match the v1 contract"
            )
        filename = descriptor["file"]
        digest = descriptor["sha256"]
        if (
            filename != OUTPUT_FILENAMES[key]
            or not _is_safe_manifest_filename(filename)
            or filename.casefold() in seen_filenames
        ):
            raise ContractError(f"manifest output {key} has an invalid v2 file name")
        seen_filenames.add(filename.casefold())
        if type(digest) is not str or not SHA256_PATTERN.fullmatch(digest):
            raise ContractError(f"manifest output {key} has an invalid digest")
        if key == "normalized_events_csv" and descriptor["schema"] != list(
            NORMALIZED_CSV_COLUMNS
        ):
            raise ContractError("manifest normalized CSV schema is invalid")
        path = root / filename
        if path.parent != root:
            raise ContractError(f"manifest output {key} escapes the artifact directory")
        resolved_outputs[key] = path

    return outputs, resolved_outputs, inputs, resolved_inputs


def _evidence_from_snapshots(
    root: Path,
    manifest: dict[str, Any],
    manifest_bytes: bytes,
    output_bytes: Mapping[str, bytes],
    resolved_outputs: Mapping[str, Path],
    input_bytes: Mapping[str, bytes],
    resolved_inputs: Mapping[str, Path],
) -> Evidence:
    outputs, expected_output_paths, inputs, expected_input_paths = (
        _validated_manifest_artifacts(manifest, root)
    )
    if dict(resolved_outputs) != expected_output_paths:
        raise IntegrityError("evidence output paths do not match the manifest")
    if dict(resolved_inputs) != expected_input_paths:
        raise IntegrityError("evidence input paths do not match the manifest")
    if set(output_bytes) != set(outputs):
        raise IntegrityError("evidence output snapshots do not match the manifest")
    if set(input_bytes) != set(inputs):
        raise IntegrityError("evidence input snapshots do not match the manifest")
    for key, descriptor in inputs.items():
        raw_input = input_bytes[key]
        if type(raw_input) is not bytes:
            raise IntegrityError(f"manifest input {key} snapshot is invalid")
        if sha256_hex(raw_input) != descriptor["sha256"]:
            raise IntegrityError(f"manifest digest mismatch for {descriptor['file']}")
    for key, descriptor in outputs.items():
        raw_output = output_bytes[key]
        if type(raw_output) is not bytes:
            raise IntegrityError(f"manifest output {key} snapshot is invalid")
        if sha256_hex(raw_output) != descriptor["sha256"]:
            raise IntegrityError(f"manifest digest mismatch for {descriptor['file']}")

    accepted = _load_jsonl_bytes(
        output_bytes["normalized_events_jsonl"],
        resolved_outputs["normalized_events_jsonl"],
    )
    quarantined = _load_jsonl_bytes(
        output_bytes["quarantine_records_jsonl"],
        resolved_outputs["quarantine_records_jsonl"],
    )
    for key, records in (
        ("normalized_events_jsonl", accepted),
        ("quarantine_records_jsonl", quarantined),
    ):
        canonical_artifact = b"".join(
            canonical_json_bytes(record) + b"\n" for record in records
        )
        if output_bytes[key] != canonical_artifact:
            raise ContractError(f"manifest output {key} is not canonical JSONL")
    if manifest["accepted_rows"] != len(accepted):
        raise IntegrityError("accepted row count does not match the manifest")
    if manifest["quarantined_rows"] != len(quarantined):
        raise IntegrityError("quarantined row count does not match the manifest")

    source_digest = manifest["source_file_sha256"]

    seen_ids: set[str] = set()
    seen_source_rows: set[int] = set()
    for event in accepted:
        _validate_normalized_event(event, source_digest=source_digest)
        event_id = event["event_id"]
        if event_id in seen_ids:
            raise IntegrityError("normalized event_id is duplicated")
        seen_ids.add(event_id)
        source_row = event["source_row_number"]
        if source_row in seen_source_rows:
            raise IntegrityError("normalized source_row_number is duplicated")
        seen_source_rows.add(source_row)
    if [event["event_id"] for event in accepted] != sorted(seen_ids):
        raise IntegrityError("normalized events are not ordered by event_id")

    quarantine_rows: list[int] = []
    for record in quarantined:
        _validate_quarantine_record(record)
        source_row = record["source_row_number"]
        if source_row in seen_source_rows:
            raise IntegrityError("accepted and quarantined source rows overlap")
        if source_row in quarantine_rows:
            raise IntegrityError("quarantined source_row_number is duplicated")
        quarantine_rows.append(source_row)
    if quarantine_rows != sorted(quarantine_rows):
        raise IntegrityError("quarantine records are not ordered by source row")

    actual_source_rows = seen_source_rows | set(quarantine_rows)
    expected_source_rows = set(range(2, manifest["source_rows"] + 2))
    if actual_source_rows != expected_source_rows:
        raise IntegrityError(
            "accepted and quarantined source rows do not form the exact producer partition"
        )

    csv_records = _load_normalized_csv_bytes(
        output_bytes["normalized_events_csv"],
        resolved_outputs["normalized_events_csv"],
    )
    expected_csv_records = [
        {column: str(event[column]) for column in NORMALIZED_CSV_COLUMNS}
        for event in accepted
    ]
    if csv_records != expected_csv_records:
        raise IntegrityError("normalized CSV rows do not match normalized JSONL rows")

    try:
        replay = replay_pipeline(
            source_bytes=input_bytes["source_csv"],
            aliases_bytes=input_bytes["resolved_aliases_json"],
        )
    except ReplayContractError as exc:
        raise ContractError(f"independent pipeline replay failed: {exc}") from exc

    replay_metadata = {
        "aliases_sha256": replay.aliases_sha256,
        "pipeline_run_id": replay.pipeline_run_id,
        "source_file_sha256": replay.source_file_sha256,
        "source_rows": replay.source_rows,
    }
    for field, expected in replay_metadata.items():
        if manifest[field] != expected:
            raise IntegrityError(
                f"pipeline {field} does not match independent replay"
            )
    if manifest["accepted_rows"] != len(replay.accepted):
        raise IntegrityError("accepted row count does not match independent replay")
    if manifest["quarantined_rows"] != len(replay.quarantined):
        raise IntegrityError("quarantined row count does not match independent replay")

    replay_outputs = {
        "normalized_events_jsonl": replay.normalized_jsonl,
        "normalized_events_csv": replay.normalized_csv,
        "quarantine_records_jsonl": replay.quarantine_jsonl,
    }
    for key, expected_bytes in replay_outputs.items():
        if output_bytes[key] != expected_bytes:
            raise IntegrityError(
                f"manifest output {key} does not match independent pipeline replay"
            )

    immutable_manifest = _freeze_json(manifest)
    immutable_accepted = tuple(
        _freeze_json(event) for event in sorted(accepted, key=lambda record: record["event_id"])
    )
    return Evidence(
        directory=root,
        manifest=immutable_manifest,
        manifest_sha256=sha256_hex(manifest_bytes),
        accepted_events=immutable_accepted,
        normalized_filename=outputs["normalized_events_jsonl"]["file"],
        normalized_sha256=outputs["normalized_events_jsonl"]["sha256"],
        quarantine_sha256=outputs["quarantine_records_jsonl"]["sha256"],
        _manifest_bytes=manifest_bytes,
        _output_snapshots=tuple(
            (key, output_bytes[key]) for key in sorted(output_bytes)
        ),
        _input_snapshots=tuple(
            (key, input_bytes[key]) for key in sorted(input_bytes)
        ),
    )


def _validate_normalized_event(
    event: Mapping[str, Any], *, source_digest: str
) -> None:
    if type(event) is not dict or set(event) != EVENT_FIELDS:
        raise ContractError("normalized event fields do not match the v1 contract")
    for field in EVENT_STRING_FIELDS:
        if type(event[field]) is not str:
            raise ContractError(f"normalized event {field} must be a string")
        if not event[field] or event[field] != event[field].strip():
            raise ContractError(f"normalized event {field} must be non-empty and trimmed")
    for field in ("event_id", "raw_record_sha256", "source_file_sha256"):
        if not SHA256_PATTERN.fullmatch(event[field]):
            raise ContractError(f"normalized event {field} is invalid")
    if event["source_file_sha256"] != source_digest:
        raise IntegrityError("event source digest does not match the manifest")
    if (
        type(event["source_row_number"]) is not int
        or event["source_row_number"] < 2
    ):
        raise ContractError("normalized event source_row_number is invalid")
    if type(event["volume"]) is not int or event["volume"] < 0:
        raise ContractError("normalized event volume is invalid")
    if event["transform_version"] != NORMALIZED_EVENT_TRANSFORM_VERSION:
        raise ContractError("normalized event transform_version is invalid")
    if event["source_system"] not in ALLOWED_SOURCE_SYSTEMS:
        raise ContractError("normalized event source_system is invalid")
    if not SYMBOL_PATTERN.fullmatch(event["symbol"]):
        raise ContractError("normalized event symbol is invalid")
    if not VENUE_PATTERN.fullmatch(event["venue"]):
        raise ContractError("normalized event venue is invalid")
    if not re.fullmatch(r"[A-Z]{3}", event["currency"]):
        raise ContractError("normalized event currency is invalid")
    if not UTC_TIMESTAMP_PATTERN.fullmatch(event["event_time_utc"]):
        raise ContractError("normalized event event_time_utc is invalid")
    try:
        parsed_time = datetime.strptime(
            event["event_time_utc"], "%Y-%m-%dT%H:%M:%S.%fZ"
        )
    except ValueError as exc:
        raise ContractError("normalized event event_time_utc is invalid") from exc
    if (
        parsed_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        != event["event_time_utc"]
    ):
        raise ContractError("normalized event event_time_utc is invalid")
    try:
        price = Decimal(event["price"])
    except InvalidOperation as exc:
        raise ContractError("normalized event price is invalid") from exc
    if (
        not PRICE_PATTERN.fullmatch(event["price"])
        or not price.is_finite()
        or price <= 0
        or format(price, ".6f") != event["price"]
    ):
        raise ContractError("normalized event price is invalid")

    expected_event_id = sha256_hex(
        canonical_json_bytes(
            {
                "event_time_utc": event["event_time_utc"],
                "symbol": event["symbol"],
                "venue": event["venue"],
            }
        )
    )
    if event["event_id"] != expected_event_id:
        raise IntegrityError("normalized event_id does not match its identity fields")


def _validate_quarantine_record(record: Mapping[str, Any]) -> None:
    if type(record) is not dict or set(record) != QUARANTINE_FIELDS:
        raise ContractError("quarantine record fields do not match the v1 contract")
    if record["stage"] != "row_validation":
        raise ContractError("quarantine record stage is invalid")
    if (
        type(record["source_row_number"]) is not int
        or record["source_row_number"] < 2
    ):
        raise ContractError("quarantine record source_row_number is invalid")
    for field in ("quarantine_id", "raw_record_sha256"):
        if type(record[field]) is not str or not SHA256_PATTERN.fullmatch(
            record[field]
        ):
            raise ContractError(f"quarantine record {field} is invalid")

    raw_record = record["raw_record"]
    if type(raw_record) is not dict or set(raw_record) != RAW_RECORD_FIELDS:
        raise ContractError("quarantine raw_record fields do not match the v1 contract")
    if any(type(value) is not str for value in raw_record.values()):
        raise ContractError("quarantine raw_record values must be strings")
    expected_raw_digest = sha256_hex(canonical_json_bytes(raw_record))
    if record["raw_record_sha256"] != expected_raw_digest:
        raise IntegrityError("quarantine raw_record digest is invalid")

    errors = record["errors"]
    if (
        type(errors) is not list
        or not errors
        or any(type(error) is not str for error in errors)
        or errors != sorted(set(errors))
        or any(error not in QUARANTINE_ERROR_MESSAGES for error in errors)
    ):
        raise ContractError("quarantine errors are invalid")
    expected_messages = [QUARANTINE_ERROR_MESSAGES[error] for error in errors]
    if record["validation_messages"] != expected_messages:
        raise IntegrityError("quarantine validation messages do not match errors")
    expected_quarantine_id = sha256_hex(
        canonical_json_bytes(
            {
                "errors": errors,
                "raw_record_sha256": record["raw_record_sha256"],
                "source_row_number": record["source_row_number"],
            }
        )
    )
    if record["quarantine_id"] != expected_quarantine_id:
        raise IntegrityError("quarantine_id does not match its bound fields")


def _load_normalized_csv_bytes(raw: bytes, path: Path) -> list[dict[str, str]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractError(f"invalid normalized CSV {path}: {exc}") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != list(NORMALIZED_CSV_COLUMNS):
        raise ContractError("normalized CSV header does not match the v1 contract")

    records: list[dict[str, str]] = []
    for row in reader:
        if None in row or set(row) != set(NORMALIZED_CSV_COLUMNS):
            raise ContractError("normalized CSV row does not match the v1 contract")
        if any(type(value) is not str for value in row.values()):
            raise ContractError("normalized CSV values must be strings")
        records.append(dict(row))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=NORMALIZED_CSV_COLUMNS,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(records)
    if raw != buffer.getvalue().encode("utf-8"):
        raise ContractError("normalized CSV is not canonically encoded")
    return records


def _validate_evidence_binding(evidence: Evidence) -> None:
    if type(evidence) is not Evidence:
        raise IntegrityError("evidence semantic binding is invalid")
    if (
        not isinstance(evidence.directory, Path)
        or type(evidence.manifest_sha256) is not str
        or type(evidence.accepted_events) is not tuple
        or type(evidence.normalized_filename) is not str
        or type(evidence.normalized_sha256) is not str
        or type(evidence.quarantine_sha256) is not str
        or type(evidence._manifest_bytes) is not bytes
        or type(evidence._output_snapshots) is not tuple
        or type(evidence._input_snapshots) is not tuple
    ):
        raise IntegrityError("evidence semantic binding is invalid")
    _require_immutable_json(evidence.manifest)
    _require_immutable_json(evidence.accepted_events)

    snapshots: dict[str, bytes] = {}
    for item in evidence._output_snapshots:
        if (
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not bytes
            or item[0] in snapshots
        ):
            raise IntegrityError("evidence output snapshot binding is invalid")
        snapshots[item[0]] = item[1]

    input_snapshots: dict[str, bytes] = {}
    for item in evidence._input_snapshots:
        if (
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not bytes
            or item[0] in input_snapshots
        ):
            raise IntegrityError("evidence input snapshot binding is invalid")
        input_snapshots[item[0]] = item[1]

    try:
        manifest = _load_json_bytes(
            evidence._manifest_bytes,
            evidence.directory / "<manifest snapshot>",
        )
        _, resolved_outputs, _, resolved_inputs = _validated_manifest_artifacts(
            manifest, evidence.directory
        )
        expected = _evidence_from_snapshots(
            evidence.directory,
            manifest,
            evidence._manifest_bytes,
            snapshots,
            resolved_outputs,
            input_snapshots,
            resolved_inputs,
        )
        actual_binding = canonical_json_bytes(
            _evidence_semantic_document(evidence)
        )
        expected_binding = canonical_json_bytes(
            _evidence_semantic_document(expected)
        )
    except (ContractError, IntegrityError, OSError, TypeError, ValueError) as exc:
        raise IntegrityError(f"evidence semantic binding is invalid: {exc}") from exc
    if actual_binding != expected_binding:
        raise IntegrityError("evidence semantic binding is invalid")


def _evidence_semantic_document(evidence: Evidence) -> dict[str, Any]:
    return {
        "accepted_events": evidence.accepted_events,
        "manifest": evidence.manifest,
        "manifest_sha256": evidence.manifest_sha256,
        "normalized_filename": evidence.normalized_filename,
        "normalized_sha256": evidence.normalized_sha256,
        "quarantine_sha256": evidence.quarantine_sha256,
    }


def _require_immutable_json(value: Any) -> None:
    if type(value) is IMMUTABLE_MAPPING_TYPE:
        for key, item in value.items():
            if type(key) is not str:
                raise IntegrityError("evidence semantic binding is invalid")
            _require_immutable_json(item)
        return
    if type(value) is tuple:
        for item in value:
            _require_immutable_json(item)
        return
    if value is None or type(value) in {bool, int, float, str}:
        return
    raise IntegrityError("evidence semantic binding is invalid")


def build_decision(
    request: Mapping[str, Any], *, evidence: Evidence, policy: Policy
) -> dict[str, Any]:
    _validate_evidence_binding(evidence)
    _validate_policy_binding(policy)
    _validate_request(request)
    task_type = request["task_type"]

    if task_type in policy.refused_tasks:
        return _decision(request, evidence, policy, "REFUSE", "action_not_authorized")
    if task_type in policy.abstained_tasks:
        return _decision(
            request,
            evidence,
            policy,
            "ABSTAIN",
            "production_evidence_unavailable",
        )
    if task_type not in policy.allowed_tasks:
        return _decision(request, evidence, policy, "ABSTAIN", "unsupported_task")

    if task_type == "quality_status":
        context = {
            "accepted_rows": evidence.manifest["accepted_rows"],
            "context_type": "quality_status",
            "pipeline_run_id": evidence.manifest["pipeline_run_id"],
            "quarantine_detail_included": False,
            "quarantined_rows": evidence.manifest["quarantined_rows"],
            "source_file_sha256": evidence.manifest["source_file_sha256"],
            "transform_version": evidence.manifest["transform_version"],
        }
        citation = {
            "artifact": "manifest.json",
            "artifact_sha256": evidence.manifest_sha256,
            "record_id": evidence.manifest["pipeline_run_id"],
        }
        return _decision(
            request,
            evidence,
            policy,
            "ADMIT",
            "governed_quality_summary_available",
            context=context,
            citations=[citation],
        )

    subject = request["subject"]
    if subject is None:
        return _decision(request, evidence, policy, "ABSTAIN", "subject_required")
    normalized_subject = subject.upper()
    matches = [
        dict(event)
        for event in evidence.accepted_events
        if event["symbol"] == normalized_subject
    ]
    if not matches:
        return _decision(request, evidence, policy, "ABSTAIN", "no_governed_evidence")

    selected = matches[: policy.max_context_records]
    citations = [
        {
            "artifact": evidence.normalized_filename,
            "artifact_sha256": evidence.normalized_sha256,
            "record_id": event["event_id"],
            "record_sha256": sha256_hex(canonical_json_bytes(event)),
        }
        for event in selected
    ]
    context = {
        "context_type": "accepted_observation_summary",
        "records": selected,
        "requested_subject": subject,
        "resolved_subject": normalized_subject,
        "total_matching_records": len(matches),
        "truncated": len(matches) > len(selected),
    }
    return _decision(
        request,
        evidence,
        policy,
        "ADMIT",
        "governed_context_available",
        context=context,
        citations=citations,
    )


def verify_decision(
    decision: Mapping[str, Any], *, evidence: Evidence, policy: Policy
) -> None:
    _require_canonical_decision_json(decision)
    _validate_evidence_binding(evidence)
    _validate_policy_binding(policy)
    request = {
        "request_id": decision.get("request_id"),
        "subject": decision.get("subject"),
        "task_type": decision.get("task_type"),
    }
    try:
        recomputed = build_decision(request, evidence=evidence, policy=policy)
    except ContractError as exc:
        raise IntegrityError(f"decision request binding is invalid: {exc}") from exc
    if decision.get("schema_version") != DECISION_SCHEMA:
        raise IntegrityError("decision schema is invalid")
    if decision.get("policy_sha256") != policy.sha256:
        raise IntegrityError("decision policy binding is invalid")
    binding = decision.get("input_binding")
    if binding != {
        "pipeline_manifest_sha256": evidence.manifest_sha256,
        "pipeline_run_id": evidence.manifest["pipeline_run_id"],
    }:
        raise IntegrityError("decision input binding is invalid")
    if decision.get("model_execution") != {
        "authorized": False,
        "status": "NOT_EXECUTED",
    }:
        raise IntegrityError("decision must keep model execution disabled")
    if _contains_exact_key(decision, "raw_record"):
        raise IntegrityError("decision exposes a quarantined raw record")

    disposition = decision.get("disposition")
    context = decision.get("context")
    citations = decision.get("citations")
    if disposition not in {"ADMIT", "ABSTAIN", "REFUSE"}:
        raise IntegrityError("decision disposition is invalid")
    if not isinstance(citations, list):
        raise IntegrityError("decision citations must be a list")
    if disposition != "ADMIT":
        if context is not None or citations:
            raise IntegrityError("non-admitted decisions cannot carry context or citations")
        if canonical_json_bytes(decision) != canonical_json_bytes(recomputed):
            raise IntegrityError("decision does not match governed recomputation")
        return
    if not isinstance(context, dict) or not citations:
        raise IntegrityError("admitted decisions require context and citations")

    events_by_id = {event["event_id"]: event for event in evidence.accepted_events}
    for citation in citations:
        if not isinstance(citation, dict):
            raise IntegrityError("citation must be an object")
        artifact = citation.get("artifact")
        if artifact == "manifest.json":
            if citation != {
                "artifact": "manifest.json",
                "artifact_sha256": evidence.manifest_sha256,
                "record_id": evidence.manifest["pipeline_run_id"],
            }:
                raise IntegrityError("manifest citation is invalid")
        elif artifact == evidence.normalized_filename:
            event = events_by_id.get(citation.get("record_id"))
            if event is None:
                raise IntegrityError("citation record does not resolve")
            expected = {
                "artifact": evidence.normalized_filename,
                "artifact_sha256": evidence.normalized_sha256,
                "record_id": event["event_id"],
                "record_sha256": sha256_hex(canonical_json_bytes(event)),
            }
            if citation != expected:
                raise IntegrityError("normalized-event citation is invalid")
        else:
            raise IntegrityError("citation references a non-admitted artifact")

    context_type = context.get("context_type")
    if context_type == "accepted_observation_summary":
        subject = decision.get("subject")
        if not isinstance(subject, str):
            raise IntegrityError("accepted observation context requires a subject")
        resolved_subject = subject.upper()
        matches = [
            dict(event)
            for event in evidence.accepted_events
            if event["symbol"] == resolved_subject
        ]
        selected = matches[: policy.max_context_records]
        expected_context = {
            "context_type": "accepted_observation_summary",
            "records": selected,
            "requested_subject": subject,
            "resolved_subject": resolved_subject,
            "total_matching_records": len(matches),
            "truncated": len(matches) > len(selected),
        }
        if context != expected_context:
            raise IntegrityError("accepted observation context is invalid")
        if [record["event_id"] for record in selected] != [
            citation["record_id"] for citation in citations
        ]:
            raise IntegrityError("context record order does not match citations")
    elif context_type == "quality_status":
        expected_context = {
            "accepted_rows": evidence.manifest["accepted_rows"],
            "context_type": "quality_status",
            "pipeline_run_id": evidence.manifest["pipeline_run_id"],
            "quarantine_detail_included": False,
            "quarantined_rows": evidence.manifest["quarantined_rows"],
            "source_file_sha256": evidence.manifest["source_file_sha256"],
            "transform_version": evidence.manifest["transform_version"],
        }
        if context != expected_context:
            raise IntegrityError("quality context is invalid")
        if len(citations) != 1 or citations[0]["artifact"] != "manifest.json":
            raise IntegrityError("quality context must cite only the manifest")
    else:
        raise IntegrityError("admitted context type is invalid")
    if canonical_json_bytes(decision) != canonical_json_bytes(recomputed):
        raise IntegrityError("decision does not match governed recomputation")


def _decision(
    request: Mapping[str, Any],
    evidence: Evidence,
    policy: Policy,
    disposition: str,
    reason_code: str,
    *,
    context: Mapping[str, Any] | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "citations": citations or [],
        "context": dict(context) if context is not None else None,
        "disposition": disposition,
        "input_binding": {
            "pipeline_manifest_sha256": evidence.manifest_sha256,
            "pipeline_run_id": evidence.manifest["pipeline_run_id"],
        },
        "model_execution": {"authorized": False, "status": "NOT_EXECUTED"},
        "policy_sha256": policy.sha256,
        "reason_codes": [reason_code],
        "request_id": request["request_id"],
        "schema_version": DECISION_SCHEMA,
        "subject": request["subject"],
        "task_type": request["task_type"],
    }


def _validate_request(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping):
        raise ContractError("request must be an object")
    if any(type(key) is not str for key in request):
        raise ContractError("request field names must be strings")
    if set(request) != {"request_id", "task_type", "subject"}:
        raise ContractError("request fields do not match the v1 contract")
    if type(request["request_id"]) is not str or not REQUEST_ID_PATTERN.fullmatch(
        request["request_id"]
    ):
        raise ContractError("request_id is invalid")
    if type(request["task_type"]) is not str or not TASK_PATTERN.fullmatch(
        request["task_type"]
    ):
        raise ContractError("task_type is invalid")
    subject = request["subject"]
    if subject is not None and (
        type(subject) is not str or not subject.strip() or len(subject) > 64
    ):
        raise ContractError("subject must be null or a non-empty string up to 64 characters")


def _require_canonical_decision_json(value: Any, *, path: str = "decision") -> None:
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise IntegrityError(f"{path} contains a noncanonical object key")
            _require_canonical_decision_json(item, path=f"{path}.{key}")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _require_canonical_decision_json(item, path=f"{path}[{index}]")
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise IntegrityError(f"{path} contains a non-finite float")
        return
    if value is None or type(value) in {bool, int, str}:
        return
    raise IntegrityError(f"{path} contains a noncanonical JSON value")


def _load_jsonl_bytes(raw: bytes, path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise ContractError(f"unable to decode JSONL artifact {path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line:
            raise ContractError(f"blank JSONL line in {path} at {line_number}")
        try:
            record = json.loads(
                line,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_nonfinite,
            )
        except (json.JSONDecodeError, ContractError) as exc:
            raise ContractError(
                f"invalid JSONL record in {path} at {line_number}: {exc}"
            ) from exc
        if not isinstance(record, dict):
            raise ContractError(f"JSONL root must be an object in {path} at {line_number}")
        records.append(record)
    return records


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ContractError(f"non-finite JSON value: {value}")


def _contains_exact_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_exact_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_exact_key(item, key) for item in value)
    return False
