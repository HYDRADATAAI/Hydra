#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HYDRA H001 Restored 60-Feature Authority Dryrun Contract v0.1

Contract:
  MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_v0.1_AFTER_POLICY_REENTRY_REVIEW

Purpose:
  Materialize the explicit restored-60-feature-authority validation dryrun execution contract
  after restored-authority policy re-entry review.

Guardrails:
  - Contract/materialization only.
  - Reads prior restored-authority policy re-entry review JSON only.
  - No dryrun execution now.
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
  - No identical policy-intake loop.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ENGINE_ID = "hydra_model_training_h001_restored_60_feature_authority_dryrun_contract_v001.py"
VERSION = "v0_1"
CONTRACT_ID = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_v0.1_AFTER_POLICY_REENTRY_REVIEW"

PRIOR_DIR_REL = Path("data") / "canonical" / "h001_restored_60_feature_authority_policy_reentry_review_contract_v0_1"
OUT_DIR_REL = Path("data") / "canonical" / "h001_restored_60_feature_authority_dryrun_contract_v0_1"

MODE = "H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_ONLY_NO_DRYRUN_EXECUTION_NO_TRAIN_NO_SCORE_NO_PROMOTION"
GUARDRAIL = (
    "RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_ONLY_READS_POLICY_REENTRY_REVIEW_JSON_"
    "NO_DRYRUN_EXECUTION_NOW_NO_DATASET_HEADER_READ_NO_DATASET_VALUE_READ_NO_FEATURE_MANIFEST_READ_"
    "NO_AUTHORITY_SCAN_NO_TRAIN_NO_SCORE_NO_PREDICT_NO_VALIDATION_TEST_METRIC_COMPUTE_NO_TEST_READ_"
    "NO_MODEL_ARTIFACT_NO_ROW_PREDICTIONS_NO_SIM_NO_QUEUE_NO_REVIEW_GATE_MUTATION_NO_SOURCE_MUTATION_"
    "NO_PROMOTION_NO_QUARANTINE_REMOVAL_NO_BRANCH_REOPEN_NO_IDENTICAL_POLICY_INTAKE_LOOP_NO_SCHEMA_MUTATION"
)

EXPECTED_PRIOR_STATUS = "H001_RESTORED_60_FEATURE_AUTHORITY_POLICY_REENTRY_REVIEW_COMPLETE"
EXPECTED_PRIOR_DECISION = "APPROVE_RESTORED_60_FEATURE_AUTHORITY_POLICY_FOR_EXPLICIT_DRYRUN_CONTRACT_NO_EXECUTION"
EXPECTED_PRIOR_VERDICT = "PASS_RESTORED_60_FEATURE_AUTHORITY_POLICY_REENTRY_REVIEW_READY_FOR_EXPLICIT_DRYRUN_CONTRACT"

CONTRACT_STATUS = "H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_MATERIALIZED_READY_FOR_EXECUTION_REVIEW"
CONTRACT_DECISION = "OPEN_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_NEXT_NO_EXECUTION_NOW"
CONTRACT_VERDICT = "PASS_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_ROUTE_SELECTED_NO_EXECUTION_NOW"
FINAL_STATUS = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_PASS_PARKED"
QUALITY_CLASSIFICATION = "H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_ACCEPTED_EXECUTION_CONTRACT_NEXT_NO_EXECUTION"

NEXT_GATE = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_VALIDATION_DRYRUN_EXECUTION_CONTRACT_v0.1_AFTER_RESTORED_AUTHORITY_DRYRUN_CONTRACT"
LEGAL_NEXT_GATES = [NEXT_GATE, "PARK_AND_STOP"]

FUTURE_SCOPE = "TRAIN_VALIDATION_ONLY_AGGREGATE_DIAGNOSTIC_DRYRUN_RESTORED_60_FEATURE_AUTHORITY_ONLY"


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


