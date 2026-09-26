from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"

SOURCE_EXT = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH006_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_EXTENSION_V001_20260925.json"
EVIDENCE = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH006_AI_DATA_CENTER_POWER_INFRASTRUCTURE_EVIDENCE_SUPPLEMENT_V001_20260925.json"
FIELDS = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH006_AI_DATA_CENTER_POWER_INFRASTRUCTURE_FIELD_POPULATION_OVERLAY_V001_20260925.json"
GRAPH = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH006_AI_DATA_CENTER_POWER_INFRASTRUCTURE_GRAPH_OVERLAY_V001_20260925.json"
STATUS = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH006_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_GAP_STATUS_V001_20260925.json"


def load(name):
    with (BASE / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class FirstSliceSourceGapClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load(SOURCE_EXT)
        cls.evidence = load(EVIDENCE)
        cls.fields = load(FIELDS)
        cls.graph = load(GRAPH)
        cls.status = load(STATUS)

    def test_new_sources_remain_non_strict_without_available_at(self):
        self.assertFalse(self.sources["runtime_live_source_authority_used"])
        self.assertEqual(3, len(self.sources["sources"]))
        for source in self.sources["sources"]:
            self.assertIsNotNone(source["acquired_at"])
            self.assertIsNone(source["available_at"])
            self.assertFalse(source["strict_original_as_of_eligible"])

    def test_switchgear_value_is_explicitly_approximate_and_traceable(self):
        updates = {item["field_name"]: item for item in self.fields["field_updates"]}
        switchgear = updates["switchgear_lead_time_days"]
        self.assertEqual(301, switchgear["value"])
        self.assertEqual("days", switchgear["unit"])
        self.assertEqual("POPULATED_APPROXIMATE_REGIONAL", switchgear["successor_status"])
        self.assertEqual("APPROXIMATE_CHART_DERIVATION", switchgear["uncertainty"])
        self.assertEqual(["EV-JLL-AMER-SWITCHGEAR-LEADTIME-2026"], switchgear["evidence_ids"])

    def test_land_permitting_population_is_bounded_not_universal(self):
        updates = {item["field_name"]: item for item in self.fields["field_updates"]}
        land = updates["land_permitting_status"]
        self.assertEqual("POPULATED_BOUNDED_FEDERAL_SCOPE", land["successor_status"])
        self.assertEqual("U.S._DOE_FEDERAL_LANDS", land["value"]["scope"])
        self.assertEqual(16, land["value"]["candidate_sites_identified"])
        self.assertEqual(4, land["value"]["sites_selected_to_move_forward"])
        self.assertEqual("NOT_GENERALIZABLE_TO_ALL_U.S._DATA_CENTER_SITES", land["uncertainty"])

    def test_fiber_gap_is_not_fabricated_closed(self):
        updates = {item["field_name"]: item for item in self.fields["field_updates"]}
        fiber = updates["fiber_connectivity_capacity"]
        self.assertEqual("SOURCE_GAP", fiber["successor_status"])
        self.assertIsNone(fiber["value"])
        self.assertEqual([], fiber["evidence_ids"])
        self.assertEqual(1, self.fields["source_gap_count_after"])

    def test_graph_overlay_closes_only_supported_edges(self):
        edges = {item["edge_id"]: item for item in self.graph["edge_updates"]}
        self.assertEqual("SUPPORTED_BOUNDED_SCOPE", edges["E012"]["successor_status"])
        self.assertEqual("SUPPORTED_APPROXIMATE_REGIONAL", edges["E014"]["successor_status"])
        self.assertEqual("UNPOPULATED_SOURCE_GAP", edges["E013"]["successor_status"])
        self.assertEqual([], edges["E013"]["evidence_ids"])

    def test_run_readiness_remains_blocked(self):
        results = self.status["results"]
        self.assertEqual(1, results["SOURCE_GAP_FIELDS_REMAINING"])
        self.assertEqual("NO", results["STRICT_ORIGINAL_AS_OF_READY"])
        self.assertEqual("NO", results["IMPLEMENTATION_ADMISSION_READY"])
        self.assertEqual("BLOCKED", results["FIRST_SERIOUS_CONSTRAINT_RUN"])
        self.assertIn(
            "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT",
            self.status["remaining_blockers"],
        )


if __name__ == "__main__":
    unittest.main()
