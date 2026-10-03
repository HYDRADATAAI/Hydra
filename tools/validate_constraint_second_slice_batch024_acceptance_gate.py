#!/usr/bin/env python3
"""Validate Batch024 strict acceptance gate for semiconductor second slice."""

from __future__ import annotations
import json, os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get("HYDRA_REPO_ROOT",Path(__file__).resolve().parents[1])).resolve()
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
ARCH=ROOT/"docs/constraint/architecture"
FIRST=ROOT/"docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
VALIDATION=ROOT/"docs/constraint/validation"

FILES={
"gate":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH024_SEMICONDUCTOR_STRICT_ACCEPTANCE_GATE_V001_20260926.json",
"blockers":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH024_SEMICONDUCTOR_ACCEPTANCE_BLOCKER_REGISTER_V001_20260926.json",
"master":ARCH/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH024_MASTER_STATUS_V001_20260926.json",
"b023cases":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json",
"b018graph":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_GRAPH_SEED_V001_20260926.json",
"b019graph":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_GRAPH_OVERLAY_V001_20260926.json",
"b021power":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_TO_POWER_INFRASTRUCTURE_GRAPH_OVERLAY_V001_20260926.json",
"b019outcome":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_HISTORICAL_OUTCOME_OVERLAY_V001_20260926.json",
"b020outcome":BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_TSMC_ARIZONA_RAMP_HISTORY_OUTCOME_OVERLAY_V001_20260926.json",
"admission":VALIDATION/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH002_NATIVE_T5_T6_ADMISSION_STATUS_V001_20260925.json",
}

SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
REPO_BLOCKER="SEMI-ACCEPT-024-XSLICE-001-CONTINUOUS-AI-SEMICONDUCTOR-POWER-CHAIN-NOT-PROVEN"
RAW_BLOCKER="SEMICONDUCTOR-SLICE-006-RAW-SOURCE-VERSIONS-NOT-MATERIALIZED"
ADMISSION_BLOCKER="CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT"

class ValidationFailure(Exception): pass
def require(c,m):
    if not c: raise ValidationFailure(m)
def load(p:Path)->dict[str,Any]:
    require(p.is_file(),f"required artifact missing: {p.relative_to(ROOT)}")
    v=json.loads(p.read_text(encoding="utf-8")); require(isinstance(v,dict),"root must be object"); return v

def path_exists(edges:list[dict[str,Any]],start:str,target:str)->bool:
    adj:dict[str,list[str]]=defaultdict(list)
    for e in edges:
        f=e.get("from"); t=e.get("to")
        if isinstance(f,str) and isinstance(t,str):
            adj[f].append(t)
    q=deque([start]); seen={start}
    while q:
        n=q.popleft()
        if n==target: return True
        for nxt in adj.get(n,[]):
            if nxt not in seen:
                seen.add(nxt); q.append(nxt)
    return False

