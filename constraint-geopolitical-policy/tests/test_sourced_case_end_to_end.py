import unittest
from datetime import datetime, timezone
from pathlib import Path

from hydra_constraint_physical import load_sourced_policy_case_graph
from hydra_constraint_policy.case_studies import (
    events_from_sourced_case_bundle,
    load_sourced_case_bundle,
)
from hydra_constraint_policy.model import eligible_as_of
from hydra_constraint_policy.physical_adapter import (
    bind_event_to_physical_graph,
    trace_event_downstream,
)
from hydra_constraint_policy.replay_adapter import to_replay_evidence


ROOT=Path(__file__).resolve().parents[2]
POLICY_DATA=ROOT/"constraint-geopolitical-policy"/"data"/"sourced_historical_cases.json"
PHYSICAL_DATA=ROOT/"constraint-physical-dependency"/"data"/"sourced_policy_case_physical_graph.json"
UTC=timezone.utc


class SourcedCaseEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=load_sourced_case_bundle(POLICY_DATA)
        cls.events=events_from_sourced_case_bundle(cls.bundle)
        cls.graph=load_sourced_policy_case_graph(PHYSICAL_DATA)

    def test_every_sourced_event_binds_to_real_physical_graph(self):
        for event in self.events:
            with self.subTest(event=event.event_id):
                bindings=bind_event_to_physical_graph(event,self.graph)
                self.assertTrue(bindings)

    def test_every_sourced_event_emits_replay_evidence(self):
        for event in self.events:
            with self.subTest(event=event.event_id):
                evidence=to_replay_evidence(event)
                self.assertTrue(evidence)
                self.assertTrue(all(r.known_at <= event.temporal.known_at for r in evidence))

    def test_suez_constraint_reaches_canal_and_maritime_traffic(self):
        event=next(e for e in self.events if e.event_id=="suez-grounding-disruption-known-2021-03-26")
        traced=trace_event_downstream(event,self.graph)
        self.assertIn(
            (
                "edge:suez-grounding-constrains-canal",
                "edge:suez-canal-supplies-maritime-traffic",
            ),
            traced["bottleneck:suez-canal-grounding-2021"],
        )

    def test_replay_cut_before_bis_announcement_sees_no_bis_event(self):
        before=datetime(2022,10,6,23,59,59,tzinfo=UTC)
        ids={e.event_id for e in eligible_as_of(self.events,before)}
        self.assertFalse(any(i.startswith("bis-") for i in ids))

    def test_replay_cut_on_bis_announcement_sees_all_announced_controls(self):
        cutoff=datetime(2022,10,7,0,0,0,tzinfo=UTC)
        ids={e.event_id for e in eligible_as_of(self.events,cutoff)}
        self.assertIn("bis-sme-controls-2022-10-07",ids)
        self.assertIn("bis-us-person-support-controls-2022-10-12",ids)
        self.assertIn("bis-advanced-computing-controls-2022-10-21",ids)


if __name__=="__main__":
    unittest.main()
