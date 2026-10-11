import unittest
from pathlib import Path

from hydra_constraint_replay.corpus import load_replay_ready_corpus
from hydra_constraint_replay.outcome_evidence import (
    EvidenceRole,
    load_outcome_enrichment_bundle,
)
from hydra_constraint_replay.promotion import (
    PromotionStage,
    evaluate_promotion,
    load_promotion_audits,
)


ROOT=Path(__file__).resolve().parents[2]
CORPUS=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl"
ENRICH=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_OUTCOME_ENRICHMENT_BATCH007_20260926.json"
AUDIT=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH007_20260926.json"


class OutcomeEnrichmentBatch007IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=load_replay_ready_corpus(CORPUS)
        cls.sources,cls.enrichments=load_outcome_enrichment_bundle(ENRICH)
        cls.audits=load_promotion_audits(AUDIT)

    def test_replay_ready_corpus_remains_unscored_and_unchanged_in_scope(self):
        self.assertEqual(22,len(self.corpus))
        self.assertTrue(all(r["tier"]=="REPLAY_READY_UNSCORED" for r in self.corpus))
        self.assertTrue(all("confidence_at_t" not in r for r in self.corpus))
        self.assertTrue(all("outcome_class" not in r for r in self.corpus))

    def test_enrichment_targets_exactly_three_existing_cases(self):
        corpus_ids={r["case_id"] for r in self.corpus}
        enrichment_ids={e.case_id for e in self.enrichments}
        self.assertEqual(
            {
                "suez-ever-given-2021",
                "black-sea-grain-corridor-2022",
                "germany-wilhelmshaven-lng-commissioning-2022-2023",
            },
            enrichment_ids,
        )
        self.assertTrue(enrichment_ids <= corpus_ids)

    def test_enriched_hypotheses_are_publisher_independent_and_prior(self):
        for enrichment in self.enrichments:
            with self.subTest(case=enrichment.case_id):
                hyp_publishers={
                    self.sources[sid].publisher
                    for sid in enrichment.historical_hypothesis_source_ids
                }
                outcome_publishers={
                    self.sources[sid].publisher
                    for sid in enrichment.outcome_source_ids
                }
                self.assertFalse(hyp_publishers & outcome_publishers)
                self.assertTrue(all(
                    self.sources[sid].role==EvidenceRole.HISTORICAL_HYPOTHESIS
                    for sid in enrichment.historical_hypothesis_source_ids
                ))
                self.assertTrue(all(
                    self.sources[sid].role==EvidenceRole.OUTCOME
                    for sid in enrichment.outcome_source_ids
                ))
                first_outcome=min(
                    self.sources[sid].available_at
                    for sid in enrichment.outcome_source_ids
                )
                self.assertLess(enrichment.hypothesis_available_at,first_outcome)

    def test_batch7_audit_advances_only_enriched_cases(self):
        enrich_by_id={e.case_id:e for e in self.enrichments}
        audit_by_id={a.case_id:a for a in self.audits}
        self.assertEqual(22,len(audit_by_id))

        for case_id,enrichment in enrich_by_id.items():
            audit=audit_by_id[case_id]
            decision=evaluate_promotion(audit)
            with self.subTest(case=case_id):
                self.assertEqual(
                    set(enrichment.historical_hypothesis_source_ids),
                    set(audit.historical_hypothesis_source_ids),
                )
                self.assertEqual(
                    set(enrichment.outcome_source_ids),
                    set(audit.outcome_source_ids),
                )
                self.assertEqual(PromotionStage.HYPOTHESIS_EVIDENCE_PRESENT,decision.stage)
                self.assertFalse(decision.scored_gold_eligible)
                self.assertIn("NO_PRECOMMITTED_CONFIDENCE_SOURCE",decision.blockers)
                self.assertIn("NO_SOURCE_GROUNDED_CONFIDENCE_VALUE",decision.blockers)

        for case_id,audit in audit_by_id.items():
            if case_id in enrich_by_id:
                continue
            with self.subTest(case=case_id):
                self.assertFalse(audit.historical_hypothesis_source_ids)

    def test_no_batch7_case_has_synthetic_confidence_or_outcome_class(self):
        for audit in self.audits:
            with self.subTest(case=audit.case_id):
                self.assertIsNone(audit.proposed_confidence_at_t)
                self.assertIsNone(audit.proposed_outcome_class)
                self.assertFalse(audit.scored_gold_eligible if hasattr(audit,"scored_gold_eligible") else False)


if __name__=="__main__":
    unittest.main()
