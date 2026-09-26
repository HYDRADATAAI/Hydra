#!/usr/bin/env python3
"""Validate Batch018 semiconductor source authority and first population."""

from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
FILES={
"authority":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_SOURCE_AUTHORITY_REGISTRY_V001_20260926.json",
"sources":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_SOURCE_REGISTRY_V001_20260926.json",
"evidence":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_EVIDENCE_SEED_V001_20260926.json",
"capacity":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_CAPACITY_YIELD_QUALIFICATION_OVERLAY_V001_20260926.json",
"graph":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_GRAPH_SEED_V001_20260926.json",
"candidates":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_T5_CANDIDATE_PROPOSALS_V001_20260926.json",
"cases":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_REQUIRED_CASE_OVERLAY_V001_20260926.json",
"status":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_STATUS_V001_20260926.json",
"master":ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_MASTER_STATUS_V001_20260926.json",
"batch017_cases":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_REQUIRED_CASE_MATRIX_V001_20260926.json",
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
    for k in ("sources","evidence","capacity","graph","candidates","cases","status"):
        require(d[k].get("slice_id")==SLICE,f"{k} slice_id drifted")

    auth=d["authority"]
    require(auth.get("runtime_live_source_authority_used") is False,"live source authority unexpectedly used")
    priorities={r.get("priority") for r in auth.get("priority_families",[])}
    require({"P0","P1","P2"} <= priorities,"source priority buckets incomplete")
    require("COMPANY_FORWARD_GUIDANCE_IS_NOT_REALIZED_CAPACITY" in auth.get("admission_rules",[]),"forward-guidance firewall missing")

    sources=d["sources"]; rows=sources.get("sources",[])
    require(len(rows)==6,"source count drifted")
    require(sources.get("source_content_persisted") is False,"raw source persistence falsely claimed")
    sids={r.get("source_id") for r in rows}
    require(len(sids)==6 and None not in sids,"source IDs invalid")
    for r in rows:
        require(r.get("acquired_at")==r.get("available_at"),"conservative available_at drifted")
        require(r.get("ordinary_raw_lineage_eligible") is False,"source unexpectedly ordinary raw-lineage eligible")

    ev=d["evidence"].get("evidence",[])
    require(len(ev)==10,"evidence count drifted")
    require(all(r.get("source_id") in sids for r in ev),"evidence source resolution failed")
    evids={r.get("evidence_id") for r in ev}
    require(len(evids)==10,"evidence IDs duplicate")

    caps=d["capacity"].get("rows",[])
    require(len(caps)==6,"capacity observation count drifted")
    by={r.get("observation_id"):r for r in caps}
    require(by["CAPOBS-MICRON-HBM-2025-BOOKED-001"].get("capacity_state")=="BOOKED","Micron sold-out supply not represented as booked")
    require(by["CAPOBS-MICRON-HBM-2025-BOOKED-001"].get("effective_capacity") is None,"Micron booked state fabricated effective capacity")
    m12=by["CAPOBS-MICRON-HBM3E12H-RAMP-001"]
    require(m12.get("capacity_state")=="RAMPING","Micron 12H ramp state drifted")
    require(m12.get("yield_value") is None and m12.get("yield_state")=="RAMPING_UNQUANTIFIED","Micron yield was fabricated or collapsed")
    cowos=by["CAPOBS-TSMC-COWOS-2025-FULLY-LOADED-001"]
    require(cowos.get("capacity_state")=="OPERATIONAL" and cowos.get("utilization_state")=="FULLY_LOADED","CoWoS current capacity state drifted")
    exp=by["CAPOBS-TSMC-COWOS-2025-EXPANSION-001"]
    require(exp.get("capacity_state")=="RAMPING","CoWoS expansion state drifted")
    require("DOES NOT PROVE DOUBLING ACHIEVED" in exp.get("semantic_limit",""),"CoWoS expansion realization firewall missing")

    graph=d["graph"]
    require(len(graph.get("nodes",[]))==12,"graph node count drifted")
    require(len(graph.get("edges",[]))==13,"graph edge count drifted")
    require(graph.get("cross_slice_edge_count")==1,"cross-slice edge count drifted")
    require(any(e.get("from")=="N-AI-COMPUTE-DEMAND" and e.get("status")=="SUPPORTED_CROSS_SLICE" for e in graph["edges"]),"AI first-slice bridge missing")
    require(all(set(e.get("evidence_ids",[])) <= evids for e in graph["edges"]),"graph evidence IDs unresolved")

    candidates=d["candidates"].get("candidates",[])
    require(len(candidates)==2,"candidate count drifted")
    for c in candidates:
        require(c.get("canonical_constraint_id") is None,"canonical constraint minted")
        require(c.get("ordinary_t6_eligible") is False,"candidate became ordinary T6 eligible")
        require(c.get("constraint_class")=="CAPACITY","candidate class drifted")
        fc=c.get("formation_confidence",{})
        require(fc.get("measurement_state")=="UNKNOWN_NOT_MEASURED" and fc.get("value") is None,"formation confidence fabricated")
    hbm=next(c for c in candidates if c["constraint_candidate_id"]=="T5C-SEMI-HBM-BOOKED-SUPPLY-2024-2025-001")
    require("DOES_NOT_ASSERT ALL GLOBAL HBM SUPPLY" in hbm.get("semantic_limit",""),"HBM scope was generalized")

    c17=d["batch017_cases"]
    require(all(r.get("status")=="GAP" for r in c17.get("cases",[])),"Batch017 predecessor case matrix was rewritten")
    ov=d["cases"]
    require(ov.get("covered_case_count_after")==2,"case coverage count drifted")
    updates={r.get("case_id"):r for r in ov.get("updates",[])}
    require(set(updates)=={1,2},"Batch018 case update set drifted")
    require(all(r.get("successor_status")=="COVERED_REVIEWED_SHADOW_REAL_PRIMARY_BOUNDED" for r in updates.values()),"case coverage scope drifted")
    require(ov.get("remaining_gap_case_ids")==list(range(3,15)),"remaining case gaps drifted")

    status=d["status"]; res=status.get("results",{})
    expected={
      "SOURCE_AUTHORITY_REGISTRY_READY":"YES","PRIMARY_SOURCES_REGISTERED":6,"EVIDENCE_OBSERVATIONS":10,
      "SUPPLIERS_POPULATED":4,"PRODUCTS_TECHNOLOGIES_POPULATED":7,"FACILITIES_POPULATED":0,"MATERIALS_POPULATED":0,
      "CAPACITY_STATE_OBSERVATIONS":6,"YIELD_STATE_OBSERVATIONS":1,"QUALIFICATION_STATE_OBSERVATIONS":2,
      "DEPENDENCY_EDGES":13,"CROSS_SLICE_EDGES":1,"CONSTRAINTS_FORMED_SHADOW":2,"CANONICAL_CONSTRAINTS_MINTED":0,
      "REQUIRED_CASES_COVERED":2,"REQUIRED_CASES_TOTAL":14,"OUTCOMES_CAPTURED":0,"FIRST_SEMICONDUCTOR_RUN":"BLOCKED"
    }
    for k,v in expected.items(): require(res.get(k)==v,f"status metric drifted: {k}")
    require("SEMICONDUCTOR-SLICE-001-SOURCE-AUTHORITY-REGISTRY-EMPTY" in status.get("closed_blockers",[]),"source-authority blocker not closed")
    require(status.get("next_repo_executable_lane")=="SECOND-SLICE-FACILITY-MATERIAL-EQUIPMENT-AND-QUALIFICATION-POPULATION","next lane drifted")

    master=d["master"]; rd=master.get("readiness",{})
    require(rd.get("SECOND_SLICE_SOURCE_AUTHORITY_READY",{}).get("status")=="YES","master source authority not ready")
    require(rd.get("SECOND_SLICE_DOMAIN_POPULATED",{}).get("status")=="PARTIAL","master domain population status drifted")
    require(rd.get("SECOND_SLICE_CAPACITY_STATE_SEPARATION",{}).get("status")=="PASS_INITIAL","capacity separation lost")
    require(rd.get("SECOND_SLICE_YIELD_SEPARATION",{}).get("status")=="PASS_INITIAL_UNQUANTIFIED","yield separation lost")
    require(rd.get("SECOND_SLICE_QUALIFICATION_SEPARATION",{}).get("status")=="PASS_INITIAL","qualification separation lost")
    require(rd.get("SECOND_SLICE_CONSTRAINT_FORMATION",{}).get("count")==2,"master candidate count drifted")
    require(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")
    require(master.get("first_serious_constraint_run")=="BLOCKED","master falsely serious-run ready")

    print("CONSTRAINT_SECOND_SLICE_BATCH018_POPULATION_VALIDATION=PASS")
    print("PRIMARY_SOURCES_REGISTERED=6")
    print("EVIDENCE_OBSERVATIONS=10")
    print("SUPPLIERS_POPULATED=4")
    print("PRODUCTS_TECHNOLOGIES_POPULATED=7")
    print("CAPACITY_STATE_OBSERVATIONS=6")
    print("DEPENDENCY_EDGES=13")
    print("CROSS_SLICE_EDGES=1")
    print("CONSTRAINTS_FORMED_SHADOW=2")
    print("REQUIRED_CASES_COVERED=2/14")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    print("NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-FACILITY-MATERIAL-EQUIPMENT-AND-QUALIFICATION-POPULATION")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError,StopIteration) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH018_POPULATION_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
