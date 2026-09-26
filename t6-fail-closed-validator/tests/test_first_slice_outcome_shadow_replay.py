from __future__ import annotations
import json, unittest
from pathlib import Path
from hydra_t6_failclosed.first_slice_shadow_replay import build_shadow_snapshot, canonical_sha256, future_leaks

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
def load(name): return json.loads((BASE/name).read_text(encoding="utf-8"))

class FirstSliceOutcomeShadowReplayTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.claims=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_CLAIM_REGISTRY_V001_20260925.json")
  cls.candidates=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_T5_CANDIDATE_PROPOSALS_V001_20260925.json")
  cls.relief=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_RELIEF_PATHS_V001_20260925.json")
  cls.beneficiaries=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BENEFICIARY_EVALUATIONS_V001_20260925.json")
  cls.outcomes=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_AI_DATA_CENTER_POWER_INFRASTRUCTURE_OUTCOME_RECORDS_V001_20260925.json")
  cls.replay=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SHADOW_REPLAY_PACKET_V001_20260925.json")
  cls.receipt=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_AI_DATA_CENTER_POWER_INFRASTRUCTURE_DETERMINISM_RECEIPT_V001_20260925.json")
 def snap(self,at): return build_shadow_snapshot(as_of=at,claim_registry=self.claims,candidates=self.candidates,relief_paths=self.relief,beneficiaries=self.beneficiaries,outcomes=self.outcomes)
 def test_outcome_is_capacity_added_only(self):
  row=self.outcomes["records"][0]
  self.assertEqual("CAPACITY_ADDED",row["outcome_label"]); self.assertEqual(0,self.outcomes["counts"]["constraint_resolutions"]); self.assertEqual(0,self.outcomes["counts"]["beneficiary_capture_confirmed"])
  self.assertEqual([],row["evidence_roles"]["constraint_support"]); self.assertEqual([],row["evidence_roles"]["beneficiary_capture_support"])
 def test_pre_cutoff_has_no_future_leak(self):
  exp=self.replay["windows"][0]["expected_graph_state"]; act=self.snap(exp["as_of"]); self.assertEqual(exp,act); self.assertEqual((),future_leaks(act,self.claims,self.outcomes)); self.assertEqual([],act["beneficiary_relationship_ids"]); self.assertEqual([],act["outcome_ids"])
 def test_post_cutoff_adds_then_available_state(self):
  exp=self.replay["windows"][1]["expected_graph_state"]; act=self.snap(exp["as_of"]); self.assertEqual(exp,act); self.assertEqual((),future_leaks(act,self.claims,self.outcomes)); self.assertEqual(10,len(act["eligible_claim_ids"])); self.assertEqual(4,len(act["beneficiary_relationship_ids"])); self.assertEqual(1,len(act["outcome_ids"]))
 def test_determinism_receipt_reproduces(self):
  pre=self.snap(self.receipt["pre_as_of"]); post=self.snap(self.receipt["post_as_of"])
  self.assertEqual(self.receipt["pre_snapshot_sha256"],canonical_sha256(pre)); self.assertEqual(self.receipt["post_snapshot_sha256"],canonical_sha256(post)); self.assertEqual(pre,self.snap(self.receipt["pre_as_of"])); self.assertEqual(post,self.snap(self.receipt["post_as_of"])); self.assertTrue(self.receipt["repeat_execution_match"])
 def test_ordinary_replay_stays_blocked(self):
  self.assertFalse(self.replay["ordinary_replay_eligible"]); self.assertIsNone(self.replay["source_version_hashes"]["SRC-EATON-TEXAS-TRANSFORMER-CAPACITY-2025-10-08"]); self.assertIn("PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION",self.replay["ordinary_replay_blockers"])
if __name__=="__main__": unittest.main()
