#!/usr/bin/env python3
"""Validate Batch023 semiconductor HBM-yield and constraint-migration closure."""

from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT",Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
FILES={
"source":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_HBM_YIELD_MIGRATION_SOURCE_REGISTRY_V001_20260926.json",
"evidence":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_HBM_YIELD_MIGRATION_EVIDENCE_V001_20260926.json",
"yield":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_HBM_YIELD_CONSTRAINT_EVALUATION_V001_20260926.json",
"migration":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_CONSTRAINT_MIGRATION_EVALUATION_V001_20260926.json",
"cases":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json",
"status":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_HBM_YIELD_MIGRATION_STATUS_V001_20260926.json",
"master":ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_MASTER_STATUS_V001_20260926.json",
"b022cases":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json",
"b021migration":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_CONSTRAINT_MIGRATION_EVALUATION_V001_20260926.json",
}
SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"

class ValidationFailure(Exception): pass
def require(c,m):
    if not c: raise ValidationFailure(m)
def load(p:Path)->dict[str,Any]:
    require(p.is_file(),f"required artifact missing: {p.relative_to(ROOT)}")
    v=json.loads(p.read_text(encoding="utf-8"))
    require(isinstance(v,dict),"root must be object")
    return v

def main()->int:
    d={k:load(v) for k,v in FILES.items()}
    for k in ("source","evidence","yield","migration","cases","status"):
        require(d[k].get("slice_id")==SLICE,f"{k} slice_id drifted")

    src=d["source"]; rows=src.get("sources",[])
    require(len(rows)==2,"Batch023 new-source count drifted")
    require(src.get("source_content_persisted") is False,"Batch023 falsely claims source persistence")
    for r in rows:
        require(r.get("acquired_at")==r.get("available_at"),"Batch023 conservative available_at drifted")
        require(r.get("ordinary_raw_lineage_eligible") is False,"Batch023 source unexpectedly ordinary raw-lineage eligible")

    ev=d["evidence"].get("evidence",[])
    require(len(ev)==4,"Batch023 evidence count drifted")
    eids={x.get("evidence_id") for x in ev}
    require(len(eids)==4,"Batch023 evidence IDs duplicate")

    y=d["yield"]["evaluation"]
    require(y.get("case_id")==3,"yield case ID drifted")
    require(y.get("constraint_variant")=="HBM_EFFECTIVE_BIT_OUTPUT_PENALTY_FROM_DIE_SIZE_AND_PACKAGING_YIELD","yield constraint variant drifted")
    require(y.get("usable_output_metric")=="BITS_PRODUCED_PER_EQUIVALENT_WAFER_SUPPLY","yield usable-output metric drifted")
    require(y.get("yield_and_packaging_effect")=="COMPLEX_PACKAGING_STACK_IMPACTS_YIELDS","yield effect drifted")
    require(y.get("effective_output_effect")=="MORE_THAN_2X_WAFER_SUPPLY_REQUIRED_FOR_EQUIVALENT_BITS_VS_DDR5","yield effective-output penalty drifted")
    require(y.get("numeric_yield_percentage") is None,"numeric HBM yield percentage was fabricated")
    require(y.get("binding_effective_output_constraint_proven") is True,"binding HBM effective-output constraint not proven")
    require(y.get("coverage_state")=="COVERED_REVIEWED_SHADOW_REAL_PRIMARY_BOUNDED_VARIANT","yield case coverage state drifted")
    require("DOES NOT INVENT A SPECIFIC YIELD PERCENTAGE" in y.get("semantic_limit",""),"yield no-false-precision firewall missing")

    mig=d["migration"]
    rows=mig.get("evaluations",[])
    require(len(rows)==2,"migration evaluation count drifted")
    by={r.get("migration_id"):r for r in rows}
    m=by["MIG-SEMI-MICRON-HBM-RAMP-TO-CLEANROOM-001"]
    require(m.get("chain_scope")=="MICRON_HBM_SUPPLY_CHAIN","migration chain scope drifted")
    require(m.get("relief_event",{}).get("state")=="OBSERVED_PARTIAL_RELIEF","old limiter relief is not observed")
    require(m.get("new_limiting_mechanism")=="CLEANROOM_CAPACITY_AND_HBM_SILICON_TRADE_RATIO_LIMIT_DRAM_BIT_SUPPLY_GROWTH","new limiting mechanism drifted")
    require(m.get("migration_state")=="COVERED_REVIEWED_SHADOW_REAL_PRIMARY_BOUNDED","migration coverage state drifted")
    require(m.get("case_11_coverage") is True,"Case 11 migration not covered")
    require(m.get("systemwide_resolution_asserted") is False,"migration falsely claims system-wide resolution")
    old=by["MIG-SEMI-COWOS-TO-MEMORY-CLEANROOM-001"]
    require(old.get("migration_state")=="REMAINS_CANDIDATE_NOT_COVERED","older CoWoS migration candidate was improperly promoted")
    require(old.get("case_11_coverage") is False,"older CoWoS migration candidate falsely covers Case 11")
    require(mig.get("covered_migration_count")==1,"covered migration count drifted")

    prev=d["b022cases"]
    require(prev.get("covered_case_count_after")==11,"Batch022 predecessor coverage drifted")
    require(prev.get("remaining_gap_case_ids")==[3,11,12],"Batch022 predecessor gap set was rewritten")
    cases=d["cases"]
    require(cases.get("covered_case_count_before")==11 and cases.get("covered_case_count_after")==13,"Batch023 case coverage count drifted")
    updates={x.get("case_id"):x for x in cases.get("updates",[])}
    require(set(updates)=={3,11},"Batch023 newly covered case set drifted")
    require(cases.get("remaining_gap_case_ids")==[12],"Batch023 remaining gap set drifted")
    prog=cases.get("progress_only",[])
    require(len(prog)==1 and prog[0].get("case_id")==12,"Batch023 progress-only case set drifted")
    require(prog[0].get("progress_state")=="UNCHANGED_EXTERNAL_RAW_LINEAGE_GATE","Case 12 raw-lineage gate drifted")

    b21=d["b021migration"]["evaluations"][0]
    require(b21.get("migration_state")=="MIGRATION_CANDIDATE_NOT_COVERED","Batch021 migration predecessor was rewritten")
    require(b21.get("case_11_coverage") is False,"Batch021 migration predecessor falsely promoted")

    st=d["status"]; r=st.get("results",{})
    expected={
      "PRIMARY_SOURCES_ADDED":2,
      "EVIDENCE_OBSERVATIONS_ADDED":4,
      "HBM_YIELD_CONSTRAINT_CASES_COVERED":1,
      "CONSTRAINT_MIGRATIONS_COVERED":1,
      "REQUIRED_CASES_COVERED":13,
      "REQUIRED_CASES_TOTAL":14,
      "NEW_REQUIRED_CASES_COVERED":[3,11],
      "REMAINING_GAP_CASES":[12],
      "REPO_EXECUTABLE_REQUIRED_CASE_GAPS":0,
      "FIRST_SEMICONDUCTOR_RUN":"BLOCKED",
    }
    for k,v in expected.items():
        require(r.get(k)==v,f"Batch023 status metric drifted: {k}")
    require(st.get("next_repo_executable_lane")=="SECOND-SLICE-STRICT-ACCEPTANCE-GATE-AND-EXTERNAL-BLOCKER-REPORT","Batch023 next lane drifted")

    mstr=d["master"]; rd=mstr.get("readiness",{})
    require(rd.get("SECOND_SLICE_HBM_YIELD_CONSTRAINT",{}).get("status")=="PASS_REVIEWED_SHADOW_BOUNDED_VARIANT","master HBM-yield status drifted")
    require(rd.get("SECOND_SLICE_CONSTRAINT_MIGRATION",{}).get("status")=="PASS_REVIEWED_SHADOW_BOUNDED_CHAIN","master migration status drifted")
    require(rd.get("SECOND_SLICE_REQUIRED_CASES",{}).get("covered")==13,"master required-case count drifted")
    require(rd.get("SECOND_SLICE_REPO_EXECUTABLE_REQUIRED_CASE_GAPS",{}).get("status")=="NONE","master repo-executable-gap status drifted")
    require(rd.get("SECOND_SLICE_REPLAY_READY",{}).get("status")=="NO","master falsely marks replay ready")
    require(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")
    require(mstr.get("first_serious_constraint_run")=="BLOCKED","master falsely serious-run ready")

    print("CONSTRAINT_SECOND_SLICE_BATCH023_HBM_YIELD_MIGRATION_VALIDATION=PASS")
    print("NEW_REQUIRED_CASES_COVERED=3,11")
    print("REQUIRED_CASES_COVERED=13/14")
    print("HBM_YIELD_CONSTRAINT_CASES=1")
    print("CONSTRAINT_MIGRATIONS_COVERED=1")
    print("REMAINING_GAPS=12")
    print("REPO_EXECUTABLE_REQUIRED_CASE_GAPS=0")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    print("NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-STRICT-ACCEPTANCE-GATE-AND-EXTERNAL-BLOCKER-REPORT")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError,KeyError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH023_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
