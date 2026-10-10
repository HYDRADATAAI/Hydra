"""Hosted, offline proof that the actual validator enforces the AWS hold.

The AWS deployment workflow stays byte-identical on disk. Synthetic conditions
exist only in the exact workflow read presented to validate_ci_contract.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
FROZEN_HEAD = "1491bae8d5b98ef9f53710262a760f37f41d2dac"
FROZEN_TREE = "287f637d02337aa17a91e415eeda156c3d134835"
FROZEN_LEAVES = 771
WORKFLOW_RELATIVE = ".github/workflows/aws-market-data-deploy.yml"
WORKFLOW_BLOB = "e512070651343e0c5892585f15cc1c258f3e2ce6"
VALIDATOR_RELATIVE = "tools/validate_public_repository.py"
EXTRA_PATHS = {
    "tools/test_aws_disabled_gate_regression.py",
    ".github/workflows/validation-aws-disabled-gate.yml",
}
# Root must prove zero source changes for RED. This one path is reserved for
# the later reviewed repair, only after a completed behavioral RED.
ALLOWED_SOURCE_CHANGES = {VALIDATOR_RELATIVE}
AUDIT = {"case_region": False, "git_command": None, "denied_events": []}


def deny_external_io(event, args):
    forbidden = event.startswith("socket.") or event in {
        "os.system", "os.posix_spawn", "os.exec", "os.spawn",
        "os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.link",
        "os.symlink", "os.truncate", "os.chmod", "os.chown", "os.utime",
    }
    if event == "subprocess.Popen":
        command = AUDIT["git_command"]
        # Windows audits the list2cmdline string and may leave executable=None;
        # POSIX audits the argv list. Both must equal this exact read command.
        expected_arguments = None if command is None else subprocess.list2cmdline(command)
        forbidden = (
            AUDIT["case_region"] or command is None
            or args[0] not in (None, "git")
            or (args[1] != command and args[1] != expected_arguments)
        )
    if event == "open":
        mode = args[1]
        flags = args[2]
        forbidden = (
            isinstance(mode, str) and any(letter in mode for letter in "wax+")
        ) or (
            isinstance(flags, int)
            and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        )
    if forbidden:
        AUDIT["denied_events"].append(event)
        raise RuntimeError("offline proof denied operation: " + event)


sys.addaudithook(deny_external_io)


def git(*args):
    allowed = {
        ("rev-parse", "HEAD"),
        ("rev-parse", "HEAD^{tree}"),
        ("rev-parse", FROZEN_HEAD + "^{tree}"),
        ("ls-tree", "-r", "-z", "--full-tree", FROZEN_HEAD),
        ("ls-tree", "-r", "-z", "--full-tree", "HEAD"),
        ("status", "--porcelain", "--untracked-files=all"),
    }
    if tuple(args) not in allowed or AUDIT["case_region"]:
        raise RuntimeError("unapproved git operation")
    command = ["git", "-C", str(ROOT), *args]
    AUDIT["git_command"] = command
    try:
        return subprocess.run(
            command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout
    finally:
        AUDIT["git_command"] = None


def leaf_inventory(ref):
    result = {}
    for entry in git("ls-tree", "-r", "-z", "--full-tree", ref).split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        mode, kind, sha = meta.decode("ascii").split()
        name = path.decode("utf-8")
        if name in result or kind != "blob" or mode not in {"100644", "100755"}:
            raise RuntimeError("unexpected source leaf: " + name)
        result[name] = {"mode": mode, "type": kind, "sha": sha}
    return result


def blob_sha(content):
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    ).hexdigest()


def disk_inventory(expected):
    observed = {}
    for name, metadata in sorted(expected.items()):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("missing or indirect source leaf: " + name)
        content = path.read_bytes()
        if blob_sha(content) != metadata["sha"]:
            raise RuntimeError("source differs from checked-out tree: " + name)
        observed[name] = {**metadata, "bytes": len(content),
                          "sha256": hashlib.sha256(content).hexdigest()}
    encoded = json.dumps(observed, sort_keys=True, separators=(",", ":")).encode()
    return observed, hashlib.sha256(encoded).hexdigest()


def fixture_cases(original):
    disabled_line = "    if: false\n"
    if original.count(disabled_line) != 1:
        raise RuntimeError("frozen disabled condition is not unique")
    active = original.replace(disabled_line, "    if: true\n", 1)
    main_condition = "github.ref == 'refs/heads/main'"
    restored = original.replace(disabled_line, "    if: " + main_condition + "\n", 1)
    spoof = "\n# if: false\n"
    return (
        ("disabled_original_accept", original, "false", False),
        ("active_true_missing_hold_text_reject", active, "true", True),
        ("active_true_comment_spoof_reject", active + spoof, "true", True),
        ("main_condition_comment_spoof_reject", restored + spoof, main_condition, True),
    )


def fixture_oracle(original, fixture, expected_condition):
    baseline = yaml.load(original, Loader=yaml.BaseLoader)
    parsed = yaml.load(fixture, Loader=yaml.BaseLoader)
    if list(parsed.get("jobs", {})) != ["deploy-and-verify"]:
        raise RuntimeError("fixture job inventory changed")
    job = parsed["jobs"]["deploy-and-verify"]
    condition = job.get("if")
    if condition != expected_condition or len(job.get("steps", [])) != 16:
        raise RuntimeError("fixture active condition or step count is incorrect")
    # All actual workflow content must remain identical after undoing the sole
    # intended condition mutation. Comments have no mapping representation.
    job["if"] = baseline["jobs"]["deploy-and-verify"]["if"]
    if parsed != baseline:
        raise RuntimeError("fixture has an unintended semantic change")
    return {"job": "deploy-and-verify", "condition": condition,
            "step_count": 16, "only_condition_changed": True}


def run_case(validator, original, case):
    case_id, fixture, expected_condition, expected_rejected = case
    oracle = fixture_oracle(original, fixture, expected_condition)
    target = (ROOT / WORKFLOW_RELATIVE).resolve()
    before_bytes = target.read_bytes()
    if blob_sha(before_bytes) != WORKFLOW_BLOB:
        raise RuntimeError("disabled AWS workflow changed before case")
    original_read_text = Path.read_text
    intercepted_reads = []
    errors = []
    caught = None

    def workflow_read_text(path, *args, **kwargs):
        if path.resolve() == target:
            intercepted_reads.append({"path": WORKFLOW_RELATIVE,
                                      "encoding": kwargs.get("encoding")})
            return fixture
        return original_read_text(path, *args, **kwargs)

    try:
        with patch.object(Path, "read_text", workflow_read_text):
            validator.validate_ci_contract(errors)
    except Exception as exc:
        caught = exc
    after_bytes = target.read_bytes()
    unrelated_errors = [error for error in errors if not error.startswith("aws-deploy ")]
    checks = {
        "actual_validator_completed": caught is None,
        "workflow_read_intercepted": len(intercepted_reads) >= 2,
        "read_method_restored": Path.read_text is original_read_text,
        "disabled_workflow_byte_preserved": before_bytes == after_bytes,
        "no_unrelated_contract_errors": not unrelated_errors,
        "expected_gate_decision": bool(errors) == expected_rejected,
    }
    infrastructure_failure = (
        caught is not None or len(intercepted_reads) < 2
        or Path.read_text is not original_read_text
        or before_bytes != after_bytes or bool(unrelated_errors)
    )
    return {
        "case": case_id, "fixture_sha256": hashlib.sha256(fixture.encode()).hexdigest(),
        "fixture_oracle": oracle, "expected_rejected": expected_rejected,
        "observed_rejected": bool(errors), "validator_errors": errors,
        "intercepted_reads": intercepted_reads, "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "passed": all(checks.values()), "infrastructure_failure": infrastructure_failure,
        "exception_type": type(caught).__name__ if caught is not None else None,
        "exception_text": str(caught) if caught is not None else None,
        "workflow_blob_before": blob_sha(before_bytes),
        "workflow_blob_after": blob_sha(after_bytes),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_OS") != "Windows"
            or sys.platform != "win32" or sys.version_info[:2] != (3, 11)
            or not sys.flags.isolated or not sys.dont_write_bytecode
            or yaml.__version__ != "6.0.2"):
        raise RuntimeError("proof requires authorized Windows/Python3.11/PyYAML6.0.2 lane")
    if re.fullmatch(r"[0-9a-f]{40}", args.expected_head) is None:
        raise RuntimeError("expected head must be an exact commit")
    head = git("rev-parse", "HEAD").decode().strip()
    tree = git("rev-parse", "HEAD^{tree}").decode().strip()
    if head != args.expected_head or git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("unexpected or dirty validation checkout")
    if git("rev-parse", FROZEN_HEAD + "^{tree}").decode().strip() != FROZEN_TREE:
        raise RuntimeError("frozen source tree mismatch")
    frozen = leaf_inventory(FROZEN_HEAD)
    current = leaf_inventory("HEAD")
    if len(frozen) != FROZEN_LEAVES or set(current) != set(frozen) | EXTRA_PATHS:
        raise RuntimeError("validation inventory differs from bounded design")
    changed = sorted(name for name in frozen if frozen[name] != current[name])
    if set(changed) - ALLOWED_SOURCE_CHANGES:
        raise RuntimeError("unapproved source delta: " + repr(changed))
    if frozen[WORKFLOW_RELATIVE]["sha"] != WORKFLOW_BLOB:
        raise RuntimeError("frozen workflow blob mismatch")
    before, before_digest = disk_inventory(current)
    original_workflow = (ROOT / WORKFLOW_RELATIVE).read_text(encoding="utf-8-sig")

    AUDIT["case_region"] = True
    source = (ROOT / VALIDATOR_RELATIVE).resolve()
    spec = importlib.util.spec_from_file_location("hydra_aws_hold_validator", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load actual repository validator")
    validator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = validator
    spec.loader.exec_module(validator)
    if (Path(validator.__file__).resolve() != source
            or Path(validator.validate_ci_contract.__code__.co_filename).resolve() != source
            or validator.ROOT != ROOT):
        raise RuntimeError("validator source binding failed")
    cases = []
    for case in fixture_cases(original_workflow):
        try:
            cases.append(run_case(validator, original_workflow, case))
        except Exception as exc:
            cases.append({"case": case[0], "passed": False,
                          "infrastructure_failure": True,
                          "exception_type": type(exc).__name__, "exception_text": str(exc)})
    imports = []
    for name, module in sorted(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        file = Path(module_file).resolve()
        try:
            relative = file.relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if relative not in before:
            raise RuntimeError("unbound repository module: " + name)
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if digest != before[relative]["sha256"]:
            raise RuntimeError("repository import bytes changed: " + name)
        imports.append({"module": name, "path": relative,
                        "git_blob": before[relative]["sha"], "sha256": digest})
    if not any(item["module"] == spec.name for item in imports):
        raise RuntimeError("actual validator absent from import inventory")
    AUDIT["case_region"] = False
    after, after_digest = disk_inventory(current)
    if (before != after or head != git("rev-parse", "HEAD").decode().strip()
            or tree != git("rev-parse", "HEAD^{tree}").decode().strip()
            or git("status", "--porcelain", "--untracked-files=all")):
        raise RuntimeError("source or checkout changed during proof")
    report = {
        "schema": "aws-disabled-gate-proof/v1",
        "claim": "actual validator rejects active AWS job despite inert hold-text spoof",
        "platform": sys.platform, "python": sys.version.split()[0],
        "pyyaml_version": yaml.__version__, "head": head, "tree": tree,
        "frozen_head": FROZEN_HEAD, "frozen_tree": FROZEN_TREE,
        "frozen_source_leaves": len(frozen), "validation_leaves": len(current),
        "source_changes": [{"path": name, "frozen": frozen[name],
                            "validation": current[name]} for name in changed],
        "unchanged_source_leaves": len(frozen) - len(changed),
        "extra_paths": sorted(EXTRA_PATHS), "imports": imports,
        "before_inventory_sha256": before_digest, "after_inventory_sha256": after_digest,
        "source_preserved": before == after, "cases": cases,
        "passed": sum(case["passed"] for case in cases),
        "failed": sum(not case["passed"] for case in cases),
        "infrastructure_failures": sum(case["infrastructure_failure"] for case in cases),
        "denied_external_io_events": list(AUDIT["denied_events"]),
        "live_aws_calls": 0, "workflow_dispatches": 0,
    }
    print("AWS_DISABLED_GATE_PROOF_JSON_BEGIN")
    print(json.dumps(report, indent=2, sort_keys=True))
    print("AWS_DISABLED_GATE_PROOF_JSON_END")
    for case in cases:
        print("CASE", case["case"], "PASS" if case["passed"] else "FAIL",
              ",".join(case.get("failed_checks", [])))
    print("SOURCE_HASHES_STABLE=" + str(len(current)))
    return 0 if report["failed"] == 0 and not AUDIT["denied_events"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("AWS_DISABLED_GATE_INFRASTRUCTURE_FAILURE", type(exc).__name__, str(exc))
        raise
