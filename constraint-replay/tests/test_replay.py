from datetime import datetime, timezone, timedelta
import pytest
from hydra_constraint_replay.models import Evidence,Hypothesis,Outcome,ReplayCase
from hydra_constraint_replay.replay import LeakageError,replay_case
from hydra_constraint_replay.metrics import evaluate_cases

UTC=timezone.utc
T=datetime(2020,1,1,tzinfo=UTC)

def ev(i, known):
    return Evidence(i,known,known,"https://example.invalid/source","sha256:test",{"fact":i})

def case(outcome="TRUE_POSITIVE", confidence=.8):
    return ReplayCase("c1",T,Hypothesis("constraint",confidence,"capacity loss","tightening"),[ev("e1",T-timedelta(days=1))],Outcome(outcome,outcome!="FALSE_POSITIVE",T+timedelta(days=10)))

def test_admissible_replay_freezes_prediction():
    r=replay_case(case())
    assert r["evidence_count"]==1 and len(r["prediction_hash"])==64

def test_future_evidence_is_rejected():
    c=case(); c.evidence.append(ev("poison",T+timedelta(seconds=1)))
    with pytest.raises(LeakageError): replay_case(c)

def test_missing_provenance_is_rejected():
    c=case(); c.evidence[0]=Evidence("e1",T,T,"","",{})
    with pytest.raises(LeakageError): replay_case(c)

def test_subsequent_event_cannot_be_preknown():
    c=case(); c.subsequent_events=[ev("future-side",T)]
    with pytest.raises(LeakageError): replay_case(c)

def test_metrics():
    m=evaluate_cases([case(),case("FALSE_POSITIVE",.7)])
    assert m["case_count"]==2
    assert m["false_positive_count"]==1
    assert m["precision"]==.5
