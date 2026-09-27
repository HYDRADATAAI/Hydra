#!/usr/bin/env python3
"""Validate Batch030 Micron quarantine and non-Micron replacement closure."""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT",Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
QOLD=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
QNEW=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V002_20260927.json"
QUAR=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001_20260927.json"
SRC=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_NON_MICRON_REPLACEMENT_SOURCE_REGISTRY_V001_20260927.json"
EVID=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_NON_MICRON_REPLACEMENT_EVIDENCE_V001_20260927.json"
C3=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_HBM_YIELD_CONSTRAINT_EVALUATION_V001_20260927.json"
C8=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_VALID_BENEFICIARY_EVALUATION_V001_20260927.json"
C11=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_CONSTRAINT_MIGRATION_EVALUATION_V001_20260927.json"
C14=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_DUPLICATE_SOURCE_INFLATION_EVALUATION_V001_20260927.json"
OVER=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260927.json"
STATUS=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_QUARANTINE_NON_MICRON_REPLACEMENT_STATUS_V001_20260927.json"
MASTER=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_MASTER_STATUS_V001_20260927.json"
B021=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_SUBSTITUTION_MIGRATION_POWER_EVIDENCE_V001_20260926.json"
RUNNER=ROOT/"tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH030_BROWSER_CAPTURE_V001_20260927.py"
MAT=ROOT/"tools/materialize_constraint_second_slice_batch030_private_t1.py"
VER=ROOT/"tools/verify_constraint_second_slice_batch030_private_t1.py"
HAND=ROOT/"tools/build_constraint_second_slice_batch030_private_t1_handback.py"
LAUNCH=ROOT/"tools/private/Invoke-HYDRAConstraintSemiconductorBatch030_V001_20260927.ps1"

class ValidationFailure(Exception): pass
def require(c,m):
    if not c: raise ValidationFailure(m)
def load(p:Path)->dict[str,Any]:
    require(p.is_file(),f"missing artifact: {p.relative_to(ROOT)}")
    v=json.loads(p.read_text(encoding="utf-8"))
    require(isinstance(v,dict),f"root must be object: {p.relative_to(ROOT)}")
    return v
def micronish(value:str)->bool:
    v=value.lower()
    return "micron" in v or "globenewswire.com" in v

