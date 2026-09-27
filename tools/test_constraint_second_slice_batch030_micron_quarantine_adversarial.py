#!/usr/bin/env python3
"""Hostile matrix for Batch030 Micron quarantine."""
from __future__ import annotations
import json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch030_micron_quarantine.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
Q=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V002_20260927.json"
QUAR=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001_20260927.json"
C3=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_HBM_YIELD_CONSTRAINT_EVALUATION_V001_20260927.json"
C14=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_DUPLICATE_SOURCE_INFLATION_EVALUATION_V001_20260927.json"
STATUS=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_QUARANTINE_NON_MICRON_REPLACEMENT_STATUS_V001_20260927.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_MASTER_STATUS_V001_20260927.json"
def sandbox():
 r=Path(tempfile.mkdtemp(prefix="hydra-semi-b030-hostile-")); shutil.copytree(ROOT/"docs/constraint",r/"docs/constraint",dirs_exist_ok=True); shutil.copytree(ROOT/"tools",r/"tools",dirs_exist_ok=True); return r
def mut(root,rel,fn):
 p=root/rel; d=json.loads(p.read_text(encoding="utf-8")); fn(d); p.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
def run(root):
 e=dict(os.environ); e["HYDRA_REPO_ROOT"]=str(root); return subprocess.run([sys.executable,str(VALIDATOR)],cwd=ROOT,env=e,text=True,capture_output=True)
def expect(name,fn,frag):
 r=sandbox()
 try:
  b=run(r)
  if b.returncode: raise AssertionError(f"{name}: baseline failed\n{b.stdout}\n{b.stderr}")
  fn(r); x=run(r)
  if x.returncode==0: raise AssertionError(f"{name}: hostile mutation passed")
  out=x.stdout+x.stderr
  if frag not in out: raise AssertionError(f"{name}: expected {frag!r}\n{out}")
  print(f"PASS :: {name} :: {frag}")
 finally: shutil.rmtree(r,ignore_errors=True)
def main():
 cases=[
  ("micron_publisher_reinserted",lambda r:mut(r,Q,lambda d:d["queue"][0].__setitem__("publisher","Micron Technology")),"Micron publisher escaped quarantine"),
  ("micron_locator_reinserted",lambda r:mut(r,Q,lambda d:d["queue"][0].__setitem__("source_locator","https://investors.micron.com/example")),"Micron-linked locator escaped quarantine"),
  ("quarantine_retry_enabled",lambda r:mut(r,QUAR,lambda d:d.__setitem__("retry_authorized",True)),"Micron retry unexpectedly authorized"),
  ("quarantine_source_removed",lambda r:mut(r,QUAR,lambda d:d["quarantined"].pop()),"quarantine count drifted"),
  ("case3_micron_basis",lambda r:mut(r,C3,lambda d:d["evaluation"].__setitem__("constraint_variant","MICRON_HBM_YIELD")),"Case3 still contains Micron basis"),
  ("case14_translation_weight",lambda r:mut(r,C14,lambda d:d["evaluation"]["evidence_occurrences"][1].__setitem__("independent_confirmation_weight",1)),"Case14 translation copy inflates evidence"),
  ("status_capture_count_faked",lambda r:mut(r,STATUS,lambda d:d["results"].__setitem__("ACTIVE_CAPTURE_SOURCE_COUNT",41)),"Batch030 status metric drifted: ACTIVE_CAPTURE_SOURCE_COUNT"),
  ("status_materialized_faked",lambda r:mut(r,STATUS,lambda d:d["results"].__setitem__("RAW_SOURCE_VERSIONS_MATERIALIZED",38)),"Batch030 status metric drifted: RAW_SOURCE_VERSIONS_MATERIALIZED"),
  ("master_micron_dep",lambda r:mut(r,MASTER,lambda d:d["readiness"]["SECOND_SLICE_MICRON_DEPENDENT_ACTIVE_CASES"].__setitem__("status","PRESENT")),"master Micron dependency remains"),
  ("master_replay_ready",lambda r:mut(r,MASTER,lambda d:d["readiness"]["SECOND_SLICE_REPLAY_READY"].__setitem__("status","YES")),"master falsely replay ready")
 ];
 for c in cases: expect(*c)
 print("CONSTRAINT_SECOND_SLICE_BATCH030_HOSTILE_MATRIX=PASS"); print(f"HOSTILE_CASES={len(cases)}"); return 0
if __name__=="__main__": raise SystemExit(main())
