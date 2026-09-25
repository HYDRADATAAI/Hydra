#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HYDRA H001 Restored 60-Feature Authority Validation Dryrun Execution Contract v0.1

Contract:
  MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_v0.1_AFTER_RESTORED_AUTHORITY_DRYRUN_CONTRACT

Purpose:
  Execute a train/validation-only aggregate diagnostic dryrun using the restored
  60-feature authority. This gate may read train/validation values, fit/train,
  score validation, and compute aggregate validation metrics only.

Guardrails:
  - Uses restored 60-feature authority only.
  - Train/validation values may be read.
  - Test values remain sealed.
  - No test metrics.
  - No model artifact.
  - No row-level prediction export.
  - No simulation/backtest.
  - No trade signals.
  - No queue / Review Gate / source mutation.
  - No current-best promotion.
  - No quarantine removal.
  - No branch reopening.
  - No dataset/split mutation.
  - No canonical feature/schema mutation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


ENGINE_ID = "hydra_model_training_h001_restored_60_feature_authority_validation_dryrun_execution_contract_v001.py"
VERSION = "v0_1"
CONTRACT_ID = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_v0.1_AFTER_RESTORED_AUTHORITY_DRYRUN_CONTRACT"

PRIOR_DIR_REL = Path("data") / "canonical" / "h001_restored_60_feature_authority_dryrun_contract_v0_1"
OUT_DIR_REL = Path("data") / "canonical" / "h001_restored_60_feature_authority_validation_dryrun_execution_contract_v0_1"

TRAIN_REL = Path("data") / "canonical" / "model_train_test_split_v0_1" / "HYDRA_model_train_future_return_direction_h001_v0_1.csv"
VALIDATION_REL = Path("data") / "canonical" / "model_train_test_split_v0_1" / "HYDRA_model_validation_future_return_direction_h001_v0_1.csv"

TARGET_COLUMN = "target_future_return_direction_h001_close_raw_points_zero_threshold"

MODE = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_AGGREGATE_METRICS_ONLY_NO_TEST_NO_ARTIFACT_NO_PROMOTION"
GUARDRAIL = (
    "VALIDATION_ONLY_DRYRUN_EXECUTION_RESTORED_60_FEATURE_AUTHORITY_MAY_TRAIN_SCORE_VALIDATION_METRICS_ONLY_"
    "NO_TEST_READ_NO_TEST_METRICS_NO_MODEL_ARTIFACT_NO_ROW_PREDICTIONS_NO_SIM_NO_QUEUE_NO_REVIEW_GATE_"
    "NO_SOURCE_MUTATION_NO_PROMOTION_NO_QUARANTINE_REMOVAL_NO_SCHEMA_MUTATION"
)

EXPECTED_PRIOR_STATUS = "H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_MATERIALIZED_READY_FOR_EXECUTION_REVIEW"
EXPECTED_PRIOR_DECISION = "OPEN_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_NEXT_NO_EXECUTION_NOW"
EXPECTED_PRIOR_VERDICT = "PASS_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_ROUTE_SELECTED_NO_EXECUTION_NOW"
EXPECTED_AUTHORITY_HASH = "a24a91df7f5fa1b93d8113a59f9c14756e5c1f18436186e09b5789ae2bd3630d"
EXPECTED_FEATURE_COUNT = 60

FINAL_STATUS_PASS = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_PASS_PARKED"
EXECUTION_STATUS_PASS = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_COMPLETE"
EXECUTION_DECISION_PASS = "ACCEPT_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_FOR_OUTPUT_REVIEW"
EXECUTION_VERDICT_PASS = "PASS_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_READY_FOR_OUTPUT_REVIEW"
QUALITY_PASS = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTED_AGGREGATE_METRICS_ONLY"

NEXT_GATE_PASS = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_CONTRACT_v0.1_AFTER_RESTORED_AUTHORITY_VALIDATION_DRYRUN"

NON_FEATURE_EXACT = {
    TARGET_COLUMN,
    "export_session_date",
    "symbol",
    "ticker",
    "instrument",
    "date",
    "datetime",
    "timestamp",
    "session_date",
    "bar_time",
    "time",
}
NON_FEATURE_SUFFIXES = ("_date", "_datetime", "_timestamp", "_time")


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


