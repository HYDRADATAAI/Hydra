"""Immutable pipeline result models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True)
class NormalizedEvent:
    event_id: str
    source_system: str
    source_record_id: str
    symbol: str
    event_time_utc: datetime
    price: Decimal
    volume: int
    currency: str
    venue: str
    source_file_sha256: str
    raw_record_sha256: str
    source_row_number: int
    transform_version: str

    def json_record(self) -> dict[str, object]:
        return {
            "currency": self.currency,
            "event_id": self.event_id,
            "event_time_utc": _format_utc(self.event_time_utc),
            "price": format(self.price, ".6f"),
            "raw_record_sha256": self.raw_record_sha256,
            "source_file_sha256": self.source_file_sha256,
            "source_record_id": self.source_record_id,
            "source_row_number": self.source_row_number,
            "source_system": self.source_system,
            "symbol": self.symbol,
            "transform_version": self.transform_version,
            "venue": self.venue,
            "volume": self.volume,
        }


@dataclass(frozen=True)
class QuarantineRecord:
    quarantine_id: str
    stage: str
    source_row_number: int
    raw_record_sha256: str
    errors: tuple[str, ...]
    validation_messages: tuple[str, ...]
    raw_record: Mapping[str, str]

    def json_record(self) -> dict[str, object]:
        return {
            "errors": list(self.errors),
            "quarantine_id": self.quarantine_id,
            "raw_record": dict(self.raw_record),
            "raw_record_sha256": self.raw_record_sha256,
            "source_row_number": self.source_row_number,
            "stage": self.stage,
            "validation_messages": list(self.validation_messages),
        }


@dataclass(frozen=True)
class PipelineResult:
    pipeline_run_id: str
    source_file_sha256: str
    aliases_sha256: str
    transform_version: str
    accepted: tuple[NormalizedEvent, ...]
    quarantined: tuple[QuarantineRecord, ...]


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
