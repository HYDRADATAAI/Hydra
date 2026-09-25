"""Synthetic market-data ingestion, validation, normalization, and quarantine."""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping

from .hashing import canonical_json_bytes, object_sha256, sha256_hex
from .models import NormalizedEvent, PipelineResult, QuarantineRecord


TRANSFORM_VERSION = "hydra-market-normalizer/v1"
RUN_SCHEMA = "hydra-market-pipeline-run/v1"
ROW_VALIDATION_STAGE = "row_validation"
ALLOWED_SOURCE_SYSTEMS = frozenset({"SYNTH_A", "SYNTH_B", "SYNTH_VENDOR"})
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
SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,15}$")
VENUE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,15}$")
SIX_PLACES = Decimal("0.000001")
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
    """Raised when the input file shape violates the producer contract."""


def load_aliases(path: str | Path) -> tuple[dict[str, str], str]:
    raw = Path(path).read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"symbol alias config is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError("symbol alias config must be a JSON object")

    aliases: dict[str, str] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not isinstance(raw_value, str):
            raise ContractError("symbol alias keys and values must be strings")
        key = raw_key.strip().upper()
        target = raw_value.strip().upper()
        if not key or not SYMBOL_PATTERN.fullmatch(target):
            raise ContractError(f"invalid symbol alias: {raw_key!r} -> {raw_value!r}")
        aliases[key] = target

    return aliases, object_sha256(aliases)


def run_pipeline(
    *,
    input_csv: str | Path,
    aliases_path: str | Path,
) -> PipelineResult:
    input_path = Path(input_csv)
    source_bytes = input_path.read_bytes()
    source_file_sha256 = sha256_hex(source_bytes)
    aliases, aliases_sha256 = load_aliases(aliases_path)

    pipeline_run_id = object_sha256(
        {
            "aliases_sha256": aliases_sha256,
            "run_schema": RUN_SCHEMA,
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

    accepted: list[NormalizedEvent] = []
    quarantined: list[QuarantineRecord] = []
    seen_event_ids: set[str] = set()

    for source_row_number, row in enumerate(reader, start=2):
        raw_record = {
            column: "" if row.get(column) is None else str(row.get(column))
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
        symbol = aliases.get(raw_symbol, raw_symbol)
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
                _quarantine(
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
            NormalizedEvent(
                event_id=event_id,
                source_system=source_system,
                source_record_id=source_record_id,
                symbol=symbol,
                event_time_utc=event_time_utc,
                price=price,
                volume=volume,
                currency=currency,
                venue=venue,
                source_file_sha256=source_file_sha256,
                raw_record_sha256=raw_record_sha256,
                source_row_number=source_row_number,
                transform_version=TRANSFORM_VERSION,
            )
        )
        seen_event_ids.add(event_id)

    return PipelineResult(
        pipeline_run_id=pipeline_run_id,
        source_file_sha256=source_file_sha256,
        aliases_sha256=aliases_sha256,
        transform_version=TRANSFORM_VERSION,
        accepted=tuple(sorted(accepted, key=lambda item: item.event_id)),
        quarantined=tuple(sorted(quarantined, key=lambda item: item.source_row_number)),
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


def _quarantine(
    *,
    source_row_number: int,
    raw_record: Mapping[str, str],
    raw_record_sha256: str,
    errors: list[str],
) -> QuarantineRecord:
    sorted_errors = tuple(sorted(set(errors)))
    quarantine_id = object_sha256(
        {
            "errors": sorted_errors,
            "raw_record_sha256": raw_record_sha256,
            "source_row_number": source_row_number,
        }
    )
    return QuarantineRecord(
        quarantine_id=quarantine_id,
        stage=ROW_VALIDATION_STAGE,
        source_row_number=source_row_number,
        raw_record_sha256=raw_record_sha256,
        errors=sorted_errors,
        validation_messages=tuple(ERROR_MESSAGES[error] for error in sorted_errors),
        raw_record=dict(raw_record),
    )


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
