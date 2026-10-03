import hashlib
import json
import unittest
from datetime import datetime
from pathlib import Path

from hydra_constraint_policy.case_studies import (
    events_from_sourced_case_bundle,
    load_sourced_case_bundle,
)
from hydra_constraint_policy.model import eligible_as_of
from hydra_constraint_replay.corpus import load_replay_ready_corpus


ROOT=Path(__file__).resolve().parents[2]
CORPUS=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl"


def git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    header=f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header+payload).hexdigest()


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z","+00:00"))


class ReplayReadyCorpusIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=load_replay_ready_corpus(CORPUS)

    def test_source_bundle_blob_pins_match_committed_files(self):
        for record in self.records:
            with self.subTest(case=record["case_id"]):
                path=ROOT/record["source_bundle"]
                self.assertEqual(record["source_bundle_blob_sha"],git_blob_sha(path))

    def test_every_cut_matches_authoritative_policy_eligibility(self):
        cache={}
        for record in self.records:
            bundle_path=record["source_bundle"]
            if bundle_path not in cache:
                bundle=load_sourced_case_bundle(ROOT/bundle_path)
                cache[bundle_path]=(bundle,events_from_sourced_case_bundle(bundle))
            bundle,all_events=cache[bundle_path]
            case=next(c for c in bundle["cases"] if c["case_id"]==record["case_id"])
            case_event_ids={e["event_id"] for e in case["events"]}
            case_events=[e for e in all_events if e.event_id in case_event_ids]

            observations=case.get("observations",[])
            for cut in record["replay_cuts"]:
                replay_t=dt(cut["replay_t"])
                with self.subTest(case=record["case_id"],cut=cut["cut_id"]):
                    eligible_ids={e.event_id for e in eligible_as_of(case_events,replay_t)}
                    self.assertEqual(set(cut["eligible_event_ids"]),eligible_ids)
                    self.assertEqual(
                        set(cut["future_event_ids"]),
                        case_event_ids-eligible_ids,
                    )
                    expected_known_not_effective={
                        e.event_id for e in case_events
                        if e.temporal.known_at <= replay_t
                        and e.temporal.effective_at is not None
                        and e.temporal.effective_at > replay_t
                    }
                    self.assertEqual(
                        set(cut["known_but_not_effective_event_ids"]),
                        expected_known_not_effective,
                    )
                    available_obs={
                        o["observation_id"] for o in observations
                        if dt(o["known_at"]) <= replay_t
                    }
                    future_obs={o["observation_id"] for o in observations}-available_obs
                    self.assertEqual(set(cut["available_observation_ids"]),available_obs)
                    self.assertEqual(set(cut["future_observation_ids"]),future_obs)

    def test_no_case_is_silently_promoted_to_scored_gold(self):
        for record in self.records:
            with self.subTest(case=record["case_id"]):
                self.assertEqual("UNSCORED",record["score_status"])
                self.assertNotIn("confidence_at_t",record)
                self.assertNotIn("outcome_class",record)
                self.assertIn(
                    "NO_INDEPENDENT_HISTORICAL_HYPOTHESIS_SOURCE",
                    record["promotion_blockers"],
                )
                self.assertIn(
                    "NO_PRECOMMITTED_CONFIDENCE_SOURCE",
                    record["promotion_blockers"],
                )


if __name__=="__main__":
    unittest.main()
