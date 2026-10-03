#!/usr/bin/env python3
"""Validate Batch033 semiconductor ordinary-T2 source-version normalization."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"constraint-t1-raw-artifact-store"/"src"
sys.path.insert(0,str(SRC))
from hydra_constraint_t1_raw.ordinary_t2_lineage import (  # noqa: E402
    OrdinaryT2LineageError,
    build_ordinary_t2_lineage,
    validate_ordinary_t2_lineage,
)

BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
VAL=ROOT/"docs/constraint/validation"
ARCH=ROOT/"docs/constraint/architecture"
QUEUE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json"
ATTEST=VAL/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH032_SEMICONDUCTOR_T1_MATERIALIZATION_ATTESTATION_V001_20260928.json"
LINEAGE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH033_SEMICONDUCTOR_ORDINARY_T2_SOURCE_VERSION_LINEAGE_V001_20260928.json"
STATUS=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH033_SEMICONDUCTOR_ORDINARY_T2_NORMALIZATION_STATUS_V001_20260928.json"
MASTER=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH033_MASTER_STATUS_V001_20260928.json"
MANIFEST=VAL/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH033_ARTIFACT_MANIFEST_V001_20260928.json"
SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"

class ValidationError(RuntimeError): pass
def req(c,m):
    if not c: raise ValidationError(m)
def load(p):
    v=json.loads(p.read_text(encoding="utf-8")); req(isinstance(v,dict),f"object required: {p}"); return v
def git_blob_sha(p):
    r=subprocess.run(["git","hash-object",str(p.relative_to(ROOT))],cwd=ROOT,text=True,capture_output=True,check=False)
    req(r.returncode==0,f"git hash-object failed: {p}"); return r.stdout.strip()

def validate_documents(queue,att,lineage,status,master,manifest):
    rows=queue.get("queue"); req(isinstance(rows,list) and len(rows)==30,"Batch031 queue must contain 30")
    req(queue.get("provider_exclusion_policy")=="MICRON_AND_DIRECT_TSMC_PROVIDER_CAPTURE_EXCLUDED_FROM_ACTIVE_CAPTURE","provider exclusion drift")
    expected=build_ordinary_t2_lineage(attestation=att,source_records=rows,expected_slice_id=SLICE)
    req(lineage==expected,"Batch033 lineage differs from deterministic rebuild")
    validate_ordinary_t2_lineage(packet=lineage,source_records=rows,expected_slice_id=SLICE)
    req(lineage.get("source_count")==30 and lineage.get("normalized_source_version_count")==30,"lineage count drift")
    req(lineage.get("ordinary_current_source_set_ready") is True,"current source set not ready")
    req(lineage.get("strict_historical_replay_ready") is False,"strict replay promoted")
    req(lineage.get("canonical_evidence_admission_promoted") is False,"canonical evidence promoted")
    req(lineage.get("historical_replay_blocker")=="PRE_ACQUISITION_HISTORICAL_VERSION_AVAILABILITY_NOT_ESTABLISHED","historical blocker drift")
    req(len(lineage.get("availability_boundaries",[]))==30,"availability boundary count drift")
    req(len(lineage["availability_boundaries"][-1]["eligible_source_ids"])==30,"final boundary incomplete")

    req(status.get("result")=="PASS_ORDINARY_T2_SOURCE_VERSION_NORMALIZATION_CURRENT_ONLY","status result drift")
    sr=status.get("results",{})
    req(sr.get("NORMALIZED_SOURCE_VERSIONS")==30,"status normalized count drift")
    req(sr.get("STRICT_HISTORICAL_REPLAY_READY")=="NO","status replay promoted")
    req(sr.get("CANONICAL_EVIDENCE_ADMISSION_PROMOTED")=="NO","status canonical evidence promoted")
    req(sr.get("REMAINING_REQUIRED_CASE")==12,"status Case12 drift")
    req(status.get("next_repo_executable_lane")=="SEMICONDUCTOR_T2_EVIDENCE_LINEAGE_BINDING_FROM_BATCH033_SOURCE_VERSIONS","status next lane drift")

    req(master.get("record_id")=="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH033_MASTER_STATUS_V001","master identity drift")
    req(master.get("first_serious_constraint_run")=="BLOCKED","master serious run promoted")
    rd=master.get("readiness",{})
    req(rd.get("SECOND_SLICE_ORDINARY_T2_NORMALIZATION",{}).get("status")=="COMPLETE_30_OF_30_SOURCE_VERSIONS","master normalization drift")
    req(rd.get("SECOND_SLICE_ORDINARY_SOURCE_VERSION_LINEAGE",{}).get("count")==30,"master lineage count drift")
    req(rd.get("SECOND_SLICE_T2_EVIDENCE_LINEAGE",{}).get("status")=="NOT_YET_BOUND","master evidence lineage falsely bound")
    req(rd.get("SECOND_SLICE_REPLAY_READY",{}).get("status")=="NO_STRICT_HISTORICAL","master replay promoted")
    req(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master full run promoted")
    req(master.get("next_repo_executable_lane")=="SEMICONDUCTOR_T2_EVIDENCE_LINEAGE_BINDING_FROM_BATCH033_SOURCE_VERSIONS","master next lane drift")

    req(manifest.get("result")=="PASS_ORDINARY_T2_SOURCE_VERSION_NORMALIZATION_CURRENT_ONLY","manifest result drift")
    exp=manifest.get("expected",{})
    req(exp.get("normalized_source_version_count")==30,"manifest count drift")
    req(exp.get("strict_historical_replay_ready") is False,"manifest replay promoted")
    req(exp.get("canonical_evidence_admission_promoted") is False,"manifest canonical evidence promoted")
    req(exp.get("remaining_required_case")==12,"manifest Case12 drift")
    seen=set()
    for art in manifest.get("artifacts",[]):
        rel=art.get("path"); sha=art.get("git_blob_sha")
        req(isinstance(rel,str) and rel and rel not in seen,"manifest path invalid/duplicate"); seen.add(rel)
        p=ROOT/rel; req(p.is_file(),f"manifest artifact missing: {rel}")
        req(git_blob_sha(p)==sha,f"manifest blob pin mismatch: {rel}")
    return True

def main():
    try:
        validate_documents(load(QUEUE),load(ATTEST),load(LINEAGE),load(STATUS),load(MASTER),load(MANIFEST))
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValidationError,OrdinaryT2LineageError) as exc:
        print("BATCH033_ORDINARY_T2_NORMALIZATION=FAIL"); print(f"ERROR={exc}"); return 1
    print("BATCH033_ORDINARY_T2_NORMALIZATION=PASS")
    print("NORMALIZED_SOURCE_VERSIONS=30")
    print("ORDINARY_CURRENT_SOURCE_SET_READY=YES")
    print("STRICT_HISTORICAL_REPLAY_READY=NO")
    print("CASE12=OPEN")
    print("NEXT=SEMICONDUCTOR_T2_EVIDENCE_LINEAGE_BINDING_FROM_BATCH033_SOURCE_VERSIONS")
    return 0
if __name__=="__main__": raise SystemExit(main())
