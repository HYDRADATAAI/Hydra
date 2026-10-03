#!/usr/bin/env python3
"""Validate Batch022 semiconductor tool/material/duplicate-evidence depth."""

from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT",Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
FILES={
"source":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_YIELD_TOOL_MATERIAL_DUPLICATE_SOURCE_REGISTRY_V001_20260926.json",
"evidence":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_YIELD_TOOL_MATERIAL_DUPLICATE_EVIDENCE_V001_20260926.json",
"tool":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_TOOL_BOTTLENECK_EVALUATION_V001_20260926.json",
"material":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_MATERIAL_BOTTLENECK_EVALUATION_V001_20260926.json",
"duplicate":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_DUPLICATE_SOURCE_INFLATION_EVALUATION_V001_20260926.json",
"yield":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_HBM_YIELD_CONSTRAINT_EVALUATION_V001_20260926.json",
"cases":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json",
"status":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_YIELD_TOOL_MATERIAL_DUPLICATE_STATUS_V001_20260926.json",
"master":ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_MASTER_STATUS_V001_20260926.json",
"b021cases":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json",
}
SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
class ValidationFailure(Exception): pass
def require(c,m):
    if not c: raise ValidationFailure(m)
def load(p:Path)->dict[str,Any]:
    require(p.is_file(),f"required artifact missing: {p.relative_to(ROOT)}")
    v=json.loads(p.read_text(encoding="utf-8")); require(isinstance(v,dict),"root must be object"); return v

