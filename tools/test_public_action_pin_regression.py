#!/usr/bin/env python3
"""Hosted-only hostile action-pin checks using isolated repository copies.

Workflow mutations are inert text fixtures. Only the copied public validator is
executed; no mutated workflow, action, AWS command, or domain test is launched.
The same harness is used unchanged before and after the bounded parser repair.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = "tools/validate_public_repository.py"
SQL = ".github/workflows/sql-data-quality-sample.yml"
AWS = ".github/workflows/aws-market-data-pipeline.yml"
SUCCESSOR = ".github/workflows/nyx-constraint-successor-chain.yml"
FIRST_SLICE = ".github/workflows/constraint-first-slice-integration.yml"
CHECKOUT = "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
PYTHON = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
EXPECTED_ACTIONS = {
    SQL: [CHECKOUT, PYTHON],
    AWS: [CHECKOUT, PYTHON,
          "aws-actions/setup-sam@89ddb14d60e682855e3fea4be85b3c56485de310",
          "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"],
    SUCCESSOR: [CHECKOUT, PYTHON],
    FIRST_SLICE: [CHECKOUT, PYTHON],
}


@dataclass(frozen=True)
class Case:
    name: str
    workflow: str | None
    mutation: str
    expected: str


CASES = (
    Case("original_positive", None, "unchanged", "pass"),
    Case("sql_unnamed_equivalent_positive", SQL, "unnamed_equivalent", "pass"),
    Case("sql_named_extra_mutable", SQL, "named_mutable", "mutable_rejection"),
    Case("sql_unnamed_extra_mutable", SQL, "unnamed_mutable", "mutable_rejection"),
    Case("sql_named_extra_full_sha", SQL, "named_full_sha", "inventory_rejection"),
    Case("sql_unnamed_extra_full_sha", SQL, "unnamed_full_sha", "inventory_rejection"),
    Case("aws_unnamed_extra_mutable", AWS, "unnamed_mutable", "mutable_rejection"),
    Case("successor_unnamed_extra_mutable", SUCCESSOR, "unnamed_mutable", "mutable_rejection"),
    Case("first_slice_unnamed_extra_mutable", FIRST_SLICE, "unnamed_mutable", "mutable_rejection"),
)


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise AssertionError(detail)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def source_snapshot() -> dict[str, bytes]:
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    result = {}
    for raw in names:
        if not raw:
            continue
        name = os.fsdecode(raw)
        path = ROOT / name
        require(not path.is_symlink(), f"source symlink is outside fixed harness scope: {name}")
        require(path.is_file(), f"tracked source file missing: {name}")
        result[name] = path.read_bytes()
    require(VALIDATOR in result, "tracked public validator missing")
    return result


def manifest(contents: dict[str, bytes]) -> dict[str, str]:
    return {name: sha256(data) for name, data in sorted(contents.items())}


def step_blocks(text: str) -> list[str]:
    """Constrained byte-preservation helper, not a general YAML parser."""
    require(text.count("    steps:\n") == 1, "fixed fixture must have one four-space steps key")
    starts = [m.start() for m in re.finditer(r"(?m)^      - ", text)]
    require(bool(starts), "fixed fixture has no six-space block steps")
    return [text[start:end] for start, end in zip(starts, starts[1:] + [len(text)])]


def action_refs(text: str) -> list[str]:
    refs = []
    for block in step_blocks(text):
        values = []
        for line in block.splitlines():
            if line.startswith("      - uses: "):
                values.append(line[len("      - uses: "):])
            elif line.startswith("        uses: "):
                values.append(line[len("        uses: "):])
        require(len(values) <= 1, "multiple action keys in fixed step fixture")
        refs.extend(value.split(" #", 1)[0].strip() for value in values)
    return refs


def run_blocks(text: str) -> list[str]:
    return [block for block in step_blocks(text)
            if any(line.startswith(("        run:", "      - run:"))
                   for line in block.splitlines())]


def mutate(original: str, case: Case) -> str:
    require(case.workflow is not None, "mutation requires a workflow")
    expected = EXPECTED_ACTIONS[case.workflow]
    require(action_refs(original) == expected, "fixed baseline action inventory drifted")
    if case.mutation == "unnamed_equivalent":
        pattern = re.compile(r"(?m)^      - name: [^\n]+\n        uses: ([^\n]+)\n")
        matches = list(pattern.finditer(original))
        require(len(matches) == len(expected), "named-action rewrite anchor count changed")
        changed = pattern.sub(lambda m: "      - uses: " + m.group(1) + "\n", original)
        # Reconstruct all original name/uses prefixes to prove no other edits.
        restored = changed
        for match in reversed(matches):
            replacement = "      - uses: " + match.group(1) + "\n"
            require(restored.count(replacement) == 1, "ambiguous inverse named-action rewrite")
            restored = restored.replace(replacement, match.group(0), 1)
        require(restored == original, "unnamed rewrite changed unrelated bytes")
        require(action_refs(changed) == expected, "unnamed rewrite changed action references")
    else:
        mutable = case.mutation.endswith("mutable")
        ref = "actions/checkout@v4" if mutable else CHECKOUT
        if case.mutation.startswith("unnamed_"):
            added = f"      - uses: {ref}\n\n"
        else:
            require(case.mutation.startswith("named_"), "unknown fixture mutation")
            added = f"      - name: R32 inert parser fixture\n        uses: {ref}\n\n"
        anchor = "    steps:\n"
        require(original.count(anchor) == 1, "extra-step insertion anchor changed")
        changed = original.replace(anchor, anchor + added, 1)
        require(changed.replace(anchor + added, anchor, 1) == original,
                "extra-step insertion changed unrelated bytes")
        require(action_refs(changed) == [ref, *expected], "extra action is not isolated")
    require(run_blocks(changed) == run_blocks(original), "workflow run bodies changed")
    return changed


def evaluate(case: Case, result: subprocess.CompletedProcess[str]) -> tuple[bool, list[str]]:
    lines = result.stdout.splitlines()
    errors = [line for line in lines if line.startswith("ERROR: ")]
    if case.expected == "pass":
        return (result.returncode == 0
                and "PUBLIC_REPOSITORY_VALIDATION=PASS" in lines
                and "PUBLIC_REPOSITORY_VALIDATION=FAIL" not in lines
                and not errors and not result.stderr.strip()), errors
    require(case.workflow is not None, "negative case needs a workflow diagnostic")
    inventory = f"ERROR: {case.workflow} action pins changed: "
    mutable = f"ERROR: {case.workflow} actions must use full commit SHAs"
    relevant = [line for line in errors if line.startswith(inventory)]
    expected_count = 1 if case.expected == "inventory_rejection" else 2
    exact_errors = len(relevant) == 1 and len(errors) == expected_count
    if case.expected == "mutable_rejection":
        exact_errors = exact_errors and errors.count(mutable) == 1
    return (result.returncode == 1
            and "PUBLIC_REPOSITORY_VALIDATION=FAIL" in lines
            and "PUBLIC_REPOSITORY_VALIDATION=PASS" not in lines
            and exact_errors and not result.stderr.strip()), errors


def run_case(case: Case, baseline: dict[str, bytes]) -> dict:
    contents = dict(baseline)
    if case.workflow is not None:
        contents[case.workflow] = mutate(contents[case.workflow].decode("utf-8"), case).encode("utf-8")
    changed_paths = [name for name in baseline if baseline[name] != contents[name]]
    require(changed_paths == ([] if case.workflow is None else [case.workflow]),
            "mutation changed an unexpected source path")
    require(contents[VALIDATOR] == baseline[VALIDATOR], "mutation touched public validator")
    with tempfile.TemporaryDirectory(prefix="hydra-r32-action-pin-") as temporary:
        copy = Path(temporary) / "repo"
        for name, data in contents.items():
            target = copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        before = manifest(contents)
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(copy / VALIDATOR)],
            cwd=copy, text=True, capture_output=True, timeout=120,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        after = {str(path.relative_to(copy)).replace(os.sep, "/"): sha256(path.read_bytes())
                 for path in copy.rglob("*") if path.is_file()}
        require(before == after, "copied validator execution mutated the temporary source tree")
        passed, errors = evaluate(case, result)
        return {"case": case.name, "expectation": case.expected,
                "result": "PASS" if passed else "FAIL", "returncode": result.returncode,
                "errors": errors, "stderr": result.stderr,
                "changed_paths": changed_paths, "temporary_source_unchanged": True,
                "stdout_sha256": sha256(result.stdout.encode("utf-8")),
                "validator_sha256": before[VALIDATOR],
                "workflow_sha256": before.get(case.workflow) if case.workflow else None}


def main() -> int:
    require(os.environ.get("GITHUB_ACTIONS") == "true", "this carrier is hosted-only")
    require(sys.version_info[:2] == (3, 11), "this carrier requires Python 3.11")
    head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
    require(not git("status", "--porcelain"), "source checkout is not clean")
    baseline = source_snapshot()
    before = manifest(baseline)
    print(json.dumps({"head": head, "tree": tree, "source_files": len(before),
                      "source_manifest_sha256": sha256(json.dumps(before, sort_keys=True).encode()),
                      "validator_sha256": before[VALIDATOR],
                      "harness_sha256": before[str(Path(__file__).relative_to(ROOT))]}, sort_keys=True))
    results = []
    try:
        for case in CASES:
            try:
                result = run_case(case, baseline)
            except Exception as exc:
                result = {"case": case.name, "expectation": case.expected,
                          "result": "FAIL", "harness_error": f"{type(exc).__name__}: {exc}"}
            results.append(result)
            print(json.dumps(result, sort_keys=True), flush=True)
    finally:
        unchanged = (source_snapshot() == baseline
                     and git("rev-parse", "HEAD") == head
                     and git("rev-parse", "HEAD^{tree}") == tree
                     and not git("status", "--porcelain"))
        print(json.dumps({"source_unchanged": unchanged, "head": head, "tree": tree}, sort_keys=True))
    passed = sum(row["result"] == "PASS" for row in results)
    failed = len(results) - passed
    ok = unchanged and len(results) == len(CASES) and failed == 0
    print(f"ACTION_PIN_REGRESSION={'PASS' if ok else 'FAIL'} TOTAL={len(results)} PASS={passed} FAIL={failed}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
