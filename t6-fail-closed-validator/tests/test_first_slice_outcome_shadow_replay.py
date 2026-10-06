from __future__ import annotations
import copy, json, unittest
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
  cls.overlay=load("HYDRA_CONSTRAINT_LILY_OWNER_SEAM_RECONCILIATION_T5_CANDIDATE_TEMPORAL_IDENTITY_OVERLAY_V002_20260926.json")
 def expected_successor(self,index):
  expected=copy.deepcopy(self.replay["windows"][index]["expected_graph_state"])
  for key in ("constraint_candidate_ids","relief_path_ids","beneficiary_relationship_ids"): expected[key]=[]
  return expected
 def snap(self,at): return build_shadow_snapshot(candidate_overlay=self.overlay,as_of=at,claim_registry=self.claims,candidates=self.candidates,relief_paths=self.relief,beneficiaries=self.beneficiaries,outcomes=self.outcomes)
 def test_outcome_is_capacity_added_only(self):
  row=self.outcomes["records"][0]
  self.assertEqual("CAPACITY_ADDED",row["outcome_label"]); self.assertEqual(0,self.outcomes["counts"]["constraint_resolutions"]); self.assertEqual(0,self.outcomes["counts"]["beneficiary_capture_confirmed"])
  self.assertEqual([],row["evidence_roles"]["constraint_support"]); self.assertEqual([],row["evidence_roles"]["beneficiary_capture_support"])
 def test_pre_cutoff_has_no_future_leak(self):
  exp=self.expected_successor(0); act=self.snap(exp["as_of"]); self.assertEqual(exp,act); self.assertEqual((),future_leaks(act,self.claims,self.outcomes)); self.assertEqual([],act["beneficiary_relationship_ids"]); self.assertEqual([],act["outcome_ids"])
 def test_post_cutoff_adds_then_available_state(self):
  exp=self.expected_successor(1); act=self.snap(exp["as_of"]); self.assertEqual(exp,act); self.assertEqual((),future_leaks(act,self.claims,self.outcomes)); self.assertEqual(10,len(act["eligible_claim_ids"])); self.assertEqual(0,len(act["beneficiary_relationship_ids"])); self.assertEqual(1,len(act["outcome_ids"]))
 def test_determinism_receipt_reproduces(self):
  pre=self.snap(self.receipt["pre_as_of"]); post=self.snap(self.receipt["post_as_of"])
  self.assertEqual(self.receipt["pre_snapshot_sha256"],canonical_sha256(self.replay["windows"][0]["expected_graph_state"])); self.assertEqual(self.receipt["post_snapshot_sha256"],canonical_sha256(self.replay["windows"][1]["expected_graph_state"])); self.assertEqual(pre,self.snap(self.receipt["pre_as_of"])); self.assertEqual(post,self.snap(self.receipt["post_as_of"])); self.assertTrue(self.receipt["repeat_execution_match"])
 def test_ordinary_replay_stays_blocked(self):
  self.assertFalse(self.replay["ordinary_replay_eligible"]); self.assertIsNone(self.replay["source_version_hashes"]["SRC-EATON-TEXAS-TRANSFORMER-CAPACITY-2025-10-08"]); self.assertIn("PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION",self.replay["ordinary_replay_blockers"])
 def test_relief_available_at_is_inclusive_and_excludes_future_path(self):
  inputs = dict(
   claim_registry=copy.deepcopy(self.claims),
   candidates=copy.deepcopy(self.candidates),
   relief_paths=copy.deepcopy(self.relief),
   beneficiaries=copy.deepcopy(self.beneficiaries),
   outcomes=copy.deepcopy(self.outcomes),
   candidate_overlay=copy.deepcopy(self.overlay),
  )
  relief = next(row for row in inputs["relief_paths"]["relief_paths"]
                if row["relief_path_id"] == "REL-AIDC-004")
  identity = relief["relief_path_id"]
  cutoff = "2026-09-26T12:47:00Z"
  relief["available_at"] = cutoff
  at_boundary = build_shadow_snapshot(as_of=cutoff, **inputs)
  self.assertIn(identity, at_boundary["relief_path_ids"])
  relief["available_at"] = "2026-09-26T12:47:01Z"
  after_cutoff = build_shadow_snapshot(as_of=cutoff, **inputs)
  self.assertNotIn(identity, after_cutoff["relief_path_ids"])
 def test_shadow_visibility_requires_positive_lineage(self):
  cases = (
   ("relief_paths", "relief_paths", "relief_path_id", "REL-AIDC-004",
    "relief_path_ids", {"support_claim_ids": [], "support_evidence_ids": []}),
   ("beneficiaries", "relationships", "beneficiary_relationship_id",
    "BEN-AIDC-EATON-TRANSFORMER-001", "beneficiary_relationship_ids", {"evidence_lineage": {}}),
   ("beneficiaries_blocking_only", "relationships", "beneficiary_relationship_id",
    "BEN-AIDC-EATON-TRANSFORMER-001", "beneficiary_relationship_ids",
    {"evidence_lineage": {
     "constraint_evidence": [], "entity_connection": [], "advantage_mechanism": [],
     "capacity_or_availability": [], "economic_or_strategic_capture": [],
     "disconfirming_or_blocking": ["EV-FERC-ORDER2023-QUEUE-REFORM"],
    }}),
  )
  for collection, rows_key, id_key, identity, snapshot_key, empty_lineage in cases:
   with self.subTest(collection=collection):
    inputs = copy.deepcopy(dict(
     claim_registry=self.claims, candidates=self.candidates,
     relief_paths=self.relief, beneficiaries=self.beneficiaries,
     outcomes=self.outcomes, candidate_overlay=self.overlay,
    ))
    cutoff = "2026-09-26T12:47:00Z"
    expected = build_shadow_snapshot(as_of=cutoff, **inputs)
    self.assertIn(identity, expected[snapshot_key])
    rows_collection = "beneficiaries" if collection == "beneficiaries_blocking_only" else collection
    row = next(row for row in inputs[rows_collection][rows_key] if row[id_key] == identity)
    row.update(empty_lineage)
    if collection == "beneficiaries_blocking_only":
     lineage = row["evidence_lineage"]
     self.assertTrue(lineage["disconfirming_or_blocking"])
     self.assertTrue(all(not values for role, values in lineage.items()
                         if role != "disconfirming_or_blocking"))
    expected[snapshot_key].remove(identity)
    self.assertEqual(expected, build_shadow_snapshot(as_of=cutoff, **inputs))
if __name__=="__main__": unittest.main()
