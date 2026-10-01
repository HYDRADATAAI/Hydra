"""Windows-only red/green validation for the bounded Thread G receipt repair."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest

BASE = "ed690ddda710476ee6a051b77032f7d09a24d3d2"
SOURCE = "t6-fail-closed-validator/src/hydra_t6_failclosed/native_binding_admission.py"
TEST = "test_native_admission_input_types.py"


def git(*args):
    return subprocess.check_output(["git", *args])


def digest(data):
    return hashlib.sha256(data).hexdigest()


def child():
    suite = unittest.defaultTestLoader.discover(sys.argv[2], pattern=sys.argv[3])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record = {
        "tests": result.testsRun,
        "failures": [case.id() for case, _ in result.failures],
        "errors": [case.id() for case, _ in result.errors],
        "skips": [(case.id(), reason) for case, reason in result.skipped],
    }
    Path(sys.argv[4]).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


def main():
    if sys.platform != "win32":
        raise SystemExit("Windows required; do not run HYDRA tests on another OS")
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        return child()
    repo = Path(__file__).resolve().parents[2]
    os.chdir(repo)
    out = Path(r"D:\NYX_PORTABLE\THREAD_G_RECEIPT_REPAIR")
    out.mkdir(parents=True, exist_ok=True)
    os.environ.update(TEMP=str(out), TMP=str(out), PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    before = {p: digest(Path(p).read_bytes()) for p in git("ls-files", "-z").decode().split("\0") if p}
    baseline = out / "baseline"
    prefix = "t6-fail-closed-validator/src/"
    for p in git("ls-tree", "-r", "--name-only", BASE, "--", prefix).decode().splitlines():
        dest = baseline / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(git("show", BASE + ":" + p))
    expected_failures = {"test_native_admission_input_types.NativeAdmissionInputTypesTests.test_" + field + "_" + label for field in (
        "runtime_activation_authorized", "canonical_promotion_authorized", "live_source_authorized", "model_training_authorized", "trading_authorized"
    ) for label in ("integer_zero", "float_zero")}
    expected_errors = {"test_native_admission_input_types.NativeAdmissionInputTypesTests.test_chain_" + label for label in ("object", "integer", "boolean")}
    runs = {}

    def run(label, src, pattern):
        env = dict(os.environ, PYTHONPATH=str(src))
        report = out / (label + ".json")
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", str(repo / "t6-fail-closed-validator/tests"), pattern, str(report)]
        result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        (out / (label + ".log")).write_text(result.stdout, encoding="utf-8")
        print(result.stdout)
        data = json.loads(report.read_text(encoding="utf-8"))
        runs[label] = dict(data, command=command, returncode=result.returncode)
        return data, result.returncode

    red, rc = run("baseline", baseline / prefix, TEST)
    if rc != 1 or set(red["failures"]) != expected_failures or set(red["errors"]) != expected_errors or red["skips"] or red["tests"] != 37:
        raise AssertionError("Baseline does not reproduce exactly the 13 expected input-validation failures")
    baseline_bytes = git("show", BASE + ":" + SOURCE)
    candidate_bytes = Path(SOURCE).read_bytes()
    same = baseline_bytes == candidate_bytes
    if not same:
        for label, pattern in (("repaired_types", TEST), ("existing_admission", "test_native_binding_admission.py"), ("existing_bridge", "test_native_t5_t6_bridge.py")):
            green, rc = run(label, repo / prefix, pattern)
            if rc or green["failures"] or green["errors"] or green["skips"] or not green["tests"]:
                raise AssertionError("Candidate regression failed: " + label)
    after = {p: digest(Path(p).read_bytes()) for p in before}
    if before != after or git("status", "--porcelain").strip():
        raise AssertionError("Tracked source changed during validation")
    report = {
        "status": "BASELINE_DEFECTS_REPRODUCED" if same else "PASS_REPAIRED",
        "base": BASE, "head": git("rev-parse", "HEAD").decode().strip(),
        "tree": git("rev-parse", "HEAD^{tree}").decode().strip(),
        "os": platform.platform(), "python": sys.version,
        "baseline_source_sha256": digest(baseline_bytes), "candidate_source_sha256": digest(candidate_bytes),
        "tracked_source_count": len(before), "source_hashes_stable": True,
        "IMPLEMENTATION_AUTHORITY_ROUTE": "UNRESOLVED", "IMPLEMENTATION_ADMITTED": "NO",
        "REQUEST_SENT": False, "REAL_RECEIPT_SIGNATURE_VERIFICATION": "NOT_PERFORMED",
        "test_boundary": "Shape probes use a non-cryptographic test double. Existing tests use public synthetic test keys only. No authentic admission receipt is created or verified.",
        "runs": runs,
    }
    (out / "RESULT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "SOURCE_HASHES.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
