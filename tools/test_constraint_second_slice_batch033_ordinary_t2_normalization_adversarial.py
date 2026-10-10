from __future__ import annotations
import copy, importlib.util, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"tools/validate_constraint_second_slice_batch033_ordinary_t2_normalization.py"
S=importlib.util.spec_from_file_location("b033",P)
if S is None or S.loader is None: raise RuntimeError("validator import failed")
v=importlib.util.module_from_spec(S); S.loader.exec_module(v)

class Batch033Hostile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=(v.load(v.QUEUE),v.load(v.ATTEST),v.load(v.LINEAGE),v.load(v.STATUS),v.load(v.MASTER),v.load(v.MANIFEST))
    def docs(self): return tuple(copy.deepcopy(x) for x in self.base)
    def reject(self,docs,pattern):
        with self.assertRaisesRegex((v.ValidationError,v.OrdinaryT2LineageError),pattern): v.validate_documents(*docs)
    def test_baseline(self): self.assertTrue(v.validate_documents(*self.docs()))
    def test_backdating_rejected(self):
        q,a,l,s,m,f=self.docs(); l["members"][0]["available_at"]="2020-01-01T00:00:00Z"; self.reject((q,a,l,s,m,f),"deterministic rebuild")
    def test_replay_promotion_rejected(self):
        q,a,l,s,m,f=self.docs(); l["strict_historical_replay_ready"]=True; self.reject((q,a,l,s,m,f),"deterministic rebuild")
    def test_source_version_drift_rejected(self):
        q,a,l,s,m,f=self.docs(); l["members"][0]["source_version_id"]="SV-FAKE"; self.reject((q,a,l,s,m,f),"deterministic rebuild")
    def test_master_evidence_binding_promotion_rejected(self):
        q,a,l,s,m,f=self.docs(); m["readiness"]["SECOND_SLICE_T2_EVIDENCE_LINEAGE"]["status"]="COMPLETE"; self.reject((q,a,l,s,m,f),"falsely bound")
    def test_case12_closure_rejected(self):
        q,a,l,s,m,f=self.docs(); s["results"]["REMAINING_REQUIRED_CASE"]=None; self.reject((q,a,l,s,m,f),"Case12 drift")
    def test_manifest_replay_promotion_rejected(self):
        q,a,l,s,m,f=self.docs(); f["expected"]["strict_historical_replay_ready"]=True; self.reject((q,a,l,s,m,f),"manifest replay promoted")

if __name__=="__main__": unittest.main()
