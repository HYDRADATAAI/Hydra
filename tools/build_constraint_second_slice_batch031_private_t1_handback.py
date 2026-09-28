#!/usr/bin/env python3
"""Build Batch031 private T1 handback after exact verification."""
from __future__ import annotations
import argparse,json,sys
from datetime import datetime,timezone
from pathlib import Path
QUEUE_REL=Path("docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json")
def fail(m): print("BATCH031_PRIVATE_T1_HANDBACK=FAIL"); print("ERROR="+m); raise SystemExit(1)
def load(p):
    if not p.is_file(): fail(f"missing JSON: {p}")
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict): fail(f"JSON root must be object: {p}")
    return v
def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--repo-root",required=True); ap.add_argument("--private-root",required=True); ap.add_argument("--output-path",required=True); a=ap.parse_args()
    repo=Path(a.repo_root).resolve(); private=Path(a.private_root).resolve(); out=Path(a.output_path).resolve()
    if out==repo or out.is_relative_to(repo): fail("handback must remain outside public repo")
    doc=load(repo/QUEUE_REL); queue=doc.get("queue")
    if not isinstance(queue,list) or len(queue)!=30: fail("queue must contain exactly 30 capture intents")
    sys.path.insert(0,str(repo/"constraint-t1-raw-artifact-store"/"src"))
    from hydra_constraint_t1_raw.store import RawArtifactStore,is_ordinary_t2_eligible
    store=RawArtifactStore(root=private,public_repo_root=repo); release=load(private/"releases"/f"{doc['release_id']}.json")
    if store.validate_stored_release_manifest(release): fail("release invalid")
    members=[]
    for item in queue:
        r=load(private/"receipts"/item["source_id"]/f"{item['source_version_id']}.json")
        if store.validate_receipt(r): fail(f"{item['source_id']}: receipt invalid")
        if not is_ordinary_t2_eligible(receipt=r,release_manifest=release,store=store): fail(f"{item['source_id']}: not ordinary T2 eligible")
        members.append({"source_id":r["source_id"],"source_version_id":r["source_version_id"],"artifact_sha256":r["artifact_sha256"],"receipt_sha256":r["receipt_sha256"],"source_locator":r["source_locator"],"acquired_at":r["acquired_at"],"available_at":r["available_at"],"content_type":r["content_type"],"byte_length":r["byte_length"]})
    hand={"schema_version":"hydra-constraint-second-slice-private-t1-handback/v2","record_id":"HYDRA_CONSTRAINT_SEMI_B030_PRIVATE_T1_HANDBACK_V001","slice_id":"SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1","generated_at":datetime.now(timezone.utc).isoformat(),"queue_record_id":doc["record_id"],"release_id":release["release_id"],"release_sha256":release["release_sha256"],"expected_source_count":30,"valid_receipt_count":30,"ordinary_t2_eligible_source_count":30,"provider_exclusion_policy":doc["provider_exclusion_policy"],"members":members,"next_action":"INGEST_BATCH031_PRIVATE_T1_HANDBACK_INTO_SEMICONDUCTOR_ORDINARY_REPLAY_LANE"}
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(hand,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("BATCH031_PRIVATE_T1_HANDBACK=PASS"); print("OUTPUT_PATH="+str(out)); print("RELEASE_SHA256="+release["release_sha256"]); return 0
if __name__=="__main__": raise SystemExit(main())
