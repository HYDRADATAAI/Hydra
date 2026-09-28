from __future__ import annotations
import copy, importlib.util, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"tools/validate_constraint_second_slice_batch034_t2_evidence_lineage.py"
S=importlib.util.spec_from_file_location("b034",P)
if S is None or S.loader is None: raise RuntimeError("validator import failed")
v=importlib.util.module_from_spec(S); S.loader.exec_module(v)

class Batch034Hostile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence=v.evidence_records()
        cls.base=(v.load(v.QUEUE),v.load(v.LINEAGE),v.load(v.BINDING),v.load(v.STATUS),v.load(v.MASTER),v.load(v.MANIFEST))
    def docs(self): return tuple(copy.deepcopy(x) for x in self.base)
    def reject(self,docs,pattern):
        with self.assertRaisesRegex((v.ValidationError,v.OrdinaryT2EvidenceLineageError),pattern):
            v.validate_documents(*docs,self.evidence)
    def test_baseline(self): self.assertTrue(v.validate_documents(*self.docs(),self.evidence))
    def test_evidence_backdating_rejected(self):
        q,l,b,s,m,f=self.docs(); b["bindings"][0]["ordinary_t2_available_at"]="2020-01-01T00:00:00Z"; self.reject((q,l,b,s,m,f),"deterministic rebuild")
    def test_source_version_hash_drift_rejected(self):
        q,l,b,s,m,f=self.docs(); b["bindings"][0]["artifact_sha256"]="0"*64; self.reject((q,l,b,s,m,f),"deterministic rebuild")
    def test_quarantined_evidence_reentry_rejected(self):
        q,l,b,s,m,f=self.docs(); item=b["excluded_evidence"].pop(); item.pop("exclusion_reason"); item.update({"source_version_id":"SV-FAKE","artifact_sha256":"0"*64,"receipt_sha256":"1"*64,"source_locator":"https://example.invalid","reviewed_evidence_available_at":None,"source_version_available_at":"2026-09-28T00:00:00Z","ordinary_t2_available_at":"2026-09-28T00:00:00Z","availability_basis":"SOURCE_VERSION_AVAILABLE_AT_ONLY","availability_adjusted_to_source_version":True,"ordinary_t2_source_version_eligible":True,"canonical_evidence_admitted":False}); b["bindings"].append(item); self.reject((q,l,b,s,m,f),"deterministic rebuild")
    def test_canonical_evidence_promotion_rejected(self):
        q,l,b,s,m,f=self.docs(); b["canonical_evidence_admission_promoted"]=True; self.reject((q,l,b,s,m,f),"deterministic rebuild")
    def test_case12_closure_rejected(self):
        q,l,b,s,m,f=self.docs(); s["results"]["REMAINING_REQUIRED_CASE"]=None; self.reject((q,l,b,s,m,f),"Case12 drift")
    def test_master_repo_blocker_invention_rejected(self):
        q,l,b,s,m,f=self.docs(); m["repo_executable_blockers"]=["FAKE"]; self.reject((q,l,b,s,m,f),"not empty")
    def test_master_full_run_promotion_rejected(self):
        q,l,b,s,m,f=self.docs(); m["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"]="YES"; self.reject((q,l,b,s,m,f),"full run promoted")

if __name__=="__main__": unittest.main()
