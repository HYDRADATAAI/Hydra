#!/usr/bin/env python3
"""Hostile matrix for Batch029 locator remediation."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch029_locator_remediation.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
OVERLAY=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH029_SEMICONDUCTOR_MICRON_CAPTURE_LOCATOR_REMEDIATION_V001_20260927.json"
STATUS=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH029_SEMICONDUCTOR_MICRON_CAPTURE_LOCATOR_REMEDIATION_STATUS_V001_20260927.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH029_MASTER_STATUS_V001_20260927.json"
RUNNER="tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py"

def sandbox():
    root=Path(tempfile.mkdtemp(prefix="hydra-semi-b029-hostile-"))
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
      ("remediation_removed",lambda r:mutate_json(r,OVERLAY,lambda d:d["remediations"].pop()),"Micron remediation count drifted"),
      ("source_identity_mutation",lambda r:mutate_json(r,OVERLAY,lambda d:d.__setitem__("source_identity_mutated",True)),"source identity mutation unexpectedly allowed"),
      ("host_allowlist_drift",lambda r:mutate_json(r,OVERLAY,lambda d:d["resolution_policy"].__setitem__("allowed_resolved_host","example.com")),"resolved host allowlist drifted"),
      ("quarter_path_drift",lambda r:mutate_json(r,OVERLAY,lambda d:d["remediations"][0].__setitem__("required_path_prefix","/621799436/files/doc_financials/2025/q3/")),"fiscal quarter path mismatch"),
      ("runner_search_engine",lambda r:mutate_text(r,RUNNER,lambda s:s+"\n# search engine\n"),"runner unexpectedly relies on search engine"),
      ("status_materialized_faked",lambda r:mutate_json(r,STATUS,lambda d:d["results"].__setitem__("RAW_SOURCE_VERSIONS_MATERIALIZED",41)),"Batch029 status metric drifted: RAW_SOURCE_VERSIONS_MATERIALIZED"),
      ("master_replay_ready",lambda r:mutate_json(r,MASTER,lambda d:d["readiness"]["SECOND_SLICE_REPLAY_READY"].__setitem__("status","YES")),"master falsely claims replay ready"),
      ("master_full_ready",lambda r:mutate_json(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ];
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH029_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0

if __name__=="__main__": raise SystemExit(main())
