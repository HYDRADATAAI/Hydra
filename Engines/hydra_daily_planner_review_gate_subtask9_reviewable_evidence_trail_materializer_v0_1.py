#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HYDRA Daily Planner Review Gate — Subtask 9 Reviewable Evidence Trail Materializer v0.1."""

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

ENGINE_ID = "hydra_daily_planner_review_gate_subtask9_reviewable_evidence_trail_materializer_v0_1"
VERSION = "v0.1"
MODE = "NON_MUTATING_DAILY_PLANNER_REVIEW_GATE_SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL_MATERIALIZER"
REQUIRED_FIELDS = ['review_date', 'instruments', 'sources', 'evidence_trail_source', 'source_artifacts', 'planner_source_references', 'chart_or_screenshot_references', 'reviewed_section_references', 'claim_to_evidence_mapping', 'missing_evidence_notes', 'conflicting_evidence_notes', 'audit_replay_requirements', 'evidence_confidence', 'allowed_inferences', 'not_allowed_inferences']
FIELD_DESCRIPTIONS = {'review_date': 'Trading/review date for this Review Gate packet.', 'instruments': 'Instrument list covered by this reviewable evidence trail, e.g. ES,NQ.', 'sources': 'Reviewed source(s) used to populate the evidence-trail section.', 'evidence_trail_source': 'Where evidence-trail requirements came from: planner text, screenshots, manual notes, scaffold-smoke, etc.', 'source_artifacts': 'Artifacts/files/reports that support the reviewed planner packet; no broad scan or content extraction.', 'planner_source_references': 'References to planner text, plan screenshots, Asana notes, or manual packet sections.', 'chart_or_screenshot_references': 'References to chart/screenshot evidence if present; may be missing or scaffold-smoke.', 'reviewed_section_references': 'Which prior Review Gate sections this evidence trail supports or cites.', 'claim_to_evidence_mapping': 'Mapping between key planner claims and supporting review evidence.', 'missing_evidence_notes': 'Explicit notes for missing evidence that cannot yet be inferred.', 'conflicting_evidence_notes': 'Explicit notes for evidence conflicts, ambiguity, or unresolved contradictions.', 'audit_replay_requirements': 'What must be available later for a human/agent to replay and audit the review decision.', 'evidence_confidence': 'High, moderate, low, unknown, conflicting, or scaffold-smoke.', 'allowed_inferences': 'What Hydra may infer from this evidence-trail section without measuring outcomes or issuing signals.', 'not_allowed_inferences': 'What Hydra may not infer yet: no joins, level-distance calculations, reactions, MFE/MAE, signals, simulation, ML labels, execution.'}
OUT_DIR = Path("data") / "canonical" / "daily_planner_review_gate_subtask9_reviewable_evidence_trail_v0_1"
PREFIX = "HYDRA_daily_planner_review_gate_subtask9_reviewable_evidence_trail"
DOC_PREFIX = "HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK9_REVIEWABLE_EVIDENCE_TRAIL"
PREV_GATE_DIR = Path("data") / "canonical" / "daily_planner_review_gate_subtask8_if_this_then_that_scenario_map_acceptance_gate_v0_1"
PREV_GATE_FILE = "HYDRA_daily_planner_review_gate_subtask8_if_this_then_that_scenario_map_acceptance_gate_result_v0_1.json"
PREV_PACKET_DIR = Path("data") / "canonical" / "daily_planner_review_gate_subtask8_if_this_then_that_scenario_map_v0_1"
PREV_PACKET_FILE = "HYDRA_daily_planner_review_gate_subtask8_if_this_then_that_scenario_map_packet_v0_1.json"

def parse_args():
    p = argparse.ArgumentParser(description=f"{ENGINE_ID} {VERSION}")
    p.add_argument("--hydra-root", required=True)
    p.add_argument("--manual-json", default="")
    for f in REQUIRED_FIELDS:
        p.add_argument("--" + f.replace("_", "-"), default="")
    return p.parse_args()

def collect_cli(args) -> Dict[str, str]:
    return {f: as_text(getattr(args, f)) for f in REQUIRED_FIELDS if as_text(getattr(args, f))}

