from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from hydra_constraint_replay.models import Evidence, Hypothesis, Outcome, ReplayCase
from hydra_constraint_replay.replay import LeakageError, replay_case


UTC = timezone.utc
REPLAY_T = datetime(2020, 1, 1, tzinfo=UTC)


def _case():
    evidence = Evidence(
        "e1",
        REPLAY_T - timedelta(days=1),
        REPLAY_T - timedelta(days=1),
        "https://example.invalid/source",
        "sha256:test",
        {"fact": "e1"},
    )
    hypothesis = Hypothesis("constraint", 0.8, "capacity loss", "tightening")
    outcome = Outcome("TRUE_POSITIVE", True, REPLAY_T + timedelta(days=10))
    return ReplayCase("c1", REPLAY_T, hypothesis, [evidence], outcome)


@pytest.mark.parametrize(
    ("field", "label"),
    [
        ("effective_at", "EFFECTIVE_AT"),
        ("resolved_at", "RESOLVED_AT"),
    ],
)
def test_optional_evidence_timestamps_must_be_timezone_aware(field, label):
    replay = _case()
    replay.evidence[0] = replace(
        replay.evidence[0], **{field: datetime(2019, 12, 31)}
    )

    with pytest.raises(LeakageError, match=f"e1.{label}: timezone-aware timestamp required"):
        replay_case(replay)


@pytest.mark.parametrize("field", ["effective_at", "resolved_at"])
def test_optional_evidence_timestamps_are_frozen_into_prediction_hash(field):
    original = _case()
    changed = _case()
    changed.evidence[0] = replace(
        changed.evidence[0],
        **{field: REPLAY_T - timedelta(days=1)},
    )

    assert replay_case(original)["prediction_hash"] != replay_case(changed)["prediction_hash"]


def test_optional_evidence_timestamps_allow_none():
    assert replay_case(_case())["provenance_complete"] is True
