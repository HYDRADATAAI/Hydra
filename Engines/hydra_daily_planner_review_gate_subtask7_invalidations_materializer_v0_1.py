#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HYDRA Daily Planner Review Gate — Subtask 7 Invalidations Materializer v0.1

Materializes Review Gate Subtask 7 "Invalidations" as a non-mutating packet.
No market data scan, planner/market join, level-distance calculation, reaction measurement,
MFE/MAE, outcome measurement, trade signals, queue mutation, ML labels, simulation, execution,
external API call, or Asana mutation is performed.
"""

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


ENGINE_ID = "hydra_daily_planner_review_gate_subtask7_invalidations_materializer_v0_1"
VERSION = "v0.1"
MODE = "NON_MUTATING_DAILY_PLANNER_REVIEW_GATE_SUBTASK7_INVALIDATIONS_MATERIALIZER"
REQUIRED_FIELDS = ['review_date', 'instruments', 'sources', 'invalidation_source', 'primary_invalidation_condition', 'bullish_invalidation', 'bearish_invalidation', 'range_rotation_invalidation', 'level_invalidation', 'scenario_invalidation', 'confirmation_failure_invalidation', 'conflict_unknowns', 'invalidation_confidence', 'allowed_inferences', 'not_allowed_inferences']
FIELD_DESCRIPTIONS = {'review_date': 'Trading/review date for this Review Gate packet.', 'instruments': 'Instrument list covered by this invalidations review, e.g. ES,NQ.', 'sources': 'Reviewed source(s) used to populate the invalidations section.', 'invalidation_source': 'Where invalidation requirements came from: planner text, screenshots, manual notes, scaffold-smoke, etc.', 'primary_invalidation_condition': 'Main condition that invalidates the primary scenario or planner read. No execution instruction.', 'bullish_invalidation': 'Condition that invalidates a bullish lean/scenario, if applicable.', 'bearish_invalidation': 'Condition that invalidates a bearish lean/scenario, if applicable.', 'range_rotation_invalidation': 'Condition that invalidates a range/rotation expectation, if applicable.', 'level_invalidation': 'Condition that invalidates a key-level read without calculating level distance.', 'scenario_invalidation': 'Condition that invalidates a scenario map or makes it unusable.', 'confirmation_failure_invalidation': 'Condition showing confirmation failed or is absent, without creating a signal.', 'conflict_unknowns': 'Known conflicts, missing items, or unknowns that limit invalidation confidence.', 'invalidation_confidence': 'High, moderate, low, unknown, conflicting, or scaffold-smoke.', 'allowed_inferences': 'What Hydra may infer from this invalidations section without measuring outcomes or issuing signals.', 'not_allowed_inferences': 'What Hydra may not infer yet: no joins, level-distance calculations, reactions, MFE/MAE, signals, simulation, ML labels, execution.'}
OUT_PARENT = Path("data") / "canonical" / "daily_planner_review_gate_subtask7_invalidations_v0_1"
PACKET_JSON_NAME = "HYDRA_daily_planner_review_gate_subtask7_invalidations_packet_v0_1.json"
FIELDS_CSV_NAME = "HYDRA_daily_planner_review_gate_subtask7_invalidations_fields_v0_1.csv"
TEMPLATE_CSV_NAME = "HYDRA_daily_planner_review_gate_subtask7_invalidations_manual_input_template_v0_1.csv"
MANIFEST_JSON_NAME = "HYDRA_daily_planner_review_gate_subtask7_invalidations_manifest_v0_1.json"
PACKET_MD_NAME = "HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK7_INVALIDATIONS_PACKET_V0_1.md"
ASANA_MD_NAME = "HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK7_INVALIDATIONS_ASANA_PAYLOAD_V0_1.md"
REPORT_MD_NAME = "HYDRA_DAILY_PLANNER_REVIEW_GATE_SUBTASK7_INVALIDATIONS_REPORT_V0_1.md"
OPEN_COMMANDS_NAME = "HYDRA_daily_planner_review_gate_subtask7_invalidations_open_commands_v0_1.txt"


def check_subtask6_prerequisite(hydra_root: Path):
    result_path = hydra_root / "data" / "canonical" / "daily_planner_review_gate_subtask6_confirmation_requirements_acceptance_gate_v0_1" / "HYDRA_daily_planner_review_gate_subtask6_confirmation_requirements_acceptance_gate_result_v0_1.json"
    data = read_json(result_path)
    if not data:
        return False, "MISSING_SUBTASK6_ACCEPTANCE_RESULT", result_path
    status = as_text(recursive_find_key(data, "overall_status"))
    ready = (
        status == "SUBTASK6_CONFIRMATION_REQUIREMENTS_ACCEPTED"
        and bool_from_any(recursive_find_key(data, "subtask_complete"))
        and bool_from_any(recursive_find_key(data, "content_execution_complete"))
        and bool_from_any(recursive_find_key(data, "human_accepted"))
    )
    return ready, status or "UNKNOWN_SUBTASK6_ACCEPTANCE_STATUS", result_path


def inherit_from_subtask6_packet(hydra_root: Path):
    packet_path = hydra_root / "data" / "canonical" / "daily_planner_review_gate_subtask6_confirmation_requirements_v0_1" / "HYDRA_daily_planner_review_gate_subtask6_confirmation_requirements_packet_v0_1.json"
    data = read_json(packet_path) or {}
    inherited = {}
    for field in ["review_date", "instruments", "sources"]:
        found = recursive_find_key(data, field)
        if found is not None:
            inherited[field] = as_text(found)
    if not inherited.get("sources"):
        inherited["sources"] = "Subtask 6 accepted confirmation-requirements packet"
    return inherited


def collect_cli(args):
    return {k.replace('_','-'):'' for k in []} | {
        "review_date": args.review_date,
        "instruments": args.instruments,
        "sources": args.sources,
        "invalidation_source": args.invalidation_source,
        "primary_invalidation_condition": args.primary_invalidation_condition,
        "bullish_invalidation": args.bullish_invalidation,
        "bearish_invalidation": args.bearish_invalidation,
        "range_rotation_invalidation": args.range_rotation_invalidation,
        "level_invalidation": args.level_invalidation,
        "scenario_invalidation": args.scenario_invalidation,
        "confirmation_failure_invalidation": args.confirmation_failure_invalidation,
        "conflict_unknowns": args.conflict_unknowns,
        "invalidation_confidence": args.invalidation_confidence,
        "allowed_inferences": args.allowed_inferences,
        "not_allowed_inferences": args.not_allowed_inferences,
    }


def validate(values: Dict[str, str], prereq_ready: bool):
    rows = []
    fail = 0
    warn = 0
    err = 0
    passed = 0
    for field in REQUIRED_FIELDS:
        val = as_text(values.get(field, ""))
        missing = is_missing(val, field)
        status = "PASS" if not missing else "FAIL_REQUIRED"
        if missing:
            fail += 1
        else:
            passed += 1
        rows.append({"field_key": field, "required": True, "value": val, "populated": not missing, "status": status, "description": FIELD_DESCRIPTIONS.get(field, "")})
    if not prereq_ready:
        fail += 1
        err += 1
        rows.append({"field_key": "subtask6_prerequisite", "required": True, "value": "Subtask 6 Confirmation Requirements accepted prerequisite not confirmed", "populated": False, "status": "FAIL_REQUIRED", "description": "Subtask 7 requires accepted Subtask 6."})
    hits = forbidden_hits(values)
    for hit in hits:
        fail += 1
        err += 1
        rows.append({"field_key": "blocked_capability_language", "required": True, "value": hit, "populated": True, "status": "FAIL_REQUIRED", "description": "Forbidden capability language outside not_allowed_inferences."})
    nai = values.get("not_allowed_inferences", "").lower()
    if nai and not any(term in nai for term in ["no planner/market join", "no trade signals", "no simulation", "no ml"]):
        warn += 1
        rows.append({"field_key": "not_allowed_inferences_guardrail_warning", "required": False, "value": values.get("not_allowed_inferences", ""), "populated": True, "status": "WARN", "description": "Recommended explicit no join/no signal/no simulation/no ML language."})
    return rows, passed, fail, err, warn


def template_rows(values):
    return [{"field_key": f, "required": True, "fill_value_here": values.get(f, ""), "description": FIELD_DESCRIPTIONS.get(f, ""), "accepted_values_or_notes": "high|moderate|low|unknown|conflicting|scaffold-smoke" if f == "invalidation_confidence" else "Free text. No joins, MFE/MAE, signals, simulation, ML labels, or execution logic."} for f in REQUIRED_FIELDS]


def md_table(rows, columns):
    def esc(x): return as_text(x).replace("|", "\\|").replace("\n", "<br>")
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"]*len(columns)) + " |"]
    for r in rows:
        out.append("| " + " | ".join(esc(r.get(c, "")) for c in columns) + " |")
    return "\n".join(out)


def packet_md(packet, field_rows):
    s = packet["summary"]
    f = packet["fields"]
    return f"""# HYDRA Daily Planner Review Gate — Subtask 7 Invalidations Packet {VERSION}

