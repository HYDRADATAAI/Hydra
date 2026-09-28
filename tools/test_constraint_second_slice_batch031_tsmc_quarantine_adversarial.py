#!/usr/bin/env python3
"""Hostile mutations for the Batch031 TSMC provider quarantine."""
from __future__ import annotations
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch031_tsmc_quarantine.py"
BASE=Path("docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1")
QUEUE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json"
QUAR=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_TSMC_DIRECT_PROVIDER_QUARANTINE_V001_20260928.json"
PREV=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V002_20260927.json"

def load(path): return json.loads(path.read_text(encoding="utf-8"))
def save(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def run_case(mutator):
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        (root/BASE).mkdir(parents=True)
        for rel in (QUEUE,QUAR,PREV):
            shutil.copy2(ROOT/rel,root/rel)
        mutator(root)
        p=subprocess.run([sys.executable,str(VALIDATOR),"--repo-root",str(root)],text=True,capture_output=True)
        return p.returncode,p.stdout+p.stderr

def main():
    cases=[]
    def tsmc_reentry(root):
        q=load(root/QUEUE); prev=load(root/PREV)
        t=next(x for x in prev["queue"] if x["source_id"]=="SRC-SEMI-B022-TSMC-Q2-2026-TRANSCRIPT-2026-07-16")
        t=dict(t); t["ordinal"]=30; q["queue"][-1]=t; save(root/QUEUE,q)
    cases.append(("direct_tsmc_reentry",tsmc_reentry))

    def policy_drift(root):
        q=load(root/QUEUE); q["provider_exclusion_policy"]="MICRON_ONLY"; save(root/QUEUE,q)
    cases.append(("provider_policy_drift",policy_drift))

    def identity_drift(root):
        q=load(root/QUEUE); q["queue"][0]["source_locator"]="https://example.com/changed"; save(root/QUEUE,q)
    cases.append(("retained_identity_drift",identity_drift))

    def quarantine_drop(root):
        q=load(root/QUAR); q["quarantined_sources"].pop(); q["quarantined_source_count"]=7; save(root/QUAR,q)
    cases.append(("quarantine_member_dropped",quarantine_drop))

    failures=[]
    for name,mutator in cases:
        code,out=run_case(mutator)
        if code==0:
            failures.append(name)
            print(f"HOSTILE_FAIL {name}: validator accepted mutation")
        else:
            print(f"HOSTILE_PASS {name}")
    if failures:
        print("BATCH031_TSMC_PROVIDER_QUARANTINE_HOSTILE=FAIL")
        return 1
    print("BATCH031_TSMC_PROVIDER_QUARANTINE_HOSTILE=PASS")
    print("CASES=4/4")
    return 0

if __name__=="__main__": raise SystemExit(main())
