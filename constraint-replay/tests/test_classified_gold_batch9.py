import hashlib
import unittest
from pathlib import Path

from hydra_constraint_replay.corpus import load_replay_ready_corpus
from hydra_constraint_replay.classified_gold import (
    load_classified_gold_corpus,
    summarize_classified_gold,
)
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
    summarize_promotion,
)


ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_CLASSIFIED_GOLD_UNCALIBRATED_BATCH008_20260926.jsonl"
NEW=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_CLASSIFIED_GOLD_UNCALIBRATED_BATCH009_20260926.jsonl"
ENRICH=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_OUTCOME_ENRICHMENT_BATCH009_20260926.json"
CONF=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_CONFIDENCE_ADMISSIBILITY_BATCH009_20260926.json"
MAP=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_OUTCOME_MAPPING_BATCH009_20260926.json"
AUDIT=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH009_20260926.json"
REPLAY_READY=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl"


def git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()


class ClassifiedGoldBatch009ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=load_classified_gold_corpus(OLD)
        cls.new=load_classified_gold_corpus(NEW)
        cls.sources,cls.enrichments=load_outcome_enrichment_bundle(ENRICH)
        cls.confidence,cls.mappings=load_confidence_audit(CONF)
        cls.declared_at,cls.mapping_inputs=load_outcome_mapping_bundle(MAP)
        cls.audits=load_promotion_audits(AUDIT)
        cls.replay_ready=load_replay_ready_corpus(REPLAY_READY)

    def test_expands_from_three_to_six_without_rewriting_predecessors(self):
        self.assertEqual(3,len(self.old))
        self.assertEqual(6,len(self.new))
        old_by={r.case_id:r for r in self.old}
        new_by={r.case_id:r for r in self.new}
        for case_id,record in old_by.items():
            with self.subTest(case=case_id):
                self.assertEqual(record,new_by[case_id])

    def test_batch9_source_pins_match_checked_out_bytes(self):
        new_ids={
            "us-section232-steel-tariff-2018",
            "eu-russian-oil-import-restrictions-2022",
            "panama-canal-drought-transit-policy-2023",
        }
        for record in self.new:
            if record.case_id not in new_ids:
                continue
            for path,sha in record.source_artifact_pins:
                with self.subTest(case=record.case_id,path=path):
                    self.assertEqual(sha,git_blob_sha(ROOT/path))

    def test_new_cases_already_exist_in_replay_ready_corpus(self):
        replay_ids={r["case_id"] for r in self.replay_ready}
        new_ids={r.case_id for r in self.new}-{r.case_id for r in self.old}
        self.assertTrue(new_ids <= replay_ids)

    def test_mapping_evidence_equals_admitted_enrichment_sources(self):
        enrich={e.case_id:e for e in self.enrichments}
        mappings={m.case_id:m for m in self.mapping_inputs}
        for case_id,enrichment in enrich.items():
            admitted=set(enrichment.historical_hypothesis_source_ids)
            admitted.update(enrichment.outcome_source_ids)
            with self.subTest(case=case_id):
                self.assertEqual(admitted,set(mappings[case_id].evidence_source_ids))

    def test_new_case_set_is_exact(self):
        old_ids={r.case_id for r in self.old}
        new_ids={r.case_id for r in self.new}-old_ids
        self.assertEqual(
            {
                "us-section232-steel-tariff-2018",
                "eu-russian-oil-import-restrictions-2022",
                "panama-canal-drought-transit-policy-2023",
            },
            new_ids,
        )

    def test_all_new_mappings_are_partial_realization(self):
        decisions={
            m.case_id:map_positive_constraint_outcome(m)
            for m in self.mapping_inputs
        }
        self.assertEqual(
            {
                "us-section232-steel-tariff-2018",
                "eu-russian-oil-import-restrictions-2022",
                "panama-canal-drought-transit-policy-2023",
            },
            set(decisions),
        )
        self.assertTrue(all(d.outcome_class=="PARTIAL_REALIZATION" for d in decisions.values()))

    def test_new_confidence_evidence_is_nonprobabilistic(self):
        self.assertEqual(3,len(self.confidence))
        self.assertTrue(all(
            admissible_confidence_value(e,self.mappings) is None
            for e in self.confidence
        ))

    def test_new_enrichment_publishers_are_independent(self):
        for enrichment in self.enrichments:
            hp={self.sources[s].publisher for s in enrichment.historical_hypothesis_source_ids}
            op={self.sources[s].publisher for s in enrichment.outcome_source_ids}
            with self.subTest(case=enrichment.case_id):
                self.assertFalse(hp & op)
                self.assertLess(
                    enrichment.hypothesis_available_at,
                    min(self.sources[s].available_at for s in enrichment.outcome_source_ids),
                )

    def test_batch9_promotion_summary_is_six_classified_zero_calibrated(self):
        summary=summarize_promotion(self.audits)
        self.assertEqual(22,summary["case_count"])
        self.assertEqual(6,summary["classified_gold_uncalibrated_count"])
        self.assertEqual(6,summary["outcome_class_supported_count"])
        self.assertEqual(6,summary["independent_hypothesis_present_count"])
        self.assertEqual(0,summary["confidence_source_present_count"])
        self.assertEqual(0,summary["score_ready_count"])

    def test_new_cases_have_only_calibration_blockers(self):
        audits={a.case_id:a for a in self.audits}
        for case_id in {
            "us-section232-steel-tariff-2018",
            "eu-russian-oil-import-restrictions-2022",
            "panama-canal-drought-transit-policy-2023",
        }:
            decision=evaluate_promotion(audits[case_id])
            with self.subTest(case=case_id):
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

    def test_six_case_summary_remains_uncalibrated(self):
        summary=summarize_classified_gold(self.new)
        self.assertEqual(6,summary["case_count"])
        self.assertEqual({"PARTIAL_REALIZATION":6},summary["outcome_class_counts"])
        self.assertEqual(0,summary["calibrated_case_count"])
        self.assertIsNone(summary["brier_score"])


if __name__=="__main__":
    unittest.main()
