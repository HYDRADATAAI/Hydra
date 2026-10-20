import hashlib
import unittest
from pathlib import Path

from hydra_constraint_replay.corpus import load_replay_ready_corpus
from hydra_constraint_replay.classified_gold import load_classified_gold_corpus, summarize_classified_gold
from hydra_constraint_replay.confidence import admissible_confidence_value, load_confidence_audit
from hydra_constraint_replay.outcome_evidence import load_outcome_enrichment_bundle
from hydra_constraint_replay.outcome_mapping import load_outcome_mapping_bundle, map_positive_constraint_outcome
from hydra_constraint_replay.promotion import PromotionStage, evaluate_promotion, load_promotion_audits, summarize_promotion

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_CLASSIFIED_GOLD_UNCALIBRATED_BATCH012_20260926.jsonl"
NEW=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_CLASSIFIED_GOLD_UNCALIBRATED_BATCH013_20260926.jsonl"
ENRICH=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_OUTCOME_ENRICHMENT_BATCH013_20260926.json"
CONF=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_CONFIDENCE_ADMISSIBILITY_BATCH013_20260926.json"
MAP=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_OUTCOME_MAPPING_BATCH013_20260926.json"
AUDIT=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH013_20260926.json"
REPLAY_READY=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl"

def git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()

class ClassifiedGoldBatch013ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=load_classified_gold_corpus(OLD)
        cls.new=load_classified_gold_corpus(NEW)
        cls.sources,cls.enrichments=load_outcome_enrichment_bundle(ENRICH)
        cls.confidence,cls.mappings=load_confidence_audit(CONF)
        cls.declared_at,cls.mapping_inputs=load_outcome_mapping_bundle(MAP)
        cls.audits=load_promotion_audits(AUDIT)
        cls.replay_ready=load_replay_ready_corpus(REPLAY_READY)

    def test_expands_from_fifteen_to_eighteen_without_rewriting_predecessors(self):
        self.assertEqual(15,len(self.old))
        self.assertEqual(18,len(self.new))
        new_by={r.case_id:r for r in self.new}
        for r in self.old:
            self.assertEqual(r,new_by[r.case_id])

    def test_new_case_set_is_exact(self):
        new_ids={r.case_id for r in self.new}-{r.case_id for r in self.old}
        self.assertEqual({
            "russia-food-import-embargo-2014",
            "bis-semiconductor-controls-2022",
            "wto-china-rare-earths-resource-dispute-2014-2015",
        },new_ids)

    def test_new_cases_exist_in_replay_ready(self):
        replay_ids={r["case_id"] for r in self.replay_ready}
        self.assertTrue(({r.case_id for r in self.new}-{r.case_id for r in self.old}) <= replay_ids)

    def test_new_mapping_classes_are_two_partial_one_unevaluable(self):
        decisions={m.case_id:map_positive_constraint_outcome(m) for m in self.mapping_inputs}
        self.assertEqual("PARTIAL_REALIZATION",decisions["russia-food-import-embargo-2014"].outcome_class)
        self.assertEqual("PARTIAL_REALIZATION",decisions["bis-semiconductor-controls-2022"].outcome_class)
        self.assertEqual("UNEVALUABLE",decisions["wto-china-rare-earths-resource-dispute-2014-2015"].outcome_class)

    def test_rareearth_case_preserves_open_compliance_disagreement(self):
        r=next(m for m in self.mapping_inputs if m.case_id=="wto-china-rare-earths-resource-dispute-2014-2015")
        self.assertTrue(r.contradiction_open)
        self.assertEqual("UNEVALUABLE",map_positive_constraint_outcome(r).outcome_class)

    def test_new_confidence_is_nonprobabilistic(self):
        self.assertEqual(3,len(self.confidence))
        self.assertTrue(all(admissible_confidence_value(e,self.mappings) is None for e in self.confidence))

    def test_publishers_are_independent_and_hypotheses_prior(self):
        for e in self.enrichments:
            hp={self.sources[s].publisher for s in e.historical_hypothesis_source_ids}
            op={self.sources[s].publisher for s in e.outcome_source_ids}
            self.assertFalse(hp & op)
            self.assertLess(e.hypothesis_available_at,min(self.sources[s].available_at for s in e.outcome_source_ids))

    def test_mapping_evidence_equals_enrichment_sources(self):
        enrich={e.case_id:e for e in self.enrichments}
        maps={m.case_id:m for m in self.mapping_inputs}
        for cid,e in enrich.items():
            admitted=set(e.historical_hypothesis_source_ids)|set(e.outcome_source_ids)
            self.assertEqual(admitted,set(maps[cid].evidence_source_ids))

    def test_source_pins_match_checked_out_bytes(self):
        new_ids={r.case_id for r in self.new}-{r.case_id for r in self.old}
        for r in self.new:
            if r.case_id not in new_ids:
                continue
            for path,sha in r.source_artifact_pins:
                self.assertEqual(sha,git_blob_sha(ROOT/path))

    def test_promotion_summary_is_eighteen_classified_zero_calibrated(self):
        s=summarize_promotion(self.audits)
        self.assertEqual(22,s["case_count"])
        self.assertEqual(18,s["classified_gold_uncalibrated_count"])
        self.assertEqual(18,s["outcome_class_supported_count"])
        self.assertEqual(18,s["independent_hypothesis_present_count"])
        self.assertEqual(0,s["confidence_source_present_count"])
        self.assertEqual(0,s["score_ready_count"])

    def test_new_cases_have_only_calibration_blockers(self):
        audits={a.case_id:a for a in self.audits}
        for cid in {
            "russia-food-import-embargo-2014",
            "bis-semiconductor-controls-2022",
            "wto-china-rare-earths-resource-dispute-2014-2015",
        }:
            d=evaluate_promotion(audits[cid])
            self.assertEqual(PromotionStage.CLASSIFIED_GOLD_UNCALIBRATED,d.stage)
            self.assertTrue(d.classified_gold_uncalibrated_eligible)
            self.assertFalse(d.scored_gold_eligible)
            self.assertFalse(d.classification_blockers)
            self.assertEqual({"NO_PRECOMMITTED_CONFIDENCE_SOURCE","NO_SOURCE_GROUNDED_CONFIDENCE_VALUE"},set(d.calibration_blockers))

    def test_eighteen_case_summary_remains_uncalibrated(self):
        s=summarize_classified_gold(self.new)
        self.assertEqual(18,s["case_count"])
        self.assertEqual({"PARTIAL_REALIZATION":16,"UNEVALUABLE":2},s["outcome_class_counts"])
        self.assertEqual(0,s["calibrated_case_count"])
        self.assertIsNone(s["brier_score"])

if __name__=="__main__":
    unittest.main()
