from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

OUTCOME_CLASSES = {
    "TRUE_POSITIVE","FALSE_POSITIVE","TRUE_NEGATIVE","FALSE_NEGATIVE",
    "PARTIAL_REALIZATION","RIGHT_MECHANISM_WRONG_TIMING",
    "RIGHT_CONSTRAINT_WRONG_BENEFICIARY","INVALIDATED","UNRESOLVED","UNEVALUABLE",
}

@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    known_at: datetime
    observed_at: datetime
    source_uri: str
    source_hash: str
    payload: dict
    effective_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

@dataclass(frozen=True)
class Hypothesis:
    constraint_candidate: str
    confidence_at_t: float
    expected_mechanism: str
    expected_direction: str
    expected_horizon_days: Optional[int] = None
    invalidators: tuple[str, ...] = ()
    geography: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    infrastructure: tuple[str, ...] = ()
    affected_entities: tuple[str, ...] = ()

@dataclass(frozen=True)
class Outcome:
    outcome_class: str
    realized_constraint: Optional[bool]
    impact_first_observed_at: Optional[datetime] = None
    beneficiary_outcomes: tuple[str, ...] = ()
    exposure_outcomes: tuple[str, ...] = ()
    false_negative_evidence: tuple[str, ...] = ()

@dataclass
class ReplayCase:
    case_id: str
    replay_t: datetime
    hypothesis: Hypothesis
    evidence: list[Evidence]
    outcome: Outcome
    subsequent_events: list[Evidence] = field(default_factory=list)
