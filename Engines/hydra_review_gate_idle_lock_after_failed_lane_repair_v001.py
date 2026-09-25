#!/usr/bin/env python3
"""
HYDRA Review Gate Idle Lock After Failed-Lane Repair v0.1

Read-only idle lock after post failed-lane repair global next-lane selector.

Purpose:
- Confirm failed-lane repair branch is closed.
- Confirm Review Gate is idle.
- Write a derived-only idle lock checkpoint so the next work session starts clean.

Guardrails:
- no simulation
- no active queue writes
- no queue mutation
- no source packet/template mutation
- no evidence application
- no code edits
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ENGINE_ID = "hydra_review_gate_idle_lock_after_failed_lane_repair_v001.py"
VERSION = "v0_1"

POST_SELECTOR_REL = Path("data/canonical/post_failed_lane_repair_global_next_lane_selector_v0_1")
FINAL_CLOSEOUT_REL = Path("data/canonical/global_failed_lane_repair_final_closeout_v0_1")
OUT_REL = Path("data/canonical/review_gate_idle_lock_after_failed_lane_repair_v0_1")

POST_SELECTOR_SUMMARY_NAME = "HYDRA_post_failed_lane_repair_global_next_lane_selector_summary_v0_1.csv"
POST_SELECTOR_ACTION_NAME = "HYDRA_post_failed_lane_repair_global_next_lane_selector_selected_action_v0_1.csv"
POST_SELECTOR_CHECKS_NAME = "HYDRA_post_failed_lane_repair_global_next_lane_selector_checks_v0_1.csv"
FINAL_CLOSEOUT_SUMMARY_NAME = "HYDRA_global_failed_lane_repair_final_closeout_summary_v0_1.csv"

EXPECTED_SELECTOR_STATUS = "POST_FAILED_LANE_REPAIR_GLOBAL_NEXT_SELECTOR_REVIEW_GATE_IDLE_CONFIRMED"
EXPECTED_SELECTOR_NEXT = "REVIEW_GATE_IDLE_WAIT_FOR_NEW_EVIDENCE_OR_NEW_QUEUE_INPUT_NO_SIMULATION"
EXPECTED_SELECTED_LANE = "REVIEW_GATE_IDLE"
EXPECTED_SELECTED_ACTION = "WAIT_FOR_NEW_EVIDENCE_OR_NEW_QUEUE_INPUT_DO_NOT_SIMULATE"
EXPECTED_FINAL_CLOSEOUT_STATUS = "GLOBAL_FAILED_LANE_REPAIR_FINAL_CLOSEOUT_COMPLETE_NO_ACTIVE_FAILED_LANES"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def norm(value: Any) -> str:
    return "" if value is None else str(value).strip()


def as_int(value: Any, default: int = 0) -> int:
    try:
        s = norm(value)
        return default if s == "" else int(float(s))
    except Exception:
        return default


def is_falseish(value: Any) -> bool:
    return norm(value).lower() in {"", "false", "0", "no", "n"}


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]
    except Exception:
        return []


def write_csv_rows(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def add_check(checks: List[Dict[str, Any]], check_id: str, check_name: str, expected: Any, actual: Any, passed: bool) -> None:
    checks.append({
        "check_id": check_id,
        "check_name": check_name,
        "expected": expected,
        "actual": actual,
        "passed": bool(passed),
        "severity": "ERROR",
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="HYDRA review gate idle lock after failed-lane repair v0.1.")
    parser.add_argument("--hydra-root", required=True)
    args = parser.parse_args()

    hydra_root = Path(args.hydra_root)
    docs_dir = hydra_root / "docs"
    post_dir = hydra_root / POST_SELECTOR_REL
    final_dir = hydra_root / FINAL_CLOSEOUT_REL
    out_dir = hydra_root / OUT_REL

    post_summary_path = post_dir / POST_SELECTOR_SUMMARY_NAME
    post_action_path = post_dir / POST_SELECTOR_ACTION_NAME
    post_checks_path = post_dir / POST_SELECTOR_CHECKS_NAME
    final_summary_path = final_dir / FINAL_CLOSEOUT_SUMMARY_NAME

    post_summary_rows = read_csv_rows(post_summary_path)
    post_action_rows = read_csv_rows(post_action_path)
    post_checks_rows = read_csv_rows(post_checks_path)
    final_summary_rows = read_csv_rows(final_summary_path)

    post_summary = post_summary_rows[0] if post_summary_rows else {}
    post_action = post_action_rows[0] if post_action_rows else {}
    final_summary = final_summary_rows[0] if final_summary_rows else {}

    checks: List[Dict[str, Any]] = []

    add_check(checks, "FILE_001", "post_selector_summary_exists", True, post_summary_path.exists(), post_summary_path.exists())
    add_check(checks, "FILE_002", "post_selector_action_exists", True, post_action_path.exists(), post_action_path.exists())
    add_check(checks, "FILE_003", "post_selector_checks_exists", True, post_checks_path.exists(), post_checks_path.exists())
    add_check(checks, "FILE_004", "final_closeout_summary_exists", True, final_summary_path.exists(), final_summary_path.exists())

    selector_overall = norm(post_summary.get("overall_status"))
    selector_status = norm(post_summary.get("selector_status"))
    selector_next = norm(post_summary.get("next_allowed_step"))
    selector_checks_failed = as_int(post_summary.get("checks_failed"))
    selected_next_lane = norm(post_summary.get("selected_next_lane")) or norm(post_action.get("selected_next_lane"))
    selected_next_action = norm(post_summary.get("selected_next_action")) or norm(post_action.get("selected_next_action"))

    active_failed_lane_summary_rows = as_int(post_summary.get("active_failed_lane_summary_rows"))
    missing_registry_match_rows = as_int(post_summary.get("missing_registry_match_rows"))
    new_input_signal_count = as_int(post_summary.get("new_input_signal_count"))
    cumulative_stale_registry_rows = as_int(post_summary.get("cumulative_stale_registry_rows"))

    final_overall = norm(final_summary.get("overall_status"))
    final_status = norm(final_summary.get("final_closeout_status"))
    final_next = norm(final_summary.get("next_allowed_step"))
    final_checks_failed = as_int(final_summary.get("checks_failed"))

    failed_post_checks = [r for r in post_checks_rows if norm(r.get("passed")).lower() not in {"true", "1", "yes", "y"}]

    add_check(checks, "POST_001", "post_selector_overall_status", "PASS", selector_overall, selector_overall == "PASS")
    add_check(checks, "POST_002", "post_selector_status", EXPECTED_SELECTOR_STATUS, selector_status, selector_status == EXPECTED_SELECTOR_STATUS)
    add_check(checks, "POST_003", "post_selector_next_allowed_step", EXPECTED_SELECTOR_NEXT, selector_next, selector_next == EXPECTED_SELECTOR_NEXT)
    add_check(checks, "POST_004", "selected_next_lane", EXPECTED_SELECTED_LANE, selected_next_lane, selected_next_lane == EXPECTED_SELECTED_LANE)
    add_check(checks, "POST_005", "selected_next_action", EXPECTED_SELECTED_ACTION, selected_next_action, selected_next_action == EXPECTED_SELECTED_ACTION)
    add_check(checks, "POST_006", "post_selector_checks_failed", 0, selector_checks_failed, selector_checks_failed == 0)
    add_check(checks, "POST_007", "post_selector_checks_table_failed_rows", 0, len(failed_post_checks), len(failed_post_checks) == 0)

    add_check(checks, "COUNT_001", "active_failed_lane_summary_rows", 0, active_failed_lane_summary_rows, active_failed_lane_summary_rows == 0)
    add_check(checks, "COUNT_002", "missing_registry_match_rows", 0, missing_registry_match_rows, missing_registry_match_rows == 0)
    add_check(checks, "COUNT_003", "new_input_signal_count", 0, new_input_signal_count, new_input_signal_count == 0)
    add_check(checks, "COUNT_004", "cumulative_stale_registry_rows_min_4", ">=4", cumulative_stale_registry_rows, cumulative_stale_registry_rows >= 4)

    add_check(checks, "FINAL_001", "final_closeout_overall_status", "PASS", final_overall, final_overall == "PASS")
    add_check(checks, "FINAL_002", "final_closeout_status", EXPECTED_FINAL_CLOSEOUT_STATUS, final_status, final_status == EXPECTED_FINAL_CLOSEOUT_STATUS)
    add_check(checks, "FINAL_003", "final_closeout_checks_failed", 0, final_checks_failed, final_checks_failed == 0)

    for field in [
        "simulator_called",
        "simulation_results_written",
        "simulation_authorized",
        "active_queue_written",
        "queue_mutation",
        "source_packet_modified",
        "capture_template_modified",
        "setup4_rank4_rebuilt",
        "evidence_merge_applied",
        "selector_created_sim_candidate",
        "selector_created_queue_rows",
        "evidence_applied",
        "code_modified",
    ]:
        add_check(checks, f"GUARD_POST_{field}", field, False, post_summary.get(field, ""), is_falseish(post_summary.get(field, "")))

    failed = [c for c in checks if not c["passed"]]
    overall_status = "PASS" if not failed else "FAIL"

    if overall_status == "PASS":
        idle_lock_status = "REVIEW_GATE_IDLE_LOCK_AFTER_FAILED_LANE_REPAIR_CONFIRMED"
        next_allowed_step = "REVIEW_GATE_IDLE_LOCKED_WAIT_FOR_NEW_EVIDENCE_OR_QUEUE_INPUT_NO_SIMULATION"
    else:
        idle_lock_status = "REVIEW_GATE_IDLE_LOCK_AFTER_FAILED_LANE_REPAIR_BLOCKED"
        next_allowed_step = "STOP_FIX_REVIEW_GATE_IDLE_LOCK_AFTER_FAILED_LANE_REPAIR_BLOCKERS"

    summary_out = out_dir / "HYDRA_review_gate_idle_lock_after_failed_lane_repair_summary_v0_1.csv"
    idle_lock_out = out_dir / "HYDRA_review_gate_idle_lock_after_failed_lane_repair_lock_v0_1.csv"
    checks_out = out_dir / "HYDRA_review_gate_idle_lock_after_failed_lane_repair_checks_v0_1.csv"
    artifacts_out = out_dir / "HYDRA_review_gate_idle_lock_after_failed_lane_repair_artifacts_v0_1.csv"
    json_out = out_dir / "HYDRA_review_gate_idle_lock_after_failed_lane_repair_v0_1.json"
    report_out = docs_dir / "HYDRA_REVIEW_GATE_IDLE_LOCK_AFTER_FAILED_LANE_REPAIR_V0_1.md"
    checkpoint_out = docs_dir / "HYDRA_CHECKPOINT_20260524_REVIEW_GATE_IDLE_LOCK_AFTER_FAILED_LANE_REPAIR_V0_1.txt"

    summary_row = {
        "engine_id": ENGINE_ID,
        "version": VERSION,
        "created_utc": utc_now_iso(),
        "overall_status": overall_status,
        "idle_lock_status": idle_lock_status,
        "source_selector_status": selector_status,
        "source_final_closeout_status": final_status,
        "selected_next_lane": selected_next_lane,
        "selected_next_action": selected_next_action,
        "new_input_signal_count": new_input_signal_count,
        "active_failed_lane_summary_rows": active_failed_lane_summary_rows,
        "missing_registry_match_rows": missing_registry_match_rows,
        "cumulative_stale_registry_rows": cumulative_stale_registry_rows,
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "simulator_called": False,
        "simulation_results_written": False,
        "simulation_authorized": False,
        "active_queue_written": False,
        "queue_mutation": False,
        "source_packet_modified": False,
        "capture_template_modified": False,
        "setup4_rank4_rebuilt": False,
        "evidence_merge_applied": False,
        "idle_lock_created_sim_candidate": False,
        "idle_lock_created_queue_rows": False,
        "evidence_applied": False,
        "code_modified": False,
        "next_allowed_step": next_allowed_step,
    }

    lock_row = {
        "idle_lock_status": idle_lock_status,
        "selected_next_lane": selected_next_lane,
        "selected_next_action": selected_next_action,
        "allowed_actions": "NEW_EVIDENCE_INPUT_OR_NEW_QUEUE_INPUT_ONLY",
        "disallowed_actions": "SIMULATION;ACTIVE_QUEUE_WRITE;QUEUE_MUTATION;SOURCE_PACKET_MODIFICATION;EVIDENCE_APPLICATION;CODE_MUTATION",
        "next_allowed_step": next_allowed_step,
        "simulation_authorized": False,
        "active_queue_written": False,
        "queue_mutation": False,
        "source_packet_modified": False,
        "code_modified": False,
    }

    write_csv_rows(summary_out, [summary_row], list(summary_row.keys()))
    write_csv_rows(idle_lock_out, [lock_row], list(lock_row.keys()))
    write_csv_rows(checks_out, checks, ["check_id", "check_name", "expected", "actual", "passed", "severity"])

    artifact_rows = [
        {"artifact_type": "summary", "path": str(summary_out)},
        {"artifact_type": "idle_lock", "path": str(idle_lock_out)},
        {"artifact_type": "checks", "path": str(checks_out)},
        {"artifact_type": "json", "path": str(json_out)},
        {"artifact_type": "report", "path": str(report_out)},
        {"artifact_type": "checkpoint", "path": str(checkpoint_out)},
        {"artifact_type": "source_post_selector_summary", "path": str(post_summary_path)},
        {"artifact_type": "source_post_selector_action", "path": str(post_action_path)},
        {"artifact_type": "source_final_closeout_summary", "path": str(final_summary_path)},
    ]
    write_csv_rows(artifacts_out, artifact_rows, ["artifact_type", "path"])
    write_text(json_out, json.dumps({"summary": summary_row, "failed_checks": failed, "idle_lock": lock_row, "artifacts": artifact_rows}, indent=2))

    report = f"""# HYDRA Review Gate Idle Lock After Failed-Lane Repair v0.1

