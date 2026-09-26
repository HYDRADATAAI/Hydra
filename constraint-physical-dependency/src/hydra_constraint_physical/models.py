from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

NodeKind = Literal[
    "resource","deposit_source","extraction","processing","transport",
    "infrastructure","manufacturing","product_technology","company",
    "country","bottleneck","substitute","beneficiary"
]

@dataclass(frozen=True)
class Provenance:
    source_id: str
    source_url: str
    publisher: str
    retrieved_at: date
    known_at: date
    published_at: date | None = None
    locator: str | None = None
    evidence_hash: str | None = None

@dataclass(frozen=True)
class Snapshot:
    valid_from: date
    valid_to: date | None = None
    known_at: date | None = None
    capacity_nameplate: float | None = None
    capacity_usable: float | None = None
    capacity_unit: str | None = None
    utilization: float | None = None
    market_share: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def active_as_of(self, when: date, knowledge_cutoff: date | None = None) -> bool:
        valid = self.valid_from <= when and (self.valid_to is None or when < self.valid_to)
        if not valid:
            return False
        if knowledge_cutoff is None:
            return True
        # Point-in-time replay is fail-closed: a state with no historical
        # knowledge timestamp cannot be treated as knowable merely because its
        # world-time validity interval includes the query date.
        return self.known_at is not None and self.known_at <= knowledge_cutoff

@dataclass(frozen=True)
class Node:
    node_id: str
    kind: NodeKind
    name: str
    country_code: str | None = None
    snapshots: tuple[Snapshot, ...] = ()
    provenance: tuple[Provenance, ...] = ()

@dataclass(frozen=True)
class Edge:
    edge_id: str
    source_id: str
    target_id: str
    relation: str
    valid_from: date
    valid_to: date | None = None
    known_at: date | None = None
    share: float | None = None
    capacity: float | None = None
    capacity_unit: str | None = None
    substitution_time_days: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    provenance: tuple[Provenance, ...] = ()

    def active_as_of(self, when: date, knowledge_cutoff: date | None = None) -> bool:
        valid = self.valid_from <= when and (self.valid_to is None or when < self.valid_to)
        if not valid:
            return False
        if knowledge_cutoff is None:
            return True
        # Missing knowledge time is UNKNOWN, never implicitly historical.
        return self.known_at is not None and self.known_at <= knowledge_cutoff
