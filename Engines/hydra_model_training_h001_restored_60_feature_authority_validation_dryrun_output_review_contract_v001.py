#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HYDRA H001 Restored 60-Feature Authority Validation Dryrun Output Review Contract v0.1

Contract:
  MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_CONTRACT_v0.1_AFTER_RESTORED_AUTHORITY_VALIDATION_DRYRUN

Purpose:
  Review the aggregate outputs from the restored 60-feature authority validation dryrun.
  Accept the output for result checkpoint, but do not promote unless separately authorized.

Guardrails:
  - Output review only.
  - Reads prior restored-authority validation dryrun JSON only.
  - No dataset header/value read.
  - No feature manifest read.
  - No authority scan.
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


ENGINE_ID = "hydra_model_training_h001_restored_60_feature_authority_validation_dryrun_output_review_contract_v001.py"
VERSION = "v0_1"
CONTRACT_ID = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_CONTRACT_v0.1_AFTER_RESTORED_AUTHORITY_VALIDATION_DRYRUN"

PRIOR_DIR_REL = Path("data") / "canonical" / "h001_restored_60_feature_authority_validation_dryrun_execution_contract_v0_1"
OUT_DIR_REL = Path("data") / "canonical" / "h001_restored_60_feature_authority_validation_dryrun_output_review_contract_v0_1"

MODE = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_ONLY_NO_DATASET_NO_TRAIN_NO_SCORE_NO_PROMOTION"
GUARDRAIL = (
    "RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_ONLY_READS_PRIOR_AGGREGATE_JSON_"
    "NO_DATASET_HEADER_READ_NO_DATASET_VALUE_READ_NO_FEATURE_MANIFEST_READ_NO_AUTHORITY_SCAN_"
    "NO_TRAIN_NO_SCORE_NO_PREDICT_NO_VALIDATION_TEST_METRIC_COMPUTE_NO_TEST_READ_NO_MODEL_ARTIFACT_"
    "NO_ROW_PREDICTIONS_NO_SIM_NO_QUEUE_NO_REVIEW_GATE_MUTATION_NO_SOURCE_MUTATION_NO_PROMOTION_"
    "NO_QUARANTINE_REMOVAL_NO_BRANCH_REOPEN_NO_SCHEMA_MUTATION"
)

EXPECTED_PRIOR_STATUS = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_COMPLETE"
EXPECTED_PRIOR_DECISION = "ACCEPT_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_FOR_OUTPUT_REVIEW"
EXPECTED_PRIOR_VERDICT = "PASS_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_READY_FOR_OUTPUT_REVIEW"
EXPECTED_FEATURE_COUNT = 60
EXPECTED_AUTHORITY_HASH = "a24a91df7f5fa1b93d8113a59f9c14756e5c1f18436186e09b5789ae2bd3630d"

# Locked diagnostic reference carried from the earlier accepted H001 branch.
REFERENCE_VALIDATION_ACCURACY = 0.36694692701935705
REFERENCE_VALIDATION_BALANCED_ACCURACY = 0.43792145864879845
REFERENCE_VALIDATION_MACRO_F1 = 0.31395599264627605
REFERENCE_VALIDATION_WEIGHTED_F1 = 0.40544791808773095

FINAL_STATUS = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_CONTRACT_PASS_PARKED"
REVIEW_STATUS = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_COMPLETE"
REVIEW_DECISION = "ACCEPT_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_FOR_RESULT_CHECKPOINT_NOT_PROMOTION"
REVIEW_VERDICT = "PASS_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_READY_FOR_RESULT_CHECKPOINT"
QUALITY_CLASSIFICATION = "H001_RESTORED_60_FEATURE_AUTHORITY_OUTPUT_REVIEW_AUTHORITY_MATCHED_BALANCED_ACCURACY_DEGRADED_NOT_PROMOTION_READY"

NEXT_GATE = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_RESULT_CHECKPOINT_v0.1_AFTER_OUTPUT_REVIEW"
LEGAL_NEXT_GATES = [NEXT_GATE, "PARK_AND_STOP"]


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


