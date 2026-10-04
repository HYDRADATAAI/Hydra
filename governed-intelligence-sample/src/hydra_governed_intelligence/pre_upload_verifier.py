"""Verify every generated governed-intelligence artifact before CI upload."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import sys
import tempfile
import zipfile
import zlib
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import NoReturn


SOURCE_ROOT = Path(__file__).resolve().parents[1]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from hydra_governed_intelligence import (  # noqa: E402
    ContractError,
    IntegrityError,
    load_evidence,
    load_grounding_policy,
    load_policy,
    load_retrieval_policy,
    verify_decision,
    verify_grounding_receipt,
    verify_retrieval_decision,
)
from hydra_governed_intelligence.context import Evidence  # noqa: E402


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PUBLISHED_RETRIEVAL_METRICS = {
    "macro_recall_at_k": "0.583333",
    "mean_reciprocal_rank": "0.666667",
    "micro_recall_at_k": "0.444444",
}
BUNDLE_MEMBERS = (
    "governed-intelligence-sample/build/evaluation/decisions.jsonl",
    "governed-intelligence-sample/build/evaluation/evaluation_report.json",
    "governed-intelligence-sample/build/evaluation/output_manifest.json",
    "governed-intelligence-sample/build/grounding/grounding_evaluation_report.json",
    "governed-intelligence-sample/build/grounding/grounding_output_manifest.json",
    "governed-intelligence-sample/build/grounding/grounding_receipts.jsonl",
    "governed-intelligence-sample/build/retrieval/retrieval_decisions.jsonl",
    "governed-intelligence-sample/build/retrieval/retrieval_evaluation_report.json",
    "governed-intelligence-sample/build/retrieval/retrieval_output_manifest.json",
    "market-data-pipeline-sample/build/demo/manifest.json",
    "market-data-pipeline-sample/build/demo/normalized_events.csv",
    "market-data-pipeline-sample/build/demo/normalized_events.jsonl",
    "market-data-pipeline-sample/build/demo/quarantine_records.jsonl",
    "market-data-pipeline-sample/build/demo/resolved_symbol_aliases.json",
    "market-data-pipeline-sample/build/demo/source_snapshot.csv",
)
VERIFICATION_SUPPORT_FILES = (
    "governed-intelligence-sample/config/grounding_policy.json",
    "governed-intelligence-sample/config/policy.json",
    "governed-intelligence-sample/config/retrieval_policy.json",
    "governed-intelligence-sample/fixtures/evaluation_cases.json",
    "governed-intelligence-sample/fixtures/grounding_cases.json",
    "governed-intelligence-sample/fixtures/retrieval_cases.json",
    "governed-intelligence-sample/fixtures/retrieval_qrels.json",
)
VERIFICATION_INPUTS = BUNDLE_MEMBERS + VERIFICATION_SUPPORT_FILES
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIP_EXTERNAL_ATTR = (stat.S_IFREG | 0o644) << 16


class VerificationError(RuntimeError):
    """Raised when a generated artifact fails the pre-upload contract."""


@dataclass(frozen=True)
class VerificationSummary:
    manifest_outputs: int
    receipts: int
    input_snapshots_verified: int
    source_rows_replayed: int


@dataclass(frozen=True)
class BundleSummary:
    manifest_outputs: int
    receipts: int
    input_snapshots_verified: int
    source_rows_replayed: int
    bundle_members: int
    bundle_bytes: int
    bundle_sha256: str


def _fail(label: str, detail: str) -> NoReturn:
    raise VerificationError(f"{label}: {detail}")


def _require(condition: bool, label: str, detail: str) -> None:
    if not condition:
        _fail(label, detail)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON value: {value}")


def _parse_json(raw: bytes, label: str) -> object:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        _fail(label, f"invalid JSON: {exc}")


def _file_bytes(path: Path, label: str) -> bytes:
    _require(path.is_file(), label, "missing regular file")
    _require(not path.is_symlink(), label, "symbolic links are not allowed")
    try:
        return path.read_bytes()
    except OSError as exc:
        _fail(label, f"unable to read file: {exc}")


def _snapshot_file(path: Path, label: str) -> bytes:
    """Read one regular, non-symlinked input into its immutable byte snapshot."""

    descriptor: int | None = None
    try:
        path_before = path.lstat()
        _require(
            not _is_symlink_or_reparse(path_before),
            label,
            "symbolic links and reparse points are not allowed",
        )
        _require(stat.S_ISREG(path_before.st_mode), label, "missing regular file")

        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            descriptor_before = os.fstat(handle.fileno())
            _require(
                stat.S_ISREG(descriptor_before.st_mode),
                label,
                "missing regular file",
            )
            _require(
                os.path.samestat(path_before, descriptor_before),
                label,
                "file identity changed while opening",
            )
            payload = handle.read()
            descriptor_after = os.fstat(handle.fileno())
            path_after = path.lstat()
            _require(
                stat.S_ISREG(descriptor_after.st_mode)
                and stat.S_ISREG(path_after.st_mode)
                and not _is_symlink_or_reparse(path_after),
                label,
                "file type changed while reading",
            )
            _require(
                os.path.samestat(descriptor_before, descriptor_after)
                and os.path.samestat(descriptor_after, path_after),
                label,
                "file identity changed while reading",
            )
            _require(
                descriptor_before.st_size == descriptor_after.st_size == len(payload)
                and descriptor_before.st_mtime_ns == descriptor_after.st_mtime_ns,
                label,
                "file metadata changed while reading",
            )
            return payload
    except OSError as exc:
        _fail(label, f"unable to snapshot file: {exc}")
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _is_symlink_or_reparse(metadata: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & reparse_flag
    )


def _checked_repository_root(repository_root: Path, label: str) -> Path:
    root = repository_root.absolute()
    try:
        metadata = root.lstat()
    except OSError as exc:
        _fail(label, f"unable to inspect repository root: {exc}")
    _require(
        not _is_symlink_or_reparse(metadata),
        label,
        "repository root must not be a symbolic link or reparse point",
    )
    _require(stat.S_ISDIR(metadata.st_mode), label, "repository root is missing")
    return root


def _relative_snapshot_path(repository_root: Path, candidate: Path, label: str) -> Path:
    try:
        relative_path = candidate.absolute().relative_to(repository_root)
    except ValueError:
        _fail(label, "path is not contained under the repository root")
    _require(
        bool(relative_path.parts)
        and "." not in relative_path.parts
        and ".." not in relative_path.parts,
        label,
        "unsafe snapshot path",
    )
    return relative_path


def _windows_close_handle(handle: int) -> None:
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle(ctypes.c_void_p(handle))


def _windows_normalize_path(path: str | Path) -> str:
    normalized = str(path)
    if normalized.startswith("\\\\?\\UNC\\"):
        normalized = "\\\\" + normalized[8:]
    elif normalized.startswith("\\\\?\\"):
        normalized = normalized[4:]
    return os.path.normcase(os.path.normpath(normalized))


def _windows_final_path(handle: int) -> str:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFinalPathNameByHandleW.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(32768)
    length = kernel32.GetFinalPathNameByHandleW(
        wintypes.HANDLE(handle),
        buffer,
        len(buffer),
        0,
    )
    if length == 0 or length >= len(buffer):
        error = ctypes.get_last_error()
        raise OSError(error, ctypes.FormatError(error))
    return _windows_normalize_path(buffer.value)


def _require_windows_handle_path(handle: int, expected: Path, label: str) -> None:
    _require(
        _windows_final_path(handle) == _windows_normalize_path(expected),
        label,
        "opened handle physical path changed",
    )


def _windows_validate_handle(
    handle: int,
    label: str,
    *,
    directory: bool,
) -> tuple[int, int]:
    import ctypes
    from ctypes import wintypes

    class ByHandleFileInformation(ctypes.Structure):
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

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetFileInformationByHandle.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ByHandleFileInformation),
    )
    kernel32.GetFileInformationByHandle.restype = wintypes.BOOL

    info = ByHandleFileInformation()
    if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(info)):
        error = ctypes.get_last_error()
        raise OSError(error, ctypes.FormatError(error))

    file_attribute_directory = 0x00000010
    file_attribute_reparse_point = 0x00000400
    if info.dwFileAttributes & file_attribute_reparse_point:
        _fail(label, "symbolic links and reparse points are not allowed")
    is_directory = bool(info.dwFileAttributes & file_attribute_directory)
    if is_directory != directory:
        _fail(label, "snapshot path type changed")
    file_index = (info.nFileIndexHigh << 32) | info.nFileIndexLow
    return (int(info.dwVolumeSerialNumber), file_index)


def _windows_open_path(path: Path, label: str, *, directory: bool) -> int:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    kernel32.CreateFileW.restype = wintypes.HANDLE

    generic_read = 0x80000000
    file_read_attributes = 0x00000080
    file_share_read = 0x00000001
    file_share_write = 0x00000002
    open_existing = 3
    file_flag_backup_semantics = 0x02000000
    file_flag_open_reparse_point = 0x00200000
    desired_access = file_read_attributes if directory else generic_read
    flags = file_flag_open_reparse_point
    if directory:
        flags |= file_flag_backup_semantics

    handle = kernel32.CreateFileW(
        str(path),
        desired_access,
        file_share_read | file_share_write,
        None,
        open_existing,
        flags,
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle == invalid_handle:
        error = ctypes.get_last_error()
        raise OSError(error, ctypes.FormatError(error), str(path))
    try:
        _windows_validate_handle(handle, label, directory=directory)
    except (OSError, VerificationError):
        _windows_close_handle(handle)
        raise
    return int(handle)


def _windows_open_relative(
    parent_handle: int,
    name: str,
    label: str,
    *,
    directory: bool,
) -> int:
    import ctypes
    from ctypes import wintypes

    class UnicodeString(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.USHORT),
            ("MaximumLength", wintypes.USHORT),
            ("Buffer", wintypes.LPWSTR),
        ]

    class ObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.ULONG),
            ("RootDirectory", wintypes.HANDLE),
            ("ObjectName", ctypes.POINTER(UnicodeString)),
            ("Attributes", wintypes.ULONG),
            ("SecurityDescriptor", wintypes.LPVOID),
            ("SecurityQualityOfService", wintypes.LPVOID),
        ]

    class IoStatusBlock(ctypes.Structure):
        _fields_ = [
            ("StatusOrPointer", ctypes.c_void_p),
            ("Information", ctypes.c_size_t),
        ]

    name_buffer = ctypes.create_unicode_buffer(name)
    name_bytes = name.encode("utf-16-le")
    unicode_name = UnicodeString(
        len(name_bytes),
        len(name_bytes) + 2,
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    object_attributes = ObjectAttributes(
        ctypes.sizeof(ObjectAttributes),
        wintypes.HANDLE(parent_handle),
        ctypes.pointer(unicode_name),
        0x00000040,
        None,
        None,
    )
    io_status = IoStatusBlock()
    handle = wintypes.HANDLE()
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    ntdll.NtCreateFile.restype = wintypes.LONG

    generic_read = 0x80000000
    file_read_attributes = 0x00000080
    synchronize = 0x00100000
    file_share_read = 0x00000001
    file_share_write = 0x00000002
    file_open = 0x00000001
    file_directory_file = 0x00000001
    file_synchronous_io_nonalert = 0x00000020
    file_non_directory_file = 0x00000040
    file_open_reparse_point = 0x00200000
    desired_access = (
        file_read_attributes | synchronize if directory else generic_read | synchronize
    )
    create_options = file_synchronous_io_nonalert | file_open_reparse_point
    create_options |= file_directory_file if directory else file_non_directory_file
    status = ntdll.NtCreateFile(
        ctypes.byref(handle),
        desired_access,
        ctypes.byref(object_attributes),
        ctypes.byref(io_status),
        None,
        0,
        file_share_read | file_share_write,
        file_open,
        create_options,
        None,
        0,
    )
    if status < 0:
        ntdll.RtlNtStatusToDosError.restype = wintypes.ULONG
        error = int(ntdll.RtlNtStatusToDosError(status))
        raise OSError(error, ctypes.FormatError(error), name)
    opened_handle = int(handle.value)
    try:
        _windows_validate_handle(opened_handle, label, directory=directory)
    except (OSError, VerificationError):
        _windows_close_handle(opened_handle)
        raise
    return opened_handle


def _close_bound_directories(handles: list[int]) -> None:
    for handle in reversed(handles):
        try:
            if os.name == "nt":
                _windows_close_handle(handle)
            else:
                os.close(handle)
        except OSError:
            pass


def _open_bound_directory_chain(
    repository_root: Path,
    directory_parts: tuple[str, ...],
    label: str,
) -> list[int]:
    handles: list[int] = []
    try:
        if os.name == "nt":
            current = repository_root
            expected_physical = repository_root.resolve(strict=True)
            root_handle = _windows_open_path(current, label, directory=True)
            handles.append(root_handle)
            _require_windows_handle_path(root_handle, expected_physical, label)
            for part in directory_parts:
                current /= part
                expected_physical /= part
                handle = _windows_open_relative(
                    handles[-1],
                    part,
                    label,
                    directory=True,
                )
                handles.append(handle)
                _require_windows_handle_path(handle, expected_physical, label)
            return handles

        _require(
            os.open in os.supports_dir_fd
            and os.stat in os.supports_dir_fd
            and os.stat in os.supports_follow_symlinks
            and bool(getattr(os, "O_NOFOLLOW", 0))
            and bool(getattr(os, "O_DIRECTORY", 0)),
            label,
            "platform lacks safe descriptor-relative traversal",
        )
        directory_flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | os.O_NOFOLLOW
            | os.O_DIRECTORY
        )
        root_before = repository_root.lstat()
        root_handle = os.open(repository_root, directory_flags)
        handles.append(root_handle)
        root_descriptor = os.fstat(root_handle)
        _require(
            stat.S_ISDIR(root_descriptor.st_mode)
            and os.path.samestat(root_before, root_descriptor),
            label,
            "repository root identity changed while opening",
        )

        for part in directory_parts:
            before = os.stat(part, dir_fd=handles[-1], follow_symlinks=False)
            _require(
                not _is_symlink_or_reparse(before),
                label,
                "symbolic-link or reparse-point ancestors are not allowed",
            )
            _require(
                stat.S_ISDIR(before.st_mode),
                label,
                "snapshot ancestor is not a directory",
            )
            handle = os.open(part, directory_flags, dir_fd=handles[-1])
            handles.append(handle)
            descriptor = os.fstat(handle)
            _require(
                stat.S_ISDIR(descriptor.st_mode)
                and os.path.samestat(before, descriptor),
                label,
                "snapshot ancestor identity changed while opening",
            )
        return handles
    except VerificationError:
        _close_bound_directories(handles)
        raise
    except OSError as exc:
        _close_bound_directories(handles)
        _fail(label, f"unable to open snapshot ancestry: {exc}")


def _bound_leaf_lstat(parent_handle: int, leaf_name: str, candidate: Path) -> os.stat_result:
    if os.name == "nt":
        return candidate.lstat()
    return os.stat(
        leaf_name,
        dir_fd=parent_handle,
        follow_symlinks=False,
    )


def _open_bound_leaf(
    parent_handle: int,
    leaf_name: str,
    candidate: Path,
    label: str,
) -> int:
    if os.name == "nt":
        import msvcrt

        handle = _windows_open_relative(
            parent_handle,
            leaf_name,
            label,
            directory=False,
        )
        try:
            return msvcrt.open_osfhandle(
                handle,
                os.O_RDONLY | getattr(os, "O_BINARY", 0),
            )
        except OSError:
            _windows_close_handle(handle)
            raise
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | os.O_NOFOLLOW
    return os.open(leaf_name, flags, dir_fd=parent_handle)


def _snapshot_repository_file(
    repository_root: Path,
    candidate: Path,
    label: str,
) -> bytes:
    root = _checked_repository_root(repository_root, label)
    relative_path = _relative_snapshot_path(root, candidate, label)
    root_before = root.lstat()
    directory_handles = _open_bound_directory_chain(
        root,
        relative_path.parts[:-1],
        label,
    )
    descriptor: int | None = None
    try:
        parent_handle = directory_handles[-1]
        leaf_name = relative_path.parts[-1]
        windows_root_identity: tuple[int, int] | None = None
        if os.name == "nt":
            windows_root_identity = _windows_validate_handle(
                directory_handles[0],
                label,
                directory=True,
            )
            _require(
                (root_before.st_dev, root_before.st_ino) == windows_root_identity,
                label,
                "repository root identity changed while opening",
            )
            path_before = None
        else:
            path_before = _bound_leaf_lstat(parent_handle, leaf_name, candidate)
            _require(
                not _is_symlink_or_reparse(path_before),
                label,
                "symbolic links and reparse points are not allowed",
            )
            _require(stat.S_ISREG(path_before.st_mode), label, "missing regular file")

        descriptor = _open_bound_leaf(parent_handle, leaf_name, candidate, label)
        if os.name == "nt":
            import msvcrt

            expected_physical = root.resolve(strict=True) / relative_path
            _require_windows_handle_path(
                msvcrt.get_osfhandle(descriptor),
                expected_physical,
                label,
            )
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            descriptor_before = os.fstat(handle.fileno())
            _require(
                stat.S_ISREG(descriptor_before.st_mode)
                and (
                    path_before is None
                    or os.path.samestat(path_before, descriptor_before)
                ),
                label,
                "file identity changed while opening",
            )
            payload = handle.read()
            descriptor_after = os.fstat(handle.fileno())
            if os.name == "nt":
                root_after = root.lstat()
                root_identity_after = _windows_validate_handle(
                    directory_handles[0],
                    label,
                    directory=True,
                )
                _require(
                    windows_root_identity == root_identity_after
                    and (root_after.st_dev, root_after.st_ino)
                    == windows_root_identity
                    and os.path.samestat(root_before, root_after),
                    label,
                    "repository root identity changed while reading",
                )
                _require_windows_handle_path(
                    directory_handles[0],
                    root.resolve(strict=True),
                    label,
                )
                _require(
                    stat.S_ISREG(descriptor_after.st_mode),
                    label,
                    "file type changed while reading",
                )
                identity_unchanged = os.path.samestat(
                    descriptor_before,
                    descriptor_after,
                )
            else:
                path_after = _bound_leaf_lstat(parent_handle, leaf_name, candidate)
                _require(
                    stat.S_ISREG(descriptor_after.st_mode)
                    and stat.S_ISREG(path_after.st_mode)
                    and not _is_symlink_or_reparse(path_after),
                    label,
                    "file type changed while reading",
                )
                identity_unchanged = os.path.samestat(
                    descriptor_before,
                    descriptor_after,
                ) and os.path.samestat(descriptor_after, path_after)
            _require(
                identity_unchanged,
                label,
                "file identity changed while reading",
            )
            _require(
                descriptor_before.st_size == descriptor_after.st_size == len(payload)
                and descriptor_before.st_mtime_ns == descriptor_after.st_mtime_ns,
                label,
                "file metadata changed while reading",
            )
            return payload
    except VerificationError:
        raise
    except OSError as exc:
        _fail(label, f"unable to snapshot file: {exc}")
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        _close_bound_directories(directory_handles)


def _bound_directory_entries(
    repository_root: Path,
    relative_directory: Path,
    label: str,
) -> set[str]:
    handles = _open_bound_directory_chain(
        repository_root,
        relative_directory.parts,
        label,
    )
    try:
        if os.name == "nt":
            return {entry.name for entry in (repository_root / relative_directory).iterdir()}
        return set(os.listdir(handles[-1]))
    except OSError as exc:
        _fail(label, f"unable to enumerate artifact directory: {exc}")
    finally:
        _close_bound_directories(handles)


def _write_github_output(path: Path, summary: BundleSummary) -> None:
    _require(
        SHA256_PATTERN.fullmatch(summary.bundle_sha256) is not None,
        "GitHub step output",
        "bundle SHA-256 is invalid",
    )
    _require(
        summary.input_snapshots_verified == 2,
        "GitHub step output",
        "input snapshot count changed",
    )
    _require(
        summary.source_rows_replayed == 7,
        "GitHub step output",
        "source row replay count changed",
    )
    payload = (
        f"bundle_sha256={summary.bundle_sha256}\n"
        f"input_snapshots_verified={summary.input_snapshots_verified}\n"
        f"source_rows_replayed={summary.source_rows_replayed}\n"
    ).encode("ascii")
    descriptor: int | None = None
    try:
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags, 0o600)
        written = os.write(descriptor, payload)
        _require(
            written == len(payload),
            "GitHub step output",
            "short write",
        )
        os.fsync(descriptor)
    except OSError as exc:
        _fail("GitHub step output", f"unable to write output: {exc}")
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _snapshot_verification_inputs(repository_root: Path) -> dict[str, bytes]:
    root = _checked_repository_root(repository_root, "artifact snapshots")

    candidates: dict[str, Path] = {}
    for relative_name in VERIFICATION_INPUTS:
        _require(relative_name.isascii(), relative_name, "path must be ASCII")
        _require("\\" not in relative_name, relative_name, "path must use POSIX separators")
        relative_path = Path(relative_name)
        _require(
            not relative_path.is_absolute()
            and "." not in relative_path.parts
            and ".." not in relative_path.parts,
            relative_name,
            "unsafe verification input path",
        )
        candidate = root / relative_path
        candidates[relative_name] = candidate

    expected_by_directory: dict[str, set[str]] = {}
    for member in BUNDLE_MEMBERS:
        member_path = Path(member)
        expected_by_directory.setdefault(member_path.parent.as_posix(), set()).add(
            member_path.name
        )
    for directory_name, expected_names in expected_by_directory.items():
        actual_names = _bound_directory_entries(
            root,
            Path(directory_name),
            directory_name,
        )
        _require(
            actual_names == expected_names,
            directory_name,
            "directory contains unlisted or missing entries",
        )

    snapshots: dict[str, bytes] = {}
    for relative_name, candidate in candidates.items():
        snapshots[relative_name] = _snapshot_repository_file(
            root,
            candidate,
            f"artifact snapshot:{relative_name}",
        )
    return snapshots


def _build_bundle_bytes(snapshots: dict[str, bytes]) -> bytes:
    _require(
        set(BUNDLE_MEMBERS).issubset(snapshots),
        "artifact bundle",
        "required snapshots are missing",
    )
    buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(
            buffer,
            mode="w",
            compression=zipfile.ZIP_STORED,
            allowZip64=False,
            strict_timestamps=True,
        ) as archive:
            archive.comment = b""
            for member in BUNDLE_MEMBERS:
                info = zipfile.ZipInfo(member, date_time=ZIP_TIMESTAMP)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.create_version = 20
                info.extract_version = 20
                info.flag_bits = 0
                info.internal_attr = 0
                info.external_attr = ZIP_EXTERNAL_ATTR
                info.extra = b""
                info.comment = b""
                archive.writestr(info, snapshots[member])
    except (OSError, ValueError, zipfile.LargeZipFile) as exc:
        _fail("artifact bundle", f"unable to build deterministic ZIP: {exc}")
    return buffer.getvalue()


def _verify_bundle(
    archive_bytes: bytes,
    snapshots: dict[str, bytes],
) -> dict[str, bytes]:
    label = "artifact bundle"
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes), mode="r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            _require(names == list(BUNDLE_MEMBERS), label, "member order or names changed")
            _require(len(names) == len(set(names)), label, "duplicate member name")
            _require(archive.comment == b"", label, "archive comment is not empty")

            verified: dict[str, bytes] = {}
            for info in infos:
                member_label = f"{label}:{info.filename}"
                expected = snapshots[info.filename]
                _require(not info.is_dir(), member_label, "directory entries are not allowed")
                _require(info.date_time == ZIP_TIMESTAMP, member_label, "timestamp changed")
                _require(
                    info.compress_type == zipfile.ZIP_STORED,
                    member_label,
                    "compression method changed",
                )
                _require(info.create_system == 3, member_label, "creator system changed")
                _require(info.create_version == 20, member_label, "creator version changed")
                _require(info.extract_version == 20, member_label, "extract version changed")
                _require(info.flag_bits == 0, member_label, "ZIP flags changed")
                _require(info.internal_attr == 0, member_label, "internal attributes changed")
                _require(
                    info.external_attr == ZIP_EXTERNAL_ATTR,
                    member_label,
                    "file mode changed",
                )
                _require(info.extra == b"", member_label, "extra metadata is not empty")
                _require(info.comment == b"", member_label, "member comment is not empty")
                _require(info.volume == 0, member_label, "member volume changed")
                _require(info.file_size == len(expected), member_label, "file size changed")
                _require(
                    info.compress_size == len(expected),
                    member_label,
                    "stored size changed",
                )
                _require(
                    info.CRC == zlib.crc32(expected) & 0xFFFFFFFF,
                    member_label,
                    "CRC changed",
                )
                payload = archive.read(info)
                _require(payload == expected, member_label, "payload differs from snapshot")
                verified[info.filename] = payload
            return verified
    except VerificationError:
        raise
    except (KeyError, OSError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
        _fail(label, f"invalid ZIP: {exc}")


def _materialize_snapshots(root: Path, snapshots: dict[str, bytes]) -> None:
    for relative_name, payload in snapshots.items():
        destination = root / Path(relative_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)


def _publish_bundle(bundle_path: Path, archive_bytes: bytes) -> None:
    destination = bundle_path.absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    _require(not destination.is_symlink(), "artifact bundle", "destination is a symbolic link")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(archive_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
        _require(
            _file_bytes(destination, "published artifact bundle") == archive_bytes,
            "artifact bundle",
            "published bytes changed",
        )
    except VerificationError:
        raise
    except OSError as exc:
        _fail("artifact bundle", f"unable to publish atomically: {exc}")
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _digest(path: Path, label: str) -> str:
    return hashlib.sha256(_file_bytes(path, label)).hexdigest()


def _load_json(path: Path, label: str) -> object:
    return _parse_json(_file_bytes(path, label), label)


def _load_jsonl(path: Path, label: str) -> list[object]:
    raw = _file_bytes(path, label)
    _require(raw.endswith(b"\n"), label, "JSONL must end with a newline")
    lines = raw.splitlines()
    _require(bool(lines) and all(lines), label, "JSONL must contain no blank records")
    return [
        _parse_json(line, f"{label}[{index}]")
        for index, line in enumerate(lines, 1)
    ]


def _verify_manifest(
    directory: Path,
    manifest_name: str,
    schema: str,
    expected_outputs: dict[str, tuple[str, set[str]]],
    expected_inputs: dict[str, tuple[str, set[str]]] | None = None,
) -> tuple[dict[str, object], int]:
    directory = directory.resolve()
    label = f"manifest:{manifest_name}"
    manifest = _load_json(directory / manifest_name, label)
    _require(type(manifest) is dict, label, "root must be an object")
    _require(manifest.get("schema_version") == schema, label, "schema changed")
    outputs = manifest.get("outputs")
    _require(type(outputs) is dict, label, "outputs must be an object")
    _require(set(outputs) == set(expected_outputs), label, "output set changed")

    listed_files: set[str] = set()
    descriptor_sets = [("outputs", outputs, expected_outputs)]
    if expected_inputs is not None:
        inputs = manifest.get("inputs")
        _require(type(inputs) is dict, label, "inputs must be an object")
        _require(set(inputs) == set(expected_inputs), label, "input set changed")
        descriptor_sets.append(("inputs", inputs, expected_inputs))

    for group_name, descriptors, expected_descriptors in descriptor_sets:
        for key, (expected_file, expected_fields) in expected_descriptors.items():
            descriptor = descriptors[key]
            entry_label = f"{label}:{group_name}:{key}"
            _require(
                type(descriptor) is dict,
                entry_label,
                "descriptor must be an object",
            )
            _require(
                set(descriptor) == expected_fields,
                entry_label,
                "descriptor fields changed",
            )
            filename = descriptor.get("file")
            expected_sha = descriptor.get("sha256")
            _require(type(filename) is str, entry_label, "file must be a string")
            _require(filename == expected_file, entry_label, "file name changed")
            _require(Path(filename).name == filename, entry_label, "unsafe file name")
            _require(
                type(expected_sha) is str and SHA256_PATTERN.fullmatch(expected_sha),
                entry_label,
                "invalid SHA-256",
            )
            artifact_path = (directory / filename).resolve()
            _require(
                artifact_path.parent == directory,
                entry_label,
                "artifact escapes artifact directory",
            )
            _require(
                filename not in listed_files,
                entry_label,
                "duplicate artifact file",
            )
            listed_files.add(filename)
            _require(
                _digest(artifact_path, entry_label) == expected_sha,
                entry_label,
                "SHA-256 mismatch",
            )

    actual_entries = {path.name for path in directory.iterdir()}
    expected_entries = listed_files | {manifest_name}
    _require(
        actual_entries == expected_entries,
        label,
        "directory contains unlisted or missing entries",
    )
    for entry in directory.iterdir():
        _require(
            entry.is_file() and not entry.is_symlink(),
            label,
            f"unsafe directory entry: {entry.name}",
        )
    return manifest, len(outputs)


def _load_cases(
    path: Path,
    schema: str,
    label: str,
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    suite = _load_json(path, label)
    _require(
        type(suite) is dict and set(suite) == {"cases", "schema_version"},
        label,
        "suite fields changed",
    )
    _require(suite["schema_version"] == schema, label, "suite schema changed")
    cases = suite["cases"]
    _require(type(cases) is list and bool(cases), label, "suite must contain cases")
    _require(
        all(type(case) is dict for case in cases),
        label,
        "suite cases must be objects",
    )
    case_ids = [case.get("case_id") for case in cases]
    _require(
        all(type(case_id) is str for case_id in case_ids),
        label,
        "case IDs must be strings",
    )
    _require(
        len(case_ids) == len(set(case_ids)),
        label,
        "case IDs must be unique",
    )
    return cases, {case["case_id"]: case for case in cases}


def _load_bound_qrels(path: Path, *, evidence: Evidence) -> dict[str, tuple[str, ...]]:
    label = "retrieval qrels"
    document = _load_json(path, label)
    _require(
        type(document) is dict
        and set(document) == {"corpus_binding", "judgments", "schema_version"},
        label,
        "fields changed",
    )
    _require(
        document["schema_version"] == "hydra-governed-retrieval-qrels/v1",
        label,
        "schema changed",
    )

    binding = document["corpus_binding"]
    _require(
        type(binding) is dict
        and set(binding)
        == {"normalized_events_sha256", "pipeline_manifest_sha256", "record_ids"},
        label,
        "corpus binding fields changed",
    )
    _require(
        binding["normalized_events_sha256"] == evidence.normalized_sha256
        and binding["pipeline_manifest_sha256"] == evidence.manifest_sha256,
        label,
        "corpus digest binding mismatch",
    )
    record_ids = binding["record_ids"]
    expected_record_ids = sorted(event["event_id"] for event in evidence.accepted_events)
    _require(
        type(record_ids) is list
        and all(
            type(record_id) is str and SHA256_PATTERN.fullmatch(record_id)
            for record_id in record_ids
        )
        and record_ids == sorted(set(record_ids))
        and record_ids == expected_record_ids,
        label,
        "corpus record IDs do not match verified evidence",
    )

    judgments = document["judgments"]
    _require(
        type(judgments) is list and bool(judgments),
        label,
        "judgments must be a non-empty list",
    )
    qrels: dict[str, tuple[str, ...]] = {}
    accepted_record_ids = set(expected_record_ids)
    for index, judgment in enumerate(judgments, 1):
        judgment_label = f"{label}[{index}]"
        _require(
            type(judgment) is dict
            and set(judgment) == {"case_id", "relevant_record_ids"},
            judgment_label,
            "judgment fields changed",
        )
        case_id = judgment["case_id"]
        relevant_record_ids = judgment["relevant_record_ids"]
        _require(
            type(case_id) is str and bool(case_id) and case_id not in qrels,
            judgment_label,
            "case ID is invalid or duplicated",
        )
        _require(
            type(relevant_record_ids) is list
            and bool(relevant_record_ids)
            and all(
                type(record_id) is str and SHA256_PATTERN.fullmatch(record_id)
                for record_id in relevant_record_ids
            )
            and relevant_record_ids == sorted(set(relevant_record_ids))
            and set(relevant_record_ids).issubset(accepted_record_ids),
            judgment_label,
            "relevant record IDs are invalid",
        )
        qrels[case_id] = tuple(relevant_record_ids)
    return qrels


def _verify_report(
    path: Path,
    manifest: dict[str, object],
    expected_schema: str,
    expected_count: int,
    expected_dispositions: dict[str, int] | None,
    expected_check_keys: set[str],
    expected_static_checks: dict[str, object],
    label: str,
) -> dict[str, object]:
    report = _load_json(path, label)
    _require(type(report) is dict, label, "report must be an object")
    _require(
        set(report)
        == {
            "case_count",
            "checks",
            "disposition_counts",
            "failures",
            "input_binding",
            "schema_version",
            "status",
        },
        label,
        "report fields changed",
    )
    _require(report["schema_version"] == expected_schema, label, "schema changed")
    _require(report.get("status") == "PASS", label, "status is not PASS")
    _require(report.get("failures") == [], label, "report contains failures")
    _require(report.get("case_count") == expected_count, label, "case count changed")
    if expected_dispositions is not None:
        _require(
            report.get("disposition_counts") == expected_dispositions,
            label,
            "disposition counts changed",
        )
    _require(
        report.get("input_binding") == manifest["input_binding"],
        label,
        "manifest binding mismatch",
    )
    _require(type(report.get("checks")) is dict, label, "checks must be an object")
    _require(set(report["checks"]) == expected_check_keys, label, "check set changed")
    _require(
        all(report["checks"].get(key) == value for key, value in expected_static_checks.items()),
        label,
        "static checks changed",
    )
    return report


def _require_derived_report_values(
    report: dict[str, object],
    *,
    disposition_counts: dict[str, int],
    checks: dict[str, object],
    label: str,
) -> None:
    _require(
        report["disposition_counts"] == disposition_counts,
        label,
        "disposition counts do not match verified receipts",
    )
    report_checks = report["checks"]
    _require(type(report_checks) is dict, label, "checks must be an object")
    for key, expected in checks.items():
        _require(
            report_checks.get(key) == expected,
            label,
            f"{key} does not match verified receipts",
        )


def _format_fraction(value: Fraction) -> str:
    return f"{float(value):.6f}"


def _verify_domain_receipt(label: str, verifier: object, *args: object, **kwargs: object) -> None:
    try:
        verifier(*args, **kwargs)
    except (ContractError, IntegrityError) as exc:
        _fail(label, f"receipt verification failed: {exc}")


def verify_repository_artifacts(repository_root: Path) -> VerificationSummary:
    """Verify a repository tree reconstructed from captured artifact bytes."""

    root = repository_root.resolve()
    intelligence = root / "governed-intelligence-sample"
    pipeline = root / "market-data-pipeline-sample" / "build" / "demo"

    pipeline_manifest, pipeline_output_count = _verify_manifest(
        pipeline,
        "manifest.json",
        "hydra-market-pipeline-manifest/v2",
        {
            "normalized_events_csv": (
                "normalized_events.csv",
                {"file", "schema", "sha256"},
            ),
            "normalized_events_jsonl": (
                "normalized_events.jsonl",
                {"file", "sha256"},
            ),
            "quarantine_records_jsonl": (
                "quarantine_records.jsonl",
                {"file", "sha256"},
            ),
        },
        {
            "resolved_aliases_json": (
                "resolved_symbol_aliases.json",
                {"file", "schema_version", "sha256"},
            ),
            "source_csv": (
                "source_snapshot.csv",
                {"file", "schema_version", "sha256"},
            ),
        },
    )
    pipeline_inputs = pipeline_manifest["inputs"]
    _require(
        pipeline_inputs["source_csv"]["schema_version"]
        == "hydra-market-source-csv/v1",
        "pipeline manifest",
        "source snapshot schema changed",
    )
    _require(
        pipeline_inputs["resolved_aliases_json"]["schema_version"]
        == "hydra-market-resolved-aliases/v1",
        "pipeline manifest",
        "resolved aliases schema changed",
    )
    evaluation_dir = intelligence / "build" / "evaluation"
    evaluation_manifest, evaluation_output_count = _verify_manifest(
        evaluation_dir,
        "output_manifest.json",
        "hydra-governed-intelligence-output-manifest/v1",
        {
            "decisions_jsonl": ("decisions.jsonl", {"file", "sha256"}),
            "evaluation_report": (
                "evaluation_report.json",
                {"file", "sha256"},
            ),
        },
    )
    retrieval_dir = intelligence / "build" / "retrieval"
    retrieval_manifest, retrieval_output_count = _verify_manifest(
        retrieval_dir,
        "retrieval_output_manifest.json",
        "hydra-governed-retrieval-output-manifest/v3",
        {
            "retrieval_decisions_jsonl": (
                "retrieval_decisions.jsonl",
                {"file", "sha256"},
            ),
            "retrieval_evaluation_report": (
                "retrieval_evaluation_report.json",
                {"file", "sha256"},
            ),
        },
    )
    grounding_dir = intelligence / "build" / "grounding"
    grounding_manifest, grounding_output_count = _verify_manifest(
        grounding_dir,
        "grounding_output_manifest.json",
        "hydra-grounding-output-manifest/v1",
        {
            "grounding_evaluation_report": (
                "grounding_evaluation_report.json",
                {"file", "sha256"},
            ),
            "grounding_receipts_jsonl": (
                "grounding_receipts.jsonl",
                {"file", "sha256"},
            ),
        },
    )

    pipeline_manifest_path = pipeline / "manifest.json"
    normalized_sha = pipeline_manifest["outputs"]["normalized_events_jsonl"][
        "sha256"
    ]
    expected_evaluation_binding = {
        "evaluation_suite_sha256": _digest(
            intelligence / "fixtures" / "evaluation_cases.json",
            "evaluation suite",
        ),
        "pipeline_manifest_sha256": _digest(
            pipeline_manifest_path,
            "pipeline manifest",
        ),
        "policy_sha256": _digest(
            intelligence / "config" / "policy.json",
            "context policy",
        ),
    }
    expected_retrieval_binding = {
        "normalized_events_sha256": normalized_sha,
        "pipeline_manifest_sha256": _digest(
            pipeline_manifest_path,
            "pipeline manifest",
        ),
        "retrieval_policy_sha256": _digest(
            intelligence / "config" / "retrieval_policy.json",
            "retrieval policy",
        ),
        "retrieval_qrels_sha256": _digest(
            intelligence / "fixtures" / "retrieval_qrels.json",
            "retrieval qrels",
        ),
        "retrieval_suite_sha256": _digest(
            intelligence / "fixtures" / "retrieval_cases.json",
            "retrieval suite",
        ),
    }
    expected_grounding_binding = {
        "grounding_policy_sha256": _digest(
            intelligence / "config" / "grounding_policy.json",
            "grounding policy",
        ),
        "grounding_suite_sha256": _digest(
            intelligence / "fixtures" / "grounding_cases.json",
            "grounding suite",
        ),
        "pipeline_manifest_sha256": _digest(
            pipeline_manifest_path,
            "pipeline manifest",
        ),
        "retrieval_policy_sha256": _digest(
            intelligence / "config" / "retrieval_policy.json",
            "retrieval policy",
        ),
    }
    _require(
        evaluation_manifest.get("input_binding") == expected_evaluation_binding,
        "evaluation manifest",
        "input binding mismatch",
    )
    _require(
        retrieval_manifest.get("input_binding") == expected_retrieval_binding,
        "retrieval manifest",
        "input binding mismatch",
    )
    _require(
        grounding_manifest.get("input_binding") == expected_grounding_binding,
        "grounding manifest",
        "input binding mismatch",
    )

    _verify_report(
        evaluation_dir / "evaluation_report.json",
        evaluation_manifest,
        "hydra-governed-intelligence-evaluation-report/v1",
        5,
        {"ABSTAIN": 2, "ADMIT": 2, "REFUSE": 1},
        {
            "citation_integrity_pass_count",
            "disposition_match_count",
            "quarantined_raw_records_exposed_count",
            "unauthorized_model_execution_count",
        },
        {
            "citation_integrity_pass_count": 5,
            "disposition_match_count": 5,
            "quarantined_raw_records_exposed_count": 0,
            "unauthorized_model_execution_count": 0,
        },
        "evaluation report",
    )
    retrieval_report = _verify_report(
        retrieval_dir / "retrieval_evaluation_report.json",
        retrieval_manifest,
        "hydra-governed-retrieval-evaluation-report/v3",
        13,
        None,
        {
            "decision_verification_pass_count",
            "expectation_match_count",
            "citation_applicable_case_count",
            "citation_integrity_pass_case_count",
            "verified_citation_count",
            "citation_not_applicable_case_count",
            "quality_case_count",
            "qrel_case_count",
            "relevant_judgment_count",
            "retrieved_relevant_count",
            "recall_at_k",
            "micro_recall_at_k",
            "macro_recall_at_k",
            "mean_reciprocal_rank",
            "hard_negative_case_count",
            "hard_negative_false_admit_count",
            "unauthorized_model_execution_count",
            "quarantined_raw_records_exposed_count",
        },
        {
            "decision_verification_pass_count": 13,
            "expectation_match_count": 13,
            "citation_applicable_case_count": 4,
            "citation_integrity_pass_case_count": 4,
            "verified_citation_count": 4,
            "citation_not_applicable_case_count": 9,
            "quality_case_count": 6,
            "hard_negative_case_count": 4,
            "hard_negative_false_admit_count": 0,
            "unauthorized_model_execution_count": 0,
            "quarantined_raw_records_exposed_count": 0,
        },
        "retrieval report",
    )
    grounding_report = _verify_report(
        grounding_dir / "grounding_evaluation_report.json",
        grounding_manifest,
        "hydra-grounding-evaluation-report/v1",
        8,
        None,
        {
            "expectation_match_count",
            "grounding_integrity_pass_count",
            "claim_pass_count",
            "claim_fail_count",
            "candidate_execution_claim_rejected_count",
            "required_case_count",
            "required_case_total",
            "required_disposition_count",
            "required_disposition_total",
            "proof_coverage_status",
            "unauthorized_model_execution_count",
            "unauthorized_external_action_count",
            "quarantined_raw_records_exposed_count",
        },
        {
            "expectation_match_count": 8,
            "grounding_integrity_pass_count": 8,
            "candidate_execution_claim_rejected_count": 1,
            "required_case_count": 8,
            "required_case_total": 8,
            "required_disposition_count": 4,
            "required_disposition_total": 4,
            "proof_coverage_status": "PASS",
            "unauthorized_model_execution_count": 0,
            "unauthorized_external_action_count": 0,
            "quarantined_raw_records_exposed_count": 0,
        },
        "grounding report",
    )

    evidence = load_evidence(pipeline)
    input_snapshots_verified = len(pipeline_inputs)
    source_rows_replayed = pipeline_manifest.get("source_rows")
    _require(
        input_snapshots_verified == 2,
        "pipeline replay",
        "input snapshot count changed",
    )
    _require(
        source_rows_replayed == 7,
        "pipeline replay",
        "source row count changed",
    )
    context_policy = load_policy(intelligence / "config" / "policy.json")
    retrieval_policy = load_retrieval_policy(
        intelligence / "config" / "retrieval_policy.json"
    )
    grounding_policy = load_grounding_policy(
        intelligence / "config" / "grounding_policy.json"
    )

    context_cases, context_by_id = _load_cases(
        intelligence / "fixtures" / "evaluation_cases.json",
        "hydra-governed-intelligence-evaluation-suite/v1",
        "context suite",
    )
    context_records = _load_jsonl(
        evaluation_dir / "decisions.jsonl",
        "context receipts",
    )
    _require(
        [item.get("case_id") for item in context_records if type(item) is dict]
        == [case["case_id"] for case in context_cases],
        "context receipts",
        "case order or identity changed",
    )
    for item in context_records:
        _require(
            type(item) is dict and set(item) == {"case_id", "decision"},
            "context receipt",
            "record fields changed",
        )
        case = context_by_id[item["case_id"]]
        decision = item["decision"]
        request = case["request"]
        _require(
            {
                key: decision.get(key)
                for key in ("request_id", "subject", "task_type")
            }
            == request,
            item["case_id"],
            "request binding mismatch",
        )
        _verify_domain_receipt(
            item["case_id"],
            verify_decision,
            decision,
            evidence=evidence,
            policy=context_policy,
        )
        expected = case["expected"]
        _require(
            decision["disposition"] == expected["disposition"],
            item["case_id"],
            "disposition mismatch",
        )
        _require(
            expected["reason_code"] in decision["reason_codes"],
            item["case_id"],
            "reason code mismatch",
        )
        _require(
            len(decision["citations"]) == expected["citation_count"],
            item["case_id"],
            "citation count mismatch",
        )

    retrieval_cases, retrieval_by_id = _load_cases(
        intelligence / "fixtures" / "retrieval_cases.json",
        "hydra-governed-retrieval-evaluation-suite/v3",
        "retrieval suite",
    )
    retrieval_records = _load_jsonl(
        retrieval_dir / "retrieval_decisions.jsonl",
        "retrieval receipts",
    )
    _require(
        [item.get("case_id") for item in retrieval_records if type(item) is dict]
        == [case["case_id"] for case in retrieval_cases],
        "retrieval receipts",
        "case order or identity changed",
    )
    retrieval_disposition_counts = {"ABSTAIN": 0, "ADMIT": 0, "REFUSE": 0}
    ranked_record_ids_by_case: dict[str, list[str]] = {}
    for item in retrieval_records:
        _require(
            type(item) is dict
            and set(item) == {"case_id", "decision", "metric_group"},
            "retrieval receipt",
            "record fields changed",
        )
        case = retrieval_by_id[item["case_id"]]
        decision = item["decision"]
        request = case["request"]
        _require(
            item["metric_group"] == case["metric_group"],
            item["case_id"],
            "metric group mismatch",
        )
        _require(
            {key: decision.get(key) for key in ("query", "request_id", "top_k")}
            == request,
            item["case_id"],
            "request binding mismatch",
        )
        _verify_domain_receipt(
            item["case_id"],
            verify_retrieval_decision,
            decision,
            evidence=evidence,
            policy=retrieval_policy,
        )
        retrieval_disposition_counts[decision["disposition"]] += 1
        ranked_record_ids_by_case[item["case_id"]] = (
            []
            if decision["context"] is None
            else [
                result["record"]["event_id"]
                for result in decision["context"]["results"]
            ]
        )
        expected = case["expected"]
        ranked_symbols = (
            []
            if decision["context"] is None
            else [
                result["record"]["symbol"]
                for result in decision["context"]["results"]
            ]
        )
        _require(
            decision["disposition"] == expected["disposition"],
            item["case_id"],
            "disposition mismatch",
        )
        _require(
            expected["reason_code"] in decision["reason_codes"],
            item["case_id"],
            "reason code mismatch",
        )
        _require(
            ranked_symbols == expected["ranked_symbols"],
            item["case_id"],
            "ranking mismatch",
        )

    qrels = _load_bound_qrels(
        intelligence / "fixtures" / "retrieval_qrels.json",
        evidence=evidence,
    )
    quality_case_ids = {
        case["case_id"]
        for case in retrieval_cases
        if case["metric_group"] == "QUALITY"
    }
    _require(
        set(qrels) == quality_case_ids,
        "retrieval qrels",
        "case IDs do not match retrieval quality cases",
    )
    relevant_judgment_count = 0
    retrieved_relevant_count = 0
    macro_recall_total = Fraction(0, 1)
    reciprocal_rank_total = Fraction(0, 1)
    for case_id in quality_case_ids:
        relevant = set(qrels[case_id])
        ranked_record_ids = ranked_record_ids_by_case[case_id]
        per_case_hits = len(set(ranked_record_ids).intersection(relevant))
        relevant_judgment_count += len(relevant)
        retrieved_relevant_count += per_case_hits
        macro_recall_total += Fraction(per_case_hits, len(relevant))
        for rank, record_id in enumerate(ranked_record_ids, start=1):
            if record_id in relevant:
                reciprocal_rank_total += Fraction(1, rank)
                break
    qrel_case_count = len(qrels)
    micro_recall = Fraction(retrieved_relevant_count, relevant_judgment_count)
    macro_recall = macro_recall_total / qrel_case_count
    mean_reciprocal_rank = reciprocal_rank_total / qrel_case_count
    formatted_micro_recall = _format_fraction(micro_recall)
    derived_retrieval_checks = {
        "qrel_case_count": qrel_case_count,
        "relevant_judgment_count": relevant_judgment_count,
        "retrieved_relevant_count": retrieved_relevant_count,
        "recall_at_k": formatted_micro_recall,
        "micro_recall_at_k": formatted_micro_recall,
        "macro_recall_at_k": _format_fraction(macro_recall),
        "mean_reciprocal_rank": _format_fraction(mean_reciprocal_rank),
    }
    _require_derived_report_values(
        retrieval_report,
        disposition_counts=retrieval_disposition_counts,
        checks=derived_retrieval_checks,
        label="retrieval report",
    )
    _require(
        {
            key: derived_retrieval_checks[key]
            for key in PUBLISHED_RETRIEVAL_METRICS
        }
        == PUBLISHED_RETRIEVAL_METRICS,
        "retrieval report",
        "verified qrels metrics changed from the published baseline",
    )

    grounding_cases, grounding_by_id = _load_cases(
        intelligence / "fixtures" / "grounding_cases.json",
        "hydra-grounding-evaluation-suite/v1",
        "grounding suite",
    )
    grounding_records = _load_jsonl(
        grounding_dir / "grounding_receipts.jsonl",
        "grounding receipts",
    )
    _require(
        [item.get("case_id") for item in grounding_records if type(item) is dict]
        == [case["case_id"] for case in grounding_cases],
        "grounding receipts",
        "case order or identity changed",
    )
    grounding_disposition_counts = {
        "ABSTAIN": 0,
        "ADMIT": 0,
        "QUARANTINE": 0,
        "REFUSE": 0,
    }
    grounding_claim_pass_count = 0
    grounding_claim_fail_count = 0
    for item in grounding_records:
        _require(
            type(item) is dict and set(item) == {"case_id", "receipt"},
            "grounding receipt",
            "record fields changed",
        )
        case = grounding_by_id[item["case_id"]]
        receipt = item["receipt"]
        _verify_domain_receipt(
            item["case_id"],
            verify_grounding_receipt,
            receipt,
            retrieval_request=case["retrieval_request"],
            candidate=case["candidate"],
            evidence=evidence,
            retrieval_policy=retrieval_policy,
            grounding_policy=grounding_policy,
        )
        grounding_disposition_counts[receipt["disposition"]] += 1
        grounding_claim_pass_count += sum(
            result["status"] == "PASS" for result in receipt["claim_results"]
        )
        grounding_claim_fail_count += sum(
            result["status"] == "FAIL" for result in receipt["claim_results"]
        )
        expected = case["expected"]
        _require(
            receipt["disposition"] == expected["disposition"],
            item["case_id"],
            "disposition mismatch",
        )
        _require(
            receipt["reason_codes"] == expected["reason_codes"],
            item["case_id"],
            "reason codes mismatch",
        )
        _require(
            len(receipt["grounded_claims"]) == expected["grounded_claim_count"],
            item["case_id"],
            "grounded claim count mismatch",
        )

    _require_derived_report_values(
        grounding_report,
        disposition_counts=grounding_disposition_counts,
        checks={
            "claim_pass_count": grounding_claim_pass_count,
            "claim_fail_count": grounding_claim_fail_count,
        },
        label="grounding report",
    )

    manifest_outputs = (
        pipeline_output_count
        + evaluation_output_count
        + retrieval_output_count
        + grounding_output_count
    )
    receipt_count = (
        len(context_records) + len(retrieval_records) + len(grounding_records)
    )
    _require(
        manifest_outputs == 9,
        "artifact verification",
        "manifest output count changed",
    )
    _require(
        receipt_count == 26,
        "artifact verification",
        "receipt count changed",
    )
    return VerificationSummary(
        manifest_outputs=manifest_outputs,
        receipts=receipt_count,
        input_snapshots_verified=input_snapshots_verified,
        source_rows_replayed=source_rows_replayed,
    )


def package_repository_artifacts(
    repository_root: Path,
    bundle_path: Path,
) -> BundleSummary:
    """Snapshot, package, verify, and atomically publish the CI artifact bundle."""

    snapshots = _snapshot_verification_inputs(repository_root)
    archive_bytes = _build_bundle_bytes(snapshots)
    archived_members = _verify_bundle(archive_bytes, snapshots)

    verification_snapshots = {
        name: snapshots[name] for name in VERIFICATION_SUPPORT_FILES
    }
    verification_snapshots.update(archived_members)
    with tempfile.TemporaryDirectory(prefix="hydra-governed-proof-") as temp_directory:
        verification_root = Path(temp_directory)
        _materialize_snapshots(verification_root, verification_snapshots)
        verification = verify_repository_artifacts(verification_root)

    repository_root = repository_root.resolve()
    destination = bundle_path.absolute()
    input_paths = {
        (repository_root / Path(relative_name)).resolve()
        for relative_name in VERIFICATION_INPUTS
    }
    _require(
        destination.resolve() not in input_paths,
        "artifact bundle",
        "destination overlaps a verification input",
    )
    _publish_bundle(destination, archive_bytes)
    return BundleSummary(
        manifest_outputs=verification.manifest_outputs,
        receipts=verification.receipts,
        input_snapshots_verified=verification.input_snapshots_verified,
        source_rows_replayed=verification.source_rows_replayed,
        bundle_members=len(archived_members),
        bundle_bytes=len(archive_bytes),
        bundle_sha256=hashlib.sha256(archive_bytes).hexdigest(),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create and verify the deterministic governed-intelligence upload bundle."
        )
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root containing both governed and pipeline samples.",
    )
    parser.add_argument(
        "--bundle-path",
        type=Path,
        required=True,
        help="Destination for the atomically published deterministic ZIP bundle.",
    )
    parser.add_argument(
        "--github-output-path",
        type=Path,
        help="Optional GITHUB_OUTPUT file that receives bundle_sha256.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        summary = package_repository_artifacts(args.repository_root, args.bundle_path)
        if args.github_output_path is not None:
            _write_github_output(args.github_output_path, summary)
    except (VerificationError, ContractError, IntegrityError, OSError) as exc:
        print(f"PRE_UPLOAD_ARTIFACT_VERIFICATION=FAIL: {exc}", file=sys.stderr)
        return 1

    print("PRE_UPLOAD_ARTIFACT_VERIFICATION=PASS")
    print(f"MANIFEST_OUTPUTS_VERIFIED={summary.manifest_outputs}")
    print(f"RECEIPTS_VERIFIED={summary.receipts}")
    print(f"INPUT_SNAPSHOTS_VERIFIED={summary.input_snapshots_verified}")
    print(f"SOURCE_ROWS_REPLAYED={summary.source_rows_replayed}")
    print(f"BUNDLE_MEMBERS={summary.bundle_members}")
    print(f"BUNDLE_BYTES={summary.bundle_bytes}")
    print(f"BUNDLE_SHA256={summary.bundle_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