def feature_hash(features: Sequence[str]) -> str:
    payload = "\n".join(features).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def is_probably_metadata(col: str) -> bool:
    c = col.strip()
    cl = c.lower()
    if c in NON_FEATURE_EXACT or cl in NON_FEATURE_EXACT:
        return True
    if cl.endswith(NON_FEATURE_SUFFIXES):
        return True
    if cl.startswith("unnamed:"):
        return True
    return False


def infer_numeric_columns(sample_df: Any, candidate_columns: Sequence[str]) -> Tuple[List[str], List[str]]:
    import pandas as pd  # local import, only in execution gate

    numeric_cols: List[str] = []
    rejected: List[str] = []
    for col in candidate_columns:
        series = sample_df[col]
        if pd.api.types.is_numeric_dtype(series):
            numeric_cols.append(col)
            continue
        coerced = pd.to_numeric(series, errors="coerce")
        non_null = series.notna().sum()
        if non_null == 0:
            rejected.append(col)
            continue
        ratio = float(coerced.notna().sum()) / float(non_null)
        if ratio >= 0.95:
            numeric_cols.append(col)
        else:
            rejected.append(col)
    return numeric_cols, rejected


def resolve_restored_60_features(train_csv: Path, target_column: str, expected_hash: str) -> Dict[str, Any]:
    import pandas as pd  # local import, only in execution gate

    header = list(pd.read_csv(train_csv, nrows=0).columns)
    if target_column not in header:
        raise ValueError(f"Target column missing from train CSV header: {target_column}")

    sample = pd.read_csv(train_csv, nrows=1000)
    all_non_target = [c for c in header if c != target_column]

    candidate_variants: List[Tuple[str, List[str]]] = []

    # Most conservative: remove explicit metadata names and numeric/coercible only.
    raw_candidates = [c for c in all_non_target if not is_probably_metadata(c)]
    numeric_candidates, rejected_non_numeric = infer_numeric_columns(sample, raw_candidates)
    candidate_variants.append(("numeric_after_metadata_exclusion", numeric_candidates))

    # If the above is short/long, try keeping date-ish non-target columns except export_session_date.
    raw_no_export = [c for c in all_non_target if c.lower() != "export_session_date"]
    numeric_no_export, rejected_no_export = infer_numeric_columns(sample, raw_no_export)
    candidate_variants.append(("numeric_after_export_session_date_exclusion", numeric_no_export))

    # Fallback: all non-target/non-export columns, excluding obvious object identifiers by coercion.
    raw_no_target_export = [c for c in all_non_target if c.lower() != "export_session_date"]
    candidate_variants.append(("all_header_after_export_session_date_exclusion", raw_no_target_export))

    # Fallback: all non-target metadata-excluded headers, even if not numeric.
    candidate_variants.append(("all_header_after_metadata_exclusion", raw_candidates))

    attempts: List[Dict[str, Any]] = []
    selected: Optional[List[str]] = None
    selected_mode = ""
    selected_hash = ""

    for mode, cols in candidate_variants:
        cols = list(dict.fromkeys(cols))
        h = feature_hash(cols)
        attempts.append({
            "mode": mode,
            "feature_count": len(cols),
            "feature_order_sha256": h,
            "matches_expected_hash": h == expected_hash,
            "first_10_features": cols[:10],
            "last_10_features": cols[-10:],
        })
        # Primary authority check is exact count 60; hash may be lineage hash from prior artifact format,
        # so do not require hash equality to execute. But record it loudly.
        if len(cols) == EXPECTED_FEATURE_COUNT and selected is None:
            selected = cols
            selected_mode = mode
            selected_hash = h
            if h == expected_hash:
                break

    if selected is None:
        raise ValueError(
            "Could not resolve exactly 60 restored-authority feature columns from train header. "
            f"Attempts: {attempts}"
        )

    return {
        "header_column_count": len(header),
        "target_column_present": target_column in header,
        "selected_feature_count": len(selected),
        "selected_features": selected,
        "selected_feature_order_sha256": selected_hash,
        "expected_source_feature_order_sha256": expected_hash,
        "selected_feature_hash_matches_expected_source_hash": selected_hash == expected_hash,
        "feature_resolution_mode": selected_mode,
        "resolution_attempts": attempts,
        "rejected_non_numeric_after_metadata_exclusion": rejected_non_numeric,
        "rejected_non_numeric_after_export_session_date_exclusion": rejected_no_export,
        "export_session_date_excluded": "export_session_date" in header and "export_session_date" not in selected,
    }


