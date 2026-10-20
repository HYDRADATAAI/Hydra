"""Hash-contract controls for PR388's intentional optional-clock schema change."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

from hydra_constraint_replay.models import Evidence, Hypothesis, Outcome, ReplayCase
from hydra_constraint_replay.replay import replay_case


T = datetime(2020, 1, 1, tzinfo=timezone.utc)


def case():
    return ReplayCase(
        "synthetic-hash-contract", T,
        Hypothesis("capacity", 0.5, "disruption", "tightening"),
        [Evidence(i, T, T, "https://example.invalid/fixture", "sha256:fixture", {"id": i})
         for i in ("b", "a")],
        Outcome("UNRESOLVED", None),
    )


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_current_hash_is_recomputable_from_public_frozen_prediction():
    row = replay_case(case())
    frozen = {key: row[key] for key in ("case_id", "replay_t", "hypothesis", "evidence")}
    assert row["prediction_hash"] == digest(frozen)
    # PR388 deliberately changes even unresolved records' legacy identity.
    legacy = json.loads(json.dumps(frozen))
    for evidence in legacy["evidence"]:
        assert evidence.pop("resolved_at") is None
    assert row["prediction_hash"] != digest(legacy)


def test_evidence_order_and_subsequent_outcome_do_not_change_prediction_identity():
    original = case()
    changed = case()
    changed.evidence.reverse()
    changed.outcome = Outcome("TRUE_POSITIVE", True, T + timedelta(days=1))
    changed.subsequent_events = [replace(changed.evidence[0], known_at=T + timedelta(days=1))]
    assert replay_case(original)["prediction_hash"] == replay_case(changed)["prediction_hash"]


def test_resolution_cutoff_includes_equal_instant_with_another_offset():
    replay = case()
    resolution = T.astimezone(timezone(timedelta(hours=2)))
    replay.evidence[0] = replace(replay.evidence[0], resolved_at=resolution)
    row = replay_case(replay)
    assert next(e for e in row["evidence"] if e["evidence_id"] == "b")["resolved_at"] == resolution.isoformat()
    assert row["prediction_hash"] != replay_case(case())["prediction_hash"]
