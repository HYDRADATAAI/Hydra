#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HYDRA H001 SOURCE-MANIFEST CONFIRMATION VALIDATION CONTRACT v0.1

Purpose:
  Validate the human-edited source-manifest confirmation/triage packet after:
    - gamma_context_source was marked NO
    - orderflow_context_source was marked NO
    - base_target_attached_rows was marked YES with keys:
        symbol / session_date / timestamp

This contract validates the decision structure only. It does NOT validate raw
source contents, does NOT register manifests as production-ready, does NOT run
source joins, does NOT write expanded data, does NOT run research eval, and
does NOT fit/train/score/predict/promote.

Expected outcome:
  - base_target_attached_rows confirmation accepted
  - gamma_context_source remains unresolved/rejected
  - orderflow_context_source remains unresolved/rejected
  - manifest_registration_complete remains False
  - source_join_execution_ready remains False
  - larger-coverage join path stays parked until gamma/orderflow manifests exist

Guardrails:
  - Confirmation validation only
  - No source join execution
  - No expanded data artifact write
  - No raw source scan / no full source-file load
  - No model fit / train / score / prediction / promotion
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ENGINE_ID = "hydra_model_training_h001_context_filter_filtered_target_attached_dataset_options_gamma_orderflow_bounded_artifact_source_manifest_confirmation_validation_contract_v001.py"
VERSION = "v0_1"
MODE = "SOURCE_MANIFEST_CONFIRMATION_VALIDATION_ONLY_NO_REGISTRATION_NO_JOIN_NO_DATA_WRITE_NO_EVAL_NO_TRAIN_NO_SCORE_NO_PROMOTION"
GUARDRAIL = "CONFIRMATION_VALIDATION_ONLY_NO_SOURCE_JOIN_NO_EXPANDED_DATA_WRITE_NO_MODEL_FIT_NO_PROMOTION"

SOURCE_CONFIRMED_GLOBS = [
    "H001_SOURCE_MANIFEST_CONFIRMATION_TRIAGE_PACKET_V0_1_*_TRIAGE_PACKET_USER_CONFIRMED.csv",
    "*SOURCE_MANIFEST*USER_CONFIRMED*.csv",
]

REQUIRED_FAMILIES = ["gamma_context_source", "orderflow_context_source", "base_target_attached_rows"]
REQUIRED_YES_KEYS = ["confirmed_schema_id", "confirmed_symbol_key", "confirmed_session_date_key", "confirmed_timestamp_or_row_id_key"]


def now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def latest_file_multi(root: Path, rel_dir: str, patterns: List[str]) -> Optional[Path]:
    base = root / rel_dir
    if not base.exists():
        return None
    matches: List[Path] = []
    for pattern in patterns:
        matches.extend(base.glob(pattern))
    if not matches:
        return None
    return max(matches, key=lambda p: (p.stat().st_mtime, p.name))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, sort_keys=False, default=str)


def serialize_cell(v: Any) -> str:
    if isinstance(v, (dict, list, tuple, set)):
        return json.dumps(list(v) if isinstance(v, set) else v, ensure_ascii=False, sort_keys=True)
    if v is None:
        return ""
    return str(v)


def write_rows_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: List[str] = []
    for row in rows:
        for k in row.keys():
            if k not in keys:
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        if not keys:
            f.write("")
            return
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: serialize_cell(row.get(k)) for k in keys})


def write_single_row_csv(path: Path, row: Dict[str, Any]) -> None:
    write_rows_csv(path, [row])


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
        return list(csv.DictReader(f))


def print_kv(payload: Dict[str, Any], keys: Iterable[str]) -> None:
    for k in keys:
        if k in payload:
            print(f"{k}: {payload[k]}")


def yes_no(value: Any) -> str:
    return str(value or "").strip().upper()


