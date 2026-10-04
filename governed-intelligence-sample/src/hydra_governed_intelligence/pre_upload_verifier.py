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


@dataclass(frozen=True)
class BundleSummary:
    manifest_outputs: int
    receipts: int
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
            not stat.S_ISLNK(path_before.st_mode),
            label,
            "symbolic links are not allowed",
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
                and stat.S_ISREG(path_after.st_mode),
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


def _write_github_output(path: Path, bundle_sha256: str) -> None:
    _require(
        SHA256_PATTERN.fullmatch(bundle_sha256) is not None,
        "GitHub step output",
        "bundle SHA-256 is invalid",
    )
    payload = f"bundle_sha256={bundle_sha256}\n".encode("ascii")
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
    root = repository_root.resolve()
    _require(root.is_dir(), "artifact snapshots", "repository root is missing")

    expected_by_directory: dict[str, set[str]] = {}
    for member in BUNDLE_MEMBERS:
        member_path = Path(member)
        expected_by_directory.setdefault(member_path.parent.as_posix(), set()).add(
            member_path.name
        )
    for directory_name, expected_names in expected_by_directory.items():
        directory = root / Path(directory_name)
        _require(directory.is_dir(), directory_name, "artifact directory is missing")
        try:
            actual_names = {entry.name for entry in directory.iterdir()}
        except OSError as exc:
            _fail(directory_name, f"unable to enumerate artifact directory: {exc}")
        _require(
            actual_names == expected_names,
            directory_name,
            "directory contains unlisted or missing entries",
        )

    snapshots: dict[str, bytes] = {}
    for relative_name in VERIFICATION_INPUTS:
        _require(relative_name.isascii(), relative_name, "path must be ASCII")
        _require("\\" not in relative_name, relative_name, "path must use POSIX separators")
        relative_path = Path(relative_name)
        _require(
            not relative_path.is_absolute() and ".." not in relative_path.parts,
            relative_name,
            "unsafe verification input path",
        )
        snapshots[relative_name] = _snapshot_file(
            root / relative_path,
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
    for key, (expected_file, expected_fields) in expected_outputs.items():
        descriptor = outputs[key]
        entry_label = f"{label}:{key}"
        _require(type(descriptor) is dict, entry_label, "descriptor must be an object")
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
        output_path = (directory / filename).resolve()
        _require(
            output_path.parent == directory,
            entry_label,
            "output escapes artifact directory",
        )
        _require(filename not in listed_files, entry_label, "duplicate output file")
        listed_files.add(filename)
        _require(
            _digest(output_path, entry_label) == expected_sha,
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
        "hydra-market-pipeline-manifest/v1",
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
    return VerificationSummary(manifest_outputs=manifest_outputs, receipts=receipt_count)


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
            _write_github_output(args.github_output_path, summary.bundle_sha256)
    except (VerificationError, ContractError, IntegrityError, OSError) as exc:
        print(f"PRE_UPLOAD_ARTIFACT_VERIFICATION=FAIL: {exc}", file=sys.stderr)
        return 1

    print("PRE_UPLOAD_ARTIFACT_VERIFICATION=PASS")
    print(f"MANIFEST_OUTPUTS_VERIFIED={summary.manifest_outputs}")
    print(f"RECEIPTS_VERIFIED={summary.receipts}")
    print(f"BUNDLE_MEMBERS={summary.bundle_members}")
    print(f"BUNDLE_BYTES={summary.bundle_bytes}")
    print(f"BUNDLE_SHA256={summary.bundle_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
