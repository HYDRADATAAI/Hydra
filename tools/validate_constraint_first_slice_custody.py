#!/usr/bin/env python3
"""Validate Batch017 persisted T1->T2 custody hardening."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT",Path(__file__).resolve().parents[1])).resolve()
IMPL=ROOT/"docs/constraint/implementation"
VAL=ROOT/"docs/constraint/validation"
ARCH=ROOT/"docs/constraint/architecture"

CONTRACT=IMPL/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_T1_T2_PERSISTED_CHAIN_OF_CUSTODY_CONTRACT_V001_20260925.json"
STATUS=VAL/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_T1_T2_CHAIN_OF_CUSTODY_STATUS_V001_20260925.json"
MASTER17=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_MASTER_STATUS_V001_20260925.json"
MASTER16=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_MASTER_STATUS_V001_20260925.json"

class ValidationFailure(Exception): pass
def require(cond: bool,msg: str)->None:
    if not cond: raise ValidationFailure(msg)
def load(path:Path)->dict[str,Any]:
    require(path.is_file(),f"required artifact missing: {path.relative_to(ROOT)}")
    value=json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value,dict),f"root must be object: {path.relative_to(ROOT)}")
    return value

def main()->int:
    contract,status,master17,master16=map(load,(CONTRACT,STATUS,MASTER17,MASTER16))
    required=set(contract.get("ordinary_t2_eligibility_requires",[]))
    require(required=={
        "VALID_RAW_ARTIFACT_BYTES","MATCHING_ARTIFACT_SHA256","SOURCE_ID","SOURCE_VERSION_ID",
        "ACQUIRED_AT","AVAILABLE_AT","ELIGIBLE_PROCESSING_DISPOSITION",
        "EXACT_PERSISTED_SOURCE_VERSION_RECEIPT","EXACT_PERSISTED_RELEASE_MANIFEST","EXACT_RELEASE_MEMBERSHIP"
    },f"Batch017 custody requirement set drifted: {sorted(required)}")
    sem=contract.get("authority_semantics",{})
    require(sem.get("caller_supplied_in_memory_receipt_authoritative") is False,"Batch017 in-memory receipt authority unexpectedly enabled")
    require(sem.get("caller_supplied_in_memory_release_manifest_authoritative") is False,"Batch017 in-memory release authority unexpectedly enabled")
    require(sem.get("self_consistent_recomputed_digest_sufficient") is False,"Batch017 recomputed digest unexpectedly sufficient")
    require(sem.get("persisted_record_identity_required") is True,"Batch017 persisted identity requirement removed")
    boundary=contract.get("private_boundary",{})
    require(boundary.get("raw_source_bytes_allowed_in_public_repo") is False,"Batch017 raw bytes unexpectedly allowed in public repo")
    require(boundary.get("symlink_redirect_into_public_repo_allowed") is False,"Batch017 symlink redirect into public repo allowed")
    require(boundary.get("symlink_escape_outside_private_root_allowed") is False,"Batch017 private-root escape allowed")

    r=status.get("results",{})
    require(r.get("PERSISTED_RECEIPT_IDENTITY_REQUIRED")=="YES","Batch017 persisted receipt identity not required")
    require(r.get("PERSISTED_RELEASE_IDENTITY_REQUIRED")=="YES","Batch017 persisted release identity not required")
    require(r.get("FORGED_IN_MEMORY_RELEASE_AUTHORITY")=="NO","Batch017 forged release became authority")
    require(r.get("FORGED_RECEIPT_DISPOSITION_UPGRADE")=="BLOCKED","Batch017 forged disposition upgrade not blocked")
    require(r.get("REAL_OUTCOME_RECORDS")==5 and r.get("REAL_OUTCOME_LABELS")==4,"Batch017 lost Batch016 outcome coverage")
    require(r.get("CORE_REAL_OUTCOME_DIMENSIONS")=="3_OF_3","Batch017 lost core outcome dimensions")
    require(r.get("REPO_EXECUTABLE_ACCEPTANCE_BLOCKERS")==0,"Batch017 invented repo-executable blockers")
    require(r.get("FIRST_SLICE_REAL_RAW_ARTIFACTS_MATERIALIZED")=="NO","Batch017 falsely materialized raw artifacts")
    require(r.get("IMPLEMENTATION_ADMITTED")=="NO","Batch017 falsely admits implementation")
    require(r.get("FULL_CONSTRAINT_RUN_READY")=="NO","Batch017 falsely claims full-run readiness")
    require(r.get("FIRST_SERIOUS_CONSTRAINT_RUN")=="BLOCKED","Batch017 falsely claims serious-run readiness")

    r16=master16.get("readiness",{})
    r17=master17.get("readiness",{})
    require(r16.get("REAL_OUTCOME_CORE_DIMENSION_COVERAGE")==r17.get("REAL_OUTCOME_CORE_DIMENSION_COVERAGE"),"Batch017 changed Batch016 outcome coverage")
    require(master16.get("remaining_blockers")==master17.get("remaining_blockers"),"Batch017 blocker set drifted")
    require(master16.get("repo_executable_blockers")==[] and master17.get("repo_executable_blockers")==[],"Batch017 repo-executable blocker state drifted")
    expected="NONE_FIRST_SLICE_ACCEPTANCE_REQUIRES_PRIVATE_RAW_MATERIALIZATION_AND_NATIVE_ADMISSION"
    require(master17.get("next_repo_executable_lane")==expected,"Batch017 next lane drifted")
    require(r17.get("T1_T2_PERSISTED_CHAIN_OF_CUSTODY_READY",{}).get("status")=="YES","Batch017 master lost custody readiness")
    require(r17.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","Batch017 master falsely full-run ready")
    require(master17.get("first_serious_constraint_run")=="BLOCKED","Batch017 master falsely serious-run ready")

    print("CONSTRAINT_FIRST_SLICE_PERSISTED_CUSTODY_VALIDATION=PASS")
    print("PERSISTED_RECEIPT_IDENTITY_REQUIRED=YES")
    print("PERSISTED_RELEASE_IDENTITY_REQUIRED=YES")
    print("CALLER_SUPPLIED_IN_MEMORY_RELEASE_AUTHORITY=NO")
    print("REAL_OUTCOME_RECORDS=5")
    print("REPO_EXECUTABLE_ACCEPTANCE_BLOCKERS=0")
    print("FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED")
    print(f"NEXT_REPO_EXECUTABLE_LANE={expected}")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError) as exc:
        print("CONSTRAINT_FIRST_SLICE_PERSISTED_CUSTODY_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
