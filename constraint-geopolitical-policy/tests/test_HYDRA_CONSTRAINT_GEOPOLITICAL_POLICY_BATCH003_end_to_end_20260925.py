import unittest
from datetime import datetime, timezone
from pathlib import Path

from hydra_constraint_physical import load_sourced_policy_case_graph
from hydra_constraint_policy.case_studies import (
    events_from_sourced_case_bundle,
    load_sourced_case_bundle,
)
from hydra_constraint_policy.model import EventType, eligible_as_of
from hydra_constraint_policy.physical_adapter import (
    bind_event_to_physical_graph,
    trace_event_downstream,
)
from hydra_constraint_policy.replay_adapter import to_replay_evidence
from hydra_constraint_replay.models import Evidence


ROOT=Path(__file__).resolve().parents[2]
POLICY_DATA=ROOT/"constraint-geopolitical-policy"/"data"/"HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH003_SOURCED_HISTORICAL_CASES_20260925.json"
PHYSICAL_DATA=ROOT/"constraint-physical-dependency"/"data"/"HYDRA_CONSTRAINT_PHYSICAL_POLICY_GRAPH_BATCH003_SOURCED_20260925.json"
BATCH1=ROOT/"constraint-geopolitical-policy"/"data"/"sourced_historical_cases.json"
BATCH2=ROOT/"constraint-geopolitical-policy"/"data"/"HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH002_SOURCED_HISTORICAL_CASES_20260925.json"
UTC=timezone.utc


