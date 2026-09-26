import unittest
from pathlib import Path

from hydra_constraint_replay.confidence import (
    admissible_confidence_value,
    load_confidence_audit,
)
from hydra_constraint_replay.outcome_evidence import load_outcome_enrichment_bundle
from hydra_constraint_replay.outcome_mapping import (
    load_outcome_mapping_bundle,
    map_positive_constraint_outcome,
)
from hydra_constraint_replay.promotion import (
    PromotionStage,
    evaluate_promotion,
    load_promotion_audits,
)


ROOT=Path(__file__).resolve().parents[2]
CONF=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_CONFIDENCE_ADMISSIBILITY_BATCH008_20260926.json"
MAP=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_OUTCOME_MAPPING_BATCH008_20260926.json"
ENRICH=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_OUTCOME_ENRICHMENT_BATCH007_20260926.json"
AUDIT=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH008_20260926.json"


class Batch008GovernanceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.confidence,cls.ordinal_mappings=load_confidence_audit(CONF)
        cls.declared_at,cls.mapping_inputs=load_outcome_mapping_bundle(MAP)
        cls.sources,cls.enrichments=load_outcome_enrichment_bundle(ENRICH)
        cls.audits=load_promotion_audits(AUDIT)

    def test_target_case_sets_align(self):
        expected={
            "suez-ever-given-2021",
            "black-sea-grain-corridor-2022",
            "germany-wilhelmshaven-lng-commissioning-2022-2023",
        }
        self.assertEqual(expected,{e.case_id for e in self.confidence})
        self.assertEqual(expected,{m.case_id for m in self.mapping_inputs})
        self.assertEqual(expected,{e.case_id for e in self.enrichments})

    def test_confidence_evidence_references_admitted_hypothesis_sources(self):
        enrich={e.case_id:e for e in self.enrichments}
        for evidence in self.confidence:
            with self.subTest(case=evidence.case_id):
                self.assertIn(
                    evidence.source_id,
                    enrich[evidence.case_id].historical_hypothesis_source_ids,
                )
                self.assertIsNone(
                    admissible_confidence_value(evidence,self.ordinal_mappings)
                )

    def test_mapping_sources_are_all_admitted_enrichment_sources(self):
        enrich={e.case_id:e for e in self.enrichments}
        for mapping in self.mapping_inputs:
            admitted=set(enrich[mapping.case_id].historical_hypothesis_source_ids)
            admitted.update(enrich[mapping.case_id].outcome_source_ids)
            with self.subTest(case=mapping.case_id):
                self.assertEqual(set(mapping.evidence_source_ids),admitted)

    def test_mapping_decisions_match_batch8_promotion_classes(self):
        audits={a.case_id:a for a in self.audits}
        for mapping in self.mapping_inputs:
            decision=map_positive_constraint_outcome(mapping)
            audit=audits[mapping.case_id]
            with self.subTest(case=mapping.case_id):
                self.assertTrue(audit.outcome_class_supported)
                self.assertEqual(decision.outcome_class,audit.proposed_outcome_class)
                self.assertEqual("PARTIAL_REALIZATION",audit.proposed_outcome_class)

    def test_only_confidence_blockers_remain_for_three_candidates(self):
        audits={a.case_id:a for a in self.audits}
        for case_id in {
            "suez-ever-given-2021",
            "black-sea-grain-corridor-2022",
            "germany-wilhelmshaven-lng-commissioning-2022-2023",
        }:
            decision=evaluate_promotion(audits[case_id])
            with self.subTest(case=case_id):
                self.assertEqual(PromotionStage.HYPOTHESIS_EVIDENCE_PRESENT,decision.stage)
                self.assertFalse(decision.scored_gold_eligible)
                self.assertEqual(
                    {
                        "NO_PRECOMMITTED_CONFIDENCE_SOURCE",
                        "NO_SOURCE_GROUNDED_CONFIDENCE_VALUE",
                    },
                    set(decision.blockers),
                )


if __name__=="__main__":
    unittest.main()
