from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"

def load(name):
    with (BASE / name).open("r", encoding="utf-8") as f:
        return json.load(f)

class FirstSlicePopulationSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json")
        cls.fields = load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_FIELD_MATRIX_V001_20260925.json")
        cls.evidence = load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_EVIDENCE_SEED_V001_20260925.json")
        cls.graph = load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_GRAPH_SEED_V001_20260925.json")
        cls.status = load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_POPULATION_STATUS_V001_20260925.json")

    def test_live_source_gate_is_not_bypassed(self):
        self.assertFalse(self.sources["live_source_authority_used"])
        self.assertEqual("NO", self.status["results"]["LIVE_SOURCE_USED"])

    def test_first_field_scope_is_frozen_to_24(self):
        self.assertEqual(24, self.fields["field_count"])
        self.assertEqual(24, len(self.fields["fields"]))

    def test_strict_replay_fails_closed_without_available_at(self):
        self.assertFalse(self.evidence["strict_original_as_of_ready"])
        self.assertEqual("NO", self.status["results"]["STRICT_ORIGINAL_AS_OF_READY"])
        self.assertTrue(all(not s["strict_original_as_of_eligible"] for s in self.sources["sources"]))

    def test_supported_edges_have_evidence(self):
        evidence_ids = {x["evidence_id"] for x in self.evidence["observations"]}
        for edge in self.graph["edges"]:
            if edge["status"] == "SUPPORTED_SEED":
                self.assertTrue(edge["evidence_ids"], edge["edge_id"])
                self.assertTrue(set(edge["evidence_ids"]) <= evidence_ids, edge["edge_id"])

    def test_source_gap_edges_are_explicit(self):
        gaps = [x for x in self.graph["edges"] if x["status"] == "UNPOPULATED_SOURCE_GAP"]
        self.assertEqual(3, len(gaps))
        self.assertTrue(all(not x["evidence_ids"] for x in gaps))

    def test_every_evidence_observation_resolves_to_registered_source(self):
        source_ids = {x["source_id"] for x in self.sources["sources"]}
        self.assertTrue(source_ids)
        for obs in self.evidence["observations"]:
            self.assertIn(obs["source_id"], source_ids)

    def test_population_is_partial_not_run_ready(self):
        self.assertEqual("YES_PARTIAL", self.status["results"]["GRAPH_SEED_READY"])
        self.assertEqual("BLOCKED", self.status["results"]["FIRST_SERIOUS_CONSTRAINT_RUN"])
        self.assertEqual("PIT-001-EXACT-ACQUIRED-AT-AND-AVAILABLE-AT-CAPTURE", self.status["next_population_blocker"])

if __name__ == "__main__":
    unittest.main()
