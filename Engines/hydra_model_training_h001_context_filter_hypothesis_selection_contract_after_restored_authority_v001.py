#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HYDRA H001 Context Filter Hypothesis Selection Contract After Restored Authority v0.1

Contract:
  MODEL_TRAINING_H001_CONTEXT_FILTER_HYPOTHESIS_SELECTION_CONTRACT_v0.1_AFTER_NEW_HYPOTHESIS_REVIEW_SELECTION_PACKET

Purpose:
  Select the context_filter hypothesis candidate after the restored 60-feature authority branch
  terminal handoff and new-hypothesis review packet.

Why context_filter:
  - Restored 60-feature authority is solved.
  - The restored 60-feature HGB full-sample dryrun degraded balanced accuracy.
  - A context/regime filter is materially different from an identical model retry.
  - It targets mixed-regime class confusion and balanced-recall degradation.

Guardrails:
  - Selection contract only.
  - Reads prior new-hypothesis review selection packet JSON only.
  - No dataset header/value read.
  - No feature manifest read.
  - No authority artifact scan.
  - No model fit/training.
  - No scoring/prediction.
  - No validation/test metric computation.
  - No test read.
  - No model artifact.
  - No row-level predictions.
  - No simulation/backtest.
  - No trade signals.
  - No source/evidence/Review Gate/queue mutation.
  - No current-best promotion.
  - No quarantine removal.
  - No branch reopening.
  - No dataset/split mutation.
  - No canonical feature/schema mutation.
  - No identical model lane.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ENGINE_ID = "hydra_model_training_h001_context_filter_hypothesis_selection_contract_after_restored_authority_v001.py"
VERSION = "v0_1"
CONTRACT_ID = "MODEL_TRAINING_H001_CONTEXT_FILTER_HYPOTHESIS_SELECTION_CONTRACT_v0.1_AFTER_NEW_HYPOTHESIS_REVIEW_SELECTION_PACKET"

PRIOR_DIR_REL = Path("data") / "canonical" / "h001_new_hypothesis_review_selection_packet_after_restored_authority_v0_1"
OUT_DIR_REL = Path("data") / "canonical" / "h001_context_filter_hypothesis_selection_after_restored_authority_v0_1"

MODE = "H001_CONTEXT_FILTER_HYPOTHESIS_SELECTION_ONLY_NO_DATASET_NO_MODEL_NO_MUTATION"
GUARDRAIL = (
    "CONTEXT_FILTER_HYPOTHESIS_SELECTION_ONLY_READS_PRIOR_SELECTION_PACKET_JSON_"
    "NO_DATASET_HEADER_READ_NO_DATASET_VALUE_READ_NO_FEATURE_MANIFEST_READ_NO_AUTHORITY_SCAN_"
    "NO_TRAIN_NO_SCORE_NO_PREDICT_NO_VALIDATION_TEST_METRIC_COMPUTE_NO_TEST_READ_NO_MODEL_ARTIFACT_"
    "NO_ROW_PREDICTIONS_NO_SIM_NO_QUEUE_NO_REVIEW_GATE_MUTATION_NO_SOURCE_MUTATION_NO_PROMOTION_"
    "NO_QUARANTINE_REMOVAL_NO_BRANCH_REOPEN_NO_SCHEMA_MUTATION_NO_IDENTICAL_MODEL_LANE"
)

EXPECTED_PRIOR_STATUS = "H001_NEW_HYPOTHESIS_REVIEW_SELECTION_PACKET_AFTER_RESTORED_AUTHORITY_COMPLETE"
EXPECTED_PRIOR_DECISION = "PREPARE_NEW_HYPOTHESIS_CANDIDATE_REVIEW_PACKET_FOR_HUMAN_SELECTION_NO_EXECUTION"
EXPECTED_PRIOR_VERDICT = "PASS_NEW_HYPOTHESIS_REVIEW_SELECTION_PACKET_READY_PARK_AND_STOP"
EXPECTED_PRIOR_QUALITY = "H001_NEW_HYPOTHESIS_REVIEW_SELECTION_PACKET_READY_HUMAN_SELECTION_REQUIRED_NO_EXECUTION"

