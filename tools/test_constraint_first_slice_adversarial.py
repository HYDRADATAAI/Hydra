#!/usr/bin/env python3
"""Adversarial mutation checks for the current Constraint first-slice guard."""

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
VALIDATOR = ROOT / "tools/validate_constraint_first_slice_successor.py"
VALIDATION_DIR = ROOT / "docs/constraint/validation"

MANIFEST_NAMES = [
    f"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH00{n}_ARTIFACT_MANIFEST_V001_20260925.json"
    for n in range(3, 10)
]


def copy_file(relative: str, destination_root: Path) -> None:
    source = ROOT / relative
    target = destination_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def make_sandbox() -> Path:
    temp = Path(tempfile.mkdtemp(prefix="hydra-constraint-hostile-"))
    shutil.copytree(ROOT / "docs/constraint", temp / "docs/constraint", dirs_exist_ok=True)

    for name in MANIFEST_NAMES:
        manifest = json.loads((VALIDATION_DIR / name).read_text(encoding="utf-8"))
        for entry in manifest["artifacts"]:
            relative = entry["path"]
            if not (temp / relative).exists():
                copy_file(relative, temp)
    return temp


def git_blob_sha(root: Path, relative: str) -> str:
    result = subprocess.run(
        ["git", "hash-object", relative],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def repin_manifest(root: Path, manifest_name: str, relative: str) -> None:
    path = root / "docs/constraint/validation" / manifest_name
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for entry in manifest["artifacts"]:
        if entry["path"] == relative:
            entry["git_blob_sha"] = git_blob_sha(root, relative)
            path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            return
    raise AssertionError(f"manifest {manifest_name} does not contain {relative}")


def mutate_json(
    root: Path,
    relative: str,
    mutator: Callable[[dict], None],
    *,
    manifest_name: str | None = None,
) -> None:
    path = root / relative
    value = json.loads(path.read_text(encoding="utf-8"))
    mutator(value)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    if manifest_name is not None:
        repin_manifest(root, manifest_name, relative)


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
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


def expect_failure(
    name: str,
    mutator: Callable[[Path], None],
    expected_fragment: str,
) -> None:
    sandbox = make_sandbox()
    try:
        baseline = run_validator(sandbox)
        if baseline.returncode != 0:
            raise AssertionError(
                f"{name}: baseline failed before mutation\n"
                f"STDOUT:\n{baseline.stdout}\nSTDERR:\n{baseline.stderr}"
            )

        mutator(sandbox)
        result = run_validator(sandbox)
        if result.returncode == 0:
            raise AssertionError(f"{name}: hostile mutation incorrectly passed")
        output = result.stdout + result.stderr
        if expected_fragment not in output:
            raise AssertionError(
                f"{name}: expected {expected_fragment!r} not found\nOUTPUT:\n{output}"
            )
        print(f"PASS :: {name} :: {expected_fragment}")
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def case_backdated_availability(root: Path) -> None:
    relative = (
        "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH007_AI_DATA_CENTER_POWER_INFRASTRUCTURE_"
        "CONSERVATIVE_AVAILABILITY_OVERLAY_V001_20260925.json"
    )
    mutate_json(
        root,
        relative,
        lambda doc: doc["records"][0].__setitem__(
            "conservative_available_at", "2026-09-25T23:51:59.000000Z"
        ),
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH007_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def case_fiber_scope_overclaim(root: Path) -> None:
    relative = (
        "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_"
        "FIBER_FIELD_OVERLAY_V001_20260925.json"
    )

    def mutate(doc: dict) -> None:
        update = doc["field_updates"][0]
        update["value"]["site_access_example"]["exact_site_capacity"] = "400_GBPS"
        update["uncertainty"] = "UNIVERSAL_SITE_CAPACITY_ASSUMED"

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def case_admission_falsely_granted(root: Path) -> None:
    relative = (
        "docs/constraint/validation/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH002_NATIVE_T5_T6_ADMISSION_STATUS_V001_20260925.json"
    )

    def mutate(doc: dict) -> None:
        doc["implementation_admitted"] = "YES"
        doc["runtime_activation_authorized"] = "YES"

    mutate_json(root, relative, mutate)


def case_raw_materialization_falsely_claimed(root: Path) -> None:
    relative = (
        "docs/constraint/validation/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH008_T1_RAW_ARTIFACT_PERSISTENCE_STATUS_V001_20260925.json"
    )
    mutate_json(
        root,
        relative,
        lambda doc: doc["results"].__setitem__("NINE_REAL_SOURCE_ARTIFACTS_MATERIALIZED", "YES"),
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH008_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def case_source_disappears(root: Path) -> None:
    relative = (
        "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH007_AI_DATA_CENTER_POWER_INFRASTRUCTURE_"
        "CONSERVATIVE_AVAILABILITY_OVERLAY_V001_20260925.json"
    )
    mutate_json(
        root,
        relative,
        lambda doc: doc["records"].pop(),
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH007_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def case_current_blocker_set_drift(root: Path) -> None:
    relative = (
        "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_"
        "SOURCE_GAP_STATUS_V001_20260925.json"
    )

    def mutate(doc: dict) -> None:
        doc["remaining_blockers"] = [
            "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"
        ]

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def case_master_falsely_ready(root: Path) -> None:
    relative = (
        "docs/constraint/architecture/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_MASTER_STATUS_V001_20260925.json"
    )

    def mutate(doc: dict) -> None:
        doc["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"] = "YES"
        doc["first_serious_constraint_run"] = "PASS"

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def main() -> int:
    cases = [
        ("backdated_availability", case_backdated_availability, "conservative availability drift"),
        ("fiber_scope_overclaim", case_fiber_scope_overclaim, "fiber exact site capacity unexpectedly quantified"),
        ("admission_falsely_granted", case_admission_falsely_granted, "native implementation unexpectedly admitted"),
        ("raw_materialization_falsely_claimed", case_raw_materialization_falsely_claimed, "real raw sources falsely marked materialized"),
        ("source_disappears", case_source_disappears, "availability source set differs from registry"),
        ("current_blocker_set_drift", case_current_blocker_set_drift, "Batch009 current remaining blockers drifted"),
        ("master_falsely_ready", case_master_falsely_ready, "current master falsely claims full-run readiness"),
    ]
    for name, mutator, expected in cases:
        expect_failure(name, mutator, expected)

    print("CONSTRAINT_FIRST_SLICE_HOSTILE_MUTATION_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
