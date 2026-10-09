"""S3-triggered Lambda adapter for the deterministic market-data transform."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import unquote_plus

try:
    from .processor import ProcessedBatch, process_csv
except ImportError:  # Lambda loads this module from the CodeUri root.
    from processor import ProcessedBatch, process_csv


CONTENT_TYPES = {
    "manifest.json": "application/json",
    "normalized_events.jsonl": "application/x-ndjson",
    "quarantine_records.jsonl": "application/x-ndjson",
}
ARTIFACT_WRITE_ORDER = (
    "normalized_events.jsonl",
    "quarantine_records.jsonl",
    "manifest.json",
)


def lambda_handler(
    event: dict[str, Any],
    context: object,
    *,
    s3_client: object | None = None,
    glue_client: object | None = None,
) -> dict[str, object]:
    del context
    output_bucket = os.environ.get("CURATED_BUCKET", "").strip()
    if not output_bucket:
        raise RuntimeError("CURATED_BUCKET must be configured")
    catalog_database = os.environ.get("DATA_CATALOG_DATABASE", "").strip()
    if not catalog_database:
        raise RuntimeError("DATA_CATALOG_DATABASE must be configured")

    client = s3_client or _boto3_s3_client()
    catalog = glue_client or _boto3_glue_client()
    source_objects = sorted(_source_objects(event))
    if not source_objects:
        raise ValueError("event contains no S3 ObjectCreated records")

    processed: list[dict[str, object]] = []
    for source_bucket, source_key in source_objects:
        response = client.get_object(Bucket=source_bucket, Key=source_key)
        source_bytes = _body_bytes(response["Body"])
        batch = process_csv(source_bytes)
        output_keys = _write_batch(client, output_bucket, batch)
        _publish_partition(catalog, catalog_database, output_bucket, batch.run_id)
        processed.append(
            {
                "accepted_rows": len(batch.accepted),
                "output_bucket": output_bucket,
                "output_keys": output_keys,
                "pipeline_run_id": batch.run_id,
                "quarantined_rows": len(batch.quarantined),
                "source_bucket": source_bucket,
                "source_key": source_key,
            }
        )

    return {"processed": processed, "status": "PASS"}


def _source_objects(event: dict[str, Any]) -> list[tuple[str, str]]:
    objects: list[tuple[str, str]] = []
    records = event.get("Records", [])
    if not isinstance(records, list):
        raise ValueError("event Records must be a list")
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("eventSource") != "aws:s3":
            continue
        if not str(record.get("eventName", "")).startswith("ObjectCreated:"):
            continue
        s3 = record.get("s3", {})
        bucket = s3.get("bucket", {}).get("name")
        key = s3.get("object", {}).get("key")
        if isinstance(bucket, str) and isinstance(key, str):
            objects.append((bucket, unquote_plus(key)))
    return objects


def _write_batch(client: object, bucket: str, batch: ProcessedBatch) -> list[str]:
    destinations = {
        "normalized_events.jsonl": f"curated/accepted/{batch.run_id}/normalized_events.jsonl",
        "quarantine_records.jsonl": f"curated/quarantine/{batch.run_id}/quarantine_records.jsonl",
        "manifest.json": f"curated/manifests/{batch.run_id}/manifest.json",
    }
    metadata = {
        "pipeline-run-id": batch.run_id,
        "source-sha256": batch.source_file_sha256,
        "transform-version": "hydra-aws-market-normalizer-v1",
    }
    for artifact_name in ARTIFACT_WRITE_ORDER:
        client.put_object(
            Body=batch.artifacts[artifact_name],
            Bucket=bucket,
            ContentType=CONTENT_TYPES[artifact_name],
            Key=destinations[artifact_name],
            Metadata=metadata,
            ServerSideEncryption="AES256",
        )
    return [destinations[name] for name in ARTIFACT_WRITE_ORDER]


GLUE_PARTITION_COLUMNS = (
    {"Name": "currency", "Type": "string"},
    {"Name": "event_id", "Type": "string"},
    {"Name": "event_time_utc", "Type": "string"},
    {"Name": "price", "Type": "string"},
    {"Name": "raw_record_sha256", "Type": "string"},
    {"Name": "source_file_sha256", "Type": "string"},
    {"Name": "source_record_id", "Type": "string"},
    {"Name": "source_row_number", "Type": "bigint"},
    {"Name": "source_system", "Type": "string"},
    {"Name": "symbol", "Type": "string"},
    {"Name": "transform_version", "Type": "string"},
    {"Name": "venue", "Type": "string"},
    {"Name": "volume", "Type": "bigint"},
)


def _publish_partition(
    catalog: object, database: str, bucket: str, run_id: str
) -> None:
    """Expose an accepted prefix only after every deterministic artifact is stored."""
    try:
        catalog.create_partition(
            DatabaseName=database,
            TableName="normalized_events",
            PartitionInput={
                "Values": [run_id],
                "StorageDescriptor": {
                    "Columns": list(GLUE_PARTITION_COLUMNS),
                    "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "Location": f"s3://{bucket}/curated/accepted/{run_id}/",
                    "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    "SerdeInfo": {
                        "Parameters": {"ignore.malformed.jsons": "false"},
                        "SerializationLibrary": "org.openx.data.jsonserde.JsonSerDe",
                    },
                },
            },
        )
    except Exception as exc:
        # S3 events can be retried or delivered concurrently for the same content hash.
        # A previously registered partition is safe because it was created after all
        # three immutable artifacts were written by this same content-addressed run.
        response = getattr(exc, "response", None)
        error = response.get("Error", {}) if isinstance(response, dict) else {}
        if error.get("Code") != "AlreadyExistsException":
            raise


def _body_bytes(body: object) -> bytes:
    value = body.read() if hasattr(body, "read") else body
    if not isinstance(value, bytes):
        raise TypeError("S3 object Body must resolve to bytes")
    return value


def _boto3_s3_client() -> object:
    import boto3

    return boto3.client("s3")


def _boto3_glue_client() -> object:
    import boto3

    return boto3.client("glue")
