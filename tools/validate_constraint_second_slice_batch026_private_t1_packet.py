#!/usr/bin/env python3
"""Validate the public Batch026 semiconductor private-T1 execution packet."""

from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT",Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
QUEUE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
CONTRACT=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_MATERIALIZATION_CONTRACT_V001_20260926.json"
STATUS=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_MATERIALIZATION_STATUS_V001_20260926.json"
MASTER=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_MASTER_STATUS_V001_20260926.json"
SUCCESSOR_STATUS=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_QUARANTINE_NON_MICRON_REPLACEMENT_STATUS_V001_20260927.json"
REGISTRIES=[
 BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_SOURCE_REGISTRY_V001_20260926.json",
 BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_SOURCE_REGISTRY_EXTENSION_V001_20260926.json",
 BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_POLICY_SUBSTITUTION_OUTCOME_SOURCE_REGISTRY_EXTENSION_V001_20260926.json",
 BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_SUBSTITUTION_MIGRATION_POWER_SOURCE_REGISTRY_V001_20260926.json",
 BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_YIELD_TOOL_MATERIAL_DUPLICATE_SOURCE_REGISTRY_V001_20260926.json",
 BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_HBM_YIELD_MIGRATION_SOURCE_REGISTRY_V001_20260926.json",
 BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_CONTINUOUS_CROSS_SLICE_SOURCE_REGISTRY_V001_20260926.json",
]
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
    queue_doc=load(QUEUE)
    contract=load(CONTRACT)
    status=load(STATUS)
    master=load(MASTER)
    successor=load(SUCCESSOR_STATUS)

    require(queue_doc.get("slice_id")==SLICE,"queue slice_id drifted")
    require(contract.get("slice_id")==SLICE,"contract slice_id drifted")
    require(status.get("slice_id")==SLICE,"status slice_id drifted")
    require(queue_doc.get("source_count")==41,"queue source_count drifted")
    queue=queue_doc.get("queue",[])
    require(isinstance(queue,list) and len(queue)==41,"queue must contain exactly 41 intents")
    require(queue_doc.get("public_repo_contains_raw_source_bytes") is False,"queue falsely allows public raw bytes")
    require(queue_doc.get("release_id")=="REL-SEMI-B026-V001","release id drifted")

    # Queue must equal the unique source set actually used by Batches 018-025.
    expected_ids=set()
    for path in REGISTRIES:
        reg=load(path)
        for src in reg.get("sources",[]):
            expected_ids.add(src.get("source_id"))
    require(None not in expected_ids,"predecessor registry contains invalid source id")
    require(len(expected_ids)==41,f"predecessor unique source count drifted: {len(expected_ids)}")
    actual_ids={row.get("source_id") for row in queue}
    require(actual_ids==expected_ids,f"Batch026 queue source set differs from Batches018-025 by {sorted(actual_ids ^ expected_ids)}")

    intents=[row.get("capture_intent_id") for row in queue]
    versions=[row.get("source_version_id") for row in queue]
    inbox=[row.get("inbox_filename") for row in queue]
    require(len(set(intents))==41,"capture_intent_id values not unique")
    require(len(set(versions))==41,"source_version_id values not unique")
    require(len(set(inbox))==41,"inbox filenames not unique")
    require(versions==[f"SV-SEMI-B026-{i:03d}" for i in range(1,42)],"source_version_id sequence drifted")
    require(intents==[f"CAP-SEMI-B026-{i:03d}" for i in range(1,42)],"capture_intent_id sequence drifted")

    for row in queue:
        require(row.get("historical_backdating_authorized") is False,f"{row.get('source_id')}: historical backdating unexpectedly authorized")
        require(row.get("reviewed_available_at_usage")=="REFERENCE_ONLY_NOT_RECEIPT_BACKDATING_AUTHORITY",f"{row.get('source_id')}: reviewed availability usage drifted")
        require(row.get("receipt_acquired_at_policy")=="ACTUAL_PRIVATE_CAPTURE_TIMESTAMP",f"{row.get('source_id')}: receipt acquired_at policy drifted")
        require(row.get("receipt_available_at_policy")=="EQUAL_ACTUAL_PRIVATE_CAPTURE_TIMESTAMP_UNLESS_EXPLICIT_EXACT_VERSION_AVAILABILITY_PROOF",f"{row.get('source_id')}: receipt available_at policy drifted")
        require(row.get("processing_disposition")=="ELIGIBLE",f"{row.get('source_id')}: disposition drifted")
        require(isinstance(row.get("source_locator"),str) and row["source_locator"].startswith("https://"),f"{row.get('source_id')}: source locator invalid")
        require(row.get("content_type_hint") in {"application/pdf","text/html"},f"{row.get('source_id')}: content type hint invalid")

    temporal=queue_doc.get("temporal_policy",{})
    require(temporal.get("public_review_available_at_is_reference_only") is True,"queue temporal reference firewall missing")
    require(temporal.get("historical_backdating_authorized") is False,"queue temporal backdating flag drifted")
    require(temporal.get("default_receipt_available_at")=="ACTUAL_PRIVATE_CAPTURE_TIMESTAMP","queue default receipt available_at drifted")

    require(contract.get("source_count")==41,"contract source count drifted")
    require(contract.get("release_id")=="REL-SEMI-B026-V001","contract release id drifted")
    require(contract.get("owner_namespace")=="PIPELINE_T1_SOURCE_ACQUISITION","contract owner drifted")
    require("NO_COPYING_PUBLIC_REVIEW_AVAILABLE_AT_INTO_RECEIPT" in contract.get("materialization_rules",[]),"contract no-backdating rule missing")
    require("ALL_RELEASE_MEMBERS_MUST_BE_ORDINARY_T2_ELIGIBLE" in contract.get("materialization_rules",[]),"contract ordinary T2 eligibility rule missing")

    results=status.get("results",{})
    expected={
      "PRIVATE_CAPTURE_EXECUTION_PACKET_READY":"YES",
      "UNIQUE_SOURCE_CAPTURE_INTENTS":41,
      "SOURCE_VERSION_IDS_RESERVED":41,
      "LOCAL_MATERIALIZER_READY":"YES",
      "LOCAL_VERIFIER_READY":"YES",
      "NETWORK_ACQUISITION_PERFORMED_BY_PACKET":"NO",
      "RAW_SOURCE_VERSIONS_MATERIALIZED":0,
      "VALID_T1_RECEIPTS":0,
      "T1_RELEASE_MANIFEST_PRESENT":"NO",
      "ORDINARY_T2_ELIGIBLE_SOURCES":0,
      "REQUIRED_CASES_COVERED":13,
      "REQUIRED_CASES_TOTAL":14,
      "REMAINING_REQUIRED_CASES":[12],
      "FIRST_SEMICONDUCTOR_RUN":"BLOCKED",
    }
    for k,v in expected.items():
        require(results.get(k)==v,f"Batch026 status metric drifted: {k}")
    require(status.get("next_required_action")=="EXECUTE_BATCH026_PRIVATE_CAPTURE_QUEUE_ON_WORKSTATION","Batch026 next required action drifted")
    require(status.get("repo_executable_modeling_lane")=="NONE","Batch026 falsely creates another repo modeling lane")

    rd=master.get("readiness",{})
    require(rd.get("SECOND_SLICE_PUBLIC_REPO_ACCEPTANCE_BLOCKERS",{}).get("status")=="NONE","master repo blockers unexpectedly remain")
    require(rd.get("SECOND_SLICE_PRIVATE_CAPTURE_PACKET",{}).get("status")=="READY","master private packet not ready")
    require(rd.get("SECOND_SLICE_PRIVATE_CAPTURE_PACKET",{}).get("source_count")==41,"master packet source count drifted")
    require(rd.get("SECOND_SLICE_RAW_SOURCE_VERSIONS",{}).get("status")=="NO","master falsely claims raw materialization")
    require(rd.get("SECOND_SLICE_T1_RELEASE",{}).get("status")=="NO","master falsely claims T1 release")
    require(rd.get("SECOND_SLICE_ORDINARY_T2_ELIGIBILITY",{}).get("status")=="NO","master falsely claims ordinary T2 eligibility")
    require(rd.get("SECOND_SLICE_REPLAY_READY",{}).get("status")=="NO","master falsely claims replay ready")
    require(rd.get("SECOND_SLICE_IMPLEMENTATION_ADMITTED",{}).get("status")=="NO","master falsely admits implementation")
    require(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")
    require(master.get("next_required_action")=="EXECUTE_BATCH026_PRIVATE_CAPTURE_QUEUE_ON_WORKSTATION","master next action drifted")
    require(master.get("next_repo_executable_lane")=="NONE","master falsely exposes repo lane")
    require(master.get("first_serious_constraint_run")=="BLOCKED","master falsely serious-run ready")

    require(successor.get("record_id")=="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_QUARANTINE_NON_MICRON_REPLACEMENT_STATUS_V001","current successor status identity drifted")
    require(successor.get("result")=="PASS_MICRON_QUARANTINE_AND_NON_MICRON_REPLACEMENT_READY_CAPTURE_NOT_EXECUTED","current successor must remain capture-not-executed")
    successor_results=successor.get("results",{})
    require(successor_results.get("ACTIVE_CAPTURE_SOURCE_COUNT")==38,"current successor active source count drifted")
    require(successor_results.get("MICRON_ACTIVE_CAPTURE_COUNT")==0,"current successor reintroduced quarantined Micron sources")
    require(successor_results.get("RAW_SOURCE_VERSIONS_MATERIALIZED")==0,"current successor falsely claims raw capture")
    require(successor.get("next_required_action")=="RUN_BATCH030_MICRON_FREE_BROWSER_CAPTURE","current successor next action drifted")
    require(successor.get("repo_executable_modeling_lane")=="NONE","current successor falsely exposes repo lane")

    print("CONSTRAINT_SECOND_SLICE_BATCH026_PRIVATE_T1_PACKET_VALIDATION=PASS")
    print("BATCH026_PACKET_STATUS=HISTORICAL")
    print("BATCH026_OPERATIONAL_STATUS=SUPERSEDED_BY_BATCH030_QUARANTINE")
    print("CURRENT_SUCCESSOR_BATCH=030")
    print("CURRENT_SUCCESSOR_CAPTURE=NOT_EXECUTED")
    print("UNIQUE_SOURCE_CAPTURE_INTENTS=41")
    print("SOURCE_VERSION_IDS_RESERVED=41")
    print("QUEUE_MATCHES_BATCHES_018_025=YES")
    print("HISTORICAL_BACKDATING_AUTHORIZED=NO")
    print("RAW_SOURCE_VERSIONS_MATERIALIZED=0")
    print("ORDINARY_T2_ELIGIBLE_SOURCES=0")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    print("HISTORICAL_NEXT_REQUIRED_ACTION_AS_OF_2026-09-26=EXECUTE_BATCH026_PRIVATE_CAPTURE_QUEUE_ON_WORKSTATION")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH026_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
