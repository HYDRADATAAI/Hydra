from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "aws-market-data-deploy.yml"
STEP_NAME = "Empty versioned buckets and delete stack"
RUN_TOKEN = "123-1"
RAW_BUCKET = "hydra-public-raw-expected"


def teardown_script() -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"      - name: {STEP_NAME}")
    run_line = next(i for i in range(start + 1, len(lines)) if lines[i] == "        run: |")
    body = []
    for line in lines[run_line + 1:]:
        if line.strip() and len(line) - len(line.lstrip(" ")) <= 8:
            break
        body.append(line[10:] if line.startswith("          ") else "")
    return "\n".join(body) + "\n"


def install_cli_stubs(root: Path) -> None:
    aws = root / "aws"
    aws.write_text(
        """#!/usr/bin/env python3
import json, os, pathlib, sys
args = sys.argv[1:]
def log(path, value):
    with open(os.environ[path], "a", encoding="utf-8") as f:
        f.write(json.dumps(value) + "\\n")
log("AWS_CALL_LOG", args)
if args[:2] == ["cloudformation", "describe-stacks"]:
    if "--query" in args:
        counter = pathlib.Path(os.environ["STATUS_COUNTER"])
        index = int(counter.read_text() or "0") if counter.exists() else 0
        states = json.loads(os.environ["STACK_STATUS_SEQUENCE"])
        print(states[min(index, len(states) - 1)])
        counter.write_text(str(index + 1))
    else:
        error = os.environ.get("DESCRIBE_STACKS_ERROR")
        if error:
            print(error, file=sys.stderr)
            raise SystemExit(int(os.environ.get("DESCRIBE_STACKS_ERROR_STATUS", "255")))
        print(os.environ["STACK_DESCRIPTION"])
elif args[:2] == ["cloudformation", "describe-stack-resources"]:
    print(os.environ["STACK_RESOURCES"])
elif args[:2] == ["s3", "rm"]:
    log("CLEANUP_LOG", args)
elif args[:2] == ["s3api", "list-object-versions"]:
    if "--starting-token" in args:
        print(os.environ["VERSION_PAGE_2"])
    else:
        print(os.environ["VERSION_PAGE_1"])
elif args[:2] == ["s3api", "delete-objects"]:
    counter = pathlib.Path(os.environ["DELETE_COUNTER"])
    index = int(counter.read_text() or "0") if counter.exists() else 0
    counter.write_text(str(index + 1))
    errors_on = int(os.environ.get("DELETE_ERRORS_ON_CALL", "0"))
    print(json.dumps({"Errors": [{"Key": "bad"}] if index + 1 == errors_on else []}))
else:
    raise SystemExit(99)
""",
        encoding="utf-8",
    )
    jq = root / "jq"
    jq.write_text(
        """#!/usr/bin/env python3
import json, sys
query = sys.argv[-1]
data = json.load(sys.stdin)
if "Tags[]?" in query:
    for tag in data["Stacks"][0].get("Tags", []):
        if tag.get("Key") == "hydra:deployment-run":
            print(tag.get("Value", ""))
elif ".Stacks[0].StackStatus" in query:
    print(data["Stacks"][0]["StackStatus"])
elif ".StackResources[]" in query:
    for resource in data.get("StackResources", []):
        if resource.get("LogicalResourceId") in ("RawBucket", "CuratedBucket") and resource.get("ResourceStatus") in ("CREATE_COMPLETE", "DELETE_FAILED"):
            print(resource["LogicalResourceId"] + "\\t" + resource["PhysicalResourceId"])
elif ".Objects | length" in query:
    print(len(data.get("Objects", [])))
elif ".NextToken // empty" in query:
    print(data.get("NextToken", ""))
elif ".Errors | length" in query:
    print(len(data.get("Errors", [])))
elif ".Versions // []" in query:
    entries = data.get("Versions", []) + data.get("DeleteMarkers", [])
    print(json.dumps({"Objects": [{"Key": item.get("Key"), "VersionId": item.get("VersionId")} for item in entries], "Quiet": True}))
else:
    raise SystemExit(2)
""",
        encoding="utf-8",
    )
    sam = root / "sam"
    sam.write_text(
        """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["SAM_CALL_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
""",
        encoding="utf-8",
    )
    sleep = root / "sleep"
    sleep.write_text(
        """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["SLEEP_CALL_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
""",
        encoding="utf-8",
    )
    for executable in (aws, jq, sam, sleep):
        executable.chmod(0o755)


