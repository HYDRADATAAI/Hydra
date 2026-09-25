#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HYDRA Daily Planner Review Gate — Subtask 9 Reviewable Evidence Trail Acceptance Gate v0.1."""

from __future__ import annotations
import argparse, csv, datetime as dt, json, os, shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

GUARDRAILS = [
    "no market-data scan", "no recursive scan", "no multi-file scan", "no planner/market join",
    "no level-distance calculation", "no price-reaction measurement", "no MFE/MAE calculation",
    "no outcome measurement", "no trade signals", "no queue mutation", "no ML labels",
    "no simulation", "no execution", "no external API calls", "no Asana mutation",
]
BLOCKED_FLAGS = {
    "planner_market_join_allowed": False,
    "simulation_allowed": False,
    "ml_labeling_allowed": False,
    "trade_signal_generation_allowed": False,
}
PLACEHOLDERS = {"", "fill_value_here", "todo", "tbd", "none", "null", "nan", "n/a", "na", "missing", "blank", "placeholder", "unknown", "not provided"}
CONFIDENCE_OK = {"high", "moderate", "low", "unknown", "conflicting", "scaffold-smoke"}

def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def atomic_write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)

def atomic_write_json(path: Path, obj: Any) -> None:
    atomic_write_text(path, json.dumps(obj, indent=2) + "\n")

def atomic_write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)

def read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def as_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, (list, tuple, set)):
        return ",".join(as_text(x) for x in v if as_text(x))
    if isinstance(v, dict):
        return json.dumps(v, sort_keys=True)
    return str(v).strip()

