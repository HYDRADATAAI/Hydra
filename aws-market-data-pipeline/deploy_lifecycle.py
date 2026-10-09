"""Fail-closed lifecycle helpers for the temporary AWS demo stack."""

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
OWNERSHIP_TAGS = (
    "hydra:github-repository",
    "hydra:github-run-id",
    "hydra:github-run-attempt",
)
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


def describe_stack(
    stack_name: str, aws_region: str, *, runner: Runner
) -> dict[str, Any] | None:
    result = run(
        ["aws", "cloudformation", "describe-stacks", "--stack-name", stack_name,
         "--region", aws_region, "--output", "json"],
        runner=runner,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout or "").lower()
        if "does not exist" in detail:
            return None
        raise LifecycleError(
            "unable to establish stack state; refusing lifecycle action: "
            + (result.stderr or result.stdout or "describe-stacks failed").strip()
        )
    try:
        stacks = json.loads(result.stdout).get("Stacks", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        raise LifecycleError("describe-stacks returned invalid JSON") from exc
    if len(stacks) != 1 or not isinstance(stacks[0], dict):
        raise LifecycleError("describe-stacks returned an unexpected result")
    return stacks[0]


def write_github_env(env: Mapping[str, str], key: str, value: str) -> None:
    with Path(required(env, "GITHUB_ENV")).open("a", encoding="utf-8") as stream:
        stream.write(f"{key}={value}\n")


def guard(*, env: Mapping[str, str], runner: Runner = subprocess.run) -> str:
    """Refuse an existing or indeterminate stack and export a unique name."""
    name = effective_stack_name(env)
    if describe_stack(name, region(env), runner=runner) is not None:
        raise LifecycleError("refusing to update or delete an existing stack")
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


def deploy(*, env: Mapping[str, str], runner: Runner = subprocess.run) -> str:
    """Deploy a run-scoped stack with tags used to authorize later cleanup."""
    name = required(env, "STACK_NAME")
    aws_region = region(env)
    if describe_stack(name, aws_region, runner=runner) is not None:
        raise LifecycleError("refusing to update or delete an existing stack")
    raw, curated = bucket_names(name, aws_region, runner=runner)
    tags = {
        **identity(env),
        "hydra:sample": "aws-market-data-pipeline",
        "hydra:data-boundary": "synthetic-non-live",
    }
    command = [
        "sam", "deploy", "--stack-name", name, "--region", aws_region,
        "--resolve-s3", "--capabilities", "CAPABILITY_IAM",
        "--no-confirm-changeset", "--no-fail-on-empty-changeset",
        "--parameter-overrides", f"RawBucketName={raw}",
        f"CuratedBucketName={curated}", "--tags",
        *[f"{key}={value}" for key, value in tags.items()],
    ]
    run(command, runner=runner)
    write_github_env(env, "RAW_BUCKET", raw)
    write_github_env(env, "CURATED_BUCKET", curated)
    return name


def tags_match(observed: Any, expected: Mapping[str, str]) -> bool:
    if not isinstance(observed, list):
        return False
    by_key = {
        row.get("Key"): row.get("Value")
        for row in observed
        if isinstance(row, dict)
    }
    return all(by_key.get(key) == value for key, value in expected.items())


def owned_buckets(
    name: str,
    aws_region: str,
    tags: Mapping[str, str],
    *,
    runner: Runner,
) -> list[str]:
    result = run(
        ["aws", "cloudformation", "list-stack-resources", "--stack-name", name,
         "--region", aws_region, "--output", "json"],
        runner=runner,
    )
    try:
        resources = json.loads(result.stdout).get("StackResourceSummaries", [])
    except (json.JSONDecodeError, AttributeError) as exc:
        raise LifecycleError("list-stack-resources returned invalid JSON") from exc

    owned: list[str] = []
    for item in resources:
        if (
            item.get("LogicalResourceId") not in BUCKET_RESOURCES
            or item.get("ResourceType") != "AWS::S3::Bucket"
            or item.get("ResourceStatus") == "DELETE_COMPLETE"
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
        if tags_match(bucket_tags, tags):
            owned.append(bucket)
    return owned


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
    """Clean only this attempt's tagged stack and its tagged S3 resources."""
    name = required(env, "STACK_NAME")
    aws_region = region(env)
    tags = identity(env)
    stack = describe_stack(name, aws_region, runner=runner)
    if stack is None or not tags_match(stack.get("Tags"), tags):
        return False
    for bucket in owned_buckets(name, aws_region, tags, runner=runner):
        empty_bucket(bucket, aws_region, runner=runner)
    run(
        ["sam", "delete", "--stack-name", name, "--region", aws_region, "--no-prompts"],
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
