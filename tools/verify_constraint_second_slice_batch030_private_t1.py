#!/usr/bin/env python3
"""Verify Batch030 private T1 receipts and exact release membership."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from typing import Any
QUEUE_REL=Path("docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V002_20260927.json")
def fail(m): print("BATCH030_PRIVATE_T1_VERIFICATION=FAIL"); print("ERROR="+m); raise SystemExit(1)
def load(p):
    if not p.is_file(): fail(f"missing JSON: {p}")
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict): fail(f"JSON root must be object: {p}")
    return v
def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--repo-root",required=True); ap.add_argument("--private-root",required=True); a=ap.parse_args()
    repo=Path(a.repo_root).resolve(); private=Path(a.private_root).resolve(); doc=load(repo/QUEUE_REL); queue=doc.get("queue")
    if not isinstance(queue,list) or len(queue)!=38: fail("queue must contain exactly 38 capture intents")
    sys.path.insert(0,str(repo/"constraint-t1-raw-artifact-store"/"src"))
    from hydra_constraint_t1_raw.store import RawArtifactStore,is_ordinary_t2_eligible
    store=RawArtifactStore(root=private,public_repo_root=repo); receipts=[]; missing=[]; invalid=[]
    for item in queue:
        rp=private/"receipts"/item["source_id"]/f"{item['source_version_id']}.json"
        if not rp.is_file(): missing.append(item["source_id"]); continue
        r=load(rp); issues=store.validate_receipt(r)
        if issues: invalid.append((item["source_id"],",".join(issues))); continue
        if r.get("source_locator")!=item["source_locator"]: invalid.append((item["source_id"],"source_locator_mismatch")); continue
        if r.get("acquired_at")!=r.get("available_at"): invalid.append((item["source_id"],"unexpected_backdating")); continue
        if r.get("processing_disposition")!="ELIGIBLE": invalid.append((item["source_id"],"not_eligible")); continue
        receipts.append(r)
    relp=private/"releases"/f"{doc['release_id']}.json"; release=load(relp) if relp.is_file() else None
    issues=("release_record_missing",) if release is None else store.validate_stored_release_manifest(release)
    expected={(x["source_id"],x["source_version_id"]) for x in queue}; actual=set()
    if release: actual={(x.get("source_id"),x.get("source_version_id")) for x in release.get("members",[])}
    eligible=0
    if release is not None and not issues:
        eligible=sum(1 for r in receipts if is_ordinary_t2_eligible(receipt=r,release_manifest=release,store=store))
    print("BATCH030_PRIVATE_T1_VERIFICATION_SUMMARY"); print("EXPECTED_RECEIPTS=38"); print(f"VALID_RECEIPTS={len(receipts)}"); print(f"MISSING_RECEIPTS={len(missing)}"); print(f"INVALID_RECEIPTS={len(invalid)}"); print(f"RELEASE_VALID={'YES' if not issues else 'NO'}"); print(f"RELEASE_MEMBERS={len(actual)}"); print(f"ORDINARY_T2_ELIGIBLE_SOURCES={eligible}")
    if len(receipts)!=38 or missing or invalid or issues or actual!=expected or eligible!=38:
        print("BATCH030_PRIVATE_T1_VERIFICATION=BLOCKED"); return 1
    print("BATCH030_PRIVATE_T1_VERIFICATION=PASS"); print("T1_RELEASE_ID="+release["release_id"]); print("T1_RELEASE_SHA256="+release["release_sha256"]); return 0
if __name__=="__main__": raise SystemExit(main())
