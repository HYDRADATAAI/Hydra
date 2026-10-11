"""Synthetic adapter regressions; no historical availability claim is made."""
from datetime import datetime, timedelta, timezone
import unittest

from hydra_constraint_policy.model import (
    EventType, HistoricalEvent, Provenance, TemporalFacts,
)
from hydra_constraint_policy.replay_adapter import to_replay_evidence
from hydra_constraint_replay.models import Hypothesis, Outcome, ReplayCase
from hydra_constraint_replay.replay import replay_case


T = datetime(2020, 1, 1, tzinfo=timezone.utc)


def event(resolved_at=None):
    known = T - timedelta(days=2)
    return HistoricalEvent(
        "synthetic-resolution", EventType.SHIPPING_DISRUPTION,
        "Synthetic disruption", TemporalFacts(known, known, known, resolved_at),
        (Provenance("synthetic", "doc", known, known, "v1", "sha256:fixture"),),
        statement="Synthetic fixture only.",
        metadata={"source_uris": {"doc": "https://example.invalid/fixture"}},
    )


def freeze(resolved_at=None):
    return replay_case(ReplayCase(
        "synthetic-resolution", T,
        Hypothesis("capacity", 0.5, "disruption", "tightening"),
        to_replay_evidence(event(resolved_at)), Outcome("UNRESOLVED", None),
    ))


class ReplayResolutionCutoffTests(unittest.TestCase):
    def test_adapter_routes_resolution_through_typed_evidence_clock(self):
        resolution = T - timedelta(days=1)
        evidence = to_replay_evidence(event(resolution))[0]
        self.assertEqual(resolution, evidence.resolved_at)
        self.assertNotIn("resolved_at", evidence.payload)

    def test_future_resolution_does_not_leak_through_payload_hash(self):
        original = freeze()
        for delta in (timedelta(microseconds=1), timedelta(days=5)):
            with self.subTest(delta=delta):
                future = freeze(T + delta)
                self.assertEqual(original["prediction_hash"], future["prediction_hash"])
                self.assertEqual(original["evidence"], future["evidence"])

    def test_resolution_at_cutoff_is_frozen_and_changes_identity(self):
        frozen = freeze(T)
        self.assertEqual(T.isoformat(), frozen["evidence"][0]["resolved_at"])
        self.assertNotEqual(freeze()["prediction_hash"], frozen["prediction_hash"])

    def test_past_resolution_changes_identity_without_changing_payload(self):
        original = freeze()
        past = freeze(T - timedelta(days=1))
        self.assertEqual(original["evidence"][0]["payload_hash"], past["evidence"][0]["payload_hash"])
        self.assertNotEqual(original["prediction_hash"], past["prediction_hash"])


if __name__ == "__main__":
    unittest.main()
