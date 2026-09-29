#!/usr/bin/env python3
"""Validate Batch034 evidence-to-source-version lineage closure."""
from __future__ import annotations
import importlib.util, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"constraint-t1-raw-artifact-store"/"src"
sys.path.insert(0,str(SRC))
from hydra_constraint_t1_raw.ordinary_t2_evidence_lineage import (  # noqa: E402
    OrdinaryT2EvidenceLineageError,
    build_ordinary_t2_evidence_lineage,
    validate_ordinary_t2_evidence_lineage,
)

BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
VAL=ROOT/"docs/constraint/validation"
ARCH=ROOT/"docs/constraint/architecture"
QUEUE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json"
LINEAGE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH033_SEMICONDUCTOR_ORDINARY_T2_SOURCE_VERSION_LINEAGE_V001_20260928.json"
BINDING=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_SEMICONDUCTOR_ORDINARY_T2_EVIDENCE_LINEAGE_BINDING_V001_20260928.json"
STATUS=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_SEMICONDUCTOR_T2_EVIDENCE_LINEAGE_STATUS_V001_20260928.json"
MASTER=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_MASTER_STATUS_V001_20260928.json"
MANIFEST=VAL/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_ARTIFACT_MANIFEST_V001_20260928.json"
BUILDER=ROOT/"tools/build_constraint_second_slice_batch034_t2_evidence_lineage.py"
SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"

SPEC=importlib.util.spec_from_file_location("b034_builder",BUILDER)
if SPEC is None or SPEC.loader is None: raise RuntimeError("unable to import Batch034 builder")
builder=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(builder)

class ValidationError(RuntimeError): pass
def req(c,m):
    if not c: raise ValidationError(m)
def load(p):
    v=json.loads(p.read_text(encoding="utf-8")); req(isinstance(v,dict),f"object required: {p}"); return v
def git_blob_sha(p):
    r=subprocess.run(["git","hash-object",str(p.relative_to(ROOT))],cwd=ROOT,text=True,capture_output=True,check=False)
    req(r.returncode==0,f"git hash-object failed: {p}"); return r.stdout.strip()

def evidence_records():
    out=[]
    for path in builder.EVIDENCE_PATHS:
        builder.collect(load(path),origin=path.relative_to(ROOT).as_posix(),out=out)
    return out

