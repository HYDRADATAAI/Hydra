from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"tools/validate_constraint_second_slice_batch034_t2_evidence_lineage.py"
S=importlib.util.spec_from_file_location("b034",P)
if S is None or S.loader is None:
    raise RuntimeError("validator import failed")
v=importlib.util.module_from_spec(S)
S.loader.exec_module(v)

class Batch034Hostile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=(
            v.load(v.LINEAGE),
            [v.load(path) for path in v.EVIDENCE_FILES],
            v.load(v.PACKET),
            v.load(v.STATUS),
            v.load(v.MASTER),
            v.load(v.MANIFEST),
        )

    def docs(self):
        return tuple(copy.deepcopy(x) for x in self.base)

    def reject(self,docs,pattern):
        with self.assertRaisesRegex((v.ValidationError,v.EvidenceLineageBindingError),pattern):
            v.validate_documents(*docs)

    def test_baseline(self):
        self.assertTrue(v.validate_documents(*self.docs()))

    def test_bound_source_version_drift_rejected(self):
        l,e,p,s,m,f=self.docs()
        p["bound_evidence"][0]["source_version_id"]="SV-FAKE"
        self.reject((l,e,p,s,m,f),"deterministic rebuild")

    def test_unbound_evidence_drop_rejected(self):
        l,e,p,s,m,f=self.docs()
        p["unbound_evidence"].pop()
        p["unbound_evidence_count"]=26
        self.reject((l,e,p,s,m,f),"deterministic rebuild")

    def test_implicit_source_substitution_rejected(self):
        l,e,p,s,m,f=self.docs()
        p["unbound_evidence"][0]["source_id"]=p["bound_evidence"][0]["source_id"]
        self.reject((l,e,p,s,m,f),"deterministic rebuild")

    def test_replay_promotion_rejected(self):
        l,e,p,s,m,f=self.docs()
        p["strict_historical_replay_ready"]=True
        self.reject((l,e,p,s,m,f),"deterministic rebuild")

    def test_status_case12_closure_rejected(self):
        l,e,p,s,m,f=self.docs()
        s["results"]["REMAINING_REQUIRED_CASE"]=None
        self.reject((l,e,p,s,m,f),"Case12 drift")

    def test_master_full_run_promotion_rejected(self):
        l,e,p,s,m,f=self.docs()
        m["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"]="YES"
        self.reject((l,e,p,s,m,f),"full run promoted")

    def test_manifest_evidence_admission_promotion_rejected(self):
        l,e,p,s,m,f=self.docs()
        f["expected"]["canonical_evidence_admission_promoted"]=True
        self.reject((l,e,p,s,m,f),"evidence admission promoted")

if __name__=="__main__":
    unittest.main()
