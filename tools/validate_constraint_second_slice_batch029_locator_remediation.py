#!/usr/bin/env python3
"""Validate Batch029 Micron capture-locator remediation."""

from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT",Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
OVERLAY=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH029_SEMICONDUCTOR_MICRON_CAPTURE_LOCATOR_REMEDIATION_V001_20260927.json"
STATUS=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH029_SEMICONDUCTOR_MICRON_CAPTURE_LOCATOR_REMEDIATION_STATUS_V001_20260927.json"
MASTER=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH029_MASTER_STATUS_V001_20260927.json"
QUEUE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
RUNNER=ROOT/"tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py"
MATERIALIZER=ROOT/"tools/materialize_constraint_second_slice_batch026_private_t1.py"
VERIFIER=ROOT/"tools/verify_constraint_second_slice_batch026_private_t1.py"
HANDBACK=ROOT/"tools/build_constraint_second_slice_batch026_private_t1_handback.py"
SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"

class ValidationFailure(Exception): pass
def require(c,m):
    if not c: raise ValidationFailure(m)
def load(p:Path)->dict[str,Any]:
    require(p.is_file(),f"required artifact missing: {p.relative_to(ROOT)}")
    v=json.loads(p.read_text(encoding="utf-8"))
    require(isinstance(v,dict),f"root must be object: {p.relative_to(ROOT)}")
    return v

