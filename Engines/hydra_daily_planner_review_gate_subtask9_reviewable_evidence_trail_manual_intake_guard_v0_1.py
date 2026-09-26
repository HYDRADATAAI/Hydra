#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HYDRA Daily Planner Review Gate — Subtask 9 Reviewable Evidence Trail Manual Intake Guard v0.1."""

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

ENGINE_ID="hydra_daily_planner_review_gate_subtask9_reviewable_evidence_trail_manual_intake_guard_v0_1"
VERSION="v0.1"
MODE="NON_MUTATING_DAILY_PLANNER_REVIEW_GATE_SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_MANUAL_INTAKE_GUARD"
REQUIRED_FIELDS=['review_date', 'instruments', 'sources', 'evidence_trail_source', 'source_artifacts', 'planner_source_references', 'chart_or_screenshot_references', 'reviewed_section_references', 'claim_to_evidence_mapping', 'missing_evidence_notes', 'conflicting_evidence_notes', 'audit_replay_requirements', 'evidence_confidence', 'allowed_inferences', 'not_allowed_inferences']
TEMPLATE_PARTS=["data","canonical","daily_planner_review_gate_subtask9_reviewable_evidence_trail_v0_1","HYDRA_daily_planner_review_gate_subtask9_reviewable_evidence_trail_manual_input_template_v0_1.csv"]
OUT_PARENT=Path("data")/"canonical"/"daily_planner_review_gate_subtask9_reviewable_evidence_trail_manual_intake_guard_v0_1"
PREFIX="HYDRA_daily_planner_review_gate_subtask9_reviewable_evidence_trail"

def main() -> int:
    p=argparse.ArgumentParser(description=f"{ENGINE_ID} {VERSION}"); p.add_argument("--hydra-root", required=True); args=p.parse_args()
    hydra_root=Path(args.hydra_root).expanduser().resolve(); print_header(ENGINE_ID, VERSION, hydra_root, MODE)
    template=hydra_root.joinpath(*TEMPLATE_PARTS); print(f"[HYDRA] input_csv={template}")
    values=read_template_csv(template, REQUIRED_FIELDS); rows=[]
    for f in REQUIRED_FIELDS:
        val=values.get(f,""); missing=is_missing(val,f); rows.append({"field_key": f, "value": val, "required": True, "status": "PASS" if not missing else "FAIL_REQUIRED", "populated": not missing})
    passed=sum(1 for r in rows if r["status"]=="PASS"); fail=len(REQUIRED_FIELDS)-passed; ready=fail==0
    status="SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_MANUAL_INPUT_READY" if ready else "SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_MANUAL_INPUT_BLOCKED"
    out_dir=hydra_root/OUT_PARENT; ensure_dir(out_dir); docs=hydra_root/"docs"; ensure_dir(docs)
    draft_json=out_dir/f"{PREFIX}_manual_input_draft_v0_1.json"; ready_json=out_dir/f"{PREFIX}_manual_input_ready_v0_1.json"; result_json=out_dir/f"{PREFIX}_manual_intake_guard_result_v0_1.json"; checks_csv=out_dir/f"{PREFIX}_manual_intake_guard_checks_v0_1.csv"; fields_csv=out_dir/f"{PREFIX}_manual_intake_guard_fields_v0_1.csv"; manifest_json=out_dir/f"{PREFIX}_manual_intake_guard_manifest_v0_1.json"; checkpoint_md=docs/"HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_MANUAL_INTAKE_GUARD_CHECKPOINT_V0_1.md"; report_md=docs/"HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_MANUAL_INTAKE_GUARD_REPORT_V0_1.md"; next_commands_txt=out_dir/f"{PREFIX}_manual_intake_guard_next_commands_v0_1.txt"; open_commands_txt=out_dir/f"{PREFIX}_manual_intake_guard_open_commands_v0_1.txt"
    draft={"engine_id":ENGINE_ID,"version":VERSION,"fields":values,"field_rows":rows}; atomic_write_json(draft_json,draft)
    if ready: atomic_write_json(ready_json,draft)
    result={"engine_id":ENGINE_ID,"version":VERSION,"overall_status":status,"ready_for_materializer":ready,"required_fields_count":len(REQUIRED_FIELDS),"populated_required_count":passed,"missing_required_count":fail,"pass_count":passed,"fail_required_count":fail,"critical_fail_count":0,"warning_count":0,**BLOCKED_FLAGS}
    atomic_write_json(result_json,result); atomic_write_csv(checks_csv,rows,["field_key","value","required","status","populated"]); atomic_write_csv(fields_csv,rows,["field_key","value","required","status","populated"]); atomic_write_json(manifest_json,{"engine_id":ENGINE_ID,"version":VERSION,"overall_status":status})
    atomic_write_text(report_md, "# HYDRA Daily Planner Review Gate — Subtask 9 Reviewable Evidence Trail Manual Intake Guard Report v0.1\n\n" + "\n".join(f"- {k}: `{v}`" for k, v in result.items()) + "\n")
    atomic_write_text(checkpoint_md, report_md.read_text(encoding="utf-8"))
    cmd = f'python "{hydra_root}\\engines\\hydra_daily_planner_review_gate_subtask9_reviewable_evidence_trail_materializer_v0_1.py" --hydra-root "{hydra_root}" --manual-json "{ready_json}"\n' if ready else ""
    atomic_write_text(next_commands_txt, cmd)
    atomic_write_text(open_commands_txt, f'notepad "{report_md}"\nnotepad "{fields_csv}"\n')
    print("HYDRA DAILY PLANNER REVIEW GATE SUBTASK 9 REVIEWABLE EVIDENCE TRAIL MANUAL INTAKE GUARD COMPLETE")
    print(f"overall_status: {status}"); print(f"ready_for_materializer: {ready}"); print(f"required_fields_count: {len(REQUIRED_FIELDS)}"); print(f"populated_required_count: {passed}"); print(f"missing_required_count: {fail}"); print(f"pass_count: {passed}"); print(f"fail_required_count: {fail}"); print("critical_fail_count: 0"); print("warning_count: 0")
    for k,v in BLOCKED_FLAGS.items(): print(f"{k}: {v}")
    print(f"draft_json: {draft_json}");
    if ready: print(f"ready_manual_json: {ready_json}")
    print(f"result_json: {result_json}"); print(f"checks_csv: {checks_csv}"); print(f"fields_csv: {fields_csv}"); print(f"manifest_json: {manifest_json}"); print(f"checkpoint_md: {checkpoint_md}"); print(f"report_md: {report_md}"); print(f"next_commands_txt: {next_commands_txt}"); print(f"open_commands_txt: {open_commands_txt}"); print("next_valid_action: "+("Rerun Subtask 9 materializer with the emitted manual JSON, then run/build the Subtask 9 acceptance gate." if ready else "Fill missing/failed manual fields, rerun this guard, then rerun Subtask 9 materializer only when READY."))
    return 0
if __name__=="__main__": raise SystemExit(main())
