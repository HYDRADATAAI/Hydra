#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HYDRA Daily Planner Review Gate — Subtask 9 Reviewable Evidence Trail Manual Template Patcher v0.1."""

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

ENGINE_ID="hydra_daily_planner_review_gate_subtask9_reviewable_evidence_trail_manual_template_patcher_v0_1"
VERSION="v0.1"
MODE="CONTROLLED_SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_MANUAL_INPUT_TEMPLATE_PATCHER_ONLY"
REQUIRED_FIELDS=['review_date', 'instruments', 'sources', 'evidence_trail_source', 'source_artifacts', 'planner_source_references', 'chart_or_screenshot_references', 'reviewed_section_references', 'claim_to_evidence_mapping', 'missing_evidence_notes', 'conflicting_evidence_notes', 'audit_replay_requirements', 'evidence_confidence', 'allowed_inferences', 'not_allowed_inferences']
SMOKE={'review_date': '2026-05-24', 'instruments': 'ES,NQ', 'sources': 'Subtask 8 accepted if-this-then-that scenario map packet; Subtask 9 scaffold-smoke manual patch', 'evidence_trail_source': 'Procedural scaffold-smoke source only; real evidence artifacts were not audited in this packet.', 'source_artifacts': 'Scaffold-smoke only: prior accepted Review Gate packet artifacts are referenced structurally; no files were broadly scanned.', 'planner_source_references': 'Scaffold-smoke only: planner references are represented as required placeholders, not real reviewed planner claims.', 'chart_or_screenshot_references': 'Scaffold-smoke only: chart/screenshot references are not required for plumbing proof and remain non-substantive.', 'reviewed_section_references': 'Subtasks 1 through 8 accepted scaffold-smoke packets are the structural references for this evidence trail.', 'claim_to_evidence_mapping': 'Scaffold-smoke only: each review claim must eventually map to source artifact, section reference, and human-review note.', 'missing_evidence_notes': 'Real trading-day evidence is not attached in this scaffold-smoke packet; missing evidence must be marked explicitly in production review.', 'conflicting_evidence_notes': 'No real conflicting evidence evaluated in scaffold-smoke; production packets must preserve conflicts instead of resolving by assumption.', 'audit_replay_requirements': 'A future reviewer must be able to open source artifacts, packet JSON, packet markdown, and acceptance checks to replay the review path.', 'evidence_confidence': 'scaffold-smoke', 'allowed_inferences': 'Hydra may infer that reviewable evidence-trail fields are structurally represented in Review Gate plumbing only.', 'not_allowed_inferences': 'Hydra may not infer planner/market join readiness, level-distance results, price-reaction results, MFE/MAE, outcome quality, trade signals, queue mutation readiness, ML labels, simulation readiness, execution logic, or real trading edge from scaffold-smoke data.'}
OUT_PARENT=Path("data")/"canonical"/"daily_planner_review_gate_subtask9_reviewable_evidence_trail_manual_template_patcher_v0_1"
TEMPLATE_PARTS=["data","canonical","daily_planner_review_gate_subtask9_reviewable_evidence_trail_v0_1","HYDRA_daily_planner_review_gate_subtask9_reviewable_evidence_trail_manual_input_template_v0_1.csv"]
PREFIX="HYDRA_daily_planner_review_gate_subtask9_reviewable_evidence_trail"

