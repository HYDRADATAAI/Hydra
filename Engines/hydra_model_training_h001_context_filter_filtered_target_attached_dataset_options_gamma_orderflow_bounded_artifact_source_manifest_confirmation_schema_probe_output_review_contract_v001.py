#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HYDRA MODEL TRAINING H001 SOURCE-MANIFEST CONFIRMATION SCHEMA PROBE
OUTPUT REVIEW CONTRACT v0.1

Purpose:
  Review the source-manifest confirmation packet schema probe output.

Expected prior result:
  - schema_probe_ready: True
  - probe_row_count: 3
  - candidate_manifest_readable_count: 3
  - suggested_confirmation_row_count: 3
  - confirmation_packet_confirmed: False
  - manifest_registration_complete: False
  - source_join_execution_ready: False

This output review verifies the probe outputs exist and are complete for the
three required manifest families. It does NOT accept suggestions as human
confirmation. It keeps all registration/join/model paths blocked until the
confirmation packet has explicit YES/NO decisions.

Guardrails:
  - Output review only
  - No automatic confirmation
  - No manifest validation as registered
  - No manifest registration
  - No source join execution
  - No expanded data artifact write
  - No raw source scan / no full source-file load
  - No research eval
  - No model fit / train / score / prediction / promotion
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ENGINE_ID = "hydra_model_training_h001_context_filter_filtered_target_attached_dataset_options_gamma_orderflow_bounded_artifact_source_manifest_confirmation_schema_probe_output_review_contract_v001.py"
VERSION = "v0_1"
MODE = "SOURCE_MANIFEST_CONFIRMATION_SCHEMA_PROBE_OUTPUT_REVIEW_ONLY_NO_CONFIRMATION_NO_VALIDATION_NO_REGISTRATION_NO_JOIN_NO_TRAIN"
GUARDRAIL = "SCHEMA_PROBE_OUTPUT_REVIEW_ONLY_NO_AUTO_CONFIRM_NO_MANIFEST_VALIDATION_NO_SOURCE_JOIN_NO_MODEL_FIT_NO_PROMOTION"

SOURCE_SCHEMA_PROBE_GLOBS = [
    "H001_SOURCE_MANIFEST_CONFIRMATION_SCHEMA_PROBE_V0_1_*.json",
]

REQUIRED_FAMILIES = {"gamma_context_source", "orderflow_context_source", "base_target_attached_rows"}


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


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def print_kv(payload: Dict[str, Any], keys: Iterable[str]) -> None:
    for k in keys:
        if k in payload:
            print(f"{k}: {payload[k]}")


def as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def safe_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        s = str(v).strip()
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default


