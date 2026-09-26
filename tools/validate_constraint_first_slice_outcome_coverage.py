#!/usr/bin/env python3
"""Validate Batch016 real-outcome coverage expansion without authority escalation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("HYDRA_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
SLICE = ROOT / "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
ARCH = ROOT / "docs/constraint/architecture"

SOURCES = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_OUTCOME_SOURCE_REGISTRY_EXTENSION_V001_20260925.json"
OUTCOMES = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_OUTCOME_RECORDS_SUPPLEMENT_V001_20260925.json"
COVERAGE = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_REAL_OUTCOME_COVERAGE_MATRIX_V001_20260925.json"
EVAL = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_EVALUATION_PROTOCOL_V001_20260925.json"
GATE = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json"
BLOCKERS = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BLOCKER_REGISTER_V001_20260925.json"
MASTER = ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_MASTER_STATUS_V001_20260925.json"
BEN10 = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BENEFICIARY_EVALUATIONS_V001_20260925.json"

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
    sources = load(SOURCES)
    outcomes = load(OUTCOMES)
    coverage = load(COVERAGE)
    evaluation = load(EVAL)
    gate = load(GATE)
    blockers = load(BLOCKERS)
    master = load(MASTER)
    ben10 = load(BEN10)

    source_rows = sources.get("sources")
    require(isinstance(source_rows, list) and len(source_rows) == 3, "Batch016 outcome source count drifted")
    source_ids = {row.get("source_id") for row in source_rows}
    require(len(source_ids) == 3 and None not in source_ids, "Batch016 outcome source IDs invalid")
    for row in source_rows:
        require(row.get("acquired_at") == row.get("available_at"), "Batch016 conservative availability drifted")
        require(row.get("historical_backdating_authorized") is False, "Batch016 historical backdating unexpectedly authorized")
        require(row.get("ordinary_raw_lineage_eligible") is False, "Batch016 source unexpectedly raw-lineage eligible")
    require(sources.get("runtime_live_source_authority_used") is False, "Batch016 falsely uses runtime live-source authority")
    require(sources.get("source_content_persisted") is False, "Batch016 falsely claims source content persistence")

    records = outcomes.get("records")
    require(isinstance(records, list) and len(records) == 3, "Batch016 outcome record count drifted")
    by_id = {row.get("outcome_id"): row for row in records}
    expected_ids = {
        "OUT-AIDC-LOUDOUN-ONSITE-GAS-SUBSTITUTION-SUCCEEDED-001",
        "OUT-AIDC-EATON-DATACENTER-ORDER-CAPTURE-Q1-2026-001",
        "OUT-AIDC-GEV-DATACENTER-ORDER-CAPTURE-H1-2026-001",
    }
    require(set(by_id) == expected_ids, "Batch016 outcome ID set drifted")
    require(all(row.get("source_id") in source_ids for row in records), "Batch016 outcome source lineage unresolved")
    require(all(row.get("ordinary_replay_eligible") is False for row in records), "Batch016 outcome unexpectedly ordinary-replay eligible")
    require(all(row.get("outcome_label") != "CONSTRAINT_RESOLVED" for row in records), "Batch016 fabricated constraint resolution")

    substitution = by_id["OUT-AIDC-LOUDOUN-ONSITE-GAS-SUBSTITUTION-SUCCEEDED-001"]
    require(substitution.get("outcome_label") == "SUBSTITUTION_SUCCEEDED", "Loudoun substitution outcome label drifted")
    require(substitution.get("related_relief_path_id") == "REL-AIDC-002", "Loudoun substitution relief path drifted")
    require(substitution.get("outcome_scope") == "ONE_UNNAMED_LOUDOUN_DATA_CENTER", "Loudoun substitution scope was generalized")
    require(substitution.get("entity_name") == "UNNAMED_LOUDOUN_DATA_CENTER", "Loudoun source was falsely resolved to a named entity")

    eaton = by_id["OUT-AIDC-EATON-DATACENTER-ORDER-CAPTURE-Q1-2026-001"]
    gev = by_id["OUT-AIDC-GEV-DATACENTER-ORDER-CAPTURE-H1-2026-001"]
    for row in (eaton, gev):
        require(row.get("outcome_label") == "BENEFICIARY_CAPTURE_CONFIRMED", "beneficiary capture outcome label drifted")
        require(row.get("constraint_attribution_status") == "BOUNDED_NOT_EXCLUSIVE_CAUSATION", "beneficiary capture causation was overstated")
        require(row.get("beneficiary_relationship_id"), "beneficiary capture relationship missing")

    # Outcome evidence does not retroactively qualify the Batch010 relationships.
    require(ben10.get("qualified_relationship_count") == 0, "Batch010 beneficiary history was retroactively qualified")
    for row in ben10.get("relationships", []):
        require(row.get("qualification_state") == "INELIGIBLE_TO_EVALUATE", "Batch010 beneficiary qualification was rewritten")
        require(row.get("eligibility_state") == "BLOCKED", "Batch010 beneficiary eligibility was rewritten")

    counts = outcomes.get("counts")
    require(isinstance(counts, dict), "Batch016 outcome counts missing")
    require(counts.get("outcomes_added_this_batch") == 3, "Batch016 added-outcome count drifted")
    require(counts.get("current_slice_real_outcome_count") == 5, "Batch016 total real-outcome count drifted")
    require(counts.get("substitution_succeeded_total") == 1, "Batch016 substitution outcome count drifted")
    require(counts.get("beneficiary_capture_confirmed_total") == 2, "Batch016 beneficiary-capture count drifted")
    require(counts.get("constraint_resolutions_total") == 0, "Batch016 falsely records constraint resolution")

    dims = coverage.get("evaluation_dimensions")
    require(isinstance(dims, list) and len(dims) == 3, "Batch016 core evaluation-dimension coverage drifted")
    dim_names = {row.get("dimension") for row in dims}
    require(dim_names == {"CONSTRAINT_OUTCOME_MATCH", "RELIEF_OR_INVALIDATOR_OUTCOME", "BENEFICIARY_CAPTURE_OUTCOME"}, "Batch016 evaluation dimension set drifted")
    require(all(row.get("status") == "COVERED_REAL_PRIMARY_BOUNDED" for row in dims), "Batch016 core evaluation dimension lost bounded coverage")
    require(coverage.get("core_evaluation_dimensions_covered") == 3, "Batch016 covered-dimension count drifted")
    require(coverage.get("core_evaluation_dimensions_required") == 3, "Batch016 required-dimension count drifted")
    require(coverage.get("numeric_acceptance_sample_threshold_invented") is False, "Batch016 invented numeric acceptance threshold")
    require(coverage.get("coverage_status") == "CORE_REAL_OUTCOME_DIMENSIONS_COVERED", "Batch016 outcome coverage status drifted")

    observed = evaluation.get("current_observed_coverage")
    require(isinstance(observed, dict), "Batch016 evaluation observed coverage missing")
    require(observed.get("real_outcome_records") == 5, "Batch016 evaluation real-outcome count drifted")
    require(observed.get("real_outcome_labels") == 4, "Batch016 evaluation label count drifted")
    require(observed.get("core_real_outcome_dimensions_covered") == 3, "Batch016 evaluation core coverage drifted")
    require(observed.get("ordinary_replay_admitted_cases") == 0, "Batch016 evaluation falsely admits ordinary replay")
    threshold = evaluation.get("acceptance_sufficiency_threshold")
    require(isinstance(threshold, dict) and threshold.get("status") == "NOT_AUTHORIZED_NOT_INVENTED", "Batch016 fabricated evaluation sufficiency threshold")
    require(evaluation.get("closed_blockers") == [EVAL1], "Batch016 evaluation closed-blocker set drifted")
    require(set(evaluation.get("blockers", [])) == {EVAL2, EVAL3}, "Batch016 evaluation blocker set drifted")
    require(evaluation.get("readiness", {}).get("acceptance_grade_evaluation_ready") == "NO", "Batch016 falsely acceptance-grade evaluation ready")

    gate_dims = gate.get("dimensions")
    require(isinstance(gate_dims, dict), "Batch016 gate dimensions missing")
    require(gate_dims["EVALUATION_READY"].get("status") == "BLOCKED", "Batch016 evaluation gate falsely ready")
    require(set(gate_dims["EVALUATION_READY"].get("blockers", [])) == {EVAL2, EVAL3}, "Batch016 evaluation gate blocker set drifted")
    require(gate_dims["IMPLEMENTATION_ADMITTED"].get("status") == "BLOCKED", "Batch016 implementation gate falsely ready")
    require(gate_dims["PROVENANCE_READY"].get("status") == "BLOCKED", "Batch016 provenance gate falsely ready")
    require(gate_dims["REPLAY_READY"].get("status") == "BLOCKED", "Batch016 replay gate falsely ready")
    require(EVAL1 in set(gate.get("closed_batch014_blockers", [])), "Batch016 did not close thin-outcome blocker")
    require(gate.get("overall_status") == "BLOCKED", "Batch016 overall gate falsely ready")
    require(gate.get("full_constraint_run_allowed") is False, "Batch016 full run unexpectedly allowed")

    closed = {row.get("blocker_id") for row in blockers.get("closed_items", [])}
    active = {row.get("blocker_id") for row in blockers.get("blocking_items", [])}
    require(EVAL1 in closed, "Batch016 blocker register did not close thin-outcome blocker")
    require(EVAL1 not in active, "Batch016 thin-outcome blocker remains active")
    require({EVAL2, EVAL3, RAW, ADMISSION} <= active, "Batch016 required external blockers missing")
    require(blockers.get("repo_executable_blockers") == [], "Batch016 still reports repo-executable first-slice blockers")
    expected_next = "NONE_FIRST_SLICE_ACCEPTANCE_REQUIRES_PRIVATE_RAW_MATERIALIZATION_AND_NATIVE_ADMISSION"
    require(blockers.get("next_repo_executable_lane") == expected_next, "Batch016 blocker-register next lane drifted")

    readiness = master.get("readiness")
    require(isinstance(readiness, dict), "Batch016 master readiness missing")
    outcome_ready = readiness.get("REAL_OUTCOME_CORE_DIMENSION_COVERAGE", {})
    require(outcome_ready.get("status") == "YES_BOUNDED", "Batch016 master lost real-outcome core coverage")
    require(outcome_ready.get("records") == 5 and outcome_ready.get("dimensions") == 3, "Batch016 master outcome metrics drifted")
    require(readiness.get("OUTCOME_EVALUATION_READY", {}).get("status") == "NO_ACCEPTANCE_EXTERNAL_GATES_ONLY", "Batch016 master evaluation status drifted")
    require(readiness.get("FULL_CONSTRAINT_RUN_READY", {}).get("status") == "NO", "Batch016 master falsely full-run ready")
    require(master.get("first_serious_constraint_run") == "BLOCKED", "Batch016 master falsely serious-run ready")
    require(master.get("repo_executable_blockers") == [], "Batch016 master still reports repo-executable blockers")
    require(master.get("next_repo_executable_lane") == expected_next, "Batch016 master next lane drifted")

    print("CONSTRAINT_FIRST_SLICE_REAL_OUTCOME_COVERAGE_VALIDATION=PASS")
    print("REAL_OUTCOME_RECORDS=5")
    print("REAL_OUTCOME_LABELS=4")
    print("CORE_EVALUATION_OUTCOME_DIMENSIONS=3/3")
    print("SUBSTITUTION_SUCCEEDED_OUTCOMES=1")
    print("BENEFICIARY_CAPTURE_CONFIRMED_OUTCOMES=2")
    print("CONSTRAINT_RESOLUTION_OUTCOMES=0")
    print("ACCEPT_014_EVAL_001=CLOSED")
    print("REPO_EXECUTABLE_BLOCKERS=0")
    print("EVALUATION_READY=BLOCKED_EXTERNAL_GATES_ONLY")
    print("FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED")
    print("NEXT_REPO_EXECUTABLE_LANE=NONE_FIRST_SLICE_ACCEPTANCE_REQUIRES_PRIVATE_RAW_MATERIALIZATION_AND_NATIVE_ADMISSION")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValidationFailure, json.JSONDecodeError) as exc:
        print("CONSTRAINT_FIRST_SLICE_REAL_OUTCOME_COVERAGE_VALIDATION=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
