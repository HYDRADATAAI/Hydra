#!/usr/bin/env python3
"""Strict acceptance gate for the current HYDRA Constraint first slice."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("HYDRA_REPO_ROOT", Path(__file__).resolve().parents[1])).resolve()
SLICE = ROOT / "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
VALIDATION = ROOT / "docs/constraint/validation"
ARCH = ROOT / "docs/constraint/architecture"

GATE = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json"
BLOCKERS = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BLOCKER_REGISTER_V001_20260925.json"
MASTER14 = ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_MASTER_STATUS_V001_20260925.json"

ADMISSION = VALIDATION / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH002_NATIVE_T5_T6_ADMISSION_STATUS_V001_20260925.json"
RAW8 = VALIDATION / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH008_T1_RAW_ARTIFACT_PERSISTENCE_STATUS_V001_20260925.json"
CANDIDATES10 = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_T5_CANDIDATE_PROPOSALS_V001_20260925.json"
BENEFICIARIES10 = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BENEFICIARY_EVALUATIONS_V001_20260925.json"
REPLAY11 = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SHADOW_REPLAY_PACKET_V001_20260925.json"
MASTER11 = ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH011_MASTER_STATUS_V001_20260925.json"
MASTER12 = ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_MASTER_STATUS_V001_20260925.json"
CASE_MATRIX13 = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_AI_DATA_CENTER_POWER_INFRASTRUCTURE_REQUIRED_CASE_MATRIX_V001_20260925.json"
MASTER13 = ARCH / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_MASTER_STATUS_V001_20260925.json"

ALLOWED = {"READY", "READY_WITH_NONBLOCKING_GAPS", "BLOCKED"}
EXPECTED_DIMENSIONS = {
    "AUTHORITY_CURRENT",
    "SCHEMA_COMPATIBLE",
    "IMPLEMENTATION_ADMITTED",
    "PROVENANCE_READY",
    "ENTITY_RESOLUTION_READY",
    "GRAPH_PATH_READY",
    "CONTRADICTION_READY",
    "CONFIDENCE_READY",
    "HISTORICAL_AS_OF_READY",
    "NO_LOOKAHEAD_READY",
    "OUTCOME_LABELS_READY",
    "REPLAY_READY",
    "EVALUATION_READY",
}
RAW_BLOCKER = "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"
ADMISSION_BLOCKER = "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT"
CANONICAL_BLOCKER = "CANONICAL-T5-T6-CONSTRAINT-AND-BENEFICIARY-ADMISSION-NOT-AUTHORIZED"
HASH_BLOCKER = "ORDINARY-POINT-IN-TIME-REPLAY-SOURCE-VERSION-HASHES-INCOMPLETE"


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
    gate = load(GATE)
    blockers = load(BLOCKERS)
    master14 = load(MASTER14)
    admission = load(ADMISSION)
    raw8 = load(RAW8)
    candidates10 = load(CANDIDATES10)
    beneficiaries10 = load(BENEFICIARIES10)
    replay11 = load(REPLAY11)
    master11 = load(MASTER11)
    master12 = load(MASTER12)
    matrix13 = load(CASE_MATRIX13)
    master13 = load(MASTER13)

    require(gate.get("slice_id") == "AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1", "acceptance gate slice_id drifted")
    dims = gate.get("dimensions")
    require(isinstance(dims, dict), "acceptance gate dimensions missing")
    require(set(dims) == EXPECTED_DIMENSIONS, "acceptance gate dimension set drifted")
    require(gate.get("allowed_gate_states") == ["READY", "READY_WITH_NONBLOCKING_GAPS", "BLOCKED"], "allowed gate state vocabulary drifted")
    for name, row in dims.items():
        require(isinstance(row, dict), f"{name} row invalid")
        require(row.get("status") in ALLOWED, f"{name} has invalid status")

    # Underlying facts that force blocking.
    require(admission.get("implementation_admitted") == "NO", "native implementation unexpectedly admitted")
    require(admission.get("first_serious_constraint_run") == "BLOCKED", "admission artifact falsely run-ready")
    require(raw8.get("results", {}).get("NINE_REAL_SOURCE_ARTIFACTS_MATERIALIZED") == "NO", "real nine-source raw materialization unexpectedly complete")
    require(replay11.get("ordinary_replay_eligible") is False, "shadow replay unexpectedly ordinary-eligible")
    require(replay11.get("source_version_hash_status") == "BLOCKED_RAW_SOURCE_BODY_NOT_MATERIALIZED", "shadow replay raw-hash blocker drifted")
    require(matrix13.get("ordinary_replay_admitted_case_count") == 0, "required case matrix unexpectedly ordinary replay admitted")

    # Confidence must remain blocked while candidate formation confidence is
    # absent and all beneficiary confidence values are null.
    candidate_rows = candidates10.get("candidates")
    require(isinstance(candidate_rows, list) and candidate_rows, "Batch010 candidate rows missing")
    require(all("formation_confidence" not in row for row in candidate_rows), "formation confidence unexpectedly populated")
    beneficiary_rows = beneficiaries10.get("relationships")
    require(isinstance(beneficiary_rows, list) and beneficiary_rows, "Batch010 beneficiary rows missing")
    require(all(row.get("beneficiary_confidence") is None for row in beneficiary_rows), "beneficiary confidence unexpectedly populated")
    require(beneficiaries10.get("qualified_relationship_count") == 0, "qualified beneficiary unexpectedly minted")

    # Shadow success exists but cannot become ordinary acceptance.
    r11 = master11.get("readiness", {})
    require(r11.get("SHADOW_NO_LOOKAHEAD", {}).get("status") == "PASS", "shadow no-lookahead no longer passes")
    require(r11.get("SHADOW_DETERMINISM", {}).get("status") == "PASS", "shadow determinism no longer passes")
    require(r11.get("OUTCOME_EVALUATION_READY", {}).get("status") == "THIN_NOT_ACCEPTANCE_READY", "Batch011 outcome evaluation readiness drifted")
    r12 = master12.get("readiness", {})
    require(r12.get("REAL_OUTCOME_RECORDS", {}).get("count") == 2, "real outcome count drifted")
    r13 = master13.get("readiness", {})
    require(r13.get("REQUIRED_FUNCTIONAL_CASE_MATRIX", {}).get("count") == 10, "required functional case count drifted")
    require(r13.get("POINT_IN_TIME_REPLAY_READY", {}).get("status") == "NO_ORDINARY", "Batch013 unexpectedly ordinary replay ready")
    require(r13.get("LINEAGE_COMPLETE", {}).get("status") == "NO", "Batch013 unexpectedly lineage complete")
    require(master13.get("first_serious_constraint_run") == "BLOCKED", "Batch013 unexpectedly run-ready")

    expected_statuses = {
        "AUTHORITY_CURRENT": "READY",
        "SCHEMA_COMPATIBLE": "READY_WITH_NONBLOCKING_GAPS",
        "IMPLEMENTATION_ADMITTED": "BLOCKED",
        "PROVENANCE_READY": "BLOCKED",
        "ENTITY_RESOLUTION_READY": "READY_WITH_NONBLOCKING_GAPS",
        "GRAPH_PATH_READY": "READY_WITH_NONBLOCKING_GAPS",
        "CONTRADICTION_READY": "READY_WITH_NONBLOCKING_GAPS",
        "CONFIDENCE_READY": "BLOCKED",
        "HISTORICAL_AS_OF_READY": "BLOCKED",
        "NO_LOOKAHEAD_READY": "READY_WITH_NONBLOCKING_GAPS",
        "OUTCOME_LABELS_READY": "READY_WITH_NONBLOCKING_GAPS",
        "REPLAY_READY": "BLOCKED",
        "EVALUATION_READY": "BLOCKED",
    }
    for name, expected in expected_statuses.items():
        require(dims[name].get("status") == expected, f"{name} status drifted")

    # Required blocker bindings.
    require(ADMISSION_BLOCKER in set(dims["IMPLEMENTATION_ADMITTED"].get("blockers", [])), "implementation admission blocker missing")
    require(CANONICAL_BLOCKER in set(dims["IMPLEMENTATION_ADMITTED"].get("blockers", [])), "canonical admission blocker missing")
    require(RAW_BLOCKER in set(dims["PROVENANCE_READY"].get("blockers", [])), "provenance raw blocker missing")
    require(HASH_BLOCKER in set(dims["PROVENANCE_READY"].get("blockers", [])), "provenance hash blocker missing")
    require(RAW_BLOCKER in set(dims["REPLAY_READY"].get("blockers", [])), "replay raw blocker missing")
    require(HASH_BLOCKER in set(dims["REPLAY_READY"].get("blockers", [])), "replay hash blocker missing")

    # Overall state is mechanically fail-closed.
    blocked_dimensions = sorted(name for name, row in dims.items() if row["status"] == "BLOCKED")
    require(blocked_dimensions, "no required dimension is blocked; acceptance gate assumptions changed")
    require(gate.get("overall_status") == "BLOCKED", "overall acceptance gate falsely not BLOCKED")
    require(gate.get("full_constraint_run_allowed") is False, "full constraint run unexpectedly allowed")
    require(gate.get("first_serious_constraint_run") == "BLOCKED", "first serious run unexpectedly allowed")

    # Blocker register must include every blocker named by blocked dimensions.
    register_rows = blockers.get("blocking_items")
    require(isinstance(register_rows, list) and register_rows, "blocking register empty")
    register_ids = {row.get("blocker_id") for row in register_rows}
    required_ids: set[str] = set()
    for row in dims.values():
        if row.get("status") == "BLOCKED":
            required_ids.update(row.get("blockers", []))
    require(required_ids <= register_ids, f"blocker register missing gate blockers: {sorted(required_ids - register_ids)}")
    require(blockers.get("overall_status") == "BLOCKED", "blocker register falsely not BLOCKED")

    # Master must reflect the gate rather than silently flatten it.
    require(master14.get("acceptance_gate", {}).get("status") == "BLOCKED", "Batch014 master acceptance gate drifted")
    r14 = master14.get("readiness")
    require(isinstance(r14, dict), "Batch014 readiness missing")
    require(r14.get("IMPLEMENTATION_ADMITTED", {}).get("status") == "NO", "Batch014 master falsely admits implementation")
    require(r14.get("FIRST_SLICE_RAW_ARTIFACTS_MATERIALIZED", {}).get("status") == "NO", "Batch014 master falsely materializes raw artifacts")
    require(r14.get("CONFIDENCE_READY", {}).get("status") == "NO", "Batch014 master falsely claims confidence ready")
    require(r14.get("POINT_IN_TIME_REPLAY_READY", {}).get("status") == "NO_ORDINARY", "Batch014 master falsely claims ordinary replay")
    require(r14.get("OUTCOME_EVALUATION_READY", {}).get("status") == "NO_ACCEPTANCE", "Batch014 master falsely claims evaluation ready")
    require(r14.get("FULL_CONSTRAINT_RUN_READY", {}).get("status") == "NO", "Batch014 master falsely claims full run ready")
    require(master14.get("first_serious_constraint_run") == "BLOCKED", "Batch014 master falsely allows serious run")
    require(master14.get("next_repo_executable_lane") == "FIRST-SLICE-TYPED-CONFIDENCE-AND-EVALUATION-READINESS-CLOSURE", "Batch014 next repo lane drifted")

    print("CONSTRAINT_FIRST_SLICE_STRICT_ACCEPTANCE_GATE=PASS")
    print("OVERALL_STATUS=BLOCKED")
    print(f"BLOCKED_DIMENSIONS={','.join(blocked_dimensions)}")
    print("AUTHORITY_CURRENT=READY")
    print("IMPLEMENTATION_ADMITTED=BLOCKED")
    print("PROVENANCE_READY=BLOCKED")
    print("CONFIDENCE_READY=BLOCKED")
    print("REPLAY_READY=BLOCKED")
    print("EVALUATION_READY=BLOCKED")
    print("FULL_CONSTRAINT_RUN_ALLOWED=NO")
    print("FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED")
    print("NEXT_REPO_EXECUTABLE_LANE=FIRST-SLICE-TYPED-CONFIDENCE-AND-EVALUATION-READINESS-CLOSURE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValidationFailure, json.JSONDecodeError) as exc:
        print("CONSTRAINT_FIRST_SLICE_STRICT_ACCEPTANCE_GATE=FAIL")
        print(f"ERROR={exc}")
        raise SystemExit(1)