SELECTED_CANDIDATE_ID = "H001_NEW_HYPOTHESIS_CANDIDATE_001_CONTEXT_FILTER"
SELECTED_HYPOTHESIS_FAMILY = "context_filter"

FINAL_STATUS_PASS = "MODEL_TRAINING_H001_CONTEXT_FILTER_HYPOTHESIS_SELECTION_CONTRACT_PASS_PARKED"
SELECTION_STATUS_PASS = "H001_CONTEXT_FILTER_HYPOTHESIS_SELECTION_COMPLETE"
SELECTION_DECISION_PASS = "SELECT_CONTEXT_FILTER_HYPOTHESIS_POLICY_CONTRACT_NEXT_NO_EXECUTION"
SELECTION_VERDICT_PASS = "PASS_CONTEXT_FILTER_HYPOTHESIS_SELECTION_READY_FOR_POLICY_CONTRACT"
QUALITY_PASS = "H001_CONTEXT_FILTER_HYPOTHESIS_SELECTION_ACCEPTED_POLICY_CONTRACT_NEXT_NO_EXECUTION"

NEXT_GATE = "MODEL_TRAINING_H001_CONTEXT_FILTER_HYPOTHESIS_POLICY_CONTRACT_v0.1_AFTER_CONTEXT_FILTER_HYPOTHESIS_SELECTION"
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
        "# HYDRA H001 Context Filter Hypothesis Selection Contract After Restored Authority v0.1",
        "",
        "## Decision",
        "",
        f"- **overall_status**: `{result.get('overall_status')}`",
        f"- **final_context_filter_hypothesis_selection_status**: `{result.get('final_context_filter_hypothesis_selection_status')}`",
        f"- **context_filter_hypothesis_selection_status**: `{result.get('context_filter_hypothesis_selection_status')}`",
        f"- **context_filter_hypothesis_selection_decision**: `{result.get('context_filter_hypothesis_selection_decision')}`",
        f"- **context_filter_hypothesis_selection_verdict**: `{result.get('context_filter_hypothesis_selection_verdict')}`",
        f"- **quality_classification**: `{result.get('quality_classification')}`",
        f"- **selected_hypothesis_family**: `{result.get('selected_hypothesis_family')}`",
        f"- **recommended_next_gate**: `{result.get('recommended_next_gate')}`",
        "",
        "## Interpretation",
        "",
        result.get("selection_interpretation", ""),
        "",
        "## Why This Candidate",
        "",
        "- Restored 60-feature authority is already fixed.",
        "- Full-sample HGB degraded balanced accuracy.",
        "- Context filtering is materially different from an identical HGB retry.",
        "- The next policy contract should define safe, bounded context-filter review only.",
        "",
        "## Guardrails",
        "",
        "- No dataset reads.",
        "- No training/scoring.",
        "- No test read.",
        "- No model artifact.",
        "- No promotion.",
        "- No schema mutation.",
        "- No identical model-lane retry.",
        "",
        "## Artifacts",
        "",
    ]
    for key in [
        "json",
        "md",
        "checks_csv",
        "decision_csv",
        "selected_candidate_csv",
        "hypothesis_requirements_csv",
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

    print("HYDRA H001 CONTEXT FILTER HYPOTHESIS SELECTION CONTRACT AFTER RESTORED AUTHORITY START")
    print(f"engine_id: {ENGINE_ID}")
    print(f"version: {VERSION}")
    print(f"contract_id: {CONTRACT_ID}")
    print(f"hydra_root: {hydra_root}")
    print(f"docs_dir: {docs_dir}")
    print(f"prior_new_hypothesis_review_selection_packet_dir: {prior_dir}")
    print(f"mode: {MODE}")
    print(f"guardrail: {GUARDRAIL}")
    print()

    checks: List[Dict[str, Any]] = []
    failures: List[str] = []
    warnings: List[str] = []

    try:
        source_path = latest_result_json(prior_dir)
        source = read_json(source_path)
        add_check(checks, "source_selection_packet_json_found", "found", str(source_path), "PASS")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    required_matches = [
        ("source_overall_status", "PASS", source.get("overall_status")),
        ("source_packet_status", EXPECTED_PRIOR_STATUS, source.get("new_hypothesis_review_selection_packet_status")),
        ("source_packet_decision", EXPECTED_PRIOR_DECISION, source.get("new_hypothesis_review_selection_packet_decision")),
        ("source_packet_verdict", EXPECTED_PRIOR_VERDICT, source.get("new_hypothesis_review_selection_packet_verdict")),
        ("source_quality", EXPECTED_PRIOR_QUALITY, source.get("quality_classification")),
        ("source_candidate_option_count", 5, source.get("candidate_option_count")),
        ("source_human_selection_required", True, boolish(source.get("human_selection_required"))),
        ("source_selected_hypothesis_now", False, boolish(source.get("selected_hypothesis_now"))),
        ("authority_restored_and_matched", True, boolish(source.get("authority_restored_and_matched"))),
        ("source_feature_count_used", 60, source.get("source_feature_count_used")),
        ("selected_feature_count", 60, source.get("selected_feature_count")),
        ("export_session_date_excluded", True, boolish(source.get("export_session_date_excluded"))),
        ("material_balanced_accuracy_drop", True, boolish(source.get("material_balanced_accuracy_drop"))),
        ("new_hypothesis_required_for_any_future_model_lane", True, boolish(source.get("new_hypothesis_required_for_any_future_model_lane"))),
        ("identical_model_lane_authorized", False, boolish(source.get("identical_model_lane_authorized"))),
        ("promotion_supported_now", False, boolish(source.get("promotion_supported_now"))),
        ("schema_mutation_authorized", False, boolish(source.get("schema_mutation_authorized"))),
        ("dataset_value_read_run", False, boolish(source.get("dataset_value_read_run"))),
        ("model_fit_or_training_run", False, boolish(source.get("model_fit_or_training_run"))),
        ("model_scoring_or_prediction_run", False, boolish(source.get("model_scoring_or_prediction_run"))),
        ("test_values_read", False, boolish(source.get("test_values_read"))),
        ("model_artifact_written", False, boolish(source.get("model_artifact_written"))),
        ("canonical_feature_schema_mutation", False, boolish(source.get("canonical_feature_schema_mutation"))),
    ]

    for cid, expected, actual in required_matches:
        status = "PASS" if actual == expected else "FAIL"
        add_check(checks, cid, expected, actual, status, "CRITICAL" if status == "FAIL" else "INFO")
        if status == "FAIL":
            failures.append(f"{cid}: expected={expected!r}, actual={actual!r}")

    candidates = source.get("candidate_hypothesis_options", [])
    selected_candidate = None
    if isinstance(candidates, list):
        for c in candidates:
            if isinstance(c, dict) and c.get("candidate_id") == SELECTED_CANDIDATE_ID:
                selected_candidate = c
                break

    if selected_candidate is None:
        failures.append(f"Candidate not found in prior packet: {SELECTED_CANDIDATE_ID}")
        add_check(checks, "selected_candidate_found", SELECTED_CANDIDATE_ID, None, "FAIL", "CRITICAL")
    else:
        add_check(checks, "selected_candidate_found", SELECTED_CANDIDATE_ID, selected_candidate.get("candidate_id"), "PASS")
        add_check(checks, "selected_candidate_family", SELECTED_HYPOTHESIS_FAMILY, selected_candidate.get("hypothesis_family"), "PASS" if selected_candidate.get("hypothesis_family") == SELECTED_HYPOTHESIS_FAMILY else "FAIL")

    if failures:
        overall_status = "FAIL"
        final_status = "MODEL_TRAINING_H001_CONTEXT_FILTER_HYPOTHESIS_SELECTION_CONTRACT_FAIL_PARKED"
        selection_status = "H001_CONTEXT_FILTER_HYPOTHESIS_SELECTION_FAILED"
        selection_decision = "REJECT_CONTEXT_FILTER_HYPOTHESIS_SELECTION_REQUIRED_CHECKS_FAILED"
        selection_verdict = "FAIL_CONTEXT_FILTER_HYPOTHESIS_SELECTION_NOT_READY"
        quality = "H001_CONTEXT_FILTER_HYPOTHESIS_SELECTION_FAILED"
        next_gate = "PARK_AND_STOP"
        legal_next_gates = ["PARK_AND_STOP"]
    else:
        overall_status = "PASS"
        final_status = FINAL_STATUS_PASS
        selection_status = SELECTION_STATUS_PASS
        selection_decision = SELECTION_DECISION_PASS
        selection_verdict = SELECTION_VERDICT_PASS
        quality = QUALITY_PASS
        next_gate = NEXT_GATE
        legal_next_gates = LEGAL_NEXT_GATES

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
        "final_context_filter_hypothesis_selection_status": final_status,
        "context_filter_hypothesis_selection_status": selection_status,
        "context_filter_hypothesis_selection_decision": selection_decision,
        "context_filter_hypothesis_selection_verdict": selection_verdict,
        "quality_classification": quality,
        "selection_interpretation": (
            "Context-filter hypothesis selected for the next policy contract. This is a materially different hypothesis from the closed restored 60-feature full-sample HGB lane. "
            "It targets the balanced-accuracy degradation by proposing regime/context gating before any future model execution. This selection contract opens only a future policy contract; it does not execute, train, score, read data, promote, mutate schema, or reopen branches."
            if overall_status == "PASS"
            else "Context-filter hypothesis selection failed required checks. Park."
        ),
        "source_new_hypothesis_review_selection_packet_json": str(source_path),
        "selected_candidate_id": SELECTED_CANDIDATE_ID if overall_status == "PASS" else "",
        "selected_hypothesis_family": SELECTED_HYPOTHESIS_FAMILY if overall_status == "PASS" else "",
        "selected_candidate_label": selected_candidate.get("candidate_label") if selected_candidate else "",
        "selected_candidate_first_safe_contract": selected_candidate.get("first_safe_contract") if selected_candidate else "",
        "material_difference_from_closed_lane": selected_candidate.get("material_difference_from_closed_lane") if selected_candidate else "",
        "why_it_targets_balanced_accuracy": selected_candidate.get("why_it_targets_balanced_accuracy") if selected_candidate else "",
        "authority_restored_and_matched": source.get("authority_restored_and_matched"),
        "source_feature_count_used": source.get("source_feature_count_used"),
        "selected_feature_count": source.get("selected_feature_count"),
        "export_session_date_excluded": source.get("export_session_date_excluded"),
        "validation_balanced_accuracy_delta_vs_reference": source.get("validation_balanced_accuracy_delta_vs_reference"),
        "material_balanced_accuracy_drop": source.get("material_balanced_accuracy_drop"),
        "old_branch_terminal_parked": True,
        "old_model_lane_not_edgeful": True,
        "new_hypothesis_required_for_any_future_model_lane": True,
        "context_filter_policy_contract_required_next": overall_status == "PASS",
        "context_filter_policy_contract_run_now": False,
        "dryrun_execution_run_now": False,
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
        "schema_mutation_authorized": False,
        "promotion_supported_now": False,
        "current_best_promotion_authorized": False,
        "quarantine_removal_authorized": False,
        "identical_model_lane_authorized": False,
        "identical_model_lane_opened_now": False,
        "fail_required_count": len(failures),
        "warning_count": len(warnings),
        "critical_fail_count": len(failures),
        "pass_count": sum(1 for c in checks if c.get("status") == "PASS"),
        "required_total": len(checks),
        "recommended_next_gate": next_gate,
        "legal_next_gates": legal_next_gates,
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"result_{stamp}.json"
    md_path = docs_dir / f"HYDRA_MODEL_TRAINING_H001_CONTEXT_FILTER_HYPOTHESIS_SELECTION_CONTRACT_AFTER_RESTORED_AUTHORITY_V0_1_{stamp}.md"
    checks_path = out_dir / f"checks_{stamp}.csv"
    decision_path = out_dir / f"decision_{stamp}.csv"
    selected_path = out_dir / f"selected_candidate_{stamp}.csv"
    reqs_path = out_dir / f"hypothesis_requirements_{stamp}.csv"
    blocked_path = out_dir / f"blocked_actions_{stamp}.csv"
    artifact_path = out_dir / f"artifact_inventory_{stamp}.csv"
    next_path = out_dir / f"next_gate_checklist_{stamp}.csv"

    result.update({
        "json": str(json_path),
        "md": str(md_path),
        "checks_csv": str(checks_path),
        "decision_csv": str(decision_path),
        "selected_candidate_csv": str(selected_path),
        "hypothesis_requirements_csv": str(reqs_path),
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
        "selection_status": selection_status,
        "selection_decision": selection_decision,
        "selection_verdict": selection_verdict,
        "quality_classification": quality,
        "selected_candidate_id": result["selected_candidate_id"],
        "selected_hypothesis_family": result["selected_hypothesis_family"],
        "recommended_next_gate": next_gate,
        "legal_next_gates": legal_next_gates,
    }]

    selected_rows = [{
        "selected_candidate_id": result["selected_candidate_id"],
        "hypothesis_family": result["selected_hypothesis_family"],
        "candidate_label": result["selected_candidate_label"],
        "material_difference_from_closed_lane": result["material_difference_from_closed_lane"],
        "why_it_targets_balanced_accuracy": result["why_it_targets_balanced_accuracy"],
        "first_safe_contract": result["selected_candidate_first_safe_contract"],
        "execution_now": False,
    }]

    req_rows = [
        {"requirement_id": "REQ_001", "requirement": "must define explicit context filters/regime gates", "required": True},
        {"requirement_id": "REQ_002", "requirement": "must prove material difference from closed restored-authority full-sample HGB lane", "required": True},
        {"requirement_id": "REQ_003", "requirement": "must keep test sealed", "required": True},
        {"requirement_id": "REQ_004", "requirement": "must not mutate schema or source data", "required": True},
        {"requirement_id": "REQ_005", "requirement": "must not promote or remove quarantine", "required": True},
        {"requirement_id": "REQ_006", "requirement": "must route through policy/review before execution", "required": True},
    ]

    blocked_rows = [
        {"action_id": "BLOCK_001", "action": "model_execution_now", "blocked": True},
        {"action_id": "BLOCK_002", "action": "dataset_header_or_value_read_now", "blocked": True},
        {"action_id": "BLOCK_003", "action": "feature_manifest_read_now", "blocked": True},
        {"action_id": "BLOCK_004", "action": "test_value_read_now", "blocked": True},
        {"action_id": "BLOCK_005", "action": "model_artifact_write_now", "blocked": True},
        {"action_id": "BLOCK_006", "action": "promotion_now", "blocked": True},
        {"action_id": "BLOCK_007", "action": "schema_mutation_now", "blocked": True},
        {"action_id": "BLOCK_008", "action": "identical_model_lane_retry_now", "blocked": True},
        {"action_id": "BLOCK_009", "action": "quarantine_removal_now", "blocked": True},
        {"action_id": "BLOCK_010", "action": "branch_reopen_now", "blocked": True},
    ]

    artifact_rows = [
        {"artifact_key": "source_selection_packet_json", "path": str(source_path), "exists": source_path.exists()},
        {"artifact_key": "result_json", "path": str(json_path), "exists": True},
        {"artifact_key": "report_md", "path": str(md_path), "exists": True},
        {"artifact_key": "selected_candidate_csv", "path": str(selected_path), "exists": True},
        {"artifact_key": "hypothesis_requirements_csv", "path": str(reqs_path), "exists": True},
        {"artifact_key": "next_gate_checklist_csv", "path": str(next_path), "exists": True},
    ]

    next_rows = [
        {"route_id": "NEXT_001", "candidate_route": NEXT_GATE, "selected": overall_status == "PASS", "reason": "context-filter hypothesis selected; policy contract required"},
        {"route_id": "NEXT_002", "candidate_route": "PARK_AND_STOP", "selected": overall_status != "PASS", "reason": "legal fallback"},
    ]

    write_json(json_path, result)
    write_md(md_path, result)
    write_csv(checks_path, checks)
    write_csv(decision_path, decision_rows)
    write_csv(selected_path, selected_rows)
    write_csv(reqs_path, req_rows)
    write_csv(blocked_path, blocked_rows)
    write_csv(artifact_path, artifact_rows)
    write_csv(next_path, next_rows)

    print("HYDRA H001 CONTEXT FILTER HYPOTHESIS SELECTION CONTRACT AFTER RESTORED AUTHORITY COMPLETE")
    print(f"overall_status: {overall_status}")
    print(f"final_context_filter_hypothesis_selection_status: {final_status}")
    print(f"context_filter_hypothesis_selection_status: {selection_status}")
    print(f"context_filter_hypothesis_selection_decision: {selection_decision}")
    print(f"context_filter_hypothesis_selection_verdict: {selection_verdict}")
    print(f"quality_classification: {quality}")
    print(f"source_new_hypothesis_review_selection_packet_json: {source_path}")
    print(f"selected_candidate_id: {result['selected_candidate_id']}")
    print(f"selected_hypothesis_family: {result['selected_hypothesis_family']}")
    print(f"selected_candidate_label: {result['selected_candidate_label']}")
    print(f"material_difference_from_closed_lane: {result['material_difference_from_closed_lane']}")
    print(f"why_it_targets_balanced_accuracy: {result['why_it_targets_balanced_accuracy']}")
    print(f"authority_restored_and_matched: {result['authority_restored_and_matched']}")
    print(f"source_feature_count_used: {result['source_feature_count_used']}")
    print(f"selected_feature_count: {result['selected_feature_count']}")
    print(f"export_session_date_excluded: {result['export_session_date_excluded']}")
    print(f"validation_balanced_accuracy_delta_vs_reference: {result['validation_balanced_accuracy_delta_vs_reference']}")
    print(f"material_balanced_accuracy_drop: {result['material_balanced_accuracy_drop']}")
    print("context_filter_policy_contract_run_now: False")
    print("dryrun_execution_run_now: False")
    print("dataset_header_read_run: False")
    print("dataset_value_read_run: False")
    print("model_fit_or_training_run: False")
    print("model_scoring_or_prediction_run: False")
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
    print(f"selected_candidate_csv: {selected_path}")
    print(f"hypothesis_requirements_csv: {reqs_path}")
    print(f"blocked_actions_csv: {blocked_path}")
    print(f"artifact_inventory_csv: {artifact_path}")
    print(f"next_gate_checklist_csv: {next_path}")
    print(f"legal_next_gates: {legal_next_gates}")
    print()
    print("GUARDRAILS CONFIRMED:")
    print(
        "context-filter hypothesis selection only; read prior new-hypothesis review selection packet JSON only; "
        "selected context_filter for future policy contract; no dataset header/value read, no feature manifest read, "
        "no authority artifact scan, no model fit/training, no scoring/prediction, no validation/test model metric computation, "
        "no test read, no model artifact, no row-level predictions, no sim/backtest, no trade signals, no source/evidence/"
        "Review Gate/queue mutation, no current-best promotion, no quarantine removal, no branch reopening, no dataset/split "
        "mutation, no canonical feature/schema mutation, no identical model lane"
    )
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
