#!/usr/bin/env python3
"""Validate Batch034 semiconductor ordinary-T2 evidence lineage binding."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"constraint-t1-raw-artifact-store"/"src"
sys.path.insert(0,str(SRC))

from hydra_constraint_t1_raw.evidence_lineage_binding import (  # noqa: E402
    EvidenceLineageBindingError,
    build_evidence_lineage_binding,
)

BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
VAL=ROOT/"docs/constraint/validation"
LINEAGE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH033_SEMICONDUCTOR_ORDINARY_T2_SOURCE_VERSION_LINEAGE_V001_20260928.json"
EVIDENCE_FILES=[
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_EVIDENCE_SEED_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_EVIDENCE_SUPPLEMENT_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_POLICY_SUBSTITUTION_OUTCOME_EVIDENCE_SUPPLEMENT_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_SUBSTITUTION_MIGRATION_POWER_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_YIELD_TOOL_MATERIAL_DUPLICATE_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_HBM_YIELD_MIGRATION_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_CONTINUOUS_CROSS_SLICE_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_NON_MICRON_REPLACEMENT_EVIDENCE_V001_20260927.json",
]
PACKET=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_SEMICONDUCTOR_T2_EVIDENCE_LINEAGE_BINDING_V001_20260928.json"
STATUS=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_SEMICONDUCTOR_T2_EVIDENCE_LINEAGE_STATUS_V001_20260928.json"
MASTER=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_MASTER_STATUS_V001_20260928.json"
MANIFEST=VAL/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_ARTIFACT_MANIFEST_V001_20260928.json"
SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"

class ValidationError(RuntimeError):
    pass

def req(condition:bool,message:str)->None:
    if not condition:
        raise ValidationError(message)

def load(path:Path)->dict:
    value=json.loads(path.read_text(encoding="utf-8"))
    req(isinstance(value,dict),f"object required: {path}")
    return value

def git_blob_sha(path:Path)->str:
    result=subprocess.run(
        ["git","hash-object",str(path.relative_to(ROOT))],
        cwd=ROOT,text=True,capture_output=True,check=False,
    )
    req(result.returncode==0,f"git hash-object failed: {path}")
    return result.stdout.strip()

def validate_documents(lineage,evidence_docs,packet,status,master,manifest):
    expected=build_evidence_lineage_binding(
        source_lineage=lineage,
        evidence_documents=evidence_docs,
        expected_slice_id=SLICE,
    )
    req(packet==expected,"Batch034 packet differs from deterministic rebuild")
    req(packet.get("source_count")==30,"Batch034 source count drift")
    req(packet.get("reviewed_evidence_record_count")==61,"reviewed evidence count drift")
    req(packet.get("bound_evidence_count")==34,"bound evidence count drift")
    req(packet.get("unbound_evidence_count")==27,"unbound evidence count drift")
    req(packet.get("bound_active_source_count")==30,"bound active-source count drift")
    req(packet.get("active_source_coverage_complete") is True,"active source evidence coverage incomplete")
    req(packet.get("ordinary_t2_evidence_lineage_bound") is True,"ordinary T2 evidence lineage not bound")
    req(packet.get("strict_historical_replay_ready") is False,"strict historical replay promoted")
    req(packet.get("historical_availability_backdated") is False,"historical availability backdated")
    req(packet.get("canonical_evidence_admission_promoted") is False,"canonical evidence promoted")
    req(packet.get("canonical_t5_t6_admission_promoted") is False,"canonical T5/T6 promoted")
    req(
        packet.get("unbound_evidence_policy")=="PRESERVE_UNBOUND_NO_IMPLICIT_SOURCE_SUBSTITUTION",
        "unbound evidence policy drift",
    )
    req(
        packet.get("no_lookahead_rule")=="EVIDENCE_VISIBLE_IFF_BOUND_SOURCE_AVAILABLE_AT_LTE_AS_OF",
        "evidence no-lookahead rule drift",
    )

    req(status.get("result")=="PASS_ORDINARY_T2_EVIDENCE_LINEAGE_BOUND_CURRENT_ONLY","status result drift")
    sr=status.get("results",{})
    req(sr.get("ACTIVE_SOURCE_SCOPE")==30,"status source count drift")
    req(sr.get("REVIEWED_EVIDENCE_RECORDS")==61,"status reviewed count drift")
    req(sr.get("BOUND_EVIDENCE_RECORDS")==34,"status bound count drift")
    req(sr.get("UNBOUND_EVIDENCE_RECORDS")==27,"status unbound count drift")
    req(sr.get("BOUND_ACTIVE_SOURCES")==30,"status active-source binding drift")
    req(sr.get("ACTIVE_SOURCE_COVERAGE_COMPLETE")=="YES","status coverage incomplete")
    req(sr.get("STRICT_HISTORICAL_REPLAY_READY")=="NO","status replay promoted")
    req(sr.get("REMAINING_REQUIRED_CASE")==12,"status Case12 drift")
    req(
        status.get("next_repo_executable_lane")=="NONE_CURRENT_REPO_LINEAGE_COMPLETE_EXTERNAL_OR_HISTORICAL_GATES_REMAIN",
        "status next lane drift",
    )

    req(master.get("record_id")=="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_MASTER_STATUS_V001","master identity drift")
    req(master.get("first_serious_constraint_run")=="BLOCKED","first serious run promoted")
    rd=master.get("readiness",{})
    ev=rd.get("SECOND_SLICE_T2_EVIDENCE_LINEAGE",{})
    req(ev.get("status")=="BOUND_CURRENT_ONLY","master evidence-lineage status drift")
    req(ev.get("bound_evidence")==34,"master bound evidence count drift")
    req(ev.get("unbound_evidence_preserved")==27,"master unbound evidence count drift")
    req(ev.get("bound_active_sources")==30,"master active-source coverage drift")
    req(rd.get("SECOND_SLICE_REPLAY_READY",{}).get("status")=="NO_STRICT_HISTORICAL","master replay promoted")
    req(rd.get("SECOND_SLICE_IMPLEMENTATION_ADMITTED",{}).get("status")=="NO","master implementation admission promoted")
    req(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master full run promoted")
    req(
        master.get("next_repo_executable_lane")=="NONE_CURRENT_REPO_LINEAGE_COMPLETE_EXTERNAL_OR_HISTORICAL_GATES_REMAIN",
        "master next lane drift",
    )

    req(manifest.get("result")=="PASS_ORDINARY_T2_EVIDENCE_LINEAGE_BOUND_CURRENT_ONLY","manifest result drift")
    exp=manifest.get("expected",{})
    req(exp.get("active_source_count")==30,"manifest source count drift")
    req(exp.get("reviewed_evidence_count")==61,"manifest reviewed count drift")
    req(exp.get("bound_evidence_count")==34,"manifest bound count drift")
    req(exp.get("unbound_evidence_count")==27,"manifest unbound count drift")
    req(exp.get("bound_active_source_count")==30,"manifest active source count drift")
    req(exp.get("active_source_coverage_complete") is True,"manifest coverage drift")
    req(exp.get("strict_historical_replay_ready") is False,"manifest replay promoted")
    req(exp.get("canonical_evidence_admission_promoted") is False,"manifest evidence admission promoted")
    req(exp.get("remaining_required_case")==12,"manifest Case12 drift")
    seen=set()
    for art in manifest.get("artifacts",[]):
        rel=art.get("path"); sha=art.get("git_blob_sha")
        req(isinstance(rel,str) and rel and rel not in seen,"manifest path invalid/duplicate")
        seen.add(rel)
        path=ROOT/rel
        req(path.is_file(),f"manifest artifact missing: {rel}")
        req(git_blob_sha(path)==sha,f"manifest blob pin mismatch: {rel}")
    return True

def main()->int:
    try:
        validate_documents(
            load(LINEAGE),
            [load(path) for path in EVIDENCE_FILES],
            load(PACKET),
            load(STATUS),
            load(MASTER),
            load(MANIFEST),
        )
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValidationError,EvidenceLineageBindingError) as exc:
        print("BATCH034_T2_EVIDENCE_LINEAGE=FAIL")
        print(f"ERROR={exc}")
        return 1
    print("BATCH034_T2_EVIDENCE_LINEAGE=PASS")
    print("ACTIVE_SOURCES=30")
    print("REVIEWED_EVIDENCE=61")
    print("BOUND_EVIDENCE=34")
    print("UNBOUND_EVIDENCE_PRESERVED=27")
    print("BOUND_ACTIVE_SOURCES=30")
    print("STRICT_HISTORICAL_REPLAY_READY=NO")
    print("CASE12=OPEN")
    print("NEXT=NONE_CURRENT_REPO_LINEAGE_COMPLETE_EXTERNAL_OR_HISTORICAL_GATES_REMAIN")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