def main()->int:
    d={k:load(v) for k,v in FILES.items()}
    for k in ("source","evidence","tool","material","duplicate","yield","cases","status"):
        require(d[k].get("slice_id")==SLICE,f"{k} slice_id drifted")

    src=d["source"]; rows=src.get("sources",[])
    require(len(rows)==9,"Batch022 source count drifted")
    require(src.get("source_content_persisted") is False,"Batch022 falsely claims source persistence")
    sids={r.get("source_id") for r in rows}; require(len(sids)==9 and None not in sids,"Batch022 source IDs invalid")
    for r in rows:
        require(r.get("acquired_at")==r.get("available_at"),"Batch022 conservative available_at drifted")
        require(r.get("ordinary_raw_lineage_eligible") is False,"Batch022 source unexpectedly ordinary raw-lineage eligible")

    ev=d["evidence"].get("evidence",[])
    require(len(ev)==9,"Batch022 evidence count drifted")
    eids={r.get("evidence_id") for r in ev}; require(len(eids)==9,"Batch022 evidence IDs duplicate")
    require(all(r.get("source_id") in sids for r in ev),"Batch022 evidence source lineage unresolved")

    tool=d["tool"]["evaluation"]
    require(tool.get("case_id")==4,"tool case ID drifted")
    require(tool.get("bottleneck_type")=="BACKEND_TEST_EQUIPMENT_SHORTAGE","tool bottleneck type drifted")
    require(tool.get("specific_fab_delay_proven") is False,"tool shortage was escalated into a specific fab delay")
    require(tool.get("case_variant")=="REAL_TOOL_BOTTLENECK_WITHOUT_SPECIFIC_FAB_COMPLETION_DELAY","tool case variant drifted")
    require(tool.get("coverage_state")=="COVERED_REVIEWED_SHADOW_REAL_PRIMARY_BOUNDED","tool case coverage state drifted")
    require(tool.get("canonical_constraint_minted") is False,"tool case minted canonical constraint")
    require(tool.get("ordinary_t6_eligible") is False,"tool case became ordinary T6 eligible")

    mat=d["material"]["evaluation"]
    require(mat.get("case_id")==5,"material case ID drifted")
    require(mat.get("material")=="HIGH_PURITY_QUARTZ","material identity drifted")
    require(mat.get("raw_resource_state")=="QUARTZ_GEOLOGICALLY_ABUNDANT","material geological state drifted")
    require(mat.get("required_grade_state")=="HIGH_PURITY_AND_ULTRA_HIGH_PURITY_PROCESSING_REQUIRED","material grade distinction drifted")
    require(mat.get("producer_concentration")=="TWO_US_PRODUCERS_AROUND_SPRUCE_PINE_IN_2024","HPQ producer concentration drifted")
    require(mat.get("constraint_attachment")=="HIGH_PURITY_PROCESSING_AND_OPERATIONAL_AVAILABILITY_NOT_GEOLOGICAL_QUARTZ_EXISTENCE","material bottleneck attached to wrong stage")
    require(mat.get("downstream_critical_supply_failure_proven") is False,"downstream semiconductor supply failure was fabricated")
    require(mat.get("coverage_state")=="COVERED_REVIEWED_SHADOW_REAL_PRIMARY_BOUNDED","material case coverage state drifted")

    dup=d["duplicate"]["evaluation"]
    require(dup.get("case_id")==14,"duplicate case ID drifted")
    require(dup.get("unique_occurrence_count")==2,"duplicate occurrence count drifted")
    require(dup.get("independent_evidence_cluster_count")==1,"duplicate copies inflated independent evidence count")
    require(dup.get("confidence_multiplier_from_copy")==0,"distribution copy inflated confidence")
    occ=dup.get("evidence_occurrences",[])
    require(len(occ)==2,"duplicate evidence occurrence count drifted")
    clusters={r.get("independence_cluster_id") for r in occ}
    require(len(clusters)==1,"duplicate occurrences split into multiple independence clusters")
    weights=sorted(r.get("independent_confirmation_weight") for r in occ)
    require(weights==[0,1],"duplicate independence weights drifted")
    require(dup.get("coverage_state")=="COVERED_REVIEWED_SHADOW_REAL_DUPLICATE","duplicate case coverage state drifted")

    y=d["yield"]["evaluation"]
    require(y.get("case_id")==3,"yield case ID drifted")
    require(y.get("yield_separation_proven") is True,"yield separation lost")
    require(y.get("mass_production_complexity_proven") is True,"HBM complexity prerequisite lost")
    require(y.get("numeric_yield_available") is False,"numeric yield was fabricated")
    require(y.get("binding_effective_output_constraint_proven") is False,"binding HBM yield constraint was fabricated")
    require(y.get("coverage_state")=="PROGRESS_ONLY_NOT_COVERED","yield case prematurely covered")

    prev=d["b021cases"]
    require(prev.get("covered_case_count_after")==8,"Batch021 predecessor coverage drifted")
    require(prev.get("remaining_gap_case_ids")==[3,4,5,11,12,14],"Batch021 predecessor gaps were rewritten")

    cases=d["cases"]
    require(cases.get("covered_case_count_before")==8 and cases.get("covered_case_count_after")==11,"Batch022 coverage count drifted")
    updates={r.get("case_id"):r for r in cases.get("updates",[])}
    require(set(updates)=={4,5,14},"Batch022 newly covered case set drifted")
    require(cases.get("remaining_gap_case_ids")==[3,11,12],"Batch022 remaining gap set drifted")
    prog={r.get("case_id"):r for r in cases.get("progress_only",[])}
    require(set(prog)=={3,11,12},"Batch022 progress-only set drifted")
    require(prog[3].get("progress_state")=="YIELD_LIMITER_SEPARATION_PROVEN_BINDING_OUTPUT_CONSTRAINT_NOT_PROVEN","Case 3 progress state drifted")
    require(prog[11].get("progress_state")=="UNCHANGED_MIGRATION_CANDIDATE_NOT_COVERED","Case 11 prematurely covered")
    require(prog[12].get("progress_state")=="UNCHANGED_EXTERNAL_RAW_LINEAGE_GATE","Case 12 raw-lineage gate drifted")

    st=d["status"]; r=st.get("results",{})
    expected={
      "PRIMARY_SOURCES_ADDED":9,"EVIDENCE_OBSERVATIONS_ADDED":9,
      "TOOL_BOTTLENECK_CASES_COVERED":1,"MATERIAL_BOTTLENECK_CASES_COVERED":1,
      "DUPLICATE_EVIDENCE_CASES_COVERED":1,"YIELD_CONSTRAINT_CASES_COVERED":0,
      "REQUIRED_CASES_COVERED":11,"REQUIRED_CASES_TOTAL":14,
      "NEW_REQUIRED_CASES_COVERED":[4,5,14],"REMAINING_GAP_CASES":[3,11,12],
      "FIRST_SEMICONDUCTOR_RUN":"BLOCKED"
    }
    for k,v in expected.items(): require(r.get(k)==v,f"Batch022 status metric drifted: {k}")
    require(st.get("next_repo_executable_lane")=="SECOND-SLICE-HBM-YIELD-AND-CONSTRAINT-MIGRATION-DEPTH","Batch022 next lane drifted")

    m=d["master"]; rd=m.get("readiness",{})
    require(rd.get("SECOND_SLICE_TOOL_BOTTLENECK",{}).get("status")=="PASS_REVIEWED_SHADOW_BOUNDED_VARIANT","master tool status drifted")
    require(rd.get("SECOND_SLICE_MATERIAL_BOTTLENECK",{}).get("status")=="PASS_REVIEWED_SHADOW","master material status drifted")
    require(rd.get("SECOND_SLICE_DUPLICATE_EVIDENCE_GOVERNANCE",{}).get("status")=="PASS_REVIEWED_SHADOW","master duplicate status drifted")
    require(rd.get("SECOND_SLICE_HBM_YIELD_CONSTRAINT",{}).get("status")=="PARTIAL_NOT_COVERED","master yield status drifted")
    require(rd.get("SECOND_SLICE_CONSTRAINT_MIGRATION",{}).get("status")=="PARTIAL_NOT_COVERED","master migration status drifted")
    require(rd.get("SECOND_SLICE_REQUIRED_CASES",{}).get("covered")==11,"master required-case count drifted")
    require(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")
    require(m.get("first_serious_constraint_run")=="BLOCKED","master falsely serious-run ready")

    print("CONSTRAINT_SECOND_SLICE_BATCH022_TOOL_MATERIAL_DUPLICATE_VALIDATION=PASS")
    print("NEW_REQUIRED_CASES_COVERED=4,5,14")
    print("REQUIRED_CASES_COVERED=11/14")
    print("TOOL_BOTTLENECK_CASES=1")
    print("MATERIAL_BOTTLENECK_CASES=1")
    print("DUPLICATE_EVIDENCE_CASES=1")
    print("HBM_YIELD_CASES_COVERED=0")
    print("REMAINING_GAPS=3,11,12")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    print("NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-HBM-YIELD-AND-CONSTRAINT-MIGRATION-DEPTH")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH022_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
