#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HYDRA Subtask 7 Invalidations Acceptance Gate v0.1."""

from __future__ import annotations
import argparse
import csv
import datetime as dt
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

GUARDRAILS = [
    "no market-data scan",
    "no recursive scan",
    "no multi-file scan",
    "no planner/market join",
    "no level-distance calculation",
    "no price-reaction measurement",
    "no MFE/MAE calculation",
    "no outcome measurement",
    "no trade signals",
    "no queue mutation",
    "no ML labels",
    "no simulation",
    "no execution",
    "no external API calls",
    "no Asana mutation",
]
BLOCKED_FLAGS = {
    "planner_market_join_allowed": False,
    "simulation_allowed": False,
    "ml_labeling_allowed": False,
    "trade_signal_generation_allowed": False,
}
PLACEHOLDER_VALUES = {
    "", "fill_value_here", "todo", "tbd", "none", "null", "nan", "n/a", "na", "missing", "blank",
    "<fill>", "<todo>", "placeholder", "not provided", "not_provided", "no context", "no context confirmed",
    "unavailable", "not available",
}
ACCEPTED_CONFIDENCE = {"high", "moderate", "low", "unknown", "conflicting", "scaffold-smoke"}
FORBIDDEN_CONTENT_PATTERNS = [
    r"\bplanner/market\s+join\b",
    r"\bmarket[- ]data\s+join\b",
    r"\blevel[- ]distance\b",
    r"\bprice[- ]reaction\b",
    r"\bmfe\b",
    r"\bmae\b",
    r"\boutcome\s+measurement\b",
    r"\btrade\s+signal(?:s)?\b",
    r"\bgo\s+long\b",
    r"\bgo\s+short\b",
    r"\bbuy\s+(?:here|now|signal)\b",
    r"\bsell\s+(?:here|now|signal)\b",
    r"\bqueue\s+mutation\b",
    r"\bml\s+label(?:s|ing)?\b",
    r"\bsimulation\b",
    r"\bexecution\b",
]

def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def normalize_hydra_root(path_text: str) -> Path:
    return Path(path_text).expanduser().resolve()

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def atomic_write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")
    os.replace(tmp, path)

def atomic_write_json(path: Path, obj: Any) -> None:
    atomic_write_text(path, json.dumps(obj, indent=2, sort_keys=False) + "\n")

def atomic_write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    os.replace(tmp, path)

def read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        return ",".join(str(x).strip() for x in value if str(x).strip())
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value).strip()

def lower_text(value: Any) -> str:
    return as_text(value).lower().strip()

def is_missing(value: Any, field_key: str = "") -> bool:
    txt = lower_text(value)
    if txt in PLACEHOLDER_VALUES:
        return True
    if field_key.endswith("confidence") and txt not in ACCEPTED_CONFIDENCE:
        return True
    if txt == "unknown" and not field_key.endswith("confidence"):
        return True
    return False

def recursive_find_key(obj: Any, target_key: str) -> Optional[Any]:
    target_norm = target_key.lower()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() == target_norm:
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

