"""Independent stdlib replay of the public market-pipeline v1 transform."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from typing import Any, Mapping


PIPELINE_MANIFEST_SCHEMA = "hydra-market-pipeline-manifest/v2"
PIPELINE_RUN_SCHEMA = "hydra-market-pipeline-run/v1"
TRANSFORM_VERSION = "hydra-market-normalizer/v1"
SOURCE_CSV_SCHEMA = "hydra-market-source-csv/v1"
RESOLVED_ALIASES_SCHEMA = "hydra-market-resolved-aliases/v1"
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
SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,15}$")
VENUE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,15}$")
SIX_PLACES = Decimal("0.000001")
PRICE_DECIMAL_PRECISION = 28
ERROR_MESSAGES = {
    "currency_invalid": "currency must be exactly three alphabetic characters",
    "duplicate_normalized_event": (
        "normalized symbol, UTC timestamp, and venue already appeared earlier in the file"
    ),
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
    "source_system_invalid": (
        "source_system is not in the allowed public synthetic source list"
    ),
    "source_system_missing": "source_system is required",
    "symbol_invalid": "symbol must normalize to an allowed uppercase market symbol",
    "symbol_missing": "symbol is required",
    "venue_invalid": "venue must be a non-empty uppercase venue identifier",
    "volume_invalid": "volume must be an integer",
    "volume_missing": "volume is required",
    "volume_negative": "volume must be greater than or equal to zero",
}


class ReplayContractError(ValueError):
    """Raised when a replay input does not satisfy the producer contract."""


@dataclass(frozen=True)
class ReplayResult:
    source_file_sha256: str
    aliases_sha256: str
    pipeline_run_id: str
    source_rows: int
    accepted: tuple[Mapping[str, Any], ...]
    quarantined: tuple[Mapping[str, Any], ...]
    normalized_jsonl: bytes
    normalized_csv: bytes
    quarantine_jsonl: bytes


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ReplayContractError(f"value is not canonical JSON: {exc}") from exc


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def object_sha256(value: Any) -> str:
    return sha256_hex(canonical_json_bytes(value))


def replay_pipeline(*, source_bytes: bytes, aliases_bytes: bytes) -> ReplayResult:
    """Replay the transform from immutable input bytes without producer imports."""

    if type(source_bytes) is not bytes or type(aliases_bytes) is not bytes:
        raise ReplayContractError("pipeline replay snapshots must be exact bytes")

    aliases = _load_resolved_aliases(aliases_bytes)
    source_file_sha256 = sha256_hex(source_bytes)
    aliases_sha256 = object_sha256(aliases)
    pipeline_run_id = object_sha256(
        {
            "aliases_sha256": aliases_sha256,
            "run_schema": PIPELINE_RUN_SCHEMA,
            "source_file_sha256": source_file_sha256,
            "transform_version": TRANSFORM_VERSION,
        }
    )

    try:
        text = source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ReplayContractError("source snapshot must be valid UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    reader.fieldnames = _validate_header(reader.fieldnames)

    accepted: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    source_rows = 0

    for source_row_number, row in enumerate(reader, start=2):
        source_rows += 1
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
                _quarantine_record(
                    source_row_number=source_row_number,
                    raw_record=raw_record,
                    raw_record_sha256=raw_record_sha256,
                    errors=errors,
                )
            )
            continue

        if event_time_utc is None or price is None or volume is None:
            raise ReplayContractError("accepted row is missing a normalized value")
        accepted.append(
            {
                "currency": currency,
                "event_id": event_id,
                "event_time_utc": _format_utc(event_time_utc),
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

    accepted.sort(key=lambda item: item["event_id"])
    quarantined.sort(key=lambda item: item["source_row_number"])
    normalized_jsonl = _jsonl_bytes(accepted)
    quarantine_jsonl = _jsonl_bytes(quarantined)
    normalized_csv = _csv_bytes(accepted)

    return ReplayResult(
        source_file_sha256=source_file_sha256,
        aliases_sha256=aliases_sha256,
        pipeline_run_id=pipeline_run_id,
        source_rows=source_rows,
        accepted=tuple(accepted),
        quarantined=tuple(quarantined),
        normalized_jsonl=normalized_jsonl,
        normalized_csv=normalized_csv,
        quarantine_jsonl=quarantine_jsonl,
    )


def _load_resolved_aliases(raw: bytes) -> dict[str, str]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError, ReplayContractError) as exc:
        raise ReplayContractError(f"resolved aliases snapshot is invalid JSON: {exc}") from exc
    if type(value) is not dict:
        raise ReplayContractError("resolved aliases snapshot must be a JSON object")

    aliases: dict[str, str] = {}
    for key, target in value.items():
        if type(key) is not str or type(target) is not str:
            raise ReplayContractError("resolved alias keys and values must be strings")
        if not key or key != key.strip().upper():
            raise ReplayContractError("resolved alias keys must be normalized uppercase strings")
        if target != target.strip().upper() or not SYMBOL_PATTERN.fullmatch(target):
            raise ReplayContractError("resolved alias targets must be valid normalized symbols")
        aliases[key] = target

    if raw != canonical_json_bytes(aliases):
        raise ReplayContractError("resolved aliases snapshot is not canonical JSON")
    return aliases


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReplayContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ReplayContractError(f"non-finite JSON number: {value}")


def _validate_header(fieldnames: list[str] | None) -> list[str]:
    if fieldnames is None:
        raise ReplayContractError("source snapshot has no CSV header")
    normalized = [field.strip() for field in fieldnames]
    duplicates = sorted({field for field in normalized if normalized.count(field) > 1})
    missing = sorted(set(REQUIRED_COLUMNS) - set(normalized))
    extra = sorted(set(normalized) - set(REQUIRED_COLUMNS))
    if duplicates or missing or extra or len(normalized) != len(REQUIRED_COLUMNS):
        raise ReplayContractError(
            "source CSV contract mismatch: "
            f"missing={missing}, extra={extra}, duplicates={duplicates}"
        )
    return normalized


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
        price_context = Context(
            prec=PRICE_DECIMAL_PRECISION,
            rounding=ROUND_HALF_EVEN,
            traps=[InvalidOperation],
        )
        with localcontext(price_context):
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
) -> dict[str, Any]:
    sorted_errors = sorted(set(errors))
    quarantine_id = object_sha256(
        {
            "errors": sorted_errors,
            "raw_record_sha256": raw_record_sha256,
            "source_row_number": source_row_number,
        }
    )
    return {
        "errors": sorted_errors,
        "quarantine_id": quarantine_id,
        "raw_record": dict(raw_record),
        "raw_record_sha256": raw_record_sha256,
        "source_row_number": source_row_number,
        "stage": ROW_VALIDATION_STAGE,
        "validation_messages": [ERROR_MESSAGES[error] for error in sorted_errors],
    }


def _jsonl_bytes(records: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(record) + b"\n" for record in records)


def _csv_bytes(records: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=NORMALIZED_CSV_COLUMNS,
        lineterminator="\n",
    )
    writer.writeheader()
    for record in records:
        writer.writerow({column: record[column] for column in NORMALIZED_CSV_COLUMNS})
    return buffer.getvalue().encode("utf-8")


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