def resolve_path(root: Path, value: Any) -> Optional[Path]:
    if not value:
        return None
    p = Path(str(value))
    if p.exists():
        return p
    rel = root / str(value).replace("\\", "/")
    if rel.exists():
        return rel
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hydra-root", required=True)
    args = ap.parse_args()

    hydra_root = Path(args.hydra_root).expanduser().resolve()
    docs_dir = hydra_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    print("HYDRA MODEL TRAINING H001 SOURCE-MANIFEST CONFIRMATION SCHEMA PROBE OUTPUT REVIEW CONTRACT START")
    print(f"engine_id: {ENGINE_ID}")
    print(f"version: {VERSION}")
    print(f"hydra_root: {hydra_root}")
    print(f"mode: {MODE}")
    print(f"guardrail: {GUARDRAIL}")

    checks: List[Dict[str, Any]] = []

    source_json = latest_file_multi(hydra_root, "docs", SOURCE_SCHEMA_PROBE_GLOBS)
    source: Dict[str, Any] = {}
    if source_json:
        try:
            source = load_json(source_json)
            checks.append({"check_name": "source_schema_probe_json_loadable", "status": "PASS", "detail": str(source_json)})
        except Exception as e:
            checks.append({"check_name": "source_schema_probe_json_loadable", "status": "FAIL_REQUIRED", "detail": repr(e)})
    else:
        checks.append({"check_name": "source_schema_probe_json_found", "status": "FAIL_REQUIRED", "detail": SOURCE_SCHEMA_PROBE_GLOBS})

    source_ready = (
        source.get("overall_status") in {"PASS", "PASS_WITH_WARNINGS"}
        and as_bool(source.get("schema_probe_ready"))
        and not as_bool(source.get("confirmation_packet_confirmed"))
        and not as_bool(source.get("manifest_registration_complete"))
        and not as_bool(source.get("manifest_registration_execution_ready"))
        and not as_bool(source.get("source_join_execution_ready"))
        and not as_bool(source.get("expanded_data_artifact_written"))
        and not as_bool(source.get("feature_source_join_run"))
        and not as_bool(source.get("model_fit_run"))
        and not as_bool(source.get("train_run"))
        and not as_bool(source.get("score_run"))
        and not as_bool(source.get("prediction_run"))
        and not as_bool(source.get("promotion_authorized"))
        and safe_int(source.get("probe_row_count")) == 3
        and safe_int(source.get("candidate_manifest_readable_count")) == 3
        and safe_int(source.get("suggested_confirmation_row_count")) == 3
    )
    checks.append({
        "check_name": "source_schema_probe_ready_for_output_review",
        "status": "PASS" if source_ready else "FAIL_REQUIRED",
        "detail": {
            "overall_status": source.get("overall_status"),
            "schema_probe_ready": source.get("schema_probe_ready"),
            "confirmation_packet_confirmed": source.get("confirmation_packet_confirmed"),
            "source_join_execution_ready": source.get("source_join_execution_ready"),
            "probe_row_count": source.get("probe_row_count"),
            "candidate_manifest_readable_count": source.get("candidate_manifest_readable_count"),
            "suggested_confirmation_row_count": source.get("suggested_confirmation_row_count"),
        },
    })

    probe_csv = resolve_path(hydra_root, source.get("artifact_probe_csv"))
    suggested_csv = resolve_path(hydra_root, source.get("artifact_suggested_confirmation_csv"))

    artifact_review_rows: List[Dict[str, Any]] = []
    missing_artifacts: List[str] = []
    for name, p in {"probe_csv": probe_csv, "suggested_confirmation_csv": suggested_csv}.items():
        exists = bool(p and p.exists())
        artifact_review_rows.append({
            "artifact_name": name,
            "artifact_path": str(p) if p else "",
            "artifact_exists": exists,
            "csv_row_count": count_csv_rows(p) if exists and p and p.suffix.lower() == ".csv" else "",
        })
        if not exists:
            missing_artifacts.append(name)
    checks.append({
        "check_name": "schema_probe_artifacts_exist",
        "status": "PASS" if not missing_artifacts else "FAIL_REQUIRED",
        "detail": missing_artifacts,
    })

    probe_rows = read_csv_rows(probe_csv) if probe_csv and probe_csv.exists() else []
    suggested_rows = read_csv_rows(suggested_csv) if suggested_csv and suggested_csv.exists() else []

    probe_families = {str(r.get("manifest_family")) for r in probe_rows}
    suggested_families = {str(r.get("manifest_family")) for r in suggested_rows}

    checks.extend([
        {"check_name": "probe_rows_cover_required_families", "status": "PASS" if REQUIRED_FAMILIES.issubset(probe_families) and len(probe_rows) == 3 else "FAIL_REQUIRED", "detail": {"families": sorted(probe_families), "row_count": len(probe_rows)}},
        {"check_name": "suggested_confirmation_rows_cover_required_families", "status": "PASS" if REQUIRED_FAMILIES.issubset(suggested_families) and len(suggested_rows) == 3 else "FAIL_REQUIRED", "detail": {"families": sorted(suggested_families), "row_count": len(suggested_rows)}},
    ])

    readable_rows = [r for r in probe_rows if str(r.get("candidate_exists")).lower() in {"true", "1", "yes"}]
    checks.append({
        "check_name": "all_candidate_manifests_readable_in_probe",
        "status": "PASS" if len(readable_rows) == 3 else "WARNING",
        "detail": {"readable_count": len(readable_rows), "required": 3},
    })

    # Suggested confirmation rows should remain REVIEW, not YES.
    auto_yes_rows = [r for r in suggested_rows if str(r.get("confirm_candidate_path", "")).strip().upper() == "YES"]
    checks.append({
        "check_name": "suggestions_do_not_auto_confirm",
        "status": "PASS" if not auto_yes_rows else "FAIL_REQUIRED",
        "detail": {"auto_yes_count": len(auto_yes_rows)},
    })

    reviewed_suggestion_rows: List[Dict[str, Any]] = []
    for row in suggested_rows:
        reviewed_suggestion_rows.append({
            "manifest_family": row.get("manifest_family"),
            "candidate_manifest_path": row.get("candidate_manifest_path"),
            "suggested_schema_id": row.get("confirmed_schema_id"),
            "suggested_symbol_key": row.get("confirmed_symbol_key"),
            "suggested_session_date_key": row.get("confirmed_session_date_key"),
            "suggested_timestamp_or_row_id_key": row.get("confirmed_timestamp_or_row_id_key"),
            "confirm_candidate_path": row.get("confirm_candidate_path"),
            "review_status": "NEEDS_USER_YES_OR_NO",
            "note": "Do not treat REVIEW as YES. User must confirm/correct before validation.",
        })

    fail_required_count = sum(1 for c in checks if c.get("status") == "FAIL_REQUIRED")
    warning_count = sum(1 for c in checks if c.get("status") == "WARNING") + 1
    ready = fail_required_count == 0
    overall_status = "PASS_WITH_WARNINGS" if ready else "FAIL_REQUIRED"

    stamp = now_stamp()
    base = f"H001_SOURCE_MANIFEST_CONFIRMATION_SCHEMA_PROBE_OUT_REVIEW_V0_1_{stamp}"
    artifact_json = docs_dir / f"{base}.json"
    artifact_md = docs_dir / f"{base}.md"
    artifact_decision_csv = docs_dir / f"{base}_DECISION.csv"
    artifact_artifact_review_csv = docs_dir / f"{base}_ARTIFACT_REVIEW.csv"
    artifact_probe_review_csv = docs_dir / f"{base}_PROBE_REVIEW.csv"
    artifact_suggested_confirmation_review_csv = docs_dir / f"{base}_SUGGESTED_CONFIRMATION_REVIEW.csv"
    artifact_checks_csv = docs_dir / f"{base}_CHECKS.csv"

    if ready:
        final_lane_status = "MODEL_TRAINING_H001_SOURCE_MANIFEST_CONFIRMATION_SCHEMA_PROBE_OUTPUT_REVIEW_PASS_WITH_WARNINGS_PARKED"
        review_status = "H001_SOURCE_MANIFEST_CONFIRMATION_SCHEMA_PROBE_OUTPUT_REVIEW_COMPLETE_WITH_WARNINGS"
        selection_decision = "ACCEPT_SCHEMA_PROBE_OUTPUT_AND_PARK_FOR_USER_CONFIRMATION_DECISIONS"
        selection_verdict = "PASS_WITH_WARNINGS_SCHEMA_PROBE_OUTPUT_VALID_SUGGESTIONS_ONLY_NO_CONFIRMATION_NO_JOIN"
        quality_classification = "H001_SOURCE_MANIFEST_SCHEMA_PROBE_OUTPUT_ACCEPTED_AWAITING_YES_NO_CONFIRMATION"
        output_review_complete = True
    else:
        final_lane_status = "MODEL_TRAINING_H001_SOURCE_MANIFEST_CONFIRMATION_SCHEMA_PROBE_OUTPUT_REVIEW_FAIL_PARKED"
        review_status = "H001_SOURCE_MANIFEST_CONFIRMATION_SCHEMA_PROBE_OUTPUT_REVIEW_INCOMPLETE"
        selection_decision = "PARK_SCHEMA_PROBE_OUTPUT_REVIEW_REQUIRED_CHECK_FAILED"
        selection_verdict = "FAIL_REQUIRED_NO_SCHEMA_PROBE_OUTPUT_REVIEW_NO_JOIN"
        quality_classification = "H001_SOURCE_MANIFEST_SCHEMA_PROBE_OUTPUT_NOT_ACCEPTED"
        output_review_complete = False

    payload: Dict[str, Any] = {
        "overall_status": overall_status,
        "final_lane_status": final_lane_status,
        "review_status": review_status,
        "selection_decision": selection_decision,
        "selection_verdict": selection_verdict,
        "quality_classification": quality_classification,
        "schema_probe_output_review_complete": output_review_complete,
        "schema_probe_output_valid": ready,
        "suggested_confirmation_packet_valid": ready,
        "confirmation_packet_confirmed": False,
        "confirmation_packet_has_yes_no_decisions": False,
        "manifest_registration_complete": False,
        "manifest_registration_execution_ready": False,
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
        "source_schema_probe_json": str(source_json) if source_json else "",
        "artifact_probe_csv": str(probe_csv) if probe_csv else "",
        "artifact_suggested_confirmation_csv": str(suggested_csv) if suggested_csv else "",
        "probe_row_count": len(probe_rows),
        "suggested_confirmation_row_count": len(suggested_rows),
        "candidate_manifest_readable_count": len(readable_rows),
        "manual_yes_no_required": True,
        "recommended_policy_action": "copy_or_review_suggested_confirmation_rows_then_set_confirm_candidate_path_yes_or_no",
        "recommended_next_gate": "PARK_UNTIL_CONFIRMATION_PACKET_HAS_YES_NO_DECISIONS",
        "alternative_safe_gate": "PARK_AND_STOP",
        "pass_count": sum(1 for c in checks if c.get("status") == "PASS"),
        "fail_required_count": fail_required_count,
        "warning_count": warning_count,
        "guardrail_violation_count": 0,
        "artifact_json": str(artifact_json),
        "artifact_md": str(artifact_md),
        "artifact_decision_csv": str(artifact_decision_csv),
        "artifact_artifact_review_csv": str(artifact_artifact_review_csv),
        "artifact_probe_review_csv": str(artifact_probe_review_csv),
        "artifact_suggested_confirmation_review_csv": str(artifact_suggested_confirmation_review_csv),
        "artifact_checks_csv": str(artifact_checks_csv),
    }

    write_json(artifact_json, payload)
    artifact_md.write_text(
        "# HYDRA H001 Source-Manifest Confirmation Schema Probe Output Review\n\n"
        f"- overall_status: `{overall_status}`\n"
        f"- output_review_complete: `{output_review_complete}`\n"
        f"- confirmation_packet_confirmed: `False`\n"
        f"- source_join_execution_ready: `False`\n"
        f"- recommended_next_gate: `{payload['recommended_next_gate']}`\n\n"
        "Schema/key suggestions exist, but user YES/NO confirmation is still required.\n",
        encoding="utf-8",
        newline="\n",
    )

    write_single_row_csv(artifact_decision_csv, payload)
    write_rows_csv(artifact_artifact_review_csv, artifact_review_rows)
    write_rows_csv(artifact_probe_review_csv, probe_rows)
    write_rows_csv(artifact_suggested_confirmation_review_csv, reviewed_suggestion_rows)
    write_rows_csv(artifact_checks_csv, checks)

    print("HYDRA MODEL TRAINING H001 SOURCE-MANIFEST CONFIRMATION SCHEMA PROBE OUTPUT REVIEW CONTRACT COMPLETE")
    ordered_keys = [
        "overall_status",
        "final_lane_status",
        "review_status",
        "selection_decision",
        "selection_verdict",
        "quality_classification",
        "schema_probe_output_review_complete",
        "schema_probe_output_valid",
        "suggested_confirmation_packet_valid",
        "confirmation_packet_confirmed",
        "confirmation_packet_has_yes_no_decisions",
        "manifest_registration_complete",
        "manifest_registration_execution_ready",
        "source_join_execution_ready",
        "expanded_data_artifact_written",
        "feature_source_join_run",
        "research_eval_run",
        "model_fit_run",
        "train_run",
        "score_run",
        "prediction_run",
        "promotion_authorized",
        "probe_row_count",
        "suggested_confirmation_row_count",
        "candidate_manifest_readable_count",
        "manual_yes_no_required",
        "recommended_policy_action",
        "recommended_next_gate",
        "pass_count",
        "fail_required_count",
        "warning_count",
        "guardrail_violation_count",
        "artifact_suggested_confirmation_review_csv",
        "artifact_json",
        "artifact_md",
    ]
    print_kv(payload, ordered_keys)

    return 0 if overall_status in {"PASS", "PASS_WITH_WARNINGS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
