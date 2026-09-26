"""Cross-domain binding between policy history and the physical dependency graph."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from hydra_constraint_physical import DependencyGraph, Edge, Node

from .model import HistoricalEvent, Relation, ValidationError


PHYSICAL_RELATION_KINDS = {
    "RESOURCE",
    "INFRASTRUCTURE",
    "STRATEGIC_ASSET",
    "DEPENDENCY",
    "CONSTRAINT",
}

NODE_KIND_COMPATIBILITY = {
    "RESOURCE": {"resource"},
    "INFRASTRUCTURE": {"infrastructure", "transport"},
    "STRATEGIC_ASSET": {
        "deposit_source", "extraction", "processing", "transport",
        "infrastructure", "manufacturing", "bottleneck",
    },
    "DEPENDENCY": {
        "extraction", "processing", "transport", "infrastructure",
        "manufacturing", "product_technology", "company", "country", "bottleneck",
    },
    "CONSTRAINT": {"bottleneck"},
}

EDGE_RELATION_COMPATIBILITY = {
    "DEPENDENCY": {
        "extracted_by", "feeds", "processed_by", "transported_via", "requires",
        "manufactures", "used_in", "depends_on", "constrains", "controlled_by", "supplies",
    },
    "CONSTRAINT": {"constrains"},
}


class PhysicalBindingError(ValidationError):
    pass


@dataclass(frozen=True)
class PhysicalBinding:
    relation_kind: str
    entity_id: str
    reference_type: str
    physical_kind: str
    confidence: float


def _physical_when(event: HistoricalEvent, physical_when: datetime | date | None) -> date:
    if physical_when is not None:
        return physical_when.date() if isinstance(physical_when, datetime) else physical_when
    anchor = event.temporal.effective_at or event.temporal.observed_at or event.temporal.known_at
    return anchor.date()


def bind_event_to_physical_graph(
    event: HistoricalEvent,
    graph: DependencyGraph,
    physical_when: datetime | date | None = None,
) -> tuple[PhysicalBinding, ...]:
    """Validate physical references using the graph's point-in-time resolver.

    Physical validity is evaluated at EFFECTIVE_AT when present (otherwise
    OBSERVED_AT/KNOWN_AT), while knowledge is always cut off at event KNOWN_AT.
    That permits known planned actions to reference a future-effective asset
    without allowing evidence learned after the event into the binding.
    """
    event.validate()
    when = _physical_when(event, physical_when)
    knowledge_cutoff = event.temporal.known_at.date()
    out: list[PhysicalBinding] = []

    for relation in event.relations:
        if relation.kind not in PHYSICAL_RELATION_KINDS:
            continue

        resolved = graph.resolve_reference(
            relation.entity_id,
            when=when,
            knowledge_cutoff=knowledge_cutoff,
        )
        if resolved is None:
            raise PhysicalBindingError(
                f"{event.event_id}: unresolved or not-yet-knowable physical reference "
                f"{relation.kind}:{relation.entity_id}"
            )

        ref_type, obj = resolved
        if ref_type == "node":
            assert isinstance(obj, Node)
            allowed = NODE_KIND_COMPATIBILITY.get(relation.kind, set())
            if obj.kind not in allowed:
                raise PhysicalBindingError(
                    f"{event.event_id}: {relation.kind}:{relation.entity_id} resolves to "
                    f"node kind {obj.kind!r}, expected one of {sorted(allowed)}"
                )
            physical_kind = obj.kind
        else:
            assert isinstance(obj, Edge)
            allowed_relations = EDGE_RELATION_COMPATIBILITY.get(relation.kind, set())
            if obj.relation not in allowed_relations:
                raise PhysicalBindingError(
                    f"{event.event_id}: {relation.kind}:{relation.entity_id} resolves to "
                    f"edge relation {obj.relation!r}, expected one of {sorted(allowed_relations)}"
                )
            physical_kind = obj.relation

        out.append(PhysicalBinding(
            relation_kind=relation.kind,
            entity_id=relation.entity_id,
            reference_type=ref_type,
            physical_kind=physical_kind,
            confidence=relation.confidence,
        ))

    return tuple(out)


def trace_event_downstream(
    event: HistoricalEvent,
    graph: DependencyGraph,
    physical_when: datetime | date | None = None,
    max_depth: int = 12,
) -> dict[str, tuple[tuple[str, ...], ...]]:
    """Return structural downstream edge paths from bound physical references.

    This is reachability evidence only, not a forecast of economic outcome.
    """
    bindings = bind_event_to_physical_graph(event, graph, physical_when)
    when = _physical_when(event, physical_when)
    view = graph.as_of(when, event.temporal.known_at.date())
    result: dict[str, tuple[tuple[str, ...], ...]] = {}

    for binding in bindings:
        resolved = view.resolve_reference(binding.entity_id)
        if resolved is None:
            raise PhysicalBindingError(f"binding disappeared from point-in-time view: {binding.entity_id}")
        ref_type, obj = resolved

        if ref_type == "node":
            paths = view.trace(binding.entity_id, max_depth=max_depth)
            result[binding.entity_id] = tuple(tuple(edge.edge_id for edge in path) for path in paths)
            continue

        edge = obj
        assert isinstance(edge, Edge)
        downstream = view.trace(edge.target_id, max_depth=max(0, max_depth - 1))
        paths = [(edge,)] + [tuple([edge, *path]) for path in downstream]
        result[binding.entity_id] = tuple(tuple(e.edge_id for e in path) for path in paths)

    return result
