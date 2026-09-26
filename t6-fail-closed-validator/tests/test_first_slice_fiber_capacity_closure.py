from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"

SOURCE = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_EXTENSION_V001_20260925.json"
EVIDENCE = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_FIBER_EVIDENCE_SUPPLEMENT_V001_20260925.json"
FIELDS = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_FIBER_FIELD_OVERLAY_V001_20260925.json"
GRAPH = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_FIBER_GRAPH_OVERLAY_V001_20260925.json"
STATUS = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_GAP_STATUS_V001_20260925.json"


def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


class FirstSliceFiberCapacityClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load(SOURCE)
        cls.evidence = load(EVIDENCE)
        cls.fields = load(FIELDS)
        cls.graph = load(GRAPH)
        cls.status = load(STATUS)

    def test_sources_are_current_review_only_and_not_live_authority(self):
        self.assertFalse(self.sources["runtime_live_source_authority_used"])
        self.assertFalse(self.sources["source_content_persisted"])
        self.assertEqual(2, len(self.sources["sources"]))
        for source in self.sources["sources"]:
            self.assertEqual(source["acquired_at"], source["available_at"])
            self.assertFalse(source["historical_backdating_authorized"])
            self.assertFalse(source["ordinary_raw_lineage_eligible"])

    def test_fiber_field_is_bounded_not_universal(self):
        update = self.fields["field_updates"][0]
        self.assertEqual("fiber_connectivity_capacity", update["field_name"])
        self.assertEqual("POPULATED_BOUNDED_SITE_AND_PROVIDER_PROFILE", update["successor_status"])
        self.assertEqual(0, self.fields["source_gap_count_after"])
        self.assertEqual("EXISTING", update["value"]["site_access_example"]["fiber_connectivity"])
        self.assertEqual("UNSPECIFIED", update["value"]["site_access_example"]["exact_site_capacity"])
        self.assertEqual([100, 400], update["value"]["provider_capacity_example"]["advertised_connection_speeds_gbps"])
        self.assertIn("NOT_UNIVERSAL", update["uncertainty"])

    def test_provider_capacity_is_not_misattributed_to_paducah(self):
        update = self.fields["field_updates"][0]["value"]
        self.assertEqual("DOE Paducah Site, Kentucky", update["site_access_example"]["site"])
        self.assertEqual("Lumen Technologies", update["provider_capacity_example"]["provider"])
        self.assertNotIn("provider", update["site_access_example"])

    def test_fiber_graph_edge_is_supported_at_bounded_scope(self):
        edge = self.graph["edge_updates"][0]
        self.assertEqual("E013", edge["edge_id"])
        self.assertEqual("SUPPORTED_BOUNDED_SITE_PROVIDER_SCOPE", edge["successor_status"])
        self.assertEqual(2, len(edge["evidence_ids"]))

    def test_all_evidence_resolves_to_new_sources(self):
        source_ids = {source["source_id"] for source in self.sources["sources"]}
        for observation in self.evidence["observations"]:
            self.assertIn(observation["source_id"], source_ids)

    def test_original_source_gap_queue_is_closed_but_run_is_not_ready(self):
        self.assertEqual(0, self.status["results"]["ORIGINAL_FROZEN_SOURCE_GAP_FIELDS_REMAINING"])
        self.assertEqual("PARTIAL", self.status["results"]["DOMAIN_DATA_POPULATED"])
        self.assertEqual("NO", self.status["results"]["FIRST_SLICE_REAL_RAW_ARTIFACTS_MATERIALIZED"])
        self.assertEqual("NO", self.status["results"]["IMPLEMENTATION_ADMISSION_READY"])
        self.assertEqual("BLOCKED", self.status["results"]["FIRST_SERIOUS_CONSTRAINT_RUN"])
        self.assertNotIn("SOURCE-GAP-FIBER-CONNECTIVITY-CAPACITY", self.status["remaining_blockers"])

    def test_predecessors_are_not_rewritten(self):
        self.assertFalse(self.status["predecessor_artifacts_rewritten"])


if __name__ == "__main__":
    unittest.main()