def check_prev(hydra_root: Path):
    p = hydra_root / PREV_GATE_DIR / PREV_GATE_FILE
    data = read_json(p)
    if not data:
        return False, "MISSING_SUBTASK8_ACCEPTANCE_RESULT", p
    status = as_text(recursive_find_key(data, "overall_status"))
    ready = status == "SUBTASK8_IF_THIS_THEN_THAT_SCENARIO_MAP_ACCEPTED" and bool_from_any(recursive_find_key(data, "subtask_complete")) and bool_from_any(recursive_find_key(data, "content_execution_complete")) and bool_from_any(recursive_find_key(data, "human_accepted"))
    return ready, status or "UNKNOWN_SUBTASK8_ACCEPTANCE_STATUS", p

def inherit_prev(hydra_root: Path) -> Dict[str, str]:
    p = hydra_root / PREV_PACKET_DIR / PREV_PACKET_FILE
    data = read_json(p) or {}
    out = {}
    for f in ["review_date", "instruments", "sources"]:
        found = recursive_find_key(data, f)
        if found is not None:
            out[f] = as_text(found)
    if not out.get("sources"):
        out["sources"] = "Subtask 8 accepted if-this-then-that scenario map packet"
    return out

def main() -> int:
    args = parse_args()
    hydra_root = Path(args.hydra_root).expanduser().resolve()
    print_header(ENGINE_ID, VERSION, hydra_root, MODE)
    canonical = hydra_root / OUT_DIR
    docs = hydra_root / "docs"
    ensure_dir(canonical); ensure_dir(docs)
    prev_ready, prev_status, prev_path = check_prev(hydra_root)
    values = inherit_prev(hydra_root)
    values.update(read_manual_json(Path(args.manual_json) if args.manual_json else None, REQUIRED_FIELDS))
    values.update(collect_cli(args))
    field_rows=[]
    for f in REQUIRED_FIELDS:
        val = values.get(f, "")
        missing = is_missing(val, f)
        field_rows.append({"field_key": f, "required": True, "value": val, "populated": not missing, "status": "PASS" if not missing else "FAIL_REQUIRED", "description": FIELD_DESCRIPTIONS.get(f, "")})
    populated = sum(1 for f in REQUIRED_FIELDS if not is_missing(values.get(f, ""), f))
    missing = len(REQUIRED_FIELDS) - populated
    validation_error_count = 0 if prev_ready else 1
    validation_warning_count = 0
    if not prev_ready:
        section_status = "BLOCKED_PREREQUISITE"
        next_valid_action = "Complete/accept Subtask 8 If-this-then-that Scenario Map before continuing Subtask 9."
    elif missing:
        section_status = "BLOCKED_MISSING_REVIEWABLE_EVIDENCE_TRAIL_CONTEXT"
        next_valid_action = "Fill the generated Subtask 9 manual input template or rerun with required fields: --evidence-trail-source, --source-artifacts, --planner-source-references, --chart-or-screenshot-references, --reviewed-section-references, --claim-to-evidence-mapping, --missing-evidence-notes, --conflicting-evidence-notes, --audit-replay-requirements, --evidence-confidence, --allowed-inferences, and --not-allowed-inferences."
    else:
        section_status = "REVIEW_READY"
        next_valid_action = "Human-review the Subtask 9 Reviewable evidence trail packet. If accepted, proceed to Subtask 10 Explicit blocked / unknown areas. Do not start planner/market join, simulation, ML labels, or trade signals from this lane."
    overall_status = "REVIEWABLE_EVIDENCE_TRAIL_PACKET_MATERIALIZED"
    summary = {"overall_status": overall_status, "section_status": section_status, "subtask8_prerequisite_ready": prev_ready, "subtask8_acceptance_status": prev_status, "required_fields_count": len(REQUIRED_FIELDS), "populated_required_count": populated, "missing_required_count": missing, "validation_error_count": validation_error_count, "validation_warning_count": validation_warning_count, "content_execution_complete": False, "human_acceptance_required": True, **BLOCKED_FLAGS, "next_valid_action": next_valid_action}
    packet = {"engine_id": ENGINE_ID, "version": VERSION, "mode": MODE, "generated_at_utc": utc_now_iso(), "hydra_root": str(hydra_root), "guardrails": GUARDRAILS, "blocked_capabilities": BLOCKED_FLAGS, "subtask8_prerequisite": {"ready": prev_ready, "acceptance_status": prev_status, "result_json": str(prev_path)}, "summary": summary, "fields": {f: values.get(f, "") for f in REQUIRED_FIELDS}, "field_rows": field_rows}
    packet_json = canonical / f"{PREFIX}_packet_v0_1.json"
    fields_csv = canonical / f"{PREFIX}_fields_v0_1.csv"
    template_csv = canonical / f"{PREFIX}_manual_input_template_v0_1.csv"
    manifest_json = canonical / f"{PREFIX}_manifest_v0_1.json"
    packet_md = docs / f"{DOC_PREFIX}_PACKET_V0_1.md"
    asana_md = docs / f"{DOC_PREFIX}_ASANA_PAYLOAD_V0_1.md"
    report_md = docs / f"{DOC_PREFIX}_REPORT_V0_1.md"
    open_commands_txt = canonical / f"{PREFIX}_open_commands_v0_1.txt"
    atomic_write_json(packet_json, packet)
    atomic_write_csv(fields_csv, field_rows, ["field_key","required","value","populated","status","description"])
    atomic_write_csv(template_csv, [{"field_key": f, "required": True, "fill_value_here": values.get(f, ""), "description": FIELD_DESCRIPTIONS.get(f, ""), "accepted_values_or_notes": "Free text. No joins, MFE/MAE, signals, simulation, ML labels, or execution logic."} for f in REQUIRED_FIELDS], ["field_key","required","fill_value_here","description","accepted_values_or_notes"])
    atomic_write_json(manifest_json, {"engine_id": ENGINE_ID, "version": VERSION, "overall_status": overall_status, "section_status": section_status, "artifacts": {"packet_json": str(packet_json), "fields_csv": str(fields_csv), "manual_input_template_csv": str(template_csv), "manifest_json": str(manifest_json), "packet_md": str(packet_md), "asana_payload_md": str(asana_md), "report_md": str(report_md), "open_commands_txt": str(open_commands_txt)}, "guardrails": GUARDRAILS, "blocked_capabilities": BLOCKED_FLAGS, "next_valid_action": next_valid_action})
    atomic_write_text(packet_md, "# HYDRA Daily Planner Review Gate — Subtask 9 Reviewable Evidence Trail Packet v0.1\n\n" + "\n".join(f"- {k}: `{v}`" for k, v in summary.items()) + "\n")
    atomic_write_text(asana_md, "# Asana Payload — Subtask 9 Reviewable Evidence Trail\n\nPurpose: require evidence references and replayability without joins, signals, outcome measurement, or simulation.\n")
    atomic_write_text(report_md, "# HYDRA Daily Planner Review Gate — Subtask 9 Reviewable Evidence Trail Report v0.1\n\n" + "\n".join(f"- {k}: `{v}`" for k, v in summary.items()) + "\n")
    atomic_write_text(open_commands_txt, "\n".join([f'notepad "{packet_md}"', f'notepad "{report_md}"', f'notepad "{asana_md}"', f'notepad "{fields_csv}"', f'notepad "{template_csv}"']) + "\n")
    print("HYDRA DAILY PLANNER REVIEW GATE SUBTASK 9 REVIEWABLE EVIDENCE TRAIL MATERIALIZER COMPLETE")
    print(f"overall_status: {overall_status}")
    print(f"section_status: {section_status}")
    print(f"subtask8_prerequisite_ready: {prev_ready}")
    print(f"subtask8_acceptance_status: {prev_status}")
    print(f"required_fields_count: {len(REQUIRED_FIELDS)}")
    print(f"populated_required_count: {populated}")
    print(f"missing_required_count: {missing}")
    print(f"validation_error_count: {validation_error_count}")
    print(f"validation_warning_count: {validation_warning_count}")
    print("content_execution_complete: False")
    print("human_acceptance_required: True")
    for k,v in BLOCKED_FLAGS.items(): print(f"{k}: {v}")
    print(f"packet_json: {packet_json}")
    print(f"fields_csv: {fields_csv}")
    print(f"manual_input_template_csv: {template_csv}")
    print(f"manifest_json: {manifest_json}")
    print(f"packet_md: {packet_md}")
    print(f"asana_payload_md: {asana_md}")
    print(f"report_md: {report_md}")
    print(f"open_commands_txt: {open_commands_txt}")
    print(f"next_valid_action: {next_valid_action}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
