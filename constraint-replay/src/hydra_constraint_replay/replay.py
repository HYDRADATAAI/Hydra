from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
from .models import ReplayCase, OUTCOME_CLASSES

class LeakageError(ValueError):
    pass

def _stable_hash(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()

def _require_aware(ts: datetime, label: str) -> None:
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise LeakageError(f"{label}: timezone-aware timestamp required")

def replay_case(case: ReplayCase) -> dict:
    _require_aware(case.replay_t, "REPLAY_T")
    if not 0 <= case.hypothesis.confidence_at_t <= 1:
        raise ValueError("confidence_at_t must be within [0,1]")
    if case.outcome.outcome_class not in OUTCOME_CLASSES:
        raise ValueError("unknown outcome class")

    ids=set()
    evidence_fingerprints=[]
    for e in case.evidence:
        _require_aware(e.known_at, f"{e.evidence_id}.KNOWN_AT")
        _require_aware(e.observed_at, f"{e.evidence_id}.OBSERVED_AT")
        if e.evidence_id in ids:
            raise ValueError(f"duplicate evidence_id: {e.evidence_id}")
        ids.add(e.evidence_id)
        if e.known_at > case.replay_t:
            raise LeakageError(f"{e.evidence_id}: KNOWN_AT after REPLAY_T")
        if not e.source_uri or not e.source_hash:
            raise LeakageError(f"{e.evidence_id}: provenance incomplete")
        evidence_fingerprints.append({
            "evidence_id":e.evidence_id,
            "known_at":e.known_at.isoformat(),
            "observed_at":e.observed_at.isoformat(),
            "effective_at":None if e.effective_at is None else e.effective_at.isoformat(),
            "source_uri":e.source_uri,
            "source_hash":e.source_hash,
            "payload_hash":_stable_hash(e.payload),
        })

    for e in case.subsequent_events:
        _require_aware(e.known_at, f"{e.evidence_id}.KNOWN_AT")
        if e.known_at <= case.replay_t:
            raise LeakageError(f"{e.evidence_id}: subsequent event was already known at replay time")

    frozen = {
        "case_id":case.case_id,
        "replay_t":case.replay_t.isoformat(),
        "hypothesis":asdict(case.hypothesis),
        "evidence":sorted(evidence_fingerprints,key=lambda x:x["evidence_id"]),
    }
    impact=case.outcome.impact_first_observed_at
    if impact is not None:
        _require_aware(impact, "IMPACT_FIRST_OBSERVED_AT")
        if impact <= case.replay_t:
            raise LeakageError("outcome impact is not subsequent to REPLAY_T")
    lead_days=None if impact is None else (impact-case.replay_t).total_seconds()/86400
    return {
        **frozen,
        "prediction_hash":_stable_hash(frozen),
        "outcome_class":case.outcome.outcome_class,
        "realized_constraint":case.outcome.realized_constraint,
        "lead_time_days":lead_days,
        "evidence_count":len(case.evidence),
        "provenance_complete":True,
        "leakage_violations":[],
    }
