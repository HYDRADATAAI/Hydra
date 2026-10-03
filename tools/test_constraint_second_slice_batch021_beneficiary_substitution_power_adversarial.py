#!/usr/bin/env python3
"""Hostile matrix for Batch021 beneficiary/substitution/migration/power depth."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from typing import Callable
ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch021_beneficiary_substitution_power.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
SRC=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_SUBSTITUTION_MIGRATION_POWER_SOURCE_REGISTRY_V001_20260926.json"
BEN=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_EVALUATION_V001_20260926.json"
SUB=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_SUBSTITUTION_QUALIFICATION_EVALUATION_V001_20260926.json"
QUAL=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_SAMSUNG_HBM3E_QUALIFICATION_TIMELINE_V001_20260926.json"
MIG=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_CONSTRAINT_MIGRATION_EVALUATION_V001_20260926.json"
POWER=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_TO_POWER_INFRASTRUCTURE_GRAPH_OVERLAY_V001_20260926.json"
CASES=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_MASTER_STATUS_V001_20260926.json"
def sandbox():
    t=Path(tempfile.mkdtemp(prefix="hydra-semi-b021-hostile-")); shutil.copytree(ROOT/"docs/constraint",t/"docs/constraint",dirs_exist_ok=True); return t
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
    finally: shutil.rmtree(root,ignore_errors=True)
def main():
    cases=[
      ("backdate_source",lambda r:mutate(r,SRC,lambda d:d["sources"][0].__setitem__("available_at","2024-06-26T00:00:00Z")),"conservative available_at drifted"),
      ("micron_canonical_qualified",lambda r:mutate(r,BEN,lambda d:d["relationships"][0].__setitem__("qualification_state","QUALIFIED")),"canonical qualification escaped gate"),
      ("micron_ordinary_eligible",lambda r:mutate(r,BEN,lambda d:d["relationships"][0].__setitem__("ordinary_t6_eligible",True)),"beneficiary became ordinary T6 eligible"),
      ("samsung_spare_capacity_faked",lambda r:mutate(r,SUB,lambda d:d["evaluations"][0].__setitem__("unbooked_addressable_capacity_state","PROVEN_AVAILABLE")),"spare capacity was fabricated"),
      ("substitution_resolves_parent",lambda r:mutate(r,SUB,lambda d:d["evaluations"][0].__setitem__("parent_constraint_effect","RESOLVED")),"falsely resolved parent constraint"),
      ("qualification_backfilled",lambda r:mutate(r,QUAL,lambda d:d["states"][1].__setitem__("target_specific_qualification","PROVEN_FOR_AMD_MI350X_MI355X")),"historical qualification was backfilled"),
      ("migration_falsely_closed",lambda r:mutate(r,MIG,lambda d:(d["evaluations"][0].__setitem__("migration_state","COVERED"),d["evaluations"][0].__setitem__("case_11_coverage",True))),"migration case prematurely covered"),
      ("power_constraint_invented",lambda r:mutate(r,POWER,lambda d:d.__setitem__("power_constraint_asserted",True)),"power dependency was escalated into a power constraint"),
      ("case11_preclosed",lambda r:mutate(r,CASES,lambda d:d.__setitem__("remaining_gap_case_ids",[3,4,5,12,14])),"remaining gap set drifted"),
      ("case12_replay_closed",lambda r:mutate(r,CASES,lambda d:d["progress_only"][1].__setitem__("progress_state","COVERED")),"Case 12 raw-lineage gate drifted"),
      ("master_full_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ];
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH021_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0
if __name__=="__main__": raise SystemExit(main())
