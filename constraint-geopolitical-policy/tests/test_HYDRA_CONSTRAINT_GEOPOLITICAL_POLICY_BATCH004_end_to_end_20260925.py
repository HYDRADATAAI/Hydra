import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from hydra_constraint_physical import load_sourced_policy_case_graph
from hydra_constraint_physical.sourced_case_graph import SourcedGraphValidationError
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
POLICY_DATA=ROOT/"constraint-geopolitical-policy"/"data"/"HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH004_SOURCED_HISTORICAL_CASES_20260925.json"
PHYSICAL_DATA=ROOT/"constraint-physical-dependency"/"data"/"HYDRA_CONSTRAINT_PHYSICAL_POLICY_GRAPH_BATCH004_SOURCED_20260925.json"
BATCH1=ROOT/"constraint-geopolitical-policy"/"data"/"sourced_historical_cases.json"
BATCH2=ROOT/"constraint-geopolitical-policy"/"data"/"HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH002_SOURCED_HISTORICAL_CASES_20260925.json"
BATCH3=ROOT/"constraint-geopolitical-policy"/"data"/"HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH003_SOURCED_HISTORICAL_CASES_20260925.json"
UTC=timezone.utc


class Batch004EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=load_sourced_case_bundle(POLICY_DATA)
        cls.events=events_from_sourced_case_bundle(cls.bundle)
        cls.graph=load_sourced_policy_case_graph(PHYSICAL_DATA)

    def by_id(self,event_id):
        return next(e for e in self.events if e.event_id==event_id)

    def test_batch_shape(self):
        self.assertEqual(5,len(self.bundle["cases"]))
        self.assertEqual(10,len(self.bundle["sources"]))
        self.assertEqual(6,len(self.events))

    def test_event_ids_unique_across_first_four_batches(self):
        prior=[]
        for path in (BATCH1,BATCH2,BATCH3):
            prior.extend(events_from_sourced_case_bundle(load_sourced_case_bundle(path)))
        ids=[e.event_id for e in prior+self.events]
        self.assertEqual(len(ids),len(set(ids)))

    def test_every_batch4_event_binds_and_emits_authoritative_replay_evidence(self):
        for event in self.events:
            with self.subTest(event=event.event_id):
                self.assertTrue(bind_event_to_physical_graph(event,self.graph))
                evidence=to_replay_evidence(event)
                self.assertTrue(evidence)
                self.assertTrue(all(isinstance(x,Evidence) for x in evidence))

    def test_japan_korea_case_does_not_leak_september_material_identities_into_july(self):
        e=self.by_id("japan-korea-export-licensing-change-2019-07")
        self.assertEqual(EventType.ECONOMICALLY_RELEVANT_DIPLOMATIC_CHANGE,e.event_type)
        self.assertGreater(e.temporal.known_at,e.temporal.effective_at)
        self.assertEqual(
            {
                "resource:japan-korea-controlled-tech-materials-2019",
                "manufacturing:korea-semiconductor-display-production-2019",
            },
            {r.entity_id for r in e.relations},
        )
        july_ids={b.entity_id for b in bind_event_to_physical_graph(e,self.graph)}
        self.assertNotIn("resource:fluorinated-polyimide-japan-korea-2019",july_ids)

    def test_eastern_mediterranean_case_preserves_source_attribution(self):
        e=self.by_id("eu-eastern-mediterranean-drilling-framework-2019-11-11")
        self.assertEqual(EventType.TERRITORIAL_DISPUTE,e.event_type)
        self.assertIn("Council",e.statement)
        traced=trace_event_downstream(e,self.graph,max_depth=3)
        self.assertIn(
            (
                "edge:eastmed-hydrocarbons-extracted-by-offshore-drilling",
                "edge:eastmed-offshore-drilling-located-at-cyprus-framework",
            ),
            traced["resource:eastern-mediterranean-hydrocarbons-eu-framework-2019"],
        )

    def test_nord_stream_certification_states_remain_separate(self):
        suspended=self.by_id("nord-stream-2-certification-suspended-2021-11-16")
        halted=self.by_id("nord-stream-2-certification-halted-2022-02-22")
        self.assertEqual(EventType.REGULATORY_CHANGE,suspended.event_type)
        self.assertEqual(EventType.INFRASTRUCTURE_POLICY,halted.event_type)
        cut=datetime(2022,1,1,tzinfo=UTC)
        ids={e.event_id for e in eligible_as_of(self.events,cut)}
        self.assertIn(suspended.event_id,ids)
        self.assertNotIn(halted.event_id,ids)

    def test_45x_incentive_is_known_before_program_effective_date(self):
        e=self.by_id("us-section45x-advanced-manufacturing-credit-enacted-2022")
        self.assertEqual(EventType.INCENTIVE,e.event_type)
        self.assertLess(e.temporal.known_at,e.temporal.effective_at)
        self.assertIsNone(
            self.graph.resolve_reference(
                "manufacturing:us-section45x-eligible-production",
                datetime(2022,8,16,tzinfo=UTC).date(),
                datetime(2022,8,16,tzinfo=UTC).date(),
            )
        )
        self.assertTrue(bind_event_to_physical_graph(e,self.graph))

    def test_wilhelmshaven_capacity_is_typed_and_point_in_time(self):
        e=self.by_id("wilhelmshaven-lng-terminal-opened-2022-12-17")
        self.assertLess(e.temporal.known_at,e.temporal.effective_at)
        self.assertIsNone(
            self.graph.resolve_reference(
                "infrastructure:wilhelmshaven-lng-fsru-esperanza",
                datetime(2022,12,17,tzinfo=UTC).date(),
                datetime(2022,12,17,tzinfo=UTC).date(),
            )
        )
        kind,node=self.graph.resolve_reference(
            "infrastructure:wilhelmshaven-lng-fsru-esperanza",
            datetime(2023,1,1,tzinfo=UTC).date(),
            datetime(2022,12,17,tzinfo=UTC).date(),
        )
        self.assertEqual("node",kind)
        self.assertEqual(5.0,node.snapshots[0].capacity_nameplate)
        self.assertEqual("bcm/year",node.snapshots[0].capacity_unit)
        edge=self.graph.edges["edge:wilhelmshaven-fsru-supplies-direct-lng-imports"]
        self.assertEqual(5.0,edge.capacity)
        self.assertEqual("bcm/year",edge.capacity_unit)

    def test_sourced_graph_rejects_non_numeric_capacity(self):
        raw=json.loads(PHYSICAL_DATA.read_text(encoding="utf-8"))
        target=next(n for n in raw["nodes"] if n["node_id"]=="infrastructure:wilhelmshaven-lng-fsru-esperanza")
        target["capacity_nameplate"]="five"
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"
            p.write_text(json.dumps(raw),encoding="utf-8")
            with self.assertRaisesRegex(SourcedGraphValidationError,"capacity_nameplate must be numeric"):
                load_sourced_policy_case_graph(p)

    def test_sourced_graph_rejects_negative_edge_capacity(self):
        raw=json.loads(PHYSICAL_DATA.read_text(encoding="utf-8"))
        raw["edges"][-1]["capacity"]=-1
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"
            p.write_text(json.dumps(raw),encoding="utf-8")
            with self.assertRaisesRegex(SourcedGraphValidationError,"negative capacity"):
                load_sourced_policy_case_graph(p)


if __name__=="__main__":
    unittest.main()
