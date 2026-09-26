from datetime import datetime, timezone, timedelta
import pytest
from hydra_constraint_replay.models import Evidence,Hypothesis,Outcome,ReplayCase
from hydra_constraint_replay.replay import LeakageError,replay_case
from hydra_constraint_replay.metrics import evaluate_cases

UTC=timezone.utc
T=datetime(2020,1,1,tzinfo=UTC)

def ev(i, known, payload=None):
    return Evidence(i,known,known,"https://example.invalid/source","sha256:test",payload or {"fact":i})

def case(outcome="TRUE_POSITIVE", confidence=.8):
    realized={"FALSE_POSITIVE":False,"TRUE_NEGATIVE":False}.get(outcome,True)
    impact=None if outcome=="TRUE_NEGATIVE" else T+timedelta(days=10)
    return ReplayCase("c1",T,Hypothesis("constraint",confidence,"capacity loss","tightening"),[ev("e1",T-timedelta(days=1))],Outcome(outcome,realized,impact))

def test_admissible_replay_freezes_full_evidence_identity():
    r=replay_case(case())
    assert r["evidence_count"]==1 and len(r["prediction_hash"])==64
    assert r["evidence"][0]["payload_hash"]

def test_prediction_hash_changes_if_historical_payload_changes():
    a=case(); b=case()
    b.evidence[0]=ev("e1",T-timedelta(days=1),{"fact":"changed"})
    assert replay_case(a)["prediction_hash"] != replay_case(b)["prediction_hash"]

def test_future_evidence_is_rejected():
    c=case(); c.evidence.append(ev("poison",T+timedelta(seconds=1)))
    with pytest.raises(LeakageError): replay_case(c)

def test_missing_provenance_is_rejected():
    c=case(); c.evidence[0]=Evidence("e1",T,T,"","",{})
    with pytest.raises(LeakageError): replay_case(c)

def test_subsequent_event_cannot_be_preknown():
    c=case(); c.subsequent_events=[ev("future-side",T)]
    with pytest.raises(LeakageError): replay_case(c)

def test_pre_replay_outcome_is_rejected():
    c=case(); c.outcome=Outcome("TRUE_POSITIVE",True,T)
    with pytest.raises(LeakageError): replay_case(c)

def test_naive_timestamps_are_rejected():
    c=case(); c.replay_t=datetime(2020,1,1)
    with pytest.raises(LeakageError): replay_case(c)

def test_metrics():
    m=evaluate_cases([case(),case("FALSE_POSITIVE",.7),case("TRUE_NEGATIVE",.2)])
    assert m["case_count"]==3
    assert m["false_positive_count"]==1
    assert m["precision"]==.5
    assert m["false_positive_rate"]==.5
    assert m["median_lead_time_days"]==10
