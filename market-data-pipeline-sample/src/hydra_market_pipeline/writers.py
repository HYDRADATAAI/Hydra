"""Deterministic JSONL/manifest output and typed Parquet output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping

import pyarrow as pa
import pyarrow.parquet as pq

from .hashing import canonical_json_bytes, sha256_hex
from .models import PipelineResult


PARQUET_SCHEMA = pa.schema(
    [
        pa.field("currency", pa.string(), nullable=False),
        pa.field("event_id", pa.string(), nullable=False),
        pa.field("event_time_utc", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("price", pa.decimal128(18, 6), nullable=False),
        pa.field("raw_record_sha256", pa.string(), nullable=False),
        pa.field("source_file_sha256", pa.string(), nullable=False),
        pa.field("source_record_id", pa.string(), nullable=False),
        pa.field("source_row_number", pa.int64(), nullable=False),
        pa.field("source_system", pa.string(), nullable=False),
        pa.field("symbol", pa.string(), nullable=False),
        pa.field("transform_version", pa.string(), nullable=False),
        pa.field("venue", pa.string(), nullable=False),
        pa.field("volume", pa.int64(), nullable=False),
    ]
)


def write_outputs(result: PipelineResult, *, output_dir: str | Path) -> dict[str, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    normalized_jsonl = directory / "normalized_events.jsonl"
    quarantine_jsonl = directory / "quarantine_records.jsonl"
    normalized_parquet = directory / "normalized_events.parquet"
    manifest_path = directory / "manifest.json"

    _write_jsonl(normalized_jsonl, (event.json_record() for event in result.accepted))
    _write_jsonl(quarantine_jsonl, (record.json_record() for record in result.quarantined))

    table = pa.Table.from_pylist(
        [event.parquet_record() for event in result.accepted],
        schema=PARQUET_SCHEMA,
    )
    pq.write_table(
        table,
        normalized_parquet,
        compression="zstd",
        use_dictionary=False,
        write_statistics=True,
    )

    manifest = {
        "accepted_rows": len(result.accepted),
        "aliases_sha256": result.aliases_sha256,
        "outputs": {
            "normalized_events_jsonl": {
                "file": normalized_jsonl.name,
                "sha256": sha256_hex(normalized_jsonl.read_bytes()),
            },
            "normalized_events_parquet": {
                "file": normalized_parquet.name,
                "rows": table.num_rows,
                "schema": [field.name for field in PARQUET_SCHEMA],
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
        "normalized_jsonl": normalized_jsonl,
        "normalized_parquet": normalized_parquet,
        "quarantine_jsonl": quarantine_jsonl,
    }


def _write_jsonl(path: Path, records: Iterable[Mapping[str, object]]) -> None:
    with path.open("wb") as handle:
        for record in records:
            handle.write(canonical_json_bytes(record))
            handle.write(b"\n")
