#!/usr/bin/env python3
"""Hostile matrix for Batch026 public private-T1 execution packet."""

from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch026_private_t1_packet.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
QUEUE=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
CONTRACT=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_MATERIALIZATION_CONTRACT_V001_20260926.json"
STATUS=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_MATERIALIZATION_STATUS_V001_20260926.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_MASTER_STATUS_V001_20260926.json"

def sandbox():
    root=Path(tempfile.mkdtemp(prefix="hydra-semi-b026-hostile-"))
    shutil.copytree(ROOT/"docs/constraint",root/"docs/constraint",dirs_exist_ok=True)
    return root
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
      ("queue_source_removed",lambda r:mutate(r,QUEUE,lambda d:d["queue"].pop()),"queue must contain exactly 41 intents"),
      ("duplicate_version_id",lambda r:mutate(r,QUEUE,lambda d:d["queue"][1].__setitem__("source_version_id",d["queue"][0]["source_version_id"])),"source_version_id values not unique"),
      ("backdating_authorized",lambda r:mutate(r,QUEUE,lambda d:d["queue"][0].__setitem__("historical_backdating_authorized",True)),"historical backdating unexpectedly authorized"),
      ("review_time_used_as_receipt",lambda r:mutate(r,QUEUE,lambda d:d["queue"][0].__setitem__("receipt_available_at_policy","COPY_REVIEWED_AVAILABLE_AT")),"receipt available_at policy drifted"),
      ("public_raw_allowed",lambda r:mutate(r,QUEUE,lambda d:d.__setitem__("public_repo_contains_raw_source_bytes",True)),"queue falsely allows public raw bytes"),
      ("contract_backdating_rule_removed",lambda r:mutate(r,CONTRACT,lambda d:d.__setitem__("materialization_rules",[x for x in d["materialization_rules"] if x!="NO_COPYING_PUBLIC_REVIEW_AVAILABLE_AT_INTO_RECEIPT"])),"contract no-backdating rule missing"),
      ("status_raw_materialized_faked",lambda r:mutate(r,STATUS,lambda d:d["results"].__setitem__("RAW_SOURCE_VERSIONS_MATERIALIZED",41)),"status metric drifted: RAW_SOURCE_VERSIONS_MATERIALIZED"),
      ("status_release_faked",lambda r:mutate(r,STATUS,lambda d:d["results"].__setitem__("T1_RELEASE_MANIFEST_PRESENT","YES")),"status metric drifted: T1_RELEASE_MANIFEST_PRESENT"),
      ("master_replay_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["SECOND_SLICE_REPLAY_READY"].__setitem__("status","YES")),"master falsely claims replay ready"),
      ("master_full_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ];
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH026_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0

if __name__=="__main__": raise SystemExit(main())