def write_md(path: Path, result: Dict[str, Any]) -> None:
    lines = [
        "# HYDRA H001 Restored 60-Feature Authority Dryrun Contract v0.1",
        "",
        "## Decision",
        "",
        f"- **overall_status**: `{result.get('overall_status')}`",
        f"- **final_restored_authority_dryrun_contract_status**: `{result.get('final_restored_authority_dryrun_contract_status')}`",
        f"- **restored_authority_dryrun_contract_status**: `{result.get('restored_authority_dryrun_contract_status')}`",
        f"- **restored_authority_dryrun_contract_decision**: `{result.get('restored_authority_dryrun_contract_decision')}`",
        f"- **restored_authority_dryrun_contract_verdict**: `{result.get('restored_authority_dryrun_contract_verdict')}`",
        f"- **quality_classification**: `{result.get('quality_classification')}`",
        f"- **recommended_next_gate**: `{result.get('recommended_next_gate')}`",
        "",
        "## Interpretation",
        "",
        result.get("contract_interpretation", ""),
        "",
        "## Restored Authority Carry-Forward",
        "",
        f"- **source_feature_count_used**: `{result.get('source_feature_count_used')}`",
        f"- **source_feature_order_sha256**: `{result.get('source_feature_order_sha256')}`",
        f"- **restored_authority_evidence_found**: `{result.get('restored_authority_evidence_found')}`",
        f"- **locked_60_feature_authority_restored_found**: `{result.get('locked_60_feature_authority_restored_found')}`",
        f"- **metadata_exclusion_resolution_found**: `{result.get('metadata_exclusion_resolution_found')}`",
        f"- **no_matrix_mutation_resolution_found**: `{result.get('no_matrix_mutation_resolution_found')}`",
        f"- **export_session_date_metadata_evidence_found**: `{result.get('export_session_date_metadata_evidence_found')}`",
        f"- **approved_future_execution_scope**: `{result.get('approved_future_execution_scope')}`",
        "",
        "## Blocked Actions In This Gate",
        "",
        "- dryrun execution",
        "- dataset header/value read",
        "- feature manifest read",
        "- authority scan",
        "- model fit/training",
        "- scoring/prediction",
        "- validation/test metric computation",
        "- test read",
        "- model artifact write",
        "- row-level predictions",
        "- simulation/backtest",
        "- trade signal generation",
        "- source/evidence/Review Gate/queue mutation",
        "- current-best promotion",
        "- quarantine removal",
        "- branch reopening",
        "- dataset/split mutation",
        "- canonical feature/schema mutation",
        "- identical policy-intake loop",
        "",
        "## Artifacts",
        "",
    ]
    for key in [
        "json",
        "md",
        "checks_csv",
        "decision_csv",
        "dryrun_contract_csv",
        "approved_scope_csv",
        "dryrun_execution_requirements_csv",
        "authority_carry_forward_csv",
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

    print("HYDRA H001 RESTORED 60-FEATURE AUTHORITY DRYRUN CONTRACT START")
    print(f"engine_id: {ENGINE_ID}")
    print(f"version: {VERSION}")
    print(f"contract_id: {CONTRACT_ID}")
    print(f"hydra_root: {hydra_root}")
    print(f"docs_dir: {docs_dir}")
    print(f"prior_restored_authority_policy_reentry_review_dir: {prior_dir}")
    print(f"mode: {MODE}")
    print(f"guardrail: {GUARDRAIL}")
    print()

    checks: List[Dict[str, Any]] = []
    failures: List[str] = []
    warnings: List[str] = []

    try:
        source_path = latest_result_json(prior_dir)
        source = read_json(source_path)
        add_check(checks, "source_policy_reentry_review_json_found", "found", str(source_path), "PASS")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    required_matches = [
        ("prior_overall_status", "PASS", source.get("overall_status")),
        ("prior_status", EXPECTED_PRIOR_STATUS, source.get("restored_authority_policy_reentry_review_status")),
        ("prior_decision", EXPECTED_PRIOR_DECISION, source.get("restored_authority_policy_reentry_review_decision")),
        ("prior_verdict", EXPECTED_PRIOR_VERDICT, source.get("restored_authority_policy_reentry_review_verdict")),
        ("source_feature_count_used", 60, source.get("source_feature_count_used")),
        ("restored_authority_evidence_found", True, boolish(source.get("restored_authority_evidence_found"))),
        ("locked_60_feature_authority_restored_found", True, boolish(source.get("locked_60_feature_authority_restored_found"))),
        ("metadata_exclusion_resolution_found", True, boolish(source.get("metadata_exclusion_resolution_found"))),
        ("no_matrix_mutation_resolution_found", True, boolish(source.get("no_matrix_mutation_resolution_found"))),
        ("export_session_date_metadata_evidence_found", True, boolish(source.get("export_session_date_metadata_evidence_found"))),
        ("review_contract_run_now", True, boolish(source.get("review_contract_run_now"))),
        ("dryrun_execution_run_now", False, boolish(source.get("dryrun_execution_run_now"))),
        ("model_fit_or_training_run", False, boolish(source.get("model_fit_or_training_run"))),
        ("model_scoring_or_prediction_run", False, boolish(source.get("model_scoring_or_prediction_run"))),
        ("validation_or_test_metric_computation_run", False, boolish(source.get("validation_or_test_metric_computation_run"))),
        ("dataset_header_read_run", False, boolish(source.get("dataset_header_read_run"))),
        ("dataset_value_read_run", False, boolish(source.get("dataset_value_read_run"))),
        ("test_values_read", False, boolish(source.get("test_values_read"))),
        ("model_artifact_written", False, boolish(source.get("model_artifact_written"))),
        ("canonical_feature_schema_mutation", False, boolish(source.get("canonical_feature_schema_mutation"))),
        ("schema_mutation_authorized", False, boolish(source.get("schema_mutation_authorized"))),
        ("promotion_supported_now", False, boolish(source.get("promotion_supported_now"))),
        ("current_best_promotion_authorized", False, boolish(source.get("current_best_promotion_authorized"))),
        ("quarantine_removal_authorized", False, boolish(source.get("quarantine_removal_authorized"))),
        ("identical_policy_intake_loop_authorized", False, boolish(source.get("identical_policy_intake_loop_authorized"))),
    ]

    for cid, expected, actual in required_matches:
        status = "PASS" if actual == expected else "FAIL"
        add_check(checks, cid, expected, actual, status, "CRITICAL" if status == "FAIL" else "INFO")
        if status == "FAIL":
            failures.append(f"{cid}: expected={expected!r}, actual={actual!r}")

    feature_hash = source.get("source_feature_order_sha256", "")
    if not isinstance(feature_hash, str) or len(feature_hash) != 64:
        add_check(checks, "source_feature_order_sha256_valid", "64-char sha256", feature_hash, "FAIL", "CRITICAL")
        failures.append("source_feature_order_sha256 missing or invalid")
    else:
        add_check(checks, "source_feature_order_sha256_valid", "64-char sha256", feature_hash, "PASS")

    if failures:
        overall_status = "FAIL"
        final_status = "MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_FAIL_PARKED"
        contract_status = "H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_FAILED"
        decision = "REJECT_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_REQUIRED_CHECKS_FAILED"
        verdict = "FAIL_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_NOT_READY"
        quality = "H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_FAILED_NO_EXECUTION"
        recommended_next = "PARK_AND_STOP"
        legal_next = ["PARK_AND_STOP"]
    else:
        overall_status = "PASS"
        final_status = FINAL_STATUS
        contract_status = CONTRACT_STATUS
        decision = CONTRACT_DECISION
        verdict = CONTRACT_VERDICT
        quality = QUALITY_CLASSIFICATION
        recommended_next = NEXT_GATE
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
        "final_restored_authority_dryrun_contract_status": final_status,
        "restored_authority_dryrun_contract_status": contract_status,
        "restored_authority_dryrun_contract_decision": decision,
        "restored_authority_dryrun_contract_verdict": verdict,
        "restored_authority_dryrun_contract_reason": (
            "restored_60_feature_authority_policy_review_validated_validation_dryrun_execution_contract_required_next_no_execution_now"
            if overall_status == "PASS"
            else "restored_60_feature_authority_dryrun_contract_failed_required_checks_no_execution"
        ),
        "quality_classification": quality,
        "contract_interpretation": (
            "Restored 60-feature authority dryrun contract materialized. The next gate may run a "
            "train/validation-only aggregate diagnostic dryrun using restored 60-feature authority. "
            "This contract gate does not execute dryrun, train, score, read data, mutate schema, promote, "
            "remove quarantine, or reopen branches."
            if overall_status == "PASS"
            else "Restored 60-feature authority dryrun contract failed required checks. Park and do not execute."
        ),
        "source_restored_authority_policy_reentry_review_json": str(source_path),
        "source_feature_count_used": source.get("source_feature_count_used"),
        "source_feature_order_sha256": source.get("source_feature_order_sha256"),
        "restored_authority_evidence_found": source.get("restored_authority_evidence_found"),
        "locked_60_feature_authority_restored_found": source.get("locked_60_feature_authority_restored_found"),
        "metadata_exclusion_resolution_found": source.get("metadata_exclusion_resolution_found"),
        "no_matrix_mutation_resolution_found": source.get("no_matrix_mutation_resolution_found"),
        "export_session_date_metadata_evidence_found": source.get("export_session_date_metadata_evidence_found"),
        "top_evidence_path": source.get("top_evidence_path"),
        "restored_authority_policy_candidate_id": source.get("restored_authority_policy_candidate_id"),
        "approved_future_execution_scope": FUTURE_SCOPE,
        "future_may_fit_train": overall_status == "PASS",
        "future_may_score_validation": overall_status == "PASS",
        "future_may_compute_validation_metrics": overall_status == "PASS",
        "future_may_read_train_validation_values": overall_status == "PASS",
        "future_may_read_test_values": False,
        "future_may_compute_test_metrics": False,
        "future_may_write_model_artifact": False,
        "future_may_write_row_level_predictions": False,
        "future_may_simulate_or_backtest": False,
        "future_may_generate_trade_signals": False,
        "future_may_mutate_hydra_state": False,
        "future_may_promote_current_best": False,
        "future_may_remove_quarantine": False,
        "selected_route": recommended_next,
        "selected_route_type": "restored_60_feature_authority_validation_dryrun_execution_contract" if overall_status == "PASS" else "park",
        "selected_restored_authority_validation_dryrun_execution_contract_next": overall_status == "PASS",
        "dryrun_contract_run_now": True,
        "dryrun_execution_run_now": False,
        "model_fit_or_training_run": False,
        "model_scoring_or_prediction_run": False,
        "validation_or_test_metric_computation_run": False,
        "dataset_header_read_run": False,
        "dataset_value_read_run": False,
        "feature_manifest_read_run": False,
        "authority_artifact_scan_run": False,
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
        "identical_policy_intake_loop_opened_now": False,
        "schema_mutation_authorized": False,
        "promotion_supported_now": False,
        "current_best_promotion_authorized": False,
        "quarantine_removal_authorized": False,
        "identical_policy_intake_loop_authorized": False,
        "fail_required_count": len(failures),
        "warning_count": len(warnings),
        "critical_fail_count": len(failures),
        "pass_count": sum(1 for c in checks if c.get("status") == "PASS"),
        "required_total": len(checks),
        "recommended_next_gate": recommended_next,
        "legal_next_gates": legal_next,
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"result_{stamp}.json"
    md_path = docs_dir / f"HYDRA_MODEL_TRAINING_H001_RESTORED_60_FEATURE_AUTHORITY_DRYRUN_CONTRACT_V0_1_{stamp}.md"
    checks_path = out_dir / f"checks_{stamp}.csv"
    decision_path = out_dir / f"decision_{stamp}.csv"
    dryrun_contract_path = out_dir / f"dryrun_contract_{stamp}.csv"
    approved_scope_path = out_dir / f"approved_scope_{stamp}.csv"
    dryrun_reqs_path = out_dir / f"dryrun_execution_requirements_{stamp}.csv"
    authority_path = out_dir / f"authority_carry_forward_{stamp}.csv"
    blocked_path = out_dir / f"blocked_actions_{stamp}.csv"
    artifact_inv_path = out_dir / f"artifact_inventory_{stamp}.csv"
    next_path = out_dir / f"next_gate_checklist_{stamp}.csv"

    result.update({
        "json": str(json_path),
        "md": str(md_path),
        "checks_csv": str(checks_path),
        "decision_csv": str(decision_path),
        "dryrun_contract_csv": str(dryrun_contract_path),
        "approved_scope_csv": str(approved_scope_path),
        "dryrun_execution_requirements_csv": str(dryrun_reqs_path),
        "authority_carry_forward_csv": str(authority_path),
        "blocked_actions_csv": str(blocked_path),
        "artifact_inventory_csv": str(artifact_inv_path),
        "next_gate_checklist_csv": str(next_path),
    })

    decision_rows = [{
        "contract_id": CONTRACT_ID,
        "engine_id": ENGINE_ID,
        "version": VERSION,
        "timestamp": result["run_timestamp"],
        "overall_status": overall_status,
        "final_status": final_status,
        "contract_status": contract_status,
        "decision": decision,
        "verdict": verdict,
        "quality_classification": quality,
        "source_json": str(source_path),
        "source_feature_count_used": result["source_feature_count_used"],
        "source_feature_order_sha256": result["source_feature_order_sha256"],
        "approved_future_execution_scope": FUTURE_SCOPE,
        "recommended_next_gate": recommended_next,
        "legal_next_gates": legal_next,
        "fail_required_count": len(failures),
        "warning_count": len(warnings),
    }]

    dryrun_contract_rows = [
        {"contract_item": "execution_scope", "value": FUTURE_SCOPE, "required": True, "notes": "future gate only"},
        {"contract_item": "feature_authority", "value": result["source_feature_order_sha256"], "required": True, "notes": "restored 60-feature authority"},
        {"contract_item": "feature_count", "value": result["source_feature_count_used"], "required": True, "notes": "must use restored 60 features"},
        {"contract_item": "test_seal", "value": "test_values_read=False", "required": True, "notes": "test remains sealed"},
        {"contract_item": "artifact_write", "value": "model_artifact_written=False", "required": True, "notes": "no model artifact"},
        {"contract_item": "row_predictions", "value": "row_level_predictions_written=False", "required": True, "notes": "aggregate outputs only"},
        {"contract_item": "promotion", "value": "promotion_supported_now=False", "required": True, "notes": "dryrun cannot promote"},
    ]

    approved_scope_rows = [
        {"scope_id": "SCOPE_001", "permission": "future_train_validation_only_dryrun_execution", "allowed": overall_status == "PASS", "notes": "next explicit execution contract only"},
        {"scope_id": "SCOPE_002", "permission": "future_fit_train", "allowed": overall_status == "PASS", "notes": "next gate only"},
        {"scope_id": "SCOPE_003", "permission": "future_score_validation", "allowed": overall_status == "PASS", "notes": "next gate only"},
        {"scope_id": "SCOPE_004", "permission": "future_compute_validation_metrics", "allowed": overall_status == "PASS", "notes": "next gate only"},
        {"scope_id": "SCOPE_005", "permission": "future_read_test_values", "allowed": False, "notes": "blocked"},
        {"scope_id": "SCOPE_006", "permission": "future_write_model_artifact", "allowed": False, "notes": "blocked"},
        {"scope_id": "SCOPE_007", "permission": "future_promote_current_best", "allowed": False, "notes": "blocked"},
        {"scope_id": "SCOPE_008", "permission": "schema_mutation", "allowed": False, "notes": "blocked"},
    ]

    dryrun_reqs_rows = [
        {"requirement_id": "REQ_001", "requirement": "must use restored 60-feature authority hash", "value": result["source_feature_order_sha256"], "required": True},
        {"requirement_id": "REQ_002", "requirement": "must use restored 60-feature count", "value": result["source_feature_count_used"], "required": True},
        {"requirement_id": "REQ_003", "requirement": "must remain train/validation-only aggregate diagnostic dryrun", "value": FUTURE_SCOPE, "required": True},
        {"requirement_id": "REQ_004", "requirement": "must not read test tail", "value": "test_values_read=False", "required": True},
        {"requirement_id": "REQ_005", "requirement": "must not write model artifact", "value": "model_artifact_written=False", "required": True},
        {"requirement_id": "REQ_006", "requirement": "must not write row-level predictions", "value": "row_level_predictions_written=False", "required": True},
        {"requirement_id": "REQ_007", "requirement": "must not mutate schema/matrix/source/review queue", "value": "mutation=False", "required": True},
        {"requirement_id": "REQ_008", "requirement": "must route to output review after execution", "value": "output_review_required_after_dryrun", "required": True},
    ]

    authority_rows = [{
        "authority_id": "AUTH_001_RESTORED_60_FEATURE",
        "source_feature_count_used": result["source_feature_count_used"],
        "source_feature_order_sha256": result["source_feature_order_sha256"],
        "restored_authority_evidence_found": result["restored_authority_evidence_found"],
        "locked_60_feature_authority_restored_found": result["locked_60_feature_authority_restored_found"],
        "metadata_exclusion_resolution_found": result["metadata_exclusion_resolution_found"],
        "no_matrix_mutation_resolution_found": result["no_matrix_mutation_resolution_found"],
        "export_session_date_metadata_evidence_found": result["export_session_date_metadata_evidence_found"],
        "top_evidence_path": result["top_evidence_path"],
    }]

    blocked_rows = [
        {"action_id": "BLOCK_001", "action": "dryrun_execution_now", "blocked": True},
        {"action_id": "BLOCK_002", "action": "model_fit_or_training_now", "blocked": True},
        {"action_id": "BLOCK_003", "action": "model_scoring_or_prediction_now", "blocked": True},
        {"action_id": "BLOCK_004", "action": "validation_or_test_metric_computation_now", "blocked": True},
        {"action_id": "BLOCK_005", "action": "dataset_header_or_value_read_now", "blocked": True},
        {"action_id": "BLOCK_006", "action": "feature_manifest_read_now", "blocked": True},
        {"action_id": "BLOCK_007", "action": "authority_scan_now", "blocked": True},
        {"action_id": "BLOCK_008", "action": "test_read_now", "blocked": True},
        {"action_id": "BLOCK_009", "action": "model_artifact_write_now", "blocked": True},
        {"action_id": "BLOCK_010", "action": "row_level_prediction_export_now", "blocked": True},
        {"action_id": "BLOCK_011", "action": "simulation_or_backtest_now", "blocked": True},
        {"action_id": "BLOCK_012", "action": "source_evidence_review_gate_queue_mutation_now", "blocked": True},
        {"action_id": "BLOCK_013", "action": "current_best_promotion_now", "blocked": True},
        {"action_id": "BLOCK_014", "action": "quarantine_removal_now", "blocked": True},
        {"action_id": "BLOCK_015", "action": "branch_reopen_now", "blocked": True},
        {"action_id": "BLOCK_016", "action": "schema_mutation_now", "blocked": True},
        {"action_id": "BLOCK_017", "action": "identical_policy_intake_loop_now", "blocked": True},
    ]

    artifact_rows = [
        {"artifact_key": "source_policy_reentry_review_json", "path": str(source_path), "exists": source_path.exists()},
        {"artifact_key": "result_json", "path": str(json_path), "exists": True},
        {"artifact_key": "report_md", "path": str(md_path), "exists": True},
        {"artifact_key": "checks_csv", "path": str(checks_path), "exists": True},
        {"artifact_key": "decision_csv", "path": str(decision_path), "exists": True},
        {"artifact_key": "dryrun_contract_csv", "path": str(dryrun_contract_path), "exists": True},
        {"artifact_key": "approved_scope_csv", "path": str(approved_scope_path), "exists": True},
        {"artifact_key": "dryrun_execution_requirements_csv", "path": str(dryrun_reqs_path), "exists": True},
        {"artifact_key": "authority_carry_forward_csv", "path": str(authority_path), "exists": True},
        {"artifact_key": "blocked_actions_csv", "path": str(blocked_path), "exists": True},
        {"artifact_key": "next_gate_checklist_csv", "path": str(next_path), "exists": True},
    ]

    next_rows = [
        {"route_id": "NEXT_001", "candidate_route": NEXT_GATE, "selected": overall_status == "PASS", "reason": "explicit restored 60-feature authority validation dryrun execution contract required next"},
        {"route_id": "NEXT_002", "candidate_route": "PARK_AND_STOP", "selected": overall_status != "PASS", "reason": "legal fallback"},
    ]

    write_json(json_path, result)
    write_md(md_path, result)
    write_csv(checks_path, checks)
    write_csv(decision_path, decision_rows)
    write_csv(dryrun_contract_path, dryrun_contract_rows)
    write_csv(approved_scope_path, approved_scope_rows)
    write_csv(dryrun_reqs_path, dryrun_reqs_rows)
    write_csv(authority_path, authority_rows)
    write_csv(blocked_path, blocked_rows)
    write_csv(artifact_inv_path, artifact_rows)
    write_csv(next_path, next_rows)

    print("HYDRA H001 RESTORED 60-FEATURE AUTHORITY DRYRUN CONTRACT COMPLETE")
    print(f"overall_status: {overall_status}")
    print(f"final_restored_authority_dryrun_contract_status: {final_status}")
    print(f"restored_authority_dryrun_contract_status: {contract_status}")
    print(f"restored_authority_dryrun_contract_decision: {decision}")
    print(f"restored_authority_dryrun_contract_verdict: {verdict}")
    print(f"quality_classification: {quality}")
    print(f"source_restored_authority_policy_reentry_review_json: {source_path}")
    print(f"source_feature_count_used: {result['source_feature_count_used']}")
    print(f"source_feature_order_sha256: {result['source_feature_order_sha256']}")
    print(f"restored_authority_evidence_found: {result['restored_authority_evidence_found']}")
    print(f"locked_60_feature_authority_restored_found: {result['locked_60_feature_authority_restored_found']}")
    print(f"metadata_exclusion_resolution_found: {result['metadata_exclusion_resolution_found']}")
    print(f"no_matrix_mutation_resolution_found: {result['no_matrix_mutation_resolution_found']}")
    print(f"export_session_date_metadata_evidence_found: {result['export_session_date_metadata_evidence_found']}")
    print(f"approved_future_execution_scope: {result['approved_future_execution_scope']}")
    print(f"future_may_fit_train: {result['future_may_fit_train']}")
    print(f"future_may_score_validation: {result['future_may_score_validation']}")
    print(f"future_may_compute_validation_metrics: {result['future_may_compute_validation_metrics']}")
    print("dryrun_contract_run_now: True")
    print("dryrun_execution_run_now: False")
    print("model_fit_or_training_run: False")
    print("model_scoring_or_prediction_run: False")
    print("validation_or_test_metric_computation_run: False")
    print("dataset_header_read_run: False")
    print("dataset_value_read_run: False")
    print("test_values_read: False")
    print("model_artifact_written: False")
    print("canonical_feature_schema_mutation: False")
    print(f"fail_required_count: {len(failures)}")
    print(f"warning_count: {len(warnings)}")
    print(f"critical_fail_count: {len(failures)}")
    print(f"pass_count: {result['pass_count']}")
    print(f"required_total: {result['required_total']}")
    print(f"recommended_next_gate: {recommended_next}")
    print(f"json: {json_path}")
    print(f"md: {md_path}")
    print(f"checks_csv: {checks_path}")
    print(f"decision_csv: {decision_path}")
    print(f"dryrun_contract_csv: {dryrun_contract_path}")
    print(f"approved_scope_csv: {approved_scope_path}")
    print(f"dryrun_execution_requirements_csv: {dryrun_reqs_path}")
    print(f"authority_carry_forward_csv: {authority_path}")
    print(f"blocked_actions_csv: {blocked_path}")
    print(f"artifact_inventory_csv: {artifact_inv_path}")
    print(f"next_gate_checklist_csv: {next_path}")
    print(f"legal_next_gates: {legal_next}")
    print()
    print("GUARDRAILS CONFIRMED:")
    print(
        "restored 60-feature authority dryrun contract only; read prior policy re-entry review JSON only; "
        "materialized explicit restored-authority validation dryrun execution contract next; no dryrun execution now, "
        "no dataset header/value read, no feature manifest read, no authority artifact scan, no model fit/training, "
        "no scoring/prediction, no validation/test model metric computation, no test read, no model artifact, "
        "no row-level predictions, no sim/backtest, no trade signals, no source/evidence/Review Gate/queue mutation, "
        "no current-best promotion, no quarantine removal, no branch reopening, no dataset/split mutation, "
        "no canonical feature/schema mutation, no identical policy-intake loop"
    )
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
