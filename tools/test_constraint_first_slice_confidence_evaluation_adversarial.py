#!/usr/bin/env python3
"""Hostile mutation matrix for Batch015 confidence/evaluation closure."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools/validate_constraint_first_slice_confidence_evaluation.py"

CONF = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_AI_DATA_CENTER_POWER_INFRASTRUCTURE_TYPED_CONFIDENCE_OVERLAY_V001_20260925.json"
EVAL = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_AI_DATA_CENTER_POWER_INFRASTRUCTURE_EVALUATION_PROTOCOL_V001_20260925.json"
GATE = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json"
BLOCKERS = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BLOCKER_REGISTER_V001_20260925.json"
MASTER = "docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_MASTER_STATUS_V001_20260925.json"


def make_sandbox() -> Path:
    temp = Path(tempfile.mkdtemp(prefix="hydra-confidence-hostile-"))
    shutil.copytree(ROOT / "docs/constraint", temp / "docs/constraint", dirs_exist_ok=True)
    return temp


def mutate(root: Path, relative: str, fn: Callable[[dict], None]) -> None:
    path = root / relative
    doc = json.loads(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def run(root: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["HYDRA_REPO_ROOT"] = str(root)
    return subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, env=env, text=True, capture_output=True, check=False)


def expect_failure(name: str, fn: Callable[[Path], None], fragment: str) -> None:
    root = make_sandbox()
    try:
        baseline = run(root)
        if baseline.returncode != 0:
            raise AssertionError(f"{name}: baseline failed\n{baseline.stdout}\n{baseline.stderr}")
        fn(root)
        result = run(root)
        if result.returncode == 0:
            raise AssertionError(f"{name}: hostile mutation incorrectly passed")
        output = result.stdout + result.stderr
        if fragment not in output:
            raise AssertionError(f"{name}: expected {fragment!r}\n{output}")
        print(f"PASS :: {name} :: {fragment}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def case_numeric_formation_confidence(root: Path) -> None:
    mutate(root, CONF, lambda doc: doc["candidate_confidence"][0].__setitem__("value", 0.91))


def case_numeric_beneficiary_confidence(root: Path) -> None:
    mutate(root, CONF, lambda doc: doc["beneficiary_confidence"][0].__setitem__("value", 0.87))


def case_candidate_row_removed(root: Path) -> None:
    mutate(root, CONF, lambda doc: doc["candidate_confidence"].pop())


def case_beneficiary_state_promoted(root: Path) -> None:
    def change(doc: dict) -> None:
        doc["beneficiary_confidence"][0]["measurement_state"] = "MEASURED_HIGH"
        doc["beneficiary_confidence"][0]["qualification_state"] = "QUALIFIED"
    mutate(root, CONF, change)


def case_threshold_invented(root: Path) -> None:
    def change(doc: dict) -> None:
        doc["acceptance_sufficiency_threshold"] = {"status":"AUTHORIZED","minimum_real_outcomes":2}
    mutate(root, EVAL, change)


def case_evaluation_ready(root: Path) -> None:
    mutate(root, GATE, lambda doc: doc["dimensions"]["EVALUATION_READY"].__setitem__("status", "READY"))


def case_confidence_blocked_again(root: Path) -> None:
    mutate(root, GATE, lambda doc: doc["dimensions"]["CONFIDENCE_READY"].__setitem__("status", "BLOCKED"))


def case_closed_confidence_blocker_reactivated(root: Path) -> None:
    def change(doc: dict) -> None:
        doc["blocking_items"].append({
            "blocker_id":"ACCEPT-014-CONF-001-TYPED-FORMATION-CONFIDENCE-NOT-POPULATED",
            "dimension":"CONFIDENCE_READY",
            "repo_executable":True
        })
    mutate(root, BLOCKERS, change)


def case_master_full_ready(root: Path) -> None:
    def change(doc: dict) -> None:
        doc["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"] = "YES"
        doc["first_serious_constraint_run"] = "READY"
    mutate(root, MASTER, change)


def main() -> int:
    cases = [
        ("numeric_formation_confidence", case_numeric_formation_confidence, "formation confidence numeric value was fabricated"),
        ("numeric_beneficiary_confidence", case_numeric_beneficiary_confidence, "beneficiary confidence numeric value was fabricated"),
        ("candidate_row_removed", case_candidate_row_removed, "typed formation-confidence row count drifted"),
        ("beneficiary_state_promoted", case_beneficiary_state_promoted, "beneficiary confidence state drifted"),
        ("threshold_invented", case_threshold_invented, "evaluation acceptance threshold was fabricated"),
        ("evaluation_ready", case_evaluation_ready, "Batch015 evaluation gate falsely ready"),
        ("confidence_blocked_again", case_confidence_blocked_again, "Batch015 confidence gate did not advance correctly"),
        ("closed_confidence_blocker_reactivated", case_closed_confidence_blocker_reactivated, "closed confidence blockers remain active"),
        ("master_full_ready", case_master_full_ready, "master falsely full-run ready"),
    ]
    for name, fn, fragment in cases:
        expect_failure(name, fn, fragment)

    print("CONSTRAINT_FIRST_SLICE_TYPED_CONFIDENCE_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
