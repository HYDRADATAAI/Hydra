#!/usr/bin/env python3
"""Validate Batch027 workstation launcher contract without touching private data."""

from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT",Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
CONTRACT=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH027_SEMICONDUCTOR_WORKSTATION_EXECUTION_LAUNCHER_CONTRACT_V001_20260926.json"
STATUS=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH027_SEMICONDUCTOR_WORKSTATION_EXECUTION_LAUNCHER_STATUS_V001_20260926.json"
MASTER=ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH027_MASTER_STATUS_V001_20260926.json"
QUEUE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
LAUNCHER=ROOT/"tools/Invoke-HydraConstraintSemiconductorBatch026PrivateT1.ps1"
PRIVATE_CAPTURE_LAUNCHER=ROOT/"tools/private/Invoke-HYDRAConstraintSemiconductorBatch026BrowserCapture_V001_20260927.ps1"
QUARANTINE_POLICY=ROOT/"tools/constraint_source_quarantine.py"
QUARANTINE_MANIFEST=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001_20260927.json"
HANDBACK=ROOT/"tools/build_constraint_second_slice_batch026_private_t1_handback.py"
MATERIALIZER=ROOT/"tools/materialize_constraint_second_slice_batch026_private_t1.py"
VERIFIER=ROOT/"tools/verify_constraint_second_slice_batch026_private_t1.py"
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
    require(c.get("launcher")=="tools/Invoke-HydraConstraintSemiconductorBatch026PrivateT1.ps1","launcher path drifted")
    require(c.get("handback_builder")=="tools/build_constraint_second_slice_batch026_private_t1_handback.py","handback builder path drifted")
    require(q.get("source_count")==41 and len(q.get("queue",[]))==41,"Batch026 queue count drifted")
    require(c.get("expected_handback_filename")=="HYDRA_CONSTRAINT_SEMI_B026_PRIVATE_T1_HANDBACK_V001.json","handback filename drifted")

    for p in (LAUNCHER,PRIVATE_CAPTURE_LAUNCHER,QUARANTINE_POLICY,QUARANTINE_MANIFEST,HANDBACK,MATERIALIZER,VERIFIER):
        require(p.is_file(),f"launcher dependency missing: {p.relative_to(ROOT)}")

    mode_names=[row.get("mode") for row in c.get("modes",[])]
    require(mode_names==["ContractCheck","Prep","Status","Materialize","Verify","All"],"launcher mode set/order drifted")
    guarantees=set(c.get("guarantees",[]))
    required_guarantees={
      "NO_NETWORK_ACQUISITION","NO_PUBLIC_RAW_SOURCE_BYTES","NO_CAPTURE_TIMESTAMP_INFERENCE_FROM_FILE_MTIME",
      "NO_COPYING_PUBLIC_REVIEW_AVAILABLE_AT_INTO_T1_RECEIPTS","NO_RELEASE_CREATION_UNLESS_ALL_41_RECEIPTS_VALIDATE",
      "NO_HANDBACK_EMISSION_UNLESS_ALL_41_SOURCES_ARE_ORDINARY_T2_ELIGIBLE"
    }
    require(required_guarantees<=guarantees,"launcher guarantees incomplete")

    text=LAUNCHER.read_text(encoding="utf-8")
    for token in (
      'ValidateSet("ContractCheck","Prep","Status","Materialize","Verify","All")',
      'BATCH027_WORKSTATION_LAUNCHER_CONTRACT_CHECK=PASS',
      'HYDRA_CONSTRAINT_SEMI_B026_CAPTURE_CHECKLIST_V001.csv',
      'HYDRA_CONSTRAINT_SEMI_B026_PRIVATE_T1_HANDBACK_V001.json',
      '--dry-run',
      'Join-Path $PSScriptRoot ".."',
      'D:\\HYDRA\\_PRIVATE\\constraint\\raw',
      'historical_backdating_authorized = $false',
      'BATCH026_OPERATIONAL_MODES=CLOSED',
      'SUPERSEDED_BY_BATCH030_QUARANTINE',
      'if ($Mode -ne "ContractCheck")',
    ):
        require(token in text,f"launcher token missing: {token}")
    mode_gate=text.index('if ($Mode -ne "ContractCheck")')
    mode_fail_token='Fail ("SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 " + $Mode'
    require(mode_fail_token in text[mode_gate:],"Batch026 operational mode gate must fail with the supersession error")
    mode_fail=text.index(mode_fail_token,mode_gate)
    first_operational_mode=text.index('if ($Mode -eq "Prep")')
    require(mode_gate < mode_fail < first_operational_mode,"Batch026 operational modes must fail before Prep or other private side effects")
    require("function Fail([string]$Message)" in text and "exit 1" in text[text.index("function Fail([string]$Message)"):text.index("function Require-Path")],"launcher failure handler must terminate with a nonzero exit")
    expected_quarantine_ids={
      "SRC-SEMI-MICRON-Q2FY25-REMARKS-2025-03-20",
      "SRC-SEMI-B021-MICRON-Q1FY26-REMARKS-2025-12-17",
      "SRC-SEMI-B021-MICRON-Q3FY24-REMARKS-2024-06-26",
      "SRC-SEMI-B021-MICRON-Q3FY25-REMARKS-2025-06-25",
      "SRC-SEMI-B021-MICRON-Q4FY25-REMARKS-2025-09-23",
      "SRC-SEMI-B022-GLOBENEWSWIRE-MICRON-HBM3E-2024-02-26",
      "SRC-SEMI-B022-MICRON-HBM3E-VOLUME-2024-02-26",
      "SRC-SEMI-B023-MICRON-Q1FY24-REMARKS-2023-12-20",
      "SRC-SEMI-B023-MICRON-Q2FY26-MARKET-OUTLOOK-2026-03-18",
    }
    quarantine=load(QUARANTINE_MANIFEST)
    ids=quarantine.get("quarantined")
    require(isinstance(ids,list) and len(ids)==9 and set(ids)==expected_quarantine_ids,"Batch030 quarantine source-ID set drifted")
    policy_text=QUARANTINE_POLICY.read_text(encoding="utf-8")
    for source_id in expected_quarantine_ids:
        require(source_id in policy_text,f"source quarantine policy missing ID: {source_id}")
    retired_tools=(
      ROOT/"tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py",
      MATERIALIZER,VERIFIER,HANDBACK,
    )
    for path in retired_tools:
        require("reject_retired_batch026" in path.read_text(encoding="utf-8"),f"Batch026 retirement guard missing: {path.relative_to(ROOT)}")
    private_launcher_text=PRIVATE_CAPTURE_LAUNCHER.read_text(encoding="utf-8")
    require("SUPERSEDED_BY_BATCH030_QUARANTINE" in private_launcher_text,"private capture launcher must close superseded Batch026 capture")
    private_failure_marker='Write-Host "ERROR=SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 browser capture is closed."'
    require(private_failure_marker in private_launcher_text,"private capture launcher must report the retirement failure")
    private_runtime_create=private_launcher_text.index("New-Item -ItemType Directory -Path $RuntimeRoot -Force")
    require(
      private_launcher_text.index(private_failure_marker) < private_launcher_text.find("exit 1",private_launcher_text.index(private_failure_marker),private_runtime_create) < private_runtime_create,
      "private capture launcher must exit before creating its private runtime",
    )
    require('[string]$RepoRoot,' in text, "launcher must not hard-code a workstation repo root")
    require("HYDRA_GITHUB" not in text and "HYDRA_PRIVATE" not in text, "stale operational root restored")
    require("Invoke-WebRequest" not in text and "curl " not in text and "wget " not in text,"launcher unexpectedly performs network acquisition")
    require("LastWriteTime" not in text and "mtime" not in text.lower(),"launcher infers capture timestamp from file metadata")

    htext=HANDBACK.read_text(encoding="utf-8")
    require('SCHEMA = "hydra-constraint-second-slice-private-t1-handback/v1"' in htext,"handback schema drifted")
    require("ordinary_t2_eligible_source_count" in htext,"handback ordinary T2 count missing")
    require("historical_backdating_used" in htext,"handback historical backdating flag missing")
    require("INGEST_BATCH026_PRIVATE_T1_HANDBACK_INTO_SEMICONDUCTOR_ORDINARY_REPLAY_LANE" in htext,"handback next action missing")

    results=s.get("results",{})
    expected={
      "WORKSTATION_LAUNCHER_READY":"YES","CONTRACT_CHECK_MODE_READY":"YES","PREP_MODE_READY":"YES",
      "STATUS_MODE_READY":"YES","MATERIALIZE_MODE_READY":"YES","VERIFY_MODE_READY":"YES","ALL_MODE_READY":"YES",
      "PRIVATE_HANDBACK_BUILDER_READY":"YES","NETWORK_ACQUISITION_ADDED":"NO","EXPECTED_PRIVATE_SOURCE_COUNT":41,
      "RAW_SOURCE_VERSIONS_MATERIALIZED":0,"VALID_T1_RECEIPTS":0,"ORDINARY_T2_ELIGIBLE_SOURCES":0,
      "T1_RELEASE_MANIFEST_PRESENT":"NO","FIRST_SEMICONDUCTOR_RUN":"BLOCKED"
    }
    for k,v in expected.items():
        require(results.get(k)==v,f"Batch027 status metric drifted: {k}")
    require(s.get("next_required_action")=="RUN_BATCH027_WORKSTATION_PREP_THEN_CAPTURE_THEN_ALL","Batch027 historical next action drifted")
    require(s.get("repo_executable_modeling_lane")=="NONE","Batch027 falsely exposes repo modeling lane")

    rd=m.get("readiness",{})
    require(rd.get("SECOND_SLICE_WORKSTATION_LAUNCHER",{}).get("status")=="READY","master launcher not ready")
    require(rd.get("SECOND_SLICE_PRIVATE_HANDBACK_BUILDER",{}).get("status")=="READY","master handback builder not ready")
    require(rd.get("SECOND_SLICE_RAW_SOURCE_VERSIONS",{}).get("status")=="NO","master falsely claims raw materialization")
    require(rd.get("SECOND_SLICE_T1_RELEASE",{}).get("status")=="NO","master falsely claims T1 release")
    require(rd.get("SECOND_SLICE_ORDINARY_T2_ELIGIBILITY",{}).get("status")=="NO","master falsely claims ordinary T2 eligibility")
    require(rd.get("SECOND_SLICE_REPLAY_READY",{}).get("status")=="NO","master falsely claims replay ready")
    require(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")
    require(m.get("next_required_action")=="RUN_BATCH027_WORKSTATION_PREP_THEN_CAPTURE_THEN_ALL","Batch027 historical master action drifted")
    require(m.get("next_repo_executable_lane")=="NONE","master falsely exposes repo lane")

    print("CONSTRAINT_SECOND_SLICE_BATCH027_WORKSTATION_LAUNCHER_VALIDATION=PASS")
    print("WORKSTATION_LAUNCHER_CONTRACT=VALIDATED")
    print("BATCH026_OPERATIONAL_MODES=CLOSED")
    print("HISTORICAL_BATCH027_ACTION_RETIRED=RUN_BATCH027_WORKSTATION_PREP_THEN_CAPTURE_THEN_ALL")
    print("PRIVATE_HANDBACK_BUILDER_PRESENT=YES")
    print("EXPECTED_PRIVATE_SOURCE_COUNT=41")
    print("RAW_SOURCE_VERSIONS_MATERIALIZED=0")
    print("ORDINARY_T2_ELIGIBLE_SOURCES=0")
    print("OPERATIONAL_NEXT_ACTION=SUPERSEDED_BY_BATCH030_QUARANTINE")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH027_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
