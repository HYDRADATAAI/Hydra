"""Adapter from geopolitical/policy events into HYDRA Constraint replay evidence.

This module intentionally mirrors the public constraint-replay Evidence contract
without importing that package. It keeps this branch independently testable while
making the eventual integration mechanical rather than semantic.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from .model import HistoricalEvent


@dataclass(frozen=True)
class ReplayEvidenceRecord:
    evidence_id: str
    known_at: datetime
    observed_at: datetime
    source_uri: str
    source_hash: str
    payload: dict
    effective_at: datetime | None = None


def to_replay_evidence(event: HistoricalEvent) -> list[ReplayEvidenceRecord]:
    """Emit one replay evidence record per provenance document.

    Fail closed: event validation runs first, and the source must expose a
    resolvable URI in event metadata keyed by document ID.
    """
    event.validate()
    source_uris = event.metadata.get("source_uris", {})
    if not isinstance(source_uris, dict):
        raise ValueError("metadata.source_uris must be a document_id -> URI mapping")

    records: list[ReplayEvidenceRecord] = []
    for p in event.provenance:
        uri = source_uris.get(p.document_id)
        if not uri:
            raise ValueError(f"missing source URI for {p.document_id}")
        observed = event.temporal.observed_at or event.temporal.known_at
        records.append(ReplayEvidenceRecord(
            evidence_id=f"{event.event_id}:{p.document_id}:{p.source_version}",
            known_at=max(event.temporal.known_at, p.available_at),
            observed_at=observed,
            source_uri=uri,
            source_hash=p.content_digest,
            effective_at=event.temporal.effective_at,
            payload={
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "title": event.title,
                "claim_kind": event.claim_kind.value,
                "statement": event.statement,
                "relations": [
                    {"kind": r.kind, "entity_id": r.entity_id, "confidence": r.confidence}
                    for r in event.relations
                ],
                "resolved_at": event.temporal.resolved_at.isoformat()
                    if event.temporal.resolved_at else None,
            },
        ))
    return records
