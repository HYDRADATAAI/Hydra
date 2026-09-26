import json
import unittest
from pathlib import Path

from hydra_constraint_replay.end_to_end import run_classified_replay_e2e


ROOT=Path(__file__).resolve().parents[2]
REPLAY="constraint-replay/corpus/HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl"
CLASSIFIED="constraint-replay/corpus/HYDRA_CONSTRAINT_CLASSIFIED_GOLD_UNCALIBRATED_BATCH014_20260926.jsonl"
PROMOTION="constraint-replay/corpus/HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH014_20260926.json"
EXPECTED=ROOT/"constraint-replay"/"runs"/"HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_RUN_20260926.json"


class Batch015EndToEndReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=run_classified_replay_e2e(ROOT,REPLAY,CLASSIFIED,PROMOTION)
        cls.expected=json.loads(EXPECTED.read_text(encoding="utf-8"))

    def test_runtime_output_equals_committed_run_artifact(self):
        self.assertEqual(self.expected,self.result)

    def test_run_status_and_digest_are_frozen(self):
        self.assertEqual("PASS",self.result["run_status"])
        self.assertEqual(
            "812c7eac1d68f7c07f195acb7831a04bd710e827ceb9dee24975ae8a728785c0",
            self.result["run_digest_sha256"],
        )

    def test_full_case_and_cut_coverage(self):
        c=self.result["coverage"]
        self.assertEqual(22,c["case_count"])
        self.assertEqual(82,c["replay_cut_count"])
        self.assertEqual(31,c["event_id_count"])
        self.assertEqual(9,c["observation_id_count"])
        self.assertEqual(1.0,c["classification_coverage"])
        self.assertEqual(22,c["classified_gold_uncalibrated_count"])
        self.assertEqual(0,c["calibrated_case_count"])

    def test_outcome_distribution_is_expected(self):
        self.assertEqual(
            {"PARTIAL_REALIZATION":17,"UNEVALUABLE":5},
            self.result["outcomes"]["class_counts"],
        )
        self.assertEqual(5,self.result["outcomes"]["unevaluable_count"])

    def test_integrity_gates_are_all_closed_green(self):
        integrity=self.result["integrity"]
        self.assertTrue(integrity["replay_ready_case_set_equals_classified_case_set"])
        self.assertTrue(integrity["replay_ready_case_set_equals_promotion_case_set"])
        self.assertTrue(integrity["replay_source_bundle_pins_valid"])
        self.assertTrue(integrity["classified_artifact_pins_valid"])
        self.assertEqual(0,integrity["classification_blockers_remaining"])
        self.assertEqual(0,integrity["calibrated_cases_present"])

    def test_calibration_is_explicitly_blocked_not_missing(self):
        calibration=self.result["calibration"]
        self.assertEqual(
            "BLOCKED_NO_ADMISSIBLE_NUMERIC_CONFIDENCE",
            calibration["status"],
        )
        self.assertEqual(0,calibration["calibrated_case_count"])
        self.assertIsNone(calibration["brier_score"])
        self.assertEqual(
            [
                "NO_PRECOMMITTED_CONFIDENCE_SOURCE",
                "NO_SOURCE_GROUNDED_CONFIDENCE_VALUE",
            ],
            calibration["common_blockers"],
        )

    def test_all_case_rows_are_uncalibrated_and_have_positive_lead(self):
        self.assertEqual(22,len(self.result["cases"]))
        for row in self.result["cases"]:
            with self.subTest(case=row["case_id"]):
                self.assertEqual(
                    "CLASSIFIED_GOLD_UNCALIBRATED",
                    row["classification_stage"],
                )
                self.assertFalse(row["calibrated"])
                self.assertGreater(row["evidence_availability_lead_days"],0)
                self.assertGreaterEqual(row["replay_cut_count"],2)


if __name__=="__main__":
    unittest.main()
