"""Prepared native regression tests; NOT EXECUTED in the source audit.

Run on Windows: python -B test_thread_f_non_escalation.py --repo D:\\path\\to\\Hydra
Unrepaired source is expected to FAIL the rejection assertions documented in AUDIT.txt.
Only in-memory copies of public JSON are mutated; repository files are never changed.
"""
from __future__ import annotations
import argparse, copy, importlib.util, json, os, subprocess, sys, unittest
from pathlib import Path

PIN='fa94ab3e2fdd4776d84d110f4233ba84409eb947'

def suite(repo):
    sys.dont_write_bytecode=True
    path=repo/'tools/validate_constraint_second_slice_batch034_t2_evidence_lineage.py'
    spec=importlib.util.spec_from_file_location('thread_f_validator',path)
    v=importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
    from hydra_constraint_t1_raw.ordinary_t2_evidence_lineage import select_ordinary_t2_evidence

    class ThreadF(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.base=tuple(v.load(p) for p in (v.QUEUE,v.LINEAGE,v.BINDING,v.STATUS,v.MASTER,v.MANIFEST))
            cls.evidence=v.evidence_records()
        def docs(self):return copy.deepcopy(self.base)
        def rejects(self,docs):
            with self.assertRaises((v.ValidationError,v.OrdinaryT2EvidenceLineageError)):
                v.validate_documents(*docs,self.evidence)
        def test_baseline_current_documents(self):
            self.assertTrue(v.validate_documents(*self.docs(),self.evidence))
        def test_master_implementation_promotion_rejected(self):
            x=self.docs();x[4]['readiness']['SECOND_SLICE_IMPLEMENTATION_ADMITTED']['status']='YES';self.rejects(x)
        def test_master_historical_proof_promotion_rejected(self):
            x=self.docs();x[4]['readiness']['SECOND_SLICE_HISTORICAL_AVAILABILITY']['status']='VERIFIED';self.rejects(x)
        def test_status_t5_t6_admission_promotion_rejected(self):
            x=self.docs();x[3]['results']['CANONICAL_T5_T6_ADMISSION_PROMOTED']='YES';self.rejects(x)
        def test_status_backdating_promotion_rejected(self):
            x=self.docs();x[3]['results']['HISTORICAL_AVAILABILITY_BACKDATED']='YES';self.rejects(x)
        def test_manifest_serious_run_promotion_rejected(self):
            x=self.docs();x[5]['expected']['first_serious_constraint_run']='READY';self.rejects(x)
        def test_master_blocker_erasure_rejected(self):
            x=self.docs();x[4]['remaining_blockers']=[];self.rejects(x)
        def test_unknown_owner_gate_promotion_rejected(self):
            x=self.docs();x[4]['D_OWNER_GATE']='PASS';self.rejects(x)
        def test_unknown_trusted_timestamp_promotion_rejected(self):
            x=self.docs();x[3]['results']['TRUSTED_TIMESTAMP_VERIFIED']='YES';self.rejects(x)
        def test_empty_manifest_inventory_rejected(self):
            x=self.docs();x[5]['artifacts']=[];self.rejects(x)
        def test_missing_manifest_inventory_rejected(self):
            x=self.docs();del x[5]['artifacts'];self.rejects(x)
        def test_combined_admission_promotion_and_inventory_omission_rejected(self):
            x=self.docs();x[4]['readiness']['SECOND_SLICE_IMPLEMENTATION_ADMITTED']['status']='YES';x[5]['artifacts']=[];self.rejects(x)
        def test_binding_canonical_promotion_rejected(self):
            x=self.docs();x[2]['canonical_evidence_admission_promoted']=True;self.rejects(x)
        def test_binding_historical_promotion_rejected(self):
            x=self.docs();x[2]['strict_historical_replay_ready']=True;self.rejects(x)
        def test_binding_extra_owner_authority_rejected(self):
            x=self.docs();x[2]['D_OWNER_GATE']='PASS';self.rejects(x)
        def test_valid_lineage_exposes_nothing_before_first_capture(self):
            x=self.docs()
            result=select_ordinary_t2_evidence(packet=x[2],lineage_packet=x[1],source_records=x[0]['queue'],evidence_records=self.evidence,expected_slice_id=v.SLICE,as_of='2000-01-01T00:00:00Z')
            self.assertEqual([],result)
        def test_input_authority_claim_does_not_promote_binding(self):
            x=self.docs();ev=copy.deepcopy(self.evidence)
            ev[0].update(D_OWNER_GATE='PASS',IMPLEMENTATION_ADMITTED='YES',trusted_timestamp_verified=True)
            b=v.build_ordinary_t2_evidence_lineage(lineage_packet=x[1],source_records=x[0]['queue'],evidence_records=ev,expected_slice_id=v.SLICE)
            self.assertEqual(x[2],b)
            self.assertIs(b['canonical_t5_t6_admission_promoted'],False)
        def test_objects_unchanged_by_baseline_validation(self):
            x=self.docs();before=copy.deepcopy(x)
            v.validate_documents(*x,self.evidence)
            self.assertEqual(before,x)
    return unittest.defaultTestLoader.loadTestsFromTestCase(ThreadF)

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--json-output',type=Path);a=p.parse_args()
    if os.name!='nt':raise SystemExit('Windows required: this packet does not authorize HYDRA runtime execution in Linux.')
    repo=a.repo.resolve()
    if repo.drive.upper()!='D:':raise SystemExit('Repository must be on D:.')
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if head!=PIN:raise SystemExit('Exact source SHA mismatch; no tests executed.')
    result=unittest.TextTestRunner(verbosity=2).run(suite(repo))
    if a.json_output:
        if a.json_output.resolve().drive.upper()!='D:':raise SystemExit('Output must be on D:.')
        a.json_output.write_text(json.dumps({'head':head,'tests_run':result.testsRun,'failures':[(str(t),e) for t,e in result.failures],'errors':[(str(t),e) for t,e in result.errors],'skipped':[(str(t),why) for t,why in result.skipped],'successful':result.wasSuccessful()},indent=2)+'\n')
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())

