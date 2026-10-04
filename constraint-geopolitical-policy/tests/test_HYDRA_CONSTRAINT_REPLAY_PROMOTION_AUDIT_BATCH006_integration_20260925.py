import unittest
from pathlib import Path

from hydra_constraint_replay.corpus import load_replay_ready_corpus
from hydra_constraint_replay.promotion import (
    OutcomeEvidenceLevel,
    load_promotion_audits,
    summarize_promotion,
)
from hydra_constraint_policy.case_studies import load_sourced_case_bundle


ROOT=Path(__file__).resolve().parents[2]
CORPUS=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl"
AUDIT=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH006_20260925.json"


class PromotionAuditIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=load_replay_ready_corpus(CORPUS)
        cls.audits=load_promotion_audits(AUDIT)

    def test_audit_covers_exact_replay_corpus_case_set(self):
        self.assertEqual(
            {r["case_id"] for r in self.corpus},
            {a.case_id for a in self.audits},
        )

    def test_outcome_sources_are_real_case_observation_sources(self):
        corpus_by_id={r["case_id"]:r for r in self.corpus}
        bundle_cache={}
        for audit in self.audits:
            record=corpus_by_id[audit.case_id]
            bundle_path=record["source_bundle"]
            if bundle_path not in bundle_cache:
                bundle_cache[bundle_path]=load_sourced_case_bundle(ROOT/bundle_path)
            bundle=bundle_cache[bundle_path]
            case=next(c for c in bundle["cases"] if c["case_id"]==audit.case_id)
            observation_sources={
                sid
                for obs in case.get("observations",[])
                for sid in obs.get("source_ids",[])
            }
            with self.subTest(case=audit.case_id):
                self.assertEqual(set(audit.outcome_source_ids),observation_sources)
                if audit.outcome_evidence_level == OutcomeEvidenceLevel.NONE:
                    self.assertFalse(observation_sources)
                else:
                    self.assertTrue(observation_sources)

    def test_candidate_outcome_cases_are_exactly_three(self):
        candidates={
            a.case_id for a in self.audits
            if a.outcome_evidence_level in {
                OutcomeEvidenceLevel.SCORABLE_CANDIDATE_QUALITATIVE,
                OutcomeEvidenceLevel.SCORABLE_CANDIDATE_QUANTITATIVE,
                OutcomeEvidenceLevel.SCORABLE_CANDIDATE_OPERATIONAL,
            }
        }
        self.assertEqual(
            {
                "suez-ever-given-2021",
                "black-sea-grain-corridor-2022",
                "germany-wilhelmshaven-lng-commissioning-2022-2023",
            },
            candidates,
        )

    def test_no_existing_case_has_historical_confidence_provenance(self):
        summary=summarize_promotion(self.audits)
        self.assertEqual(0,summary["confidence_source_present_count"])
        self.assertEqual(0,summary["score_ready_count"])


if __name__=="__main__":
    unittest.main()
