from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SLICE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"
IMPL = ROOT / "docs" / "constraint" / "implementation"
VALIDATION = ROOT / "docs" / "constraint" / "validation"

REGISTRY = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"
PLAN = IMPL / "HYDRA_CONSTRAINT_AI_DATA_CENTER_POWER_INFRASTRUCTURE_PRIVATE_T1_CAPTURE_PLAN_TEMPLATE_V001_20260926.json"
AUDIT = VALIDATION / "HYDRA_CONSTRAINT_BATCH017_NINE_REGISTERED_SOURCE_DISCOVERY_PRIVATE_RECORD_AUDIT_V001_20260926.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Batch017RegisteredSourcePrivateRecordAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load(REGISTRY)
        cls.plan = load(PLAN)
        cls.audit = load(AUDIT)

    def test_exact_nine_source_universe_matches_across_registry_plan_and_discovery(self):
        registry = {row["source_id"] for row in self.registry["sources"]}
        plan = {row["source_id"] for row in self.plan["captures"]}
        audit = {row["source_id"] for row in self.audit["sources"]}
        self.assertEqual(9, len(registry))
        self.assertEqual(registry, plan)
        self.assertEqual(registry, audit)

    def test_capture_plan_uses_exact_registered_locators(self):
        registered = {row["source_id"]: row["url"] for row in self.registry["sources"]}
        for capture in self.plan["captures"]:
            self.assertEqual(
                registered[capture["source_id"]],
                capture["source_locator"],
                capture["source_id"],
            )

    def test_capture_plan_cannot_predeclare_historical_available_at(self):
        self.assertEqual(
            "ACQUISITION_TIME_CONSERVATIVE",
            self.plan["availability_mode"],
        )
        for capture in self.plan["captures"]:
            self.assertNotIn("available_at", capture)

    def test_discovery_audit_closes_discovery_only_not_private_materialization(self):
        result = self.audit["discovery_result"]
        self.assertEqual(9, result["registered_source_count"])
        self.assertEqual(9, result["reachable_exact_locator_count"])
        self.assertEqual(0, result["missing_source_count"])
        self.assertEqual(0, result["locator_substitution_required_count"])
        self.assertTrue(result["source_discovery_complete"])
        self.assertFalse(result["private_materialization_executed"])
        self.assertFalse(self.audit["ordinary_replay_claimed"])
        self.assertFalse(self.audit["canonical_admission_claimed"])
        self.assertFalse(self.audit["raw_source_bodies_published"])

    def test_discovery_content_types_match_registered_capture_shape(self):
        observed = {
            row["source_id"]: row["observed_content_type"]
            for row in self.audit["sources"]
        }
        expected_pdf = {
            "SRC-DOE-LPT-RESILIENCE-2024",
            "SRC-NERC-LTRA-2025",
        }
        self.assertEqual(
            expected_pdf,
            {source_id for source_id, ctype in observed.items() if ctype == "application/pdf"},
        )
        self.assertEqual(
            7,
            sum(ctype == "text/html" for ctype in observed.values()),
        )

    def test_every_discovery_row_resolves_exact_registered_locator(self):
        self.assertTrue(all(
            row["discovery_state"] == "RESOLVED_EXACT_REGISTERED_LOCATOR"
            for row in self.audit["sources"]
        ))

    def test_remaining_dependencies_are_only_private_lineage_or_native_admission(self):
        remaining = set(self.audit["remaining_dependencies"])
        self.assertEqual(
            {
                "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION",
                "ORDINARY-POINT-IN-TIME-REPLAY-SOURCE-VERSION-HASHES-INCOMPLETE",
                "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT",
            },
            remaining,
        )


if __name__ == "__main__":
    unittest.main()