def bool_from_any(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return lower_text(value) in {"true", "1", "yes", "y", "accepted", "pass"}

def read_manual_json(path: Optional[Path], required_fields: List[str]) -> Dict[str, str]:
    if not path:
        return {}
    data = read_json(path)
    if not data:
        raise FileNotFoundError(f"manual_json not found or empty: {path}")
    values: Dict[str, str] = {}
    for field in required_fields:
        found = recursive_find_key(data, field)
        if found is not None:
            values[field] = as_text(found)
    def scan_rows(obj: Any) -> None:
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    key = item.get("field_key") or item.get("field") or item.get("key")
                    if key in required_fields:
                        val = item.get("value")
                        if val is None:
                            val = item.get("fill_value_here")
                        if val is None:
                            val = item.get("field_value")
                        values[str(key)] = as_text(val)
                    scan_rows(item)
        elif isinstance(obj, dict):
            for v in obj.values():
                scan_rows(v)
    scan_rows(data)
    return values

def read_manual_template_csv(path: Path) -> Tuple[List[Dict[str, str]], str]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with open(path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    fill_col = "fill_value_here" if rows and "fill_value_here" in rows[0] else "value"
    return rows, fill_col

def extract_values_from_template(rows: List[Dict[str, str]], fill_col: str) -> Dict[str, str]:
    values = {}
    for row in rows:
        key = as_text(row.get("field_key") or row.get("field") or row.get("key"))
        if key:
            values[key] = as_text(row.get(fill_col, ""))
    return values

def forbidden_hits(values: Dict[str, Any], allowed_blocked_field: str = "not_allowed_inferences") -> List[str]:
    hits = []
    for field, value in values.items():
        if field == allowed_blocked_field:
            continue
        txt = as_text(value).lower()
        for pat in FORBIDDEN_CONTENT_PATTERNS:
            if re.search(pat, txt, flags=re.IGNORECASE):
                hits.append(f"{field}:{pat}")
    return hits

def print_header(engine_id: str, version: str, hydra_root: Path, mode: str) -> None:
    print(f"[HYDRA] engine_id={engine_id}")
    print(f"[HYDRA] version={version}")
    print(f"[HYDRA] hydra_root={hydra_root}")
    print(f"[HYDRA] mode={mode}")
    print("[HYDRA] guardrails: " + ", ".join(GUARDRAILS))

ENGINE_ID = "hydra_daily_planner_review_gate_subtask7_invalidations_acceptance_gate_v0_1"
VERSION = "v0.1"
MODE = "NON_MUTATING_DAILY_PLANNER_REVIEW_GATE_SUBTASK7_INVALIDATIONS_ACCEPTANCE_GATE"
PACKET_PATH_PARTS = ["data","canonical","daily_planner_review_gate_subtask7_invalidations_v0_1","HYDRA_daily_planner_review_gate_subtask7_invalidations_packet_v0_1.json"]
OUT_PARENT = Path("data") / "canonical" / "daily_planner_review_gate_subtask7_invalidations_acceptance_gate_v0_1"
REQUIRED_STATUS = "REVIEW_READY"
ACCEPTED_STATUS = "SUBTASK7_INVALIDATIONS_ACCEPTED"

def parse_args(argv=None):
    p = argparse.ArgumentParser(description=f"{ENGINE_ID} {VERSION}")
    p.add_argument("--hydra-root", required=True)
    p.add_argument("--expected-review-date", default="")
    p.add_argument("--expected-instruments", default="")
    p.add_argument("--human-accepted", action="store_true")
    return p.parse_args(argv)

def main(argv=None):
    args = parse_args(argv); hydra_root = normalize_hydra_root(args.hydra_root)
    print_header(ENGINE_ID, VERSION, hydra_root, MODE)
    packet_json = hydra_root.joinpath(*PACKET_PATH_PARTS)
    print(f"[HYDRA] packet_json={packet_json}")
    packet = read_json(packet_json) or {}
    summary = packet.get("summary", {})
    fields = packet.get("fields", {})
    checks=[]; fail=0; passed=0; warn=0
    def add(name, required, ok, value, desc):
        nonlocal fail, passed, warn
        status = "PASS" if ok else ("FAIL_REQUIRED" if required else "WARN")
        if ok: passed += 1
        elif required: fail += 1
        else: warn += 1
        checks.append({"check_key": name, "required": required, "status": status, "value": as_text(value), "description": desc})
    add("packet_exists", True, bool(packet), str(packet_json), "Subtask 7 packet exists.")
    add("overall_status", True, as_text(summary.get("overall_status")) == "INVALIDATIONS_PACKET_MATERIALIZED", summary.get("overall_status"), "Materializer overall status must match.")
    add("section_status_review_ready", True, as_text(summary.get("section_status")) == REQUIRED_STATUS, summary.get("section_status"), "Section must be REVIEW_READY before acceptance.")
    add("subtask6_prerequisite_ready", True, bool_from_any(summary.get("subtask6_prerequisite_ready")), summary.get("subtask6_prerequisite_ready"), "Subtask 6 prerequisite must be accepted.")
    add("no_missing_required_fields", True, int(summary.get("missing_required_count", 999)) == 0, summary.get("missing_required_count"), "No missing fields allowed.")
    add("no_validation_errors", True, int(summary.get("validation_error_count", 999)) == 0, summary.get("validation_error_count"), "No validation errors allowed.")
    add("expected_review_date", True, (not args.expected_review_date) or as_text(fields.get("review_date")) == args.expected_review_date, fields.get("review_date"), "Review date must match expected if provided.")
    if args.expected_instruments:
        expected = {x.strip().upper() for x in args.expected_instruments.split(',') if x.strip()}
        actual = {x.strip().upper() for x in as_text(fields.get('instruments')).split(',') if x.strip()}
        add("expected_instruments", True, expected.issubset(actual), fields.get("instruments"), "Expected instruments must be present.")
    add("human_accepted", True, bool(args.human_accepted), args.human_accepted, "Human acceptance is required.")
    for key, value in BLOCKED_FLAGS.items():
        add(key, True, value is False, value, "Blocked capability flag must remain false.")
    subtask_complete = fail == 0
    overall = ACCEPTED_STATUS if subtask_complete else ("SUBTASK7_INVALIDATIONS_REVIEW_NOT_ACCEPTABLE" if as_text(summary.get("section_status")) == REQUIRED_STATUS else "SUBTASK7_INVALIDATIONS_BLOCKED_NOT_REVIEW_READY")
    out_dir = hydra_root / OUT_PARENT; ensure_dir(out_dir)
    result_json = out_dir / "HYDRA_daily_planner_review_gate_subtask7_invalidations_acceptance_gate_result_v0_1.json"
    checks_csv = out_dir / "HYDRA_daily_planner_review_gate_subtask7_invalidations_acceptance_gate_checks_v0_1.csv"
    manifest_json = out_dir / "HYDRA_daily_planner_review_gate_subtask7_invalidations_acceptance_gate_manifest_v0_1.json"
    checkpoint_md = hydra_root / "docs" / "HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK7_INVALIDATIONS_ACCEPTANCE_CHECKPOINT_V0_1.md"
    report_md = hydra_root / "docs" / "HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK7_INVALIDATIONS_ACCEPTANCE_GATE_REPORT_V0_1.md"
    open_commands_txt = out_dir / "HYDRA_daily_planner_review_gate_subtask7_invalidations_acceptance_gate_open_commands_v0_1.txt"
    next_valid = "Proceed to Subtask 8 If-this-then-that scenario map materializer. Do not start planner/market join, simulation, ML, or trade signals." if subtask_complete else ("Fix failed required gate checks or rerun with --human-accepted after human review. Do not proceed to Subtask 8 until this gate passes." if as_text(summary.get("section_status")) == REQUIRED_STATUS else "Fill/fix Subtask 7 Invalidations inputs and rerun the materializer to REVIEW_READY, then rerun this gate.")
    result = {"engine_id": ENGINE_ID, "version": VERSION, "overall_status": overall, "subtask_complete": subtask_complete, "content_execution_complete": subtask_complete, "human_accepted": bool(args.human_accepted), "pass_count": passed, "fail_required_count": fail, "critical_fail_count": 0, "warning_count": warn, **BLOCKED_FLAGS, "next_valid_action": next_valid}
    atomic_write_json(result_json, result)
    atomic_write_csv(checks_csv, checks, ["check_key","required","status","value","description"])
    atomic_write_json(manifest_json, {"engine_id": ENGINE_ID, "version": VERSION, "overall_status": overall, "artifacts": {"result_json": str(result_json), "checks_csv": str(checks_csv)}})
    report = "# HYDRA Daily Planner Review Gate — Subtask 7 Invalidations Acceptance Gate Report v0.1\n\n" + "\n".join(f"- {k}: `{v}`" for k,v in result.items()) + "\n"
    atomic_write_text(checkpoint_md, report); atomic_write_text(report_md, report)
    atomic_write_text(open_commands_txt, f'notepad "{report_md}"\nnotepad "{checks_csv}"\n')
    print("HYDRA DAILY PLANNER REVIEW GATE SUBTASK 7 INVALIDATIONS ACCEPTANCE GATE COMPLETE")
    print(f"overall_status: {overall}")
    print(f"subtask_complete: {subtask_complete}")
    print(f"content_execution_complete: {subtask_complete}")
    print(f"human_accepted: {bool(args.human_accepted)}")
    print(f"pass_count: {passed}")
    print(f"fail_required_count: {fail}")
    print("critical_fail_count: 0")
    print(f"warning_count: {warn}")
    for key, value in BLOCKED_FLAGS.items(): print(f"{key}: {value}")
    print(f"result_json: {result_json}")
    print(f"checks_csv: {checks_csv}")
    print(f"manifest_json: {manifest_json}")
    print(f"checkpoint_md: {checkpoint_md}")
    print(f"report_md: {report_md}")
    print(f"open_commands_txt: {open_commands_txt}")
    print(f"next_valid_action: {next_valid}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
