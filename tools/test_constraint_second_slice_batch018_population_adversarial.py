#!/usr/bin/env python3
"""Hostile mutation matrix for Batch018 first semiconductor population."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from typing import Callable

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch018_population.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
SOURCES=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_SOURCE_REGISTRY_V001_20260926.json"
CAP=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_CAPACITY_YIELD_QUALIFICATION_OVERLAY_V001_20260926.json"
GRAPH=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_GRAPH_SEED_V001_20260926.json"
CAND=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_T5_CANDIDATE_PROPOSALS_V001_20260926.json"
CASES=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_REQUIRED_CASE_OVERLAY_V001_20260926.json"
STATUS=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_STATUS_V001_20260926.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_MASTER_STATUS_V001_20260926.json"

def sandbox():
    t=Path(tempfile.mkdtemp(prefix="hydra-semi-pop-hostile-")); shutil.copytree(ROOT/"docs/constraint",t/"docs/constraint",dirs_exist_ok=True); return t
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
      ("backdated_source",lambda r:mutate(r,SOURCES,lambda d:d["sources"][0].__setitem__("available_at","2025-01-01T00:00:00Z")),"conservative available_at drifted"),
      ("raw_lineage_faked",lambda r:mutate(r,SOURCES,lambda d:d["sources"][0].__setitem__("ordinary_raw_lineage_eligible",True)),"source unexpectedly ordinary raw-lineage eligible"),
      ("micron_booked_becomes_effective",lambda r:mutate(r,CAP,lambda d:d["rows"][0].__setitem__("effective_capacity","FULL_OUTPUT")),"fabricated effective capacity"),
      ("yield_fabricated",lambda r:mutate(r,CAP,lambda d:d["rows"][1].__setitem__("yield_value",0.92)),"Micron yield was fabricated"),
      ("cowos_expansion_realized",lambda r:mutate(r,CAP,lambda d:d["rows"][5].__setitem__("semantic_limit","DOUBLING ACHIEVED")),"CoWoS expansion realization firewall missing"),
      ("cross_slice_edge_removed",lambda r:mutate(r,GRAPH,lambda d:d["edges"].pop(0)),"graph edge count drifted"),
      ("canonical_minted",lambda r:mutate(r,CAND,lambda d:d["candidates"][0].__setitem__("canonical_constraint_id","K-SEMI-001")),"canonical constraint minted"),
      ("hbm_globalized",lambda r:mutate(r,CAND,lambda d:d["candidates"][1].__setitem__("semantic_limit","GLOBAL HBM SUPPLY SOLD OUT")),"HBM scope was generalized"),
      ("case3_preclosed",lambda r:mutate(r,CASES,lambda d:d.__setitem__("remaining_gap_case_ids",list(range(4,15)))),"remaining case gaps drifted"),
      ("facility_population_faked",lambda r:mutate(r,STATUS,lambda d:d["results"].__setitem__("FACILITIES_POPULATED",5)),"status metric drifted: FACILITIES_POPULATED"),
      ("full_run_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ]
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH018_POPULATION_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0
if __name__=="__main__": raise SystemExit(main())
