#!/usr/bin/env python3
"""Validate least-privilege GitHub Actions token permissions."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PERMISSIONS = {"contents": "read"}
DEPLOY_WORKFLOW = ".github/workflows/aws-market-data-deploy.yml"
DEPLOY_TRIGGERS = {"workflow_dispatch"}
DEPLOY_JOB = "deploy-and-verify"
DEPLOY_REF_CONDITION = "github.ref == 'refs/heads/main'"
DEPLOY_DISABLED_CONDITION = "false"
DEPLOY_ENVIRONMENT = "aws-demo"
# This is the sole workflow allowed to request OIDC credentials for its AWS deploy.
DEPLOY_PERMISSIONS = {"contents": "read", "id-token": "write"}


def _mapping_node_values(node: yaml.Node | None, key: str) -> list[yaml.Node]:
    if not isinstance(node, yaml.MappingNode):
        return []
    return [
        value
        for node_key, value in node.value
        if isinstance(node_key, yaml.ScalarNode) and node_key.value == key
    ]


def _duplicate_yaml_keys(node: yaml.Node | None) -> list[tuple[str, int]]:
    if isinstance(node, yaml.MappingNode):
        seen: set[str] = set()
        duplicates: list[tuple[str, int]] = []
        for key_node, value_node in node.value:
            if isinstance(key_node, yaml.ScalarNode):
                key = key_node.value
                if key in seen:
                    duplicates.append((key, key_node.start_mark.line + 1))
                seen.add(key)
            duplicates.extend(_duplicate_yaml_keys(value_node))
        return duplicates
    if isinstance(node, yaml.SequenceNode):
        return [
            duplicate
            for child in node.value
            for duplicate in _duplicate_yaml_keys(child)
        ]
    return []


def _has_unquoted_disabled_deploy_condition(document_node: yaml.Node | None) -> bool:
    jobs_nodes = _mapping_node_values(document_node, "jobs")
    if len(jobs_nodes) != 1:
        return False
    deploy_job_nodes = _mapping_node_values(jobs_nodes[0], DEPLOY_JOB)
    if len(deploy_job_nodes) != 1:
        return False
    condition_nodes = _mapping_node_values(deploy_job_nodes[0], "if")
    if len(condition_nodes) != 1:
        return False
    condition_node = condition_nodes[0]
    return (
        isinstance(condition_node, yaml.ScalarNode)
        and condition_node.tag == "tag:yaml.org,2002:bool"
        and condition_node.value.lower() == "false"
        and condition_node.style is None
    )


def validate_workflow(
    workflow_path: Path,
    document: object,
    root: Path = ROOT,
    document_node: yaml.Node | None = None,
) -> list[str]:
    relative_path = workflow_path.relative_to(root).as_posix()
    is_deploy_workflow = relative_path == DEPLOY_WORKFLOW
    expected = DEPLOY_PERMISSIONS if is_deploy_workflow else BASELINE_PERMISSIONS
    errors: list[str] = []
    for key, line in _duplicate_yaml_keys(document_node):
        errors.append(
            f"{relative_path}: duplicate YAML mapping key {key!r} at line {line}"
        )

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

    if is_deploy_workflow:
        triggers = document.get("on")
        if not isinstance(triggers, dict) or set(triggers) != DEPLOY_TRIGGERS:
            errors.append(
                f"{relative_path}: OIDC deploy workflow must use only "
                f"{sorted(DEPLOY_TRIGGERS)!r}"
            )

        if not isinstance(jobs, dict) or set(jobs) != {DEPLOY_JOB}:
            errors.append(
                f"{relative_path}: OIDC deploy workflow must contain only job "
                f"{DEPLOY_JOB!r}"
            )
        else:
            deploy_job = jobs[DEPLOY_JOB]
            if not isinstance(deploy_job, dict):
                errors.append(
                    f"{relative_path}: OIDC deploy job must be a mapping"
                )
            else:
                condition = deploy_job.get("if")
                disabled_hold = condition == DEPLOY_DISABLED_CONDITION and (
                    _has_unquoted_disabled_deploy_condition(document_node)
                )
                if condition != DEPLOY_REF_CONDITION and not disabled_hold:
                    errors.append(
                        f"{relative_path}: OIDC deploy job must be gated to "
                        "literal unquoted false or gated to refs/heads/main"
                    )
                if deploy_job.get("environment") != DEPLOY_ENVIRONMENT:
                    errors.append(
                        f"{relative_path}: OIDC deploy job must use the "
                        f"{DEPLOY_ENVIRONMENT!r} environment"
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
            source = path.read_text(encoding="utf-8")
            document_node = yaml.compose(source)
            document = yaml.load(source, Loader=yaml.BaseLoader)
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{path.relative_to(root).as_posix()}: unable to parse YAML: {exc}")
            continue
        errors.extend(validate_workflow(path, document, root, document_node))
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