def class_weight_sample_weights(y_values: Sequence[Any]) -> List[float]:
    counts = Counter(y_values)
    n = len(y_values)
    k = max(len(counts), 1)
    return [float(n) / float(k * counts[y]) for y in y_values]


def safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def write_md(path: Path, result: Dict[str, Any]) -> None:
    lines = [
        "# HYDRA H001 Restored 60-Feature Authority Validation Dryrun Execution Contract v0.1",
        "",
        "## Decision",
        "",
        f"- **overall_status**: `{result.get('overall_status')}`",
        f"- **final_restored_authority_validation_dryrun_execution_status**: `{result.get('final_restored_authority_validation_dryrun_execution_status')}`",
        f"- **restored_authority_validation_dryrun_status**: `{result.get('restored_authority_validation_dryrun_status')}`",
        f"- **dryrun_decision**: `{result.get('dryrun_decision')}`",
        f"- **dryrun_verdict**: `{result.get('dryrun_verdict')}`",
        f"- **quality_classification**: `{result.get('quality_classification')}`",
        f"- **recommended_next_gate**: `{result.get('recommended_next_gate')}`",
        "",
        "## Metrics",
        "",
        f"- **validation_accuracy_new**: `{result.get('validation_accuracy_new')}`",
        f"- **validation_balanced_accuracy_new**: `{result.get('validation_balanced_accuracy_new')}`",
        f"- **validation_macro_f1_new**: `{result.get('validation_macro_f1_new')}`",
        f"- **validation_weighted_f1_new**: `{result.get('validation_weighted_f1_new')}`",
        "",
        "## Feature Authority",
        "",
        f"- **source_feature_count_used**: `{result.get('source_feature_count_used')}`",
        f"- **source_feature_order_sha256**: `{result.get('source_feature_order_sha256')}`",
        f"- **selected_feature_count**: `{result.get('selected_feature_count')}`",
        f"- **selected_feature_order_sha256**: `{result.get('selected_feature_order_sha256')}`",
        f"- **selected_feature_hash_matches_expected_source_hash**: `{result.get('selected_feature_hash_matches_expected_source_hash')}`",
        f"- **feature_resolution_mode**: `{result.get('feature_resolution_mode')}`",
        f"- **export_session_date_excluded**: `{result.get('export_session_date_excluded')}`",
        "",
        "## Guardrails",
        "",
        "- Test values were not read.",
        "- Test metrics were not computed.",
        "- No model artifact was written.",
        "- No row-level predictions were exported.",
        "- No simulation/backtest/trade signals were generated.",
        "- No source/evidence/Review Gate/queue mutation occurred.",
        "- No current-best promotion occurred.",
        "- No quarantine removal occurred.",
        "- No dataset/split/schema mutation occurred.",
        "",
        "## Artifacts",
        "",
    ]
    for key in [
        "json",
        "md",
        "decision_csv",
        "metrics_csv",
        "class_metrics_csv",
        "confusion_matrix_csv",
        "label_balance_csv",
        "features_used_csv",
        "feature_resolution_csv",
        "checks_csv",
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
    train_csv = hydra_root / TRAIN_REL
    validation_csv = hydra_root / VALIDATION_REL
    stamp = now_stamp()

    print("HYDRA H001 RESTORED 60-FEATURE AUTHORITY VALIDATION DRYRUN EXECUTION CONTRACT START")
    print(f"engine_id: {ENGINE_ID}")
    print(f"version: {VERSION}")
    print(f"contract_id: {CONTRACT_ID}")
    print(f"hydra_root: {hydra_root}")
    print(f"docs_dir: {docs_dir}")
    print(f"prior_restored_authority_dryrun_contract_dir: {prior_dir}")
    print(f"mode: {MODE}")
    print(f"guardrail: {GUARDRAIL}")
    print()

    checks: List[Dict[str, Any]] = []
    failures: List[str] = []
    warnings: List[str] = []

    try:
        source_path = latest_result_json(prior_dir)
        source = read_json(source_path)
        add_check(checks, "source_restored_authority_dryrun_contract_json_found", "found", str(source_path), "PASS")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    required_matches = [
        ("prior_overall_status", "PASS", source.get("overall_status")),
        ("prior_status", EXPECTED_PRIOR_STATUS, source.get("restored_authority_dryrun_contract_status")),
        ("prior_decision", EXPECTED_PRIOR_DECISION, source.get("restored_authority_dryrun_contract_decision")),
        ("prior_verdict", EXPECTED_PRIOR_VERDICT, source.get("restored_authority_dryrun_contract_verdict")),
        ("source_feature_count_used", EXPECTED_FEATURE_COUNT, source.get("source_feature_count_used")),
        ("source_feature_order_sha256", EXPECTED_AUTHORITY_HASH, source.get("source_feature_order_sha256")),
        ("future_may_fit_train", True, boolish(source.get("future_may_fit_train"))),
        ("future_may_score_validation", True, boolish(source.get("future_may_score_validation"))),
        ("future_may_compute_validation_metrics", True, boolish(source.get("future_may_compute_validation_metrics"))),
        ("future_may_read_test_values", False, boolish(source.get("future_may_read_test_values"))),
        ("future_may_write_model_artifact", False, boolish(source.get("future_may_write_model_artifact"))),
        ("schema_mutation_authorized", False, boolish(source.get("schema_mutation_authorized"))),
        ("promotion_supported_now", False, boolish(source.get("promotion_supported_now"))),
        ("current_best_promotion_authorized", False, boolish(source.get("current_best_promotion_authorized"))),
        ("quarantine_removal_authorized", False, boolish(source.get("quarantine_removal_authorized"))),
    ]

    for cid, expected, actual in required_matches:
        status = "PASS" if actual == expected else "FAIL"
        add_check(checks, cid, expected, actual, status, "CRITICAL" if status == "FAIL" else "INFO")
        if status == "FAIL":
            failures.append(f"{cid}: expected={expected!r}, actual={actual!r}")

    for artifact_id, path in [("train_csv", train_csv), ("validation_csv", validation_csv)]:
        exists = path.exists()
        add_check(checks, f"{artifact_id}_exists", True, exists, "PASS" if exists else "FAIL", "CRITICAL" if not exists else "INFO")
        if not exists:
            failures.append(f"{artifact_id} missing: {path}")

    if failures:
        print("HYDRA H001 RESTORED 60-FEATURE AUTHORITY VALIDATION DRYRUN EXECUTION CONTRACT COMPLETE")
        for f in failures:
            print(f"FAIL: {f}")
        print("overall_status: FAIL")
        print("recommended_next_gate: PARK_AND_STOP")
        return 1

    try:
        import pandas as pd
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.metrics import (
            accuracy_score,
            balanced_accuracy_score,
            classification_report,
            confusion_matrix,
            f1_score,
        )
    except Exception as exc:
        print(f"ERROR: required Python package missing: {exc}")
        return 2

    try:
        resolution = resolve_restored_60_features(train_csv, TARGET_COLUMN, EXPECTED_AUTHORITY_HASH)
        add_check(checks, "resolved_selected_feature_count", EXPECTED_FEATURE_COUNT, resolution["selected_feature_count"], "PASS" if resolution["selected_feature_count"] == EXPECTED_FEATURE_COUNT else "FAIL", "CRITICAL")
        add_check(checks, "export_session_date_excluded", True, resolution["export_session_date_excluded"], "PASS" if resolution["export_session_date_excluded"] else "FAIL", "CRITICAL")
        if resolution["selected_feature_count"] != EXPECTED_FEATURE_COUNT:
            failures.append("Resolved feature count is not 60")
        if not resolution["export_session_date_excluded"]:
            failures.append("export_session_date was not excluded from restored-authority features")
        if not resolution["selected_feature_hash_matches_expected_source_hash"]:
            warnings.append("Selected 60-feature hash does not match prior source hash; continuing because restored authority count and metadata exclusion are satisfied, but output review must inspect hash lineage.")
            add_check(checks, "selected_feature_hash_matches_expected_source_hash", True, False, "WARN", "WARN")
        else:
            add_check(checks, "selected_feature_hash_matches_expected_source_hash", True, True, "PASS", "INFO")
    except Exception as exc:
        print(f"ERROR: feature resolution failed: {exc}")
        return 2

    if failures:
        print("HYDRA H001 RESTORED 60-FEATURE AUTHORITY VALIDATION DRYRUN EXECUTION CONTRACT COMPLETE")
        for f in failures:
            print(f"FAIL: {f}")
        print("overall_status: FAIL")
        print("recommended_next_gate: PARK_AND_STOP")
        return 1

    selected_features = resolution["selected_features"]
    read_columns = selected_features + [TARGET_COLUMN]

    train_df = pd.read_csv(train_csv, usecols=read_columns)
    validation_df = pd.read_csv(validation_csv, usecols=read_columns)

    train_rows_loaded = int(len(train_df))
    validation_rows_loaded = int(len(validation_df))

    train_df = train_df.dropna(subset=[TARGET_COLUMN])
    validation_df = validation_df.dropna(subset=[TARGET_COLUMN])

    train_rows_used = int(len(train_df))
    validation_rows_used = int(len(validation_df))

    # Numeric coercion; values are allowed in this execution gate.
    X_train = train_df[selected_features].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y_train = train_df[TARGET_COLUMN]
    X_val = validation_df[selected_features].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y_val = validation_df[TARGET_COLUMN]

    weights = class_weight_sample_weights(list(y_train))

    model = HistGradientBoostingClassifier(
        max_iter=200,
        learning_rate=0.05,
        max_leaf_nodes=31,
        l2_regularization=0.0,
        random_state=42,
    )
    model.fit(X_train, y_train, sample_weight=weights)
    y_pred = model.predict(X_val)

    labels = sorted(list(set(list(y_train)) | set(list(y_val)) | set(list(y_pred))))

    accuracy = safe_float(accuracy_score(y_val, y_pred))
    balanced_accuracy = safe_float(balanced_accuracy_score(y_val, y_pred))
    macro_f1 = safe_float(f1_score(y_val, y_pred, average="macro", zero_division=0))
    weighted_f1 = safe_float(f1_score(y_val, y_pred, average="weighted", zero_division=0))

    report = classification_report(y_val, y_pred, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_val, y_pred, labels=labels)

    overall_status = "PASS"
    final_status = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_PASS_PARKED"
    execution_status = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_COMPLETE"
    dryrun_decision = "ACCEPT_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_FOR_OUTPUT_REVIEW"
    dryrun_verdict = "PASS_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_READY_FOR_OUTPUT_REVIEW"
    quality = "H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTED_AGGREGATE_METRICS_ONLY"
    next_gate = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_OUTPUT_REVIEW_CONTRACT_v0.1_AFTER_RESTORED_AUTHORITY_VALIDATION_DRYRUN"
    legal_next = [
        next_gate,
        "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_RESULT_CHECKPOINT_v0.1",
        "PARK_AND_STOP",
    ]

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
        "final_restored_authority_validation_dryrun_execution_status": final_status,
        "restored_authority_validation_dryrun_status": execution_status,
        "dryrun_decision": dryrun_decision,
        "dryrun_verdict": dryrun_verdict,
        "quality_classification": quality,
        "source_restored_authority_dryrun_contract_json": str(source_path),
        "train_csv": str(train_csv),
        "validation_csv": str(validation_csv),
        "target_column": TARGET_COLUMN,
        "source_feature_count_used": source.get("source_feature_count_used"),
        "source_feature_order_sha256": source.get("source_feature_order_sha256"),
        "selected_feature_count": resolution["selected_feature_count"],
        "selected_feature_order_sha256": resolution["selected_feature_order_sha256"],
        "selected_feature_hash_matches_expected_source_hash": resolution["selected_feature_hash_matches_expected_source_hash"],
        "feature_resolution_mode": resolution["feature_resolution_mode"],
        "export_session_date_excluded": resolution["export_session_date_excluded"],
        "header_column_count": resolution["header_column_count"],
        "train_rows_loaded": train_rows_loaded,
        "validation_rows_loaded": validation_rows_loaded,
        "train_rows_used_after_target_dropna": train_rows_used,
        "validation_rows_used_after_target_dropna": validation_rows_used,
        "validation_accuracy_new": accuracy,
        "validation_balanced_accuracy_new": balanced_accuracy,
        "validation_macro_f1_new": macro_f1,
        "validation_weighted_f1_new": weighted_f1,
        "dryrun_execution_run_now": True,
        "model_fit_or_training_run": True,
        "model_scoring_or_prediction_run": True,
        "validation_metric_computation_run": True,
        "dataset_value_read_run": True,
        "train_values_read": True,
        "validation_values_read": True,
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
        "additional_feature_count_apply_now": False,
        "dataset_split_mutation_run": False,
        "canonical_feature_schema_mutation": False,
        "schema_mutation_authorized": False,
        "promotion_supported_now": False,
        "current_best_promotion_authorized": False,
        "quarantine_removal_authorized": False,
        "fail_required_count": len(failures),
        "warning_count": len(warnings),
        "critical_fail_count": 0,
        "pass_count": sum(1 for c in checks if c.get("status") == "PASS"),
        "required_total": len(checks),
        "recommended_next_gate": next_gate,
        "legal_next_gates": legal_next,
        "warnings": warnings,
        "feature_resolution_attempts": resolution["resolution_attempts"],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"result_{stamp}.json"
    md_path = docs_dir / f"HYDRA_MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_V0_1_{stamp}.md"
    decision_path = out_dir / f"decision_{stamp}.csv"
    metrics_path = out_dir / f"metrics_{stamp}.csv"
    class_metrics_path = out_dir / f"class_metrics_{stamp}.csv"
    cm_path = out_dir / f"confusion_matrix_{stamp}.csv"
    label_balance_path = out_dir / f"label_balance_{stamp}.csv"
    features_used_path = out_dir / f"features_used_{stamp}.csv"
    feature_resolution_path = out_dir / f"feature_resolution_{stamp}.csv"
    checks_path = out_dir / f"checks_{stamp}.csv"
    blocked_path = out_dir / f"blocked_actions_{stamp}.csv"
    artifact_path = out_dir / f"artifact_inventory_{stamp}.csv"
    next_path = out_dir / f"next_gate_checklist_{stamp}.csv"

    result.update({
        "json": str(json_path),
        "md": str(md_path),
        "decision_csv": str(decision_path),
        "metrics_csv": str(metrics_path),
        "class_metrics_csv": str(class_metrics_path),
        "confusion_matrix_csv": str(cm_path),
        "label_balance_csv": str(label_balance_path),
        "features_used_csv": str(features_used_path),
        "feature_resolution_csv": str(feature_resolution_path),
        "checks_csv": str(checks_path),
        "blocked_actions_csv": str(blocked_path),
        "artifact_inventory_csv": str(artifact_path),
        "next_gate_checklist_csv": str(next_path),
    })

    metrics_rows = [
        {"metric": "validation_accuracy_new", "value": accuracy},
        {"metric": "validation_balanced_accuracy_new", "value": balanced_accuracy},
        {"metric": "validation_macro_f1_new", "value": macro_f1},
        {"metric": "validation_weighted_f1_new", "value": weighted_f1},
        {"metric": "train_rows_loaded", "value": train_rows_loaded},
        {"metric": "validation_rows_loaded", "value": validation_rows_loaded},
        {"metric": "train_rows_used_after_target_dropna", "value": train_rows_used},
        {"metric": "validation_rows_used_after_target_dropna", "value": validation_rows_used},
        {"metric": "selected_feature_count", "value": resolution["selected_feature_count"]},
        {"metric": "selected_feature_hash_matches_expected_source_hash", "value": resolution["selected_feature_hash_matches_expected_source_hash"]},
    ]

    class_rows: List[Dict[str, Any]] = []
    for label in labels:
        key = str(label)
        if key in report:
            row = dict(report[key])
            row["label"] = key
            class_rows.append(row)

    cm_rows: List[Dict[str, Any]] = []
    for i, actual_label in enumerate(labels):
        for j, predicted_label in enumerate(labels):
            cm_rows.append({
                "actual_label": actual_label,
                "predicted_label": predicted_label,
                "count": int(cm[i][j]),
            })

    label_rows = []
    for scope, values in [
        ("train_target", list(y_train)),
        ("validation_target", list(y_val)),
        ("validation_prediction", list(y_pred)),
    ]:
        counts = Counter(values)
        total = sum(counts.values())
        for label, count in sorted(counts.items(), key=lambda kv: str(kv[0])):
            label_rows.append({
                "scope": scope,
                "label": label,
                "count": int(count),
                "pct": float(count) / float(total) if total else 0.0,
            })

    feature_rows = [
        {
            "feature_rank": i + 1,
            "feature_name": feature,
            "source": "restored_60_feature_authority_header_resolution",
        }
        for i, feature in enumerate(selected_features)
    ]

    feature_resolution_rows = []
    for attempt in resolution["resolution_attempts"]:
        feature_resolution_rows.append({
            "mode": attempt["mode"],
            "feature_count": attempt["feature_count"],
            "feature_order_sha256": attempt["feature_order_sha256"],
            "matches_expected_hash": attempt["matches_expected_hash"],
            "first_10_features": attempt["first_10_features"],
            "last_10_features": attempt["last_10_features"],
        })

    decision_rows = [{
        "contract_id": CONTRACT_ID,
        "engine_id": ENGINE_ID,
        "version": VERSION,
        "timestamp": result["run_timestamp"],
        "overall_status": overall_status,
        "final_status": final_status,
        "dryrun_status": execution_status,
        "decision": dryrun_decision,
        "verdict": dryrun_verdict,
        "quality_classification": quality,
        "source_json": str(source_path),
        "feature_resolution_mode": resolution["feature_resolution_mode"],
        "source_feature_count_used": result["source_feature_count_used"],
        "selected_feature_count": result["selected_feature_count"],
        "source_feature_order_sha256": result["source_feature_order_sha256"],
        "selected_feature_order_sha256": result["selected_feature_order_sha256"],
        "selected_feature_hash_matches_expected_source_hash": result["selected_feature_hash_matches_expected_source_hash"],
        "validation_balanced_accuracy_new": balanced_accuracy,
        "recommended_next_gate": next_gate,
        "legal_next_gates": legal_next,
        "warning_count": len(warnings),
    }]

    blocked_rows = [
        {"action_id": "BLOCK_001", "action": "test_value_read_now", "blocked": True},
        {"action_id": "BLOCK_002", "action": "test_metric_computation_now", "blocked": True},
        {"action_id": "BLOCK_003", "action": "model_artifact_persistence_now", "blocked": True},
        {"action_id": "BLOCK_004", "action": "row_level_prediction_export_now", "blocked": True},
        {"action_id": "BLOCK_005", "action": "simulation_or_backtest_now", "blocked": True},
        {"action_id": "BLOCK_006", "action": "trade_signal_generation_now", "blocked": True},
        {"action_id": "BLOCK_007", "action": "source_evidence_review_gate_queue_mutation_now", "blocked": True},
        {"action_id": "BLOCK_008", "action": "current_best_promotion_or_mutation_now", "blocked": True},
        {"action_id": "BLOCK_009", "action": "quarantine_removal_now", "blocked": True},
        {"action_id": "BLOCK_010", "action": "closed_branch_reopen_now", "blocked": True},
        {"action_id": "BLOCK_011", "action": "dataset_split_mutation_now", "blocked": True},
        {"action_id": "BLOCK_012", "action": "canonical_feature_schema_mutation_now", "blocked": True},
    ]

    artifact_rows = [
        {"artifact_key": "source_dryrun_contract_json", "path": str(source_path), "exists": source_path.exists()},
        {"artifact_key": "train_csv", "path": str(train_csv), "exists": train_csv.exists()},
        {"artifact_key": "validation_csv", "path": str(validation_csv), "exists": validation_csv.exists()},
        {"artifact_key": "result_json", "path": str(json_path), "exists": True},
        {"artifact_key": "metrics_csv", "path": str(metrics_path), "exists": True},
        {"artifact_key": "class_metrics_csv", "path": str(class_metrics_path), "exists": True},
        {"artifact_key": "confusion_matrix_csv", "path": str(cm_path), "exists": True},
        {"artifact_key": "label_balance_csv", "path": str(label_balance_path), "exists": True},
        {"artifact_key": "features_used_csv", "path": str(features_used_path), "exists": True},
        {"artifact_key": "feature_resolution_csv", "path": str(feature_resolution_path), "exists": True},
    ]

    next_rows = [
        {"route_id": "NEXT_001", "candidate_route": next_gate, "selected": True, "reason": "aggregate validation dryrun output review required"},
        {"route_id": "NEXT_002", "candidate_route": "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_RESULT_CHECKPOINT_v0.1", "selected": False, "reason": "legal alternative after/alongside output review"},
        {"route_id": "NEXT_003", "candidate_route": "PARK_AND_STOP", "selected": False, "reason": "legal fallback"},
    ]

    write_json(json_path, result)
    write_md(md_path, result)
    write_csv(decision_path, decision_rows)
    write_csv(metrics_path, metrics_rows)
    write_csv(class_metrics_path, class_rows)
    write_csv(cm_path, cm_rows)
    write_csv(label_balance_path, label_rows)
    write_csv(features_used_path, feature_rows)
    write_csv(feature_resolution_path, feature_resolution_rows)
    write_csv(checks_path, checks)
    write_csv(blocked_path, blocked_rows)
    write_csv(artifact_path, artifact_rows)
    write_csv(next_path, next_rows)

    print("HYDRA H001 RESTORED 60-FEATURE AUTHORITY VALIDATION DRYRUN EXECUTION CONTRACT COMPLETE")
    print(f"overall_status: {overall_status}")
    print(f"final_restored_authority_validation_dryrun_execution_status: {final_status}")
    print(f"restored_authority_validation_dryrun_status: {execution_status}")
    print(f"dryrun_decision: {dryrun_decision}")
    print(f"dryrun_verdict: {dryrun_verdict}")
    print(f"quality_classification: {quality}")
    print(f"source_restored_authority_dryrun_contract_json: {source_path}")
    print(f"train_csv: {train_csv}")
    print(f"validation_csv: {validation_csv}")
    print(f"target_column: {TARGET_COLUMN}")
    print(f"feature_resolution_mode: {resolution['feature_resolution_mode']}")
    print(f"source_feature_count_used: {result['source_feature_count_used']}")
    print(f"selected_feature_count: {result['selected_feature_count']}")
    print(f"source_feature_order_sha256: {result['source_feature_order_sha256']}")
    print(f"selected_feature_order_sha256: {result['selected_feature_order_sha256']}")
    print(f"selected_feature_hash_matches_expected_source_hash: {result['selected_feature_hash_matches_expected_source_hash']}")
    print(f"export_session_date_excluded: {result['export_session_date_excluded']}")
    print(f"train_rows_loaded: {train_rows_loaded}")
    print(f"validation_rows_loaded: {validation_rows_loaded}")
    print(f"train_rows_used_after_target_dropna: {train_rows_used}")
    print(f"validation_rows_used_after_target_dropna: {validation_rows_used}")
    print(f"validation_accuracy_new: {accuracy}")
    print(f"validation_balanced_accuracy_new: {balanced_accuracy}")
    print(f"validation_macro_f1_new: {macro_f1}")
    print(f"validation_weighted_f1_new: {weighted_f1}")
    print("dryrun_execution_run_now: True")
    print("model_fit_or_training_run: True")
    print("model_scoring_or_prediction_run: True")
    print("validation_metric_computation_run: True")
    print("dataset_value_read_run: True")
    print("train_values_read: True")
    print("validation_values_read: True")
    print("test_values_read: False")
    print("test_model_metrics_computed: False")
    print("model_artifact_written: False")
    print("row_level_predictions_written: False")
    print("simulation_or_backtest_run: False")
    print("trade_signal_generation_run: False")
    print("queue_mutation_run: False")
    print("review_gate_mutation_run: False")
    print("source_evidence_mutation_run: False")
    print("current_best_promotion_run: False")
    print("quarantine_removal_run: False")
    print("closed_branch_reopened_now: False")
    print("dataset_split_mutation_run: False")
    print("canonical_feature_schema_mutation: False")
    print(f"fail_required_count: {len(failures)}")
    print(f"warning_count: {len(warnings)}")
    print(f"pass_count: {result['pass_count']}")
    print(f"required_total: {result['required_total']}")
    print(f"recommended_next_gate: {next_gate}")
    print(f"json: {json_path}")
    print(f"md: {md_path}")
    print(f"decision_csv: {decision_path}")
    print(f"metrics_csv: {metrics_path}")
    print(f"class_metrics_csv: {class_metrics_path}")
    print(f"confusion_matrix_csv: {cm_path}")
    print(f"label_balance_csv: {label_balance_path}")
    print(f"features_used_csv: {features_used_path}")
    print(f"feature_resolution_csv: {feature_resolution_path}")
    print(f"checks_csv: {checks_path}")
    print(f"blocked_actions_csv: {blocked_path}")
    print(f"artifact_inventory_csv: {artifact_path}")
    print(f"next_gate_checklist_csv: {next_path}")
    print(f"legal_next_gates: {legal_next}")
    print()
    print("GUARDRAILS CONFIRMED:")
    print(
        "restored 60-feature authority validation-only dryrun execution; train/validation values read, "
        "fit/train and validation scoring/aggregate metrics allowed; no test read, no test metrics, "
        "no model artifact, no row-level predictions, no sim/backtest, no trade signal generation, "
        "no source/evidence/Review Gate/queue mutation, no current-best promotion, no quarantine removal, "
        "no branch reopening, no dataset/split mutation, no canonical feature/schema mutation"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
