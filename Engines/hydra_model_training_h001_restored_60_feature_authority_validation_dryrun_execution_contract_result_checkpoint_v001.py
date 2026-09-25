#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HYDRA H001 Restored 60-Feature Authority Validation Dryrun Execution Contract Result Checkpoint v0.1

Contract:
  MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_RESULT_CHECKPOINT_v0.1_AFTER_OUTPUT_REVIEW

Purpose:
  Register/checkpoint the restored 60-feature authority validation dryrun output review result.
  The output review accepted the run as diagnostic evidence only: authority is clean/matched,
  but balanced accuracy degraded versus locked reference, so no promotion.

Guardrails:
  - Checkpoint only.
  - Reads prior output-review JSON only.
  - No dataset header/value read.
  - No feature manifest read.
  - No authority artifact scan.
  - No model fit/training.
  - No scoring/prediction.
  - No validation/test metric computation.
  - No test read.
  - No model artifact.
  - No row-level predictions.
  - No sim/backtest.
  - No trade signals.
  - No source/evidence/Review Gate/queue mutation.
  - No current-best promotion.
  - No quarantine removal.
  - No branch reopening.
  - No dataset/split mutation.
  - No canonical feature/schema mutation.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ENGINE_ID = "hydra_model_training_h001_restored_60_feature_authority_validation_dryrun_execution_contract_result_checkpoint_v001.py"
VERSION = "v0_1"
CONTRACT_ID = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_RESULT_CHECKPOINT_v0.1_AFTER_OUTPUT_REVIEW"

PRIOR_DIR_REL = Path("data") / "canonical" / "h001_restored_60_feature_authority_validation_dryrun_output_review_contract_v0_1"
OUT_DIR_REL = Path("data") / "canonical" / "h001_restored_60_feature_authority_validation_dryrun_result_checkpoint_v0_1"

MODE = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_RESULT_CHECKPOINT_ONLY_NO_DATASET_NO_TRAIN_NO_SCORE_NO_PROMOTION"
GUARDRAIL = (
    "RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_RESULT_CHECKPOINT_ONLY_READS_PRIOR_OUTPUT_REVIEW_JSON_"
    "NO_DATASET_HEADER_READ_NO_DATASET_VALUE_READ_NO_FEATURE_MANIFEST_READ_NO_AUTHORITY_SCAN_"
    "NO_TRAIN_NO_SCORE_NO_PREDICT_NO_VALIDATION_TEST_METRIC_COMPUTE_NO_TEST_READ_NO_MODEL_ARTIFACT_"
    "NO_ROW_PREDICTIONS_NO_SIM_NO_QUEUE_NO_REVIEW_GATE_MUTATION_NO_SOURCE_MUTATION_NO_PROMOTION_"
    "NO_QUARANTINE_REMOVAL_NO_BRANCH_REOPEN_NO_SCHEMA_MUTATION"
)

EXPECTED_SOURCE_STATUS = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_COMPLETE"
EXPECTED_SOURCE_DECISION = "ACCEPT_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_FOR_RESULT_CHECKPOINT_NOT_PROMOTION"
EXPECTED_SOURCE_VERDICT = "PASS_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_READY_FOR_RESULT_CHECKPOINT"
EXPECTED_SOURCE_QUALITY = "H001_RESTORED_60_FEATURE_AUTHORITY_OUTPUT_REVIEW_AUTHORITY_MATCHED_BALANCED_ACCURACY_DEGRADED_NOT_PROMOTION_READY"
EXPECTED_HASH = "a24a91df7f5fa1b93d8113a59f9c14756e5c1f18436186e09b5789ae2bd3630d"

FINAL_STATUS_PASS = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_RESULT_CHECKPOINT_PASS_PARKED"
CHECKPOINT_STATUS_PASS = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_RESULT_CHECKPOINT_COMPLETE"
CHECKPOINT_DECISION_PASS = "ACCEPT_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_RESULT_CHECKPOINT_DIAGNOSTIC_ONLY_NO_PROMOTION"
CHECKPOINT_VERDICT_PASS = "PASS_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_RESULT_CHECKPOINT_READY_FOR_CLOSEOUT_OR_NEXT_LANE_SELECTION"
QUALITY_PASS = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_RESULT_CHECKPOINT_AUTHORITY_MATCHED_BALANCED_ACCURACY_DEGRADED_NO_PROMOTION"

