"""Checkpointed, deterministic operations around the synthetic pipeline."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Mapping

from .hashing import canonical_json_bytes, object_sha256, sha256_hex
from .pipeline import (
    RUN_SCHEMA,
    TRANSFORM_VERSION,
    load_aliases,
    parse_aliases_bytes,
    run_pipeline,
)
from .writers import (
    MANIFEST_SCHEMA,
    NORMALIZED_CSV_COLUMNS,
    RESOLVED_ALIASES_SCHEMA,
    SOURCE_SNAPSHOT_SCHEMA,
    write_outputs,
)


PLAN_SCHEMA = "hydra-market-backfill-plan/v1"
CHECKPOINT_SCHEMA = "hydra-market-backfill-checkpoint/v2"
OPERATIONS_MANIFEST_SCHEMA = "hydra-market-operations-manifest/v1"
SOURCE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
ROOT_PLAN_KEYS = {
    "inputs",
    "max_partitions",
    "max_total_source_bytes",
    "schema_version",
}
INPUT_PLAN_KEYS = {"path", "source_id"}
PIPELINE_ARTIFACT_FILES = (
    "manifest.json",
    "resolved_symbol_aliases.json",
    "source_snapshot.csv",
    "normalized_events.csv",
    "normalized_events.jsonl",
    "quarantine_records.jsonl",
)


class OperationsError(ValueError):
    """Raised when an operational contract or persisted state fails closed."""


class InjectedInterruption(RuntimeError):
    """Synthetic interruption used only to prove checkpoint recovery."""


@dataclass(frozen=True)
class PlannedInput:
    source_id: str
    path: Path
    source_file_sha256: str
    source_bytes: int


@dataclass(frozen=True)
class BackfillPlan:
    backfill_id: str
    aliases_sha256: str
    max_partitions: int
    max_total_source_bytes: int
    inputs: tuple[PlannedInput, ...]


@dataclass(frozen=True)
class BackfillOutcome:
    backfill_id: str
    manifest_path: Path
    metrics_path: Path
    processed_sources: tuple[str, ...]
    reused_sources: tuple[str, ...]


def load_backfill_plan(
    *,
    plan_path: str | Path,
    aliases_path: str | Path,
) -> BackfillPlan:
    path = Path(plan_path).resolve()
    plan = _load_strict_json(path, "backfill plan")
    if not isinstance(plan, dict):
        raise OperationsError("backfill plan must be a JSON object")
    _require_exact_keys(plan, ROOT_PLAN_KEYS, "backfill plan")
    if plan["schema_version"] != PLAN_SCHEMA:
        raise OperationsError(f"unsupported backfill plan schema: {plan['schema_version']!r}")

    max_partitions = _positive_int(plan["max_partitions"], "max_partitions")
    max_total_source_bytes = _positive_int(
        plan["max_total_source_bytes"],
        "max_total_source_bytes",
    )
    raw_inputs = plan["inputs"]
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise OperationsError("backfill plan inputs must be a non-empty array")
    if len(raw_inputs) > max_partitions:
        raise OperationsError(
            f"partition budget exceeded: planned={len(raw_inputs)}, "
            f"maximum={max_partitions}"
        )

    sample_root = path.parent.parent.resolve()
    inputs: list[PlannedInput] = []
    source_ids: set[str] = set()
    resolved_paths: set[Path] = set()
    for index, raw_input in enumerate(raw_inputs):
        label = f"backfill plan input {index}"
        if not isinstance(raw_input, dict):
            raise OperationsError(f"{label} must be a JSON object")
        _require_exact_keys(raw_input, INPUT_PLAN_KEYS, label)

        source_id = raw_input["source_id"]
        relative_path = raw_input["path"]
        if not isinstance(source_id, str) or not SOURCE_ID_PATTERN.fullmatch(source_id):
            raise OperationsError(f"{label} source_id is invalid")
        if source_id in source_ids:
            raise OperationsError(f"duplicate source_id in backfill plan: {source_id}")
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise OperationsError(f"{label} path must be a non-empty string")

        source_path = (path.parent / relative_path).resolve()
        try:
            source_path.relative_to(sample_root)
        except ValueError as exc:
            raise OperationsError(f"{label} path escapes the sample root") from exc
        if not source_path.is_file():
            raise OperationsError(f"{label} source file does not exist")
        if source_path in resolved_paths:
            raise OperationsError(f"duplicate source path in backfill plan: {relative_path}")

        source_bytes = source_path.read_bytes()
        inputs.append(
            PlannedInput(
                source_id=source_id,
                path=source_path,
                source_file_sha256=sha256_hex(source_bytes),
                source_bytes=len(source_bytes),
            )
        )
        source_ids.add(source_id)
        resolved_paths.add(source_path)

    observed_source_bytes = sum(item.source_bytes for item in inputs)
    if observed_source_bytes > max_total_source_bytes:
        raise OperationsError(
            f"source-byte budget exceeded: observed={observed_source_bytes}, "
            f"maximum={max_total_source_bytes}"
        )

    _, aliases_sha256 = load_aliases(aliases_path)
    identity = {
        "aliases_sha256": aliases_sha256,
        "inputs": [
            {
                "source_file_sha256": item.source_file_sha256,
                "source_id": item.source_id,
            }
            for item in sorted(inputs, key=lambda item: item.source_id)
        ],
        "max_partitions": max_partitions,
        "max_total_source_bytes": max_total_source_bytes,
        "schema_version": PLAN_SCHEMA,
    }
    return BackfillPlan(
        backfill_id=object_sha256(identity),
        aliases_sha256=aliases_sha256,
        max_partitions=max_partitions,
        max_total_source_bytes=max_total_source_bytes,
        inputs=tuple(sorted(inputs, key=lambda item: item.source_id)),
    )



def _contains_unsafe_symlink_component(path: Path) -> bool:
    current = path
    while current != current.parent:
        if current.is_symlink():
            resolved = current.resolve(strict=False)
            macos_aliases = {
                Path("/var"): Path("/private/var"),
                Path("/tmp"): Path("/private/tmp"),
            }
            if macos_aliases.get(current) != resolved:
                return True
        current = current.parent
    return False

def execute_backfill(
    *,
    plan_path: str | Path,
    aliases_path: str | Path,
    output_dir: str | Path,
    interrupt_after_new_sources: int | None = None,
) -> BackfillOutcome:
    if interrupt_after_new_sources is not None and interrupt_after_new_sources < 1:
        raise OperationsError("interrupt_after_new_sources must be at least one")

    plan = load_backfill_plan(plan_path=plan_path, aliases_path=aliases_path)
    output_root = Path(output_dir)
    absolute_output_root = Path(os.path.abspath(output_root))
    if _contains_unsafe_symlink_component(absolute_output_root):
        raise OperationsError("output directory path must not contain symlinks")
    runs_root = output_root / "runs"
    checkpoint_path = output_root / "checkpoint.json"
    manifest_path = output_root / "operations_manifest.json"
    metrics_path = output_root / "metrics.jsonl"
    runs_root.mkdir(parents=True, exist_ok=True)

    checkpoint = _load_or_create_checkpoint(checkpoint_path, plan)
    completed = checkpoint["completed"]
    assert isinstance(completed, dict)
    _verify_completed_sources(plan, completed, runs_root)

    reused_sources = [
        item.source_id for item in plan.inputs if item.source_id in completed
    ]
    processed_sources: list[str] = []
    for item in plan.inputs:
        if item.source_id in completed:
            continue

        result = run_pipeline(input_csv=item.path, aliases_path=aliases_path)
        if result.source_file_sha256 != item.source_file_sha256:
            raise OperationsError(f"source changed while processing: {item.source_id}")
        if result.aliases_sha256 != plan.aliases_sha256:
            raise OperationsError(f"aliases changed while processing: {item.source_id}")
        run_dir = runs_root / result.pipeline_run_id
        _verify_run_paths_before_write(run_dir)
        outputs = write_outputs(result, output_dir=run_dir)
        manifest_sha256 = sha256_hex(outputs["manifest"].read_bytes())
        completed[item.source_id] = {
            "accepted_rows": len(result.accepted),
            "aliases_sha256": result.aliases_sha256,
            "manifest_sha256": manifest_sha256,
            "pipeline_run_id": result.pipeline_run_id,
            "quarantined_rows": len(result.quarantined),
            "source_file_sha256": result.source_file_sha256,
            "source_rows": len(result.accepted) + len(result.quarantined),
        }
        _write_json_atomic(checkpoint_path, checkpoint)
        _verify_pipeline_artifacts(run_dir, completed[item.source_id])
        processed_sources.append(item.source_id)

        if (
            interrupt_after_new_sources is not None
            and len(processed_sources) >= interrupt_after_new_sources
        ):
            raise InjectedInterruption(
                f"synthetic interruption after {len(processed_sources)} source(s)"
            )

    _verify_completed_sources(plan, completed, runs_root)
    operations_manifest = _build_operations_manifest(plan, completed)
    _write_json_atomic(manifest_path, operations_manifest)
    _write_metrics(metrics_path, operations_manifest)
    return BackfillOutcome(
        backfill_id=plan.backfill_id,
        manifest_path=manifest_path,
        metrics_path=metrics_path,
        processed_sources=tuple(processed_sources),
        reused_sources=tuple(reused_sources),
    )


def _load_or_create_checkpoint(path: Path, plan: BackfillPlan) -> dict[str, object]:
    if path.is_symlink():
        raise OperationsError("checkpoint must not be a symlink")
    if not path.exists():
        checkpoint: dict[str, object] = {
            "backfill_id": plan.backfill_id,
            "completed": {},
            "schema_version": CHECKPOINT_SCHEMA,
        }
        _write_json_atomic(path, checkpoint)
        return checkpoint

    checkpoint = _load_strict_json(path, "checkpoint")
    if not isinstance(checkpoint, dict):
        raise OperationsError("checkpoint must be a JSON object")
    _require_exact_keys(
        checkpoint,
        {"backfill_id", "completed", "schema_version"},
        "checkpoint",
    )
    if checkpoint["schema_version"] != CHECKPOINT_SCHEMA:
        raise OperationsError("checkpoint schema is unsupported")
    if checkpoint["backfill_id"] != plan.backfill_id:
        raise OperationsError("checkpoint does not belong to the current pinned plan")
    if not isinstance(checkpoint["completed"], dict):
        raise OperationsError("checkpoint completed field must be an object")
    return checkpoint


def _verify_run_paths_before_write(run_dir: Path) -> None:
    if run_dir.is_symlink():
        raise OperationsError(f"persisted run directory must not be a symlink: {run_dir.name}")
    if run_dir.exists() and not run_dir.is_dir():
        raise OperationsError(f"persisted run directory is not a directory: {run_dir.name}")
    for file_name in PIPELINE_ARTIFACT_FILES:
        if (run_dir / file_name).is_symlink():
            raise OperationsError(f"persisted run artifact must not be a symlink: {file_name}")


def _verify_completed_sources(
    plan: BackfillPlan,
    completed: Mapping[str, object],
    runs_root: Path,
) -> None:
    planned = {item.source_id: item for item in plan.inputs}
    unexpected = sorted(set(completed) - set(planned))
    if unexpected:
        raise OperationsError(f"checkpoint contains unplanned sources: {unexpected}")

    if runs_root.is_symlink() or not runs_root.is_dir():
        raise OperationsError("persisted runs directory is missing or invalid")

    for source_id, raw_entry in completed.items():
        if not isinstance(raw_entry, dict):
            raise OperationsError(f"checkpoint entry is invalid: {source_id}")
        _require_exact_keys(
            raw_entry,
            {
                "accepted_rows",
                "aliases_sha256",
                "manifest_sha256",
                "pipeline_run_id",
                "quarantined_rows",
                "source_file_sha256",
                "source_rows",
            },
            f"checkpoint entry {source_id}",
        )
        for count_name in ("accepted_rows", "quarantined_rows", "source_rows"):
            count = raw_entry[count_name]
            if type(count) is not int or count < 0:
                raise OperationsError(
                    f"checkpoint {count_name} is invalid: {source_id}"
                )
        if (
            raw_entry["accepted_rows"] + raw_entry["quarantined_rows"]
            != raw_entry["source_rows"]
        ):
            raise OperationsError(f"checkpoint row accounting mismatch: {source_id}")
        if raw_entry["source_file_sha256"] != planned[source_id].source_file_sha256:
            raise OperationsError(f"checkpoint source digest mismatch: {source_id}")
        if raw_entry["aliases_sha256"] != plan.aliases_sha256:
            raise OperationsError(f"checkpoint aliases digest mismatch: {source_id}")
        for digest_name in (
            "aliases_sha256",
            "manifest_sha256",
            "source_file_sha256",
        ):
            digest = raw_entry[digest_name]
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise OperationsError(
                    f"checkpoint {digest_name} is invalid: {source_id}"
                )
        run_id = raw_entry["pipeline_run_id"]
        if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{64}", run_id):
            raise OperationsError(f"checkpoint pipeline run ID is invalid: {source_id}")
        _verify_pipeline_artifacts(runs_root / run_id, raw_entry)


def _verify_pipeline_artifacts(run_dir: Path, checkpoint_entry: Mapping[str, object]) -> None:
    if run_dir.is_symlink() or not run_dir.is_dir():
        raise OperationsError(f"persisted run directory is missing or invalid: {run_dir.name}")
    manifest_path = run_dir / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise OperationsError(f"persisted run manifest is missing or invalid: {run_dir.name}")
    manifest_bytes = manifest_path.read_bytes()
    if sha256_hex(manifest_bytes) != checkpoint_entry["manifest_sha256"]:
        raise OperationsError(f"persisted run manifest digest mismatch: {run_dir.name}")

    manifest = _load_strict_json_bytes(manifest_bytes, "pipeline manifest")
    if not isinstance(manifest, dict):
        raise OperationsError("pipeline manifest must be a JSON object")
    _require_exact_keys(
        manifest,
        {
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
        },
        "pipeline manifest",
    )
    if manifest["schema_version"] != MANIFEST_SCHEMA:
        raise OperationsError(f"persisted pipeline manifest schema mismatch: {run_dir.name}")
    for count_name in ("accepted_rows", "quarantined_rows", "source_rows"):
        count = manifest[count_name]
        if type(count) is not int or count < 0:
            raise OperationsError(f"persisted {count_name} is invalid: {run_dir.name}")
    if (
        manifest["accepted_rows"] + manifest["quarantined_rows"]
        != manifest["source_rows"]
    ):
        raise OperationsError(f"persisted source row accounting mismatch: {run_dir.name}")
    for digest_name in ("aliases_sha256", "pipeline_run_id", "source_file_sha256"):
        digest = manifest[digest_name]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise OperationsError(f"persisted {digest_name} is invalid: {run_dir.name}")
    if manifest["transform_version"] != TRANSFORM_VERSION:
        raise OperationsError(f"persisted transform version mismatch: {run_dir.name}")
    if manifest.get("pipeline_run_id") != checkpoint_entry["pipeline_run_id"]:
        raise OperationsError(f"persisted pipeline run ID mismatch: {run_dir.name}")
    if manifest.get("accepted_rows") != checkpoint_entry["accepted_rows"]:
        raise OperationsError(f"persisted accepted count mismatch: {run_dir.name}")
    if manifest.get("quarantined_rows") != checkpoint_entry["quarantined_rows"]:
        raise OperationsError(f"persisted quarantine count mismatch: {run_dir.name}")
    if manifest.get("source_rows") != checkpoint_entry["source_rows"]:
        raise OperationsError(f"persisted source row count mismatch: {run_dir.name}")
    if manifest.get("source_file_sha256") != checkpoint_entry["source_file_sha256"]:
        raise OperationsError(f"persisted source digest mismatch: {run_dir.name}")
    if manifest.get("aliases_sha256") != checkpoint_entry["aliases_sha256"]:
        raise OperationsError(f"persisted aliases digest mismatch: {run_dir.name}")

    expected_inputs = {
        "resolved_aliases_json": {
            "file": "resolved_symbol_aliases.json",
            "schema_version": RESOLVED_ALIASES_SCHEMA,
            "sha256": manifest.get("aliases_sha256"),
        },
        "source_csv": {
            "file": "source_snapshot.csv",
            "schema_version": SOURCE_SNAPSHOT_SCHEMA,
            "sha256": manifest.get("source_file_sha256"),
        },
    }
    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != set(expected_inputs):
        raise OperationsError(f"persisted input contract mismatch: {run_dir.name}")
    for name, expected_descriptor in expected_inputs.items():
        descriptor = inputs[name]
        if not isinstance(descriptor, dict) or descriptor != expected_descriptor:
            raise OperationsError(f"persisted input descriptor mismatch: {name}")
        artifact_path = run_dir / expected_descriptor["file"]
        if artifact_path.is_symlink() or not artifact_path.is_file():
            raise OperationsError(f"persisted input is missing or invalid: {artifact_path.name}")
        artifact_bytes = artifact_path.read_bytes()
        if sha256_hex(artifact_bytes) != expected_descriptor["sha256"]:
            raise OperationsError(f"persisted input digest mismatch: {artifact_path.name}")
        if name == "source_csv":
            try:
                source_text = artifact_bytes.decode("utf-8-sig")
                source_rows = sum(
                    1 for _ in csv.DictReader(io.StringIO(source_text, newline=""))
                )
            except (UnicodeDecodeError, csv.Error) as exc:
                raise OperationsError("persisted source snapshot is invalid CSV") from exc
            if source_rows != manifest["source_rows"]:
                raise OperationsError("persisted source snapshot row count mismatch")
        elif name == "resolved_aliases_json":
            try:
                normalized_aliases, aliases_sha256 = parse_aliases_bytes(artifact_bytes)
            except ValueError as exc:
                raise OperationsError("persisted resolved aliases snapshot is invalid") from exc
            if canonical_json_bytes(normalized_aliases) != artifact_bytes:
                raise OperationsError("persisted resolved aliases snapshot is not normalized")
            if aliases_sha256 != manifest["aliases_sha256"]:
                raise OperationsError("persisted resolved aliases digest mismatch")

    expected_pipeline_run_id = object_sha256(
        {
            "aliases_sha256": manifest["aliases_sha256"],
            "run_schema": RUN_SCHEMA,
            "source_file_sha256": manifest["source_file_sha256"],
            "transform_version": manifest["transform_version"],
        }
    )
    if manifest["pipeline_run_id"] != expected_pipeline_run_id:
        raise OperationsError(f"persisted pipeline run identity mismatch: {run_dir.name}")

    expected_outputs = {
        "normalized_events_csv": {
            "file": "normalized_events.csv",
            "schema": list(NORMALIZED_CSV_COLUMNS),
        },
        "normalized_events_jsonl": {"file": "normalized_events.jsonl"},
        "quarantine_records_jsonl": {"file": "quarantine_records.jsonl"},
    }
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict) or set(outputs) != set(expected_outputs):
        raise OperationsError(f"persisted output contract mismatch: {run_dir.name}")
    for name, expected_descriptor in expected_outputs.items():
        descriptor = outputs[name]
        if not isinstance(descriptor, dict):
            raise OperationsError(f"persisted output descriptor is invalid: {run_dir.name}")
        expected_keys = set(expected_descriptor) | {"sha256"}
        if set(descriptor) != expected_keys:
            raise OperationsError(f"persisted output descriptor keys mismatch: {name}")
        for key, expected_value in expected_descriptor.items():
            if descriptor.get(key) != expected_value:
                raise OperationsError(f"persisted output descriptor mismatch: {name}")
        file_name = descriptor.get("file")
        expected_sha256 = descriptor.get("sha256")
        if (
            not isinstance(file_name, str)
            or Path(file_name).name != file_name
            or not isinstance(expected_sha256, str)
        ):
            raise OperationsError(f"persisted output descriptor is unsafe: {run_dir.name}")
        artifact_path = run_dir / file_name
        if artifact_path.is_symlink() or not artifact_path.is_file():
            raise OperationsError(f"persisted output is missing or invalid: {file_name}")
        if sha256_hex(artifact_path.read_bytes()) != expected_sha256:
            raise OperationsError(f"persisted output digest mismatch: {file_name}")


def _build_operations_manifest(
    plan: BackfillPlan,
    completed: Mapping[str, object],
) -> dict[str, object]:
    source_entries = []
    for item in plan.inputs:
        raw_entry = completed.get(item.source_id)
        if not isinstance(raw_entry, dict):
            raise OperationsError(f"backfill is incomplete: {item.source_id}")
        source_entries.append(
            {
                "accepted_rows": raw_entry["accepted_rows"],
                "manifest_sha256": raw_entry["manifest_sha256"],
                "pipeline_run_id": raw_entry["pipeline_run_id"],
                "quarantined_rows": raw_entry["quarantined_rows"],
                "source_bytes": item.source_bytes,
                "source_file_sha256": item.source_file_sha256,
                "source_id": item.source_id,
                "source_rows": raw_entry["source_rows"],
            }
        )

    planned_partitions = len(plan.inputs)
    completed_partitions = len(source_entries)
    accepted_rows = sum(int(item["accepted_rows"]) for item in source_entries)
    quarantined_rows = sum(int(item["quarantined_rows"]) for item in source_entries)
    source_rows = sum(int(item["source_rows"]) for item in source_entries)
    observed_source_bytes = sum(item.source_bytes for item in plan.inputs)
    partition_ratio = _ratio(completed_partitions, planned_partitions)
    accounting_ratio = _ratio(accepted_rows + quarantined_rows, source_rows)
    return {
        "backfill_id": plan.backfill_id,
        "cost_guard": {
            "max_partitions": plan.max_partitions,
            "max_total_source_bytes": plan.max_total_source_bytes,
            "observed_partitions": planned_partitions,
            "observed_source_bytes": observed_source_bytes,
            "status": "PASS",
        },
        "data_boundary": "synthetic_non_live",
        "metrics": {
            "accepted_rows": accepted_rows,
            "completed_partitions": completed_partitions,
            "planned_partitions": planned_partitions,
            "quarantined_rows": quarantined_rows,
            "source_bytes": observed_source_bytes,
            "source_rows": source_rows,
        },
        "schema_version": OPERATIONS_MANIFEST_SCHEMA,
        "slis": {
            "partition_completion_ratio": {
                "status": "PASS" if partition_ratio == "1.000000" else "FAIL",
                "target": "1.000000",
                "value": partition_ratio,
            },
            "row_accounting_ratio": {
                "status": "PASS" if accounting_ratio == "1.000000" else "FAIL",
                "target": "1.000000",
                "value": accounting_ratio,
            },
        },
        "sources": source_entries,
        "status": "PASS",
    }


def _write_metrics(path: Path, manifest: Mapping[str, object]) -> None:
    metrics = manifest["metrics"]
    slis = manifest["slis"]
    assert isinstance(metrics, dict)
    assert isinstance(slis, dict)
    records = [
        {
            "backfill_id": manifest["backfill_id"],
            "data_boundary": manifest["data_boundary"],
            "metric": key,
            "schema_version": "hydra-market-operations-metric/v1",
            "type": "counter",
            "value": metrics[key],
        }
        for key in sorted(metrics)
    ]
    records.extend(
        {
            "backfill_id": manifest["backfill_id"],
            "data_boundary": manifest["data_boundary"],
            "metric": key,
            "schema_version": "hydra-market-operations-metric/v1",
            "status": value["status"],
            "target": value["target"],
            "type": "sli",
            "value": value["value"],
        }
        for key, value in sorted(slis.items())
        if isinstance(value, dict)
    )
    payload = b"".join(canonical_json_bytes(record) + b"\n" for record in records)
    _write_bytes_atomic(path, payload)


def _ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "1.000000"
    return format(
        (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.000001")),
        ".6f",
    )


def _load_strict_json(path: Path, label: str) -> object:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise OperationsError(f"{label} is unreadable or invalid JSON: {exc}") from exc
    return _load_strict_json_bytes(raw, label)


def _load_strict_json_bytes(raw: bytes, label: str) -> object:
    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise OperationsError(f"{label} contains duplicate key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise OperationsError(f"{label} contains non-finite number: {value}")

    try:
        return json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperationsError(f"{label} is unreadable or invalid JSON: {exc}") from exc


def _require_exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    label: str,
) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing or extra:
        raise OperationsError(f"{label} keys mismatch: missing={missing}, extra={extra}")


def _positive_int(value: object, label: str) -> int:
    if type(value) is not int or value < 1:
        raise OperationsError(f"{label} must be a positive integer")
    return value


def _write_json_atomic(path: Path, value: object) -> None:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    _write_bytes_atomic(path, payload)


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(payload)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
