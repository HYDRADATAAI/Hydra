#!/usr/bin/env python3
"""Hostile matrix for Batch024 strict acceptance gate."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch024_acceptance_gate.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
GATE=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH024_SEMICONDUCTOR_STRICT_ACCEPTANCE_GATE_V001_20260926.json"
BLOCK=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH024_SEMICONDUCTOR_ACCEPTANCE_BLOCKER_REGISTER_V001_20260926.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH024_MASTER_STATUS_V001_20260926.json"
B021POWER=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_TO_POWER_INFRASTRUCTURE_GRAPH_OVERLAY_V001_20260926.json"
B023CASES=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json"

def sandbox():
    t=Path(tempfile.mkdtemp(prefix="hydra-semi-b024-hostile-"))
    shutil.copytree(ROOT/"docs/constraint",t/"docs/constraint",dirs_exist_ok=True)
    return t
def mutate(root,rel,fn):
    p=root/rel; d=json.loads(p.read_text(encoding="utf-8")); fn(d); p.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
def run(root):
    env=dict(os.environ); env["HYDRA_REPO_ROOT"]=str(root)
    return subprocess.run([sys.executable,str(VALIDATOR)],cwd=ROOT,env=env,text=True,capture_output=True,check=False)
def expect(name,fn,frag):
    root=sandbox()
    try:
      b=run(root)
      if b.returncode: raise AssertionError(f"{name}: baseline failed\n{b.stdout}\n{b.stderr}")
      fn(root); r=run(root)
      if r.returncode==0: raise AssertionError(f"{name}: hostile mutation passed")
      out=r.stdout+r.stderr
      if frag not in out: raise AssertionError(f"{name}: expected {frag!r}\n{out}")
      print(f"PASS :: {name} :: {frag}")
    finally:
      shutil.rmtree(root,ignore_errors=True)
def main():
    cases=[
      ("cross_slice_pass_faked",lambda r:mutate(r,GATE,lambda d:d["dimensions"]["CROSS_SLICE_GRAPH"].__setitem__("status","PASS")),"CROSS_SLICE_GRAPH status drifted"),
      ("provenance_pass_faked",lambda r:mutate(r,GATE,lambda d:d["dimensions"]["PROVENANCE"].__setitem__("status","PASS")),"PROVENANCE status drifted"),
      ("no_lookahead_pass_faked",lambda r:mutate(r,GATE,lambda d:d["dimensions"]["NO_LOOKAHEAD"].__setitem__("status","PASS")),"NO_LOOKAHEAD status drifted"),
      ("replay_pass_faked",lambda r:mutate(r,GATE,lambda d:d["dimensions"]["DETERMINISTIC_REPLAY"].__setitem__("status","PASS")),"DETERMINISTIC_REPLAY status drifted"),
      ("implementation_pass_faked",lambda r:mutate(r,GATE,lambda d:d["dimensions"]["IMPLEMENTATION_ADMITTED"].__setitem__("status","PASS")),"IMPLEMENTATION_ADMITTED status drifted"),
      ("overall_pass_faked",lambda r:mutate(r,GATE,lambda d:(d.__setitem__("overall_status","PASS"),d.__setitem__("full_constraint_run_allowed",True))),"overall acceptance gate falsely not blocked"),
      ("repo_blocker_removed",lambda r:mutate(r,BLOCK,lambda d:d.__setitem__("repo_executable_blockers",[])),"repo-executable blocker register drifted"),
      ("raw_blocker_removed",lambda r:mutate(r,BLOCK,lambda d:d.__setitem__("external_or_private_blockers",[x for x in d["external_or_private_blockers"] if x["blocker_id"]!="SEMICONDUCTOR-SLICE-006-RAW-SOURCE-VERSIONS-NOT-MATERIALIZED"])),"raw-lineage blocker missing"),
      ("case12_closed",lambda r:mutate(r,B023CASES,lambda d:d.__setitem__("remaining_gap_case_ids",[])),"Batch023 remaining case gap drifted"),
      ("power_constraint_invented",lambda r:mutate(r,B021POWER,lambda d:d.__setitem__("power_constraint_asserted",True)),"power dependency escalated into power constraint"),
      ("master_cross_slice_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["SECOND_SLICE_CROSS_SLICE_GRAPH_ACCEPTANCE"].__setitem__("status","YES")),"master cross-slice acceptance status drifted"),
      ("master_full_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ];
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH024_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0

if __name__=="__main__": raise SystemExit(main())
