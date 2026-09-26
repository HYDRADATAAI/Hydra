#!/usr/bin/env python3
"""Hostile mutation checks for Batch017 persisted custody."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from typing import Callable

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_first_slice_custody.py"
CONTRACT="docs/constraint/implementation/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_T1_T2_PERSISTED_CHAIN_OF_CUSTODY_CONTRACT_V001_20260925.json"
STATUS="docs/constraint/validation/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_T1_T2_CHAIN_OF_CUSTODY_STATUS_V001_20260925.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_MASTER_STATUS_V001_20260925.json"

def sandbox()->Path:
    root=Path(tempfile.mkdtemp(prefix="hydra-custody-hostile-"))
    shutil.copytree(ROOT/"docs/constraint",root/"docs/constraint",dirs_exist_ok=True)
    return root
def mutate(root:Path,relative:str,fn:Callable[[dict],None])->None:
    p=root/relative; d=json.loads(p.read_text(encoding="utf-8")); fn(d); p.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
def run(root:Path)->subprocess.CompletedProcess[str]:
    env=dict(os.environ); env["HYDRA_REPO_ROOT"]=str(root)
    return subprocess.run([sys.executable,str(VALIDATOR)],cwd=ROOT,env=env,text=True,capture_output=True,check=False)
def expect(name:str,fn:Callable[[Path],None],fragment:str)->None:
    root=sandbox()
    try:
        base=run(root)
        if base.returncode!=0: raise AssertionError(f"{name}: baseline failed\n{base.stdout}\n{base.stderr}")
        fn(root); result=run(root)
        if result.returncode==0: raise AssertionError(f"{name}: hostile mutation incorrectly passed")
        output=result.stdout+result.stderr
        if fragment not in output: raise AssertionError(f"{name}: expected {fragment!r}\n{output}")
        print(f"PASS :: {name} :: {fragment}")
    finally: shutil.rmtree(root,ignore_errors=True)

def in_memory_release(root): mutate(root,CONTRACT,lambda d:d["authority_semantics"].__setitem__("caller_supplied_in_memory_release_manifest_authoritative",True))
def recomputed_digest(root): mutate(root,CONTRACT,lambda d:d["authority_semantics"].__setitem__("self_consistent_recomputed_digest_sufficient",True))
def persisted_identity_removed(root): mutate(root,CONTRACT,lambda d:d["authority_semantics"].__setitem__("persisted_record_identity_required",False))
def forged_upgrade_allowed(root): mutate(root,STATUS,lambda d:d["results"].__setitem__("FORGED_RECEIPT_DISPOSITION_UPGRADE","ALLOWED"))
def outcome_regressed(root): mutate(root,STATUS,lambda d:d["results"].__setitem__("REAL_OUTCOME_RECORDS",2))
def repo_blocker_invented(root): mutate(root,MASTER,lambda d:d.__setitem__("repo_executable_blockers",["FAKE-REPO-BLOCKER"]))
def full_ready(root):
    def change(d):
        d["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"]="YES"; d["first_serious_constraint_run"]="READY"
    mutate(root,MASTER,change)

def main()->int:
    cases=[
      ("in_memory_release_authority",in_memory_release,"Batch017 in-memory release authority unexpectedly enabled"),
      ("recomputed_digest_authority",recomputed_digest,"Batch017 recomputed digest unexpectedly sufficient"),
      ("persisted_identity_removed",persisted_identity_removed,"Batch017 persisted identity requirement removed"),
      ("forged_upgrade_allowed",forged_upgrade_allowed,"Batch017 forged disposition upgrade not blocked"),
      ("outcome_coverage_regressed",outcome_regressed,"Batch017 lost Batch016 outcome coverage"),
      ("repo_blocker_invented",repo_blocker_invented,"Batch017 repo-executable blocker state drifted"),
      ("full_run_falsely_ready",full_ready,"Batch017 master falsely full-run ready"),
    ]
    for case in cases: expect(*case)
    print("CONSTRAINT_FIRST_SLICE_PERSISTED_CUSTODY_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0
if __name__=="__main__": raise SystemExit(main())
