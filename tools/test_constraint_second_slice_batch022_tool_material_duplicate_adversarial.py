#!/usr/bin/env python3
"""Hostile matrix for Batch022 tool/material/duplicate-evidence depth."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch022_tool_material_duplicate.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
SRC=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_YIELD_TOOL_MATERIAL_DUPLICATE_SOURCE_REGISTRY_V001_20260926.json"
TOOL=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_TOOL_BOTTLENECK_EVALUATION_V001_20260926.json"
MAT=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_MATERIAL_BOTTLENECK_EVALUATION_V001_20260926.json"
DUP=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_DUPLICATE_SOURCE_INFLATION_EVALUATION_V001_20260926.json"
YIELD=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_HBM_YIELD_CONSTRAINT_EVALUATION_V001_20260926.json"
CASES=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_REQUIRED_CASE_OVERLAY_V001_20260926.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_MASTER_STATUS_V001_20260926.json"
def sandbox():
    t=Path(tempfile.mkdtemp(prefix="hydra-semi-b022-hostile-")); shutil.copytree(ROOT/"docs/constraint",t/"docs/constraint",dirs_exist_ok=True); return t
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
      ("source_backdated",lambda r:mutate(r,SRC,lambda d:d["sources"][0].__setitem__("available_at","2026-07-16T00:00:00Z")),"conservative available_at drifted"),
      ("tool_specific_fab_delay_faked",lambda r:mutate(r,TOOL,lambda d:d["evaluation"].__setitem__("specific_fab_delay_proven",True)),"escalated into a specific fab delay"),
      ("tool_canonical_mint",lambda r:mutate(r,TOOL,lambda d:d["evaluation"].__setitem__("canonical_constraint_minted",True)),"tool case minted canonical constraint"),
      ("material_geological_scarcity",lambda r:mutate(r,MAT,lambda d:d["evaluation"].__setitem__("raw_resource_state","QUARTZ_GEOLOGICALLY_SCARCE")),"material geological state drifted"),
      ("material_downstream_failure_faked",lambda r:mutate(r,MAT,lambda d:d["evaluation"].__setitem__("downstream_critical_supply_failure_proven",True)),"downstream semiconductor supply failure was fabricated"),
      ("duplicate_inflated",lambda r:mutate(r,DUP,lambda d:d["evaluation"].__setitem__("independent_evidence_cluster_count",2)),"duplicate copies inflated independent evidence count"),
      ("duplicate_confidence_weight",lambda r:mutate(r,DUP,lambda d:d["evaluation"].__setitem__("confidence_multiplier_from_copy",1)),"distribution copy inflated confidence"),
      ("yield_falsely_covered",lambda r:mutate(r,YIELD,lambda d:d["evaluation"].__setitem__("coverage_state","COVERED")),"yield case prematurely covered"),
      ("yield_constraint_fabricated",lambda r:mutate(r,YIELD,lambda d:d["evaluation"].__setitem__("binding_effective_output_constraint_proven",True)),"binding HBM yield constraint was fabricated"),
      ("migration_preclosed",lambda r:mutate(r,CASES,lambda d:d.__setitem__("remaining_gap_case_ids",[3,12])),"remaining gap set drifted"),
      ("replay_preclosed",lambda r:mutate(r,CASES,lambda d:d["progress_only"][2].__setitem__("progress_state","COVERED")),"Case 12 raw-lineage gate drifted"),
      ("master_full_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ];
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH022_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0
if __name__=="__main__": raise SystemExit(main())
