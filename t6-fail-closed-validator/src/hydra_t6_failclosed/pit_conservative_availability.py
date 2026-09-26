"""Validate conservative available_at overlays without backdating or ordinary-lineage escalation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from .models import Issue, sorted_issues

OVERLAY_SCHEMA = "hydra-constraint-first-slice-conservative-availability-overlay/v1"
BASIS = "HYDRA_FIRST_DEFENSIBLE_ACQUISITION_OBSERVATION"


def validate_conservative_availability_overlay(value: Mapping[str, Any]) -> tuple[Issue, ...]:
    issues: list[Issue] = []
    if value.get("schema_version") != OVERLAY_SCHEMA:
        issues.append(Issue("availability_overlay_schema_invalid", "unsupported conservative availability overlay schema", "$.schema_version"))
    if value.get("historical_backdating_authorized") is not False:
        issues.append(Issue("availability_overlay_backdating_escalation", "Batch007 may not authorize historical backdating", "$.historical_backdating_authorized"))
    records = value.get("records")
    if not isinstance(records, list) or not records:
        issues.append(Issue("availability_overlay_records_missing", "overlay requires source records", "$.records"))
        return sorted_issues(issues)
    seen=set()
    for i, record in enumerate(records):
        path=f"$.records[{i}]"
        if not isinstance(record, Mapping):
            issues.append(Issue("availability_overlay_record_invalid", "record must be an object", path))
            continue
        sid=record.get("source_id")
        if not isinstance(sid,str) or not sid:
            issues.append(Issue("availability_overlay_source_id_invalid", "source_id is required", f"{path}.source_id"))
        elif sid in seen:
            issues.append(Issue("availability_overlay_source_id_duplicate", "source_id must be unique", f"{path}.source_id"))
        else:
            seen.add(sid)
        acquired=_parse(record.get("inherited_acquired_at"))
        available=_parse(record.get("conservative_available_at"))
        if acquired is None:
            issues.append(Issue("availability_overlay_acquired_at_invalid", "inherited_acquired_at must be timezone-aware ISO-8601", f"{path}.inherited_acquired_at"))
        if available is None:
            issues.append(Issue("availability_overlay_available_at_invalid", "conservative_available_at must be timezone-aware ISO-8601", f"{path}.conservative_available_at"))
        if acquired and available and available != acquired:
            issues.append(Issue("availability_overlay_not_conservative", "without earlier proof conservative available_at must equal acquired_at", f"{path}.conservative_available_at"))
        if record.get("availability_basis") != BASIS:
            issues.append(Issue("availability_overlay_basis_invalid", "availability basis must be first defensible Hydra acquisition/observation", f"{path}.availability_basis"))
        if record.get("historical_backdating_authorized") is not False:
            issues.append(Issue("availability_overlay_record_backdating_escalation", "record may not authorize historical backdating", f"{path}.historical_backdating_authorized"))
        if record.get("source_content_persisted") is not False:
            issues.append(Issue("availability_overlay_content_claim_invalid", "overlay must preserve Batch004 source_content_persisted=false", f"{path}.source_content_persisted"))
        if record.get("ordinary_replay_lineage_eligible") is not False:
            issues.append(Issue("availability_overlay_lineage_escalation", "temporal eligibility alone cannot grant ordinary replay lineage", f"{path}.ordinary_replay_lineage_eligible"))
    return sorted_issues(issues)


def temporally_eligible(record: Mapping[str, Any], query_time: datetime) -> bool:
    available=_parse(record.get("conservative_available_at"))
    return available is not None and query_time.tzinfo is not None and available <= query_time


def _parse(value: Any) -> datetime | None:
    if not isinstance(value,str):
        return None
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None
