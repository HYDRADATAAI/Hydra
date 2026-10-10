"""Offline four-case proof of deterministic polling response-body cleanup.

Run only in the isolated hosted validation lane. This observes closure before
return/raise; it does not measure a live network resource leak.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import urllib.error
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FROZEN_HEAD = "2ff5289b71dc69a964935596f9407c3e5c39035a"
FROZEN_TREE = "4852d0b344cfdd5239f08c9e2eb2ee6e54026c95"
FROZEN_LEAVES = 774
EXTRA_PATHS = {
    "tools/test_polling_response_cleanup_regression.py",
    ".github/workflows/validation-polling-response-cleanup.yml",
}
ALLOWED_SOURCE_CHANGES = {
    "constraint-runtime/src/hydra_constraint/polling.py",
    "constraint-runtime/tests/test_polling_response_limit.py",
}
AUDIT = {"case_region": False, "denied_events": []}


def deny_external_io(event, args):
    forbidden = event.startswith("socket.") or (
        AUDIT["case_region"]
        and event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"}
    )
    if forbidden:
        AUDIT["denied_events"].append(event)
        raise RuntimeError("offline proof denied external I/O: " + event)


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
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout


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


def disk_inventory(expected):
    observed = {}
    for name, metadata in sorted(expected.items()):
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("missing or indirect source leaf: " + name)
        content = path.read_bytes()
        blob = hashlib.sha1(
            b"blob " + str(len(content)).encode("ascii") + b"\0" + content
        ).hexdigest()
        if blob != metadata["sha"]:
            raise RuntimeError("source bytes differ from checked-out tree: " + name)
        observed[name] = {**metadata, "bytes": len(content),
                          "sha256": hashlib.sha256(content).hexdigest()}
    encoded = json.dumps(observed, sort_keys=True, separators=(",", ":")).encode()
    return observed, hashlib.sha256(encoded).hexdigest()


class TrackingBody(io.BytesIO):
    def __init__(self, body, status):
        super().__init__(body)
        self.status = status
        self.headers = {"X-Cleanup-Proof": "retained"}
        self.read_sizes = []
        self.bytes_read = 0
        self.close_calls = 0

    def read(self, size=-1):
        self.read_sizes.append(size)
        result = super().read(size)
        self.bytes_read += len(result)
        return result

    def close(self):
        self.close_calls += 1
        super().close()


def run_case(polling, kind, overflow):
    case_id = kind + ("_overflow" if overflow else "_exact_cap")
    status = 200 if kind == "success" else 503
    wire_body = b"abcd" if overflow else b"abc"
    stream = TrackingBody(wire_body, status)
    url = "https://offline.example.test/cleanup-proof"
    http_error = (
        urllib.error.HTTPError(url, status, "synthetic HTTP error",
                               stream.headers, stream)
        if kind == "http_error" else None
    )
    calls = []
    handlers = []
    response = None
    caught = None

    class Opener:
        def open(self, request, timeout):
            calls.append({"url": request.full_url,
                          "method": request.get_method(), "timeout": timeout})
            if http_error is not None:
                raise http_error
            return stream

    def build_opener(handler):
        handlers.append(handler)
        return Opener()

    result = {"case": case_id, "status": status, "cap": 3}
    try:
        try:
            with patch.object(polling.urllib.request, "build_opener", build_opener):
                response = polling.UrllibTransport(max_bytes=3).fetch(
                    url, headers={"User-Agent": "Hydra offline cleanup proof"}
                )
        except Exception as exc:
            caught = exc

        # Strong references to stream, HTTPError and caught exception are still
        # live here. Harness cleanup occurs only after all observations.
        observed_closed = stream.closed
        checks = {
            "one_original_get": calls == [{"url": url, "method": "GET", "timeout": 20}],
            "actual_no_redirect_handler": len(handlers) == 1 and
                type(handlers[0]) is polling._NoRedirectHandler,
            "bounded_read_requests": stream.read_sizes == ([4] if overflow else [4, 1]),
            "bounded_consumed_bytes": stream.bytes_read == (4 if overflow else 3),
            "response_body_closed": observed_closed,
        }
        if overflow:
            checks.update({
                "actual_overflow_exception": type(caught) is polling.ResponseTooLargeError,
                "overflow_cap_and_status": isinstance(caught, polling.ResponseTooLargeError)
                    and caught.max_bytes == 3 and caught.status == status,
                "no_response_on_overflow": response is None,
            })
        else:
            checks.update({
                "no_exception": caught is None,
                "actual_response": type(response) is polling.HttpResponse,
                "response_fields": isinstance(response, polling.HttpResponse)
                    and response.url == url and response.status == status
                    and response.body == b"abc"
                    and response.headers == {"x-cleanup-proof": "retained"},
                "capture_time_present": isinstance(response, polling.HttpResponse)
                    and isinstance(response.captured_at, str)
                    and response.captured_at.endswith("Z"),
            })
        unexpected = caught is not None and type(caught) is not polling.ResponseTooLargeError
        result.update({
            "checks": checks,
            "failed_checks": [name for name, value in checks.items() if not value],
            "passed": all(checks.values()),
            "infrastructure_failure": unexpected,
            "closed_before_harness_cleanup": observed_closed,
            "close_calls_before_harness_cleanup": stream.close_calls,
            "read_sizes": list(stream.read_sizes), "bytes_read": stream.bytes_read,
            "returned_status": response.status if response is not None else None,
            "exception_type": type(caught).__name__ if caught is not None else None,
            "exception_text": str(caught) if caught is not None else None,
            "retained_http_error": http_error is not None,
        })
    finally:
        # Test hygiene cannot satisfy the production-closure assertion above.
        if http_error is not None:
            http_error.close()
        stream.close()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_OS") != "Windows"
            or platform.system() != "Windows"
            or sys.version_info[:2] != (3, 11)
            or not sys.flags.isolated or not sys.dont_write_bytecode):
        raise RuntimeError("this proof requires the authorized Windows/Python 3.11 lane")
    head = git("rev-parse", "HEAD").decode().strip()
    tree = git("rev-parse", "HEAD^{tree}").decode().strip()
    if head != args.expected_head or git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("unexpected or dirty validation checkout")
    if git("rev-parse", FROZEN_HEAD + "^{tree}").decode().strip() != FROZEN_TREE:
        raise RuntimeError("frozen source tree mismatch")
    frozen = leaf_inventory(FROZEN_HEAD)
    current = leaf_inventory("HEAD")
    if len(frozen) != FROZEN_LEAVES or set(current) != set(frozen) | EXTRA_PATHS:
        raise RuntimeError("validation leaf inventory differs from bounded design")
    changed = sorted(name for name in frozen if frozen[name] != current[name])
    if set(changed) - ALLOWED_SOURCE_CHANGES:
        raise RuntimeError("unapproved source delta: " + repr(changed))
    before, before_digest = disk_inventory(current)

    AUDIT["case_region"] = True
    sys.path.insert(0, str(ROOT / "constraint-runtime" / "src"))
    from hydra_constraint import polling

    cases = []
    for kind, overflow in (("success", False), ("success", True),
                           ("http_error", False), ("http_error", True)):
        try:
            cases.append(run_case(polling, kind, overflow))
        except Exception as exc:
            cases.append({"case": kind + ("_overflow" if overflow else "_exact_cap"),
                          "passed": False, "infrastructure_failure": True,
                          "exception_type": type(exc).__name__, "exception_text": str(exc)})
    imports = []
    for name, module in sorted(sys.modules.items()):
        if name == "hydra_constraint" or name.startswith("hydra_constraint."):
            file = Path(module.__file__).resolve()
            relative = file.relative_to(ROOT).as_posix()
            if not relative.startswith("constraint-runtime/src/hydra_constraint/") or relative not in before:
                raise RuntimeError("unbound runtime import: " + name)
            data = file.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest != before[relative]["sha256"]:
                raise RuntimeError("runtime import bytes changed: " + name)
            imports.append({"module": name, "path": relative,
                            "git_blob": before[relative]["sha"], "sha256": digest})
    AUDIT["case_region"] = False
    after, after_digest = disk_inventory(current)
    if before != after or head != git("rev-parse", "HEAD").decode().strip() or tree != git("rev-parse", "HEAD^{tree}").decode().strip() or git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("source or checkout changed during the proof")

    report = {
        "schema": "polling-response-cleanup-proof/v1",
        "claim": "response body closed before fetch returns or raises; no live leak measurement",
        "platform": platform.system(), "python": platform.python_version(),
        "head": head, "tree": tree, "frozen_head": FROZEN_HEAD,
        "frozen_tree": FROZEN_TREE, "frozen_source_leaves": len(frozen),
        "validation_leaves": len(current), "source_changes": [
            {"path": name, "frozen": frozen[name], "validation": current[name]}
            for name in changed
        ],
        "unchanged_source_leaves": len(frozen) - len(changed),
        "extra_paths": sorted(EXTRA_PATHS),
        "before_inventory_sha256": before_digest, "after_inventory_sha256": after_digest,
        "source_preserved": before == after, "imports": imports,
        "cases": cases, "passed": sum(case["passed"] for case in cases),
        "failed": sum(not case["passed"] for case in cases),
        "infrastructure_failures": sum(case["infrastructure_failure"] for case in cases),
        "denied_external_io_events": list(AUDIT["denied_events"]),
    }
    print("POLLING_CLEANUP_PROOF_JSON_BEGIN")
    print(json.dumps(report, indent=2, sort_keys=True))
    print("POLLING_CLEANUP_PROOF_JSON_END")
    for case in cases:
        print("CASE", case["case"], "PASS" if case["passed"] else "FAIL",
              ",".join(case.get("failed_checks", [])))
    print("SOURCE_HASHES_STABLE=" + str(len(current)))
    return 0 if report["failed"] == 0 and not AUDIT["denied_events"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("POLLING_CLEANUP_INFRASTRUCTURE_FAILURE", type(exc).__name__, str(exc))
        raise
