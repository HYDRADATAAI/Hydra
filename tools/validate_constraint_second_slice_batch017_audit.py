#!/usr/bin/env python3
"""Validate Batch017 semiconductor second-slice scope and reuse audit."""

from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"

FILES={
"scope":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_SCOPE_MANIFEST_V001_20260926.json",
"audit":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_SEMANTIC_REUSE_AUDIT_V001_20260926.json",
"fields":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_FIELD_REQUIREMENTS_V001_20260926.json",
"cases":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_REQUIRED_CASE_MATRIX_V001_20260926.json",
"authority":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_AUTHORITY_MAP_V001_20260926.json",
"status":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_STATUS_V001_20260926.json",
"master":ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_MASTER_STATUS_V001_20260926.json",
}
SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"

class ValidationFailure(Exception): pass
def require(c,m):
    if not c: raise ValidationFailure(m)
def load(p:Path)->dict[str,Any]:
    require(p.is_file(),f"required artifact missing: {p.relative_to(ROOT)}")
    v=json.loads(p.read_text(encoding="utf-8"))
    require(isinstance(v,dict),f"root must be object: {p.relative_to(ROOT)}")
    return v

def main()->int:
    d={k:load(v) for k,v in FILES.items()}
    for k in ("scope","audit","fields","cases","authority","status"):
        require(d[k].get("slice_id")==SLICE,f"{k} slice_id drifted")

    scope=d["scope"]
    require(scope.get("semantic_duplication_created") is False,"parallel/duplicate semiconductor semantics created")
    require(scope.get("predecessor_first_slice")=="AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1","cross-slice predecessor drifted")
    require(scope.get("cross_slice_requirement",{}).get("required") is True,"cross-slice graph requirement removed")
    require(scope.get("prohibited_expansion")==["ROBOTICS","BIOTECH","HOUSING","OTHER_MAJOR_ECOSYSTEM"],"hard-stop expansion set drifted")
    universe=scope.get("bounded_universe",{})
    require(len(universe)==7,"bounded universe category count drifted")
    for name,row in universe.items():
        require(isinstance(row,dict),"bounded universe row invalid")
        require(isinstance(row.get("target_min"),int) and isinstance(row.get("target_max"),int),f"{name} bounds invalid")
        require(0 < row["target_min"] <= row["target_max"],f"{name} bounds invalid")

    audit=d["audit"]
    require(audit.get("repository_semiconductor_specific_population_found") is False,"audit falsely claims semiconductor population existed")
    require(audit.get("semantic_duplication_created") is False,"audit created semantic duplication")
    rows=audit.get("rows",[])
    require(isinstance(rows,list) and len(rows)>=20,"semantic reuse audit too small")
    allowed={"REUSE","EXTEND","POPULATE","STALE","DUPLICATE","GAP"}
    require(all(r.get("classification") in allowed for r in rows),"audit classification invalid")
    summary=audit.get("summary",{})
    require(summary.get("REUSE",0)>0 and summary.get("EXTEND",0)>0 and summary.get("POPULATE",0)>0 and summary.get("GAP",0)>0,"audit classification mix incomplete")
    require(summary.get("STALE")==0 and summary.get("DUPLICATE")==0,"audit fabricated stale/duplicate items")

    fields=d["fields"]
    frows=fields.get("fields",[])
    names=[r.get("field_name") for r in frows]
    require(len(names)==fields.get("frozen_field_count"),"field count drifted")
    require(len(names)==len(set(names)),"duplicate field names")
    critical={
      "installed_capacity","operational_capacity","available_capacity","effective_capacity","reserved_capacity","booked_capacity",
      "yield_value","yield_state","qualification_type","qualification_state",
      "material_stage","material_grade","equipment_qualification_state",
      "effective_from","effective_to","available_at","observed_at",
      "confidence_type","confidence_value","contradiction_state","quarantine_state"
    }
    require(critical <= set(names),f"required field semantics missing: {sorted(critical-set(names))}")
    firewalls=set(fields.get("semantic_firewalls",[]))
    for required in (
      "INSTALLED_CAPACITY_NE_EFFECTIVE_CAPACITY",
      "NAMEPLATE_CAPACITY_NE_USABLE_OUTPUT",
      "PROCESS_QUALIFICATION_NE_CUSTOMER_QUALIFICATION",
      "HBM_PRODUCTION_NE_QUALIFIED_HBM_FOR_SPECIFIC_ACCELERATOR",
      "NEW_CAPACITY_ANNOUNCEMENT_NE_CONSTRAINT_RESOLVED",
      "EXPORT_RESTRICTION_NE_COMPLETE_SUPPLY_CUTOFF",
    ):
        require(required in firewalls,f"semantic firewall missing: {required}")

    cases=d["cases"]
    crows=cases.get("cases",[])
    require(cases.get("required_case_count")==14,"required case count drifted")
    require({r.get("case_id") for r in crows}==set(range(1,15)),"required case IDs incomplete")
    require(all(r.get("status")=="GAP" for r in crows),"Batch017 prematurely claims required case coverage")
    require(cases.get("covered_case_count")==0,"Batch017 prematurely increments case coverage")

    authority=d["authority"]
    require(authority.get("parallel_architecture_authorized") is False,"parallel architecture unexpectedly authorized")
    owners={r.get("owner") for r in authority.get("authorities",[])}
    for owner in (
      "PIPELINE_T1_SOURCE_ACQUISITION","PIPELINE_T2_EVIDENCE_NORMALIZATION","PIPELINE_T3_SEMANTIC_EXTRACTION",
      "PIPELINE_T4_TRUST_GOVERNANCE","PIPELINE_T5_CONSTRAINT_FORMATION","PIPELINE_T6_CANONICAL_CANDIDATE_GOVERNANCE",
      "LILY_THREAD_2_CONSTRAINT_SEMANTICS","LILY_THREAD_3_CANONICAL_BENEFICIARY",
      "LILY_THREAD_4_BABY_ML_CONTRACT","LILY_THREAD_5_SOURCE_COVERAGE","LILY_THREAD_6_ARCHITECTURE_REGISTER"
    ):
        require(owner in owners,f"authority owner missing: {owner}")
    require(all(not (isinstance(o,str) and o.startswith("THREAD_")) for o in owners),"ambiguous bare THREAD_N owner introduced")

    status=d["status"]
    results=status.get("results",{})
    require(status.get("semantic_duplication_created") is False,"status reports semantic duplication")
    require(results.get("SEMICONDUCTOR_SPECIFIC_POPULATION")=="NO","Batch017 falsely claims population")
    for k in ("FACILITIES_POPULATED","SUPPLIERS_POPULATED","MATERIALS_POPULATED","DEPENDENCY_EDGES","CONSTRAINTS_FORMED","BENEFICIARY_CANDIDATES","OUTCOMES_CAPTURED"):
        require(results.get(k)==0,f"Batch017 falsely populates {k}")
    require(results.get("CROSS_SLICE_AI_SEMICONDUCTOR_POWER_GRAPH")=="NOT_BUILT","Batch017 falsely claims cross-slice graph")
    require(results.get("HISTORICAL_REPLAY")=="BLOCKED_NOT_BUILT","Batch017 falsely claims replay")
    require(results.get("FIRST_SEMICONDUCTOR_RUN")=="BLOCKED","Batch017 falsely claims semiconductor run readiness")
    require(status.get("next_repo_executable_lane")=="SECOND-SLICE-SOURCE-AUTHORITY-AND-FIRST-POPULATION","Batch017 next lane drifted")

    master=d["master"]
    active=master.get("active_verticals",{})
    require(set(active)=={"AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1",SLICE},"active vertical set drifted")
    r=master.get("readiness",{})
    require(r.get("SECOND_SLICE_SEMANTIC_REUSE",{}).get("status")=="PASS","master lost semantic reuse pass")
    require(r.get("SECOND_SLICE_NO_PARALLEL_ARCHITECTURE",{}).get("status")=="PASS","master parallel architecture guard drifted")
    require(r.get("SECOND_SLICE_REQUIRED_CASES_FROZEN",{}).get("count")==14,"master case count drifted")
    require(r.get("SECOND_SLICE_DOMAIN_POPULATED",{}).get("status")=="NO","master falsely marks second slice populated")
    require(r.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")
    require(master.get("first_serious_constraint_run")=="BLOCKED","master falsely serious-run ready")
    require(master.get("next_repo_executable_lane")=="SECOND-SLICE-SOURCE-AUTHORITY-AND-FIRST-POPULATION","master next lane drifted")

    print("CONSTRAINT_SECOND_SLICE_BATCH017_AUDIT_VALIDATION=PASS")
    print(f"SLICE_ID={SLICE}")
    print(f"FIELD_REQUIREMENTS_FROZEN={len(names)}")
    print("REQUIRED_CASES_FROZEN=14")
    print("SEMANTIC_DUPLICATION_CREATED=NO")
    print("SEMICONDUCTOR_SPECIFIC_POPULATION=NO")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    print("NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-SOURCE-AUTHORITY-AND-FIRST-POPULATION")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH017_AUDIT_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