def main()->int:
    old=load(QOLD); new=load(QNEW); quar=load(QUAR); src=load(SRC); evid=load(EVID)
    c3=load(C3); c8=load(C8); c11=load(C11); c14=load(C14); over=load(OVER); status=load(STATUS); master=load(MASTER); b21=load(B021)

    oq=old.get("queue",[]); nq=new.get("queue",[])
    require(len(oq)==41,"predecessor queue count drifted")
    require(len(nq)==38 and new.get("source_count")==38,"Batch030 queue count drifted")
    qids={x["source_id"] for x in oq}; nids={x["source_id"] for x in nq}
    quarantine=set(quar.get("quarantined",[]))
    require(len(quarantine)==9,"quarantine count drifted")
    require(quar.get("retry_authorized") is False,"Micron retry unexpectedly authorized")
    require(quar.get("predecessor_artifacts_mutated") is False,"predecessor mutation unexpectedly allowed")
    require(quarantine<=qids,"quarantine references source outside predecessor queue")

    replacements=src.get("sources",[])
    require(len(replacements)==6,"replacement source count drifted")
    replacement_ids={x["source_id"] for x in replacements}
    expected=(qids-quarantine)|replacement_ids
    require(nids==expected,f"Batch030 queue source set drifted: {sorted(nids^expected)}")
    require(new.get("quarantined_predecessor_source_count")==9,"queue quarantine count drifted")
    require(new.get("replacement_source_count")==6,"queue replacement count drifted")
    require(new.get("provider_exclusion_policy")=="MICRON_AND_MICRON_DISTRIBUTION_COPY_EXCLUDED_FROM_ACTIVE_CAPTURE","provider exclusion policy drifted")
    require(new.get("release_id")=="REL-SEMI-B030-V001","Batch030 release id drifted")
    require(new.get("private_inbox_default")=="D:\\HYDRA_PRIVATE\\constraint\\capture_inbox\\semiconductor_batch030","Batch030 inbox drifted")

    for row in nq:
        blob=json.dumps(row,ensure_ascii=False)
        require(not micronish(str(row.get("source_id",""))),f"Micron-linked source_id escaped quarantine: {row.get('source_id')}")
        require(not micronish(str(row.get("source_locator",""))),f"Micron-linked locator escaped quarantine: {row.get('source_id')}")
        require(not micronish(str(row.get("publisher",""))),f"Micron publisher escaped quarantine: {row.get('source_id')}")
        require(row.get("historical_backdating_authorized") is False,f"{row.get('source_id')}: backdating flag drifted")
    require(len({x["source_version_id"] for x in nq})==38,"Batch030 source_version_id uniqueness drifted")
    require([x["source_version_id"] for x in nq]==[f"SV-SEMI-B030-{i:03d}" for i in range(1,39)],"Batch030 source-version sequence drifted")

    for row in replacements:
        require(not micronish(json.dumps(row,ensure_ascii=False)),f"replacement source is Micron-linked: {row.get('source_id')}")
        require(row.get("ordinary_raw_lineage_eligible") is False,f"{row.get('source_id')}: replacement falsely raw-lineage eligible")

    eids={x.get("evidence_id") for x in evid.get("evidence",[])}
    require(len(eids)==7,"replacement evidence count drifted")
    source_ids={x.get("source_id") for x in replacements}
    for row in evid.get("evidence",[]):
        require(row.get("source_id") in source_ids,"replacement evidence references non-replacement source")

    e3=c3.get("evaluation",{})
    require(e3.get("case_id")==3 and e3.get("binding_effective_output_constraint_proven") is True,"Case3 replacement coverage drifted")
    require(e3.get("coverage_state")=="COVERED_REVIEWED_SHADOW_REAL_PRIMARY_NON_MICRON","Case3 replacement state drifted")
    require(set(e3.get("evidence_ids",[]))<=eids,"Case3 replacement evidence unresolved")
    require("MICRON" not in json.dumps(c3).upper(),"Case3 still contains Micron basis")

    rels=c8.get("relationships",[])
    require(len(rels)==1 and rels[0].get("beneficiary_entity_id")=="ENTITY-SK-HYNIX","Case8 replacement entity drifted")
    require(rels[0].get("case_disposition")=="VALID_BENEFICIARY_CASE_COVERED_SHADOW_NON_MICRON","Case8 disposition drifted")
    require("MICRON" not in json.dumps(c8).upper(),"Case8 still contains Micron basis")
    require(rels[0].get("qualified_relationship_minted") is False,"Case8 falsely minted canonical beneficiary")

    mig=c11.get("evaluations",[])
    require(len(mig)==1 and mig[0].get("case_11_coverage") is True,"Case11 replacement coverage drifted")
    require(mig[0].get("relief_event",{}).get("state")=="OBSERVED_PARTIAL_RELIEF","Case11 relief state drifted")
    require(mig[0].get("systemwide_resolution_asserted") is False,"Case11 falsely asserts systemwide resolution")
    require("MICRON" not in json.dumps(c11).upper(),"Case11 still contains Micron basis")

    ev14=c14.get("evaluation",{})
    occ=ev14.get("evidence_occurrences",[])
    require(ev14.get("case_id")==14 and len(occ)==3,"Case14 replacement occurrence count drifted")
    require(ev14.get("independent_evidence_cluster_count")==2,"Case14 cluster count drifted")
    translation=[x for x in occ if x.get("source_role")=="TRANSLATION_COPY_SAME_PUBLISHER_EVENT"]
    require(len(translation)==1 and translation[0].get("independent_confirmation_weight")==0,"Case14 translation copy inflates evidence")
    existing_ids={x.get("evidence_id") for x in b21.get("evidence",[])}
    require("EV-SEMI-B021-SAMSUNG-AMD-HBM3E-QUALIFIED-2026" in existing_ids,"Case14 independent AMD counterpart evidence missing")
    require("MICRON" not in json.dumps(c14).upper(),"Case14 still contains Micron basis")

    require(over.get("covered_case_count_after")==13,"required case count drifted")
    require(over.get("remaining_gap_case_ids")==[12],"remaining case set drifted")
    require(over.get("micron_dependent_active_cases_after")==0,"Micron-dependent active case remains")
    require({x.get("case_id") for x in over.get("replacements",[])}=={3,8,11,14},"replacement case set drifted")

    results=status.get("results",{})
    expected_metrics={
      "MICRON_LINKED_SOURCE_INTENTS_QUARANTINED":9,
      "NON_MICRON_REPLACEMENT_SOURCES_ADDED":6,
      "ACTIVE_CAPTURE_SOURCE_COUNT":38,
      "MICRON_ACTIVE_CAPTURE_COUNT":0,
      "REQUIRED_CASES_COVERED":13,
      "REQUIRED_CASES_TOTAL":14,
      "REMAINING_REQUIRED_CASES":[12],
      "RAW_SOURCE_VERSIONS_MATERIALIZED":0,
      "VALID_T1_RECEIPTS":0,
      "ORDINARY_T2_ELIGIBLE_SOURCES":0,
      "FIRST_SEMICONDUCTOR_RUN":"BLOCKED"
    }
    for k,v in expected_metrics.items(): require(results.get(k)==v,f"Batch030 status metric drifted: {k}")
    require(status.get("next_required_action")=="RUN_BATCH030_MICRON_FREE_BROWSER_CAPTURE","Batch030 next action drifted")

    rd=master.get("readiness",{})
    require(rd.get("SECOND_SLICE_PROVIDER_EXCLUSION_POLICY",{}).get("status")=="ACTIVE_MICRON_QUARANTINED","master provider policy drifted")
    require(rd.get("SECOND_SLICE_MICRON_DEPENDENT_ACTIVE_CASES",{}).get("status")=="NONE","master Micron dependency remains")
    require(rd.get("SECOND_SLICE_PRIVATE_CAPTURE_QUEUE",{}).get("source_count")==38,"master capture count drifted")
    require(rd.get("SECOND_SLICE_REPLAY_READY",{}).get("status")=="NO","master falsely replay ready")
    require(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")

    for p in (RUNNER,MAT,VER,HAND,LAUNCH): require(p.is_file(),f"Batch030 tool missing: {p.relative_to(ROOT)}")
    runner=RUNNER.read_text(encoding="utf-8")
    require("EXPECTED_COUNT=38" in runner,"Batch030 runner count drifted")
    require("Micron-linked source is forbidden in Batch030" in runner,"Batch030 runner provider firewall missing")
    require("semiconductor_batch030" in LAUNCH.read_text(encoding="utf-8"),"Batch030 launcher inbox drifted")

    print("CONSTRAINT_SECOND_SLICE_BATCH030_MICRON_QUARANTINE_VALIDATION=PASS")
    print("MICRON_LINKED_SOURCE_INTENTS_QUARANTINED=9")
    print("NON_MICRON_REPLACEMENT_SOURCES_ADDED=6")
    print("ACTIVE_CAPTURE_SOURCE_COUNT=38")
    print("MICRON_ACTIVE_CAPTURE_COUNT=0")
    print("REQUIRED_CASES_COVERED=13/14")
    print("REMAINING_REQUIRED_CASE=12")
    print("RAW_SOURCE_VERSIONS_MATERIALIZED=0")
    print("NEXT_REQUIRED_ACTION=RUN_BATCH030_MICRON_FREE_BROWSER_CAPTURE")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH030_VALIDATION=FAIL"); print(f"ERROR={exc}"); raise SystemExit(1)
