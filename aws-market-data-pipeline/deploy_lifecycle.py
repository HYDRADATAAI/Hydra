"""Create-only AWS demo lifecycle helper with StackId-bound cleanup."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

Runner = Callable[..., subprocess.CompletedProcess[str]]
BUCKET_RESOURCES = {"RawBucket", "CuratedBucket"}


class LifecycleError(RuntimeError):
    """Raised when lifecycle state cannot be established safely."""


def required(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise LifecycleError(f"required environment variable is missing: {key}")
    return value


def run(args: Sequence[str], *, runner: Runner, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = runner(list(args), text=True, capture_output=True, check=False)
    if check and result.returncode:
        detail = (result.stderr or result.stdout or "command failed").strip()
        raise LifecycleError(f"{args[0]} failed: {detail}")
    return result


def identity(env: Mapping[str, str]) -> dict[str, str]:
    return {
        "hydra:github-repository": required(env, "GITHUB_REPOSITORY"),
        "hydra:github-run-id": required(env, "GITHUB_RUN_ID"),
        "hydra:github-run-attempt": required(env, "GITHUB_RUN_ATTEMPT"),
    }


def region(env: Mapping[str, str]) -> str:
    return required(env, "AWS_REGION")


def effective_stack_name(env: Mapping[str, str]) -> str:
    name = (
        f"{required(env, 'STACK_NAME')}-"
        f"{required(env, 'GITHUB_RUN_ID')}-"
        f"{required(env, 'GITHUB_RUN_ATTEMPT')}"
    )
    if len(name) > 128 or not re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*", name):
        raise LifecycleError("effective stack name is invalid for CloudFormation")
    return name


def write_github_env(env: Mapping[str, str], key: str, value: str) -> None:
    with Path(required(env, "GITHUB_ENV")).open("a", encoding="utf-8") as stream:
        stream.write(f"{key}={value}\n")


def guard(*, env: Mapping[str, str], runner: Runner = subprocess.run) -> str:
    """Export a run-unique stack name; CreateStack provides the create-only gate."""
    name = effective_stack_name(env)
    write_github_env(env, "STACK_NAME", name)
    return name


def bucket_names(
    stack_name: str, aws_region: str, *, runner: Runner
) -> tuple[str, str]:
    result = run(
        ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
        runner=runner,
    )
    account = result.stdout.strip()
    if not re.fullmatch(r"\d{12}", account):
        raise LifecycleError("AWS account ID could not be verified")
    suffix = hashlib.sha256(stack_name.encode("utf-8")).hexdigest()[:12]
    unique = f"{account}-{aws_region}-{suffix}"
    return f"hydra-public-raw-{unique}", f"hydra-public-curated-{unique}"


def _stack_id(response: str, *, expected_name: str, aws_region: str) -> str:
    try:
        stack_id = json.loads(response)["StackId"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise LifecycleError("CreateStack did not return a StackId") from exc
    pattern = (
        rf"^arn:aws(?:-[a-z]+)?:cloudformation:{re.escape(aws_region)}:"
        rf"\d{{12}}:stack/{re.escape(expected_name)}/[0-9a-fA-F-]+$"
    )
    if not isinstance(stack_id, str) or not re.fullmatch(pattern, stack_id):
        raise LifecycleError("CreateStack returned an unexpected StackId")
    return stack_id


def deploy(*, env: Mapping[str, str], runner: Runner = subprocess.run) -> str:
    """Package with SAM, then create a new stack and persist only its returned ID."""
    name = required(env, "STACK_NAME")
    aws_region = region(env)
    raw, curated = bucket_names(name, aws_region, runner=runner)
    temp_dir = Path(required(env, "RUNNER_TEMP"))
    temp_dir.mkdir(parents=True, exist_ok=True)
    packaged_template = temp_dir / "hydra-market-data-packaged-template.yaml"
    package_prefix = (
        f"hydra-demo/{required(env, 'GITHUB_RUN_ID')}/"
        f"{required(env, 'GITHUB_RUN_ATTEMPT')}"
    )
    sample_dir = required(env, "SAMPLE_DIR")
    run(
        [
            "sam", "package", "--template-file", str(Path(sample_dir) / "template.json"),
            "--resolve-s3", "--s3-prefix", package_prefix,
            "--output-template-file", str(packaged_template), "--region", aws_region,
        ],
        runner=runner,
    )
    if not packaged_template.is_file():
        raise LifecycleError("sam package did not produce a template")

    tags = {
        **identity(env),
        "hydra:sample": "aws-market-data-pipeline",
        "hydra:data-boundary": "synthetic-non-live",
    }
    create_args = [
        "aws", "cloudformation", "create-stack", "--stack-name", name,
        "--template-body", f"file://{packaged_template}",
        "--capabilities", "CAPABILITY_IAM", "CAPABILITY_AUTO_EXPAND",
        "--disable-rollback", "--region", aws_region,
        "--parameters", f"ParameterKey=RawBucketName,ParameterValue={raw}",
        f"ParameterKey=CuratedBucketName,ParameterValue={curated}",
        "--tags", *[f"Key={key},Value={value}" for key, value in tags.items()],
        "--output", "json",
    ]
    created = run(create_args, runner=runner)
    stack_id = _stack_id(created.stdout, expected_name=name, aws_region=aws_region)
    # Persist the returned ID immediately. A later waiter failure still has a
    # positively identified stack for the always-run teardown step.
    write_github_env(env, "STACK_ID", stack_id)
    write_github_env(env, "RAW_BUCKET", raw)
    write_github_env(env, "CURATED_BUCKET", curated)
    run(
        ["aws", "cloudformation", "wait", "stack-create-complete",
         "--stack-name", stack_id, "--region", aws_region],
        runner=runner,
    )
    return stack_id


def tags_match(observed: Any, expected: Mapping[str, str]) -> bool:
    if not isinstance(observed, list):
        return False
    by_key = {
        row.get("Key"): row.get("Value")
        for row in observed
        if isinstance(row, dict)
    }
    return all(by_key.get(key) == value for key, value in expected.items())


def owned_buckets(stack_id: str, aws_region: str, *, runner: Runner) -> list[str]:
    result = run(
        ["aws", "cloudformation", "list-stack-resources", "--stack-name", stack_id,
         "--region", aws_region, "--output", "json"],
        runner=runner,
    )
    try:
        resources = json.loads(result.stdout).get("StackResourceSummaries", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        raise LifecycleError("list-stack-resources returned invalid JSON") from exc

    buckets: list[str] = []
    for item in resources:
        if (
            item.get("LogicalResourceId") not in BUCKET_RESOURCES
            or item.get("ResourceType") != "AWS::S3::Bucket"
            or item.get("ResourceStatus") != "CREATE_COMPLETE"
        ):
            continue
        bucket = item.get("PhysicalResourceId")
        if not isinstance(bucket, str) or not bucket:
            continue
        bucket_result = run(
            ["aws", "s3api", "get-bucket-tagging", "--bucket", bucket,
             "--region", aws_region, "--output", "json"],
            runner=runner,
            check=False,
        )
        if bucket_result.returncode:
            continue
        try:
            bucket_tags = json.loads(bucket_result.stdout).get("TagSet", [])
        except (json.JSONDecodeError, AttributeError):
            continue
        if tags_match(bucket_tags, identity_from_stack(stack_id, runner=runner, region=aws_region)):
            buckets.append(bucket)
    return buckets


def identity_from_stack(
    stack_id: str, *, runner: Runner, region: str
) -> dict[str, str]:
    result = run(
        ["aws", "cloudformation", "describe-stacks", "--stack-name", stack_id,
         "--region", region, "--output", "json"],
        runner=runner,
    )
    try:
        stacks = json.loads(result.stdout).get("Stacks", [])
        if len(stacks) != 1 or stacks[0].get("StackId") != stack_id:
            raise LifecycleError("StackId could not be re-verified")
        tags = stacks[0].get("Tags", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        raise LifecycleError("describe-stacks returned invalid JSON") from exc
    expected = {
        key: value for key, value in {
            item.get("Key"): item.get("Value")
            for item in tags if isinstance(item, dict)
        }.items()
        if key in {
            "hydra:github-repository",
            "hydra:github-run-id",
            "hydra:github-run-attempt",
        }
    }
    if len(expected) != 3:
        raise LifecycleError("stack is missing the run-ownership tags")
    return expected


def empty_bucket(bucket: str, aws_region: str, *, runner: Runner) -> None:
    result = run(
        ["aws", "s3api", "list-object-versions", "--bucket", bucket,
         "--region", aws_region, "--output", "json"],
        runner=runner,
    )
    try:
        listing = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LifecycleError("list-object-versions returned invalid JSON") from exc
    versions = [
        {"Key": row["Key"], "VersionId": row["VersionId"]}
        for field in ("Versions", "DeleteMarkers")
        for row in listing.get(field, [])
        if "Key" in row and "VersionId" in row
    ]
    for offset in range(0, len(versions), 1000):
        batch = versions[offset:offset + 1000]
        run(
            ["aws", "s3api", "delete-objects", "--bucket", bucket,
             "--region", aws_region, "--delete",
             json.dumps({"Objects": batch, "Quiet": True}, separators=(",", ":"))],
            runner=runner,
        )


def teardown(*, env: Mapping[str, str], runner: Runner = subprocess.run) -> bool:
    """Empty verified CREATE_COMPLETE buckets, then delete only the captured StackId."""
    stack_id = env.get("STACK_ID", "").strip()
    if not stack_id:
        return False
    aws_region = region(env)
    expected_tags = identity(env)
    actual_tags = identity_from_stack(stack_id, runner=runner, region=aws_region)
    if actual_tags != expected_tags:
        return False
    for bucket in owned_buckets(stack_id, aws_region, runner=runner):
        empty_bucket(bucket, aws_region, runner=runner)
    run(
        ["aws", "cloudformation", "delete-stack", "--stack-name", stack_id,
         "--region", aws_region],
        runner=runner,
    )
    return True


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 1 or args[0] not in {"guard", "deploy", "teardown"}:
        print("usage: deploy_lifecycle.py {guard|deploy|teardown}", file=sys.stderr)
        return 2
    try:
        {"guard": guard, "deploy": deploy, "teardown": teardown}[args[0]](env=os.environ)
    except (LifecycleError, OSError) as exc:
        print(f"AWS_DEMO_LIFECYCLE=FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
