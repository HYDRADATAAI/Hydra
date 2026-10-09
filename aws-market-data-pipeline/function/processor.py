"""Deterministic synthetic market-data transform used locally and in Lambda."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Mapping


TRANSFORM_VERSION = "hydra-aws-market-normalizer/v1"
MANIFEST_SCHEMA = "hydra-aws-market-pipeline-manifest/v1"
REQUIRED_COLUMNS = (
    "source_system",
    "source_record_id",
    "symbol",
    "event_time",
    "price",
    "volume",
    "currency",
    "venue",
)
ALLOWED_SOURCE_SYSTEMS = frozenset({"SYNTH_A", "SYNTH_B", "SYNTH_VENDOR"})
SYMBOL_ALIASES = {"AAA.US": "AAA", "EEE.US": "EEE"}
SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,15}$")
VENUE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,15}$")
SIX_PLACES = Decimal("0.000001")
MAX_SOURCE_ROWS = 10_000
ERROR_MESSAGES = {
    "currency_invalid": "currency must be exactly three alphabetic characters",
    "duplicate_normalized_event": "normalized symbol, UTC timestamp, and venue already appeared earlier in the file",
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
    "source_system_invalid": "source_system is not in the allowed public synthetic source list",
    "source_system_missing": "source_system is required",
    "symbol_invalid": "symbol must normalize to an allowed uppercase market symbol",
    "symbol_missing": "symbol is required",
    "venue_invalid": "venue must be a non-empty uppercase venue identifier",
    "volume_invalid": "volume must be an integer",
    "volume_missing": "volume is required",
    "volume_negative": "volume must be greater than or equal to zero",
}


class ContractError(ValueError):
    """Raised when the source object violates the file-level contract."""


@dataclass(frozen=True)
class ProcessedBatch:
    run_id: str
    source_file_sha256: str
    accepted: tuple[dict[str, object], ...]
    quarantined: tuple[dict[str, object], ...]
    artifacts: Mapping[str, bytes]


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def object_sha256(value: object) -> str:
    return sha256_hex(canonical_json_bytes(value))


def process_csv(source_bytes: bytes) -> ProcessedBatch:
    source_file_sha256 = sha256_hex(source_bytes)
    aliases_sha256 = object_sha256(SYMBOL_ALIASES)
    run_id = object_sha256(
        {
            "aliases_sha256": aliases_sha256,
            "source_file_sha256": source_file_sha256,
            "transform_version": TRANSFORM_VERSION,
        }
    )

    try:
        text = source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContractError("input CSV must be valid UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    _validate_header(reader.fieldnames)

    accepted: list[dict[str, object]] = []
    quarantined: list[dict[str, object]] = []
    seen_event_ids: set[str] = set()

    for source_row_number, row in enumerate(reader, start=2):
        if source_row_number > MAX_SOURCE_ROWS + 1:
            raise ContractError(f"input CSV exceeds max_rows={MAX_SOURCE_ROWS}")
        raw_record = {
            column: "" if row.get(column) is None else str(row[column])
            for column in REQUIRED_COLUMNS
        }
        raw_record_sha256 = object_sha256(raw_record)
        errors: list[str] = []

        if None in row:
            errors.append("row_extra_values")

        source_system = raw_record["source_system"].strip().upper()
        source_record_id = raw_record["source_record_id"].strip()
        if not source_system:
            errors.append("source_system_missing")
        elif source_system not in ALLOWED_SOURCE_SYSTEMS:
            errors.append("source_system_invalid")
        if not source_record_id:
            errors.append("source_record_id_missing")

        raw_symbol = raw_record["symbol"].strip().upper()
        symbol = SYMBOL_ALIASES.get(raw_symbol, raw_symbol)
        if not raw_symbol:
            errors.append("symbol_missing")
        elif not SYMBOL_PATTERN.fullmatch(symbol):
            errors.append("symbol_invalid")

        event_time_utc = _parse_event_time(raw_record["event_time"], errors)
        price = _parse_price(raw_record["price"], errors)
        volume = _parse_volume(raw_record["volume"], errors)

        currency = raw_record["currency"].strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            errors.append("currency_invalid")

        venue = raw_record["venue"].strip().upper()
        if not VENUE_PATTERN.fullmatch(venue):
            errors.append("venue_invalid")

        event_id = ""
        if event_time_utc is not None and symbol and venue:
            event_id = object_sha256(
                {
                    "event_time_utc": _format_utc(event_time_utc),
                    "symbol": symbol,
                    "venue": venue,
                }
            )
            if event_id in seen_event_ids:
                errors.append("duplicate_normalized_event")

        if errors:
            quarantined.append(
                _quarantine_record(
                    source_row_number=source_row_number,
                    raw_record=raw_record,
                    raw_record_sha256=raw_record_sha256,
                    errors=errors,
                )
            )
            continue

        assert event_time_utc is not None
        assert price is not None
        assert volume is not None
        accepted.append(
            {
                "currency": currency,
                "event_id": event_id,
                "event_time_utc": _format_utc(event_time_utc),
                "pipeline_run_id": run_id,
                "price": format(price, ".6f"),
                "raw_record_sha256": raw_record_sha256,
                "source_file_sha256": source_file_sha256,
                "source_record_id": source_record_id,
                "source_row_number": source_row_number,
                "source_system": source_system,
                "symbol": symbol,
                "transform_version": TRANSFORM_VERSION,
                "venue": venue,
                "volume": volume,
            }
        )
        seen_event_ids.add(event_id)

    accepted_records = tuple(sorted(accepted, key=lambda item: str(item["event_id"])))
    quarantine_records = tuple(
        sorted(quarantined, key=lambda item: int(item["source_row_number"]))
    )
    normalized_bytes = _jsonl_bytes(accepted_records)
    quarantine_bytes = _jsonl_bytes(quarantine_records)
    manifest = {
        "accepted_rows": len(accepted_records),
        "aliases_sha256": aliases_sha256,
        "outputs": {
            "normalized_events.jsonl": {"sha256": sha256_hex(normalized_bytes)},
            "quarantine_records.jsonl": {"sha256": sha256_hex(quarantine_bytes)},
        },
        "pipeline_run_id": run_id,
        "quarantined_rows": len(quarantine_records),
        "schema_version": MANIFEST_SCHEMA,
        "source_file_sha256": source_file_sha256,
        "transform_version": TRANSFORM_VERSION,
    }
    artifacts = {
        "manifest.json": canonical_json_bytes(manifest) + b"\n",
        "normalized_events.jsonl": normalized_bytes,
        "quarantine_records.jsonl": quarantine_bytes,
    }
    return ProcessedBatch(
        run_id=run_id,
        source_file_sha256=source_file_sha256,
        accepted=accepted_records,
        quarantined=quarantine_records,
        artifacts=artifacts,
    )


def _validate_header(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ContractError("input CSV has no header")
    normalized = [field.strip() for field in fieldnames]
    duplicates = sorted({field for field in normalized if normalized.count(field) > 1})
    missing = sorted(set(REQUIRED_COLUMNS) - set(normalized))
    extra = sorted(set(normalized) - set(REQUIRED_COLUMNS))
    if duplicates or missing or extra or len(normalized) != len(REQUIRED_COLUMNS):
        raise ContractError(
            "input CSV contract mismatch: "
            f"missing={missing}, extra={extra}, duplicates={duplicates}"
        )


def _parse_event_time(value: str, errors: list[str]) -> datetime | None:
    text = value.strip()
    if not text:
        errors.append("event_time_missing")
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        errors.append("event_time_invalid")
        return None
    if parsed.tzinfo is None:
        errors.append("event_time_timezone_missing")
        return None
    return parsed.astimezone(UTC)


def _parse_price(value: str, errors: list[str]) -> Decimal | None:
    text = value.strip()
    if not text:
        errors.append("price_missing")
        return None
    try:
        price = Decimal(text)
    except InvalidOperation:
        errors.append("price_invalid")
        return None
    if not price.is_finite():
        errors.append("price_non_finite")
        return None
    if price <= 0:
        errors.append("price_non_positive")
        return None
    try:
        normalized = price.quantize(SIX_PLACES)
    except InvalidOperation:
        errors.append("price_invalid")
        return None
    if normalized != price:
        errors.append("price_scale_exceeds_6")
        return None
    return normalized


def _parse_volume(value: str, errors: list[str]) -> int | None:
    text = value.strip()
    if not text:
        errors.append("volume_missing")
        return None
    try:
        volume = int(text)
    except ValueError:
        errors.append("volume_invalid")
        return None
    if volume < 0:
        errors.append("volume_negative")
        return None
    return volume


def _quarantine_record(
    *,
    source_row_number: int,
    raw_record: Mapping[str, str],
    raw_record_sha256: str,
    errors: list[str],
) -> dict[str, object]:
    sorted_errors = tuple(sorted(set(errors)))
    return {
        "errors": list(sorted_errors),
        "quarantine_id": object_sha256(
            {
                "errors": sorted_errors,
                "raw_record_sha256": raw_record_sha256,
                "source_row_number": source_row_number,
            }
        ),
        "raw_record": dict(raw_record),
        "raw_record_sha256": raw_record_sha256,
        "source_row_number": source_row_number,
        "stage": "row_validation",
        "validation_messages": [ERROR_MESSAGES[error] for error in sorted_errors],
    }


def _jsonl_bytes(records: tuple[dict[str, object], ...]) -> bytes:
    return b"".join(canonical_json_bytes(record) + b"\n" for record in records)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
