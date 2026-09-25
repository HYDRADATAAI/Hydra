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
from hydra_constraint_replay.models import Evidence


ROOT=Path(__file__).resolve().parents[2]
POLICY_DATA=ROOT/"constraint-geopolitical-policy"/"data"/"HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH002_SOURCED_HISTORICAL_CASES_20260925.json"
PHYSICAL_DATA=ROOT/"constraint-physical-dependency"/"data"/"HYDRA_CONSTRAINT_PHYSICAL_POLICY_GRAPH_BATCH002_SOURCED_20260925.json"
BATCH1_POLICY=ROOT/"constraint-geopolitical-policy"/"data"/"sourced_historical_cases.json"
UTC=timezone.utc


class Batch002EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=load_sourced_case_bundle(POLICY_DATA)
        cls.events=events_from_sourced_case_bundle(cls.bundle)
        cls.graph=load_sourced_policy_case_graph(PHYSICAL_DATA)

    def by_id(self,event_id):
        return next(e for e in self.events if e.event_id==event_id)

    def test_batch_shape(self):
        self.assertEqual(7,len(self.bundle["cases"]))
        self.assertEqual(9,len(self.bundle["sources"]))
        self.assertEqual(8,len(self.events))

    def test_batch1_and_batch2_event_ids_do_not_collide(self):
        batch1=events_from_sourced_case_bundle(load_sourced_case_bundle(BATCH1_POLICY))
        ids=[e.event_id for e in batch1+self.events]
        self.assertEqual(len(ids),len(set(ids)))

    def test_every_batch2_event_binds_and_emits_authoritative_replay_evidence(self):
        for event in self.events:
            with self.subTest(event=event.event_id):
                self.assertTrue(bind_event_to_physical_graph(event,self.graph))
                replay=to_replay_evidence(event)
                self.assertTrue(replay)
                self.assertTrue(all(isinstance(x,Evidence) for x in replay))

    def test_steel_tariff_was_known_before_effective_date(self):
        e=self.by_id("us-steel-tariff-proclamation-9705-2018")
        self.assertLess(e.temporal.known_at,e.temporal.effective_at)
        before=datetime(2018,3,15,23,59,58,tzinfo=UTC)
        after=datetime(2018,3,15,23,59,59,tzinfo=UTC)
        self.assertNotIn(e,eligible_as_of(self.events,before))
        self.assertIn(e,eligible_as_of(self.events,after))

    def test_gallium_germanium_controls_preserve_announcement_window(self):
        e=self.by_id("china-gallium-germanium-export-controls-2023")
        self.assertEqual(datetime(2023,8,1,0,0,tzinfo=UTC),e.temporal.effective_at)
        self.assertLess(e.temporal.known_at,e.temporal.effective_at)

    def test_imo_rule_preserves_multi_year_warning_window(self):
        e=self.by_id("imo-global-sulphur-limit-2020")
        lead=(e.temporal.effective_at-e.temporal.known_at).days
        self.assertGreater(lead,1100)
        self.assertIn(e,eligible_as_of(self.events,datetime(2017,1,1,tzinfo=UTC)))

    def test_uniper_control_edge_not_available_at_announcement(self):
        announced=self.by_id("germany-uniper-takeover-announced-2022-09-21")
        completed=self.by_id("germany-uniper-state-participation-completed-2022-12-22")
        a=bind_event_to_physical_graph(announced,self.graph)
        self.assertTrue(any(x.entity_id=="company:uniper" for x in a))
        self.assertIsNone(
            self.graph.resolve_reference(
                "edge:uniper-controlled-by-germany-2022",
                announced.temporal.known_at.date(),
                announced.temporal.known_at.date(),
            )
        )
        c=bind_event_to_physical_graph(completed,self.graph)
        self.assertTrue(any(x.entity_id=="edge:uniper-controlled-by-germany-2022" for x in c))

    def test_black_sea_grain_chain_reaches_three_ports(self):
        e=self.by_id("black-sea-grain-safe-transport-mechanism-2022")
        traced=trace_event_downstream(e,self.graph,max_depth=4)
        paths=traced["resource:ukrainian-grain-foodstuffs"]
        targets=set()
        for path in paths:
            targets.update(path)
        self.assertIn("edge:ukrainian-grain-transported-via-black-sea-corridor",targets)
        self.assertIn("edge:black-sea-corridor-requires-odesa",targets)
        self.assertIn("edge:black-sea-corridor-requires-chornomorsk",targets)
        self.assertIn("edge:black-sea-corridor-requires-yuzhny-pivdennyi",targets)

    def test_cbam_known_before_transitional_start(self):
        e=self.by_id("eu-cbam-reporting-rules-2023")
        self.assertLess(e.temporal.known_at,e.temporal.effective_at)

    def test_pdvsa_state_ownership_is_structurally_represented(self):
        paths=self.graph.as_of(
            datetime(2019,1,28,tzinfo=UTC).date(),
            datetime(2019,1,28,tzinfo=UTC).date(),
        ).trace("company:pdvsa")
        self.assertTrue(any(path[-1].target_id=="country:venezuela" for path in paths))


if __name__=="__main__":
    unittest.main()
