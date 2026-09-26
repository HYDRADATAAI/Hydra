#!/usr/bin/env python3
"""Validate Batch021 valid-beneficiary, qualification, substitution, migration, and power depth."""

from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT",Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
FIRST=ROOT/"docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
FILES={
"source":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_SUBSTITUTION_MIGRATION_POWER_SOURCE_REGISTRY_V001_20260926.json",
"evidence":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_SUBSTITUTION_MIGRATION_POWER_EVIDENCE_V001_20260926.json",
"beneficiary":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_EVALUATION_V001_20260926.json",
"substitution":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_SUBSTITUTION_QUALIFICATION_EVALUATION_V001_20260926.json",
"qualification":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_SAMSUNG_HBM3E_QUALIFICATION_TIMELINE_V001_20260926.json",
"migration":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_CONSTRAINT_MIGRATION_EVALUATION_V001_20260926.json",
"power":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_TO_POWER_INFRASTRUCTURE_GRAPH_OVERLAY_V001_20260926.json",
"cases":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json",
"status":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_SUBSTITUTION_MIGRATION_POWER_STATUS_V001_20260926.json",
"master":ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_MASTER_STATUS_V001_20260926.json",
"b020_cases":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json",
"b020_ben":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_FALSE_BENEFICIARY_EVALUATION_V001_20260926.json",
"b020_sub":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_SUBSTITUTION_EVALUATION_V001_20260926.json",
"b019_graph":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_GRAPH_OVERLAY_V001_20260926.json",
"first_graph":FIRST/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_GRAPH_SEED_V001_20260925.json",
}
SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
class ValidationFailure(Exception):pass
def require(c,m):
    if not c: raise ValidationFailure(m)
def load(p:Path)->dict[str,Any]:
    require(p.is_file(),f"required artifact missing: {p.relative_to(ROOT)}")
    v=json.loads(p.read_text(encoding="utf-8")); require(isinstance(v,dict),"root must be object"); return v

