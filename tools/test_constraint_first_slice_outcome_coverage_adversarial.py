#!/usr/bin/env python3
"""Hostile mutation matrix for Batch016 real-outcome coverage closure."""

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
VALIDATOR = ROOT / "tools/validate_constraint_first_slice_outcome_coverage.py"

OUTCOMES = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_OUTCOME_RECORDS_SUPPLEMENT_V001_20260925.json"
COVERAGE = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_REAL_OUTCOME_COVERAGE_MATRIX_V001_20260925.json"
EVAL = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_EVALUATION_PROTOCOL_V001_20260925.json"
GATE = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json"
BLOCKERS = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BLOCKER_REGISTER_V001_20260925.json"
MASTER = "docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH016_MASTER_STATUS_V001_20260925.json"


def make_sandbox() -> Path:
    temp = Path(tempfile.mkdtemp(prefix="hydra-outcome-hostile-"))
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


def case_substitution_generalized(root: Path) -> None:
    mutate(root, OUTCOMES, lambda doc: doc["records"][0].__setitem__("outcome_scope", "ALL_LOUDOUN_DATA_CENTERS"))


def case_constraint_resolution_fabricated(root: Path) -> None:
    mutate(root, OUTCOMES, lambda doc: doc["records"][0].__setitem__("outcome_label", "CONSTRAINT_RESOLVED"))


def case_eaton_causation_overstated(root: Path) -> None:
    mutate(root, OUTCOMES, lambda doc: doc["records"][1].__setitem__("constraint_attribution_status", "DIRECT_EXCLUSIVE_CAUSATION_PROVEN"))


def case_gev_ordinary_replay(root: Path) -> None:
    mutate(root, OUTCOMES, lambda doc: doc["records"][2].__setitem__("ordinary_replay_eligible", True))


def case_dimension_removed(root: Path) -> None:
    mutate(root, COVERAGE, lambda doc: doc["evaluation_dimensions"].pop())


def case_numeric_threshold_invented(root: Path) -> None:
    mutate(root, COVERAGE, lambda doc: doc.__setitem__("numeric_acceptance_sample_threshold_invented", True))


def case_eval1_reactivated(root: Path) -> None:
    def change(doc: dict) -> None:
        doc["blocking_items"].append({"blocker_id":"ACCEPT-014-EVAL-001-REAL-OUTCOME-COVERAGE-THIN","dimension":"EVALUATION_READY","repo_executable":True})
    mutate(root, BLOCKERS, change)


def case_repo_blocker_reappears(root: Path) -> None:
    mutate(root, BLOCKERS, lambda doc: doc.__setitem__("repo_executable_blockers", ["FAKE-REPO-BLOCKER"]))


def case_evaluation_ready(root: Path) -> None:
    mutate(root, GATE, lambda doc: doc["dimensions"]["EVALUATION_READY"].__setitem__("status", "READY"))


def case_master_full_ready(root: Path) -> None:
    def change(doc: dict) -> None:
        doc["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"] = "YES"
        doc["first_serious_constraint_run"] = "READY"
    mutate(root, MASTER, change)


def main() -> int:
    cases = [
        ("substitution_generalized", case_substitution_generalized, "Loudoun substitution scope was generalized"),
        ("constraint_resolution_fabricated", case_constraint_resolution_fabricated, "fabricated constraint resolution"),
        ("eaton_causation_overstated", case_eaton_causation_overstated, "beneficiary capture causation was overstated"),
        ("gev_ordinary_replay", case_gev_ordinary_replay, "outcome unexpectedly ordinary-replay eligible"),
        ("dimension_removed", case_dimension_removed, "core evaluation-dimension coverage drifted"),
        ("numeric_threshold_invented", case_numeric_threshold_invented, "invented numeric acceptance threshold"),
        ("eval1_reactivated", case_eval1_reactivated, "thin-outcome blocker remains active"),
        ("repo_blocker_reappears", case_repo_blocker_reappears, "still reports repo-executable first-slice blockers"),
        ("evaluation_ready", case_evaluation_ready, "evaluation gate falsely ready"),
        ("master_full_ready", case_master_full_ready, "master falsely full-run ready"),
    ]
    for name, fn, fragment in cases:
        expect_failure(name, fn, fragment)

    print("CONSTRAINT_FIRST_SLICE_REAL_OUTCOME_COVERAGE_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
