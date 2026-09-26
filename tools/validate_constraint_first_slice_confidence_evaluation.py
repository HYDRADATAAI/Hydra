#!/usr/bin/env python3
"""Validate Batch015 typed-confidence and evaluation-readiness closure."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("HYDRA_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
SLICE = ROOT / "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
ARCH = ROOT / "docs/constraint/architecture"

CONF = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_AI_DATA_CENTER_POWER_INFRASTRUCTURE_TYPED_CONFIDENCE_OVERLAY_V001_20260925.json"
EVAL = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_AI_DATA_CENTER_POWER_INFRASTRUCTURE_EVALUATION_PROTOCOL_V001_20260925.json"
GATE = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json"
BLOCKERS = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BLOCKER_REGISTER_V001_20260925.json"
MASTER = ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_MASTER_STATUS_V001_20260925.json"

CANDIDATES10 = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_T5_CANDIDATE_PROPOSALS_V001_20260925.json"
BENEFICIARIES10 = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BENEFICIARY_EVALUATIONS_V001_20260925.json"
CASE_MATRIX13 = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_AI_DATA_CENTER_POWER_INFRASTRUCTURE_REQUIRED_CASE_MATRIX_V001_20260925.json"
MASTER12 = ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_MASTER_STATUS_V001_20260925.json"

CONF1 = "ACCEPT-014-CONF-001-TYPED-FORMATION-CONFIDENCE-NOT-POPULATED"
CONF2 = "ACCEPT-014-CONF-002-BENEFICIARY-CONFIDENCE-VALUES-NULL"
EVAL1 = "ACCEPT-014-EVAL-001-REAL-OUTCOME-COVERAGE-THIN"
EVAL2 = "ACCEPT-014-EVAL-002-NO-ORDINARY-CANONICAL-OUTPUTS-TO-EVALUATE"
EVAL3 = "ACCEPT-014-EVAL-003-ORDINARY-REPLAY-NOT-READY"
RAW = "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"
ADMISSION = "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT"


class ValidationFailure(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"required artifact missing: {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    conf = load(CONF)
    evaluation = load(EVAL)
    gate = load(GATE)
    blockers = load(BLOCKERS)
    master = load(MASTER)
    candidates = load(CANDIDATES10)
    beneficiaries = load(BENEFICIARIES10)
    matrix13 = load(CASE_MATRIX13)
    master12 = load(MASTER12)

    require(conf.get("numeric_confidence_values_invented") == 0, "numeric confidence was invented")

    candidate_ids = {row["constraint_candidate_id"] for row in candidates.get("candidates", [])}
    conf_candidate_rows = conf.get("candidate_confidence")
    require(isinstance(conf_candidate_rows, list) and len(conf_candidate_rows) == 3, "typed formation-confidence row count drifted")
    require({row.get("constraint_candidate_id") for row in conf_candidate_rows} == candidate_ids, "formation-confidence candidate set drifted")
    for row in conf_candidate_rows:
        require(row.get("confidence_type") == "FORMATION_CONFIDENCE", "formation confidence type drifted")
        require(row.get("semantic_owner_id") == "PIPELINE_T5_CONSTRAINT_FORMATION", "formation confidence owner drifted")
        require(row.get("measurement_state") == "UNKNOWN_NOT_MEASURED", "formation confidence state drifted")
        require(row.get("value") is None, "formation confidence numeric value was fabricated")
        require(row.get("unit") is None, "formation confidence unit was fabricated")
        require("not probability" in row.get("meaning", "").lower(), "formation confidence truth-probability firewall missing")

    relationship_ids = {row["beneficiary_relationship_id"] for row in beneficiaries.get("relationships", [])}
    conf_beneficiary_rows = conf.get("beneficiary_confidence")
    require(isinstance(conf_beneficiary_rows, list) and len(conf_beneficiary_rows) == 4, "typed beneficiary-confidence row count drifted")
    require({row.get("beneficiary_relationship_id") for row in conf_beneficiary_rows} == relationship_ids, "beneficiary-confidence relationship set drifted")
    for row in conf_beneficiary_rows:
        require(row.get("confidence_type") == "BENEFICIARY_CONFIDENCE", "beneficiary confidence type drifted")
        require(row.get("semantic_owner_id") == "PIPELINE_T6_CANONICAL_CANDIDATE_GOVERNANCE", "beneficiary confidence owner drifted")
        require(row.get("measurement_state") == "UNKNOWN_INELIGIBLE_TO_EVALUATE", "beneficiary confidence state drifted")
        require(row.get("value") is None, "beneficiary confidence numeric value was fabricated")
        require(row.get("qualification_state") == "INELIGIBLE_TO_EVALUATE", "beneficiary confidence qualification state drifted")

    # The overlay must not mutate predecessor confidence fields in place.
    require(all("formation_confidence" not in row for row in candidates["candidates"]), "Batch010 candidate history was rewritten")
    require(all(row.get("beneficiary_confidence") is None for row in beneficiaries["relationships"]), "Batch010 beneficiary history was rewritten")

    coverage = evaluation.get("current_observed_coverage")
    require(isinstance(coverage, dict), "evaluation coverage missing")
    require(coverage.get("required_functional_cases") == 10, "evaluation functional-case coverage drifted")
    require(coverage.get("real_outcome_records") == 2, "evaluation real-outcome count drifted")
    require(coverage.get("ordinary_replay_admitted_cases") == 0, "evaluation falsely admits ordinary replay cases")
    require(coverage.get("canonical_constraints_available_for_evaluation") == 0, "evaluation falsely has canonical constraints")
    require(coverage.get("qualified_beneficiary_relationships_available_for_evaluation") == 0, "evaluation falsely has qualified beneficiaries")
    require(coverage.get("shadow_no_lookahead") == "PASS", "evaluation shadow no-lookahead drifted")
    require(coverage.get("shadow_determinism") == "PASS", "evaluation shadow determinism drifted")
    require(matrix13.get("functional_case_coverage_count") == 10, "Batch013 case matrix drifted")
    require(master12.get("readiness", {}).get("REAL_OUTCOME_RECORDS", {}).get("count") == 2, "underlying real-outcome count drifted")

    threshold = evaluation.get("acceptance_sufficiency_threshold")
    require(isinstance(threshold, dict) and threshold.get("status") == "NOT_AUTHORIZED_NOT_INVENTED", "evaluation acceptance threshold was fabricated")
    require(evaluation.get("readiness", {}).get("evaluation_protocol_defined") == "YES", "evaluation protocol not defined")
    require(evaluation.get("readiness", {}).get("shadow_evaluation_executable") == "YES_BOUNDED", "shadow evaluation execution readiness drifted")
    require(evaluation.get("readiness", {}).get("acceptance_grade_evaluation_ready") == "NO", "evaluation falsely acceptance-ready")
    require(set(evaluation.get("blockers", [])) == {EVAL1, EVAL2, EVAL3}, "evaluation blocker set drifted")

    dims = gate.get("dimensions")
    require(isinstance(dims, dict), "Batch015 gate dimensions missing")
    require(dims["CONFIDENCE_READY"].get("status") == "READY_WITH_NONBLOCKING_GAPS", "Batch015 confidence gate did not advance correctly")
    require(dims["EVALUATION_READY"].get("status") == "BLOCKED", "Batch015 evaluation gate falsely ready")
    require(dims["IMPLEMENTATION_ADMITTED"].get("status") == "BLOCKED", "Batch015 implementation gate falsely ready")
    require(dims["PROVENANCE_READY"].get("status") == "BLOCKED", "Batch015 provenance gate falsely ready")
    require(dims["REPLAY_READY"].get("status") == "BLOCKED", "Batch015 replay gate falsely ready")
    require(set(gate.get("closed_batch014_blockers", [])) == {CONF1, CONF2}, "Batch015 closed confidence blocker set drifted")
    require(gate.get("overall_status") == "BLOCKED", "Batch015 overall gate falsely ready")
    require(gate.get("full_constraint_run_allowed") is False, "Batch015 full run unexpectedly allowed")
    require(gate.get("first_serious_constraint_run") == "BLOCKED", "Batch015 serious run unexpectedly allowed")

    closed = {row.get("blocker_id") for row in blockers.get("closed_items", [])}
    require(closed == {CONF1, CONF2}, "Batch015 closed blocker register drifted")
    active = {row.get("blocker_id") for row in blockers.get("blocking_items", [])}
    require(CONF1 not in active and CONF2 not in active, "closed confidence blockers remain active")
    require({EVAL1, EVAL2, EVAL3, RAW, ADMISSION} <= active, "required active blockers missing")
    require(blockers.get("repo_executable_blockers") == [EVAL1], "repo-executable blocker set drifted")
    require(blockers.get("next_repo_executable_lane") == "FIRST-SLICE-REAL-OUTCOME-COVERAGE-EXPANSION", "next repo lane drifted")

    readiness = master.get("readiness")
    require(isinstance(readiness, dict), "Batch015 master readiness missing")
    require(readiness.get("TYPED_CONFIDENCE_TRANSPORT_READY", {}).get("status") == "YES", "master lost typed-confidence readiness")
    require(readiness.get("CONFIDENCE_READY", {}).get("status") == "YES_WITH_EXPLICIT_UNKNOWNS", "master confidence status drifted")
    require(readiness.get("EVALUATION_PROTOCOL_READY", {}).get("status") == "YES_SHADOW_BOUNDED", "master evaluation protocol status drifted")
    require(readiness.get("OUTCOME_EVALUATION_READY", {}).get("status") == "NO_ACCEPTANCE", "master falsely evaluation-ready")
    require(readiness.get("FULL_CONSTRAINT_RUN_READY", {}).get("status") == "NO", "master falsely full-run ready")
    require(master.get("first_serious_constraint_run") == "BLOCKED", "master falsely serious-run ready")
    require(master.get("next_repo_executable_lane") == "FIRST-SLICE-REAL-OUTCOME-COVERAGE-EXPANSION", "master next repo lane drifted")

    print("CONSTRAINT_FIRST_SLICE_TYPED_CONFIDENCE_EVALUATION_VALIDATION=PASS")
    print("FORMATION_CONFIDENCE_ROWS=3")
    print("BENEFICIARY_CONFIDENCE_ROWS=4")
    print("NUMERIC_CONFIDENCE_INVENTED=NO")
    print("CONFIDENCE_READY=READY_WITH_NONBLOCKING_GAPS")
    print("EVALUATION_PROTOCOL_READY=YES_SHADOW_BOUNDED")
    print("EVALUATION_READY=BLOCKED")
    print("FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED")
    print("NEXT_REPO_EXECUTABLE_LANE=FIRST-SLICE-REAL-OUTCOME-COVERAGE-EXPANSION")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValidationFailure, json.JSONDecodeError) as exc:
        print("CONSTRAINT_FIRST_SLICE_TYPED_CONFIDENCE_EVALUATION_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
