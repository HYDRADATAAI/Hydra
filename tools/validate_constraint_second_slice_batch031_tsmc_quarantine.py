#!/usr/bin/env python3
"""Validate Batch031 direct-TSMC provider quarantine and retained-source identity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

QUEUE_REL=Path("docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json")
QUAR_REL=Path("docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_TSMC_DIRECT_PROVIDER_QUARANTINE_V001_20260928.json")
PREV_REL=Path("docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V002_20260927.json")
EXPECTED_QUARANTINED={
    "SRC-SEMI-B020-TSMC-ARIZONA-ANNOUNCEMENT-2020-05-15",
    "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20",
    "SRC-SEMI-B022-TSMC-2025-ANNUAL-EQUIPMENT-RISK",
    "SRC-SEMI-B022-TSMC-Q2-2026-TRANSCRIPT-2026-07-16",
    "SRC-SEMI-TSMC-ANNUAL-REPORT-2023",
    "SRC-SEMI-TSMC-ANNUAL-REPORT-2024",
    "SRC-SEMI-TSMC-AP6-OPENING-2023-06-08",
    "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17",
}
RETAINED_TSMC_CONTEXT={
    "SRC-SEMI-B021-APS-BISCUIT-FLATS-TSMC-2021-06",
    "SRC-SEMI-B021-AZCC-TSMC-POWER-ORDER-2021-09-09",
}
IDENTITY_FIELDS=("capture_intent_id","source_version_id","source_locator","inbox_filename","content_type_hint")

class ValidationError(RuntimeError):
    pass

def load(path:Path):
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationError(f"unable to load JSON: {path}") from exc
    if not isinstance(value,dict):
        raise ValidationError(f"JSON root must be object: {path}")
    return value

def require(condition:bool,message:str):
    if not condition:
        raise ValidationError(message)

def direct_tsmc(locator:str)->bool:
    host=(urlparse(locator).hostname or "").lower()
    return host=="tsmc.com" or host.endswith(".tsmc.com")

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root",default=".")
    args=ap.parse_args()
    root=Path(args.repo_root).resolve()
    queue=load(root/QUEUE_REL)
    quarantine=load(root/QUAR_REL)
    predecessor=load(root/PREV_REL)

    rows=queue.get("queue")
    require(isinstance(rows,list) and len(rows)==30,"Batch031 queue must contain exactly 30 sources")
    require(queue.get("source_count")==30,"Batch031 source_count must be 30")
    require(queue.get("predecessor_queue")==predecessor.get("record_id"),"Batch031 predecessor queue mismatch")
    require(queue.get("predecessor_queue_mutation")=="REMOVE_DIRECT_TSMC_PROVIDER_SOURCES_ONLY","Batch031 mutation policy drifted")
    require(queue.get("provider_exclusion_policy")=="MICRON_AND_DIRECT_TSMC_PROVIDER_CAPTURE_EXCLUDED_FROM_ACTIVE_CAPTURE","Batch031 provider exclusion policy drifted")
    require(queue.get("inherited_inbox_policy")=="REUSE_VALID_BATCH030_CAPTURE_PAIRS_FOR_RETAINED_SOURCE_IDENTITIES","Batch031 inherited inbox policy drifted")
    require(queue.get("release_id")=="REL-SEMI-B031-V001","Batch031 release id drifted")
    require(queue.get("newly_quarantined_direct_tsmc_source_count")==8,"Batch031 TSMC quarantine count drifted")

    prev_rows=predecessor.get("queue")
    require(isinstance(prev_rows,list) and len(prev_rows)==38,"Batch030 predecessor queue must contain 38 sources")
    prev={row["source_id"]:row for row in prev_rows}
    ids=[row.get("source_id") for row in rows]
    require(len(ids)==len(set(ids)),"Batch031 duplicate source_id")
    require([row.get("ordinal") for row in rows]==list(range(1,31)),"Batch031 ordinals must be contiguous 1..30")
    require(not (set(ids)&EXPECTED_QUARANTINED),"direct TSMC source re-entered active Batch031 queue")
    require(RETAINED_TSMC_CONTEXT.issubset(set(ids)),"independent primary records about TSMC were incorrectly removed")

    for row in rows:
        sid=row.get("source_id")
        require(isinstance(sid,str) and sid in prev,f"unknown retained source: {sid}")
        require(str(row.get("publisher") or "").strip().upper()!="TSMC",f"{sid}: TSMC publisher forbidden")
        require(not direct_tsmc(str(row.get("source_locator") or "")),f"{sid}: direct TSMC locator forbidden")
        require("MICRON" not in sid.upper(),f"{sid}: Micron source forbidden")
        for field in IDENTITY_FIELDS:
            require(row.get(field)==prev[sid].get(field),f"{sid}: retained identity field drifted: {field}")

    qrows=quarantine.get("quarantined_sources")
    require(isinstance(qrows,list) and len(qrows)==8,"Batch031 quarantine must contain exactly 8 sources")
    qids={row.get("source_id") for row in qrows}
    require(qids==EXPECTED_QUARANTINED,"Batch031 quarantine membership drifted")
    require(quarantine.get("policy")=="DIRECT_TSMC_PROVIDER_CAPTURE_DISABLED","Batch031 quarantine policy drifted")
    require(quarantine.get("provenance_preserved") is True,"Batch031 quarantine must preserve provenance")
    require(quarantine.get("historical_backdating_authorized") is False,"Batch031 quarantine may not authorize backdating")
    require(set(quarantine.get("retained_non_tsmc_primary_records_about_tsmc") or [])==RETAINED_TSMC_CONTEXT,"Batch031 retained TSMC-context records drifted")
    for row in qrows:
        sid=row["source_id"]
        require(sid in prev,f"quarantined source missing from predecessor: {sid}")
        require(row.get("source_version_id")==prev[sid].get("source_version_id"),f"{sid}: quarantined version drifted")
        require(row.get("source_locator")==prev[sid].get("source_locator"),f"{sid}: quarantined locator drifted")
        require(row.get("disposition")=="QUARANTINED_DIRECT_TSMC_PROVIDER",f"{sid}: quarantine disposition drifted")

    print("BATCH031_TSMC_PROVIDER_QUARANTINE=PASS")
    print("ACTIVE_SOURCES=30")
    print("DIRECT_TSMC_QUARANTINED=8")
    print("RETAINED_INDEPENDENT_TSMC_CONTEXT=2")
    print("PROVENANCE_PRESERVED=YES")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print("BATCH031_TSMC_PROVIDER_QUARANTINE=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
