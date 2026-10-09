#!/usr/bin/env python3
"""Hosted-only, no-AWS tests of the actual workflow teardown Bash body.

CLI fixtures model aggregated list-object-versions output, not a service page.
Real jq transforms those fixtures. An isolated AWS stub enforces DeleteObjects'
1000-identifier limit. No production module is imported and no AWS tool runs.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ".github/workflows/aws-market-data-deploy.yml"
STEP_NAME = "Empty versioned buckets and delete stack"
RUN_TOKEN = "123-1"
STACK = "hydra-public-market-pipeline-demo-123-1"
REGION = "us-east-1"
RAW = "hydra-public-raw-expected"
CURATED = "hydra-public-curated-expected"
LIMIT_DIAGNOSTIC = "MOCK_DELETE_LIMIT_EXCEEDED count=1001 limit=1000"


@dataclass(frozen=True)
class Case:
    name: str
    versions: int = 0
    markers: int = 0
    owner_mismatch: bool = False
    continuation: bool = False


CASES = (
    Case("owner_mismatch_rejects_before_cleanup", owner_mismatch=True),
    Case("owned_empty_bucket_reaches_stack_delete"),
    Case("owned_exactly_1000_markers", markers=1000),
    Case("owned_1001_markers_split_required", markers=1001),
    Case("owned_exactly_1000_mixed_identifiers", versions=500, markers=500),
    Case("owned_1001_mixed_identifiers_split_required", versions=500, markers=501),
    Case("owned_continuation_token_preserved", versions=1000, continuation=True),
)


STUB = r'''
import json
import os
from pathlib import Path
import sys

config = json.loads(Path(os.environ["HARNESS_FIXTURE"]).read_text())
log_path = Path(os.environ["HARNESS_LOG"])
events = [json.loads(line) for line in log_path.read_text().splitlines()] if log_path.exists() else []
tool = Path(sys.argv[0]).name
args = sys.argv[1:]

def emit(event):
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")

def reject(detail):
    emit({"op": "contract_error", "tool": tool, "args": args, "detail": detail})
    print("STUB_CONTRACT_ERROR " + detail, file=sys.stderr)
    raise SystemExit(97)

def require(condition, detail):
    if not condition:
        reject(detail)

def deleted():
    return [tuple(item) for event in events if event["op"] == "delete-objects" and event["status"] == "accepted" for item in event["ids"]]

def expected():
    return [(bucket, item["Key"], item["VersionId"]) for bucket, pages in config["pages"].items() for page in pages for key in ("Versions", "DeleteMarkers") for item in page.get(key, [])]

if tool == "sam":
    require(args == ["delete", "--stack-name", config["stack"], "--region", config["region"], "--no-prompts"], "SAM arguments changed")
    require(config["owner"] == config["run_token"], "SAM after wrong owner")
    require(sorted(deleted()) == sorted(expected()), "SAM before all identifiers deleted exactly once")
    for bucket, pages in config["pages"].items():
        require(sum(e["op"] == "list-object-versions" and e["bucket"] == bucket for e in events) == len(pages), "SAM before all pages visited")
        require(sum(e["op"] == "s3-rm" and e["bucket"] == bucket for e in events) == 1, "SAM before bucket cleanup")
    require(not any(e["op"] == "sam-delete" for e in events), "duplicate SAM delete")
    emit({"op": "sam-delete", "args": args})
    raise SystemExit(0)

require(tool == "aws", "unexpected command " + tool)
if args[:2] == ["cloudformation", "describe-stacks"]:
    require(args == ["cloudformation", "describe-stacks", "--stack-name", config["stack"], "--region", config["region"], "--output", "json"], "stack lookup arguments changed")
    require(not events, "unexpected repeated stack lookup")
    emit({"op": "describe-stacks", "args": args})
    print(json.dumps({"Stacks": [{"Tags": [{"Key": "hydra:deployment-run", "Value": config["owner"]}], "StackStatus": "CREATE_COMPLETE"}]}))
elif args[:2] == ["cloudformation", "describe-stack-resources"]:
    require(args == ["cloudformation", "describe-stack-resources", "--stack-name", config["stack"], "--region", config["region"], "--output", "json"], "resource lookup arguments changed")
    require(config["owner"] == config["run_token"], "resource lookup after wrong owner")
    require([e["op"] for e in events] == ["describe-stacks"], "resource lookup order changed")
    emit({"op": "describe-stack-resources", "args": args})
    print(json.dumps({"StackResources": [{"LogicalResourceId": logical, "PhysicalResourceId": bucket, "ResourceStatus": "CREATE_COMPLETE"} for logical, bucket in config["resources"]]}))
elif args[:2] == ["s3", "rm"]:
    require(len(args) == 6 and args[3:] == ["--recursive", "--region", config["region"]], "current-object cleanup arguments changed")
    bucket = args[2].removeprefix("s3://")
    require(args[2] == "s3://" + bucket and bucket in config["pages"], "foreign cleanup bucket")
    require(any(e["op"] == "describe-stack-resources" for e in events), "cleanup without resource lookup")
    require(not any(e["op"] == "s3-rm" and e["bucket"] == bucket for e in events), "duplicate current-object cleanup")
    emit({"op": "s3-rm", "bucket": bucket, "args": args})
elif args[:2] == ["s3api", "list-object-versions"]:
    require(len(args) >= 4 and args[2] == "--bucket", "version-list bucket arguments changed")
    bucket = args[3]
    require(bucket in config["pages"], "foreign version-list bucket")
    index = sum(e["op"] == "list-object-versions" and e["bucket"] == bucket for e in events)
    require(index < len(config["pages"][bucket]), "extra version page")
    token = None if index == 0 else config["pages"][bucket][index - 1].get("NextToken")
    expected_args = ["s3api", "list-object-versions", "--bucket", bucket, "--region", config["region"], "--page-size", "1000", "--max-items", "1000"]
    if index:
        require(bool(token), "continuation lacks token")
        expected_args += ["--starting-token", token]
    expected_args += ["--output", "json"]
    require(args == expected_args, "version-list arguments or continuation token changed")
    require(any(e["op"] == "s3-rm" and e["bucket"] == bucket for e in events), "listing before bucket cleanup")
    emit({"op": "list-object-versions", "bucket": bucket, "index": index, "token": token, "args": args})
    print(json.dumps(config["pages"][bucket][index]))
elif args[:2] == ["s3api", "delete-objects"]:
    require(len(args) == 10 and args[2] == "--bucket" and args[4:7] == ["--region", config["region"], "--delete"] and args[8:] == ["--output", "json"], "version-delete arguments changed")
    bucket = args[3]
    require(bucket in config["pages"], "foreign version-delete bucket")
    payload = json.loads(args[7])
    require(set(payload) == {"Objects", "Quiet"} and payload["Quiet"] is True and type(payload["Objects"]) is list, "malformed delete payload")
    items = payload["Objects"]
    require(bool(items) and all(type(item) is dict and set(item) == {"Key", "VersionId"} and all(type(value) is str for value in item.values()) for item in items), "malformed identifiers")
    ids = [(bucket, item["Key"], item["VersionId"]) for item in items]
    require(len(ids) == len(set(ids)), "duplicate identifiers within batch")
    listed = [e for e in events if e["op"] == "list-object-versions" and e["bucket"] == bucket]
    require(bool(listed), "delete before page listing")
    page = config["pages"][bucket][listed[-1]["index"]]
    page_ids = {(bucket, item["Key"], item["VersionId"]) for key in ("Versions", "DeleteMarkers") for item in page.get(key, [])}
    require(set(ids) <= page_ids and not (set(ids) & set(deleted())), "foreign, unlisted or repeated deletion identifier")
    status = "rejected_limit" if len(ids) > 1000 else "accepted"
    emit({"op": "delete-objects", "bucket": bucket, "ids": ids, "count": len(ids), "status": status})
    if status == "rejected_limit":
        print("MOCK_DELETE_LIMIT_EXCEEDED count=" + str(len(ids)) + " limit=1000", file=sys.stderr)
        raise SystemExit(42)
    print(json.dumps({"Errors": []}))
else:
    reject("unexpected AWS operation")
'''


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise AssertionError(detail)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def source_snapshot() -> dict[str, str]:
    result = {}
    for raw in subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0"):
        if raw:
            name = os.fsdecode(raw)
            path = ROOT / name
            require(path.is_file() and not path.is_symlink(), "unsupported tracked file " + name)
            result[name] = digest(path.read_bytes())
    require(WORKFLOW in result, "workflow is not tracked")
    return result


def teardown_script(text: str) -> str:
    lines = text.splitlines()
    marker = "      - name: " + STEP_NAME
    require(lines.count(marker) == 1, "teardown step is not unique")
    start = lines.index(marker)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("      - ")), len(lines))
    run_lines = [i for i in range(start + 1, end) if lines[i] == "        run: |"]
    require(len(run_lines) == 1, "teardown run body is not unique")
    body = []
    for line in lines[run_lines[0] + 1:end]:
        require(not line.strip() or line.startswith("          "), "unexpected teardown body indentation")
        body.append(line[10:] if line.strip() else "")
    script = "\n".join(body) + "\n"
    require(script.startswith("set -euo pipefail\n"), "teardown strict shell mode missing")
    return script


def fixture(case: Case) -> dict:
    entries = lambda count, label: [{"Key": "synthetic/" + label + "/" + str(i), "VersionId": label + "-" + str(i)} for i in range(count)]
    page = {"Versions": entries(case.versions, "version"), "DeleteMarkers": entries(case.markers, "marker")}
    pages = [page]
    if case.continuation:
        page["NextToken"] = "synthetic-next-token"
        pages.append({"DeleteMarkers": entries(3, "continuation-marker")})
    return {"stack": STACK, "region": REGION, "run_token": RUN_TOKEN,
            "owner": "another-run" if case.owner_mismatch else RUN_TOKEN,
            "resources": [["RawBucket", RAW], ["CuratedBucket", CURATED]],
            "pages": {RAW: pages, CURATED: [{"Versions": [], "DeleteMarkers": []}]}}


def manifest(root: Path) -> dict[str, tuple[str, int]]:
    result = {}
    for path in root.rglob("*"):
        require(not path.is_symlink(), "temporary fixture introduced a symlink")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = (digest(path.read_bytes()), path.stat().st_mode & 0o777)
    return result


def run_case(case: Case, script: str, bash: Path, jq: Path, seq: Path) -> dict:
    config = fixture(case)
    with tempfile.TemporaryDirectory(prefix="hydra-r34-pagination-") as temporary:
        root = Path(temporary)
        binary = root / "bin"
        binary.mkdir()
        (root / "out").mkdir()
        config_path = root / "fixture.json"
        config_path.write_text(json.dumps(config, sort_keys=True), encoding="utf-8")
        (root / "actual-teardown.sh").write_text(script, encoding="utf-8")
        require("\n" not in sys.executable and " " not in sys.executable, "unsupported Python shebang path")
        stub_text = "#!" + sys.executable + "\n" + STUB
        for name in ("aws", "sam", "sleep"):
            target = binary / name
            target.write_text(stub_text, encoding="utf-8")
            target.chmod(0o755)
        for original, name in ((jq, "jq"), (seq, "seq")):
            shutil.copyfile(original, binary / name)
            (binary / name).chmod(0o755)
        require((binary / "jq").read_bytes() == jq.read_bytes(), "real jq copy changed")
        before = manifest(root)
        log = root / "out" / "events.jsonl"
        # Construct a fresh environment: no inherited credentials, shell startup
        # hooks, network clients, GitHub tokens or fallback system PATH.
        python_library = (Path(sys.base_prefix).resolve() / "lib").resolve()
        require(python_library.is_dir(), "trusted runner Python library directory missing")
        env = {"PATH": str(binary), "TMPDIR": str(root / "out"), "LD_LIBRARY_PATH": str(python_library),
               "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
               "HARNESS_FIXTURE": str(config_path), "HARNESS_LOG": str(log),
               "AWS_REGION": REGION, "STACK_NAME": STACK, "DEPLOYMENT_RUN_TOKEN": RUN_TOKEN,
               "RAW_BUCKET": RAW, "CURATED_BUCKET": CURATED}
        result = subprocess.run([str(bash), "--noprofile", "--norc", "-e", str(root / "actual-teardown.sh")],
                                cwd=root, env=env, capture_output=True, text=True, timeout=30)
        after = manifest(root)
        require({key: value for key, value in after.items() if key != "out/events.jsonl"} == before,
                "temporary script, fixture or executable bytes/modes changed")
        events = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        require(not any(event["op"] == "contract_error" for event in events), "stub contract error: " + result.stderr)
        require(not result.stdout, "unexpected teardown stdout: " + result.stdout)
        operations = [event["op"] for event in events]
        expected_ids = [(bucket, item["Key"], item["VersionId"]) for bucket, pages in config["pages"].items()
                        for page in pages for key in ("Versions", "DeleteMarkers") for item in page.get(key, [])]
        deletes = [event for event in events if event["op"] == "delete-objects"]
        accepted = [tuple(item) for event in deletes if event["status"] == "accepted" for item in event["ids"]]
        rejected = [event for event in deletes if event["status"] != "accepted"]
        if case.owner_mismatch:
            require(result.returncode == 1 and "ownership tag does not match" in result.stderr,
                    "wrong-owner case did not reach expected rejection")
            require(operations == ["describe-stacks"], "wrong owner reached a cleanup command")
            passed, mechanism = True, "ownership_rejected_before_cleanup"
        elif result.returncode == 42:
            require(case.versions + case.markers == 1001 and not case.continuation,
                    "unexpected size-limit failure case")
            require(result.stderr.strip() == LIMIT_DIAGNOSTIC, "size-limit failure was masked by another diagnostic")
            require(len(rejected) == 1 and rejected[0]["count"] == 1001 and not accepted,
                    "unexpected rejected batch or partial deletion")
            require(operations == ["describe-stacks", "describe-stack-resources", "s3-rm", "list-object-versions", "delete-objects"],
                    "size-limit failure did not stop at exact first delete")
            passed, mechanism = False, "combined_1001_identifier_batch_rejected"
        else:
            require(result.returncode == 0 and not result.stderr, "unexpected teardown failure: " + result.stderr)
            require(not rejected and Counter(accepted) == Counter(expected_ids), "deletion identifiers incomplete/repeated")
            require(all(event["count"] <= 1000 for event in deletes), "oversized accepted deletion")
            require(operations[-1:] == ["sam-delete"] and operations.count("sam-delete") == 1,
                    "missing, repeated or premature SAM delete")
            require([event["args"] for event in events if event["op"] == "sam-delete"] ==
                    [["delete", "--stack-name", STACK, "--region", REGION, "--no-prompts"]], "SAM identity changed")
            require(sum(event["op"] == "list-object-versions" for event in events) == (3 if case.continuation else 2),
                    "wrong page count")
            passed, mechanism = True, "all_identifiers_deleted_once_then_stack_deleted"
        return {"case": case.name, "result": "PASS" if passed else "FAIL", "mechanism": mechanism,
                "returncode": result.returncode, "stderr": result.stderr.strip(), "expected_identifiers": len(expected_ids),
                "accepted_identifiers": len(accepted), "delete_batch_sizes": [event["count"] for event in deletes],
                "operations": operations, "continuation_tokens": [event["token"] for event in events if event["op"] == "list-object-versions"],
                "fixture_sha256": before["fixture.json"][0], "actual_script_sha256": before["actual-teardown.sh"][0],
                "real_jq_sha256": before["bin/jq"][0], "temporary_inputs_unchanged": True}


def main() -> int:
    require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_OS") == "Linux",
            "this harness is restricted to hosted Linux GitHub Actions")
    binaries = []
    for name in ("bash", "jq", "seq"):
        located = shutil.which(name)
        require(located is not None, "required runner executable missing: " + name)
        binaries.append(Path(located).resolve())
    before = source_snapshot()
    head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
    require(not git("status", "--porcelain"), "source checkout must start clean")
    script = teardown_script((ROOT / WORKFLOW).read_text(encoding="utf-8"))
    rows = []
    try:
        for case in CASES:
            try:
                row = run_case(case, script, *binaries)
            except Exception as exc:
                row = {"case": case.name, "result": "FAIL", "mechanism": "unexpected_harness_or_source_failure",
                       "error_type": type(exc).__name__, "error": str(exc)}
            rows.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
    finally:
        unchanged = source_snapshot() == before and git("rev-parse", "HEAD") == head and git("rev-parse", "HEAD^{tree}") == tree and not git("status", "--porcelain")
        print(json.dumps({"source_head": head, "source_tree": tree, "source_unchanged": bool(unchanged),
                          "workflow_sha256": before[WORKFLOW]}, sort_keys=True), flush=True)
        require(unchanged, "source changed during hosted regression")
    passes = sum(row["result"] == "PASS" for row in rows)
    print(json.dumps({"cases": len(rows), "passed": passes, "failed": len(rows) - passes}, sort_keys=True), flush=True)
    return 0 if passes == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
