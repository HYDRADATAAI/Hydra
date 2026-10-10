from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from hydra_constraint_replay.replay import LeakageError, replay_case
from test_replay import T, case


@pytest.mark.parametrize(
    ("field", "label"),
    [
        ("effective_at", "EFFECTIVE_AT"),
        ("resolved_at", "RESOLVED_AT"),
    ],
)
def test_optional_evidence_timestamps_must_be_timezone_aware(field, label):
    replay = case()
    replay.evidence[0] = replace(
        replay.evidence[0], **{field: datetime(2019, 12, 31)}
    )

    with pytest.raises(LeakageError, match=f"e1.{label}: timezone-aware timestamp required"):
        replay_case(replay)


@pytest.mark.parametrize("field", ["effective_at", "resolved_at"])
def test_optional_evidence_timestamps_are_frozen_into_prediction_hash(field):
    original = case()
    changed = case()
    changed.evidence[0] = replace(
        changed.evidence[0],
        **{field: T - timedelta(days=1)},
    )

    assert replay_case(original)["prediction_hash"] != replay_case(changed)["prediction_hash"]


def test_optional_evidence_timestamps_allow_none():
    assert replay_case(case())["provenance_complete"] is True
