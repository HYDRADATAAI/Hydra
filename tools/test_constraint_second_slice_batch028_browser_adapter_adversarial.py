#!/usr/bin/env python3
"""Hostile matrix for Batch028 semiconductor browser adapter."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch028_browser_adapter.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
CONTRACT=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH028_SEMICONDUCTOR_BROWSER_ACQUISITION_ADAPTER_CONTRACT_V001_20260927.json"
STATUS=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH028_SEMICONDUCTOR_BROWSER_ACQUISITION_ADAPTER_STATUS_V001_20260927.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH028_MASTER_STATUS_V001_20260927.json"
RUNNER="tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py"
LAUNCHER="tools/private/Invoke-HYDRAConstraintSemiconductorBatch026BrowserCapture_V001_20260927.ps1"

def sandbox():
    root=Path(tempfile.mkdtemp(prefix="hydra-semi-b028-hostile-"))
    shutil.copytree(ROOT/"docs/constraint",root/"docs/constraint",dirs_exist_ok=True)
    shutil.copytree(ROOT/"tools",root/"tools",dirs_exist_ok=True)
    return root
def mutate_json(root,rel,fn):
    p=root/rel; d=json.loads(p.read_text(encoding="utf-8")); fn(d); p.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
def mutate_text(root,rel,fn):
    p=root/rel; p.write_text(fn(p.read_text(encoding="utf-8")),encoding="utf-8")
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
      ("source_count_drift",lambda r:mutate_json(r,CONTRACT,lambda d:d.__setitem__("expected_source_count",40)),"contract source count drifted"),
      ("cross_origin_enabled",lambda r:mutate_json(r,CONTRACT,lambda d:d["redirect_policy"].__setitem__("cross_origin_allowed",True)),"cross-origin redirects unexpectedly allowed"),
      ("t1_persistence_claimed",lambda r:mutate_json(r,CONTRACT,lambda d:d["authorization"].__setitem__("t1_persistence_performed_by_runner",True)),"runner improperly owns T1 persistence"),
      ("runner_t1_store_import",lambda r:mutate_text(r,RUNNER,lambda s:s+"\n# RawArtifactStore\n"),"browser runner imports T1 raw store"),
      ("runner_backdating_enabled",lambda r:mutate_text(r,RUNNER,lambda s:s+'\n# "historical_backdating_authorized": True\n'),"browser runner enables historical backdating"),
      ("launcher_git_mutation",lambda r:mutate_text(r,LAUNCHER,lambda s:s+"\n# git pull origin main\n"),"launcher unexpectedly mutates git branch state"),
      ("status_materialized_faked",lambda r:mutate_json(r,STATUS,lambda d:d["results"].__setitem__("RAW_SOURCE_VERSIONS_MATERIALIZED",41)),"Batch028 status metric drifted: RAW_SOURCE_VERSIONS_MATERIALIZED"),
      ("master_replay_ready",lambda r:mutate_json(r,MASTER,lambda d:d["readiness"]["SECOND_SLICE_REPLAY_READY"].__setitem__("status","YES")),"master falsely claims replay ready"),
      ("master_full_ready",lambda r:mutate_json(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ];
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH028_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0

if __name__=="__main__": raise SystemExit(main())
