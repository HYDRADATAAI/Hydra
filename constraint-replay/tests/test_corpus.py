import copy
import json
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_replay.corpus import (
    CorpusValidationError,
    load_replay_ready_corpus,
    summarize_replay_ready_corpus,
    validate_replay_ready_record,
)


ROOT=Path(__file__).resolve().parents[2]
CORPUS=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl"


class ReplayReadyCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=load_replay_ready_corpus(CORPUS)

    def test_committed_corpus_shape(self):
        summary=summarize_replay_ready_corpus(self.records)
        self.assertEqual(22,summary.case_count)
        self.assertEqual(82,summary.replay_cut_count)
        self.assertEqual(31,summary.event_id_count)
        self.assertEqual(9,summary.observation_id_count)

    def test_every_case_remains_unscored(self):
        for record in self.records:
            with self.subTest(case=record["case_id"]):
                self.assertEqual("REPLAY_READY_UNSCORED",record["tier"])
                self.assertEqual("UNSCORED",record["score_status"])
                self.assertTrue(record["promotion_blockers"])

    def test_scored_fields_are_forbidden(self):
        bad=copy.deepcopy(self.records[0])
        bad["confidence_at_t"]=0.8
        with self.assertRaisesRegex(CorpusValidationError,"scored fields are forbidden"):
            validate_replay_ready_record(bad)

    def test_cuts_must_be_monotonic(self):
        bad=copy.deepcopy(self.records[0])
        bad["replay_cuts"][1]["eligible_event_ids"]=[]
        with self.assertRaises(CorpusValidationError):
            validate_replay_ready_record(bad)

    def test_event_universe_cannot_change_between_cuts(self):
        bad=copy.deepcopy(self.records[0])
        bad["replay_cuts"][-1]["future_event_ids"].append("invented-future-event")
        with self.assertRaisesRegex(CorpusValidationError,"event universe changed"):
            validate_replay_ready_record(bad)

    def test_duplicate_case_ids_fail(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"dup.jsonl"
            line=json.dumps(self.records[0])
            p.write_text(line+"\n"+line+"\n",encoding="utf-8")
            with self.assertRaisesRegex(CorpusValidationError,"duplicate case_id"):
                load_replay_ready_corpus(p)


if __name__=="__main__":
    unittest.main()
