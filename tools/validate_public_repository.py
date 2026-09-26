#!/usr/bin/env python3
"""Validate HYDRA's recruiter-facing core repository contract."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "t6-fail-closed-validator"
PIPELINE = ROOT / "market-data-pipeline-sample"
SQL_SAMPLE = ROOT / "sql-data-quality-sample"
AWS_SAMPLE = ROOT / "aws-market-data-pipeline"

REQUIRED_PATHS = (
    "README.md",
    ".github/workflows/public-root-hygiene.yml",
    ".github/workflows/t6-validator.yml",
    "t6-fail-closed-validator/README.md",
    "t6-fail-closed-validator/pyproject.toml",
    "t6-fail-closed-validator/src/hydra_t6_failclosed/__init__.py",
    "t6-fail-closed-validator/src/hydra_t6_failclosed/authority.py",
    "t6-fail-closed-validator/src/hydra_t6_failclosed/documents.py",
    "t6-fail-closed-validator/src/hydra_t6_failclosed/handoff.py",
    "t6-fail-closed-validator/src/hydra_t6_failclosed/models.py",
    "t6-fail-closed-validator/src/hydra_t6_failclosed/receipt.py",
    "t6-fail-closed-validator/src/hydra_t6_failclosed/service.py",
    "t6-fail-closed-validator/src/hydra_t6_failclosed/dormant_adapter.py",
    "t6-fail-closed-validator/tests/__init__.py",
    "t6-fail-closed-validator/tests/test_authority.py",
    "t6-fail-closed-validator/tests/test_camelcase_smuggling.py",
    "t6-fail-closed-validator/tests/test_documents.py",
    "t6-fail-closed-validator/tests/test_dormant_adapter.py",
    "t6-fail-closed-validator/tests/test_receipt.py",
    ".github/workflows/market-data-pipeline.yml",
    ".github/workflows/sql-data-quality-sample.yml",
    ".github/workflows/aws-market-data-pipeline.yml",
    ".github/workflows/aws-market-data-deploy.yml",
    "aws-market-data-pipeline/README.md",
    "aws-market-data-pipeline/template.json",
    "aws-market-data-pipeline/local_demo.py",
    "aws-market-data-pipeline/fixtures/synthetic_market_events.csv",
    "aws-market-data-pipeline/function/__init__.py",
    "aws-market-data-pipeline/function/app.py",
    "aws-market-data-pipeline/function/processor.py",
    "aws-market-data-pipeline/tests/__init__.py",
    "aws-market-data-pipeline/tests/test_processor.py",
    "aws-market-data-pipeline/tests/test_lambda_handler.py",
    "aws-market-data-pipeline/tests/test_template.py",
    "sql-data-quality-sample/README.md",
    "sql-data-quality-sample/fixtures/synthetic_market_events.csv",
    "sql-data-quality-sample/sql/01_schema.sql",
    "sql-data-quality-sample/sql/02_quality.sql",
    "sql-data-quality-sample/sql/03_analytics.sql",
    "sql-data-quality-sample/run_demo.py",
    "sql-data-quality-sample/tests/__init__.py",
    "sql-data-quality-sample/tests/test_sql_sample.py",
    "market-data-pipeline-sample/README.md",
    "market-data-pipeline-sample/pyproject.toml",
    "market-data-pipeline-sample/config/symbol_aliases.json",
    "market-data-pipeline-sample/contracts/input_contract.json",
    "market-data-pipeline-sample/contracts/normalized_event.schema.json",
    "market-data-pipeline-sample/contracts/quarantine_record.schema.json",
    "market-data-pipeline-sample/data/raw/synthetic_market_events.csv",
    "market-data-pipeline-sample/src/hydra_market_pipeline/__init__.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/__main__.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/cli.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/hashing.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/models.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/pipeline.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/writers.py",
    "market-data-pipeline-sample/tests/test_contract_files.py",
    "market-data-pipeline-sample/tests/test_pipeline.py",
)

FORBIDDEN_ACTIVE_PATHS = (
    "t6-fail-closed-validator/src/hydra_t6_failclosed/thread_f_adapter.py",
)

STALE_PUBLIC_PHRASES = (
    "market intelligence data platform",
    "ai-driven quantitative trading",
    "github=unbound",
    "repo/readme.md",
    "thread f",
    "thread_f",
    "cross-thread",
)

MARKDOWN_LINK = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")


def clean_reference(reference: str) -> str:
    value = reference.strip().strip("'\"")
    if value.startswith("<") and ">" in value:
        value = value[1 : value.index(">")]
    elif re.search(r"\s+[\"']", value):
        value = re.split(r"\s+[\"']", value, maxsplit=1)[0]
    return value.strip()


def local_target(source: Path, reference: str) -> Path | None:
    reference = clean_reference(reference)
    if not reference or reference.startswith(("#", "//")):
        return None

    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc:
        return None

    path_text = unquote(parsed.path)
    if not path_text:
        return None

    if path_text.startswith("/"):
        return (ROOT / path_text.lstrip("/")).resolve()
    return (source.parent / path_text).resolve()


def validate_required_paths(errors: list[str]) -> None:
    for relative in REQUIRED_PATHS:
        if not (ROOT / relative).exists():
            errors.append(f"required public path missing: {relative}")

    for relative in FORBIDDEN_ACTIVE_PATHS:
        if (ROOT / relative).exists():
            errors.append(f"retired internal path returned to active tree: {relative}")


def active_public_text_files() -> list[Path]:
    files = [ROOT / "README.md", COMPONENT / "README.md", COMPONENT / "pyproject.toml"]
    files.extend((COMPONENT / "src").rglob("*.py"))
    files.extend((COMPONENT / "tests").rglob("*.py"))
    files.extend([PIPELINE / "README.md", PIPELINE / "pyproject.toml"])
    files.extend((PIPELINE / "src").rglob("*.py"))
    files.extend((PIPELINE / "tests").rglob("*.py"))
    files.extend([SQL_SAMPLE / "README.md", SQL_SAMPLE / "run_demo.py"])
    files.extend((SQL_SAMPLE / "tests").rglob("*.py"))
    files.extend((SQL_SAMPLE / "sql").rglob("*.sql"))
    files.extend(
        path
        for path in AWS_SAMPLE.rglob("*")
        if path.suffix.casefold() in {".csv", ".json", ".md", ".py"}
    )
    return sorted(path for path in files if path.is_file())


def validate_public_language(errors: list[str]) -> None:
    for path in active_public_text_files():
        text = path.read_text(encoding="utf-8-sig").casefold()
        relative = path.relative_to(ROOT).as_posix()
        for phrase in STALE_PUBLIC_PHRASES:
            if phrase.casefold() in text:
                errors.append(f"stale/internal public phrase {phrase!r} in {relative}")


def validate_markdown_links(errors: list[str]) -> None:
    markdown_files = [
        path
        for path in ROOT.rglob("*.md")
        if "archive" not in path.relative_to(ROOT).parts
    ]
    for path in sorted(markdown_files):
        text = path.read_text(encoding="utf-8-sig")
        for match in MARKDOWN_LINK.finditer(text):
            reference = match.group(1)
            target = local_target(path, reference)
            if target is not None and not target.exists():
                errors.append(
                    f"broken Markdown link: {path.relative_to(ROOT).as_posix()} -> {reference}"
                )


def validate_safety_contract(errors: list[str]) -> None:
    pyproject_path = COMPONENT / "pyproject.toml"
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"unable to parse validator pyproject.toml: {exc}")
        return

    project = data.get("project", {})
    if project.get("requires-python") != ">=3.11":
        errors.append("validator requires-python must remain exactly '>=3.11'")

    hydra = data.get("tool", {}).get("hydra", {})
    expected = {
        "activation": "prohibited",
        "external-effects": False,
        "canonical-promotion": False,
        "candidate-ranking": False,
    }
    for key, expected_value in expected.items():
        actual = hydra.get(key)
        if actual != expected_value:
            errors.append(
                f"fail-closed pyproject contract changed: tool.hydra.{key}={actual!r}; "
                f"expected {expected_value!r}"
            )


def validate_ci_contract(errors: list[str]) -> None:
    validator_workflow = (ROOT / ".github/workflows/t6-validator.yml").read_text(
        encoding="utf-8-sig"
    )
    validator_fragments = (
        'python-version: "3.11"',
        "python -m unittest discover -s tests -t . -v",
        "working-directory: t6-fail-closed-validator",
    )
    for fragment in validator_fragments:
        if fragment not in validator_workflow:
            errors.append(f"validator CI contract missing: {fragment}")

    pipeline_workflow = (ROOT / ".github/workflows/market-data-pipeline.yml").read_text(
        encoding="utf-8-sig"
    )
    pipeline_fragments = (
        'python-version: "3.11"',
        "PYTHONPATH: src",
        "python -m unittest discover -s tests -t . -v",
        "--output-dir build/demo",
        "actions/upload-artifact@v4",
    )
    for fragment in pipeline_fragments:
        if fragment not in pipeline_workflow:
            errors.append(f"market-pipeline CI contract missing: {fragment}")

    sql_workflow = (ROOT / ".github/workflows/sql-data-quality-sample.yml").read_text(
        encoding="utf-8-sig"
    )
    sql_fragments = (
        'python-version: "3.11"',
        "python -m unittest discover -s tests -v",
        "python run_demo.py",
        "SQL_SAMPLE_SUMMARY=PASS",
    )
    for fragment in sql_fragments:
        if fragment not in sql_workflow:
            errors.append(f"sql-sample CI contract missing: {fragment}")

    aws_workflow = (ROOT / ".github/workflows/aws-market-data-pipeline.yml").read_text(
        encoding="utf-8-sig"
    )
    aws_fragments = (
        'python-version: "3.11"',
        "aws-actions/setup-sam@v3",
        "sam validate --lint --template-file template.json",
        "python -m unittest discover -s tests -t . -v",
        "python local_demo.py --output-dir build/local",
        "AWS_SAMPLE_MANIFEST=PASS",
        "actions/upload-artifact@v4",
    )
    for fragment in aws_fragments:
        if fragment not in aws_workflow:
            errors.append(f"aws-sample CI contract missing: {fragment}")

    deploy_workflow = (ROOT / ".github/workflows/aws-market-data-deploy.yml").read_text(
        encoding="utf-8-sig"
    )
    deploy_fragments = (
        "workflow_dispatch:",
        "id-token: write",
        "AWS_DEMO_ROLE_ARN",
        "mask-aws-account-id: true",
        "sam deploy",
        "deployed_outputs_match_local_replay",
        "start-query-execution",
        "inputs.teardown",
        "sam delete",
    )
    for fragment in deploy_fragments:
        if fragment not in deploy_workflow:
            errors.append(f"aws-deploy workflow contract missing: {fragment}")
    if re.search(r"(?m)^  (?:pull_request|push):", deploy_workflow):
        errors.append("aws-deploy workflow must remain manual-only")


def validate_aws_template_contract(errors: list[str]) -> None:
    template_path = AWS_SAMPLE / "template.json"
    try:
        template = json.loads(template_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"unable to parse AWS template.json: {exc}")
        return

    resources = template.get("Resources", {})
    expected = {
        "RawBucket": "AWS::S3::Bucket",
        "CuratedBucket": "AWS::S3::Bucket",
        "TransformFunction": "AWS::Serverless::Function",
        "DataCatalogDatabase": "AWS::Glue::Database",
        "NormalizedEventsTable": "AWS::Glue::Table",
        "AthenaWorkGroup": "AWS::Athena::WorkGroup",
    }
    for name, resource_type in expected.items():
        actual = resources.get(name, {}).get("Type")
        if actual != resource_type:
            errors.append(
                f"AWS template resource contract changed: {name}={actual!r}; "
                f"expected {resource_type!r}"
            )


def main() -> int:
    errors: list[str] = []

    validate_required_paths(errors)
    validate_public_language(errors)
    validate_markdown_links(errors)
    validate_safety_contract(errors)
    validate_ci_contract(errors)
    validate_aws_template_contract(errors)

    if errors:
        print("PUBLIC_REPOSITORY_VALIDATION=FAIL")
        for error in sorted(set(errors)):
            print(f"ERROR: {error}")
        return 1

    print("PUBLIC_REPOSITORY_VALIDATION=PASS")
    print(f"REQUIRED_PATHS={len(REQUIRED_PATHS)}")
    print(f"PUBLIC_TEXT_FILES={len(active_public_text_files())}")
    print("FAIL_CLOSED_CONTRACT=PASS")
    print("MARKDOWN_LINKS=PASS")
    print("VALIDATOR_CI_CONTRACT=PASS")
    print("MARKET_PIPELINE_CI_CONTRACT=PASS")
    print("SQL_SAMPLE_CI_CONTRACT=PASS")
    print("AWS_SAMPLE_CI_CONTRACT=PASS")
    print("AWS_DEPLOY_WORKFLOW_CONTRACT=PASS")
    print("AWS_TEMPLATE_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
