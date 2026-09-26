#!/usr/bin/env python3
"""Hostile mutation matrix for second-slice Batch017 audit."""

from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from typing import Callable

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch017_audit.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
SCOPE=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_SCOPE_MANIFEST_V001_20260926.json"
AUDIT=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_SEMANTIC_REUSE_AUDIT_V001_20260926.json"
FIELDS=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_FIELD_REQUIREMENTS_V001_20260926.json"
CASES=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_REQUIRED_CASE_MATRIX_V001_20260926.json"
AUTH=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_AUTHORITY_MAP_V001_20260926.json"
STATUS=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_STATUS_V001_20260926.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_MASTER_STATUS_V001_20260926.json"

def sandbox():
    t=Path(tempfile.mkdtemp(prefix="hydra-semiconductor-audit-hostile-"))
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
        if r.returncode==0: raise AssertionError(f"{name}: mutation passed")
        out=r.stdout+r.stderr
        if frag not in out: raise AssertionError(f"{name}: expected {frag!r}\n{out}")
        print(f"PASS :: {name} :: {frag}")
    finally: shutil.rmtree(root,ignore_errors=True)

def main():
    cases=[
      ("parallel_semantics",lambda r:mutate(r,SCOPE,lambda d:d.__setitem__("semantic_duplication_created",True)),"parallel/duplicate semiconductor semantics created"),
      ("fake_existing_population",lambda r:mutate(r,AUDIT,lambda d:d.__setitem__("repository_semiconductor_specific_population_found",True)),"falsely claims semiconductor population existed"),
      ("effective_capacity_removed",lambda r:mutate(r,FIELDS,lambda d:d.__setitem__("fields",[x for x in d["fields"] if x["field_name"]!="effective_capacity"])),"field count drifted"),
      ("capacity_firewall_removed",lambda r:mutate(r,FIELDS,lambda d:d.__setitem__("semantic_firewalls",[x for x in d["semantic_firewalls"] if x!="INSTALLED_CAPACITY_NE_EFFECTIVE_CAPACITY"])),"semantic firewall missing"),
      ("case_preclosed",lambda r:mutate(r,CASES,lambda d:d["cases"][0].__setitem__("status","COVERED")),"prematurely claims required case coverage"),
      ("ambiguous_owner",lambda r:mutate(r,AUTH,lambda d:d["authorities"][0].__setitem__("owner","THREAD_1")),"ambiguous bare THREAD_N owner introduced"),
      ("fake_population_count",lambda r:mutate(r,STATUS,lambda d:d["results"].__setitem__("FACILITIES_POPULATED",12)),"falsely populates FACILITIES_POPULATED"),
      ("fake_cross_slice_graph",lambda r:mutate(r,STATUS,lambda d:d["results"].__setitem__("CROSS_SLICE_AI_SEMICONDUCTOR_POWER_GRAPH","PASS")),"falsely claims cross-slice graph"),
      ("master_population_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["SECOND_SLICE_DOMAIN_POPULATED"].__setitem__("status","YES")),"falsely marks second slice populated"),
      ("master_full_ready",lambda r:mutate(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ]
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH017_AUDIT_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0
if __name__=="__main__": raise SystemExit(main())