def recursive_find_key(obj: Any, target_key: str) -> Optional[Any]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() == target_key.lower():
                return v
        for v in obj.values():
            found = recursive_find_key(v, target_key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = recursive_find_key(v, target_key)
            if found is not None:
                return found
    return None

def bool_from_any(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return as_text(v).lower() in {"true", "1", "yes", "accepted", "pass"}

def is_missing(v: Any, field: str = "") -> bool:
    txt = as_text(v).lower()
    if field.endswith("confidence"):
        return txt not in CONFIDENCE_OK
    return txt in PLACEHOLDERS

def read_manual_json(path: Optional[Path], fields: List[str]) -> Dict[str, str]:
    if not path:
        return {}
    data = read_json(path)
    if not data:
        raise FileNotFoundError(f"manual_json not found or empty: {path}")
    values: Dict[str, str] = {}
    for f in fields:
        found = recursive_find_key(data, f)
        if found is not None:
            values[f] = as_text(found)
    return values

def read_template_csv(path: Path, fields: List[str]) -> Dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"manual input template not found: {path}")
    values: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = as_text(row.get("field_key"))
            if key in fields:
                values[key] = as_text(row.get("fill_value_here") or row.get("value"))
    return values

def backup_file(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(path.name + f".bak_{stamp}")
    shutil.copy2(path, backup)
    return backup

def print_header(engine_id: str, version: str, hydra_root: Path, mode: str) -> None:
    print(f"[HYDRA] engine_id={engine_id}")
    print(f"[HYDRA] version={version}")
    print(f"[HYDRA] hydra_root={hydra_root}")
    print(f"[HYDRA] mode={mode}")
    print("[HYDRA] guardrails: " + ", ".join(GUARDRAILS))

ENGINE_ID="hydra_daily_planner_review_gate_subtask9_reviewable_evidence_trail_acceptance_gate_v0_1"
VERSION="v0.1"
MODE="NON_MUTATING_DAILY_PLANNER_REVIEW_GATE_SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_ACCEPTANCE_GATE"
PACKET_PARTS=["data","canonical","daily_planner_review_gate_subtask9_reviewable_evidence_trail_v0_1","HYDRA_daily_planner_review_gate_subtask9_reviewable_evidence_trail_packet_v0_1.json"]
OUT_PARENT=Path("data")/"canonical"/"daily_planner_review_gate_subtask9_reviewable_evidence_trail_acceptance_gate_v0_1"
PREFIX="HYDRA_daily_planner_review_gate_subtask9_reviewable_evidence_trail"

def add_check(checks, key, required, ok, value, desc):
    checks.append({"check_key":key,"required":required,"status":"PASS" if ok else ("FAIL_REQUIRED" if required else "WARN"),"value":as_text(value),"description":desc})

def main() -> int:
    p=argparse.ArgumentParser(description=f"{ENGINE_ID} {VERSION}"); p.add_argument("--hydra-root", required=True); p.add_argument("--expected-review-date", default=""); p.add_argument("--expected-instruments", default=""); p.add_argument("--human-accepted", action="store_true"); args=p.parse_args()
    hydra_root=Path(args.hydra_root).expanduser().resolve(); print_header(ENGINE_ID, VERSION, hydra_root, MODE)
    packet_json=hydra_root.joinpath(*PACKET_PARTS); print(f"[HYDRA] packet_json={packet_json}")
    packet=read_json(packet_json) or {}; summary=packet.get("summary",{}); fields=packet.get("fields",{}); checks=[]
    add_check(checks,"packet_exists",True,bool(packet),packet_json,"Subtask 9 packet exists.")
    add_check(checks,"overall_status",True,as_text(summary.get("overall_status"))=="REVIEWABLE_EVIDENCE_TRAIL_PACKET_MATERIALIZED",summary.get("overall_status"),"Materializer status must match.")
    add_check(checks,"section_status_review_ready",True,as_text(summary.get("section_status"))=="REVIEW_READY",summary.get("section_status"),"Section must be REVIEW_READY.")
    add_check(checks,"subtask8_prerequisite_ready",True,bool_from_any(summary.get("subtask8_prerequisite_ready")),summary.get("subtask8_prerequisite_ready"),"Subtask 8 prerequisite must be accepted.")
    add_check(checks,"no_missing_required_fields",True,int(summary.get("missing_required_count",999))==0,summary.get("missing_required_count"),"No missing fields.")
    add_check(checks,"no_validation_errors",True,int(summary.get("validation_error_count",999))==0,summary.get("validation_error_count"),"No validation errors.")
    add_check(checks,"expected_review_date",True,(not args.expected_review_date) or as_text(fields.get("review_date"))==args.expected_review_date,fields.get("review_date"),"Review date matches if provided.")
    if args.expected_instruments:
        expected={x.strip().upper() for x in args.expected_instruments.split(',') if x.strip()}; actual={x.strip().upper() for x in as_text(fields.get('instruments')).split(',') if x.strip()}
        add_check(checks,"expected_instruments",True,expected.issubset(actual),fields.get("instruments"),"Expected instruments must be present.")
    add_check(checks,"human_accepted",True,bool(args.human_accepted),args.human_accepted,"Human acceptance is required.")
    for k,v in BLOCKED_FLAGS.items(): add_check(checks,k,True,v is False,v,"Blocked capability flag must remain false.")
    fail=sum(1 for c in checks if c["required"] and c["status"]!="PASS"); passed=sum(1 for c in checks if c["status"]=="PASS"); warn=sum(1 for c in checks if c["status"]=="WARN")
    complete=fail==0
    overall="SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_ACCEPTED" if complete else ("SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_REVIEW_NOT_ACCEPTABLE" if as_text(summary.get("section_status"))=="REVIEW_READY" else "SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_BLOCKED_NOT_REVIEW_READY")
    next_valid="Proceed to Subtask 10 Explicit blocked / unknown areas materializer. Do not start planner/market join, simulation, ML, or trade signals." if complete else ("Fix failed required gate checks or rerun with --human-accepted after human review. Do not proceed to Subtask 10 until this gate passes." if as_text(summary.get("section_status"))=="REVIEW_READY" else "Fill/fix Subtask 9 Reviewable Evidence Trail inputs and rerun the materializer to REVIEW_READY, then rerun this gate.")
    out_dir=hydra_root/OUT_PARENT; ensure_dir(out_dir); docs=hydra_root/"docs"; ensure_dir(docs)
    result_json=out_dir/f"{PREFIX}_acceptance_gate_result_v0_1.json"; checks_csv=out_dir/f"{PREFIX}_acceptance_gate_checks_v0_1.csv"; manifest_json=out_dir/f"{PREFIX}_acceptance_gate_manifest_v0_1.json"; checkpoint_md=docs/"HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_ACCEPTANCE_CHECKPOINT_V0_1.md"; report_md=docs/"HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_ACCEPTANCE_GATE_REPORT_V0_1.md"; open_commands_txt=out_dir/f"{PREFIX}_acceptance_gate_open_commands_v0_1.txt"
    result={"engine_id":ENGINE_ID,"version":VERSION,"overall_status":overall,"subtask_complete":complete,"content_execution_complete":complete,"human_accepted":bool(args.human_accepted),"pass_count":passed,"fail_required_count":fail,"critical_fail_count":0,"warning_count":warn,**BLOCKED_FLAGS,"next_valid_action":next_valid}
    atomic_write_json(result_json,result); atomic_write_csv(checks_csv,checks,["check_key","required","status","value","description"]); atomic_write_json(manifest_json,{"engine_id":ENGINE_ID,"version":VERSION,"overall_status":overall})
    report = "# HYDRA Daily Planner Review Gate — Subtask 9 Reviewable Evidence Trail Acceptance Gate Report v0.1\n\n" + "\n".join(f"- {k}: `{v}`" for k, v in result.items()) + "\n"
    atomic_write_text(checkpoint_md, report)
    atomic_write_text(report_md, report)
    atomic_write_text(open_commands_txt, f'notepad "{report_md}"\nnotepad "{checks_csv}"\n')
    print("HYDRA DAILY PLANNER REVIEW GATE SUBTASK 9 REVIEWABLE EVIDENCE TRAIL ACCEPTANCE GATE COMPLETE")
    print(f"overall_status: {overall}"); print(f"subtask_complete: {complete}"); print(f"content_execution_complete: {complete}"); print(f"human_accepted: {bool(args.human_accepted)}"); print(f"pass_count: {passed}"); print(f"fail_required_count: {fail}"); print("critical_fail_count: 0"); print(f"warning_count: {warn}")
    for k,v in BLOCKED_FLAGS.items(): print(f"{k}: {v}")
    print(f"result_json: {result_json}"); print(f"checks_csv: {checks_csv}"); print(f"manifest_json: {manifest_json}"); print(f"checkpoint_md: {checkpoint_md}"); print(f"report_md: {report_md}"); print(f"open_commands_txt: {open_commands_txt}"); print(f"next_valid_action: {next_valid}")
    return 0
if __name__=="__main__": raise SystemExit(main())
