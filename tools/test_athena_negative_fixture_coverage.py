#!/usr/bin/env python3
"""Hosted-only proof that two actual Athena negative tests reject a command-check mutant."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import traceback
import unittest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools/validate_public_repository.py"
TEST_PATH = ROOT / "tools/test_aws_deploy_validator_contract.py"
WORKFLOW_PATH = ROOT / ".github/workflows/aws-market-data-deploy.yml"
VALIDATOR_BLOB = "c877df0dd21d708cd76f1ff750cef3c1539fbf64"
WORKFLOW_BLOB = "393010579c6bc1786bfeda19b6ea45402449d8cd"
FROZEN_SOURCE_HEAD = "9015a67116e73b48ec4268073c0079cc08f0f5a1"
FROZEN_SOURCE_TREE = "58a892d413d84fcde78d65b144cbf739fcc96ebc"
EXPECTED_TRACKED_LEAVES = 776
METHODS = (
    "test_actual_athena_workflow_step_is_valid",
    "test_missing_run_filter_does_not_satisfy_contract",
    "test_comment_only_commands_do_not_satisfy_contract",
    "test_space_after_continuation_backslash_is_not_accepted",
)
TARGETS = METHODS[2:]
GIT = str(Path(shutil.which("git") or "/missing-git").resolve())
GIT_COMMANDS = (
    ("rev-parse", "HEAD"),
    ("rev-parse", "HEAD^{tree}"),
    ("status", "--porcelain=v1", "--untracked-files=all"),
    ("ls-tree", "-rz", "--full-tree", "HEAD"),
)
FORBIDDEN_EVENTS: list[str] = []


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise RuntimeError(detail)


def emit(value: object) -> None:
    print(json.dumps(value, sort_keys=True), flush=True)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def git(*arguments: str) -> bytes:
    require(arguments in GIT_COMMANDS, "unapproved Git read")
    return subprocess.check_output(
        [GIT, "-C", str(ROOT), *arguments],
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        timeout=30,
    )


def snapshot() -> dict[str, object]:
    require(not git("status", "--porcelain=v1", "--untracked-files=all"), "checkout is dirty")
    files: dict[str, object] = {}
    for record in git("ls-tree", "-rz", "--full-tree", "HEAD").split(b"\0"):
        if not record:
            continue
        metadata, path_bytes = record.split(b"\t", 1)
        mode, kind, expected_blob = metadata.decode("ascii").split()
        relative = path_bytes.decode("utf-8")
        relative_path = Path(relative)
        require(not relative_path.is_absolute() and ".." not in relative_path.parts, "invalid tracked path")
        path = ROOT / relative_path
        require(kind == "blob" and mode in {"100644", "100755"}, "unsupported tracked leaf")
        require(not path.is_symlink() and path.is_file(), "tracked source is not a regular file")
        data = path.read_bytes()
        require(git_blob(data) == expected_blob, f"tracked bytes differ: {relative}")
        files[relative] = {
            "git_blob": expected_blob,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            "mode": stat.S_IMODE(path.stat().st_mode),
        }
    require(len(files) == EXPECTED_TRACKED_LEAVES, "unexpected tracked leaf inventory")
    head = git("rev-parse", "HEAD").decode("ascii").strip()
    require(head == os.environ.get("EXPECTED_HEAD"), "checkout does not match exact PR head")
    return {"head": head, "tree": git("rev-parse", "HEAD^{tree}").decode("ascii").strip(), "files": files}


def audit_guard(event: str, arguments: tuple[object, ...]) -> None:
    denied = event.startswith("socket.") or event in {
        "urllib.Request", "http.client.connect", "os.system", "os.exec", "os.posix_spawn",
        "os.spawn", "os.fork", "os.forkpty", "pty.spawn",
    }
    if event == "subprocess.Popen":
        executable, argv, cwd, _environment = arguments
        allowed = [GIT, "-C", str(ROOT)]
        denied = not (
            executable == GIT
            and isinstance(argv, (list, tuple))
            and list(argv[:3]) == allowed
            and tuple(argv[3:]) in GIT_COMMANDS
            and cwd is None
        )
    if denied:
        FORBIDDEN_EVENTS.append(event)
        raise PermissionError(f"fixture audit guard denied {event}")


def timeout_handler(_signal: int, _frame: object) -> None:
    raise TimeoutError("hosted fixture exceeded bounded execution time")


def make_mutant(source: bytes) -> tuple[object, str, str]:
    module = ast.parse(source, filename=str(VALIDATOR_PATH))
    functions = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "athena_success_commands_are_valid"]
    require(len(functions) == 1, "helper definition count changed")
    original = functions[0]
    require(len(original.body) == 13, "helper statement inventory changed")
    prefix_source = '''
def expected_prefix(run_script: object) -> bool:
    """Require active result retrieval and verifier commands in the SUCCEEDED branch."""
    if not isinstance(run_script, str):
        return False
    expected_query = "query=\\\"SELECT COUNT(*) AS accepted_rows FROM committed_normalized_events WHERE pipeline_run_id = '$RUN_ID'\\\""
    if expected_query not in run_script:
        return False
'''
    expected_prefix = ast.parse(prefix_source).body[0].body
    dump = lambda nodes: ast.dump(ast.Module(body=nodes, type_ignores=[]), include_attributes=False)
    require(dump(original.body[:4]) == dump(expected_prefix), "type/query prefix differs from frozen contract")
    mutant = copy.deepcopy(original)
    mutant.body = copy.deepcopy(original.body[:4]) + [ast.Return(value=ast.Constant(value=True))]
    module_copy = ast.fix_missing_locations(ast.Module(body=[mutant], type_ignores=[]))
    namespace: dict[str, object] = {}
    exec(compile(module_copy, "<r37-memory-only-command-check-mutant>", "exec"), namespace)
    return (
        namespace[original.name],
        hashlib.sha256(dump(original.body).encode()).hexdigest(),
        hashlib.sha256(dump(mutant.body).encode()).hexdigest(),
    )


class RecordingResult(unittest.TestResult):
    def __init__(self) -> None:
        super().__init__()
        self.failure_details: list[dict[str, object]] = []

    def addFailure(self, test: unittest.TestCase, error: tuple[object, ...]) -> None:
        exception_type, exception, trace = error
        self.failure_details.append({
            "type": getattr(exception_type, "__name__", "unknown"),
            "exact_assertion_error": exception_type is AssertionError,
            "message": str(exception),
            "frames": [{"file": frame.filename, "method": frame.name, "line": frame.lineno} for frame in traceback.extract_tb(trace)],
        })
        super().addFailure(test, error)


def run_method(test_module: object, test_class: type, method: str, helper: object, phase: str) -> dict[str, object]:
    calls: list[dict[str, object]] = []

    def observed_helper(run_script: object) -> object:
        call: dict[str, object] = {
            "input_type": type(run_script).__name__,
            "input_sha256": hashlib.sha256(run_script.encode()).hexdigest() if isinstance(run_script, str) else None,
        }
        calls.append(call)
        result = helper(run_script)
        call["return_type"] = type(result).__name__
        call["returned"] = result
        return result

    previous_binding = test_module.athena_success_commands_are_valid
    test_module.athena_success_commands_are_valid = observed_helper
    result = RecordingResult()
    try:
        signal.alarm(30)
        unittest.TestSuite([test_class(method)]).run(result)
    finally:
        signal.alarm(0)
        test_module.athena_success_commands_are_valid = previous_binding

    expects_kill = phase == "mutant" and method in TARGETS
    infrastructure_ok = (
        result.testsRun == 1 and not result.errors and not result.skipped
        and not result.expectedFailures and not result.unexpectedSuccesses
        and len(calls) == 1 and calls[0].get("return_type") == "bool"
    )
    unit_pass = infrastructure_ok and not result.failures
    expected_return = method == METHODS[0] or expects_kill
    killed = False
    if infrastructure_ok and len(result.failure_details) == 1 and len(result.failures) == 1:
        failure = result.failure_details[0]
        frames = failure["frames"]
        killed = (
            expects_kill and calls[0]["returned"] is True
            and failure["exact_assertion_error"] and failure["message"] == "True is not false"
            and any(Path(frame["file"]).resolve() == TEST_PATH and frame["method"] == method for frame in frames)
            and any(frame["method"] == "assertFalse" and Path(frame["file"]).name == "case.py" for frame in frames)
        )
    if not infrastructure_ok:
        outcome = "INFRASTRUCTURE_FAILURE"
    elif expects_kill:
        outcome = "PASS" if killed else "COVERAGE_FAILURE" if unit_pass and calls[0]["returned"] is False else "INFRASTRUCTURE_FAILURE"
    else:
        outcome = "PASS" if unit_pass and calls[0]["returned"] is expected_return else "INFRASTRUCTURE_FAILURE"
    row = {
        "phase": phase, "method": method, "outcome": outcome,
        "expected_mutant_kill": expects_kill, "mutant_killed": killed,
        "tests_run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skips": len(result.skipped),
        "calls": calls, "failure_details": result.failure_details,
        "error_details": [detail for _test, detail in result.errors],
    }
    emit(row)
    return row


def main() -> int:
    require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_OS") == "Linux", "hosted Linux runner required")
    require(sys.version_info[:2] == (3, 11) and sys.dont_write_bytecode, "Python 3.11 with -B required")
    require(Path(GIT).is_file() and ROOT not in Path(GIT).parents, "trusted runner Git missing")
    before = snapshot()
    rows: list[dict[str, object]] = []
    original_sys_path = list(sys.path)
    original_alarm_handler = signal.signal(signal.SIGALRM, timeout_handler)
    sys.addaudithook(audit_guard)
    try:
        source = VALIDATOR_PATH.read_bytes()
        require(git_blob(source) == VALIDATOR_BLOB, "production helper source blob changed")
        require(git_blob(WORKFLOW_PATH.read_bytes()) == WORKFLOW_BLOB, "Athena workflow blob changed")
        parsed_tests = ast.parse(TEST_PATH.read_bytes(), filename=str(TEST_PATH))
        classes = [node for node in parsed_tests.body if isinstance(node, ast.ClassDef) and node.name == "AthenaDeployValidatorContractTests"]
        require(len(classes) == 1, "actual test class count changed")
        names = [node.name for node in classes[0].body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
        require(tuple(names) == METHODS and len(set(names)) == 4, "actual four-method inventory changed")
        require(not any(name == "tools" or name.startswith("tools.") for name in sys.modules), "source modules unexpectedly preloaded")
        sys.path.insert(0, str(ROOT))
        signal.alarm(120)
        test_module = importlib.import_module("tools.test_aws_deploy_validator_contract")
        validator_module = sys.modules["tools.validate_public_repository"]
        signal.alarm(0)
        require(Path(test_module.__file__).resolve() == TEST_PATH, "test module import path changed")
        require(Path(validator_module.__file__).resolve() == VALIDATOR_PATH, "validator import path changed")
        require(getattr(sys.modules["yaml"], "__version__", None) == "6.0.2", "PyYAML version changed")
        original = validator_module.athena_success_commands_are_valid
        require(test_module.athena_success_commands_are_valid is original, "actual imported helper binding differs")
        test_class = test_module.AthenaDeployValidatorContractTests
        require(tuple(unittest.defaultTestLoader.getTestCaseNames(test_class)) == tuple(sorted(METHODS)), "unittest discovery differs")
        mutant, original_ast_hash, mutant_ast_hash = make_mutant(source)
        emit({
            "frozen_source_head": FROZEN_SOURCE_HEAD, "frozen_source_tree": FROZEN_SOURCE_TREE,
            "validation_head": before["head"], "validation_tree": before["tree"],
            "tracked_leaves": len(before["files"]), "validator_blob": VALIDATOR_BLOB,
            "test_blob": git_blob(TEST_PATH.read_bytes()), "workflow_blob": WORKFLOW_BLOB,
            "helper_ast_sha256": original_ast_hash, "mutant_ast_sha256": mutant_ast_hash,
            "mutation": "retain exact docstring/type/query prefix; replace remaining command validation with return True",
            "audit_guard_installed_before_source_imports": True,
        })
        for phase, helper in (("healthy", original), ("mutant", mutant)):
            for method in METHODS:
                rows.append(run_method(test_module, test_class, method, helper, phase))
        require(test_module.athena_success_commands_are_valid is original, "test module binding was not restored")
        require(validator_module.athena_success_commands_are_valid is original, "production module helper was modified")
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_alarm_handler)
        sys.path[:] = original_sys_path
        after = snapshot()
        unchanged = before == after
        emit({"source_head": after["head"], "source_tree": after["tree"], "source_unchanged": unchanged, "forbidden_audit_events": FORBIDDEN_EVENTS})
        require(unchanged, "source inventory changed during proof")
        require(not FORBIDDEN_EVENTS, "fixture attempted forbidden network or process activity")
    totals = {
        "cases": len(rows), "passed": sum(row["outcome"] == "PASS" for row in rows),
        "coverage_failures": sum(row["outcome"] == "COVERAGE_FAILURE" for row in rows),
        "infrastructure_failures": sum(row["outcome"] == "INFRASTRUCTURE_FAILURE" for row in rows),
        "target_negatives": len(TARGETS), "mutant_kills": sum(row["mutant_killed"] for row in rows),
    }
    emit(totals)
    require(len(rows) == 8, "fixed eight-case inventory changed")
    return 2 if totals["infrastructure_failures"] else 1 if totals["coverage_failures"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit({"fatal_infrastructure_failure": type(exc).__name__, "detail": str(exc)})
        raise SystemExit(2) from exc