def latest_result_json(directory: Path) -> Path:
    candidates = sorted(directory.glob("result_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No result_*.json found in {directory}")
    return candidates[0]


def add_check(checks: List[Dict[str, Any]], check_id: str, expected: Any, actual: Any, status: str, severity: str = "INFO") -> None:
    checks.append({
        "check_id": check_id,
        "expected": expected,
        "actual": actual,
        "status": status,
        "severity": severity,
    })


def fnum(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def write_md(path: Path, result: Dict[str, Any]) -> None:
    lines = [
        "# HYDRA H001 Restored 60-Feature Authority Validation Dryrun Output Review Contract v0.1",
        "",
        "## Decision",
        "",
        f"- **overall_status**: `{result.get('overall_status')}`",
        f"- **final_restored_authority_validation_dryrun_output_review_status**: `{result.get('final_restored_authority_validation_dryrun_output_review_status')}`",
        f"- **restored_authority_validation_dryrun_output_review_status**: `{result.get('restored_authority_validation_dryrun_output_review_status')}`",
        f"- **output_review_decision**: `{result.get('output_review_decision')}`",
        f"- **output_review_verdict**: `{result.get('output_review_verdict')}`",
        f"- **quality_classification**: `{result.get('quality_classification')}`",
        f"- **recommended_next_gate**: `{result.get('recommended_next_gate')}`",
        "",
        "## Interpretation",
        "",
        result.get("output_review_interpretation", ""),
        "",
        "## Metrics vs Locked Reference",
        "",
        f"- **reference_validation_balanced_accuracy**: `{result.get('reference_validation_balanced_accuracy')}`",
        f"- **validation_balanced_accuracy_new**: `{result.get('validation_balanced_accuracy_new')}`",
        f"- **validation_balanced_accuracy_delta_vs_reference**: `{result.get('validation_balanced_accuracy_delta_vs_reference')}`",
        f"- **authority_restored_and_matched**: `{result.get('authority_restored_and_matched')}`",
        f"- **promotion_supported_now**: `{result.get('promotion_supported_now')}`",
        "",
        "## Guardrails",
        "",
        "- Output review only.",
        "- No data read.",
        "- No train/score.",
        "- No test read.",
        "- No model artifact.",
        "- No row-level predictions.",
        "- No simulation/backtest.",
        "- No source/evidence/Review Gate/queue mutation.",
        "- No promotion.",
        "- No schema mutation.",
        "",
        "## Artifacts",
        "",
    ]
    for key in [
        "json",
        "md",
        "checks_csv",
        "decision_csv",
        "metrics_review_csv",
        "quality_findings_csv",
        "authority_review_csv",
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

    print("HYDRA H001 RESTORED 60-FEATURE AUTHORITY VALIDATION DRYRUN OUTPUT REVIEW CONTRACT START")
    print(f"engine_id: {ENGINE_ID}")
    print(f"version: {VERSION}")
    print(f"contract_id: {CONTRACT_ID}")
    print(f"hydra_root: {hydra_root}")
    print(f"docs_dir: {docs_dir}")
    print(f"prior_restored_authority_validation_dryrun_dir: {prior_dir}")
    print(f"mode: {MODE}")
    print(f"guardrail: {GUARDRAIL}")
    print()

    checks: List[Dict[str, Any]] = []
    failures: List[str] = []
    warnings: List[str] = []

    try:
        source_path = latest_result_json(prior_dir)
        source = read_json(source_path)
        add_check(checks, "source_restored_authority_validation_dryrun_json_found", "found", str(source_path), "PASS")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    required_matches = [
        ("prior_overall_status", "PASS", source.get("overall_status")),
        ("prior_status", EXPECTED_PRIOR_STATUS, source.get("restored_authority_validation_dryrun_status")),
        ("prior_decision", EXPECTED_PRIOR_DECISION, source.get("dryrun_decision")),
        ("prior_verdict", EXPECTED_PRIOR_VERDICT, source.get("dryrun_verdict")),
        ("source_feature_count_used", EXPECTED_FEATURE_COUNT, source.get("source_feature_count_used")),
        ("selected_feature_count", EXPECTED_FEATURE_COUNT, source.get("selected_feature_count")),
        ("source_feature_order_sha256", EXPECTED_AUTHORITY_HASH, source.get("source_feature_order_sha256")),
        ("selected_feature_order_sha256", EXPECTED_AUTHORITY_HASH, source.get("selected_feature_order_sha256")),
        ("selected_feature_hash_matches_expected_source_hash", True, boolish(source.get("selected_feature_hash_matches_expected_source_hash"))),
        ("export_session_date_excluded", True, boolish(source.get("export_session_date_excluded"))),
        ("dryrun_execution_run_now", True, boolish(source.get("dryrun_execution_run_now"))),
        ("model_fit_or_training_run", True, boolish(source.get("model_fit_or_training_run"))),
        ("model_scoring_or_prediction_run", True, boolish(source.get("model_scoring_or_prediction_run"))),
        ("validation_metric_computation_run", True, boolish(source.get("validation_metric_computation_run"))),
        ("test_values_read", False, boolish(source.get("test_values_read"))),
        ("test_model_metrics_computed", False, boolish(source.get("test_model_metrics_computed"))),
        ("model_artifact_written", False, boolish(source.get("model_artifact_written"))),
        ("row_level_predictions_written", False, boolish(source.get("row_level_predictions_written"))),
        ("canonical_feature_schema_mutation", False, boolish(source.get("canonical_feature_schema_mutation"))),
    ]

    for cid, expected, actual in required_matches:
        status = "PASS" if actual == expected else "FAIL"
        add_check(checks, cid, expected, actual, status, "CRITICAL" if status == "FAIL" else "INFO")
        if status == "FAIL":
            failures.append(f"{cid}: expected={expected!r}, actual={actual!r}")

    acc = fnum(source.get("validation_accuracy_new"))
    bacc = fnum(source.get("validation_balanced_accuracy_new"))
    macro = fnum(source.get("validation_macro_f1_new"))
    weighted = fnum(source.get("validation_weighted_f1_new"))

    for metric_name, metric_value in [
        ("validation_accuracy_new", acc),
        ("validation_balanced_accuracy_new", bacc),
        ("validation_macro_f1_new", macro),
        ("validation_weighted_f1_new", weighted),
    ]:
        ok = metric_value is not None
        add_check(checks, f"{metric_name}_present", "numeric", metric_value, "PASS" if ok else "FAIL", "CRITICAL" if not ok else "INFO")
        if not ok:
            failures.append(f"{metric_name} missing/non-numeric")

    balanced_delta = (bacc - REFERENCE_VALIDATION_BALANCED_ACCURACY) if bacc is not None else None
    accuracy_delta = (acc - REFERENCE_VALIDATION_ACCURACY) if acc is not None else None
    macro_delta = (macro - REFERENCE_VALIDATION_MACRO_F1) if macro is not None else None
    weighted_delta = (weighted - REFERENCE_VALIDATION_WEIGHTED_F1) if weighted is not None else None

    material_balanced_accuracy_drop = bool(balanced_delta is not None and balanced_delta < 0)
    promotion_supported_now = False
    if material_balanced_accuracy_drop:
        warnings.append("Validation balanced accuracy is below locked diagnostic reference; no promotion supported.")

    if failures:
        overall_status = "FAIL"
        final_status = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_CONTRACT_FAIL_PARKED"
        review_status = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_FAILED"
        decision = "REJECT_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_CHECKS_FAILED"
        verdict = "FAIL_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_NOT_READY"
        quality = "H001_RESTORED_60_FEATURE_AUTHORITY_OUTPUT_REVIEW_FAILED_NO_PROMOTION"
        next_gate = "PARK_AND_STOP"
        legal_next = ["PARK_AND_STOP"]
    else:
        overall_status = "PASS"
        final_status = FINAL_STATUS
        review_status = REVIEW_STATUS
        decision = REVIEW_DECISION
        verdict = REVIEW_VERDICT
        quality = QUALITY_CLASSIFICATION
        next_gate = NEXT_GATE
        legal_next = LEGAL_NEXT_GATES

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
        "final_restored_authority_validation_dryrun_output_review_status": final_status,
        "restored_authority_validation_dryrun_output_review_status": review_status,
        "output_review_decision": decision,
        "output_review_verdict": verdict,
        "quality_classification": quality,
        "output_review_interpretation": (
            "Restored 60-feature authority validation dryrun output review accepted. The feature authority is now clean: "
            "selected feature count is 60, selected hash matches the restored source hash, and export_session_date is excluded. "
            "However, validation balanced accuracy is below the locked diagnostic reference, so this run is evidence-only and not promotion-ready. "
            "Checkpoint the result; do not promote, do not remove quarantine, do not read test, and do not mutate schema."
            if overall_status == "PASS"
            else "Restored 60-feature authority validation dryrun output review failed required checks. Park and do not promote."
        ),
        "source_restored_authority_validation_dryrun_json": str(source_path),
        "source_feature_count_used": source.get("source_feature_count_used"),
        "selected_feature_count": source.get("selected_feature_count"),
        "source_feature_order_sha256": source.get("source_feature_order_sha256"),
        "selected_feature_order_sha256": source.get("selected_feature_order_sha256"),
        "selected_feature_hash_matches_expected_source_hash": source.get("selected_feature_hash_matches_expected_source_hash"),
        "export_session_date_excluded": source.get("export_session_date_excluded"),
        "feature_resolution_mode": source.get("feature_resolution_mode"),
        "authority_restored_and_matched": (
            source.get("source_feature_count_used") == 60
            and source.get("selected_feature_count") == 60
            and source.get("source_feature_order_sha256") == EXPECTED_AUTHORITY_HASH
            and source.get("selected_feature_order_sha256") == EXPECTED_AUTHORITY_HASH
            and boolish(source.get("selected_feature_hash_matches_expected_source_hash"))
        ),
        "reference_validation_accuracy": REFERENCE_VALIDATION_ACCURACY,
        "validation_accuracy_new": acc,
        "validation_accuracy_delta_vs_reference": accuracy_delta,
        "reference_validation_balanced_accuracy": REFERENCE_VALIDATION_BALANCED_ACCURACY,
        "validation_balanced_accuracy_new": bacc,
        "validation_balanced_accuracy_delta_vs_reference": balanced_delta,
        "reference_validation_macro_f1": REFERENCE_VALIDATION_MACRO_F1,
        "validation_macro_f1_new": macro,
        "validation_macro_f1_delta_vs_reference": macro_delta,
        "reference_validation_weighted_f1": REFERENCE_VALIDATION_WEIGHTED_F1,
        "validation_weighted_f1_new": weighted,
        "validation_weighted_f1_delta_vs_reference": weighted_delta,
        "material_balanced_accuracy_drop": material_balanced_accuracy_drop,
        "promotion_supported_now": promotion_supported_now,
        "checkpoint_recommended": overall_status == "PASS",
        "output_review_contract_run_now": True,
        "dataset_header_read_run": False,
        "dataset_value_read_run": False,
        "feature_manifest_read_run": False,
        "authority_artifact_scan_run": False,
        "bounded_authority_artifact_read_run": False,
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
        "schema_mutation_authorized": False,
        "current_best_promotion_authorized": False,
        "quarantine_removal_authorized": False,
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
    md_path = docs_dir / f"HYDRA_MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_CONTRACT_V0_1_{stamp}.md"
    checks_path = out_dir / f"checks_{stamp}.csv"
    decision_path = out_dir / f"decision_{stamp}.csv"
    metrics_review_path = out_dir / f"metrics_review_{stamp}.csv"
    quality_findings_path = out_dir / f"quality_findings_{stamp}.csv"
    authority_review_path = out_dir / f"authority_review_{stamp}.csv"
    blocked_path = out_dir / f"blocked_actions_{stamp}.csv"
    artifact_path = out_dir / f"artifact_inventory_{stamp}.csv"
    next_path = out_dir / f"next_gate_checklist_{stamp}.csv"

    result.update({
        "json": str(json_path),
        "md": str(md_path),
        "checks_csv": str(checks_path),
        "decision_csv": str(decision_path),
        "metrics_review_csv": str(metrics_review_path),
        "quality_findings_csv": str(quality_findings_path),
        "authority_review_csv": str(authority_review_path),
        "blocked_actions_csv": str(blocked_path),
        "artifact_inventory_csv": str(artifact_path),
        "next_gate_checklist_csv": str(next_path),
    })

    decision_rows = [{
        "contract_id": CONTRACT_ID,
        "engine_id": ENGINE_ID,
        "version": VERSION,
        "timestamp": result["run_timestamp"],
        "overall_status": overall_status,
        "final_status": final_status,
        "review_status": review_status,
        "decision": decision,
        "verdict": verdict,
        "quality_classification": quality,
        "source_json": str(source_path),
        "authority_restored_and_matched": result["authority_restored_and_matched"],
        "material_balanced_accuracy_drop": material_balanced_accuracy_drop,
        "promotion_supported_now": promotion_supported_now,
        "recommended_next_gate": next_gate,
        "legal_next_gates": legal_next,
        "warning_count": len(warnings),
        "fail_required_count": len(failures),
    }]

    metrics_rows = [
        {"metric": "validation_accuracy", "reference": REFERENCE_VALIDATION_ACCURACY, "new": acc, "delta": accuracy_delta, "better_than_reference": bool(accuracy_delta is not None and accuracy_delta > 0)},
        {"metric": "validation_balanced_accuracy", "reference": REFERENCE_VALIDATION_BALANCED_ACCURACY, "new": bacc, "delta": balanced_delta, "better_than_reference": bool(balanced_delta is not None and balanced_delta > 0)},
        {"metric": "validation_macro_f1", "reference": REFERENCE_VALIDATION_MACRO_F1, "new": macro, "delta": macro_delta, "better_than_reference": bool(macro_delta is not None and macro_delta > 0)},
        {"metric": "validation_weighted_f1", "reference": REFERENCE_VALIDATION_WEIGHTED_F1, "new": weighted, "delta": weighted_delta, "better_than_reference": bool(weighted_delta is not None and weighted_delta > 0)},
    ]

    quality_rows = [
        {"finding_id": "QUALITY_001_AUTHORITY_RESTORED", "finding": "Feature authority restored and matched selected 60-feature hash.", "status": "PASS" if result["authority_restored_and_matched"] else "FAIL"},
        {"finding_id": "QUALITY_002_BALANCED_ACCURACY", "finding": "Validation balanced accuracy degraded versus locked reference.", "status": "WARN" if material_balanced_accuracy_drop else "PASS"},
        {"finding_id": "QUALITY_003_PROMOTION", "finding": "Promotion is not supported from this dryrun.", "status": "PASS"},
        {"finding_id": "QUALITY_004_CHECKPOINT", "finding": "Checkpoint is required before any further lane selection.", "status": "PASS" if overall_status == "PASS" else "FAIL"},
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
        {"artifact_key": "source_restored_authority_validation_dryrun_json", "path": str(source_path), "exists": source_path.exists()},
        {"artifact_key": "result_json", "path": str(json_path), "exists": True},
        {"artifact_key": "report_md", "path": str(md_path), "exists": True},
        {"artifact_key": "checks_csv", "path": str(checks_path), "exists": True},
        {"artifact_key": "decision_csv", "path": str(decision_path), "exists": True},
        {"artifact_key": "metrics_review_csv", "path": str(metrics_review_path), "exists": True},
        {"artifact_key": "authority_review_csv", "path": str(authority_review_path), "exists": True},
    ]

    next_rows = [
        {"route_id": "NEXT_001", "candidate_route": NEXT_GATE, "selected": overall_status == "PASS", "reason": "output review accepted; checkpoint required"},
        {"route_id": "NEXT_002", "candidate_route": "PARK_AND_STOP", "selected": overall_status != "PASS", "reason": "legal fallback"},
    ]

    write_json(json_path, result)
    write_md(md_path, result)
    write_csv(checks_path, checks)
    write_csv(decision_path, decision_rows)
    write_csv(metrics_review_path, metrics_rows)
    write_csv(quality_findings_path, quality_rows)
    write_csv(authority_review_path, authority_rows)
    write_csv(blocked_path, blocked_rows)
    write_csv(artifact_path, artifact_rows)
    write_csv(next_path, next_rows)

    print("HYDRA H001 RESTORED 60-FEATURE AUTHORITY VALIDATION DRYRUN OUTPUT REVIEW CONTRACT COMPLETE")
    print(f"overall_status: {overall_status}")
    print(f"final_restored_authority_validation_dryrun_output_review_status: {final_status}")
    print(f"restored_authority_validation_dryrun_output_review_status: {review_status}")
    print(f"output_review_decision: {decision}")
    print(f"output_review_verdict: {verdict}")
    print(f"quality_classification: {quality}")
    print(f"source_restored_authority_validation_dryrun_json: {source_path}")
    print(f"source_feature_count_used: {result['source_feature_count_used']}")
    print(f"selected_feature_count: {result['selected_feature_count']}")
    print(f"source_feature_order_sha256: {result['source_feature_order_sha256']}")
    print(f"selected_feature_order_sha256: {result['selected_feature_order_sha256']}")
    print(f"selected_feature_hash_matches_expected_source_hash: {result['selected_feature_hash_matches_expected_source_hash']}")
    print(f"export_session_date_excluded: {result['export_session_date_excluded']}")
    print(f"authority_restored_and_matched: {result['authority_restored_and_matched']}")
    print(f"reference_validation_accuracy: {REFERENCE_VALIDATION_ACCURACY}")
    print(f"validation_accuracy_new: {acc}")
    print(f"validation_accuracy_delta_vs_reference: {accuracy_delta}")
    print(f"reference_validation_balanced_accuracy: {REFERENCE_VALIDATION_BALANCED_ACCURACY}")
    print(f"validation_balanced_accuracy_new: {bacc}")
    print(f"validation_balanced_accuracy_delta_vs_reference: {balanced_delta}")
    print(f"reference_validation_macro_f1: {REFERENCE_VALIDATION_MACRO_F1}")
    print(f"validation_macro_f1_new: {macro}")
    print(f"validation_macro_f1_delta_vs_reference: {macro_delta}")
    print(f"reference_validation_weighted_f1: {REFERENCE_VALIDATION_WEIGHTED_F1}")
    print(f"validation_weighted_f1_new: {weighted}")
    print(f"validation_weighted_f1_delta_vs_reference: {weighted_delta}")
    print(f"material_balanced_accuracy_drop: {material_balanced_accuracy_drop}")
    print(f"promotion_supported_now: {promotion_supported_now}")
    print("output_review_contract_run_now: True")
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
    print(f"decision_csv: {decision_path}")
    print(f"metrics_review_csv: {metrics_review_path}")
    print(f"quality_findings_csv: {quality_findings_path}")
    print(f"authority_review_csv: {authority_review_path}")
    print(f"blocked_actions_csv: {blocked_path}")
    print(f"artifact_inventory_csv: {artifact_path}")
    print(f"next_gate_checklist_csv: {next_path}")
    print(f"legal_next_gates: {legal_next}")
    print()
    print("GUARDRAILS CONFIRMED:")
    print(
        "restored 60-feature authority validation dryrun output review only; read prior aggregate JSON only; "
        "no dataset header/value read, no feature manifest read, no authority artifact scan, no model fit/training, "
        "no scoring/prediction, no validation/test model metric computation, no test read, no model artifact, "
        "no row-level predictions, no sim/backtest, no trade signals, no source/evidence/Review Gate/queue mutation, "
        "no current-best promotion, no quarantine removal, no branch reopening, no dataset/split mutation, "
        "no canonical feature/schema mutation"
    )
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