def validate_documents(queue,lineage,binding,status,master,manifest,evidence):
    rows=queue.get("queue"); req(isinstance(rows,list) and len(rows)==30,"active queue must contain 30")
    expected=build_ordinary_t2_evidence_lineage(
        lineage_packet=lineage,
        source_records=rows,
        evidence_records=evidence,
        expected_slice_id=SLICE,
    )
    req(binding==expected,"Batch034 binding differs from deterministic rebuild")
    validate_ordinary_t2_evidence_lineage(
        packet=binding,lineage_packet=lineage,source_records=rows,evidence_records=evidence,expected_slice_id=SLICE,
    )
    req(binding.get("input_evidence_record_count")==61,"input evidence count drift")
    req(binding.get("bound_evidence_count")==34,"bound evidence count drift")
    req(binding.get("excluded_evidence_count")==27,"excluded evidence count drift")
    req(binding.get("active_source_count")==30,"active source count drift")
    req(binding.get("active_source_count_with_bound_evidence")==30,"bound-source count drift")
    req(binding.get("all_active_sources_have_bound_evidence") is True,"active source evidence coverage incomplete")
    req(sum(1 for x in binding["bindings"] if x["availability_adjusted_to_source_version"])==34,"availability adjustment count drift")
    req(binding.get("strict_historical_replay_ready") is False,"binding strict replay promoted")
    req(binding.get("canonical_evidence_admission_promoted") is False,"binding canonical evidence promoted")
    req(len(binding.get("availability_boundaries",[]))==30,"evidence boundary count drift")

    req(status.get("result")=="PASS_ACTIVE_REVIEWED_EVIDENCE_BOUND_TO_EXACT_T2_SOURCE_VERSIONS_CURRENT_ONLY","status result drift")
    sr=status.get("results",{})
    for key,val in {
        "INPUT_REVIEWED_EVIDENCE_RECORDS":61,
        "ACTIVE_EVIDENCE_BOUND":34,
        "QUARANTINED_SOURCE_EVIDENCE_EXCLUDED":27,
        "ACTIVE_SOURCE_VERSIONS":30,
        "ACTIVE_SOURCES_WITH_BOUND_EVIDENCE":30,
        "EVIDENCE_BINDINGS_ADJUSTED_TO_SOURCE_VERSION_CUSTODY":34,
        "STRICT_HISTORICAL_REPLAY_READY":"NO",
        "CANONICAL_EVIDENCE_ADMISSION_PROMOTED":"NO",
        "REMAINING_REQUIRED_CASE":12,
    }.items(): req(sr.get(key)==val,f"status metric drift: {key}")
    req(status.get("next_repo_executable_lane")=="NONE_CURRENT_CUSTODY_T2_NORMALIZATION_AND_EVIDENCE_LINEAGE_COMPLETE","status next lane drift")

    req(master.get("record_id")=="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_MASTER_STATUS_V001","master identity drift")
    req(master.get("first_serious_constraint_run")=="BLOCKED","master serious run promoted")
    req(master.get("repo_executable_blockers")==[],"master repo-executable blocker list not empty")
    rd=master.get("readiness",{})
    req(rd.get("SECOND_SLICE_T2_EVIDENCE_LINEAGE",{}).get("status")=="COMPLETE_ACTIVE_REVIEWED_EVIDENCE_CURRENT_ONLY","master evidence lineage drift")
    req(rd.get("SECOND_SLICE_T2_EVIDENCE_LINEAGE",{}).get("bound_evidence_count")==34,"master bound count drift")
    req(rd.get("SECOND_SLICE_ACTIVE_SOURCE_EVIDENCE_COVERAGE",{}).get("status")=="YES_30_OF_30_ACTIVE_SOURCES","master source evidence coverage drift")
    req(rd.get("SECOND_SLICE_CANONICAL_EVIDENCE_ADMISSION",{}).get("status")=="NO","master canonical evidence promoted")
    req(rd.get("SECOND_SLICE_REPLAY_READY",{}).get("status")=="NO_STRICT_HISTORICAL","master replay promoted")
    req(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master full run promoted")
    req(master.get("next_repo_executable_lane")=="NONE_CURRENT_CUSTODY_T2_NORMALIZATION_AND_EVIDENCE_LINEAGE_COMPLETE","master next lane drift")

    req(manifest.get("result")=="PASS_ACTIVE_REVIEWED_EVIDENCE_BOUND_TO_EXACT_T2_SOURCE_VERSIONS_CURRENT_ONLY","manifest result drift")
    exp=manifest.get("expected",{})
    req(exp.get("active_evidence_bound")==34 and exp.get("quarantined_source_evidence_excluded")==27,"manifest evidence counts drift")
    req(exp.get("active_sources_with_bound_evidence")==30,"manifest source coverage drift")
    req(exp.get("strict_historical_replay_ready") is False,"manifest replay promoted")
    req(exp.get("canonical_evidence_admission_promoted") is False,"manifest canonical evidence promoted")
    req(exp.get("remaining_required_case")==12,"manifest Case12 drift")
    req(exp.get("repo_executable_blockers")==0,"manifest repo blocker count drift")
    seen=set()
    for art in manifest.get("artifacts",[]):
        rel=art.get("path"); sha=art.get("git_blob_sha")
        req(isinstance(rel,str) and rel and rel not in seen,"manifest path invalid/duplicate"); seen.add(rel)
        p=ROOT/rel; req(p.is_file(),f"manifest artifact missing: {rel}")
        req(git_blob_sha(p)==sha,f"manifest blob pin mismatch: {rel}")
    return True

def main():
    try:
        validate_documents(load(QUEUE),load(LINEAGE),load(BINDING),load(STATUS),load(MASTER),load(MANIFEST),evidence_records())
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValidationError,OrdinaryT2EvidenceLineageError) as exc:
        print("BATCH034_T2_EVIDENCE_LINEAGE=FAIL"); print(f"ERROR={exc}"); return 1
    print("BATCH034_T2_EVIDENCE_LINEAGE=PASS")
    print("INPUT_EVIDENCE=61"); print("BOUND_EVIDENCE=34"); print("EXCLUDED_EVIDENCE=27")
    print("ACTIVE_SOURCES_WITH_BOUND_EVIDENCE=30/30")
    print("STRICT_HISTORICAL_REPLAY_READY=NO"); print("CASE12=OPEN")
    print("REPO_EXECUTABLE_BLOCKERS=0")
    return 0
if __name__=="__main__": raise SystemExit(main())
