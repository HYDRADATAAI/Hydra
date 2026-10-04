import unittest
from pathlib import Path

from hydra_constraint_replay.outcome_evidence import load_outcome_enrichment_bundle
from hydra_constraint_replay.promotion import (
    OutcomeEvidenceLevel,
    PromotionStage,
    evaluate_promotion,
    load_promotion_audits,
    summarize_promotion,
)


ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH007_20260926.json"
ENRICH=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_OUTCOME_ENRICHMENT_BATCH007_20260926.json"


class PromotionBatch007Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audits=load_promotion_audits(AUDIT)
        cls.sources,cls.enrichments=load_outcome_enrichment_bundle(ENRICH)

    def by_id(self,case_id):
        return next(a for a in self.audits if a.case_id==case_id)

    def test_summary_reflects_hypothesis_progress_without_fake_gold(self):
        summary=summarize_promotion(self.audits)
        self.assertEqual(22,summary["case_count"])
        self.assertEqual(0,summary["score_ready_count"])
        self.assertEqual(3,summary["independent_hypothesis_present_count"])
        self.assertEqual(0,summary["confidence_source_present_count"])
        self.assertEqual(3,summary["scorable_candidate_outcome_count"])

    def test_three_candidates_are_hypothesis_evidence_present(self):
        for case_id in (
            "suez-ever-given-2021",
            "black-sea-grain-corridor-2022",
            "germany-wilhelmshaven-lng-commissioning-2022-2023",
        ):
            with self.subTest(case=case_id):
                audit=self.by_id(case_id)
                self.assertEqual(
                    OutcomeEvidenceLevel.SCORABLE_CANDIDATE_QUANTITATIVE,
                    audit.outcome_evidence_level,
                )
                decision=evaluate_promotion(audit)
                self.assertEqual(PromotionStage.HYPOTHESIS_EVIDENCE_PRESENT,decision.stage)
                self.assertFalse(decision.scored_gold_eligible)
                self.assertIn("NO_PRECOMMITTED_CONFIDENCE_SOURCE",decision.blockers)
                self.assertIn("NO_SOURCE_GROUNDED_CONFIDENCE_VALUE",decision.blockers)
                self.assertIn("OUTCOME_NOT_MAPPED_TO_SCORABLE_CLASS",decision.blockers)

    def test_enrichment_source_ids_match_promotion_audit(self):
        enrich_by_id={e.case_id:e for e in self.enrichments}
        for case_id,enrichment in enrich_by_id.items():
            audit=self.by_id(case_id)
            with self.subTest(case=case_id):
                self.assertEqual(
                    set(enrichment.historical_hypothesis_source_ids),
                    set(audit.historical_hypothesis_source_ids),
                )
                self.assertEqual(
                    set(enrichment.outcome_source_ids),
                    set(audit.outcome_source_ids),
                )

    def test_remaining_cases_did_not_gain_unsourced_hypotheses(self):
        enriched={e.case_id for e in self.enrichments}
        for audit in self.audits:
            if audit.case_id in enriched:
                continue
            with self.subTest(case=audit.case_id):
                self.assertFalse(audit.historical_hypothesis_source_ids)
                self.assertFalse(audit.historical_confidence_source_ids)


if __name__=="__main__":
    unittest.main()