class Batch003EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=load_sourced_case_bundle(POLICY_DATA)
        cls.events=events_from_sourced_case_bundle(cls.bundle)
        cls.graph=load_sourced_policy_case_graph(PHYSICAL_DATA)

    def by_id(self,event_id):
        return next(e for e in self.events if e.event_id==event_id)

    def test_batch_shape(self):
        self.assertEqual(6,len(self.bundle["cases"]))
        self.assertEqual(10,len(self.bundle["sources"]))
        self.assertEqual(10,len(self.events))

    def test_event_ids_unique_across_first_three_batches(self):
        b1=events_from_sourced_case_bundle(load_sourced_case_bundle(BATCH1))
        b2=events_from_sourced_case_bundle(load_sourced_case_bundle(BATCH2))
        ids=[e.event_id for e in b1+b2+self.events]
        self.assertEqual(len(ids),len(set(ids)))

    def test_every_batch3_event_binds_and_emits_authoritative_replay_evidence(self):
        for event in self.events:
            with self.subTest(event=event.event_id):
                self.assertTrue(bind_event_to_physical_graph(event,self.graph))
                replay=to_replay_evidence(event)
                self.assertTrue(replay)
                self.assertTrue(all(isinstance(x,Evidence) for x in replay))

    def test_embargo_and_port_restriction_are_first_class_event_types(self):
        self.assertEqual(
            EventType.EMBARGO,
            self.by_id("russia-food-import-embargo-announced-2014-08-07").event_type,
        )
        self.assertEqual(
            EventType.PORT_RESTRICTION,
            self.by_id("eu-russian-flagged-vessels-port-entry-ban-2022-04-08").event_type,
        )

    def test_date_only_publication_is_not_leaked_to_start_of_day(self):
        e=self.by_id("russia-food-import-embargo-announced-2014-08-07")
        morning=datetime(2014,8,7,12,0,0,tzinfo=UTC)
        end=datetime(2014,8,7,23,59,59,tzinfo=UTC)
        self.assertNotIn(e,eligible_as_of(self.events,morning))
        self.assertIn(e,eligible_as_of(self.events,end))

    def test_port_restriction_traverses_vessel_to_port_scope(self):
        e=self.by_id("eu-russian-flagged-vessels-port-entry-ban-2022-04-08")
        traced=trace_event_downstream(e,self.graph)
        self.assertIn(
            ("edge:russian-flagged-vessels-use-eu-ports",),
            traced["transport:russian-flagged-vessels-2022"],
        )

    def test_subsidy_case_links_industrial_capacity_to_battery_value_chain(self):
        e=self.by_id("eu-battery-ipcei-state-aid-approved-2019-12")
        self.assertEqual(EventType.SUBSIDY,e.event_type)
        traced=trace_event_downstream(e,self.graph)
        self.assertIn(
            ("edge:eu-battery-ipcei-manufactures-battery-value-chain",),
            traced["manufacturing:eu-battery-ipcei-participants-2019"],
        )

    def test_panama_warning_and_adjustment_clocks_remain_separate(self):
        restriction=self.by_id("panama-canal-transit-reductions-a48-2023")
        adjustment=self.by_id("panama-canal-transit-adjustment-a54-2023")
        self.assertLess(restriction.temporal.known_at,restriction.temporal.effective_at)
        self.assertLess(adjustment.temporal.known_at,adjustment.temporal.effective_at)
        self.assertLess(restriction.temporal.known_at,adjustment.temporal.known_at)

    def test_panama_constraint_reaches_canal_water_and_transit(self):
        e=self.by_id("panama-canal-transit-reductions-a48-2023")
        traced=trace_event_downstream(e,self.graph,max_depth=4)
        paths=traced["bottleneck:panama-canal-water-deficit-2023"]
        edge_ids={edge_id for path in paths for edge_id in path}
        self.assertIn("edge:panama-water-deficit-constrains-canal",edge_ids)
        self.assertIn("edge:panama-canal-requires-gatun-water",edge_ids)
        self.assertIn("edge:panama-canal-supplies-transit",edge_ids)

    def test_section301_trade_dispute_preserves_escalation_sequence(self):
        july_cut=datetime(2018,7,1,tzinfo=UTC)
        august_cut=datetime(2018,8,10,tzinfo=UTC)
        september_cut=datetime(2018,9,19,tzinfo=UTC)
        def trade_ids(cut):
            return {
                e.event_id for e in eligible_as_of(self.events,cut)
                if e.event_id.startswith("us-section301-")
            }
        self.assertEqual({"us-section301-list1-action-2018"},trade_ids(july_cut))
        self.assertEqual(
            {"us-section301-list1-action-2018","us-section301-list2-action-2018"},
            trade_ids(august_cut),
        )
        self.assertEqual(
            {
                "us-section301-list1-action-2018",
                "us-section301-list2-action-2018",
                "us-section301-list3-action-2018",
            },
            trade_ids(september_cut),
        )

    def test_section301_all_actions_known_before_effective_date(self):
        for event_id in (
            "us-section301-list1-action-2018",
            "us-section301-list2-action-2018",
            "us-section301-list3-action-2018",
        ):
            e=self.by_id(event_id)
            self.assertEqual(EventType.TRADE_DISPUTE,e.event_type)
            self.assertLess(e.temporal.known_at,e.temporal.effective_at)

    def test_rare_earth_resource_dispute_binds_three_resources(self):
        e=self.by_id("wto-rare-earths-dsb-adoption-2014-08-29")
        self.assertEqual(EventType.STRATEGIC_RESOURCE_DISPUTE,e.event_type)
        bindings=bind_event_to_physical_graph(e,self.graph)
        self.assertEqual(
            {
                "resource:rare-earths-wto-dispute-2014",
                "resource:tungsten-wto-dispute-2014",
                "resource:molybdenum-wto-dispute-2014",
            },
            {b.entity_id for b in bindings},
        )

    def test_rare_earth_implementation_observation_is_later_than_dsb_adoption(self):
        event=self.by_id("wto-rare-earths-dsb-adoption-2014-08-29")
        case=next(c for c in self.bundle["cases"] if c["case_id"]=="wto-china-rare-earths-resource-dispute-2014-2015")
        obs=datetime.fromisoformat(case["observations"][0]["known_at"].replace("Z","+00:00"))
        self.assertGreater(obs,event.temporal.known_at)


if __name__=="__main__":
    unittest.main()
