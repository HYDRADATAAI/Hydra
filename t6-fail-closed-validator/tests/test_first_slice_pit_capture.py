from __future__ import annotations

import json
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"

BATCH003_SOURCE = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"
BATCH004_CAPTURE = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH004_AI_DATA_CENTER_POWER_INFRASTRUCTURE_PIT_ACQUISITION_CAPTURE_V001_20260925.json"
BATCH004_STATUS = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH004_AI_DATA_CENTER_POWER_INFRASTRUCTURE_PIT_STATUS_V001_20260925.json"


def load(name):
    with (BASE / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class FirstSlicePointInTimeCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_registry = load(BATCH003_SOURCE)
        cls.capture = load(BATCH004_CAPTURE)
        cls.status = load(BATCH004_STATUS)

    def test_batch004_preserves_exact_batch003_source_set(self):
        expected = {item["source_id"] for item in self.source_registry["sources"]}
        actual = {item["source_id"] for item in self.capture["records"]}
        self.assertEqual(9, len(expected))
        self.assertEqual(expected, actual)

    def test_every_registered_source_has_exact_utc_acquisition_timestamp(self):
        for item in self.capture["records"]:
            parsed = datetime.fromisoformat(item["acquired_at"].replace("Z", "+00:00"))
            self.assertIsNotNone(parsed.tzinfo)
            self.assertEqual("RESOLVED_PUBLIC_SOURCE", item["acquisition_result"])

    def test_available_at_remains_fail_closed_without_exact_historical_proof(self):
        for item in self.capture["records"]:
            self.assertIsNone(item["available_at"])
            self.assertEqual(
                "UNRESOLVED_EXACT_HISTORICAL_AVAILABILITY",
                item["available_at_status"],
            )
            self.assertFalse(item["strict_original_as_of_eligible"])

    def test_no_runtime_live_source_authority_or_source_content_is_claimed(self):
        self.assertFalse(self.capture["runtime_live_source_authority_used"])
        self.assertTrue(self.capture["manual_public_retrieval_performed"])
        self.assertFalse(self.capture["source_content_persisted"])
        prohibited = {"content", "body", "text", "document_bytes", "pdf_bytes"}
        for item in self.capture["records"]:
            self.assertTrue(prohibited.isdisjoint(item))

    def test_pit_blocker_is_decomposed_not_falsely_closed(self):
        blockers = self.status["blocker_decomposition"]
        self.assertEqual(
            "CLOSED_BY_BATCH004",
            blockers["PIT-001A-EXACT-ACQUIRED-AT-CAPTURE"]["state"],
        )
        self.assertEqual(
            "OPEN_BLOCKING_STRICT_REPLAY",
            blockers["PIT-001B-EXACT-AVAILABLE-AT-HISTORICAL-PROOF"]["state"],
        )
        self.assertEqual("YES", self.status["results"]["ACQUIRED_AT_CAPTURE_READY"])
        self.assertEqual("NO", self.status["results"]["AVAILABLE_AT_CAPTURE_READY"])
        self.assertEqual("NO", self.status["results"]["STRICT_ORIGINAL_AS_OF_READY"])
        self.assertEqual("BLOCKED", self.status["results"]["FIRST_SERIOUS_CONSTRAINT_RUN"])

    def test_acquisition_time_is_not_relabelled_as_available_at(self):
        self.assertNotEqual(
            self.capture["acquired_at_semantics"],
            self.capture["available_at_semantics"],
        )
        self.assertEqual(
            "PIT-001B-EXACT-AVAILABLE-AT-HISTORICAL-PROOF",
            self.status["next_population_blocker"],
        )


if __name__ == "__main__":
    unittest.main()