def import_runner():
    spec=importlib.util.spec_from_file_location("hydra_batch029_runner",RUNNER)
    require(spec is not None and spec.loader is not None,"unable to import browser runner")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main()->int:
    overlay=load(OVERLAY); status=load(STATUS); master=load(MASTER); queue=load(QUEUE)
    require(overlay.get("slice_id")==SLICE,"overlay slice_id drifted")
    require(status.get("slice_id")==SLICE,"status slice_id drifted")
    rows=overlay.get("remediations",[])
    require(isinstance(rows,list) and len(rows)==7,"Micron remediation count drifted")
    require(overlay.get("source_identity_mutated") is False,"source identity mutation unexpectedly allowed")
    require(overlay.get("predecessor_registries_mutated") is False,"predecessor registry mutation unexpectedly allowed")
    require(overlay.get("batch026_queue_mutated") is False,"Batch026 queue mutation unexpectedly allowed")
    policy=overlay.get("resolution_policy",{})
    require(policy.get("allowed_resolved_host")=="s25.q4cdn.com","resolved host allowlist drifted")
    require(policy.get("required_account_path_prefix")=="/621799436/files/doc_financials/","Micron Q4 account path drifted")
    require(policy.get("https_required") is True,"HTTPS requirement lost")
    require(policy.get("record_actual_resolved_locator_in_capture_sidecar") is True,"actual capture locator not recorded")

    qrows=queue.get("queue",[])
    require(isinstance(qrows,list) and len(qrows)==41,"Batch026 queue count drifted")
    qby={x["source_id"]:x for x in qrows}
    static_ids={
        x["source_id"] for x in qrows
        if "investors.micron.com/static-files/" in x.get("source_locator","")
    }
    rem_ids={x.get("source_id") for x in rows}
    require(rem_ids==static_ids,f"remediation source set drifted: {sorted(rem_ids ^ static_ids)}")
    require(len(rem_ids)==7,"expected seven stale Micron static-file sources")

    for row in rows:
        sid=row["source_id"]
        require(row.get("original_source_locator")==qby[sid]["source_locator"],f"{sid}: original locator not preserved")
        require(row.get("ordinal")==qby[sid]["ordinal"],f"{sid}: queue ordinal drifted")
        require(row.get("document_kind") in {"prepared_remarks","presentation"},f"{sid}: document kind invalid")
        prefix=row.get("required_path_prefix")
        require(isinstance(prefix,str) and prefix.startswith("/621799436/files/doc_financials/"),f"{sid}: required quarter path invalid")
        require(f"/{row['fiscal_year']}/{row['fiscal_quarter']}/" in prefix,f"{sid}: fiscal quarter path mismatch")

    runner_text=RUNNER.read_text(encoding="utf-8")
    for token in (
        "LOCATOR_OVERLAY_RELATIVE_PATH",
        "def load_locator_remediations",
        "def validate_effective_locator",
        "def resolve_remediated_locator",
        "https://investors.micron.com/financials/quarterly-results/default.aspx",
        "LOCATOR_REMEDIATED",
        'capture_locator=capture_locator',
        '"source_locator": locator',
    ):
        require(token in runner_text,f"runner remediation token missing: {token}")
    require("search engine" not in runner_text.lower(),"runner unexpectedly relies on search engine")
    require("requests." not in runner_text,"runner added parallel requests acquisition")

    materializer_text=MATERIALIZER.read_text(encoding="utf-8")
    verifier_text=VERIFIER.read_text(encoding="utf-8")
    handback_text=HANDBACK.read_text(encoding="utf-8")
    for text,label in ((materializer_text,"materializer"),(verifier_text,"verifier")):
        require("LOCATOR_OVERLAY_REL" in text,f"{label} missing locator overlay")
        require("s25.q4cdn.com" in text,f"{label} missing Q4CDN allowlist")
        require("required_path_prefix" in text,f"{label} missing quarter-path constraint")
    require("source_locator=source_locator" in materializer_text,"materializer does not persist actual capture locator")
    require('"registered_source_locator": item["source_locator"]' in handback_text,"handback missing registered locator")
    require('"capture_source_locator": receipt["source_locator"]' in handback_text,"handback missing capture locator")

    mod=import_runner()
    sample=rows[0]
    item=qby[sample["source_id"]]
    valid=f"https://s25.q4cdn.com{sample['required_path_prefix']}Example-Prepared-Remarks.pdf"
    mod.validate_effective_locator(item=item,locator=valid,remediation=sample)
    try:
        mod.validate_effective_locator(
            item=item,
            locator="https://evil.example.com/2025/q2/Prepared-Remarks.pdf",
            remediation=sample,
        )
    except mod.CaptureError:
        pass
    else:
        raise ValidationFailure("runner accepted disallowed remediation host")

    results=status.get("results",{})
    expected={
      "STALE_MICRON_REGISTERED_LOCATORS_REMEDIATED":7,
      "ORIGINAL_SOURCE_IDENTITIES_PRESERVED":7,
      "ORIGINAL_BATCH026_QUEUE_MUTATED":"NO",
      "ORIGINAL_SOURCE_REGISTRIES_MUTATED":"NO",
      "RESOLVED_HOST_ALLOWLIST":["s25.q4cdn.com"],
      "RESOLVED_QUARTER_PATH_CONSTRAINTS":"ENFORCED",
      "ACTUAL_CAPTURE_LOCATOR_RECORDED_IN_SIDECAR":"YES",
      "REGISTERED_AND_CAPTURE_LOCATORS_BOTH_RECORDED_IN_HANDBACK":"YES",
      "RAW_SOURCE_VERSIONS_MATERIALIZED":0,
      "VALID_T1_RECEIPTS":0,
      "ORDINARY_T2_ELIGIBLE_SOURCES":0,
      "FIRST_SEMICONDUCTOR_RUN":"BLOCKED"
    }
    for k,v in expected.items():
        require(results.get(k)==v,f"Batch029 status metric drifted: {k}")
    require(status.get("next_required_action")=="RERUN_BATCH028_BROWSER_CAPTURE_WITH_BATCH029_LOCATOR_REMEDIATION","Batch029 next action drifted")

    rd=master.get("readiness",{})
    require(rd.get("SECOND_SLICE_CAPTURE_LOCATOR_REMEDIATION",{}).get("status")=="READY","master locator remediation not ready")
    require(rd.get("SECOND_SLICE_CAPTURE_LOCATOR_REMEDIATION",{}).get("remediated_source_count")==7,"master remediation count drifted")
    require(rd.get("SECOND_SLICE_RAW_SOURCE_VERSIONS",{}).get("status")=="NO","master falsely claims raw materialization")
    require(rd.get("SECOND_SLICE_T1_RELEASE",{}).get("status")=="NO","master falsely claims T1 release")
    require(rd.get("SECOND_SLICE_REPLAY_READY",{}).get("status")=="NO","master falsely claims replay ready")
    require(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")

    print("CONSTRAINT_SECOND_SLICE_BATCH029_LOCATOR_REMEDIATION_VALIDATION=PASS")
    print("MICRON_LOCATORS_REMEDIATED=7")
    print("ORIGINAL_SOURCE_IDENTITIES_PRESERVED=YES")
    print("RESOLVED_HOST_ALLOWLIST=s25.q4cdn.com")
    print("RESOLVED_QUARTER_PATH_CONSTRAINTS=ENFORCED")
    print("RAW_SOURCE_VERSIONS_MATERIALIZED=0")
    print("NEXT_REQUIRED_ACTION=RERUN_BATCH028_BROWSER_CAPTURE_WITH_BATCH029_LOCATOR_REMEDIATION")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH029_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
