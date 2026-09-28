#!/usr/bin/env python3
"""Validate Batch032 sanitized semiconductor T1 materialization attestation."""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
VAL=ROOT/"docs/constraint/validation"
ARCH=ROOT/"docs/constraint/architecture"

QUEUE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json"
QUAR=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_TSMC_DIRECT_PROVIDER_QUARANTINE_V001_20260928.json"
ATTEST=VAL/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH032_SEMICONDUCTOR_T1_MATERIALIZATION_ATTESTATION_V001_20260928.json"
STATUS=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH032_SEMICONDUCTOR_POST_CAPTURE_PUBLIC_STATUS_V001_20260928.json"
SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
REL="REL-SEMI-B031-V001"
REL_SHA="c735db9e8a5daed8cff08dc7d9c2b4cc11f5910aba61669536c3961b21ac8b77"
FILE_SHA="d7a4f2f625b3a9bdd19e24204a259b68c20dea0d40e0418859d14ddea6553f8b"
HEX64=re.compile(r"^[0-9a-f]{64}$")
PRIVATE_PATTERNS=("D:\\HYDRA_PRIVATE","D:\\HYDRA\\_PRIVATE","\\capture_inbox\\","\\receipts\\","\\objects\\sha256\\")

class ValidationError(RuntimeError): pass
def req(c,m):
    if not c: raise ValidationError(m)
def load(p):
    v=json.loads(p.read_text(encoding="utf-8"))
    req(isinstance(v,dict),f"object required: {p}")
    return v

