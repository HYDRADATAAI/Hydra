#!/usr/bin/env python3
"""Hosted-only workflow alias-value regressions against the real source scanner.

All workflow mutations are inert text fixtures in temporary directories. Eight
cases call the actual scanner; two call the full public validator on repository
copies. No fixture workflow is dispatched. Production source bytes stay exact;
full-repository cases retain the original repository legacy inventory.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = "tools/validate_public_repository.py"
FIXTURE = ".github/workflows/alias-fixture.yml"
REAL_WORKFLOW = ".github/workflows/constraint-first-slice-integration.yml"
LEGACY_REFERENCE = "actions/checkout@v4"
PINNED_REFERENCE = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
BASELINE = """name: Alias parser fixture
on: workflow_dispatch
permissions:
  contents: read
jobs:
  base_job: &base_job
    runs-on: ubuntu-latest
    steps:
      - &base_step
        uses: actions/checkout@v4
      - run: echo baseline
"""
ANCHORED_LEGACY_STEP = "      - &base_step\n        uses: actions/checkout@v4\n"
LITERAL_RUN_STEPS = """      - name: Alias-like run text
        run: |
          cat <<'TEXT'
          second_job: *base_job
          - *base_step
          TEXT
      - run: echo '*base_step'
"""


@dataclass(frozen=True)
class Case:
    name: str
    mutation: str
    expected: str


CASES = (
    Case("anchored_legacy_baseline", "unchanged", "pass"),
    Case("direct_duplicate_legacy_reference", "direct_duplicate", "count_two"),
    Case("delete_original_legacy_reference", "delete_original", "count_zero"),
    Case("whole_job_alias_value", "job_alias", "alias_rejection"),
    Case("step_alias_value", "step_alias", "alias_rejection"),
    Case("quoted_job_key_alias_value", "quoted_job_alias", "alias_rejection"),
    Case("unused_pinned_step_anchor", "pinned_anchor", "pass"),
    Case("literal_stars_and_alias_like_run_text", "literal_text", "pass"),
    Case("full_repository_original_positive", "full_repository_original", "pass"),
    Case("full_repository_whole_job_alias", "full_repository_alias", "alias_rejection"),
)


CHILD_PROBE = r"""
import importlib.util
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
fixture_path = sys.argv[2]
legacy_reference = sys.argv[3]
source = root / 'tools/validate_public_repository.py'
spec = importlib.util.spec_from_file_location('r33_public_scanner_probe', source)
if spec is None or spec.loader is None:
    raise RuntimeError('unable to load copied public scanner')
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)
if scanner.ROOT != root:
    raise AssertionError('copied scanner ROOT escaped independent fixture')
# This is in-memory fixture configuration, not a source edit or new repository
# exception. A nonempty exact baseline is necessary to exercise count bypasses.
fixture_inventory = {(fixture_path, legacy_reference): 1}
scanner.LEGACY_MUTABLE_WORKFLOW_USES = dict(fixture_inventory)
errors = []
scanner.validate_workflow_action_uses(errors)
if scanner.ROOT != root or scanner.LEGACY_MUTABLE_WORKFLOW_USES != fixture_inventory:
    raise AssertionError('scanner changed fixture ROOT or legacy inventory')
if not all(type(error) is str for error in errors):
    raise AssertionError('scanner returned a malformed error list')
