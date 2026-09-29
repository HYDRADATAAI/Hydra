from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict, deque
from typing import Any, Dict, Iterable, List, Optional, Tuple


class EvidenceClass(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C = "C"
    D = "D"
    OPEN = "OPEN"


class ExposureState(str, Enum):
    CONFIRMED = "CONFIRMED"
    CANDIDATE = "CANDIDATE"
    DEFERRED = "DEFERRED"
    BLOCKED = "BLOCKED"


AUTO_PROPAGATE = {EvidenceClass.A1, EvidenceClass.A2}
CANDIDATE_ONLY = {EvidenceClass.B1, EvidenceClass.B2}
BLOCKED_EVIDENCE = {EvidenceClass.C, EvidenceClass.OPEN}


@dataclass(frozen=True)
class Node:
    node_id: str
    node_class: str
    name: str
    lifecycle_state: str = "operating"
    operational_from: Optional[str] = None
    jurisdiction: Optional[str] = None
    concentration: Dict[str, float] = field(default_factory=dict)
    substitution: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    edge_id: str
    from_node: str
    to_node: str
    relationship: str
    evidence_class: EvidenceClass
    impact_scope: str = "production"
    semantics: str = "dependency"
    active_from: Optional[str] = None
    active_to: Optional[str] = None
    source_ids: List[str] = field(default_factory=list)
    guardrail: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    target_node_id: str
    occurred_at: str
    known_at: str
    severity: float
    commodity: Optional[str] = None
    jurisdiction: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HopDecision:
    edge_id: str
    from_node: str
    to_node: str
    evidence_class: str
    state: str
    reason: str
    evidence_factor: float
    temporal_factor: float


@dataclass
class Exposure:
    node_id: str
    node_class: str
    node_name: str
    state: str
    path: List[str]
    edge_path: List[str]
    physical_severity_score: float
    concentration_score: Optional[float]
    substitution_friction_score: Optional[float]
    reasons: List[str]
    evidence_classes: List[str]


@dataclass
class TraversalResult:
    event: Dict[str, Any]
    exposures: List[Exposure]
    blocked_hops: List[HopDecision]
    deferred_hops: List[HopDecision]
    candidate_hops: List[HopDecision]
    audit_log: List[str]
    no_auto_trading_signal: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event,
            "exposures": [asdict(x) for x in self.exposures],
            "blocked_hops": [asdict(x) for x in self.blocked_hops],
            "deferred_hops": [asdict(x) for x in self.deferred_hops],
            "candidate_hops": [asdict(x) for x in self.candidate_hops],
            "audit_log": self.audit_log,
            "no_auto_trading_signal": self.no_auto_trading_signal,
        }


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def concentration_score(values: Dict[str, float]) -> Optional[float]:
    if not values:
        return None
    weights = {"production": 0.30, "processing": 0.30, "supplier": 0.20, "route": 0.20}
    total_w = 0.0
    total = 0.0
    for key, val in values.items():
        if key in weights:
            w = weights[key]
            total += max(0.0, min(100.0, float(val))) * w
            total_w += w
    if total_w == 0:
        return None
    return round(total / total_w, 2)


def substitution_friction_score(values: Dict[str, float]) -> Optional[float]:
    if not values:
        return None
    keys = ("technical", "qualification", "logistics", "lead_time")
    return round(sum(max(0.0, min(25.0, float(values.get(k, 0.0)))) for k in keys), 2)


def evidence_gate(edge: Edge) -> Tuple[ExposureState, float, str]:
    if edge.evidence_class in AUTO_PROPAGATE:
        factor = 1.00 if edge.evidence_class == EvidenceClass.A1 else 0.92
        return ExposureState.CONFIRMED, factor, "primary/official evidence permits bounded propagation"
    if edge.evidence_class in CANDIDATE_ONLY:
        factor = 0.70 if edge.evidence_class == EvidenceClass.B1 else 0.62
        return ExposureState.CANDIDATE, factor, "evidence narrows the path but does not prove exclusive/full dependency"
    if edge.evidence_class == EvidenceClass.D:
        return ExposureState.DEFERRED, 0.0, "flow is future/deferred and is not currently observable"
    return ExposureState.BLOCKED, 0.0, "analytical/open evidence cannot propagate as fact"


