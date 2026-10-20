import copy
import unittest
from pathlib import Path

from hydra_constraint_replay.promotion import (
    OutcomeEvidenceLevel,
    PromotionError,
    PromotionStage,
    assert_scored_gold_eligible,
    evaluate_promotion,
    load_promotion_audits,
    summarize_promotion,
)


ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH006_20260925.json"


class PromotionAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audits=load_promotion_audits(AUDIT)

    def by_id(self,case_id):
        return next(a for a in self.audits if a.case_id==case_id)

    def test_audit_shape(self):
        summary=summarize_promotion(self.audits)
        self.assertEqual(22,summary["case_count"])
        self.assertEqual(0,summary["score_ready_count"])
        self.assertEqual(8,summary["outcome_evidence_present_count"])
        self.assertEqual(3,summary["scorable_candidate_outcome_count"])
        self.assertEqual(0,summary["independent_hypothesis_present_count"])
        self.assertEqual(0,summary["confidence_source_present_count"])

    def test_no_case_is_score_ready(self):
        for audit in self.audits:
            with self.subTest(case=audit.case_id):
                decision=evaluate_promotion(audit)
                self.assertFalse(decision.scored_gold_eligible)
                self.assertIn(
                    "NO_INDEPENDENT_HISTORICAL_HYPOTHESIS_SOURCE",
                    decision.blockers,
                )
                self.assertIn(
                    "NO_PRECOMMITTED_CONFIDENCE_SOURCE",
                    decision.blockers,
                )
                with self.assertRaises(PromotionError):
                    assert_scored_gold_eligible(audit)

    def test_three_outcome_candidates_are_explicit(self):
        self.assertEqual(
            OutcomeEvidenceLevel.SCORABLE_CANDIDATE_QUALITATIVE,
            self.by_id("suez-ever-given-2021").outcome_evidence_level,
        )
        self.assertEqual(
            OutcomeEvidenceLevel.SCORABLE_CANDIDATE_QUANTITATIVE,
            self.by_id("black-sea-grain-corridor-2022").outcome_evidence_level,
        )
        self.assertEqual(
            OutcomeEvidenceLevel.SCORABLE_CANDIDATE_OPERATIONAL,
            self.by_id("germany-wilhelmshaven-lng-commissioning-2022-2023").outcome_evidence_level,
        )

    def test_context_only_evidence_does_not_become_score_ready(self):
        audit=self.by_id("us-section45x-advanced-manufacturing-incentive-2022")
        self.assertEqual(OutcomeEvidenceLevel.CONTEXT_ONLY,audit.outcome_evidence_level)
        self.assertEqual(PromotionStage.OUTCOME_EVIDENCE_PRESENT,evaluate_promotion(audit).stage)
        self.assertFalse(evaluate_promotion(audit).scored_gold_eligible)

    def test_manual_confidence_without_source_fails_closed(self):
        audit=self.by_id("suez-ever-given-2021")
        raw={
            "case_id":audit.case_id,
            "replay_tier":audit.replay_tier,
            "historical_hypothesis_source_ids":list(audit.historical_hypothesis_source_ids),
            "historical_confidence_source_ids":[],
            "outcome_source_ids":list(audit.outcome_source_ids),
            "outcome_evidence_level":audit.outcome_evidence_level.value,
            "outcome_class_supported":False,
            "proposed_confidence_at_t":0.8,
            "proposed_outcome_class":None,
        }
        from hydra_constraint_replay.promotion import audit_from_dict
        with self.assertRaisesRegex(PromotionError,"confidence value requires historical confidence source"):
            audit_from_dict(raw)

    def test_outcome_class_without_support_fails_closed(self):
        audit=self.by_id("black-sea-grain-corridor-2022")
        raw={
            "case_id":audit.case_id,
            "replay_tier":audit.replay_tier,
            "historical_hypothesis_source_ids":[],
            "historical_confidence_source_ids":[],
            "outcome_source_ids":list(audit.outcome_source_ids),
            "outcome_evidence_level":audit.outcome_evidence_level.value,
            "outcome_class_supported":False,
            "proposed_confidence_at_t":None,
            "proposed_outcome_class":"TRUE_POSITIVE",
        }
        from hydra_constraint_replay.promotion import audit_from_dict
        with self.assertRaisesRegex(PromotionError,"outcome class supplied without support"):
            audit_from_dict(raw)


if __name__=="__main__":
    unittest.main()
