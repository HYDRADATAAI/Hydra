from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"

BATCH003_SOURCE = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"
BATCH005_AUDIT = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH005_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_TEMPORAL_AUDIT_V001_20260925.json"
BATCH005_STATUS = "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH005_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_TEMPORAL_STATUS_V001_20260925.json"


def load(name):
    with (BASE / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class FirstSliceSourceTemporalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predecessor = load(BATCH003_SOURCE)
        cls.audit = load(BATCH005_AUDIT)
        cls.status = load(BATCH005_STATUS)

    def test_all_batch003_sources_are_audited_once(self):
        predecessor_ids = {item["source_id"] for item in self.predecessor["sources"]}
        audited_ids = [item["source_id"] for item in self.audit["records"]]
        self.assertEqual(9, len(predecessor_ids))
        self.assertEqual(9, len(audited_ids))
        self.assertEqual(9, len(set(audited_ids)))
        self.assertEqual(predecessor_ids, set(audited_ids))

    def test_nerc_assessment_year_is_not_publication_year(self):
        records = {item["source_id"]: item for item in self.audit["records"]}
        nerc = records["SRC-NERC-LTRA-2025"]
        self.assertEqual("2025", nerc["assessment_year"])
        self.assertEqual("2026-01", nerc["observed_public_date"])
        self.assertEqual("REPORT_DATE_AND_RELEASE_MONTH", nerc["observed_date_type"])
        self.assertEqual("SUCCESSOR_CORRECTION_REQUIRED", nerc["metadata_disposition"])

        correction = self.status["corrections"]["SRC-NERC-LTRA-2025"]
        self.assertEqual("2025", correction["predecessor_publication_date"])
        self.assertEqual("2026-01", correction["current_publication_date"])
        self.assertEqual("2025", correction["assessment_year"])

    def test_document_and_event_dates_are_not_promoted_to_availability(self):
        records = {item["source_id"]: item for item in self.audit["records"]}
        lpt = records["SRC-DOE-LPT-RESILIENCE-2024"]
        webinar = records["SRC-DOE-DISTRIBUTION-TRANSFORMER-WEBINAR-2026"]
        self.assertEqual("DOCUMENT_COVER_DATE", lpt["observed_date_type"])
        self.assertEqual("EVENT_DATE", webinar["observed_date_type"])
        self.assertIsNone(lpt["available_at"])
        self.assertIsNone(webinar["available_at"])

    def test_no_temporal_audit_record_claims_exact_available_at(self):
        self.assertEqual(0, self.audit["available_at_proven_count"])
        self.assertTrue(all(item["available_at"] is None for item in self.audit["records"]))
        self.assertFalse(self.audit["strict_original_as_of_ready"])

    def test_batch005_is_overlay_not_predecessor_rewrite(self):
        self.assertFalse(self.status["predecessor_artifacts_rewritten"])
        self.assertEqual(1, self.status["counts"]["successor_corrections"])
        self.assertEqual(
            "PIT-001B-EXACT-AVAILABLE-AT-HISTORICAL-PROOF",
            self.status["next_population_blocker"],
        )
        self.assertEqual("NO", self.status["results"]["STRICT_ORIGINAL_AS_OF_READY"])
        self.assertEqual("BLOCKED", self.status["results"]["FIRST_SERIOUS_CONSTRAINT_RUN"])


if __name__ == "__main__":
    unittest.main()