## Summary

- engine_id: `{ENGINE_ID}`
- version: `{VERSION}`
- overall_status: `{s['overall_status']}`
- section_status: `{s['section_status']}`
- subtask6_prerequisite_ready: `{s['subtask6_prerequisite_ready']}`
- subtask6_acceptance_status: `{s['subtask6_acceptance_status']}`
- required_fields_count: `{s['required_fields_count']}`
- populated_required_count: `{s['populated_required_count']}`
- missing_required_count: `{s['missing_required_count']}`
- validation_error_count: `{s['validation_error_count']}`
- validation_warning_count: `{s['validation_warning_count']}`
- content_execution_complete: `{s['content_execution_complete']}`
- human_acceptance_required: `{s['human_acceptance_required']}`

## Guardrails

{chr(10).join(f'- {g}' for g in GUARDRAILS)}

## Invalidation Fields

{md_table(field_rows, ['field_key','required','populated','status','value'])}

## Rendered Subtask 7 Invalidations Section

```text
Date reviewed: {f.get('review_date','')}
Instrument(s): {f.get('instruments','')}
Source(s): {f.get('sources','')}
Invalidation source: {f.get('invalidation_source','')}
Primary invalidation condition: {f.get('primary_invalidation_condition','')}
Bullish invalidation: {f.get('bullish_invalidation','')}
Bearish invalidation: {f.get('bearish_invalidation','')}
Range/rotation invalidation: {f.get('range_rotation_invalidation','')}
Level invalidation: {f.get('level_invalidation','')}
Scenario invalidation: {f.get('scenario_invalidation','')}
Confirmation-failure invalidation: {f.get('confirmation_failure_invalidation','')}
Conflicts / unknowns: {f.get('conflict_unknowns','')}
Invalidation confidence: {f.get('invalidation_confidence','')}
What Hydra is allowed to infer: {f.get('allowed_inferences','')}
What Hydra is NOT allowed to infer yet: {f.get('not_allowed_inferences','')}
```

