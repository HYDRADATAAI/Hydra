from __future__ import annotations
import json
import copy
import unittest
from datetime import datetime
from pathlib import Path

from hydra_t6_failclosed.pit_conservative_availability import (
    temporally_eligible,
    validate_conservative_availability_overlay,
)

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
OVERLAY=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH007_AI_DATA_CENTER_POWER_INFRASTRUCTURE_CONSERVATIVE_AVAILABILITY_OVERLAY_V001_20260925.json"
STATUS=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH007_AI_DATA_CENTER_POWER_INFRASTRUCTURE_PIT_STATUS_V001_20260925.json"
BATCH004=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH004_AI_DATA_CENTER_POWER_INFRASTRUCTURE_PIT_ACQUISITION_CAPTURE_V001_20260925.json"

class ConservativeAvailabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overlay=json.loads(OVERLAY.read_text(encoding="utf-8"))
        cls.status=json.loads(STATUS.read_text(encoding="utf-8"))
        cls.batch004=json.loads(BATCH004.read_text(encoding="utf-8"))

    def test_overlay_valid(self):
        self.assertEqual((), validate_conservative_availability_overlay(self.overlay))

    def test_all_nine_sources_use_acquisition_as_conservative_availability(self):
        self.assertEqual(9,len(self.overlay["records"]))
        for row in self.overlay["records"]:
            self.assertEqual(row["inherited_acquired_at"],row["conservative_available_at"])
            self.assertFalse(row["historical_backdating_authorized"])

    def test_temporal_use_starts_at_capture_not_before(self):
        row=self.overlay["records"][0]
        self.assertFalse(temporally_eligible(row,datetime.fromisoformat("2026-09-25T23:52:01.573250+00:00")))
        self.assertTrue(temporally_eligible(row,datetime.fromisoformat("2026-09-25T23:52:01.573251+00:00")))

    def test_direct_eligibility_rejects_unverified_or_missing_acquisition(self):
        for value in ("TIMESTAMP_UNVERIFIED", None, "", "2026-09-25"):
            with self.subTest(acquired_at=value):
                row=copy.deepcopy(self.overlay["records"][0])
                row["inherited_acquired_at"]=value
                before=copy.deepcopy(row)
                self.assertFalse(temporally_eligible(row,datetime.fromisoformat("2026-09-27T00:00:00+00:00")))
                self.assertEqual(before,row)

    def test_direct_eligibility_cannot_bypass_overlay_guards(self):
        mutations = {
            "conservative_available_at": "2000-01-01T00:00:00Z",
            "availability_basis": "SOURCE_PUBLICATION_DATE",
            "historical_backdating_authorized": True,
            "source_content_persisted": True,
            "ordinary_replay_lineage_eligible": True,
            "source_id": None,
        }
        for field,value in mutations.items():
            with self.subTest(field=field):
                row=copy.deepcopy(self.overlay["records"][0])
                row[field]=value
                self.assertFalse(temporally_eligible(row,datetime.fromisoformat("2026-09-27T00:00:00+00:00")))

    def test_direct_eligibility_rejects_missing_required_fields(self):
        for field in ("inherited_acquired_at", "conservative_available_at", "availability_basis",
                      "historical_backdating_authorized", "source_content_persisted",
                      "ordinary_replay_lineage_eligible", "source_id"):
            with self.subTest(field=field):
                row=copy.deepcopy(self.overlay["records"][0])
                del row[field]
                self.assertFalse(temporally_eligible(row,datetime.fromisoformat("2026-09-27T00:00:00+00:00")))

    def test_status_metadata_cannot_silently_be_ignored(self):
        for field,value in (("acquisition_verification_status", "TIMESTAMP_UNVERIFIED"),
                            ("timestamp_verified", True), ("canonical_admission", True),
                            ("production_active", True)):
            with self.subTest(field=field):
                row=copy.deepcopy(self.overlay["records"][0]);row[field]=value
                before=copy.deepcopy(row)
                self.assertFalse(temporally_eligible(row,datetime.fromisoformat("2026-09-27T00:00:00+00:00")))
                self.assertEqual(before,row)

    def test_batch004_history_is_preserved(self):
        self.assertTrue(all(row["available_at"] is None for row in self.batch004["records"]))
        self.assertFalse(self.overlay["predecessor_artifacts_rewritten"])

    def test_temporal_fix_does_not_grant_raw_lineage(self):
        self.assertTrue(all(not row["ordinary_replay_lineage_eligible"] for row in self.overlay["records"]))
        self.assertEqual("NO",self.status["results"]["ORDINARY_T1_RAW_ARTIFACT_LINEAGE_COMPLETE"])
        self.assertEqual("NO",self.status["results"]["STRICT_ORDINARY_ORIGINAL_AS_OF_READY"])

    def test_old_available_at_blocker_is_narrowed_not_erased(self):
        b=self.status["blocker_reconciliation"]["PIT-001B-EXACT-AVAILABLE-AT-HISTORICAL-PROOF"]
        self.assertEqual("NARROWED_BY_BATCH007",b["state"])
        self.assertEqual("OPEN_ONLY_IF_PRE_CAPTURE_REPLAY_IS_REQUIRED",b["historical_backdating_status"])

    def test_next_real_population_blocker_is_raw_artifact_persistence(self):
        self.assertEqual("PIT-002-IMMUTABLE-RAW-SOURCE-ARTIFACT-PERSISTENCE",self.status["next_population_blocker"])

if __name__=="__main__":
    unittest.main()