NEXT_GATE_PASS = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_CLOSEOUT_OR_NEXT_LANE_SELECTION_CONTRACT_v0.1_AFTER_RESTORED_AUTHORITY_DRYRUN_CHECKPOINT"
LEGAL_NEXT_GATES_PASS = [NEXT_GATE_PASS, "PARK_AND_STOP"]


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def iso_now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def stringify(v: Any) -> str:
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    if v is None:
        return ""
    return str(v)


def boolish(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes", "y", "pass"}
    return bool(v)


def fnum(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def latest_result_json(directory: Path) -> Path:
    candidates = sorted(directory.glob("result_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No result_*.json found in {directory}")
    return candidates[0]


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, sort_keys=False)
        f.write("\n")
    tmp.replace(path)


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for k in row:
                if k not in fieldnames:
                    fieldnames.append(k)
        if not fieldnames:
            fieldnames = ["empty"]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: stringify(row.get(k, "")) for k in fieldnames})
    tmp.replace(path)


def add_check(checks: List[Dict[str, Any]], check_id: str, expected: Any, actual: Any, status: str, severity: str = "INFO") -> None:
    checks.append({
        "check_id": check_id,
        "expected": expected,
        "actual": actual,
        "status": status,
        "severity": severity,
    })


def write_md(path: Path, result: Dict[str, Any]) -> None:
    lines = [
        "# HYDRA H001 Restored 60-Feature Authority Validation Dryrun Result Checkpoint v0.1",
        "",
        "## Decision",
        "",
        f"- **overall_status**: `{result.get('overall_status')}`",
        f"- **overall_checkpoint_status**: `{result.get('overall_checkpoint_status')}`",
        f"- **checkpoint_ready**: `{result.get('checkpoint_ready')}`",
        f"- **checkpoint_decision**: `{result.get('checkpoint_decision')}`",
        f"- **checkpoint_verdict**: `{result.get('checkpoint_verdict')}`",
        f"- **checkpoint_quality_classification**: `{result.get('checkpoint_quality_classification')}`",
        f"- **recommended_next_gate**: `{result.get('recommended_next_gate')}`",
        "",
        "## Interpretation",
        "",
        result.get("checkpoint_interpretation", ""),
        "",
        "## Authority",
        "",
        f"- **source_feature_count_used**: `{result.get('source_feature_count_used')}`",
        f"- **selected_feature_count**: `{result.get('selected_feature_count')}`",
        f"- **source_feature_order_sha256**: `{result.get('source_feature_order_sha256')}`",
        f"- **selected_feature_order_sha256**: `{result.get('selected_feature_order_sha256')}`",
        f"- **authority_restored_and_matched**: `{result.get('authority_restored_and_matched')}`",
        f"- **export_session_date_excluded**: `{result.get('export_session_date_excluded')}`",
        "",
        "## Metrics",
        "",
        f"- **reference_validation_balanced_accuracy**: `{result.get('reference_validation_balanced_accuracy')}`",
        f"- **validation_balanced_accuracy_new**: `{result.get('validation_balanced_accuracy_new')}`",
        f"- **validation_balanced_accuracy_delta_vs_reference**: `{result.get('validation_balanced_accuracy_delta_vs_reference')}`",
        f"- **material_balanced_accuracy_drop**: `{result.get('material_balanced_accuracy_drop')}`",
        f"- **promotion_supported_now**: `{result.get('promotion_supported_now')}`",
        "",
        "## Guardrails",
        "",
        "- checkpoint only",
        "- no dataset header/value read",
        "- no feature manifest read",
        "- no train/score",
        "- no test read",
        "- no model artifact",
        "- no row-level predictions",
        "- no sim/backtest",
        "- no source/evidence/Review Gate/queue mutation",
        "- no promotion",
        "- no schema mutation",
        "",
        "## Artifacts",
        "",
    ]
    for key in [
        "json",
        "md",
        "checks_csv",
        "checkpoint_summary_csv",
        "metric_carry_forward_csv",
        "authority_carry_forward_csv",
        "quality_carry_forward_csv",
        "blocked_actions_csv",
        "artifact_inventory_csv",
        "next_gate_checklist_csv",
    ]:
        if result.get(key):
            lines.append(f"- **{key}**: `{result[key]}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hydra-root", required=True)
    args = ap.parse_args(argv)

    hydra_root = Path(args.hydra_root).expanduser().resolve()
    docs_dir = hydra_root / "docs"
    prior_dir = hydra_root / PRIOR_DIR_REL
    out_dir = hydra_root / OUT_DIR_REL
    stamp = now_stamp()

    print("HYDRA H001 RESTORED 60-FEATURE AUTHORITY VALIDATION DRYRUN EXECUTION CONTRACT RESULT CHECKPOINT START")
    print(f"engine_id: {ENGINE_ID}")
    print(f"version: {VERSION}")
    print(f"contract_id: {CONTRACT_ID}")
    print(f"hydra_root: {hydra_root}")
    print(f"docs_dir: {docs_dir}")
    print(f"prior_restored_authority_validation_dryrun_output_review_dir: {prior_dir}")
    print(f"mode: {MODE}")
    print(f"guardrail: {GUARDRAIL}")
    print()

    checks: List[Dict[str, Any]] = []
    failures: List[str] = []
    warnings: List[str] = []

    try:
        source_path = latest_result_json(prior_dir)
        source = read_json(source_path)
        add_check(checks, "source_output_review_json_found", "found", str(source_path), "PASS")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    required_matches = [
        ("source_overall_status", "PASS", source.get("overall_status")),
        ("source_review_status", EXPECTED_SOURCE_STATUS, source.get("restored_authority_validation_dryrun_output_review_status")),
        ("source_review_decision", EXPECTED_SOURCE_DECISION, source.get("output_review_decision")),
        ("source_review_verdict", EXPECTED_SOURCE_VERDICT, source.get("output_review_verdict")),
        ("source_quality_classification", EXPECTED_SOURCE_QUALITY, source.get("quality_classification")),
        ("source_feature_count_used", 60, source.get("source_feature_count_used")),
        ("selected_feature_count", 60, source.get("selected_feature_count")),
        ("source_feature_order_sha256", EXPECTED_HASH, source.get("source_feature_order_sha256")),
        ("selected_feature_order_sha256", EXPECTED_HASH, source.get("selected_feature_order_sha256")),
        ("authority_restored_and_matched", True, boolish(source.get("authority_restored_and_matched"))),
        ("export_session_date_excluded", True, boolish(source.get("export_session_date_excluded"))),
        ("material_balanced_accuracy_drop", True, boolish(source.get("material_balanced_accuracy_drop"))),
        ("promotion_supported_now", False, boolish(source.get("promotion_supported_now"))),
        ("output_review_contract_run_now", True, boolish(source.get("output_review_contract_run_now"))),
        ("dataset_header_read_run", False, boolish(source.get("dataset_header_read_run"))),
        ("dataset_value_read_run", False, boolish(source.get("dataset_value_read_run"))),
        ("model_fit_or_training_run", False, boolish(source.get("model_fit_or_training_run"))),
        ("model_scoring_or_prediction_run", False, boolish(source.get("model_scoring_or_prediction_run"))),
        ("validation_or_test_metric_computation_run", False, boolish(source.get("validation_or_test_metric_computation_run"))),
        ("test_values_read", False, boolish(source.get("test_values_read"))),
        ("model_artifact_written", False, boolish(source.get("model_artifact_written"))),
        ("canonical_feature_schema_mutation", False, boolish(source.get("canonical_feature_schema_mutation"))),
    ]

    for cid, expected, actual in required_matches:
        status = "PASS" if actual == expected else "FAIL"
        add_check(checks, cid, expected, actual, status, "CRITICAL" if status == "FAIL" else "INFO")
        if status == "FAIL":
            failures.append(f"{cid}: expected={expected!r}, actual={actual!r}")

    bacc_delta = fnum(source.get("validation_balanced_accuracy_delta_vs_reference"))
    if bacc_delta is None or bacc_delta >= 0:
        failures.append("Balanced accuracy delta is not a negative degradation as expected by review classification.")
        add_check(checks, "balanced_accuracy_delta_negative", "negative", bacc_delta, "FAIL", "CRITICAL")
    else:
        add_check(checks, "balanced_accuracy_delta_negative", "negative", bacc_delta, "PASS")

    if failures:
        overall_status = "FAIL"
        checkpoint_status = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_RESULT_CHECKPOINT_FAIL_PARKED"
        checkpoint_ready = False
        decision = "REJECT_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_RESULT_CHECKPOINT_REQUIRED_CHECKS_FAILED"
        verdict = "FAIL_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_RESULT_CHECKPOINT_NOT_READY"
        quality = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_RESULT_CHECKPOINT_FAILED"
        next_gate = "PARK_AND_STOP"
        legal_next = ["PARK_AND_STOP"]
    else:
        overall_status = "PASS"
        checkpoint_status = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_RESULT_CHECK_OFF_READY"
        checkpoint_ready = True
        decision = CHECKPOINT_DECISION_PASS
        verdict = CHECKPOINT_VERDICT_PASS
        quality = QUALITY_PASS
        next_gate = NEXT_GATE_PASS
        legal_next = LEGAL_NEXT_GATES_PASS

    result: Dict[str, Any] = {
        "engine_id": ENGINE_ID,
        "version": VERSION,
        "contract_id": CONTRACT_ID,
        "run_timestamp": iso_now(),
        "hydra_root": str(hydra_root),
        "docs_dir": str(docs_dir),
        "mode": MODE,
        "guardrail": GUARDRAIL,
        "overall_status": overall_status,
        "overall_checkpoint_status": checkpoint_status,
        "checkpoint_ready": checkpoint_ready,
        "content_execution_complete": True,
        "checkpoint_decision": decision,
        "checkpoint_verdict": verdict,
        "checkpoint_reason": (
            "accepted_restored_60_feature_authority_validation_dryrun_output_review_checkpointed_diagnostic_only_no_promotion"
            if overall_status == "PASS"
            else "restored_60_feature_authority_validation_dryrun_checkpoint_failed_required_checks"
        ),
        "checkpoint_quality_classification": quality,
        "checkpoint_interpretation": (
            "Restored 60-feature authority validation dryrun result checkpoint accepted. Feature authority is clean and matched: "
            "selected feature count is 60, selected hash equals source hash, and export_session_date is excluded. "
            "However, validation balanced accuracy degraded versus the locked diagnostic reference, so the dryrun is diagnostic-only and not promotion-ready. "
            "Proceed only to closeout or next-lane selection; do not promote, do not remove quarantine, do not read test, and do not mutate schema."
            if overall_status == "PASS"
            else "Restored 60-feature authority validation dryrun result checkpoint failed required checks. Park."
        ),
        "source_output_review_json": str(source_path),
        "source_validation_dryrun_json": source.get("source_restored_authority_validation_dryrun_json"),
        "source_feature_count_used": source.get("source_feature_count_used"),
        "selected_feature_count": source.get("selected_feature_count"),
        "source_feature_order_sha256": source.get("source_feature_order_sha256"),
        "selected_feature_order_sha256": source.get("selected_feature_order_sha256"),
        "selected_feature_hash_matches_expected_source_hash": source.get("selected_feature_hash_matches_expected_source_hash"),
        "export_session_date_excluded": source.get("export_session_date_excluded"),
        "feature_resolution_mode": source.get("feature_resolution_mode"),
        "authority_restored_and_matched": source.get("authority_restored_and_matched"),
        "reference_validation_accuracy": source.get("reference_validation_accuracy"),
        "validation_accuracy_new": source.get("validation_accuracy_new"),
        "validation_accuracy_delta_vs_reference": source.get("validation_accuracy_delta_vs_reference"),
        "reference_validation_balanced_accuracy": source.get("reference_validation_balanced_accuracy"),
        "validation_balanced_accuracy_new": source.get("validation_balanced_accuracy_new"),
        "validation_balanced_accuracy_delta_vs_reference": source.get("validation_balanced_accuracy_delta_vs_reference"),
        "reference_validation_macro_f1": source.get("reference_validation_macro_f1"),
        "validation_macro_f1_new": source.get("validation_macro_f1_new"),
        "validation_macro_f1_delta_vs_reference": source.get("validation_macro_f1_delta_vs_reference"),
        "reference_validation_weighted_f1": source.get("reference_validation_weighted_f1"),
        "validation_weighted_f1_new": source.get("validation_weighted_f1_new"),
        "validation_weighted_f1_delta_vs_reference": source.get("validation_weighted_f1_delta_vs_reference"),
        "material_balanced_accuracy_drop": source.get("material_balanced_accuracy_drop"),
        "promotion_supported_now": False,
        "current_best_promotion_authorized": False,
        "quarantine_removal_authorized": False,
        "schema_mutation_authorized": False,
        "checkpoint_registrar_run_now": True,
        "dataset_header_read_run": False,
        "dataset_value_read_run": False,
        "feature_manifest_read_run": False,
        "authority_artifact_scan_run": False,
        "model_fit_or_training_run": False,
        "model_scoring_or_prediction_run": False,
        "validation_or_test_metric_computation_run": False,
        "train_values_read": False,
        "validation_values_read": False,
        "test_values_read": False,
        "test_model_metrics_computed": False,
        "model_artifact_written": False,
        "row_level_predictions_written": False,
        "simulation_or_backtest_run": False,
        "trade_signal_generation_run": False,
        "queue_mutation_run": False,
        "review_gate_mutation_run": False,
        "source_evidence_mutation_run": False,
        "current_best_promotion_run": False,
        "quarantine_removal_run": False,
        "closed_branch_reopened_now": False,
        "dataset_split_mutation_run": False,
        "canonical_feature_schema_mutation": False,
        "fail_required_count": len(failures),
        "warning_count": len(warnings),
        "critical_fail_count": len(failures),
        "pass_count": sum(1 for c in checks if c.get("status") == "PASS"),
        "required_total": len(checks),
        "recommended_next_gate": next_gate,
        "legal_next_gates": legal_next,
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"result_{stamp}.json"
    md_path = docs_dir / f"HYDRA_MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_RESULT_CHECKPOINT_V0_1_{stamp}.md"
    checks_path = out_dir / f"checks_{stamp}.csv"
    checkpoint_summary_path = out_dir / f"checkpoint_summary_{stamp}.csv"
    metric_path = out_dir / f"metric_carry_forward_{stamp}.csv"
    authority_path = out_dir / f"authority_carry_forward_{stamp}.csv"
    quality_path = out_dir / f"quality_carry_forward_{stamp}.csv"
    blocked_path = out_dir / f"blocked_actions_{stamp}.csv"
    artifact_path = out_dir / f"artifact_inventory_{stamp}.csv"
    next_path = out_dir / f"next_gate_checklist_{stamp}.csv"

    result.update({
        "json": str(json_path),
        "md": str(md_path),
        "checks_csv": str(checks_path),
        "checkpoint_summary_csv": str(checkpoint_summary_path),
        "metric_carry_forward_csv": str(metric_path),
        "authority_carry_forward_csv": str(authority_path),
        "quality_carry_forward_csv": str(quality_path),
        "blocked_actions_csv": str(blocked_path),
        "artifact_inventory_csv": str(artifact_path),
        "next_gate_checklist_csv": str(next_path),
    })

    checkpoint_rows = [{
        "contract_id": CONTRACT_ID,
        "engine_id": ENGINE_ID,
        "version": VERSION,
        "timestamp": result["run_timestamp"],
        "overall_status": overall_status,
        "overall_checkpoint_status": checkpoint_status,
        "checkpoint_ready": checkpoint_ready,
        "decision": decision,
        "verdict": verdict,
        "quality_classification": quality,
        "source_output_review_json": str(source_path),
        "recommended_next_gate": next_gate,
        "legal_next_gates": legal_next,
        "fail_required_count": len(failures),
        "warning_count": len(warnings),
    }]

    metric_rows = [
        {"metric": "validation_accuracy", "reference": result["reference_validation_accuracy"], "new": result["validation_accuracy_new"], "delta": result["validation_accuracy_delta_vs_reference"]},
        {"metric": "validation_balanced_accuracy", "reference": result["reference_validation_balanced_accuracy"], "new": result["validation_balanced_accuracy_new"], "delta": result["validation_balanced_accuracy_delta_vs_reference"]},
        {"metric": "validation_macro_f1", "reference": result["reference_validation_macro_f1"], "new": result["validation_macro_f1_new"], "delta": result["validation_macro_f1_delta_vs_reference"]},
        {"metric": "validation_weighted_f1", "reference": result["reference_validation_weighted_f1"], "new": result["validation_weighted_f1_new"], "delta": result["validation_weighted_f1_delta_vs_reference"]},
    ]

    authority_rows = [{
        "authority_id": "AUTH_001_RESTORED_60_FEATURE_MATCHED",
        "source_feature_count_used": result["source_feature_count_used"],
        "selected_feature_count": result["selected_feature_count"],
        "source_feature_order_sha256": result["source_feature_order_sha256"],
        "selected_feature_order_sha256": result["selected_feature_order_sha256"],
        "selected_feature_hash_matches_expected_source_hash": result["selected_feature_hash_matches_expected_source_hash"],
        "export_session_date_excluded": result["export_session_date_excluded"],
        "feature_resolution_mode": result["feature_resolution_mode"],
        "authority_restored_and_matched": result["authority_restored_and_matched"],
    }]

    quality_rows = [
        {"finding_id": "QUALITY_001", "finding": "Restored 60-feature authority matched exactly.", "status": "PASS" if boolish(result["authority_restored_and_matched"]) else "FAIL"},
        {"finding_id": "QUALITY_002", "finding": "Balanced accuracy degraded versus locked reference.", "status": "WARN" if boolish(result["material_balanced_accuracy_drop"]) else "PASS"},
        {"finding_id": "QUALITY_003", "finding": "Promotion not supported.", "status": "PASS"},
        {"finding_id": "QUALITY_004", "finding": "Checkpoint complete and ready for closeout/next-lane selection.", "status": "PASS" if checkpoint_ready else "FAIL"},
    ]

    blocked_rows = [
        {"action_id": "BLOCK_001", "action": "dataset_header_or_value_read_now", "blocked": True},
        {"action_id": "BLOCK_002", "action": "feature_manifest_read_now", "blocked": True},
        {"action_id": "BLOCK_003", "action": "authority_scan_now", "blocked": True},
        {"action_id": "BLOCK_004", "action": "model_fit_or_training_now", "blocked": True},
        {"action_id": "BLOCK_005", "action": "model_scoring_or_prediction_now", "blocked": True},
        {"action_id": "BLOCK_006", "action": "validation_or_test_metric_computation_now", "blocked": True},
        {"action_id": "BLOCK_007", "action": "test_value_read_now", "blocked": True},
        {"action_id": "BLOCK_008", "action": "model_artifact_write_now", "blocked": True},
        {"action_id": "BLOCK_009", "action": "row_level_prediction_export_now", "blocked": True},
        {"action_id": "BLOCK_010", "action": "simulation_or_backtest_now", "blocked": True},
        {"action_id": "BLOCK_011", "action": "source_evidence_review_gate_queue_mutation_now", "blocked": True},
        {"action_id": "BLOCK_012", "action": "current_best_promotion_now", "blocked": True},
        {"action_id": "BLOCK_013", "action": "quarantine_removal_now", "blocked": True},
        {"action_id": "BLOCK_014", "action": "branch_reopen_now", "blocked": True},
        {"action_id": "BLOCK_015", "action": "schema_mutation_now", "blocked": True},
    ]

    artifact_rows = [
        {"artifact_key": "source_output_review_json", "path": str(source_path), "exists": source_path.exists()},
        {"artifact_key": "result_json", "path": str(json_path), "exists": True},
        {"artifact_key": "report_md", "path": str(md_path), "exists": True},
        {"artifact_key": "checks_csv", "path": str(checks_path), "exists": True},
        {"artifact_key": "checkpoint_summary_csv", "path": str(checkpoint_summary_path), "exists": True},
        {"artifact_key": "metric_carry_forward_csv", "path": str(metric_path), "exists": True},
        {"artifact_key": "authority_carry_forward_csv", "path": str(authority_path), "exists": True},
        {"artifact_key": "quality_carry_forward_csv", "path": str(quality_path), "exists": True},
        {"artifact_key": "blocked_actions_csv", "path": str(blocked_path), "exists": True},
        {"artifact_key": "next_gate_checklist_csv", "path": str(next_path), "exists": True},
    ]

    next_rows = [
        {"route_id": "NEXT_001", "candidate_route": NEXT_GATE_PASS, "selected": overall_status == "PASS", "reason": "checkpoint complete; closeout/next-lane selector required"},
        {"route_id": "NEXT_002", "candidate_route": "PARK_AND_STOP", "selected": overall_status != "PASS", "reason": "legal fallback"},
    ]

    write_json(json_path, result)
    write_md(md_path, result)
    write_csv(checks_path, checks)
    write_csv(checkpoint_summary_path, checkpoint_rows)
    write_csv(metric_path, metric_rows)
    write_csv(authority_path, authority_rows)
    write_csv(quality_path, quality_rows)
    write_csv(blocked_path, blocked_rows)
    write_csv(artifact_path, artifact_rows)
    write_csv(next_path, next_rows)

    print("HYDRA H001 RESTORED 60-FEATURE AUTHORITY VALIDATION DRYRUN EXECUTION CONTRACT RESULT CHECKPOINT COMPLETE")
    print(f"overall_status: {overall_status}")
    print(f"overall_checkpoint_status: {checkpoint_status}")
    print(f"checkpoint_ready: {checkpoint_ready}")
    print("content_execution_complete: True")
    print(f"checkpoint_decision: {decision}")
    print(f"checkpoint_verdict: {verdict}")
    print(f"checkpoint_quality_classification: {quality}")
    print(f"source_output_review_json: {source_path}")
    print(f"source_validation_dryrun_json: {result['source_validation_dryrun_json']}")
    print(f"source_feature_count_used: {result['source_feature_count_used']}")
    print(f"selected_feature_count: {result['selected_feature_count']}")
    print(f"source_feature_order_sha256: {result['source_feature_order_sha256']}")
    print(f"selected_feature_order_sha256: {result['selected_feature_order_sha256']}")
    print(f"authority_restored_and_matched: {result['authority_restored_and_matched']}")
    print(f"export_session_date_excluded: {result['export_session_date_excluded']}")
    print(f"reference_validation_balanced_accuracy: {result['reference_validation_balanced_accuracy']}")
    print(f"validation_balanced_accuracy_new: {result['validation_balanced_accuracy_new']}")
    print(f"validation_balanced_accuracy_delta_vs_reference: {result['validation_balanced_accuracy_delta_vs_reference']}")
    print(f"material_balanced_accuracy_drop: {result['material_balanced_accuracy_drop']}")
    print(f"promotion_supported_now: {result['promotion_supported_now']}")
    print(f"current_best_promotion_authorized: {result['current_best_promotion_authorized']}")
    print(f"quarantine_removal_authorized: {result['quarantine_removal_authorized']}")
    print("checkpoint_registrar_run_now: True")
    print("dataset_header_read_run: False")
    print("dataset_value_read_run: False")
    print("model_fit_or_training_run: False")
    print("model_scoring_or_prediction_run: False")
    print("validation_or_test_metric_computation_run: False")
    print("test_values_read: False")
    print("model_artifact_written: False")
    print("canonical_feature_schema_mutation: False")
    print(f"fail_required_count: {len(failures)}")
    print(f"warning_count: {len(warnings)}")
    print(f"critical_fail_count: {len(failures)}")
    print(f"pass_count: {result['pass_count']}")
    print(f"required_total: {result['required_total']}")
    print(f"recommended_next_gate: {next_gate}")
    print(f"json: {json_path}")
    print(f"md: {md_path}")
    print(f"checks_csv: {checks_path}")
    print(f"checkpoint_summary_csv: {checkpoint_summary_path}")
    print(f"metric_carry_forward_csv: {metric_path}")
    print(f"authority_carry_forward_csv: {authority_path}")
    print(f"quality_carry_forward_csv: {quality_path}")
    print(f"blocked_actions_csv: {blocked_path}")
    print(f"artifact_inventory_csv: {artifact_path}")
    print(f"next_gate_checklist_csv: {next_path}")
    print(f"legal_next_gates: {legal_next}")
    print()
    print("GUARDRAILS CONFIRMED:")
    print(
        "restored 60-feature authority validation dryrun result checkpoint only; read prior output-review JSON only; "
        "no dataset header/value read, no feature manifest read, no authority artifact scan, no model fit/training, "
        "no scoring/prediction, no validation/test model metric computation, no test read, no model artifact, "
        "no row-level predictions, no sim/backtest, no trade signals, no source/evidence/Review Gate/queue mutation, "
        "no current-best promotion, no quarantine removal, no branch reopening, no dataset/split mutation, "
        "no canonical feature/schema mutation"
    )
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
