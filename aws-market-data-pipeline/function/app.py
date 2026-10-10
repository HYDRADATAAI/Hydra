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
DEFAULT_MAX_SOURCE_OBJECT_BYTES = 1_048_576
MAX_SOURCE_OBJECT_BYTES_LIMIT = 2_000_000


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

    max_source_object_bytes = _max_source_object_bytes()
    catalog_database = os.environ.get("DATA_CATALOG_DATABASE", "").strip()
    if not catalog_database:
        raise RuntimeError("DATA_CATALOG_DATABASE must be configured")

    client = s3_client or _boto3_s3_client()
    catalog = glue_client or _boto3_glue_client()
    source_objects = sorted(
        _source_objects(event),
        key=lambda item: (
            item[0],
            item[1],
            item[2] if item[2] is not None else -1,
            item[3] or "",
        ),
    )
    if not source_objects:
        raise ValueError("event contains no S3 ObjectCreated records")

    if any(
        object_size is not None and object_size > max_source_object_bytes
        for _, _, object_size, _ in source_objects
    ):
        raise ValueError(
            f"source object exceeds max_source_object_bytes={max_source_object_bytes}"
        )

    processed: list[dict[str, object]] = []
    for source_bucket, source_key, event_object_size, version_id in source_objects:
        get_args: dict[str, object] = {"Bucket": source_bucket, "Key": source_key}
        if version_id is not None:
            get_args["VersionId"] = version_id
        response = client.get_object(**get_args)
        body = response["Body"]
        try:
            content_length = response.get("ContentLength")
            if content_length is not None:
                if type(content_length) is not int or content_length < 0:
                    raise ValueError(
                        "S3 get_object ContentLength must be a non-negative integer"
                    )
                if content_length > max_source_object_bytes:
                    raise ValueError(
                        f"source object exceeds max_source_object_bytes={max_source_object_bytes}"
                    )
                if event_object_size is not None and content_length != event_object_size:
                    raise ValueError(
                        "S3 event object size does not match get_object ContentLength"
                    )
        except Exception:
            _close_body(body)
            raise
        source_bytes = _body_bytes(body, max_bytes=max_source_object_bytes)
        if content_length is not None and len(source_bytes) != content_length:
            raise ValueError("S3 response body length does not match ContentLength")
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


def _source_objects(
    event: dict[str, Any],
) -> list[tuple[str, str, int | None, str | None]]:
    objects: list[tuple[str, str, int | None, str | None]] = []
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
        s3 = record.get("s3")
        if not isinstance(s3, dict):
            raise ValueError("S3 ObjectCreated record s3 field must be an object")
        bucket_data = s3.get("bucket")
        if not isinstance(bucket_data, dict):
            raise ValueError("S3 ObjectCreated record bucket field must be an object")
        object_data = s3.get("object")
        if not isinstance(object_data, dict):
            raise ValueError("S3 ObjectCreated record object field must be an object")
        bucket = bucket_data.get("name")
        if not isinstance(bucket, str) or not bucket:
            raise ValueError("S3 ObjectCreated record bucket name must be a non-empty string")
        key = object_data.get("key")
        if not isinstance(key, str) or not key:
            raise ValueError("S3 ObjectCreated record object key must be a non-empty string")
        object_size = object_data.get("size")
        if object_size is not None and (type(object_size) is not int or object_size < 0):
            raise ValueError("S3 event object size must be a non-negative integer")
        version_id = object_data.get("versionId")
        if version_id is not None and (not isinstance(version_id, str) or not version_id):
            raise ValueError("S3 event object versionId must be a non-empty string")
        objects.append((bucket, unquote_plus(key), object_size, version_id))
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


def _max_source_object_bytes() -> int:
    configured = os.environ.get(
        "MAX_SOURCE_OBJECT_BYTES", str(DEFAULT_MAX_SOURCE_OBJECT_BYTES)
    )
    try:
        limit = int(configured)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("MAX_SOURCE_OBJECT_BYTES must be a positive integer") from exc
    if not 1 <= limit <= MAX_SOURCE_OBJECT_BYTES_LIMIT:
        raise RuntimeError(
            f"MAX_SOURCE_OBJECT_BYTES must be between 1 and {MAX_SOURCE_OBJECT_BYTES_LIMIT}"
        )
    return limit



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
    location = f"s3://{bucket}/curated/accepted/{run_id}/"
    try:
        catalog.create_partition(
            DatabaseName=database,
            TableName="normalized_events",
            PartitionInput={
                "Values": [run_id],
                "StorageDescriptor": {
                    "Columns": list(GLUE_PARTITION_COLUMNS),
                    "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                    "Location": location,
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
        response = getattr(exc, "response", None)
        error = response.get("Error", {}) if isinstance(response, dict) else {}
        if error.get("Code") != "AlreadyExistsException":
            raise
        existing = catalog.get_partition(
            DatabaseName=database,
            TableName="normalized_events",
            PartitionValues=[run_id],
        ).get("Partition", {})
        if not _partition_matches(existing, run_id, location):
            raise RuntimeError(
                "existing Glue partition does not match this content-addressed run"
            ) from exc


def _partition_matches(partition: object, run_id: str, location: str) -> bool:
    if not isinstance(partition, dict) or partition.get("Values") != [run_id]:
        return False
    descriptor = partition.get("StorageDescriptor")
    if not isinstance(descriptor, dict) or descriptor.get("Location") != location:
        return False

    columns = descriptor.get("Columns")
    if not isinstance(columns, list):
        return False
    actual_columns = []
    for column in columns:
        if not isinstance(column, dict):
            return False
        actual_columns.append({"Name": column.get("Name"), "Type": column.get("Type")})
    if actual_columns != list(GLUE_PARTITION_COLUMNS):
        return False
    if descriptor.get("InputFormat") != "org.apache.hadoop.mapred.TextInputFormat":
        return False
    if descriptor.get("OutputFormat") != (
        "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"
    ):
        return False

    serde = descriptor.get("SerdeInfo")
    if not isinstance(serde, dict):
        return False
    parameters = serde.get("Parameters")
    return (
        serde.get("SerializationLibrary") == "org.openx.data.jsonserde.JsonSerDe"
        and isinstance(parameters, dict)
        and parameters.get("ignore.malformed.jsons") == "false"
    )


def _body_bytes(body: object, *, max_bytes: int) -> bytes:
    if isinstance(body, bytes):
        if len(body) > max_bytes:
            raise ValueError(f"S3 object body exceeds max_bytes={max_bytes}")
        return body

    read = getattr(body, "read", None)
    if not callable(read):
        raise TypeError("S3 object Body must resolve to bytes")

    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = read(min(64 * 1024, max_bytes + 1 - total))
            if not isinstance(chunk, bytes):
                raise TypeError("S3 object Body must resolve to bytes")
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"S3 object body exceeds max_bytes={max_bytes}")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        _close_body(body)


def _close_body(body: object) -> None:
    close = getattr(body, "close", None)
    if callable(close):
        close()


def _boto3_s3_client() -> object:
    import boto3

    return boto3.client("s3")


def _boto3_glue_client() -> object:
    import boto3

    return boto3.client("glue")
