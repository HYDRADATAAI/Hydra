from __future__ import annotations
import copy, hashlib, importlib.util, json, shutil, subprocess, sys, tempfile, unittest
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
        q,l,b,s,m,f=self.docs(); s["results"]["REMAINING_REQUIRED_CASE"]=None; self.reject((q,l,b,s,m,f),"REMAINING_REQUIRED_CASE")
    def test_master_repo_blocker_invention_rejected(self):
        q,l,b,s,m,f=self.docs(); m["repo_executable_blockers"]=["FAKE"]; self.reject((q,l,b,s,m,f),"not empty")
    def test_master_full_run_promotion_rejected(self):
        q,l,b,s,m,f=self.docs(); m["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"]="YES"; self.reject((q,l,b,s,m,f),"full run promoted")

    def reject_any(self, docs):
        with self.assertRaises((v.ValidationError, v.OrdinaryT2EvidenceLineageError)):
            v.validate_documents(*docs, self.evidence)

    def test_master_implementation_promotion_rejected(self):
        docs=self.docs(); docs[4]["readiness"]["SECOND_SLICE_IMPLEMENTATION_ADMITTED"]["status"]="YES"
        self.reject_any(docs)

    def test_master_historical_proof_promotion_rejected(self):
        docs=self.docs(); docs[4]["readiness"]["SECOND_SLICE_HISTORICAL_AVAILABILITY"]["status"]="VERIFIED"
        self.reject_any(docs)

    def test_status_t5_t6_admission_promotion_rejected(self):
        docs=self.docs(); docs[3]["results"]["CANONICAL_T5_T6_ADMISSION_PROMOTED"]="YES"
        self.reject_any(docs)

    def test_status_backdating_promotion_rejected(self):
        docs=self.docs(); docs[3]["results"]["HISTORICAL_AVAILABILITY_BACKDATED"]="YES"
        self.reject_any(docs)

    def test_manifest_serious_run_promotion_rejected(self):
        docs=self.docs(); docs[5]["expected"]["first_serious_constraint_run"]="READY"
        self.reject_any(docs)

    def test_master_blocker_erasure_rejected(self):
        docs=self.docs(); docs[4]["remaining_blockers"]=[]
        self.reject_any(docs)

    def test_unknown_owner_gate_promotion_rejected(self):
        docs=self.docs(); docs[4]["D_OWNER_GATE"]="PASS"
        self.reject_any(docs)

    def test_unknown_trusted_timestamp_promotion_rejected(self):
        docs=self.docs(); docs[3]["results"]["TRUSTED_TIMESTAMP_VERIFIED"]="YES"
        self.reject_any(docs)

    def test_missing_unresolved_gate_rejected(self):
        for target, key in ((3,"CANONICAL_T5_T6_ADMISSION_PROMOTED"), (3,"HISTORICAL_AVAILABILITY_BACKDATED"), (4,"SECOND_SLICE_IMPLEMENTATION_ADMITTED"), (4,"SECOND_SLICE_HISTORICAL_AVAILABILITY")):
            with self.subTest(target=target,key=key):
                docs=self.docs(); del docs[target]["results" if target==3 else "readiness"][key]
                self.reject_any(docs)

    def test_empty_manifest_inventory_rejected(self):
        docs=self.docs(); docs[5]["artifacts"]=[]
        self.reject_any(docs)

    def test_missing_manifest_inventory_rejected(self):
        docs=self.docs(); del docs[5]["artifacts"]
        self.reject_any(docs)

    def test_partial_manifest_inventory_rejected(self):
        for index in range(4):
            with self.subTest(index=index):
                docs=self.docs(); del docs[5]["artifacts"][index]
                self.reject_any(docs)

    def test_manifest_inventory_type_and_entry_schema_rejected(self):
        for bad in (None, {}, "", False):
            with self.subTest(value=bad):
                docs=self.docs(); docs[5]["artifacts"]=bad
                with self.assertRaises((v.ValidationError,v.OrdinaryT2EvidenceLineageError,TypeError)):
                    v.validate_documents(*docs,self.evidence)
        docs=self.docs(); docs[5]["artifacts"][0]["signed_authority"]="VERIFIED"
        self.reject_any(docs)

    def test_manifest_extra_authority_field_rejected(self):
        docs=self.docs(); docs[5]["IMPLEMENTATION_ADMITTED"]="YES"
        self.reject_any(docs)

    def test_combined_admission_promotion_and_inventory_omission_rejected(self):
        docs=self.docs(); docs[4]["readiness"]["SECOND_SLICE_IMPLEMENTATION_ADMITTED"]["status"]="YES"; docs[5]["artifacts"]=[]
        self.reject_any(docs)

    def test_valid_lineage_exposes_nothing_before_first_capture(self):
        from hydra_constraint_t1_raw.ordinary_t2_evidence_lineage import select_ordinary_t2_evidence
        q,l,b,_,_,_=self.docs()
        self.assertEqual([],select_ordinary_t2_evidence(packet=b,lineage_packet=l,source_records=q["queue"],evidence_records=self.evidence,expected_slice_id=v.SLICE,as_of="2000-01-01T00:00:00Z"))

    def test_input_authority_claim_does_not_promote_binding(self):
        q,l,b,_,_,_=self.docs(); evidence=copy.deepcopy(self.evidence)
        evidence[0].update(D_OWNER_GATE="PASS", IMPLEMENTATION_ADMITTED="YES", trusted_timestamp_verified=True)
        result=v.build_ordinary_t2_evidence_lineage(lineage_packet=l,source_records=q["queue"],evidence_records=evidence,expected_slice_id=v.SLICE)
        self.assertEqual(b,result)
        self.assertIs(result["canonical_t5_t6_admission_promoted"],False)

    def test_baseline_objects_unchanged(self):
        docs=self.docs(); before=copy.deepcopy(docs)
        self.assertTrue(v.validate_documents(*docs,self.evidence))
        self.assertEqual(before,docs)

    def cli_fixture(self, destination):
        required=(v.QUEUE,v.LINEAGE,v.BINDING,v.STATUS,v.MASTER,v.MANIFEST,v.BUILDER,P,*v.builder.EVIDENCE_PATHS)
        manifest=self.base[5]
        paths=set(required)|{ROOT/art["path"] for art in manifest["artifacts"]}
        for source in paths:
            target=destination/source.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
        shutil.copytree(ROOT/"constraint-t1-raw-artifact-store/src",destination/"constraint-t1-raw-artifact-store/src")

    def run_fixture(self, destination):
        return subprocess.run([sys.executable,"-B",str(destination/P.relative_to(ROOT))],cwd=destination,text=True,capture_output=True,timeout=60)

    def promoted_cli(self, *, omit_inventory=False, report=False):
        with tempfile.TemporaryDirectory(prefix="b034-") as tmp:
            dest=Path(tmp); self.cli_fixture(dest)
            baseline=self.run_fixture(dest)
            self.assertEqual(0,baseline.returncode,baseline.stdout+baseline.stderr)
            manifest_path=dest/v.MANIFEST.relative_to(ROOT)
            manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
            if report:
                target=dest/next(art["path"] for art in manifest["artifacts"] if art["path"].endswith(".md"))
                target.write_text(target.read_text(encoding="utf-8")+"\nD_OWNER_GATE=PASS\nIMPLEMENTATION_ADMITTED=YES\n",encoding="utf-8")
            else:
                target=dest/v.MASTER.relative_to(ROOT)
                master=json.loads(target.read_text(encoding="utf-8"))
                master["readiness"]["SECOND_SLICE_IMPLEMENTATION_ADMITTED"]["status"]="YES"
                target.write_text(json.dumps(master,indent=2)+"\n",encoding="utf-8")
            if omit_inventory:
                manifest["artifacts"]=[]
            else:
                raw=target.read_bytes(); digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                for art in manifest["artifacts"]:
                    if art["path"]==target.relative_to(dest).as_posix(): art["git_blob_sha"]=digest
            manifest_path.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
            result=self.run_fixture(dest)
            self.assertNotEqual(0,result.returncode,result.stdout+result.stderr)
            self.assertIn("BATCH034_T2_EVIDENCE_LINEAGE=FAIL",result.stdout)
            self.assertNotIn("BATCH034_T2_EVIDENCE_LINEAGE=PASS",result.stdout)

    def test_cli_admission_promotion_with_empty_inventory_rejected(self):
        self.promoted_cli(omit_inventory=True)

    def test_cli_admission_promotion_with_valid_recomputed_hash_rejected(self):
        self.promoted_cli()

    def test_cli_report_promotion_with_valid_recomputed_hash_rejected(self):
        self.promoted_cli(report=True)

if __name__=="__main__": unittest.main()
