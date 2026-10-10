#!/usr/bin/env python3
"""Hostile matrix for Batch023 HBM-yield and migration closure."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch023_hbm_yield_migration.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
SRC=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_HBM_YIELD_MIGRATION_SOURCE_REGISTRY_V001_20260926.json"
YIELD=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_HBM_YIELD_CONSTRAINT_EVALUATION_V001_20260926.json"
MIG=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_CONSTRAINT_MIGRATION_EVALUATION_V001_20260926.json"
CASES=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_MASTER_STATUS_V001_20260926.json"

def sandbox():
    t=Path(tempfile.mkdtemp(prefix="hydra-semi-b023-hostile-"))
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
      ("backdated_source",lambda r:mutate(r,SRC,lambda d:d["sources"][0].__setitem__("available_at","2023-12-20T00:00:00Z")),"conservative available_at drifted"),
      ("yield_percentage_faked",lambda r:mutate(r,YIELD,lambda d:d["evaluation"].__setitem__("numeric_yield_percentage",0.65)),"numeric HBM yield percentage was fabricated"),
      ("yield_output_penalty_removed",lambda r:mutate(r,YIELD,lambda d:d["evaluation"].__setitem__("binding_effective_output_constraint_proven",False)),"binding HBM effective-output constraint not proven"),
      ("yield_scope_generalized",lambda r:mutate(r,YIELD,lambda d:d["evaluation"].__setitem__("constraint_variant","GLOBAL_HBM_YIELD_SHORTAGE")),"yield constraint variant drifted"),
      ("migration_relief_unobserved",lambda r:mutate(r,MIG,lambda d:d["evaluations"][0]["relief_event"].__setitem__("state","FORWARD_EXPECTATION_ONLY")),"old limiter relief is not observed"),
      ("migration_systemwide_resolution",lambda r:mutate(r,MIG,lambda d:d["evaluations"][0].__setitem__("systemwide_resolution_asserted",True)),"migration falsely claims system-wide resolution"),
      ("migration_new_limiter_removed",lambda r:mutate(r,MIG,lambda d:d["evaluations"][0].__setitem__("new_limiting_mechanism","NONE")),"new limiting mechanism drifted"),
      ("cowos_candidate_promoted",lambda r:mutate(r,MIG,lambda d:d["evaluations"][1].__setitem__("case_11_coverage",True)),"older CoWoS migration candidate falsely covers Case 11"),
      ("case12_preclosed",lambda r:mutate(r,CASES,lambda d:d.__setitem__("remaining_gap_case_ids",[])),"remaining gap set drifted"),
      ("case12_state_closed",lambda r:mutate(r,CASES,lambda d:d["progress_only"][0].__setitem__("progress_state","COVERED")),"Case 12 raw-lineage gate drifted"),
      ("master_replay_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["SECOND_SLICE_REPLAY_READY"].__setitem__("status","YES")),"master falsely marks replay ready"),
      ("master_full_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ];
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH023_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0
if __name__=="__main__": raise SystemExit(main())
