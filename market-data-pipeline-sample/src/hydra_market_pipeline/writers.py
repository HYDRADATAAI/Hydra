"""Deterministic JSONL, CSV, quarantine, and manifest output."""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from .atomic import write_atomically as _write_atomically

from .hashing import canonical_json_bytes, sha256_hex
from .models import PipelineResult


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
MANIFEST_SCHEMA = "hydra-market-pipeline-manifest/v2"
SOURCE_SNAPSHOT_SCHEMA = "hydra-market-source-csv/v1"
RESOLVED_ALIASES_SCHEMA = "hydra-market-resolved-aliases/v1"


class OutputPathError(ValueError):
    """Raised when the requested output directory traverses a symlink or junction."""


def _contains_unsafe_symlink_component(path: Path) -> bool:
    """Detect pre-existing symlinked path components without following them silently."""
    if not path.is_absolute():
        path = Path.cwd() / path

    parts = path.parts
    current = Path(parts[0])
    for part in parts[1:]:
        current /= part
        if part == "..":
            continue
        resolved = current.resolve(strict=False)
        normalized = Path(os.path.normpath(os.fspath(current)))
        if os.path.normcase(os.fspath(resolved)) == os.path.normcase(
            os.fspath(normalized)
        ):
            continue

        macos_aliases = {
            Path("/var"): Path("/private/var"),
            Path("/tmp"): Path("/private/tmp"),
        }
        is_macos_alias = False
        if sys.platform == "darwin":
            for alias, target in macos_aliases.items():
                try:
                    relative_path = current.relative_to(alias)
                except ValueError:
                    continue
                expected = Path(os.path.normpath(os.fspath(target / relative_path)))
                is_macos_alias = os.path.normcase(
                    os.fspath(resolved)
                ) == os.path.normcase(os.fspath(expected))
                break
        if not is_macos_alias:
            return True
    return False


def write_outputs(result: PipelineResult, *, output_dir: str | Path) -> dict[str, Path]:
    directory = Path(output_dir)
    if _contains_unsafe_symlink_component(directory):
        raise OutputPathError("output directory path must not contain symlinks")
    directory = directory.resolve(strict=False)
    directory.mkdir(parents=True, exist_ok=True)

    normalized_jsonl = directory / "normalized_events.jsonl"
    normalized_csv = directory / "normalized_events.csv"
    quarantine_jsonl = directory / "quarantine_records.jsonl"
    source_snapshot = directory / "source_snapshot.csv"
    resolved_aliases_json = directory / "resolved_symbol_aliases.json"
    manifest_path = directory / "manifest.json"

    _write_jsonl(normalized_jsonl, (event.json_record() for event in result.accepted))
    _write_csv(normalized_csv, (event.json_record() for event in result.accepted))
    _write_jsonl(quarantine_jsonl, (record.json_record() for record in result.quarantined))
    _write_bytes(source_snapshot, result.source_csv_bytes)
    _write_bytes(resolved_aliases_json, canonical_json_bytes(dict(result.resolved_aliases)))

    source_snapshot_sha256 = sha256_hex(source_snapshot.read_bytes())
    resolved_aliases_sha256 = sha256_hex(resolved_aliases_json.read_bytes())
    if source_snapshot_sha256 != result.source_file_sha256:
        raise ValueError("source snapshot digest does not match the pipeline result")
    if resolved_aliases_sha256 != result.aliases_sha256:
        raise ValueError("resolved aliases digest does not match the pipeline result")

    manifest = {
        "accepted_rows": len(result.accepted),
        "aliases_sha256": result.aliases_sha256,
        "inputs": {
            "resolved_aliases_json": {
                "file": resolved_aliases_json.name,
                "schema_version": RESOLVED_ALIASES_SCHEMA,
                "sha256": resolved_aliases_sha256,
            },
            "source_csv": {
                "file": source_snapshot.name,
                "schema_version": SOURCE_SNAPSHOT_SCHEMA,
                "sha256": source_snapshot_sha256,
            },
        },
        "outputs": {
            "normalized_events_jsonl": {
                "file": normalized_jsonl.name,
                "sha256": sha256_hex(normalized_jsonl.read_bytes()),
            },
            "normalized_events_csv": {
                "file": normalized_csv.name,
                "schema": list(NORMALIZED_CSV_COLUMNS),
                "sha256": sha256_hex(normalized_csv.read_bytes()),
            },
            "quarantine_records_jsonl": {
                "file": quarantine_jsonl.name,
                "sha256": sha256_hex(quarantine_jsonl.read_bytes()),
            },
        },
        "pipeline_run_id": result.pipeline_run_id,
        "quarantined_rows": len(result.quarantined),
        "schema_version": MANIFEST_SCHEMA,
        "source_file_sha256": result.source_file_sha256,
        "source_rows": len(result.accepted) + len(result.quarantined),
        "transform_version": result.transform_version,
    }
    _write_bytes(
        manifest_path,
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
        + b"\\n",
    )

    return {
        "manifest": manifest_path,
        "normalized_csv": normalized_csv,
        "normalized_jsonl": normalized_jsonl,
        "quarantine_jsonl": quarantine_jsonl,
        "resolved_aliases_json": resolved_aliases_json,
        "source_snapshot": source_snapshot,
    }


def _write_bytes(path: Path, content: bytes) -> None:
    _write_atomically(path, "wb", lambda handle: handle.write(content))


def _write_jsonl(path: Path, records: Iterable[Mapping[str, object]]) -> None:
    def write_records(handle: Any) -> None:
        for record in records:
            handle.write(canonical_json_bytes(record))
            handle.write(b"\\n")

    _write_atomically(path, "wb", write_records)


def _write_csv(path: Path, records: Iterable[Mapping[str, object]]) -> None:
    def write_records(handle: Any) -> None:
        writer = csv.DictWriter(
            handle,
            fieldnames=NORMALIZED_CSV_COLUMNS,
            lineterminator="\\n",
        )
        writer.writeheader()
        for record in records:
            writer.writerow({column: record[column] for column in NORMALIZED_CSV_COLUMNS})

    _write_atomically(path, "w", write_records, newline="", encoding="utf-8")
