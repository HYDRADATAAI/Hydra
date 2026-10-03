#!/usr/bin/env python3
"""Adversarial mutation checks for the Constraint first-slice integration guard."""

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
VALIDATOR = ROOT / "tools/validate_constraint_first_slice_successor.py"
VALIDATION_DIR = ROOT / "docs/constraint/validation"

MANIFEST_NAMES = [
    f"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH{n:03d}_ARTIFACT_MANIFEST_V001_20260925.json"
    for n in range(3, 10)
] + [
    "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_ARTIFACT_MANIFEST_V002_20260925.json"
]


def copy_file(relative: str, destination_root: Path) -> None:
    source = ROOT / relative
    target = destination_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def make_sandbox() -> Path:
    temp = ROOT / f".tmp-hydra-constraint-integration-{uuid.uuid4().hex}"
    temp.mkdir()
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
    found = False
    for entry in manifest["artifacts"]:
        if entry["path"] == relative:
            entry["git_blob_sha"] = git_blob_sha(root, relative)
            found = True
            break
    if not found:
        raise AssertionError(f"manifest {manifest_name} does not contain {relative}")
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


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
                f"{name}: baseline validator failed before mutation\n"
                f"STDOUT:\n{baseline.stdout}\nSTDERR:\n{baseline.stderr}"
            )

        mutator(sandbox)
        result = run_validator(sandbox)
        if result.returncode == 0:
            raise AssertionError(f"{name}: hostile mutation incorrectly passed")
        output = result.stdout + result.stderr
        if expected_fragment not in output:
            raise AssertionError(
                f"{name}: expected failure fragment {expected_fragment!r} not found\n"
                f"OUTPUT:\n{output}"
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

    def mutate(doc: dict) -> None:
        doc["records"][0]["conservative_available_at"] = "2026-09-25T23:51:59.000000Z"

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH007_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def case_fiber_silently_closed(root: Path) -> None:
    relative = (
        "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH006_AI_DATA_CENTER_POWER_INFRASTRUCTURE_"
        "SOURCE_GAP_STATUS_V001_20260925.json"
    )

    def mutate(doc: dict) -> None:
        doc["results"]["FIBER_CONNECTIVITY_CAPACITY_FIELD"] = "POPULATED_UNPROVEN"
        doc["results"]["SOURCE_GAP_FIELDS_REMAINING"] = 0

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH006_ARTIFACT_MANIFEST_V001_20260925.json",
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

    def mutate(doc: dict) -> None:
        doc["results"]["NINE_REAL_SOURCE_ARTIFACTS_MATERIALIZED"] = "YES"

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH008_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def case_source_disappears(root: Path) -> None:
    relative = (
        "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH007_AI_DATA_CENTER_POWER_INFRASTRUCTURE_"
        "CONSERVATIVE_AVAILABILITY_OVERLAY_V001_20260925.json"
    )

    def mutate(doc: dict) -> None:
        doc["records"].pop()

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH007_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def case_current_fiber_reopened(root: Path) -> None:
    relative = (
        "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_AI_DATA_CENTER_POWER_INFRASTRUCTURE_"
        "SOURCE_GAP_STATUS_V001_20260925.json"
    )

    def mutate(doc: dict) -> None:
        doc["results"]["FIBER_CONNECTIVITY_CAPACITY_FIELD"] = "SOURCE_GAP"
        doc["results"]["ORIGINAL_FROZEN_SOURCE_GAP_FIELDS_REMAINING"] = 1

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH009_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def case_candidate_mints_canonical(root: Path) -> None:
    relative = (
        "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_"
        "T5_CANDIDATE_PROPOSALS_V001_20260925.json"
    )

    def mutate(doc: dict) -> None:
        doc["candidates"][0]["canonical_constraint_id"] = "K-UNAUTHORIZED"

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_ARTIFACT_MANIFEST_V002_20260925.json",
    )


def case_beneficiary_falsely_qualified(root: Path) -> None:
    relative = (
        "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_"
        "BENEFICIARY_EVALUATIONS_V001_20260925.json"
    )

    def mutate(doc: dict) -> None:
        doc["relationships"][0]["qualification_state"] = "QUALIFIED"
        doc["qualified_relationship_count"] = 1

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_ARTIFACT_MANIFEST_V002_20260925.json",
    )


def case_master_falsely_ready(root: Path) -> None:
    relative = (
        "docs/constraint/architecture/"
        "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH008_MASTER_STATUS_V001_20260925.json"
    )

    def mutate(doc: dict) -> None:
        doc["readiness"]["FULL_CONSTRAINT_RUN_READY"]["status"] = "YES"
        doc["first_serious_constraint_run"] = "PASS"

    mutate_json(
        root,
        relative,
        mutate,
        manifest_name="HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH008_ARTIFACT_MANIFEST_V001_20260925.json",
    )


def main() -> int:
    cases = [
        ("backdated_availability", case_backdated_availability, "conservative availability drift"),
        ("fiber_silently_closed", case_fiber_silently_closed, "fiber source gap was silently closed"),
        ("admission_falsely_granted", case_admission_falsely_granted, "native implementation unexpectedly admitted"),
        ("raw_materialization_falsely_claimed", case_raw_materialization_falsely_claimed, "real raw sources falsely marked materialized"),
        ("source_disappears", case_source_disappears, "availability source set differs from registry"),
        ("current_fiber_reopened", case_current_fiber_reopened, "Batch009 fiber closure drifted"),
        ("candidate_mints_canonical", case_candidate_mints_canonical, "Batch010 minted canonical constraint ID"),
        ("beneficiary_falsely_qualified", case_beneficiary_falsely_qualified, "Batch010 fabricated qualified beneficiary"),
        ("master_falsely_ready", case_master_falsely_ready, "master falsely claims full-run readiness"),
    ]
    for name, mutator, expected in cases:
        expect_failure(name, mutator, expected)

    print("CONSTRAINT_FIRST_SLICE_HOSTILE_MUTATION_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
