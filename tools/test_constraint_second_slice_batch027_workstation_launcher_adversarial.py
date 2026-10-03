#!/usr/bin/env python3
"""Hostile matrix for Batch027 workstation launcher contract."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch027_workstation_launcher.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
CONTRACT=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH027_SEMICONDUCTOR_WORKSTATION_EXECUTION_LAUNCHER_CONTRACT_V001_20260926.json"
STATUS=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH027_SEMICONDUCTOR_WORKSTATION_EXECUTION_LAUNCHER_STATUS_V001_20260926.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH027_MASTER_STATUS_V001_20260926.json"
LAUNCHER="tools/Invoke-HydraConstraintSemiconductorBatch026PrivateT1.ps1"

def sandbox():
    root=Path(tempfile.mkdtemp(prefix="hydra-semi-b027-hostile-"))
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
      ("mode_removed",lambda r:mutate_json(r,CONTRACT,lambda d:d["modes"].pop()),"launcher mode set/order drifted"),
      ("network_guarantee_removed",lambda r:mutate_json(r,CONTRACT,lambda d:d.__setitem__("guarantees",[x for x in d["guarantees"] if x!="NO_NETWORK_ACQUISITION"])),"launcher guarantees incomplete"),
      ("fixed_repo_root_reintroduced",lambda r:mutate_text(r,LAUNCHER,lambda s:s.replace('[string]$RepoRoot,','[string]$RepoRoot = "D:\\STALE\\Hydra",')),"launcher must not hard-code a workstation repo root"),
      ("launcher_network_added",lambda r:mutate_text(r,LAUNCHER,lambda s:s+"\nInvoke-WebRequest https://example.com\n"),"launcher unexpectedly performs network acquisition"),
      ("mtime_inference_added",lambda r:mutate_text(r,LAUNCHER,lambda s:s+"\n# LastWriteTime\n"),"launcher infers capture timestamp from file metadata"),
      ("status_materialized_faked",lambda r:mutate_json(r,STATUS,lambda d:d["results"].__setitem__("RAW_SOURCE_VERSIONS_MATERIALIZED",41)),"Batch027 status metric drifted: RAW_SOURCE_VERSIONS_MATERIALIZED"),
      ("status_release_faked",lambda r:mutate_json(r,STATUS,lambda d:d["results"].__setitem__("T1_RELEASE_MANIFEST_PRESENT","YES")),"Batch027 status metric drifted: T1_RELEASE_MANIFEST_PRESENT"),
      ("master_replay_ready",lambda r:mutate_json(r,MASTER,lambda d:d["readiness"]["SECOND_SLICE_REPLAY_READY"].__setitem__("status","YES")),"master falsely claims replay ready"),
      ("master_full_ready",lambda r:mutate_json(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ];
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH027_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0

if __name__=="__main__": raise SystemExit(main())