def validate_documents(queue,quar,att,status):
    req(queue.get("slice_id")==SLICE,"queue slice drift")
    rows=queue.get("queue")
    req(isinstance(rows,list) and len(rows)==30,"queue must contain exactly 30")
    qby={r["source_id"]:r for r in rows}
    req(len(qby)==30,"queue source ids duplicated")
    req(queue.get("release_id")==REL,"queue release id drift")
    req(queue.get("provider_exclusion_policy")=="MICRON_AND_DIRECT_TSMC_PROVIDER_CAPTURE_EXCLUDED_FROM_ACTIVE_CAPTURE","queue provider policy drift")

    req(att.get("schema_version")=="hydra-constraint-second-slice-public-t1-materialization-attestation/v1","attestation schema drift")
    req(att.get("slice_id")==SLICE,"attestation slice drift")
    req(att.get("queue_record_id")==queue.get("record_id"),"attestation queue binding drift")
    req(att.get("release_id")==REL,"attestation release id drift")
    req(att.get("release_sha256")==REL_SHA,"attestation release sha drift")
    req(att.get("release_record_file_sha256")==FILE_SHA,"attestation release file sha drift")
    req(att.get("materialized_source_count")==30,"materialized count drift")
    req(att.get("valid_receipt_count")==30,"valid receipt count drift")
    req(att.get("ordinary_t2_eligible_count")==30,"ordinary T2 count drift")
    req(att.get("all_sources_ordinary_t2_eligible") is True,"all-source T2 flag drift")
    req(att.get("availability_mode")=="ACQUISITION_TIME_CONSERVATIVE","availability mode drift")
    req(att.get("historical_availability_backdated") is False,"historical backdating promoted")
    req(att.get("strict_historical_replay_promoted") is False,"strict replay promoted")
    req(att.get("public_raw_content_published") is False,"raw content publication promoted")
    req(att.get("private_paths_published") is False,"private paths publication promoted")
    req(att.get("provider_exclusion_policy")==queue.get("provider_exclusion_policy"),"provider policy mismatch")
    req(att.get("remaining_replay_boundary")=="PRE_ACQUISITION_HISTORICAL_VERSION_AVAILABILITY_NOT_ESTABLISHED","replay boundary drift")
    req(att.get("next_action")=="INGEST_BATCH031_T1_RELEASE_INTO_SEMICONDUCTOR_ORDINARY_T2_NORMALIZATION","next action drift")

    members=att.get("members")
    req(isinstance(members,list) and len(members)==30,"attestation members must be 30")
    aby={m.get("source_id"):m for m in members}
    req(len(aby)==30 and set(aby)==set(qby),"attestation member set != Batch031 queue")

    allowed={"source_id","source_version_id","artifact_sha256","receipt_sha256","source_locator","acquired_at","available_at","content_type","byte_length","ordinary_t2_eligible"}
    for sid,m in aby.items():
        q=qby[sid]
        req(set(m)==allowed,f"{sid}: member fields drift")
        req(m["source_version_id"]==q["source_version_id"],f"{sid}: version drift")
        req(m["source_locator"]==q["source_locator"],f"{sid}: locator drift")
        req(m["acquired_at"]==m["available_at"],f"{sid}: historical backdating")
        req(m["ordinary_t2_eligible"] is True,f"{sid}: ordinary T2 false")
        req(isinstance(m["byte_length"],int) and m["byte_length"]>0,f"{sid}: byte length invalid")
        req(isinstance(m["artifact_sha256"],str) and HEX64.fullmatch(m["artifact_sha256"]) is not None,f"{sid}: artifact hash invalid")
        req(isinstance(m["receipt_sha256"],str) and HEX64.fullmatch(m["receipt_sha256"]) is not None,f"{sid}: receipt hash invalid")
        if q["content_type_hint"]=="application/pdf":
            req(m["content_type"]=="application/pdf",f"{sid}: expected PDF")
        else:
            req(m["content_type"] in {"text/html","multipart/related","application/x-mimearchive"},f"{sid}: expected HTML-like content")

    serialized=json.dumps(att)
    for token in PRIVATE_PATTERNS:
        req(token.lower() not in serialized.lower(),f"private filesystem token leaked: {token}")
    req("raw_bytes" not in serialized and '"body"' not in serialized,"raw content field leaked")

    qids={r["source_id"] for r in quar.get("quarantined_sources",[])}
    req(len(qids)==8,"quarantine count drift")
    req(not (qids & set(aby)),"direct TSMC quarantine member entered attestation")

    req(status.get("schema_version")=="hydra-constraint-second-slice-post-capture-public-status/v1","status schema drift")
    req(status.get("slice_id")==SLICE,"status slice drift")
    req(status.get("source_attestation_record_id")==att.get("record_id"),"status attestation binding drift")
    req(status.get("release_id")==REL and status.get("release_sha256")==REL_SHA,"status release drift")
    req(status.get("source_count")==30 and status.get("materialized_source_count")==30 and status.get("valid_receipt_count")==30 and status.get("ordinary_t2_eligible_count")==30,"status counts drift")
    req(status.get("current_release_ordinary_t2_ready") is True,"status T2 readiness drift")
    req(status.get("strict_historical_replay_promoted") is False,"status replay promoted")
    req(status.get("canonical_admission_promoted") is False,"status canonical admission promoted")
    req(status.get("public_raw_content_published") is False and status.get("private_paths_published") is False,"status publication boundary drift")
    req(status.get("closure",{}).get("PERSISTED_T1_T2_CURRENT_CUSTODY")=="COMPLETE","status custody not closed")
    req(status.get("remaining_blockers",{}).get("PRE_ACQUISITION_HISTORICAL_VERSION_AVAILABILITY")=="UNPROVEN","status historical availability drift")
    req(status.get("remaining_blockers",{}).get("REQUIRED_CASE_12_HISTORICAL_NO_LOOKAHEAD")=="OPEN","status Case12 falsely closed")
    req(status.get("next_repo_executable_lane")=="SEMICONDUCTOR_ORDINARY_T2_NORMALIZATION_FROM_BATCH031_RELEASE","status next lane drift")
    return True

def main():
    try:
        validate_documents(load(QUEUE),load(QUAR),load(ATTEST),load(STATUS))
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValidationError) as exc:
        print("BATCH032_SEMICONDUCTOR_T1_ATTESTATION=FAIL")
        print(f"ERROR={exc}")
        return 1
    print("BATCH032_SEMICONDUCTOR_T1_ATTESTATION=PASS")
    print("MEMBERS=30")
    print("ORDINARY_T2_ELIGIBLE=30")
    print("CURRENT_CUSTODY=COMPLETE")
    print("STRICT_HISTORICAL_REPLAY=NO")
    print("CASE12=OPEN")
    print("NEXT=SEMICONDUCTOR_ORDINARY_T2_NORMALIZATION_FROM_BATCH031_RELEASE")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