## Next Valid Action

{s['next_valid_action']}
"""


def asana_md():
    return f"""# Asana Payload — Hydra Daily Planner Review Gate v0.1
## Subtask 7 — Invalidations

### Purpose
Define what proves a market context, bias, scenario, key level, or confirmation read wrong before Hydra is allowed to treat the review as complete.

This section answers:

“What would invalidate the plan?”

### Required Output Format

```text
Date reviewed:
Instrument(s):
Source(s):
Invalidation source:
Primary invalidation condition:
Bullish invalidation:
Bearish invalidation:
Range/rotation invalidation:
Level invalidation:
Scenario invalidation:
Confirmation-failure invalidation:
Conflicts / unknowns:
Invalidation confidence:
What Hydra is allowed to infer:
What Hydra is NOT allowed to infer yet:
```

### Done Means
This section is complete only when invalidation logic is reviewable as planner context without creating trade signals, measuring outcomes, or joining market data.

### Explicitly Blocked In This Subtask
{chr(10).join(f'{i+1}. {g}' for i, g in enumerate(GUARDRAILS))}
"""


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=f"{ENGINE_ID} {VERSION}")
    p.add_argument("--hydra-root", required=True)
    p.add_argument("--manual-json", default="")
    for field in REQUIRED_FIELDS:
        p.add_argument("--" + field.replace("_", "-"), default="")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    hydra_root = normalize_hydra_root(args.hydra_root)
    print_header(ENGINE_ID, VERSION, hydra_root, MODE)
    canonical_dir = hydra_root / OUT_PARENT
    docs_dir = hydra_root / "docs"
    ensure_dir(canonical_dir); ensure_dir(docs_dir)

    prereq_ready, prereq_status, prereq_path = check_subtask6_prerequisite(hydra_root)
    values = inherit_from_subtask6_packet(hydra_root)
    values.update(read_manual_json(Path(args.manual_json) if args.manual_json else None, REQUIRED_FIELDS))
    values.update({k: as_text(v) for k, v in collect_cli(args).items() if as_text(v)})

    field_rows, pass_count, fail_required_count, validation_error_count, validation_warning_count = validate(values, prereq_ready)
    populated = sum(1 for f in REQUIRED_FIELDS if not is_missing(values.get(f, ""), f))
    missing = len(REQUIRED_FIELDS) - populated

    if not prereq_ready:
        section_status = "BLOCKED_PREREQUISITE"
        next_valid_action = "Complete/accept Subtask 6 Confirmation Requirements before continuing Subtask 7."
    elif missing > 0 or validation_error_count > 0:
        section_status = "BLOCKED_MISSING_INVALIDATION_CONTEXT"
        next_valid_action = "Fill the generated Subtask 7 manual input template or rerun with required fields: --invalidation-source, --primary-invalidation-condition, --bullish-invalidation, --bearish-invalidation, --range-rotation-invalidation, --level-invalidation, --scenario-invalidation, --confirmation-failure-invalidation, --conflict-unknowns, --invalidation-confidence, --allowed-inferences, and --not-allowed-inferences."
    else:
        section_status = "REVIEW_READY"
        next_valid_action = "Human-review the Subtask 7 Invalidations packet. If accepted, proceed to Subtask 8 If-this-then-that scenario map. Do not start planner/market join, simulation, ML labels, or trade signals from this lane."

    overall_status = "INVALIDATIONS_PACKET_MATERIALIZED"
    summary = {
        "overall_status": overall_status,
        "section_status": section_status,
        "subtask6_prerequisite_ready": prereq_ready,
        "subtask6_acceptance_status": prereq_status,
        "required_fields_count": len(REQUIRED_FIELDS),
        "populated_required_count": populated,
        "missing_required_count": missing,
        "validation_error_count": validation_error_count,
        "validation_warning_count": validation_warning_count,
        "content_execution_complete": False,
        "human_acceptance_required": True,
        **BLOCKED_FLAGS,
        "next_valid_action": next_valid_action,
    }
    packet = {
        "engine_id": ENGINE_ID,
        "version": VERSION,
        "mode": MODE,
        "generated_at_utc": utc_now_iso(),
        "hydra_root": str(hydra_root),
        "guardrails": GUARDRAILS,
        "blocked_capabilities": BLOCKED_FLAGS,
        "subtask6_prerequisite": {"ready": prereq_ready, "acceptance_status": prereq_status, "result_json": str(prereq_path)},
        "summary": summary,
        "fields": {f: values.get(f, "") for f in REQUIRED_FIELDS},
        "field_rows": field_rows,
    }
    paths = {
        "packet_json": canonical_dir / PACKET_JSON_NAME,
        "fields_csv": canonical_dir / FIELDS_CSV_NAME,
        "manual_input_template_csv": canonical_dir / TEMPLATE_CSV_NAME,
        "manifest_json": canonical_dir / MANIFEST_JSON_NAME,
        "packet_md": docs_dir / PACKET_MD_NAME,
        "asana_payload_md": docs_dir / ASANA_MD_NAME,
        "report_md": docs_dir / REPORT_MD_NAME,
        "open_commands_txt": canonical_dir / OPEN_COMMANDS_NAME,
    }
    atomic_write_json(paths["packet_json"], packet)
    atomic_write_csv(paths["fields_csv"], field_rows, ["field_key","required","value","populated","status","description"])
    atomic_write_csv(paths["manual_input_template_csv"], template_rows(values), ["field_key","required","fill_value_here","description","accepted_values_or_notes"])
    manifest = {"engine_id": ENGINE_ID, "version": VERSION, "generated_at_utc": packet["generated_at_utc"], "overall_status": overall_status, "section_status": section_status, "artifacts": {k: str(v) for k, v in paths.items()}, "guardrails": GUARDRAILS, "blocked_capabilities": BLOCKED_FLAGS, "next_valid_action": next_valid_action}
    atomic_write_json(paths["manifest_json"], manifest)
    atomic_write_text(paths["packet_md"], packet_md(packet, field_rows))
    atomic_write_text(paths["asana_payload_md"], asana_md())
    report = f"""# HYDRA Daily Planner Review Gate — Subtask 7 Invalidations Materializer Report {VERSION}

