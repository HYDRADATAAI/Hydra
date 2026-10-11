from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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
    frozen = replay_case(_case())

    assert frozen["evidence"][0]["effective_at"] is None
    assert frozen["evidence"][0]["resolved_at"] is None
    assert frozen["provenance_complete"] is True

def test_future_resolution_does_not_change_as_of_prediction_hash():
    original = _case()
    with_future_resolution = _case()
    with_future_resolution.evidence[0] = replace(
        with_future_resolution.evidence[0],
        resolved_at=REPLAY_T + timedelta(days=5),
    )

    original_frozen = replay_case(original)
    future_frozen = replay_case(with_future_resolution)

    assert future_frozen["evidence"][0]["resolved_at"] is None
    assert future_frozen["prediction_hash"] == original_frozen["prediction_hash"]


def test_ambiguous_fold_known_at_after_replay_is_rejected_by_utc_instant():
    eastern = ZoneInfo("America/New_York")
    replay = _case()
    replay.replay_t = datetime(2024, 11, 3, 1, 30, tzinfo=eastern, fold=0)
    replay.evidence[0] = replace(
        replay.evidence[0],
        known_at=datetime(2024, 11, 3, 1, 15, tzinfo=eastern, fold=1),
        observed_at=datetime(2024, 11, 3, 1, 15, tzinfo=eastern, fold=1),
    )

    with pytest.raises(LeakageError, match="KNOWN_AT after REPLAY_T"):
        replay_case(replay)


def test_ambiguous_fold_subsequent_event_is_later_by_utc_instant():
    eastern = ZoneInfo("America/New_York")
    replay = _case()
    replay.replay_t = datetime(2024, 11, 3, 1, 30, tzinfo=eastern, fold=0)
    replay.outcome = replace(replay.outcome, impact_first_observed_at=None)
    replay.subsequent_events = [
        replace(
            replay.evidence[0],
            known_at=datetime(2024, 11, 3, 1, 15, tzinfo=eastern, fold=1),
        )
    ]

    assert replay_case(replay)["case_id"] == "c1"


def test_ambiguous_fold_impact_lead_time_uses_utc_instant():
    eastern = ZoneInfo("America/New_York")
    replay = _case()
    replay.replay_t = datetime(2024, 11, 3, 1, 30, tzinfo=eastern, fold=0)
    replay.outcome = replace(
        replay.outcome,
        impact_first_observed_at=datetime(2024, 11, 3, 1, 15, tzinfo=eastern, fold=1),
    )

    frozen = replay_case(replay)

    assert frozen["lead_time_days"] == pytest.approx(45 / 1440)


def test_ambiguous_fold_earlier_known_at_uses_utc_instant():
    eastern = ZoneInfo("America/New_York")
    replay = _case()
    replay.replay_t = datetime(2024, 11, 3, 1, 15, tzinfo=eastern, fold=1)
    replay.outcome = replace(replay.outcome, impact_first_observed_at=None)
    replay.evidence[0] = replace(
        replay.evidence[0],
        known_at=datetime(2024, 11, 3, 1, 45, tzinfo=eastern, fold=0),
        observed_at=datetime(2024, 11, 3, 1, 45, tzinfo=eastern, fold=0),
    )

    assert replay_case(replay)["case_id"] == "c1"
