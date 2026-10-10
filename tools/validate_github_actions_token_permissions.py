#!/usr/bin/env python3
"""Validate least-privilege GitHub Actions token permissions."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PERMISSIONS = {"contents": "read"}
DEPLOY_WORKFLOW = ".github/workflows/aws-market-data-deploy.yml"
# This is the sole workflow allowed to request OIDC credentials for its AWS deploy.
DEPLOY_PERMISSIONS = {"contents": "read", "id-token": "write"}


def validate_workflow(
    workflow_path: Path, document: object, root: Path = ROOT
) -> list[str]:
    relative_path = workflow_path.relative_to(root).as_posix()
    expected = (
        DEPLOY_PERMISSIONS
        if relative_path == DEPLOY_WORKFLOW
        else BASELINE_PERMISSIONS
    )
    errors: list[str] = []

    if not isinstance(document, dict):
        return [f"{relative_path}: workflow root must be a mapping"]

    permissions = document.get("permissions")
    if permissions != expected:
        errors.append(
            f"{relative_path}: top-level permissions must be exactly {expected!r}; "
            f"found {permissions!r}"
        )

    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        errors.append(f"{relative_path}: jobs must be a mapping")
    else:
        for job_name, job in jobs.items():
            if isinstance(job, dict) and "permissions" in job:
                errors.append(
                    f"{relative_path}: job {job_name!r} must not override token permissions"
                )

    return errors


def validate_repository(root: Path = ROOT) -> list[str]:
    workflows = root / ".github" / "workflows"
    paths = sorted((*workflows.glob("*.yml"), *workflows.glob("*.yaml")))
    if not paths:
        return [".github/workflows: no workflow files found"]

    errors: list[str] = []
    for path in paths:
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{path.relative_to(root).as_posix()}: unable to parse YAML: {exc}")
            continue
        errors.extend(validate_workflow(path, document, root))
    return errors


def main() -> int:
    errors = validate_repository()
    if errors:
        print("GitHub Actions token permission validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("GitHub Actions token permissions are within the declared policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
