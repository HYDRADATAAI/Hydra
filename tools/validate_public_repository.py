#!/usr/bin/env python3
"""Validate HYDRA's recruiter-facing core repository contract."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "t6-fail-closed-validator"
PIPELINE = ROOT / "market-data-pipeline-sample"
SQL_SAMPLE = ROOT / "sql-data-quality-sample"

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


def main() -> int:
    errors: list[str] = []

    validate_required_paths(errors)
    validate_public_language(errors)
    validate_markdown_links(errors)
    validate_safety_contract(errors)
    validate_ci_contract(errors)

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