def is_blank(value: Any) -> bool:
    return str(value or "").strip() == ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hydra-root", required=True)
    args = ap.parse_args()

    hydra_root = Path(args.hydra_root).expanduser().resolve()
    docs_dir = hydra_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    print("HYDRA H001 SOURCE-MANIFEST CONFIRMATION VALIDATION CONTRACT START")
    print(f"engine_id: {ENGINE_ID}")
    print(f"version: {VERSION}")
    print(f"hydra_root: {hydra_root}")
    print(f"mode: {MODE}")
    print(f"guardrail: {GUARDRAIL}")

    checks: List[Dict[str, Any]] = []

    source_csv = latest_file_multi(hydra_root, "docs", SOURCE_CONFIRMED_GLOBS)
    if not source_csv or not source_csv.exists():
        checks.append({"check_name": "source_user_confirmed_packet_found", "status": "FAIL_REQUIRED", "detail": SOURCE_CONFIRMED_GLOBS})
        rows: List[Dict[str, str]] = []
    else:
        rows = read_csv_rows(source_csv)
        checks.append({"check_name": "source_user_confirmed_packet_found", "status": "PASS", "detail": str(source_csv)})

    family_rows = {str(r.get("manifest_family")): r for r in rows}
    missing = [fam for fam in REQUIRED_FAMILIES if fam not in family_rows]
    checks.append({
        "check_name": "confirmed_packet_has_required_families",
        "status": "PASS" if not missing else "FAIL_REQUIRED",
        "detail": {"missing_families": missing},
    })

    validation_rows: List[Dict[str, Any]] = []
    accepted_count = 0
    rejected_count = 0
    invalid_count = 0
    unresolved_families: List[str] = []
    accepted_families: List[str] = []
    rejected_families: List[str] = []

    for fam in REQUIRED_FAMILIES:
        r = family_rows.get(fam, {})
        decision = yes_no(r.get("confirm_candidate_path"))
        issues: List[str] = []

        if decision not in {"YES", "NO"}:
            issues.append("confirm_candidate_path_not_yes_or_no")

        if decision == "YES":
            for key in REQUIRED_YES_KEYS:
                if is_blank(r.get(key)):
                    issues.append(f"{key}_required_for_yes")
            if is_blank(r.get("candidate_manifest_path")) and is_blank(r.get("corrected_manifest_path")):
                issues.append("manifest_path_required_for_yes")
            if not issues:
                status = "ACCEPTED_CONFIRMED_MANIFEST"
                accepted_count += 1
                accepted_families.append(fam)
            else:
                status = "INVALID_YES_CONFIRMATION"
                invalid_count += 1

        elif decision == "NO":
            status = "REJECTED_CANDIDATE_MANIFEST_UNRESOLVED"
            rejected_count += 1
            rejected_families.append(fam)
            unresolved_families.append(fam)
        else:
            status = "INVALID_DECISION"
            invalid_count += 1

        validation_rows.append({
            "manifest_family": fam,
            "decision": decision,
            "validation_status": status,
            "candidate_manifest_path": r.get("candidate_manifest_path", ""),
            "corrected_manifest_path": r.get("corrected_manifest_path", ""),
            "confirmed_schema_id": r.get("confirmed_schema_id", ""),
            "confirmed_symbol_key": r.get("confirmed_symbol_key", ""),
            "confirmed_session_date_key": r.get("confirmed_session_date_key", ""),
            "confirmed_timestamp_or_row_id_key": r.get("confirmed_timestamp_or_row_id_key", ""),
            "issue_count": len(issues),
            "issues": issues,
        })

    if invalid_count:
        checks.append({"check_name": "all_decisions_valid", "status": "FAIL_REQUIRED", "detail": {"invalid_count": invalid_count}})
    else:
        checks.append({"check_name": "all_decisions_valid", "status": "PASS", "detail": {"accepted": accepted_count, "rejected": rejected_count}})

    expected_partial = (
        "base_target_attached_rows" in accepted_families
        and "gamma_context_source" in rejected_families
        and "orderflow_context_source" in rejected_families
    )
    checks.append({
        "check_name": "expected_partial_confirmation_shape",
        "status": "PASS" if expected_partial else "WARNING",
        "detail": {"accepted": accepted_families, "rejected": rejected_families},
    })

    restart_requirements_rows = [
        {
            "manifest_family": "gamma_context_source",
            "status": "REQUIRED_UNRESOLVED",
            "needed_for": "larger_coverage_source_join_execution",
            "minimum_fields": "manifest_path,schema_id,symbol_key,session_date_key,timestamp_or_row_id_key",
        },
        {
            "manifest_family": "orderflow_context_source",
            "status": "REQUIRED_UNRESOLVED",
            "needed_for": "larger_coverage_source_join_execution",
            "minimum_fields": "manifest_path,schema_id,symbol_key,session_date_key,timestamp_or_row_id_key",
        },
        {
            "manifest_family": "base_target_attached_rows",
            "status": "CONFIRMED_AVAILABLE",
            "needed_for": "larger_coverage_source_join_execution",
            "minimum_fields": "confirmed",
        },
    ]

    fail_required_count = sum(1 for c in checks if c.get("status") == "FAIL_REQUIRED")
    warning_count = sum(1 for c in checks if c.get("status") == "WARNING") + 1
    ready = fail_required_count == 0
    overall_status = "PASS_WITH_WARNINGS" if ready else "FAIL_REQUIRED"

    stamp = now_stamp()
    base = f"H001_SOURCE_MANIFEST_CONFIRMATION_VALIDATION_V0_1_{stamp}"
    artifact_json = docs_dir / f"{base}.json"
    artifact_md = docs_dir / f"{base}.md"
    artifact_decision_csv = docs_dir / f"{base}_DECISION.csv"
    artifact_validation_csv = docs_dir / f"{base}_VALIDATION.csv"
    artifact_restart_requirements_csv = docs_dir / f"{base}_RESTART_REQUIREMENTS.csv"
    artifact_checks_csv = docs_dir / f"{base}_CHECKS.csv"

    if ready:
        final_lane_status = "MODEL_TRAINING_H001_SOURCE_MANIFEST_CONFIRMATION_VALIDATION_PASS_WITH_WARNINGS_PARKED"
        validation_status = "H001_SOURCE_MANIFEST_CONFIRMATION_VALIDATION_COMPLETE_WITH_WARNINGS"
        selection_decision = "ACCEPT_PARTIAL_CONFIRMATION_AND_KEEP_JOIN_PATH_PARKED"
        selection_verdict = "PASS_WITH_WARNINGS_BASE_CONFIRMED_GAMMA_ORDERFLOW_UNRESOLVED_NO_JOIN"
        quality_classification = "H001_SOURCE_MANIFEST_PARTIAL_CONFIRMATION_ACCEPTED_PARKED"
        confirmation_validation_complete = True
    else:
        final_lane_status = "MODEL_TRAINING_H001_SOURCE_MANIFEST_CONFIRMATION_VALIDATION_FAIL_PARKED"
        validation_status = "H001_SOURCE_MANIFEST_CONFIRMATION_VALIDATION_INCOMPLETE"
        selection_decision = "PARK_CONFIRMATION_VALIDATION_REQUIRED_CHECK_FAILED"
        selection_verdict = "FAIL_REQUIRED_NO_CONFIRMATION_VALIDATION_NO_JOIN"
        quality_classification = "H001_SOURCE_MANIFEST_CONFIRMATION_VALIDATION_NOT_ACCEPTED"
        confirmation_validation_complete = False

    payload: Dict[str, Any] = {
        "overall_status": overall_status,
        "final_lane_status": final_lane_status,
        "validation_status": validation_status,
        "selection_decision": selection_decision,
        "selection_verdict": selection_verdict,
        "quality_classification": quality_classification,
        "source_manifest_confirmation_validation_complete": confirmation_validation_complete,
        "source_manifest_confirmation_partial": True if ready else False,
        "source_manifest_registration_complete": False,
        "source_manifest_registration_execution_ready": False,
        "source_join_execution_ready": False,
        "expanded_data_artifact_written": False,
        "feature_source_join_run": False,
        "research_eval_run": False,
        "model_fit_run": False,
        "train_run": False,
        "test_run": False,
        "score_run": False,
        "prediction_run": False,
        "promotion_authorized": False,
        "current_best_changed_now": False,
        "source_user_confirmed_packet_csv": str(source_csv) if source_csv else "",
        "accepted_manifest_family_count": accepted_count,
        "accepted_manifest_families": accepted_families,
        "rejected_manifest_family_count": rejected_count,
        "rejected_manifest_families": rejected_families,
        "unresolved_required_manifest_family_count": len(unresolved_families),
        "unresolved_required_manifest_families": unresolved_families,
        "base_target_attached_rows_confirmed": "base_target_attached_rows" in accepted_families,
        "gamma_context_source_confirmed": "gamma_context_source" in accepted_families,
        "orderflow_context_source_confirmed": "orderflow_context_source" in accepted_families,
        "recommended_policy_action": "park_join_path_until_gamma_and_orderflow_source_manifests_are_provided_with_real_keys",
        "recommended_next_gate": "PARK_UNTIL_GAMMA_AND_ORDERFLOW_SOURCE_MANIFESTS_ARE_CORRECTED",
        "alternative_safe_gate": "PARK_AND_STOP",
        "pass_count": sum(1 for c in checks if c.get("status") == "PASS"),
        "fail_required_count": fail_required_count,
        "warning_count": warning_count,
        "guardrail_violation_count": 0,
        "artifact_json": str(artifact_json),
        "artifact_md": str(artifact_md),
        "artifact_decision_csv": str(artifact_decision_csv),
        "artifact_validation_csv": str(artifact_validation_csv),
        "artifact_restart_requirements_csv": str(artifact_restart_requirements_csv),
        "artifact_checks_csv": str(artifact_checks_csv),
    }

    write_json(artifact_json, payload)
    artifact_md.write_text(
        "# HYDRA H001 Source-Manifest Confirmation Validation\n\n"
        f"- overall_status: `{overall_status}`\n"
        f"- base_confirmed: `{payload['base_target_attached_rows_confirmed']}`\n"
        f"- gamma_confirmed: `{payload['gamma_context_source_confirmed']}`\n"
        f"- orderflow_confirmed: `{payload['orderflow_context_source_confirmed']}`\n"
        f"- source_join_execution_ready: `False`\n"
        f"- recommended_next_gate: `{payload['recommended_next_gate']}`\n\n"
        "Partial confirmation accepted. Join path remains parked until gamma/orderflow manifests are corrected.\n",
        encoding="utf-8",
        newline="\n",
    )
    write_single_row_csv(artifact_decision_csv, payload)
    write_rows_csv(artifact_validation_csv, validation_rows)
    write_rows_csv(artifact_restart_requirements_csv, restart_requirements_rows)
    write_rows_csv(artifact_checks_csv, checks)

    print("HYDRA H001 SOURCE-MANIFEST CONFIRMATION VALIDATION CONTRACT COMPLETE")
    ordered_keys = [
        "overall_status",
        "final_lane_status",
        "validation_status",
        "selection_decision",
        "selection_verdict",
        "quality_classification",
        "source_manifest_confirmation_validation_complete",
        "source_manifest_confirmation_partial",
        "source_manifest_registration_complete",
        "source_manifest_registration_execution_ready",
        "source_join_execution_ready",
        "expanded_data_artifact_written",
        "feature_source_join_run",
        "research_eval_run",
        "model_fit_run",
        "train_run",
        "score_run",
        "prediction_run",
        "promotion_authorized",
        "accepted_manifest_family_count",
        "accepted_manifest_families",
        "rejected_manifest_family_count",
        "rejected_manifest_families",
        "unresolved_required_manifest_family_count",
        "unresolved_required_manifest_families",
        "base_target_attached_rows_confirmed",
        "gamma_context_source_confirmed",
        "orderflow_context_source_confirmed",
        "recommended_next_gate",
        "fail_required_count",
        "warning_count",
        "guardrail_violation_count",
        "artifact_validation_csv",
        "artifact_restart_requirements_csv",
        "artifact_json",
        "artifact_md",
    ]
    print_kv(payload, ordered_keys)

    return 0 if overall_status in {"PASS", "PASS_WITH_WARNINGS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