print(json.dumps({'errors': errors, 'legacy_inventory': [
    {'path': fixture_path, 'reference': legacy_reference, 'count': 1}
]} , sort_keys=True))
"""


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise AssertionError(detail)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def source_snapshot() -> dict[str, bytes]:
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    contents = {}
    for raw in names:
        if raw:
            name = os.fsdecode(raw)
            path = ROOT / name
            require(path.is_file() and not path.is_symlink(), f"unsupported source file: {name}")
            contents[name] = path.read_bytes()
    require(VALIDATOR in contents, "tracked validator source missing")
    return contents


def file_manifest(root: Path) -> dict[str, str]:
    result = {}
    for path in root.rglob("*"):
        require(not path.is_symlink(), "temporary scanner fixture introduced a symlink")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


def workflow_for(case: Case) -> tuple[str, list[str]]:
    require(BASELINE.count(ANCHORED_LEGACY_STEP) == 1, "baseline legacy step anchor drifted")
    require(BASELINE.count("uses: " + LEGACY_REFERENCE) == 1, "baseline legacy reference count drifted")
    aliases = {
        "job_alias": "  second_job: *base_job\n",
        "step_alias": "      - *base_step\n",
        "quoted_job_alias": '  "second_job": *base_job # alias value after quoted key\n',
    }
    if case.mutation == "unchanged":
        workflow = BASELINE
    elif case.mutation == "direct_duplicate":
        workflow = BASELINE + "      - uses: " + LEGACY_REFERENCE + "\n"
    elif case.mutation == "delete_original":
        workflow = BASELINE.replace(ANCHORED_LEGACY_STEP, "", 1)
        require("      - run: echo baseline\n" in workflow, "deletion removed the remaining valid step")
    elif case.mutation in aliases:
        workflow = BASELINE + aliases[case.mutation]
        require(workflow.removesuffix(aliases[case.mutation]) == BASELINE,
                "alias mutation changed original source nodes")
    elif case.mutation == "pinned_anchor":
        workflow = BASELINE + "      - &pinned_step\n        uses: " + PINNED_REFERENCE + "\n"
    elif case.mutation == "literal_text":
        literal_env = "env:\n  LITERAL_ALIAS: '*base_job'\n"
        workflow = BASELINE.replace("jobs:\n", literal_env + "jobs:\n", 1) + LITERAL_RUN_STEPS
        require(workflow.removesuffix(LITERAL_RUN_STEPS).replace(literal_env, "", 1) == BASELINE,
                "literal-text positive changed baseline nodes")
    else:
        raise AssertionError("unknown fixture mutation")

    if case.expected == "pass":
        errors = []
    elif case.expected in {"count_zero", "count_two"}:
        count = 0 if case.expected == "count_zero" else 2
        errors = [f"legacy mutable workflow uses count changed: {FIXTURE} -> {LEGACY_REFERENCE}; "
                  f"expected 1, got {count}. Shrink the grandfather list as the pinning drafts land."]
    else:
        require(case.expected == "alias_rejection", "unknown fixture expectation")
        line_number = len(BASELINE.splitlines()) + 1
        require(workflow.splitlines()[line_number - 1] == aliases[case.mutation].rstrip("\n"),
                "alias diagnostic anchor line changed")
        errors = [f"unsupported workflow alias value syntax: {FIXTURE}:{line_number}"]
    return workflow, errors


def run_case(case: Case, validator_bytes: bytes) -> dict:
    workflow, expected_errors = workflow_for(case)
    with tempfile.TemporaryDirectory(prefix="hydra-r33-workflow-alias-") as temporary:
        copy = Path(temporary) / "repo"
        source = copy / VALIDATOR
        fixture = copy / FIXTURE
        source.parent.mkdir(parents=True)
        fixture.parent.mkdir(parents=True)
        source.write_bytes(validator_bytes)
        fixture.write_bytes(workflow.encode("utf-8"))
        before = file_manifest(copy)
        require(set(before) == {VALIDATOR, FIXTURE}, "independent fixture file inventory drifted")
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", CHILD_PROBE, str(copy), FIXTURE, LEGACY_REFERENCE],
            cwd=copy, text=True, capture_output=True, timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        require(file_manifest(copy) == before, "scanner changed copied source or fixture bytes")
        require(source.read_bytes() == validator_bytes, "copied production source changed")
        actual = json.loads(result.stdout) if result.returncode == 0 and not result.stderr.strip() else None
        expected_inventory = [{"path": FIXTURE, "reference": LEGACY_REFERENCE, "count": 1}]
        passed = (actual is not None and set(actual) == {"errors", "legacy_inventory"}
                  and actual["errors"] == expected_errors
                  and actual["legacy_inventory"] == expected_inventory)
        return {"case": case.name, "expectation": case.expected,
                "result": "PASS" if passed else "FAIL", "returncode": result.returncode,
                "expected_errors": expected_errors, "actual": actual, "stderr": result.stderr,
                "validator_sha256": before[VALIDATOR], "fixture_sha256": before[FIXTURE],
                "temporary_source_unchanged": True}


def run_full_repository_case(case: Case, baseline: dict[str, bytes]) -> dict:
    contents = dict(baseline)
    expected_errors = []
    if case.mutation == "full_repository_alias":
        original = baseline[REAL_WORKFLOW].decode("utf-8")
        require(original.count("jobs:\n") == 1, "real workflow jobs anchor changed")
        anchor = "  validate:\n"
        anchored = "  validate: &r33_validation\n"
        extra_job = "  r33_alias_validation: *r33_validation\n"
        require(original.count(anchor) == 1, "real workflow validate job anchor changed")
        require("r33_validation" not in original and original.endswith("\n"),
                "real workflow synthetic anchor conflicts or missing final newline")
        changed = original.replace(anchor, anchored, 1) + extra_job
        require(changed.removesuffix(extra_job).replace(anchored, anchor, 1) == original,
                "real alias mutation changed original workflow configuration or run bodies")
        contents[REAL_WORKFLOW] = changed.encode("utf-8")
        line_number = len(original.splitlines()) + 1
        require(changed.splitlines()[line_number - 1] == extra_job.rstrip("\n"),
                "real alias diagnostic anchor changed")
        expected_errors = [f"ERROR: unsupported workflow alias value syntax: {REAL_WORKFLOW}:{line_number}"]
    else:
        require(case.mutation == "full_repository_original", "unknown full repository case")
    changed_paths = [path for path in baseline if contents[path] != baseline[path]]
    expected_changes = [REAL_WORKFLOW] if expected_errors else []
    require(changed_paths == expected_changes, "full repository case changed an unexpected path")
    require(contents[VALIDATOR] == baseline[VALIDATOR], "full repository case changed production source")
    with tempfile.TemporaryDirectory(prefix="hydra-r33-whole-repo-alias-") as temporary:
        copy = Path(temporary) / "repo"
        for name, data in contents.items():
            target = copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        before = file_manifest(copy)
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(copy / VALIDATOR)],
            cwd=copy, text=True, capture_output=True, timeout=120,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        require(file_manifest(copy) == before, "full validator changed temporary repository bytes")
        lines = result.stdout.splitlines()
        errors = [line for line in lines if line.startswith("ERROR: ")]
        marker = "PUBLIC_REPOSITORY_VALIDATION=FAIL" if expected_errors else "PUBLIC_REPOSITORY_VALIDATION=PASS"
        opposite = "PUBLIC_REPOSITORY_VALIDATION=PASS" if expected_errors else "PUBLIC_REPOSITORY_VALIDATION=FAIL"
        passed = (result.returncode == (1 if expected_errors else 0)
                  and errors == expected_errors and marker in lines and opposite not in lines
                  and not result.stderr.strip())
        return {"case": case.name, "expectation": case.expected,
                "result": "PASS" if passed else "FAIL", "returncode": result.returncode,
                "expected_errors": expected_errors, "actual_errors": errors,
                "stderr": result.stderr, "changed_paths": changed_paths,
                "validator_sha256": before[VALIDATOR], "workflow_sha256": before[REAL_WORKFLOW],
                "production_legacy_inventory_unchanged": True,
                "temporary_source_unchanged": True,
                "stdout_sha256": digest(result.stdout.encode("utf-8"))}


def main() -> int:
    require(os.environ.get("GITHUB_ACTIONS") == "true", "this carrier is hosted-only")
    require(sys.version_info[:2] == (3, 11), "this carrier requires Python 3.11")
    head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
    require(not git("status", "--porcelain"), "source checkout must be clean")
    baseline = source_snapshot()
    hashes = {name: digest(data) for name, data in sorted(baseline.items())}
    print(json.dumps({"head": head, "tree": tree, "source_files": len(hashes),
                      "source_manifest_sha256": digest(json.dumps(hashes, sort_keys=True).encode()),
                      "validator_sha256": hashes[VALIDATOR],
                      "harness_sha256": hashes[Path(__file__).relative_to(ROOT).as_posix()]}, sort_keys=True))
    results = []
    try:
        for case in CASES:
            try:
                row = (run_full_repository_case(case, baseline)
                       if case.mutation.startswith("full_repository_")
                       else run_case(case, baseline[VALIDATOR]))
            except Exception as exc:
                row = {"case": case.name, "expectation": case.expected,
                       "result": "FAIL", "harness_error": f"{type(exc).__name__}: {exc}"}
            results.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
    finally:
        unchanged = (source_snapshot() == baseline
                     and git("rev-parse", "HEAD") == head
                     and git("rev-parse", "HEAD^{tree}") == tree
                     and not git("status", "--porcelain"))
        print(json.dumps({"source_unchanged": unchanged, "head": head, "tree": tree}, sort_keys=True))
    passed = sum(row["result"] == "PASS" for row in results)
    failed = len(results) - passed
    ok = unchanged and len(results) == len(CASES) and failed == 0
    print(f"WORKFLOW_ALIAS_REGRESSION={'PASS' if ok else 'FAIL'} TOTAL={len(results)} PASS={passed} FAIL={failed}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