- engine_id: `{ENGINE_ID}`
- version: `{VERSION}`
- overall_status: `{overall_status}`
- section_status: `{section_status}`
- subtask6_prerequisite_ready: `{prereq_ready}`
- subtask6_acceptance_status: `{prereq_status}`
- required_fields_count: `{len(REQUIRED_FIELDS)}`
- populated_required_count: `{populated}`
- missing_required_count: `{missing}`
- validation_error_count: `{validation_error_count}`
- validation_warning_count: `{validation_warning_count}`

## Artifact Paths
{chr(10).join(f'- {k}: `{v}`' for k, v in paths.items())}

## Next Valid Action
{next_valid_action}
"""
    atomic_write_text(paths["report_md"], report)
    atomic_write_text(paths["open_commands_txt"], "\n".join([f'notepad "{paths[k]}"' for k in ["packet_md","report_md","asana_payload_md","fields_csv","manual_input_template_csv"]]) + "\n")

    print("HYDRA DAILY PLANNER REVIEW GATE SUBTASK 7 INVALIDATIONS MATERIALIZER COMPLETE")
    print(f"overall_status: {overall_status}")
    print(f"section_status: {section_status}")
    print(f"subtask6_prerequisite_ready: {prereq_ready}")
    print(f"subtask6_acceptance_status: {prereq_status}")
    print(f"required_fields_count: {len(REQUIRED_FIELDS)}")
    print(f"populated_required_count: {populated}")
    print(f"missing_required_count: {missing}")
    print(f"validation_error_count: {validation_error_count}")
    print(f"validation_warning_count: {validation_warning_count}")
    print("content_execution_complete: False")
    print("human_acceptance_required: True")
    for key, value in BLOCKED_FLAGS.items(): print(f"{key}: {value}")
    for key, value in paths.items(): print(f"{key}: {value}")
    print(f"next_valid_action: {next_valid_action}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
