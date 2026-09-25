from dataclasses import asdict
from hashlib import sha256
import json
from .models import ReplayCase, OUTCOME_CLASSES

class LeakageError(ValueError):
    pass

def _stable_hash(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()

def replay_case(case: ReplayCase) -> dict:
    if not 0 <= case.hypothesis.confidence_at_t <= 1:
        raise ValueError("confidence_at_t must be within [0,1]")
    if case.outcome.outcome_class not in OUTCOME_CLASSES:
        raise ValueError("unknown outcome class")
    ids=set()
    for e in case.evidence:
        if e.evidence_id in ids:
            raise ValueError(f"duplicate evidence_id: {e.evidence_id}")
        ids.add(e.evidence_id)
        if e.known_at > case.replay_t:
            raise LeakageError(f"{e.evidence_id}: KNOWN_AT after REPLAY_T")
        if not e.source_uri or not e.source_hash:
            raise LeakageError(f"{e.evidence_id}: provenance incomplete")
    for e in case.subsequent_events:
        if e.known_at <= case.replay_t:
            raise LeakageError(f"{e.evidence_id}: subsequent event was already known at replay time")
    frozen = {
        "case_id": case.case_id,
        "replay_t": case.replay_t.isoformat(),
        "hypothesis": asdict(case.hypothesis),
        "admissible_evidence_ids": sorted(ids),
    }
    impact = case.outcome.impact_first_observed_at
    lead_days = None if impact is None else (impact-case.replay_t).total_seconds()/86400
    return {
        **frozen,
        "prediction_hash": _stable_hash(frozen),
        "outcome_class": case.outcome.outcome_class,
        "realized_constraint": case.outcome.realized_constraint,
        "lead_time_days": lead_days,
        "evidence_count": len(case.evidence),
        "provenance_complete": True,
        "leakage_violations": [],
    }
