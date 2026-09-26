from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .model import (
    ClaimKind,
    EventType,
    HistoricalEvent,
    Provenance,
    Relation,
    TemporalFacts,
)


class CaseStudyValidationError(ValueError):
    pass


ALLOWED_BINDING_STATUSES={
    "PENDING_CANONICAL_PHYSICAL_ENTITY_POPULATION",
    "BOUND_MINIMAL_CANONICAL_SUBGRAPH",
}
ALLOWED_PHYSICAL_RELATIONS={
    "RESOURCE",
    "INFRASTRUCTURE",
    "STRATEGIC_ASSET",
    "DEPENDENCY",
    "CONSTRAINT",
}


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

        binding_status=case.get("binding_status")
        if binding_status not in ALLOWED_BINDING_STATUSES:
            raise CaseStudyValidationError(f"{cid}: unsupported binding status {binding_status!r}")

        for event in case.get("events", []):
            eid=event.get("event_id")
            if not eid or eid in seen_event_ids:
                raise CaseStudyValidationError(f"duplicate or missing event_id: {eid!r}")
            seen_event_ids.add(eid)
            if event.get("event_type") not in allowed_events:
                raise CaseStudyValidationError(f"{eid}: unsupported event_type")
            try:
                ClaimKind(event.get("claim_kind"))
            except ValueError as exc:
                raise CaseStudyValidationError(f"{eid}: unsupported claim_kind") from exc

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

            relations=event.get("relations", [])
            if binding_status=="BOUND_MINIMAL_CANONICAL_SUBGRAPH" and not relations:
                raise CaseStudyValidationError(f"{eid}: bound case event has no canonical physical relations")
            if binding_status=="PENDING_CANONICAL_PHYSICAL_ENTITY_POPULATION" and relations:
                raise CaseStudyValidationError(f"{eid}: pending case cannot claim canonical physical relations")
            for relation in relations:
                kind=relation.get("kind")
                entity_id=relation.get("entity_id")
                confidence=relation.get("confidence")
                if kind not in ALLOWED_PHYSICAL_RELATIONS:
                    raise CaseStudyValidationError(f"{eid}: unsupported physical relation kind {kind!r}")
                if not entity_id:
                    raise CaseStudyValidationError(f"{eid}: empty physical entity_id")
                if not isinstance(confidence,(int,float)) or not 0 <= confidence <= 1:
                    raise CaseStudyValidationError(f"{eid}: physical relation confidence outside [0,1]")

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


def events_from_sourced_case_bundle(bundle: dict[str, Any]) -> list[HistoricalEvent]:
    """Materialize validated case JSON as executable HistoricalEvent objects."""
    validate_sourced_case_bundle(bundle)
    sources={s["source_id"]:s for s in bundle["sources"]}
    out: list[HistoricalEvent]=[]

    for case in bundle["cases"]:
        for raw in case.get("events", []):
            source_ids=tuple(raw["source_ids"])
            provenance=tuple(
                Provenance(
                    source_id=sid,
                    document_id=sid,
                    published_at=_dt(sources[sid]["published_at"]),
                    available_at=_dt(sources[sid]["available_at"]),
                    source_version="1",
                    content_digest=sources[sid]["evidence_digest"],
                    stance="supporting",
                )
                for sid in source_ids
            )
            relations=tuple(
                Relation(
                    kind=r["kind"],
                    entity_id=r["entity_id"],
                    confidence=float(r["confidence"]),
                    provenance_document_ids=source_ids,
                )
                for r in raw.get("relations", [])
            )
            event=HistoricalEvent(
                event_id=raw["event_id"],
                event_type=EventType(raw["event_type"]),
                title=raw["event_id"].replace("-", " "),
                temporal=TemporalFacts(
                    known_at=_dt(raw["known_at"]),
                    effective_at=_dt(raw["effective_at"]) if raw.get("effective_at") else None,
                    observed_at=_dt(raw["observed_at"]) if raw.get("observed_at") else None,
                    resolved_at=_dt(raw["resolved_at"]) if raw.get("resolved_at") else None,
                ),
                provenance=provenance,
                relations=relations,
                claim_kind=ClaimKind(raw["claim_kind"]),
                statement=raw["statement"],
                metadata={
                    "case_id":case["case_id"],
                    "binding_status":case["binding_status"],
                    "source_uris":{sid:sources[sid]["url"] for sid in source_ids},
                },
            )
            event.validate()
            out.append(event)

    return out