@unittest.skipUnless(shutil.which("bash"), "the deploy teardown workflow uses Bash")
class DeployTeardownOwnershipTests(unittest.TestCase):
    def run_teardown(
        self,
        *,
        owner: str | None = RUN_TOKEN,
        status: str = "CREATE_COMPLETE",
        status_sequence: list[str] | None = None,
        resources: list[dict[str, str]] | None = None,
        page_1: dict | None = None,
        page_2: dict | None = None,
        delete_errors_on_call: int = 0,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, list[list[str]]]]:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            install_cli_stubs(root)
            aws_log = root / "aws-calls.jsonl"
            cleanup_log = root / "cleanup-calls.jsonl"
            sam_log = root / "sam-calls.jsonl"
            sleep_log = root / "sleep-calls.jsonl"
            stack_description = {
                "Stacks": [{
                    "Tags": ([{"Key": "hydra:deployment-run", "Value": owner}] if owner is not None else []),
                    "StackStatus": status,
                }]
            }
            stack_resources = resources if resources is not None else [{
                "LogicalResourceId": "RawBucket",
                "PhysicalResourceId": RAW_BUCKET,
                "ResourceStatus": "CREATE_COMPLETE",
            }]
            env = os.environ.copy()
            env.update({
                "AWS_CALL_LOG": str(aws_log),
                "CLEANUP_LOG": str(cleanup_log),
                "SAM_CALL_LOG": str(sam_log),
                "SLEEP_CALL_LOG": str(sleep_log),
                "STATUS_COUNTER": str(root / "status-counter"),
                "DELETE_COUNTER": str(root / "delete-counter"),
                "STACK_DESCRIPTION": json.dumps(stack_description),
                "STACK_STATUS_SEQUENCE": json.dumps(status_sequence or [status]),
                "STACK_RESOURCES": json.dumps({"StackResources": stack_resources}),
                "VERSION_PAGE_1": json.dumps(page_1 or {"Versions": [{"Key": "raw/a.csv", "VersionId": "v1"}], "NextToken": "page-2"}),
                "VERSION_PAGE_2": json.dumps(page_2 or {"DeleteMarkers": [{"Key": "raw/a.csv", "VersionId": "v0"}]}),
                "DELETE_ERRORS_ON_CALL": str(delete_errors_on_call),
                "DESCRIBE_STACKS_ERROR": os.environ.get("DESCRIBE_STACKS_ERROR", ""),
                "DESCRIBE_STACKS_ERROR_STATUS": os.environ.get("DESCRIBE_STACKS_ERROR_STATUS", "255"),
                "AWS_REGION": "us-east-1",
                "STACK_NAME": "hydra-public-market-pipeline-demo-123-1",
                "DEPLOYMENT_RUN_TOKEN": RUN_TOKEN,
                "RAW_BUCKET": RAW_BUCKET,
                "CURATED_BUCKET": "hydra-public-curated-expected",
                "PATH": str(root) + os.pathsep + env.get("PATH", ""),
            })
            result = subprocess.run(
                ["bash", "-e", "-c", teardown_script()],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            def read_log(path: Path) -> list[list[str]]:
                return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

            logs = {
                "aws": read_log(aws_log),
                "cleanup": read_log(cleanup_log),
                "sam": read_log(sam_log),
                "sleep": read_log(sleep_log),
            }
            return result, logs

    def test_mismatched_run_tag_stops_before_bucket_cleanup_or_stack_delete(self):
        result, logs = self.run_teardown(owner="another-run")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ownership tag does not match", result.stderr)
        self.assertEqual(len(logs["aws"]), 1)
        self.assertEqual(logs["aws"][0][:2], ["cloudformation", "describe-stacks"])
        self.assertFalse(logs["cleanup"])
        self.assertFalse(logs["sam"])

    def test_missing_run_tag_stops_before_bucket_cleanup_or_stack_delete(self):
        result, logs = self.run_teardown(owner=None)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ownership tag does not match", result.stderr)
        self.assertEqual(len(logs["aws"]), 1)
        self.assertFalse(logs["cleanup"])
        self.assertFalse(logs["sam"])

    def test_missing_stack_is_a_successful_noop(self):
        old_error = os.environ.get("DESCRIBE_STACKS_ERROR")
        old_status = os.environ.get("DESCRIBE_STACKS_ERROR_STATUS")
        os.environ["DESCRIBE_STACKS_ERROR"] = "Stack with id does not exist"
        os.environ["DESCRIBE_STACKS_ERROR_STATUS"] = "255"
        try:
            result, logs = self.run_teardown()
        finally:
            if old_error is None:
                os.environ.pop("DESCRIBE_STACKS_ERROR", None)
            else:
                os.environ["DESCRIBE_STACKS_ERROR"] = old_error
            if old_status is None:
                os.environ.pop("DESCRIBE_STACKS_ERROR_STATUS", None)
            else:
                os.environ["DESCRIBE_STACKS_ERROR_STATUS"] = old_status
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(logs["aws"]), 1)
        self.assertFalse(logs["cleanup"])
        self.assertFalse(logs["sam"])

    def test_other_stack_lookup_errors_propagate(self):
        old_error = os.environ.get("DESCRIBE_STACKS_ERROR")
        os.environ["DESCRIBE_STACKS_ERROR"] = "AccessDenied: denied"
        try:
            result, logs = self.run_teardown()
        finally:
            if old_error is None:
                os.environ.pop("DESCRIBE_STACKS_ERROR", None)
            else:
                os.environ["DESCRIBE_STACKS_ERROR"] = old_error
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("AccessDenied: denied", result.stderr)
        self.assertFalse(logs["cleanup"])
        self.assertFalse(logs["sam"])

    def test_resource_bucket_mismatch_stops_before_cleanup(self):
        result, logs = self.run_teardown(resources=[{
            "LogicalResourceId": "RawBucket",
            "PhysicalResourceId": "some-other-bucket",
            "ResourceStatus": "CREATE_COMPLETE",
        }])
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not bound to this stack resource", result.stderr)
        self.assertFalse(logs["cleanup"])
        self.assertFalse(logs["sam"])

    def test_curated_bucket_mismatch_stops_before_that_bucket_cleanup(self):
        result, logs = self.run_teardown(resources=[
            {
                "LogicalResourceId": "RawBucket",
                "PhysicalResourceId": RAW_BUCKET,
                "ResourceStatus": "CREATE_COMPLETE",
            },
            {
                "LogicalResourceId": "CuratedBucket",
                "PhysicalResourceId": "some-other-bucket",
                "ResourceStatus": "CREATE_COMPLETE",
            },
        ])
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not bound to this stack resource", result.stderr)
        self.assertEqual(len(logs["cleanup"]), 1)
        self.assertIn("s3://" + RAW_BUCKET, logs["cleanup"][0])
        self.assertFalse(logs["sam"])

    def test_unexpected_stack_status_stops_before_resource_lookup(self):
        result, logs = self.run_teardown(status="DELETE_IN_PROGRESS")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unexpected CloudFormation state", result.stderr)
        self.assertFalse(any(call[:2] == ["cloudformation", "describe-stack-resources"] for call in logs["aws"]))
        self.assertFalse(logs["cleanup"])
        self.assertFalse(logs["sam"])

    def test_in_progress_stack_is_polled_until_allowed_state(self):
        result, logs = self.run_teardown(status="CREATE_IN_PROGRESS", status_sequence=["CREATE_COMPLETE"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(logs["sleep"], [["10"]])
        status_queries = [call for call in logs["aws"] if call[:2] == ["cloudformation", "describe-stacks"] and "--query" in call]
        self.assertEqual(len(status_queries), 1)
        self.assertTrue(any(call[:2] == ["cloudformation", "describe-stack-resources"] for call in logs["aws"]))
        self.assertTrue(logs["sam"])

    def test_version_cleanup_follows_next_token_before_stack_delete(self):
        result, logs = self.run_teardown()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        version_calls = [call for call in logs["aws"] if call[:2] == ["s3api", "list-object-versions"]]
        delete_calls = [call for call in logs["aws"] if call[:2] == ["s3api", "delete-objects"]]
        self.assertEqual(len(version_calls), 2)
        self.assertIn("page-2", version_calls[1])
        self.assertEqual(len(delete_calls), 2)
        self.assertTrue(logs["sam"])

    def test_empty_version_page_continues_to_next_page(self):
        result, logs = self.run_teardown(page_1={
            "Versions": [],
            "DeleteMarkers": [],
            "NextToken": "page-2",
        })
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        version_calls = [call for call in logs["aws"] if call[:2] == ["s3api", "list-object-versions"]]
        delete_calls = [call for call in logs["aws"] if call[:2] == ["s3api", "delete-objects"]]
        self.assertEqual(len(version_calls), 2)
        self.assertIn("page-2", version_calls[1])
        self.assertEqual(len(delete_calls), 1)
        self.assertTrue(logs["sam"])

    def test_version_delete_errors_stop_before_stack_delete(self):
        result, logs = self.run_teardown(delete_errors_on_call=1)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("version cleanup reported errors", result.stderr)
        self.assertFalse(logs["sam"])


if __name__ == "__main__":
    unittest.main()
