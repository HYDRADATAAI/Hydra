from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable


class ValidationError(ValueError):
    pass


class EventType(str, Enum):
    SANCTION = "SANCTION"
    EXPORT_CONTROL = "EXPORT_CONTROL"
    IMPORT_RESTRICTION = "IMPORT_RESTRICTION"
    TARIFF = "TARIFF"
    EMBARGO = "EMBARGO"
    NATIONALIZATION = "NATIONALIZATION"
    INDUSTRIAL_POLICY = "INDUSTRIAL_POLICY"
    TRADE_DISPUTE = "TRADE_DISPUTE"
    TERRITORIAL_DISPUTE = "TERRITORIAL_DISPUTE"
    STRATEGIC_RESOURCE_DISPUTE = "STRATEGIC_RESOURCE_DISPUTE"
    SHIPPING_DISRUPTION = "SHIPPING_DISRUPTION"
    PORT_RESTRICTION = "PORT_RESTRICTION"
    SUPPLY_AFFECTING_CONFLICT = "SUPPLY_AFFECTING_CONFLICT"
    ECONOMICALLY_RELEVANT_DIPLOMATIC_CHANGE = "ECONOMICALLY_RELEVANT_DIPLOMATIC_CHANGE"
    REGULATORY_CHANGE = "REGULATORY_CHANGE"
    INFRASTRUCTURE_POLICY = "INFRASTRUCTURE_POLICY"
    SUBSIDY = "SUBSIDY"
    INCENTIVE = "INCENTIVE"


class ClaimKind(str, Enum):
    DOCUMENTED_ACTION = "DOCUMENTED_ACTION"
    DOCUMENTED_EFFECT = "DOCUMENTED_EFFECT"
    ATTRIBUTED_EXPLANATION = "ATTRIBUTED_EXPLANATION"
    ANALYTICAL_INFERENCE = "ANALYTICAL_INFERENCE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TemporalFacts:
    known_at: datetime
    effective_at: datetime | None = None
    observed_at: datetime | None = None
    resolved_at: datetime | None = None

    def validate(self) -> None:
        # Every semantic clock must be timezone-aware. A naive clock cannot
        # safely participate in point-in-time replay.
        for label,ts in (
            ("known_at",self.known_at),
            ("effective_at",self.effective_at),
            ("observed_at",self.observed_at),
            ("resolved_at",self.resolved_at),
        ):
            if ts is not None and (ts.tzinfo is None or ts.utcoffset() is None):
                raise ValidationError(f"{label} must be timezone-aware")
        # Clocks are intentionally independent. Only resolution has a hard
        # semantic lower bound against an effective action when both exist.
        if self.effective_at and self.resolved_at and self.resolved_at < self.effective_at:
            raise ValidationError("resolved_at precedes effective_at")


@dataclass(frozen=True)
class Provenance:
    source_id: str
    document_id: str
    published_at: datetime
    available_at: datetime
    source_version: str
    content_digest: str
    stance: str = "supporting"
    supersedes: str | None = None

    def validate(self) -> None:
        if not all((self.source_id, self.document_id, self.source_version, self.content_digest)):
            raise ValidationError("incomplete provenance")
        if self.stance not in {"supporting", "opposing", "neutral"}:
            raise ValidationError("invalid evidence stance")


@dataclass(frozen=True)
class Relation:
    kind: str
    entity_id: str
    confidence: float
    provenance_document_ids: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.entity_id:
            raise ValidationError("unresolved entity reference")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValidationError("confidence outside [0,1]")


@dataclass(frozen=True)
class HistoricalEvent:
    event_id: str
    event_type: EventType
    title: str
    temporal: TemporalFacts
    provenance: tuple[Provenance, ...]
    relations: tuple[Relation, ...] = ()
    claim_kind: ClaimKind = ClaimKind.DOCUMENTED_ACTION
    statement: str = ""
    causal: bool = False
    causal_evidence_document_ids: tuple[str, ...] = ()
    motive_claim: bool = False
    attributed_to: str | None = None
    duplicate_of: str | None = None
    superseded_by: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.event_id or not self.title:
            raise ValidationError("event identity/title required")
        self.temporal.validate()
        if not self.provenance:
            raise ValidationError("material event requires provenance")
        for p in self.provenance:
            p.validate()
        docs = {p.document_id for p in self.provenance}
        # Information cannot be known before the evidence carrying it was available.
        if min(p.available_at for p in self.provenance) > self.temporal.known_at:
            raise ValidationError("known_at precedes all available evidence")
        for r in self.relations:
            r.validate()
            if not set(r.provenance_document_ids).issubset(docs):
                raise ValidationError("relation cites non-event provenance")
        if self.causal and not self.causal_evidence_document_ids:
            raise ValidationError("causal assertion lacks explicit evidence")
        if not set(self.causal_evidence_document_ids).issubset(docs):
            raise ValidationError("causal evidence is not in event provenance")
        if self.motive_claim and self.claim_kind == ClaimKind.DOCUMENTED_ACTION:
            raise ValidationError("motive cannot be encoded as documented action")
        if self.motive_claim and not self.attributed_to:
            raise ValidationError("motive/explanation must be attributed")

    def canonical_digest(self) -> str:
        payload = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "title": self.title,
            "known_at": self.temporal.known_at.isoformat(),
            "documents": sorted((p.document_id, p.source_version, p.content_digest) for p in self.provenance),
            "relations": sorted((r.kind, r.entity_id, r.confidence) for r in self.relations),
            "claim_kind": self.claim_kind.value,
            "statement": self.statement,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def eligible_as_of(events: Iterable[HistoricalEvent], as_of: datetime) -> list[HistoricalEvent]:
    """Return only evidence genuinely available by as_of; deterministic ordering."""
    eligible: list[HistoricalEvent] = []
    for event in events:
        event.validate()
        if event.temporal.known_at > as_of:
            continue
        available = [p for p in event.provenance if p.available_at <= as_of]
        if not available:
            continue
        # Do not expose later source versions through an earlier event shell.
        if len(available) != len(event.provenance):
            continue
        eligible.append(event)
    return sorted(eligible, key=lambda e: (e.temporal.known_at, e.event_id))


def active_events_as_of(
    events: Iterable[HistoricalEvent], as_of: datetime
) -> list[HistoricalEvent]:
    """Return historically knowable events whose effective state is active.

    This is deliberately distinct from eligible_as_of(), which answers what
    evidence was knowable and therefore retains resolved historical events.
    """
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValidationError("as_of must be timezone-aware")
    active: list[HistoricalEvent] = []
    for event in eligible_as_of(events, as_of):
        effective=event.temporal.effective_at
        resolved=event.temporal.resolved_at
        if effective is not None and effective > as_of:
            continue
        if resolved is not None and resolved <= as_of:
            continue
        active.append(event)
    return active


def warning_signs_as_of(
    events: Iterable[HistoricalEvent], constraint_entity_id: str, as_of: datetime
) -> list[HistoricalEvent]:
    """Point-in-time precursors linked to a constraint/dependency; no hindsight promotion."""
    return [
        e for e in eligible_as_of(events, as_of)
        if any(
            r.entity_id == constraint_entity_id and r.kind in {
                "CONSTRAINT", "DEPENDENCY", "RESOURCE", "INFRASTRUCTURE", "STRATEGIC_ASSET"
            }
            for r in e.relations
        )
    ]