def main()->int:
    d={k:load(v) for k,v in FILES.items()}
    gate=d["gate"]; require(gate.get("slice_id")==SLICE,"gate slice_id drifted")
    allowed=["PASS","PASS_WITH_NONBLOCKING_GAPS","BLOCKED"]
    require(gate.get("allowed_gate_states")==allowed,"gate-state vocabulary drifted")
    dims=gate.get("dimensions",{})

    expected_status={
      "AUTHORITY_CURRENT":"PASS",
      "SEMANTIC_REUSE":"PASS",
      "NO_PARALLEL_ARCHITECTURE":"PASS",
      "SOURCE_AUTHORITY":"PASS",
      "PROVENANCE":"BLOCKED",
      "ENTITY_RESOLUTION":"PASS_WITH_NONBLOCKING_GAPS",
      "CAPACITY_STATE_SEPARATION":"PASS",
      "YIELD_SEPARATION":"PASS",
      "QUALIFICATION_SEPARATION":"PASS",
      "MATERIAL_DEPENDENCY":"PASS",
      "GEOGRAPHY_LINKAGE":"PASS_WITH_NONBLOCKING_GAPS",
      "POLICY_EVENT_TIME":"PASS_WITH_NONBLOCKING_GAPS",
      "CONSTRAINT_FORMATION":"PASS_WITH_NONBLOCKING_GAPS",
      "CONSTRAINT_MIGRATION":"PASS_WITH_NONBLOCKING_GAPS",
      "INVALIDATOR_HANDLING":"PASS_WITH_NONBLOCKING_GAPS",
      "BENEFICIARY_QUALIFICATION":"PASS_WITH_NONBLOCKING_GAPS",
      "CROSS_SLICE_GRAPH":"BLOCKED",
      "ORIGINAL_AS_OF":"BLOCKED",
      "NO_LOOKAHEAD":"BLOCKED",
      "DETERMINISTIC_REPLAY":"BLOCKED",
      "OUTCOME_CAPTURE":"PASS_WITH_NONBLOCKING_GAPS",
      "LINEAGE":"BLOCKED",
      "IMPLEMENTATION_ADMITTED":"BLOCKED",
    }
    require(set(dims)==set(expected_status),"acceptance dimension set drifted")
    for k,v in expected_status.items():
        require(dims[k].get("status")==v,f"{k} status drifted")

    # Case state: all repo-executable functional cases are done, Case 12 external.
    c23=d["b023cases"]
    require(c23.get("covered_case_count_after")==13,"Batch023 required-case count drifted")
    require(c23.get("remaining_gap_case_ids")==[12],"Batch023 remaining case gap drifted")
    rstate=gate.get("required_case_state",{})
    require(rstate=={"covered":13,"total":14,"remaining_case_ids":[12],"repo_executable_required_case_gaps":0},"gate required-case state drifted")

    # Existing graph contains two cross-slice bridges but not one continuous directed path.
    edges=[]
    edges.extend(d["b018graph"].get("edges",[]))
    edges.extend(d["b019graph"].get("edges_added",[]))
    edges.extend(d["b021power"].get("edges_added",[]))
    require(d["b018graph"].get("cross_slice_edge_count")==1,"AI-to-semiconductor bridge count drifted")
    require(d["b021power"].get("cross_slice_edges_added")==3,"semiconductor-to-power bridge count drifted")
    require(d["b021power"].get("bounded_facility_power_dependency_proven") is True,"facility power dependency lost")
    require(d["b021power"].get("power_constraint_asserted") is False,"power dependency escalated into power constraint")
    require(path_exists(edges,"N-AI-COMPUTE-DEMAND","N-SEMI-AI-ACCELERATOR-DEMAND"),"AI-to-semiconductor bridge missing")
    require(path_exists(edges,"FAC-SEMI-TSMC-ARIZONA-FIRST-FAB","N-ELECTRICITY-DEMAND"),"semiconductor-to-power bridge missing")
    require(not path_exists(edges,"N-AI-COMPUTE-DEMAND","N-ELECTRICITY-DEMAND"),"continuous AI-semiconductor-power path unexpectedly already exists")

    x=dims["CROSS_SLICE_GRAPH"]
    require(REPO_BLOCKER in set(x.get("blockers",[])),"cross-slice repo blocker missing")

    # Outcome capture exists but is shadow/current-review only.
    require(d["b019outcome"].get("outcome_count")==1,"Batch019 outcome count drifted")
    o20=d["b020outcome"].get("outcome",{})
    require(o20.get("original_target_preserved") is True,"Batch020 outcome lost original target")
    require(o20.get("historical_replay_eligible") is False,"Batch020 outcome unexpectedly replay eligible")

    # Native admission remains fail-closed.
    adm=d["admission"]
    require(adm.get("implementation_admitted")=="NO","native implementation unexpectedly admitted")
    require(adm.get("signed_admission_receipt")=="ABSENT","signed admission receipt unexpectedly present")

    # Gate and blocker register must remain fail-closed.
    require(gate.get("overall_status")=="BLOCKED","overall acceptance gate falsely not blocked")
    require(gate.get("full_constraint_run_allowed") is False,"full constraint run unexpectedly allowed")
    require(gate.get("first_semiconductor_run")=="BLOCKED","first semiconductor run unexpectedly allowed")
    require(gate.get("next_repo_executable_lane")=="SECOND-SLICE-CONTINUOUS-CROSS-SLICE-GRAPH-CLOSURE","gate next lane drifted")

    b=d["blockers"]
    repo=b.get("repo_executable_blockers",[])
    require(len(repo)==1 and repo[0].get("blocker_id")==REPO_BLOCKER,"repo-executable blocker register drifted")
    ext=b.get("external_or_private_blockers",[])
    extids={x.get("blocker_id") for x in ext}
    require(RAW_BLOCKER in extids,"raw-lineage blocker missing")
    require(ADMISSION_BLOCKER in extids,"native-admission blocker missing")
    require(len(ext)==6,"external/private blocker count drifted")
    require(b.get("next_repo_executable_lane")=="SECOND-SLICE-CONTINUOUS-CROSS-SLICE-GRAPH-CLOSURE","blocker-register next lane drifted")

    m=d["master"]; rd=m.get("readiness",{})
    require(rd.get("SECOND_SLICE_CROSS_SLICE_GRAPH_ACCEPTANCE",{}).get("status")=="NO_CONTINUOUS_CHAIN","master cross-slice acceptance status drifted")
    require(rd.get("SECOND_SLICE_PROVENANCE_READY",{}).get("status")=="NO","master provenance falsely ready")
    require(rd.get("SECOND_SLICE_NO_LOOKAHEAD_READY",{}).get("status")=="NO_ORDINARY","master no-lookahead falsely ready")
    require(rd.get("SECOND_SLICE_DETERMINISTIC_REPLAY_READY",{}).get("status")=="NO","master replay falsely ready")
    require(rd.get("SECOND_SLICE_IMPLEMENTATION_ADMITTED",{}).get("status")=="NO","master implementation falsely admitted")
    require(rd.get("FULL_CONSTRAINT_RUN_READY",{}).get("status")=="NO","master falsely full-run ready")
    require(m.get("repo_executable_acceptance_blockers")==[REPO_BLOCKER],"master repo blocker set drifted")
    require(m.get("first_serious_constraint_run")=="BLOCKED","master falsely serious-run ready")

    print("CONSTRAINT_SECOND_SLICE_BATCH024_STRICT_ACCEPTANCE_VALIDATION=PASS")
    print("STRICT_ACCEPTANCE_GATE=BLOCKED")
    print("REQUIRED_CASES_COVERED=13/14")
    print("REPO_EXECUTABLE_REQUIRED_CASE_GAPS=0")
    print("REPO_EXECUTABLE_ACCEPTANCE_BLOCKERS=1")
    print("EXTERNAL_OR_PRIVATE_ACCEPTANCE_BLOCKERS=6")
    print("CONTINUOUS_AI_SEMICONDUCTOR_POWER_CHAIN=NOT_PROVEN")
    print("FIRST_SEMICONDUCTOR_RUN=BLOCKED")
    print("NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-CONTINUOUS-CROSS-SLICE-GRAPH-CLOSURE")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ValidationFailure,json.JSONDecodeError) as exc:
        print("CONSTRAINT_SECOND_SLICE_BATCH024_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