def main() -> int:
    p=argparse.ArgumentParser(description=f"{ENGINE_ID} {VERSION}")
    p.add_argument("--hydra-root", required=True); p.add_argument("--preset", default="scaffold-smoke")
    args=p.parse_args(); hydra_root=Path(args.hydra_root).expanduser().resolve(); print_header(ENGINE_ID, VERSION, hydra_root, MODE)
    if args.preset != "scaffold-smoke": raise ValueError("Only --preset scaffold-smoke is supported in v0.1")
    template=hydra_root.joinpath(*TEMPLATE_PARTS); print(f"[HYDRA] input_csv={template}")
    rows=[]
    if template.exists():
        with open(template,"r",encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    if not rows: rows=[{"field_key": f, "required": True, "fill_value_here": "", "description": "", "accepted_values_or_notes": ""} for f in REQUIRED_FIELDS]
    backup=backup_file(template); changed=0; seen=set(); out=[]
    for row in rows:
        key=as_text(row.get("field_key"))
        if key in REQUIRED_FIELDS:
            new=SMOKE.get(key, "")
            if as_text(row.get("fill_value_here")) != new: changed += 1
            row["fill_value_here"] = new; seen.add(key)
        out.append(row)
    for f in REQUIRED_FIELDS:
        if f not in seen:
            out.append({"field_key": f, "required": True, "fill_value_here": SMOKE.get(f,""), "description": "", "accepted_values_or_notes": ""}); changed += 1
    atomic_write_csv(template, out, ["field_key","required","fill_value_here","description","accepted_values_or_notes"])
    values={r["field_key"]: r.get("fill_value_here","") for r in out if r.get("field_key") in REQUIRED_FIELDS}
    fail=sum(1 for f in REQUIRED_FIELDS if is_missing(values.get(f,""), f)); passed=len(REQUIRED_FIELDS)-fail; ready=fail==0
    status="SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_MANUAL_TEMPLATE_PATCHED_READY_FOR_INTAKE_GUARD" if ready else "SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_MANUAL_TEMPLATE_PATCHED_BUT_NOT_READY"
    out_dir=hydra_root/OUT_PARENT; ensure_dir(out_dir); docs=hydra_root/"docs"; ensure_dir(docs)
    result_json=out_dir/f"{PREFIX}_manual_template_patcher_result_v0_1.json"; fields_csv=out_dir/f"{PREFIX}_manual_template_patcher_fields_v0_1.csv"; manifest_json=out_dir/f"{PREFIX}_manual_template_patcher_manifest_v0_1.json"; report_md=docs/"HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_MANUAL_TEMPLATE_PATCHER_REPORT_V0_1.md"; next_commands_txt=out_dir/f"{PREFIX}_manual_template_patcher_next_commands_v0_1.txt"; open_commands_txt=out_dir/f"{PREFIX}_manual_template_patcher_open_commands_v0_1.txt"
    result={"engine_id":ENGINE_ID,"version":VERSION,"overall_status":status,"template_patched":True,"ready_for_intake_guard":ready,"preset":args.preset,"changed_fields_count":changed,"pass_count":passed,"fail_required_count":fail,"critical_fail_count":0,"warning_count":0,**BLOCKED_FLAGS}
    atomic_write_json(result_json,result); atomic_write_csv(fields_csv,[{"field_key": f, "value": values.get(f,""), "status":"PASS" if not is_missing(values.get(f,""), f) else "FAIL_REQUIRED"} for f in REQUIRED_FIELDS],["field_key","value","status"]); atomic_write_json(manifest_json,{"engine_id":ENGINE_ID,"version":VERSION,"overall_status":status})
    atomic_write_text(report_md, "# HYDRA Daily Planner Review Gate — Subtask 9 Reviewable Evidence Trail Manual Template Patcher Report v0.1\n\n" + "\n".join(f"- {k}: `{v}`" for k, v in result.items()) + "\n")
    atomic_write_text(next_commands_txt, f'python "{hydra_root}\\engines\\hydra_daily_planner_review_gate_subtask9_reviewable_evidence_trail_manual_intake_guard_v0_1.py" --hydra-root "{hydra_root}"\n')
    atomic_write_text(open_commands_txt, f'notepad "{report_md}"\nnotepad "{template}"\n')
    print("HYDRA DAILY PLANNER REVIEW GATE SUBTASK 9 REVIEWABLE EVIDENCE TRAIL MANUAL TEMPLATE PATCHER COMPLETE")
    print(f"overall_status: {status}"); print("template_patched: True"); print(f"ready_for_intake_guard: {ready}"); print(f"preset: {args.preset}"); print(f"changed_fields_count: {changed}"); print(f"pass_count: {passed}"); print(f"fail_required_count: {fail}"); print("critical_fail_count: 0"); print("warning_count: 0")
    for k,v in BLOCKED_FLAGS.items(): print(f"{k}: {v}")
    print(f"manual_template_csv: {template}"); print(f"backup_csv: {backup if backup else ''}"); print(f"result_json: {result_json}"); print(f"patched_fields_csv: {fields_csv}"); print(f"manifest_json: {manifest_json}"); print(f"report_md: {report_md}"); print(f"next_commands_txt: {next_commands_txt}"); print(f"open_commands_txt: {open_commands_txt}"); print("next_valid_action: Rerun the Subtask 9 manual intake guard. If ready_for_materializer=True, rerun the Subtask 9 materializer with the emitted ready JSON.")
    return 0
if __name__=="__main__": raise SystemExit(main())