def main()->int:
    d={k:load(v) for k,v in FILES.items()}
    for k in ("source","evidence","beneficiary","substitution","qualification","migration","cases","status"):
        require(d[k].get("slice_id")==SLICE,f"{k} slice_id drifted")

    src=d["source"]; rows=src.get("sources",[])
    require(len(rows)==7,"Batch021 source count drifted")
    require(src.get("source_content_persisted") is False,"Batch021 falsely claims raw source persistence")
    sids={r.get("source_id") for r in rows}; require(len(sids)==7 and None not in sids,"Batch021 source IDs invalid")
    for r in rows:
        require(r.get("acquired_at")==r.get("available_at"),"Batch021 conservative available_at drifted")
        require(r.get("ordinary_raw_lineage_eligible") is False,"Batch021 source unexpectedly ordinary raw-lineage eligible")

    ev=d["evidence"].get("evidence",[]); require(len(ev)==8,"Batch021 evidence count drifted")
    eids={r.get("evidence_id") for r in ev}; require(len(eids)==8,"Batch021 evidence IDs duplicate")
    require(all(r.get("source_id") in sids for r in ev),"Batch021 evidence source lineage unresolved")

    ben=d["beneficiary"]; rel=ben.get("relationships",[])
    require(len(rel)==1,"Batch021 valid-beneficiary relationship count drifted")
    b=rel[0]
    require(b.get("beneficiary_relationship_id")=="BEN-SEMI-MICRON-HBM-001","Micron beneficiary identity drifted")
    require(b.get("qualification_state")=="INELIGIBLE_TO_EVALUATE","Micron canonical qualification escaped gate")
    require(b.get("shadow_prequalification_state")=="VALID_BENEFICIARY_INPUT_PATTERN_SATISFIED","Micron valid-beneficiary input pattern not satisfied")
    require(b.get("canonical_qualification_state")=="BLOCKED","Micron canonical beneficiary gate escaped")
    require(b.get("qualified_relationship_minted") is False,"Micron qualified beneficiary was minted")
    require(b.get("ordinary_t6_eligible") is False,"Micron beneficiary became ordinary T6 eligible")
    lineage=b.get("evidence_lineage",{})
    for key in ("constraint_evidence","entity_connection","advantage_mechanism","capacity_or_availability","qualification_or_addressability","economic_or_strategic_capture"):
        require(isinstance(lineage.get(key),list) and lineage[key],f"Micron beneficiary evidence role missing: {key}")
    require(b.get("self_constraint_state")=="CONSTRAINED_BUT_CAPTURE_PROVEN","Micron self-constraint state drifted")

    b020ben=d["b020_ben"]
    require(b020ben.get("false_beneficiary_rejection_count")==1,"Batch020 false-beneficiary history drifted")
    require(b020ben["relationships"][0].get("case_disposition")=="FALSE_BENEFICIARY_REJECTED","Batch020 Samsung rejection was rewritten")

    sub=d["substitution"]; sr=sub.get("evaluations",[]); require(len(sr)==1,"Batch021 substitution row count drifted")
    s=sr[0]
    require(s.get("substitution_id")=="SUB-SEMI-SAMSUNG-HBM3E-2024-001","Samsung substitution identity drifted")
    require(s.get("predecessor_specific_target_qualification_state")=="UNKNOWN_NOT_PROVEN","Samsung predecessor qualification history drifted")
    require(s.get("specific_target_qualification_state")=="PROVEN_AMD_MI350X_MI355X","Samsung target qualification not proven")
    require(s.get("unbooked_addressable_capacity_state")=="UNKNOWN_NOT_PROVEN","Samsung spare capacity was fabricated")
    require(s.get("substitution_state")=="QUALIFIED_TECHNICAL_SUBSTITUTE_CAPACITY_RELIEF_UNPROVEN","Samsung substitution state drifted")
    require(s.get("parent_constraint_effect")=="TECHNICAL_OPTION_SET_WEAKENED_NOT_RESOLVED","Samsung substitution falsely resolved parent constraint")
    require(s.get("ordinary_t6_eligible") is False,"Samsung substitution became ordinary T6 eligible")
    require(sub.get("qualified_technical_substitution_count")==1 and sub.get("proven_capacity_relief_count")==0,"Batch021 substitution counts drifted")

    b020sub=d["b020_sub"]["evaluations"][0]
    require(b020sub.get("specific_target_qualification_state")=="UNKNOWN_NOT_PROVEN","Batch020 substitution history was rewritten")
    require(b020sub.get("substitution_state")=="POTENTIAL_NOT_QUALIFIED","Batch020 substitution state was rewritten")

    q=d["qualification"]; qs=q.get("states",[]); require(len(qs)==3,"Samsung qualification timeline state count drifted")
    require([x.get("state_order") for x in qs]==[1,2,3],"Samsung qualification timeline ordering drifted")
    require(qs[0].get("target_specific_qualification")=="UNKNOWN" and qs[1].get("target_specific_qualification")=="UNKNOWN","Samsung historical qualification was backfilled")
    require(qs[2].get("target_specific_qualification")=="PROVEN_FOR_AMD_MI350X_MI355X","Samsung later qualification state drifted")
    require(q.get("historical_replay_eligible") is False,"Samsung qualification timeline falsely replay eligible")

    mig=d["migration"]["evaluations"][0]
    require(mig.get("relief_state")=="FORWARD_EXPECTATION_ONLY_NOT_OBSERVED_RESOLUTION","migration falsely claims observed prior relief")
    require(mig.get("migration_state")=="MIGRATION_CANDIDATE_NOT_COVERED","migration case prematurely covered")
    require(mig.get("case_11_coverage") is False,"Case 11 prematurely covered")

    p=d["power"]
    require(p.get("reused_semiconductor_nodes")==["FAC-SEMI-TSMC-ARIZONA-FIRST-FAB","GEO-ARIZONA-US"],"power overlay semiconductor node reuse drifted")
    require(p.get("reused_power_nodes")==["N-ELECTRICITY-DEMAND","N-TRANSMISSION"],"power overlay first-slice node reuse drifted")
    first_nodes={n.get("node_id") for n in d["first_graph"].get("nodes",[])}
    require(set(p.get("reused_power_nodes",[])) <= first_nodes,"power overlay references unknown first-slice nodes")
    require("FAC-SEMI-TSMC-ARIZONA-FIRST-FAB" in set(d["b019_graph"].get("nodes_added",[])),"power overlay references unknown semiconductor facility")
    require(len(p.get("edges_added",[]))==5,"power overlay edge count drifted")
    require(p.get("cross_slice_edges_added")==3,"power cross-slice edge count drifted")
    require(p.get("bounded_facility_power_dependency_proven") is True,"facility power dependency not proven")
    require(p.get("power_constraint_asserted") is False,"power dependency was escalated into a power constraint")

    b020cases=d["b020_cases"]; require(b020cases.get("covered_case_count_after")==5,"Batch020 predecessor coverage drifted")
    cases=d["cases"]; require(cases.get("covered_case_count_before")==5 and cases.get("covered_case_count_after")==8,"Batch021 case coverage count drifted")
    updates={x.get("case_id"):x for x in cases.get("updates",[])}
    require(set(updates)=={6,8,10},"Batch021 newly covered case set drifted")
    require(cases.get("remaining_gap_case_ids")==[3,4,5,11,12,14],"Batch021 remaining gap set drifted")
    prog={x.get("case_id"):x for x in cases.get("progress_only",[])}
    require(set(prog)=={11,12},"Batch021 progress-only case set drifted")
    require(prog[11].get("progress_state")=="MIGRATION_CANDIDATE_STRUCTURED_NOT_COVERED","Case 11 falsely covered")
    require(prog[12].get("progress_state")=="UNCHANGED_EXTERNAL_RAW_LINEAGE_GATE","Case 12 raw-lineage gate drifted")

    st=d["status"]; r=st.get("results",{})
    expected={"PRIMARY_SOURCES_ADDED":7,"EVIDENCE_OBSERVATIONS_ADDED":8,"VALID_BENEFICIARY_SHADOW_PATTERNS_ADDED":1,
      "QUALIFIED_CANONICAL_BENEFICIARIES_ADDED":0,"TECHNICALLY_QUALIFIED_SUBSTITUTIONS_ADDED":1,
      "PROVEN_CAPACITY_RELIEF_SUBSTITUTIONS_ADDED":0,"CONSTRAINT_MIGRATIONS_COVERED":0,"CROSS_SLICE_POWER_EDGES_ADDED":3,
      "REQUIRED_CASES_COVERED":8,"REQUIRED_CASES_TOTAL":14,"FIRST_SEMICONDUCTOR_RUN":"BLOCKED"}
    for k,v in expected.items(): require(r.get(k)==v,f"Batch021 status metric drifted: {k}")
    require(st.get("next_repo_executable_lane")=="SECOND-SLICE-YIELD-TOOL-MATERIAL-MIGRATION-AND-DUPLICATE-EVIDENCE-DEPTH","Batch021 next lane drifted")

    m=d["master"]; rd=m.get("readiness",{})
    require(rd.get("SECOND_SLICE_VALID_BENEFICIARY_PATTERN",{}).get("status")=="PASS_SHADOW_CANONICAL_BLOCKED","master beneficiary status drifted")
    require(rd.get("SECOND_SLICE_QUALIFICATION_BOTTLENECK",{}).get("status")=="PASS_REVIEWED_SHADOW","master qualification status drifted")
    require(rd.get("SECOND_SLICE_SUBSTITUTION",{}).get("status")=="PASS_TECHNICAL_QUALIFICATION_CAPACITY_RELIEF_UNPROVEN","master substitution status drifted")
    require(rd.get("SECOND_SLICE_CONSTRAINT_MIGRATION",{}).get("status")=="PARTIAL_NOT_COVERED","master migration status drifted")
    require(rd.get("SECOND_SLICE_REQUIRED_CASES",{}).get("covered")==8,"master required-case count drifted")
    require(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")
    require(m.get("first_serious_constraint_run")=="BLOCKED","master falsely serious-run ready")

    print("CONSTRAINT_SECOND_SLICE_BATCH021_VALID_BENEFICIARY_SUBSTITUTION_POWER_VALIDATION=PASS")
    print("NEW_REQUIRED_CASES_COVERED=6,8,10")
    print("REQUIRED_CASES_COVERED=8/14")
    print("VALID_BENEFICIARY_SHADOW_PATTERNS=1")
    print("QUALIFIED_CANONICAL_BENEFICIARIES=0")
    print("TECHNICALLY_QUALIFIED_SUBSTITUTIONS=1")
    print("PROVEN_CAPACITY_RELIEF_SUBSTITUTIONS=0")
    print("CONSTRAINT_MIGRATIONS_COVERED=0")
    print("CROSS_SLICE_POWER_EDGES=3")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    print("NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-YIELD-TOOL-MATERIAL-MIGRATION-AND-DUPLICATE-EVIDENCE-DEPTH")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH021_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
