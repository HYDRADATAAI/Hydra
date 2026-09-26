#!/usr/bin/env python3
"""Hostile mutation matrix for the strict first-slice acceptance gate."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools/validate_constraint_first_slice_acceptance_gate.py"

GATE_REL = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json"
BLOCKERS_REL = "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BLOCKER_REGISTER_V001_20260925.json"
MASTER_REL = "docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_MASTER_STATUS_V001_20260925.json"


def make_sandbox() -> Path:
    temp = ROOT / f".tmp-hydra-acceptance-hostile-{uuid.uuid4().hex}"
    temp.mkdir()
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
    return subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


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


def gate_status(dimension: str, status: str):
    def case(root: Path) -> None:
        mutate(root, GATE_REL, lambda doc: doc["dimensions"][dimension].__setitem__("status", status))
    return case


def case_overall_ready(root: Path) -> None:
    def change(doc: dict) -> None:
        doc["overall_status"] = "READY"
        doc["full_constraint_run_allowed"] = True
        doc["first_serious_constraint_run"] = "READY"
    mutate(root, GATE_REL, change)


def case_blocker_removed(root: Path) -> None:
    def change(doc: dict) -> None:
        doc["blocking_items"] = [
            row for row in doc["blocking_items"]
            if row["blocker_id"] != "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"
        ]
    mutate(root, BLOCKERS_REL, change)


def case_master_ready(root: Path) -> None:
    def change(doc: dict) -> None:
        doc["acceptance_gate"]["status"] = "READY"
        doc["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"] = "YES"
        doc["first_serious_constraint_run"] = "READY"
    mutate(root, MASTER_REL, change)


def main() -> int:
    cases = [
        ("implementation_ready", gate_status("IMPLEMENTATION_ADMITTED", "READY"), "IMPLEMENTATION_ADMITTED status drifted"),
        ("provenance_ready", gate_status("PROVENANCE_READY", "READY"), "PROVENANCE_READY status drifted"),
        ("confidence_ready", gate_status("CONFIDENCE_READY", "READY"), "CONFIDENCE_READY status drifted"),
        ("historical_asof_ready", gate_status("HISTORICAL_AS_OF_READY", "READY"), "HISTORICAL_AS_OF_READY status drifted"),
        ("no_lookahead_overstated", gate_status("NO_LOOKAHEAD_READY", "READY"), "NO_LOOKAHEAD_READY status drifted"),
        ("outcome_labels_overstated", gate_status("OUTCOME_LABELS_READY", "READY"), "OUTCOME_LABELS_READY status drifted"),
        ("replay_ready", gate_status("REPLAY_READY", "READY"), "REPLAY_READY status drifted"),
        ("evaluation_ready", gate_status("EVALUATION_READY", "READY"), "EVALUATION_READY status drifted"),
        ("overall_ready", case_overall_ready, "overall acceptance gate falsely not BLOCKED"),
        ("raw_blocker_removed", case_blocker_removed, "blocker register missing gate blockers"),
        ("master_ready", case_master_ready, "Batch014 master acceptance gate drifted"),
    ]
    for name, fn, fragment in cases:
        expect_failure(name, fn, fragment)

    print("CONSTRAINT_FIRST_SLICE_STRICT_ACCEPTANCE_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
