#!/usr/bin/env python3
"""Capture the Batch030 Micron-free semiconductor queue into the private inbox."""

from __future__ import annotations
import argparse, importlib.util, json, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

QUEUE_REL=Path("docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V002_20260927.json")
BASE_RUNNER_REL=Path("tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py")
EXPECTED_SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
EXPECTED_COUNT=38
JOURNAL_SCHEMA="hydra-constraint-semiconductor-batch030-browser-capture-journal/v1"

class CaptureError(RuntimeError): pass

def utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")

def load_json(path:Path)->dict[str,Any]:
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: raise CaptureError(f"unable to read JSON: {path}") from exc
    if not isinstance(value,dict): raise CaptureError(f"top-level object required: {path}")
    return value

def write_json(path:Path,value:Mapping[str,Any]):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def import_base(repo_root:Path):
    path=repo_root/BASE_RUNNER_REL
    spec=importlib.util.spec_from_file_location("hydra_batch028_browser_base",path)
    if spec is None or spec.loader is None: raise CaptureError("unable to import Batch028 browser engine")
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def validate_queue(doc:Mapping[str,Any])->list[dict[str,Any]]:
    if doc.get("slice_id")!=EXPECTED_SLICE: raise CaptureError("queue slice_id mismatch")
    rows=doc.get("queue")
    if not isinstance(rows,list) or len(rows)!=EXPECTED_COUNT: raise CaptureError(f"queue must contain exactly {EXPECTED_COUNT} intents")
    ids=set(); versions=set(); filenames=set()
    out=[]
    for i,raw in enumerate(rows):
        if not isinstance(raw,Mapping): raise CaptureError(f"queue[{i}] must be object")
        sid=raw.get("source_id"); vid=raw.get("source_version_id"); loc=raw.get("source_locator"); fn=raw.get("inbox_filename")
        if not isinstance(sid,str) or not sid: raise CaptureError(f"queue[{i}] source_id missing")
        if "MICRON" in sid.upper() or "GLOBENEWSWIRE-MICRON" in sid.upper(): raise CaptureError(f"{sid}: Micron-linked source is forbidden in Batch030")
        if sid in ids: raise CaptureError(f"duplicate source_id: {sid}")
        if not isinstance(vid,str) or not vid or vid in versions: raise CaptureError(f"{sid}: invalid/duplicate source_version_id")
        if not isinstance(loc,str) or not loc.startswith("https://"): raise CaptureError(f"{sid}: HTTPS locator required")
        if "micron.com" in loc.lower() or "globenewswire.com" in loc.lower(): raise CaptureError(f"{sid}: forbidden provider/domain in Batch030 locator")
        if not isinstance(fn,str) or Path(fn).name!=fn or fn in filenames: raise CaptureError(f"{sid}: invalid/duplicate inbox filename")
        if raw.get("historical_backdating_authorized") is not False: raise CaptureError(f"{sid}: backdating must remain false")
        if raw.get("processing_disposition")!="ELIGIBLE": raise CaptureError(f"{sid}: disposition must remain ELIGIBLE")
        if raw.get("content_type_hint") not in {"application/pdf","text/html"}: raise CaptureError(f"{sid}: unsupported content type")
        ids.add(sid); versions.add(vid); filenames.add(fn); out.append(dict(raw))
    return out

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--authorized-public-acquisition",action="store_true")
    p.add_argument("--repo-root",required=True)
    p.add_argument("--private-root",required=True)
    p.add_argument("--inbox-root",required=True)
    p.add_argument("--browser",choices=("auto","chrome","msedge"),default="auto")
    p.add_argument("--headless",action="store_true")
    p.add_argument("--redirect-policy",choices=("exact","same-origin"),default="exact")
    p.add_argument("--challenge-wait-seconds",type=int,default=180)
    p.add_argument("--navigation-timeout-seconds",type=int,default=90)
    p.add_argument("--browser-restart-retries",type=int,default=2)
    p.add_argument("--fresh",action="store_true")
    args=p.parse_args()
    if not args.authorized_public_acquisition:
        print("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH030_BROWSER_CAPTURE=FAIL"); print("ERROR=explicit --authorized-public-acquisition is required"); return 2

    repo=Path(args.repo_root).expanduser().resolve()
    base=import_base(repo)
    private_root=base.assert_outside_repo(Path(args.private_root),repo,"PrivateRoot")
    inbox=base.assert_outside_repo(Path(args.inbox_root),repo,"InboxRoot")
    doc=load_json(repo/QUEUE_REL); queue=validate_queue(doc); inbox.mkdir(parents=True,exist_ok=True)
    journal_path=inbox/"HYDRA_CONSTRAINT_SEMI_B030_BROWSER_CAPTURE_JOURNAL_V001.json"

    if args.fresh:
        for item in queue:
            cp=inbox/item["inbox_filename"]; sp=Path(str(cp)+".capture.json")
            if cp.exists(): cp.unlink()
            if sp.exists(): sp.unlink()
        if journal_path.exists(): journal_path.unlink()

    entries=[]; pending=[]
    for item in queue:
        cp=inbox/item["inbox_filename"]; sp=Path(str(cp)+".capture.json")
        existing=base.validate_existing_pair(item=item,capture_path=cp,sidecar_path=sp,remediation=None)
        if existing is None: pending.append(item)
        else: entries.append(existing)

    write_json(journal_path,{"schema_version":JOURNAL_SCHEMA,"slice_id":EXPECTED_SLICE,"queue_record_id":doc["record_id"],"authoritative":False,"network_acquisition_authorized":True,"historical_backdating_authorized":False,"redirect_policy":args.redirect_policy,"expected_source_count":EXPECTED_COUNT,"entries":entries,"complete":len(pending)==0})
    if not pending:
        print("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH030_BROWSER_CAPTURE=PASS"); print("CAPTURED_OR_RESUMED=38"); print("PENDING=0"); print(f"JOURNAL={journal_path}"); return 0

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc: raise CaptureError(f"Playwright Python client unavailable: {exc}") from exc

    with sync_playwright() as pw:
        context=None; browser_channel=""
        try:
            context,browser_channel=base.launch_context(pw,private_root=private_root,browser=args.browser,headless=args.headless)
            captured={e["source_id"]:e for e in entries}
            for item in queue:
                if item["source_id"] in captured:
                    print(f"RESUME_OK {item['ordinal']:03d}/038 {item['source_id']}"); continue
                attempts=0
                while True:
                    cp=inbox/item["inbox_filename"]; sp=Path(str(cp)+".capture.json")
                    try:
                        row=base.capture_one(context=context,browser_channel=browser_channel,item=item,capture_path=cp,sidecar_path=sp,capture_locator=item["source_locator"],redirect_policy=args.redirect_policy,challenge_wait_seconds=args.challenge_wait_seconds,navigation_timeout_seconds=args.navigation_timeout_seconds)
                        captured[item["source_id"]]=row
                        print(f"CAPTURE_OK {item['ordinal']:03d}/038 {item['source_id']} bytes={row['byte_length']} sha256={row['artifact_sha256']}")
                        break
                    except Exception as exc:
                        if base.is_target_closed_error(exc) and attempts<max(0,args.browser_restart_retries):
                            attempts+=1
                            try: context.close()
                            except Exception: pass
                            context,browser_channel=base.launch_context(pw,private_root=private_root,browser=args.browser,headless=args.headless)
                            print(f"BROWSER_RESTART retry={attempts} source={item['source_id']}")
                            continue
                        raise CaptureError(f"{item['source_id']}: capture failed: {exc}") from exc
                ordered=[captured[q["source_id"]] for q in queue if q["source_id"] in captured]
                write_json(journal_path,{"schema_version":JOURNAL_SCHEMA,"slice_id":EXPECTED_SLICE,"queue_record_id":doc["record_id"],"authoritative":False,"network_acquisition_authorized":True,"historical_backdating_authorized":False,"redirect_policy":args.redirect_policy,"expected_source_count":EXPECTED_COUNT,"entries":ordered,"complete":len(ordered)==EXPECTED_COUNT,"updated_at":utc_timestamp()})
        finally:
            if context is not None:
                try: context.close()
                except Exception: pass
    final=load_json(journal_path).get("entries",[])
    if len(final)!=EXPECTED_COUNT: raise CaptureError(f"capture incomplete: {len(final)}/{EXPECTED_COUNT}")
    print("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH030_BROWSER_CAPTURE=PASS"); print("CAPTURED_OR_RESUMED=38"); print("PENDING=0"); print(f"JOURNAL={journal_path}"); return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except CaptureError as exc:
        print("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH030_BROWSER_CAPTURE=FAIL"); print(f"ERROR={exc}"); raise SystemExit(1)