def temporal_gate(event: Event, edge: Edge, dest: Node) -> Tuple[ExposureState, float, str]:
    event_dt = _parse_dt(event.occurred_at)
    if not event_dt:
        return ExposureState.BLOCKED, 0.0, "event timestamp is invalid"
    edge_start = _parse_dt(edge.active_from)
    edge_end = _parse_dt(edge.active_to)
    if edge_start and event_dt < edge_start:
        return ExposureState.DEFERRED, 0.0, "edge is not active yet"
    if edge_end and event_dt > edge_end:
        return ExposureState.BLOCKED, 0.0, "edge is superseded/inactive"
    op_from = _parse_dt(dest.operational_from)
    state = dest.lifecycle_state.lower()
    if op_from and event_dt < op_from:
        if edge.impact_scope in {"construction", "commissioning", "infrastructure", "future_supply"}:
            return ExposureState.CANDIDATE, 0.45, "future facility may face buildout/commissioning exposure"
        return ExposureState.DEFERRED, 0.0, "future facility cannot create current production exposure"
    if state == "planned":
        if edge.impact_scope in {"construction", "future_supply"}:
            return ExposureState.CANDIDATE, 0.35, "planned node may face project exposure only"
        return ExposureState.DEFERRED, 0.0, "planned node is not current production"
    if state == "buildout":
        if edge.impact_scope in {"construction", "commissioning", "infrastructure", "future_supply"}:
            return ExposureState.CANDIDATE, 0.50, "buildout node may face project/commissioning exposure"
        return ExposureState.DEFERRED, 0.0, "buildout node is not current production"
    if state == "ramping":
        return ExposureState.CONFIRMED, 0.80, "ramping node has bounded current exposure"
    return ExposureState.CONFIRMED, 1.00, "operating node is temporally active"


def combine_states(*states: ExposureState) -> ExposureState:
    if ExposureState.BLOCKED in states:
        return ExposureState.BLOCKED
    if ExposureState.DEFERRED in states:
        return ExposureState.DEFERRED
    if ExposureState.CANDIDATE in states:
        return ExposureState.CANDIDATE
    return ExposureState.CONFIRMED


