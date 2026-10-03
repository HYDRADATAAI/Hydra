#!/usr/bin/env python3
"""Materialize the Micron/TSMC-free Batch031 semiconductor capture set into private T1."""
from __future__ import annotations
import argparse,json,sys
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
QUEUE_REL=Path("docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json")
SIDECAR_SCHEMA="hydra-semiconductor-private-capture-sidecar/v1"
ALLOWED_HTML={"text/html","multipart/related","application/x-mimearchive"}
def fail(m): raise SystemExit(f"BATCH031_PRIVATE_T1_MATERIALIZATION=FAIL\nERROR={m}")
def load(p):
    if not p.is_file(): fail(f"missing JSON: {p}")
    v=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v,dict): fail(f"JSON root must be object: {p}")
    return v
def zoned(v):
    try: d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
    except Exception: fail("capture_completed_at invalid")
    if d.tzinfo is None: fail("capture_completed_at must be offset-aware")
def materialize_or_reuse_release(store,private,release_id,receipts):
    from hydra_constraint_t1_raw.store import build_release_manifest
    release_path=private/"releases"/f"{release_id}.json"
    if release_path.is_file():
        existing=load(release_path)
        issues=store.validate_stored_release_manifest(existing)
        if issues: fail("existing immutable release invalid: "+",".join(issues))
        expected=build_release_manifest(
            release_id=release_id,
            created_at=existing["created_at"],
            receipts=receipts,
        )
        if existing!=expected:
            fail("existing immutable release does not match current 30-receipt set")
        return existing,True
    release=store.write_release_manifest(
        release_id=release_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        receipts=receipts,
    )
    return release,False

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--repo-root",required=True); ap.add_argument("--private-root",required=True); ap.add_argument("--inbox-root",required=True); ap.add_argument("--dry-run",action="store_true"); a=ap.parse_args()
    repo=Path(a.repo_root).resolve(); private=Path(a.private_root).resolve(); inbox=Path(a.inbox_root).resolve()
    if inbox==repo or inbox.is_relative_to(repo): fail("private inbox must be outside public repository")
    doc=load(repo/QUEUE_REL); queue=doc.get("queue")
    if not isinstance(queue,list) or len(queue)!=30: fail("queue must contain exactly 30 capture intents")
    prepared=[]; missing=[]
    for item in queue:
        cp=inbox/item["inbox_filename"]; sp=Path(str(cp)+".capture.json")
        if not cp.is_file(): missing.append(f"FILE:{item['source_id']}:{cp}"); continue
        if not sp.is_file(): missing.append(f"SIDECAR:{item['source_id']}:{sp}"); continue
        side=load(sp); req={"schema_version","capture_intent_id","source_id","source_version_id","source_locator","capture_completed_at","content_type","processing_disposition","historical_backdating_authorized"}
        if set(side)!=req: fail(f"{item['source_id']}: sidecar field set invalid")
        if side["schema_version"]!=SIDECAR_SCHEMA: fail(f"{item['source_id']}: sidecar schema invalid")
        for f in ("capture_intent_id","source_id","source_version_id","source_locator"):
            if side[f]!=item[f]: fail(f"{item['source_id']}: sidecar {f} mismatch")
        if side["processing_disposition"]!="ELIGIBLE" or side["historical_backdating_authorized"] is not False: fail(f"{item['source_id']}: sidecar disposition/backdating invalid")
        zoned(side["capture_completed_at"]); ct=side["content_type"]; hint=item["content_type_hint"]
        if hint=="application/pdf" and ct!="application/pdf": fail(f"{item['source_id']}: expected PDF")
        if hint=="text/html" and ct not in ALLOWED_HTML: fail(f"{item['source_id']}: expected HTML")
        prepared.append((item,cp,side))
    if missing:
        print("BATCH031_PRIVATE_T1_MATERIALIZATION=BLOCKED"); print("EXPECTED=30"); print(f"READY={len(prepared)}"); print(f"MISSING={len(missing)}")
        for x in missing: print(x)
        return 1
    print("BATCH031_PRIVATE_CAPTURE_INBOX_VALIDATION=PASS"); print("CAPTURE_FILES_READY=30")
    if a.dry_run: print("DRY_RUN=YES"); return 0
    sys.path.insert(0,str(repo/"constraint-t1-raw-artifact-store"/"src"))
    from hydra_constraint_t1_raw.store import RawArtifactStore,is_ordinary_t2_eligible
    store=RawArtifactStore(root=private,public_repo_root=repo); receipts=[]
    for item,cp,side in prepared:
        ts=side["capture_completed_at"]
        rec=store.persist(raw_bytes=cp.read_bytes(),source_id=item["source_id"],source_version_id=item["source_version_id"],content_type=side["content_type"],acquired_at=ts,available_at=ts,source_locator=item["source_locator"],processing_disposition="ELIGIBLE")
        issues=store.validate_receipt(rec)
        if issues: fail(f"{item['source_id']}: invalid receipt: {','.join(issues)}")
        receipts.append(rec)
    release,release_reused=materialize_or_reuse_release(
        store=store,
        private=private,
        release_id=doc["release_id"],
        receipts=receipts,
    )
    if store.validate_stored_release_manifest(release): fail("stored release invalid")
    eligible=sum(1 for r in receipts if is_ordinary_t2_eligible(receipt=r,release_manifest=release,store=store))
    if eligible!=30: fail(f"ordinary T2 eligibility incomplete: {eligible}/30")
    print("BATCH031_PRIVATE_T1_MATERIALIZATION=PASS"); print("VALID_T1_RECEIPTS=30"); print("T1_RELEASE_ID="+release["release_id"]); print("T1_RELEASE_SHA256="+release["release_sha256"]); print("T1_RELEASE_REUSED="+("YES" if release_reused else "NO")); print("ORDINARY_T2_ELIGIBLE_SOURCES=30"); return 0
if __name__=="__main__": raise SystemExit(main())
