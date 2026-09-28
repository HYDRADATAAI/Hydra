from __future__ import annotations
import copy
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VAL=ROOT/"tools/validate_constraint_second_slice_batch032_t1_attestation.py"
SPEC=importlib.util.spec_from_file_location("b032_validator",VAL)
if SPEC is None or SPEC.loader is None: raise RuntimeError("validator import failed")
v=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(v)

class Batch032Hostile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queue=v.load(v.QUEUE); cls.quar=v.load(v.QUAR); cls.att=v.load(v.ATTEST); cls.status=v.load(v.STATUS); cls.master=v.load(v.MASTER); cls.manifest=v.load(v.MANIFEST)
    def docs(self): return tuple(copy.deepcopy(x) for x in (self.queue,self.quar,self.att,self.status,self.master,self.manifest))
    def reject(self,docs,pattern):
        with self.assertRaisesRegex(v.ValidationError,pattern): v.validate_documents(*docs)
    def test_baseline(self): self.assertTrue(v.validate_documents(*self.docs()))
    def test_backdating_rejected(self):
        q,z,a,s,master,m=self.docs(); a["members"][0]["available_at"]="2020-01-01T00:00:00Z"; self.reject((q,z,a,s,master,m),"historical backdating")
    def test_quarantined_tsmc_reentry_rejected(self):
        q,z,a,s,master,m=self.docs(); bad=copy.deepcopy(a["members"][0]); bad["source_id"]=z["quarantined_sources"][0]["source_id"]; a["members"][0]=bad; self.reject((q,z,a,s,master,m),"member set")
    def test_replay_promotion_rejected(self):
        q,z,a,s,master,m=self.docs(); a["strict_historical_replay_promoted"]=True; self.reject((q,z,a,s,master,m),"strict replay promoted")
    def test_private_path_flag_rejected(self):
        q,z,a,s,master,m=self.docs(); a["private_paths_published"]=True; self.reject((q,z,a,s,master,m),"private paths publication promoted")
    def test_case12_closure_rejected(self):
        q,z,a,s,master,m=self.docs(); s["remaining_blockers"]["REQUIRED_CASE_12_HISTORICAL_NO_LOOKAHEAD"]="CLOSED"; self.reject((q,z,a,s,master,m),"Case12 falsely closed")
    def test_master_full_run_promotion_rejected(self):
        q,z,a,s,master,m=self.docs(); master["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"]="YES"; self.reject((q,z,a,s,master,m),"master full run promoted")

    def test_manifest_replay_promotion_rejected(self):
        q,z,a,s,master,m=self.docs(); m["expected"]["strict_historical_replay"]="YES"; self.reject((q,z,a,s,master,m),"manifest replay promoted")

    def test_member_hash_mutation_rejected(self):
        q,z,a,s,master,m=self.docs(); a["members"][0]["artifact_sha256"]="0"*63; self.reject((q,z,a,s,master,m),"artifact hash invalid")

if __name__=="__main__": unittest.main()
