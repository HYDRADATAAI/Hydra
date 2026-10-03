"""Adapter from geopolitical/policy events into HYDRA Constraint replay evidence."""
from __future__ import annotations

from hydra_constraint_replay.models import Evidence

from .model import HistoricalEvent


def to_replay_evidence(event: HistoricalEvent) -> list[Evidence]:
    """Emit the authoritative replay Evidence model for each source document.

    Fail closed: event validation runs first, and every provenance document must
    expose an official/resolvable source URI in event metadata.
    """
    event.validate()
    source_uris=event.metadata.get("source_uris", {})
    if not isinstance(source_uris, dict):
        raise ValueError("metadata.source_uris must be a document_id -> URI mapping")

    records: list[Evidence]=[]
    for p in event.provenance:
        uri=source_uris.get(p.document_id)
        if not uri:
            raise ValueError(f"missing source URI for {p.document_id}")

        observed=event.temporal.observed_at or event.temporal.known_at
        records.append(Evidence(
            evidence_id=f"{event.event_id}:{p.document_id}:{p.source_version}",
            known_at=max(event.temporal.known_at,p.available_at),
            observed_at=observed,
            source_uri=uri,
            source_hash=p.content_digest,
            effective_at=event.temporal.effective_at,
            payload={
                "event_id":event.event_id,
                "event_type":event.event_type.value,
                "title":event.title,
                "claim_kind":event.claim_kind.value,
                "statement":event.statement,
                "relations":[
                    {
                        "kind":r.kind,
                        "entity_id":r.entity_id,
                        "confidence":r.confidence,
                    }
                    for r in event.relations
                ],
                "resolved_at":(
                    event.temporal.resolved_at.isoformat()
                    if event.temporal.resolved_at else None
                ),
            },
        ))
    return records
