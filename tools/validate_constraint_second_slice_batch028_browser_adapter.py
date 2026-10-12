#!/usr/bin/env python3
"""Validate Batch028 semiconductor browser acquisition adapter contract."""

from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT",Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
CONTRACT=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH028_SEMICONDUCTOR_BROWSER_ACQUISITION_ADAPTER_CONTRACT_V001_20260927.json"
STATUS=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH028_SEMICONDUCTOR_BROWSER_ACQUISITION_ADAPTER_STATUS_V001_20260927.json"
MASTER=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH028_MASTER_STATUS_V001_20260927.json"
QUEUE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
RUNNER=ROOT/"tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py"
LAUNCHER=ROOT/"tools/private/Invoke-HYDRAConstraintSemiconductorBatch026BrowserCapture_V001_20260927.ps1"
REQUIREMENTS=ROOT/"tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_REQUIREMENTS_V001_20260927.txt"
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
    c=load(CONTRACT); s=load(STATUS); m=load(MASTER); q=load(QUEUE)
    require(c.get("slice_id")==SLICE,"contract slice_id drifted")
    require(s.get("slice_id")==SLICE,"status slice_id drifted")
    require(c.get("expected_source_count")==41,"contract source count drifted")
    require(q.get("source_count")==41 and len(q.get("queue",[]))==41,"Batch026 queue count drifted")
    require(c.get("queue_record_id")==q.get("record_id"),"contract queue binding drifted")

    for p in (RUNNER,LAUNCHER,REQUIREMENTS):
        require(p.is_file(),f"adapter dependency missing: {p.relative_to(ROOT)}")

    auth=c.get("authorization",{})
    require(auth.get("explicit_flag_required") is True,"explicit acquisition authorization no longer required")
    require(auth.get("network_acquisition_performed_by_runner") is True,"runner network-acquisition role drifted")
    require(auth.get("t1_persistence_performed_by_runner") is False,"runner improperly owns T1 persistence")
    rp=c.get("redirect_policy",{})
    require(rp.get("default")=="exact","default redirect policy drifted")
    require(rp.get("optional")=="same-origin","optional redirect policy drifted")
    require(rp.get("cross_origin_allowed") is False,"cross-origin redirects unexpectedly allowed")
    require(rp.get("downgrade_to_http_allowed") is False,"HTTP downgrade unexpectedly allowed")

    runner=RUNNER.read_text(encoding="utf-8")
    for token in (
      'EXPECTED_SOURCE_COUNT = 41',
      'EXPECTED_SLICE_ID = "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"',
      '"--authorized-public-acquisition"',
      'choices=("exact", "same-origin")',
      'default="exact"',
      'SIDECAR_SCHEMA = "hydra-semiconductor-private-capture-sidecar/v1"',
      '"historical_backdating_authorized": False',
      '"processing_disposition": "ELIGIBLE"',
      'RESUMED_EXISTING_VALID_PAIR',
      'JOURNAL_SCHEMA = "hydra-constraint-semiconductor-batch026-browser-capture-journal/v1"',
    ):
        require(token in runner,f"runner contract token missing: {token}")
    require("RawArtifactStore" not in runner,"browser runner imports T1 raw store")
    require("write_release_manifest" not in runner,"browser runner writes T1 release")
    require("is_ordinary_t2_eligible" not in runner,"browser runner performs ordinary-T2 admission")
    require("requests." not in runner and "urllib.request" not in runner,"browser runner added parallel HTTP acquisition")
    require('"historical_backdating_authorized": True' not in runner,"browser runner enables historical backdating")

    launcher=LAUNCHER.read_text(encoding="utf-8")
    for token in (
      '[switch]$AuthorizedPublicAcquisition',
      '[ValidateSet("exact", "same-origin")]',
      '[string]$RedirectPolicy = "exact"',
      'D:\\HYDRA_PRIVATE\\constraint',
      'D:\\HYDRA_PRIVATE\\constraint\\capture_inbox\\semiconductor_batch026',
      'playwright-venv',
      '--authorized-public-acquisition',
      '--redirect-policy',
    ):
        require(token in launcher,f"launcher contract token missing: {token}")
    require(" -m playwright install" not in launcher.lower() and "playwright install chromium" not in launcher.lower() and "playwright install chrome" not in launcher.lower(),"launcher unexpectedly installs a bundled browser")
    require("git switch" not in launcher.lower() and "git pull" not in launcher.lower(),"launcher unexpectedly mutates git branch state")

    requirements=REQUIREMENTS.read_text(encoding="utf-8").strip()
    require(requirements=="playwright>=1.55,<2","Playwright requirement drifted")

    results=s.get("results",{})
    expected={
      "BROWSER_ACQUISITION_ADAPTER_READY":"YES","EXPECTED_SOURCE_COUNT":41,
      "EXPLICIT_ACQUISITION_AUTHORIZATION_REQUIRED":"YES","DEFAULT_REDIRECT_POLICY":"exact",
      "OPTIONAL_SAME_ORIGIN_REDIRECT_POLICY":"YES","CROSS_ORIGIN_REDIRECT_ALLOWED":"NO",
      "RESUME_EXISTING_VALID_PAIRS":"YES","NONAUTHORITATIVE_PRIVATE_JOURNAL":"YES",
      "T1_PERSISTENCE_PERFORMED_BY_ADAPTER":"NO","RAW_SOURCE_VERSIONS_MATERIALIZED":0,
      "VALID_T1_RECEIPTS":0,"ORDINARY_T2_ELIGIBLE_SOURCES":0,"FIRST_SEMICONDUCTOR_RUN":"BLOCKED"
    }
    for k,v in expected.items():
        require(results.get(k)==v,f"Batch028 status metric drifted: {k}")
    require(s.get("next_required_action")=="RUN_BATCH028_BROWSER_CAPTURE_IN_CLEAN_WORKTREE","Batch028 next action drifted")
    require(s.get("after_capture_action")=="RUN_BATCH027_STATUS_THEN_ALL","Batch028 after-capture action drifted")

    rd=m.get("readiness",{})
    require(rd.get("SECOND_SLICE_BROWSER_ACQUISITION_ADAPTER",{}).get("status")=="READY","master adapter not ready")
    require(rd.get("SECOND_SLICE_BROWSER_ACQUISITION_ADAPTER",{}).get("source_count")==41,"master adapter source count drifted")
    require(rd.get("SECOND_SLICE_RAW_SOURCE_VERSIONS",{}).get("status")=="NO","master falsely claims raw materialization")
    require(rd.get("SECOND_SLICE_T1_RELEASE",{}).get("status")=="NO","master falsely claims T1 release")
    require(rd.get("SECOND_SLICE_ORDINARY_T2_ELIGIBILITY",{}).get("status")=="NO","master falsely claims ordinary T2 eligibility")
    require(rd.get("SECOND_SLICE_REPLAY_READY",{}).get("status")=="NO","master falsely claims replay ready")
    require(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")
    require(m.get("next_required_action")=="RUN_BATCH028_BROWSER_CAPTURE_IN_CLEAN_WORKTREE","master next action drifted")
    require(m.get("next_repo_executable_lane")=="NONE","master falsely exposes repo modeling lane")

    print("CONSTRAINT_SECOND_SLICE_BATCH028_BROWSER_ADAPTER_VALIDATION=PASS")
    print("BROWSER_ACQUISITION_ADAPTER_READY=YES")
    print("EXPECTED_SOURCE_COUNT=41")
    print("EXPLICIT_ACQUISITION_AUTHORIZATION_REQUIRED=YES")
    print("DEFAULT_REDIRECT_POLICY=exact")
    print("T1_PERSISTENCE_PERFORMED_BY_ADAPTER=NO")
    print("RAW_SOURCE_VERSIONS_MATERIALIZED=0")
    print("NEXT_REQUIRED_ACTION=RUN_BATCH028_BROWSER_CAPTURE_IN_CLEAN_WORKTREE")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH028_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
