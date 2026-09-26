import hashlib
import unittest
from pathlib import Path

from hydra_constraint_replay.classified_gold import (
    CLASSIFIED_GOLD_TIER,
    NO_NUMERIC_CONFIDENCE,
    ClassifiedGoldError,
    ClassifiedGoldRecord,
    load_classified_gold_corpus,
    summarize_classified_gold,
)
from hydra_constraint_replay.confidence import (
    admissible_confidence_value,
    load_confidence_audit,
)
from hydra_constraint_replay.promotion import (
    PromotionStage,
    evaluate_promotion,
    load_promotion_audits,
    summarize_promotion,
)


ROOT=Path(__file__).resolve().parents[2]
CORPUS=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_CLASSIFIED_GOLD_UNCALIBRATED_BATCH008_20260926.jsonl"
CONF=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_CONFIDENCE_ADMISSIBILITY_BATCH008_20260926.json"
AUDIT=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH008_20260926.json"


def git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()


class ClassifiedGoldBatch008Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=load_classified_gold_corpus(CORPUS)
        cls.confidence,cls.mappings=load_confidence_audit(CONF)
        cls.audits=load_promotion_audits(AUDIT)

    def test_corpus_shape_and_uncalibrated_metrics(self):
        summary=summarize_classified_gold(self.records)
        self.assertEqual(3,summary["case_count"])
        self.assertEqual({"PARTIAL_REALIZATION":3},summary["outcome_class_counts"])
        self.assertEqual(0,summary["calibrated_case_count"])
        self.assertIsNone(summary["brier_score"])
        self.assertGreater(summary["mean_lead_time_days"],0)
        self.assertGreater(summary["median_lead_time_days"],0)

    def test_every_record_is_uncalibrated_classified_gold(self):
        for record in self.records:
            with self.subTest(case=record.case_id):
                self.assertEqual(CLASSIFIED_GOLD_TIER,record.tier)
                self.assertEqual(NO_NUMERIC_CONFIDENCE,record.confidence_status)
                self.assertEqual("PARTIAL_REALIZATION",record.outcome_class)

    def test_source_artifact_pins_match_checked_out_bytes(self):
        for record in self.records:
            for path,sha in record.source_artifact_pins:
                with self.subTest(case=record.case_id,path=path):
                    self.assertEqual(sha,git_blob_sha(ROOT/path))

    def test_promotion_summary_has_three_classified_and_zero_calibrated(self):
        summary=summarize_promotion(self.audits)
        self.assertEqual(3,summary["classified_gold_uncalibrated_count"])
        self.assertEqual(3,summary["outcome_class_supported_count"])
        self.assertEqual(0,summary["score_ready_count"])
        self.assertEqual(0,summary["confidence_source_present_count"])

    def test_promotion_decisions_match_classified_corpus(self):
        audits={a.case_id:a for a in self.audits}
        for record in self.records:
            decision=evaluate_promotion(audits[record.case_id])
            with self.subTest(case=record.case_id):
                self.assertEqual(PromotionStage.CLASSIFIED_GOLD_UNCALIBRATED,decision.stage)
                self.assertTrue(decision.classified_gold_uncalibrated_eligible)
                self.assertFalse(decision.scored_gold_eligible)
                self.assertFalse(decision.classification_blockers)
                self.assertEqual(
                    {
                        "NO_PRECOMMITTED_CONFIDENCE_SOURCE",
                        "NO_SOURCE_GROUNDED_CONFIDENCE_VALUE",
                    },
                    set(decision.calibration_blockers),
                )

    def test_confidence_audit_proves_no_numeric_calibration_value(self):
        confidence_by_case={e.case_id:e for e in self.confidence}
        for record in self.records:
            evidence=confidence_by_case[record.case_id]
            with self.subTest(case=record.case_id):
                self.assertIn(evidence.evidence_id,record.confidence_evidence_ids)
                self.assertIsNone(admissible_confidence_value(evidence,self.mappings))

    def test_classified_tier_rejects_fake_calibrated_status(self):
        r=self.records[0]
        bad=ClassifiedGoldRecord(
            case_id=r.case_id,
            tier=r.tier,
            replay_t=r.replay_t,
            historical_hypothesis_source_ids=r.historical_hypothesis_source_ids,
            outcome_source_ids=r.outcome_source_ids,
            outcome_first_observed_at=r.outcome_first_observed_at,
            outcome_class=r.outcome_class,
            mapping_rule_set_id=r.mapping_rule_set_id,
            confidence_status="CALIBRATED",
            confidence_evidence_ids=r.confidence_evidence_ids,
            source_artifact_pins=r.source_artifact_pins,
        )
        with self.assertRaisesRegex(ClassifiedGoldError,"unexpected confidence status"):
            bad.validate()


if __name__=="__main__":
    unittest.main()
