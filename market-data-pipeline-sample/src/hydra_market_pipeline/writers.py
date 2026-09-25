"""Deterministic JSONL, CSV, quarantine, and manifest output."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping

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


def write_outputs(result: PipelineResult, *, output_dir: str | Path) -> dict[str, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    normalized_jsonl = directory / "normalized_events.jsonl"
    normalized_csv = directory / "normalized_events.csv"
    quarantine_jsonl = directory / "quarantine_records.jsonl"
    manifest_path = directory / "manifest.json"

    _write_jsonl(normalized_jsonl, (event.json_record() for event in result.accepted))
    _write_csv(normalized_csv, (event.json_record() for event in result.accepted))
    _write_jsonl(quarantine_jsonl, (record.json_record() for record in result.quarantined))

    manifest = {
        "accepted_rows": len(result.accepted),
        "aliases_sha256": result.aliases_sha256,
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
        "schema_version": "hydra-market-pipeline-manifest/v1",
        "source_file_sha256": result.source_file_sha256,
        "transform_version": result.transform_version,
    }
    manifest_path.write_bytes(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )

    return {
        "manifest": manifest_path,
        "normalized_csv": normalized_csv,
        "normalized_jsonl": normalized_jsonl,
        "quarantine_jsonl": quarantine_jsonl,
    }


def _write_jsonl(path: Path, records: Iterable[Mapping[str, object]]) -> None:
    with path.open("wb") as handle:
        for record in records:
            handle.write(canonical_json_bytes(record))
            handle.write(b"\n")


def _write_csv(path: Path, records: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=NORMALIZED_CSV_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        for record in records:
            writer.writerow({column: record[column] for column in NORMALIZED_CSV_COLUMNS})