- engine_id: `{ENGINE_ID}`
- version: `{VERSION}`
- overall_status: `{overall_status}`
- idle_lock_status: `{idle_lock_status}`
- source_selector_status: `{selector_status}`
- source_final_closeout_status: `{final_status}`
- selected_next_lane: `{selected_next_lane}`
- selected_next_action: `{selected_next_action}`
- new_input_signal_count: `{new_input_signal_count}`
- active_failed_lane_summary_rows: `{active_failed_lane_summary_rows}`
- missing_registry_match_rows: `{missing_registry_match_rows}`
- cumulative_stale_registry_rows: `{cumulative_stale_registry_rows}`
- checks_failed: `{len(failed)}`
- simulator_called: `False`
- simulation_authorized: `False`
- active_queue_written: `False`
- queue_mutation: `False`
- source_packet_modified: `False`
- evidence_merge_applied: `False`
- code_modified: `False`
- next_allowed_step: `{next_allowed_step}`

## Idle Rule

Only new evidence input or new queue/input packet may reopen Review Gate. No simulation or queue mutation is authorized from this state.
"""
    write_text(report_out, report)

    checkpoint = (
        "HYDRA REVIEW GATE IDLE LOCK AFTER FAILED-LANE REPAIR v0.1\n"
        f"created_utc: {summary_row['created_utc']}\n"
        f"overall_status: {overall_status}\n"
        f"idle_lock_status: {idle_lock_status}\n"
        f"source_selector_status: {selector_status}\n"
        f"source_final_closeout_status: {final_status}\n"
        f"selected_next_lane: {selected_next_lane}\n"
        f"selected_next_action: {selected_next_action}\n"
        f"new_input_signal_count: {new_input_signal_count}\n"
        f"active_failed_lane_summary_rows: {active_failed_lane_summary_rows}\n"
        f"missing_registry_match_rows: {missing_registry_match_rows}\n"
        f"next_allowed_step: {next_allowed_step}\n"
        "simulator_called: False\n"
        "simulation_authorized: False\n"
        "active_queue_written: False\n"
        "queue_mutation: False\n"
        "source_packet_modified: False\n"
        "code_modified: False\n"
    )
    write_text(checkpoint_out, checkpoint)

    print("HYDRA REVIEW GATE IDLE LOCK AFTER FAILED-LANE REPAIR v0.1 COMPLETE")
    for key in [
        "engine_id",
        "version",
        "overall_status",
        "idle_lock_status",
        "source_selector_status",
        "source_final_closeout_status",
        "selected_next_lane",
        "selected_next_action",
        "new_input_signal_count",
        "active_failed_lane_summary_rows",
        "missing_registry_match_rows",
        "cumulative_stale_registry_rows",
        "checks_passed",
        "checks_failed",
        "simulator_called",
        "simulation_results_written",
        "simulation_authorized",
        "active_queue_written",
        "queue_mutation",
        "source_packet_modified",
        "capture_template_modified",
        "setup4_rank4_rebuilt",
        "evidence_merge_applied",
        "idle_lock_created_sim_candidate",
        "idle_lock_created_queue_rows",
        "evidence_applied",
        "code_modified",
        "next_allowed_step",
    ]:
        print(f"{key}: {summary_row[key]}")
    print(f"summary: {summary_out}")
    print(f"idle_lock: {idle_lock_out}")
    print(f"report: {report_out}")
    print(f"checkpoint: {checkpoint_out}")

    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