class ConstraintRuntime:
    def __init__(self, nodes: Iterable[Node], edges: Iterable[Edge]):
        self.nodes = {n.node_id: n for n in nodes}
        self.edges = list(edges)
        self.outgoing: Dict[str, List[Edge]] = defaultdict(list)
        for edge in self.edges:
            if edge.from_node not in self.nodes or edge.to_node not in self.nodes:
                raise ValueError(f"edge {edge.edge_id} references missing node")
            self.outgoing[edge.from_node].append(edge)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConstraintRuntime":
        nodes = [
            Node(
                node_id=x["node_id"],
                node_class=x["node_class"],
                name=x["name"],
                lifecycle_state=x.get("lifecycle_state", "operating"),
                operational_from=x.get("operational_from"),
                jurisdiction=x.get("jurisdiction"),
                concentration=x.get("concentration", {}),
                substitution=x.get("substitution", {}),
                tags=x.get("tags", []),
                metadata=x.get("metadata", {}),
            )
            for x in data["nodes"]
        ]
        edges = [
            Edge(
                edge_id=x["edge_id"],
                from_node=x["from_node"],
                to_node=x["to_node"],
                relationship=x["relationship"],
                evidence_class=EvidenceClass(x["evidence_class"]),
                impact_scope=x.get("impact_scope", "production"),
                semantics=x.get("semantics", "dependency"),
                active_from=x.get("active_from"),
                active_to=x.get("active_to"),
                source_ids=x.get("source_ids", []),
                guardrail=x.get("guardrail", ""),
                metadata=x.get("metadata", {}),
            )
            for x in data["edges"]
        ]
        return cls(nodes, edges)

    def evaluate_event(self, event: Event, max_hops: int = 8) -> TraversalResult:
        if event.target_node_id not in self.nodes:
            raise KeyError(f"unknown target node: {event.target_node_id}")
        if not (0 <= event.severity <= 1):
            raise ValueError("event severity must be between 0 and 1")
        exposures: List[Exposure] = []
        blocked_hops: List[HopDecision] = []
        deferred_hops: List[HopDecision] = []
        candidate_hops: List[HopDecision] = []
        audit: List[str] = []
        q = deque([(event.target_node_id, [event.target_node_id], [], ExposureState.CONFIRMED, 1.0, 1.0, [])])
        best_seen: Dict[Tuple[str, str], int] = {}
        while q:
            current, path, edge_path, inherited_state, inherited_evidence, inherited_temporal, ev_classes = q.popleft()
            if len(edge_path) >= max_hops:
                audit.append(f"max_hops reached at {current}")
                continue
            for edge in self.outgoing.get(current, []):
                dest = self.nodes[edge.to_node]
                e_state, e_factor, e_reason = evidence_gate(edge)
                t_state, t_factor, t_reason = temporal_gate(event, edge, dest)
                state = combine_states(inherited_state, e_state, t_state)
                if edge.semantics == "observed_route" and edge.evidence_class == EvidenceClass.B1:
                    state = combine_states(state, ExposureState.CANDIDATE)
                    e_reason += "; observed route is non-exclusive"
                decision = HopDecision(
                    edge_id=edge.edge_id,
                    from_node=edge.from_node,
                    to_node=edge.to_node,
                    evidence_class=edge.evidence_class.value,
                    state=state.value,
                    reason=f"{e_reason}; {t_reason}" + (f"; {edge.guardrail}" if edge.guardrail else ""),
                    evidence_factor=round(inherited_evidence * e_factor, 4),
                    temporal_factor=round(inherited_temporal * t_factor, 4),
                )
                if state == ExposureState.BLOCKED:
                    blocked_hops.append(decision)
                    audit.append(f"BLOCK {edge.edge_id}: {decision.reason}")
                    continue
                if state == ExposureState.DEFERRED:
                    deferred_hops.append(decision)
                    audit.append(f"DEFER {edge.edge_id}: {decision.reason}")
                    continue
                if state == ExposureState.CANDIDATE:
                    candidate_hops.append(decision)
                new_path = path + [dest.node_id]
                new_edge_path = edge_path + [edge.edge_id]
                new_ev_classes = ev_classes + [edge.evidence_class.value]
                evidence_factor = inherited_evidence * e_factor
                temporal_factor = inherited_temporal * t_factor
                conc = concentration_score(dest.concentration)
                sub = substitution_friction_score(dest.substitution)
                conc_factor = 0.55 if conc is None else (0.35 + 0.65 * conc / 100.0)
                sub_factor = 0.45 if sub is None else (0.30 + 0.70 * sub / 100.0)
                state_factor = 1.0 if state == ExposureState.CONFIRMED else 0.65
                severity = 100.0 * event.severity * evidence_factor * temporal_factor * conc_factor * sub_factor * state_factor
                severity = round(max(0.0, min(100.0, severity)), 2)
                exposures.append(Exposure(
                    node_id=dest.node_id,
                    node_class=dest.node_class,
                    node_name=dest.name,
                    state=state.value,
                    path=new_path,
                    edge_path=new_edge_path,
                    physical_severity_score=severity,
                    concentration_score=conc,
                    substitution_friction_score=sub,
                    reasons=[e_reason, t_reason] + ([edge.guardrail] if edge.guardrail else []),
                    evidence_classes=new_ev_classes,
                ))
                key = (dest.node_id, state.value)
                hops = len(new_edge_path)
                if best_seen.get(key, 999) <= hops:
                    continue
                best_seen[key] = hops
                q.append((dest.node_id, new_path, new_edge_path, state, evidence_factor, temporal_factor, new_ev_classes))
        exposures.sort(key=lambda x: (0 if x.state == ExposureState.CONFIRMED.value else 1, -x.physical_severity_score, x.node_id))
        return TraversalResult(
            event=asdict(event),
            exposures=exposures,
            blocked_hops=blocked_hops,
            deferred_hops=deferred_hops,
            candidate_hops=candidate_hops,
            audit_log=audit,
        )


def load_runtime_json(path: str) -> ConstraintRuntime:
    with open(path, "r", encoding="utf-8") as f:
        return ConstraintRuntime.from_dict(json.load(f))


def load_event_json(path: str) -> Event:
    with open(path, "r", encoding="utf-8") as f:
        return Event(**json.load(f))
