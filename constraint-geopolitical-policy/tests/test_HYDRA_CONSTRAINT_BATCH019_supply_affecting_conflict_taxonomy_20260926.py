import unittest
from datetime import date
from pathlib import Path

from hydra_constraint_physical import load_sourced_policy_case_graph
from hydra_constraint_policy.case_studies import (
    events_from_sourced_case_bundle,
    load_sourced_case_bundle,
)
from hydra_constraint_policy.model import EventType
from hydra_constraint_policy.physical_adapter import (
    bind_event_to_physical_graph,
    trace_event_downstream,
)
from hydra_constraint_replay.corpus import load_replay_ready_corpus


ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/"constraint-geopolitical-policy"/"data"/"HYDRA_CONSTRAINT_GEOPOLITICAL_POLICY_BATCH019_SUPPLY_AFFECTING_CONFLICT_20260926.json"
PHYSICAL=ROOT/"constraint-physical-dependency"/"data"/"HYDRA_CONSTRAINT_PHYSICAL_POLICY_BATCH019_SUPPLY_AFFECTING_CONFLICT_20260926.json"
REPLAY=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl"


class Batch019SupplyAffectingConflictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=load_sourced_case_bundle(POLICY)
        cls.events=events_from_sourced_case_bundle(cls.bundle)
        cls.graph=load_sourced_policy_case_graph(PHYSICAL)
        cls.replay=load_replay_ready_corpus(REPLAY)

    def test_supplement_shape(self):
        self.assertEqual(1,len(self.bundle["cases"]))
        self.assertEqual(1,len(self.events))
        self.assertEqual(1,len(self.bundle["cases"][0]["observations"]))

    def test_closes_supply_affecting_conflict_event_type(self):
        event=self.events[0]
        self.assertEqual(EventType.SUPPLY_AFFECTING_CONFLICT,event.event_type)
        self.assertEqual(
            "ukraine-war-agricultural-supply-shock-2022-taxonomy-supplement",
            event.metadata["case_id"],
        )

    def test_event_binds_to_authoritative_physical_graph(self):
        event=self.events[0]
        bindings=bind_event_to_physical_graph(event,self.graph)
        self.assertEqual(3,len(bindings))
        self.assertEqual(
            {
                "resource:ukraine-grain-supply-conflict-2022",
                "extraction:ukraine-agricultural-production-conflict-2022",
                "bottleneck:ukraine-war-agricultural-supply-shock-2022",
            },
            {binding.entity_id for binding in bindings},
        )

    def test_april_cut_does_not_leak_july_export_logistics(self):
        april=self.graph.as_of(date(2022,4,26),date(2022,4,26))
        self.assertIsNone(
            april.resolve_reference(
                "transport:ukraine-grain-export-logistics-conflict-2022"
            )
        )
        self.assertIsNone(
            april.resolve_reference(
                "infrastructure:ukraine-grain-storage-conflict-2022"
            )
        )
        july=self.graph.as_of(date(2022,7,5),date(2022,7,5))
        self.assertIsNotNone(
            july.resolve_reference(
                "transport:ukraine-grain-export-logistics-conflict-2022"
            )
        )
        self.assertIsNotNone(
            july.resolve_reference(
                "infrastructure:ukraine-grain-storage-conflict-2022"
            )
        )

    def test_conflict_constraint_has_structural_downstream_reachability(self):
        traces=trace_event_downstream(self.events[0],self.graph,max_depth=4)
        paths=traces["bottleneck:ukraine-war-agricultural-supply-shock-2022"]
        self.assertTrue(paths)
        self.assertTrue(any(
            "edge:ukraine-war-bottleneck-constrains-agricultural-production-2022"
            in path
            for path in paths
        ))

    def test_taxonomy_supplement_does_not_mutate_frozen_replay_case_set(self):
        replay_ids={row["case_id"] for row in self.replay}
        self.assertNotIn(
            "ukraine-war-agricultural-supply-shock-2022-taxonomy-supplement",
            replay_ids,
        )
        self.assertEqual(22,len(replay_ids))


if __name__=="__main__":
    unittest.main()
