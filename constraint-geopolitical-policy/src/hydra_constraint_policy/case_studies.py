from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .model import EventType


class CaseStudyValidationError(ValueError):
    pass


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_sourced_case_bundle(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        bundle=json.load(fh)
    validate_sourced_case_bundle(bundle)
    return bundle


def validate_sourced_case_bundle(bundle: dict[str, Any]) -> None:
    if bundle.get("evidence_digest_scope") != "sha256(normalized_evidence UTF-8)":
        raise CaseStudyValidationError("unsupported evidence digest scope")

    sources={}
    for source in bundle.get("sources", []):
        sid=source.get("source_id")
        if not sid or sid in sources:
            raise CaseStudyValidationError(f"duplicate or missing source_id: {sid!r}")
        if not str(source.get("url", "")).startswith("https://"):
            raise CaseStudyValidationError(f"{sid}: non-HTTPS source")
        evidence=source.get("normalized_evidence", "")
        expected="sha256:"+sha256(evidence.encode("utf-8")).hexdigest()
        if source.get("evidence_digest") != expected:
            raise CaseStudyValidationError(f"{sid}: evidence digest mismatch")
        _dt(source["published_at"])
        _dt(source["available_at"])
        sources[sid]=source

    seen_case_ids=set()
    seen_event_ids=set()
    seen_observation_ids=set()
    allowed_events={e.value for e in EventType}

    for case in bundle.get("cases", []):
        cid=case.get("case_id")
        if not cid or cid in seen_case_ids:
            raise CaseStudyValidationError(f"duplicate or missing case_id: {cid!r}")
        seen_case_ids.add(cid)
        if case.get("binding_status") != "PENDING_CANONICAL_PHYSICAL_ENTITY_POPULATION":
            raise CaseStudyValidationError(f"{cid}: binding status must remain explicit until canonical IDs are populated")

        for event in case.get("events", []):
            eid=event.get("event_id")
            if not eid or eid in seen_event_ids:
                raise CaseStudyValidationError(f"duplicate or missing event_id: {eid!r}")
            seen_event_ids.add(eid)
            if event.get("event_type") not in allowed_events:
                raise CaseStudyValidationError(f"{eid}: unsupported event_type")
            known=_dt(event["known_at"])
            if event.get("effective_at"):
                _dt(event["effective_at"])
            if event.get("resolved_at"):
                _dt(event["resolved_at"])
            refs=event.get("source_ids", [])
            if not refs:
                raise CaseStudyValidationError(f"{eid}: no source_ids")
            for sid in refs:
                if sid not in sources:
                    raise CaseStudyValidationError(f"{eid}: unknown source {sid}")
                if _dt(sources[sid]["available_at"]) > known:
                    raise CaseStudyValidationError(f"{eid}: source {sid} was not available by KNOWN_AT")

        for obs in case.get("observations", []):
            oid=obs.get("observation_id")
            if not oid or oid in seen_observation_ids:
                raise CaseStudyValidationError(f"duplicate or missing observation_id: {oid!r}")
            seen_observation_ids.add(oid)
            known=_dt(obs["known_at"])
            _dt(obs["observed_at"])
            refs=obs.get("source_ids", [])
            if not refs:
                raise CaseStudyValidationError(f"{oid}: no source_ids")
            for sid in refs:
                if sid not in sources:
                    raise CaseStudyValidationError(f"{oid}: unknown source {sid}")
                if _dt(sources[sid]["available_at"]) > known:
                    raise CaseStudyValidationError(f"{oid}: source {sid} was not available by KNOWN_AT")
