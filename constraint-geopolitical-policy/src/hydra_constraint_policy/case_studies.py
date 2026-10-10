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
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise CaseStudyValidationError("invalid timestamp") from exc
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise CaseStudyValidationError("timezone-aware timestamp required")
    return ts


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaseStudyValidationError(f"{label} must be an object")
    return value


def _require_array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CaseStudyValidationError(f"{label} must be an array")
    return value


def _require_fields(value: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in value]
    if missing:
        raise CaseStudyValidationError(
            f"{label}: missing required field(s): {', '.join(missing)}"
        )


def _require_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CaseStudyValidationError(f"{label} must be non-empty text")
    return value


def load_sourced_case_bundle(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        bundle=json.load(fh)
    validate_sourced_case_bundle(bundle)
    return bundle


def validate_sourced_case_bundle(bundle: dict[str, Any]) -> None:
    bundle = _require_object(bundle, "bundle")
    if bundle.get("evidence_digest_scope") != "sha256(normalized_evidence UTF-8)":
        raise CaseStudyValidationError("unsupported evidence digest scope")

    sources={}
    source_items = _require_array(bundle.get("sources", []), "sources")
    for index, raw_source in enumerate(source_items):
        label = f"sources[{index}]"
        source = _require_object(raw_source, label)
        _require_fields(
            source,
            ("source_id", "url", "normalized_evidence", "evidence_digest", "published_at", "available_at"),
            label,
        )
        sid=_require_identifier(source.get("source_id"), f"{label}.source_id")
        if sid in sources:
            raise CaseStudyValidationError(f"duplicate or missing source_id: {sid!r}")
        if not str(source.get("url", "")).startswith("https://"):
            raise CaseStudyValidationError(f"{sid}: non-HTTPS source")
        evidence=source.get("normalized_evidence", "")
        if not isinstance(evidence, str):
            raise CaseStudyValidationError(f"{sid}: normalized_evidence must be text")
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

    case_items = _require_array(bundle.get("cases", []), "cases")
    for case_index, raw_case in enumerate(case_items):
        case_label = f"cases[{case_index}]"
        case = _require_object(raw_case, case_label)
        _require_fields(case, ("case_id", "binding_status"), case_label)
        cid=_require_identifier(case.get("case_id"), f"{case_label}.case_id")
        if cid in seen_case_ids:
            raise CaseStudyValidationError(f"duplicate or missing case_id: {cid!r}")
        seen_case_ids.add(cid)

        binding_status=case.get("binding_status")
        if not isinstance(binding_status, str) or binding_status not in ALLOWED_BINDING_STATUSES:
            raise CaseStudyValidationError(f"{cid}: unsupported binding status {binding_status!r}")

        events = _require_array(case.get("events", []), f"{cid}.events")
        for event_index, raw_event in enumerate(events):
            event_label = f"{cid}.events[{event_index}]"
            event = _require_object(raw_event, event_label)
            _require_fields(
                event,
                ("event_id", "event_type", "claim_kind", "known_at", "source_ids", "statement"),
                event_label,
            )
            eid=_require_identifier(event.get("event_id"), f"{event_label}.event_id")
            if eid in seen_event_ids:
                raise CaseStudyValidationError(f"duplicate or missing event_id: {eid!r}")
            seen_event_ids.add(eid)
            event_type = event.get("event_type")
            if not isinstance(event_type, str) or event_type not in allowed_events:
                raise CaseStudyValidationError(f"{eid}: unsupported event_type")
            try:
                ClaimKind(event.get("claim_kind"))
            except (TypeError, ValueError) as exc:
                raise CaseStudyValidationError(f"{eid}: unsupported claim_kind") from exc

            known=_dt(event["known_at"])
            for clock in ("effective_at", "observed_at", "resolved_at"):
                if event.get(clock) is not None:
                    _dt(event[clock])

            refs = _require_array(event.get("source_ids", []), f"{eid}.source_ids")
            if not refs:
                raise CaseStudyValidationError(f"{eid}: no source_ids")
            for sid in refs:
                sid = _require_identifier(sid, f"{eid}.source_ids item")
                if sid not in sources:
                    raise CaseStudyValidationError(f"{eid}: unknown source {sid}")
                if _dt(sources[sid]["available_at"]) > known:
                    raise CaseStudyValidationError(f"{eid}: source {sid} was not available by KNOWN_AT")

            relations = _require_array(event.get("relations", []), f"{eid}.relations")
            if binding_status=="BOUND_MINIMAL_CANONICAL_SUBGRAPH" and not relations:
                raise CaseStudyValidationError(f"{eid}: bound case event has no canonical physical relations")
            if binding_status=="PENDING_CANONICAL_PHYSICAL_ENTITY_POPULATION" and relations:
                raise CaseStudyValidationError(f"{eid}: pending case cannot claim canonical physical relations")
            for relation_index, raw_relation in enumerate(relations):
                relation_label = f"{eid}.relations[{relation_index}]"
                relation = _require_object(raw_relation, relation_label)
                _require_fields(relation, ("kind", "entity_id", "confidence"), relation_label)
                kind=relation.get("kind")
                entity_id=relation.get("entity_id")
                confidence=relation.get("confidence")
                if not isinstance(kind, str) or kind not in ALLOWED_PHYSICAL_RELATIONS:
                    raise CaseStudyValidationError(f"{eid}: unsupported physical relation kind {kind!r}")
                if not entity_id:
                    raise CaseStudyValidationError(f"{eid}: empty physical entity_id")
                if not isinstance(confidence,(int,float)) or not 0 <= confidence <= 1:
                    raise CaseStudyValidationError(f"{eid}: physical relation confidence outside [0,1]")

        observations = _require_array(case.get("observations", []), f"{cid}.observations")
        for observation_index, raw_observation in enumerate(observations):
            observation_label = f"{cid}.observations[{observation_index}]"
            obs = _require_object(raw_observation, observation_label)
            _require_fields(
                obs,
                ("observation_id", "known_at", "observed_at", "source_ids"),
                observation_label,
            )
            oid=_require_identifier(obs.get("observation_id"), f"{observation_label}.observation_id")
            if oid in seen_observation_ids:
                raise CaseStudyValidationError(f"duplicate or missing observation_id: {oid!r}")
            seen_observation_ids.add(oid)
            known=_dt(obs["known_at"])
            _dt(obs["observed_at"])
            refs = _require_array(obs.get("source_ids", []), f"{oid}.source_ids")
            if not refs:
                raise CaseStudyValidationError(f"{oid}: no source_ids")
            for sid in refs:
                sid = _require_identifier(sid, f"{oid}.source_ids item")
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
                    effective_at=(
                        _dt(raw["effective_at"])
                        if raw.get("effective_at") is not None
                        else None
                    ),
                    observed_at=(
                        _dt(raw["observed_at"])
                        if raw.get("observed_at") is not None
                        else None
                    ),
                    resolved_at=(
                        _dt(raw["resolved_at"])
                        if raw.get("resolved_at") is not None
                        else None
                    ),
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
