#!/usr/bin/env python3
"""Validate HYDRA's recruiter-facing core repository contract."""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "t6-fail-closed-validator"
PIPELINE = ROOT / "market-data-pipeline-sample"
SQL_SAMPLE = ROOT / "sql-data-quality-sample"
AWS_SAMPLE = ROOT / "aws-market-data-pipeline"
INTELLIGENCE_SAMPLE = ROOT / "governed-intelligence-sample"

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
    ".github/workflows/governed-intelligence-sample.yml",
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
    "aws-market-data-pipeline/tests/test_athena_query_results.py",
    "aws-market-data-pipeline/verify_athena_query_results.py",
    "aws-market-data-pipeline/sql/create_committed_normalized_events.sql",
    "tools/test_aws_deploy_validator_contract.py",
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
    "market-data-pipeline-sample/config/backfill_plan.json",
    "market-data-pipeline-sample/contracts/backfill_plan.schema.json",
    "market-data-pipeline-sample/contracts/input_contract.json",
    "market-data-pipeline-sample/contracts/pipeline_manifest.schema.json",
    "market-data-pipeline-sample/contracts/normalized_event.schema.json",
    "market-data-pipeline-sample/contracts/quarantine_record.schema.json",
    "market-data-pipeline-sample/data/raw/synthetic_market_events.csv",
    "market-data-pipeline-sample/data/raw/synthetic_market_events_day2.csv",
    "market-data-pipeline-sample/src/hydra_market_pipeline/__init__.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/__main__.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/cli.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/hashing.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/models.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/operations.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/operations_cli.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/pipeline.py",
    "market-data-pipeline-sample/src/hydra_market_pipeline/writers.py",
    "market-data-pipeline-sample/tests/test_contract_files.py",
    "market-data-pipeline-sample/tests/test_pipeline.py",
    "market-data-pipeline-sample/tests/test_operations.py",
    "market-data-pipeline-sample/run_recovery_demo.py",
    "governed-intelligence-sample/README.md",
    "governed-intelligence-sample/pyproject.toml",
    "governed-intelligence-sample/config/policy.json",
    "governed-intelligence-sample/config/retrieval_policy.json",
    "governed-intelligence-sample/config/grounding_policy.json",
    "governed-intelligence-sample/contracts/request.schema.json",
    "governed-intelligence-sample/contracts/decision.schema.json",
    "governed-intelligence-sample/fixtures/evaluation_cases.json",
    "governed-intelligence-sample/fixtures/retrieval_cases.json",
    "governed-intelligence-sample/fixtures/retrieval_qrels.json",
    "governed-intelligence-sample/fixtures/grounding_cases.json",
    "governed-intelligence-sample/run_demo.py",
    "governed-intelligence-sample/run_retrieval_demo.py",
    "governed-intelligence-sample/run_grounding_demo.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/__init__.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/__main__.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/cli.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/context.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/evaluation.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/grounding.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/grounding_cli.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/pre_upload_verifier.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/pipeline_replay.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/retrieval.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/retrieval_cli.py",
    "governed-intelligence-sample/src/hydra_governed_intelligence/retrieval_evaluation.py",
    "governed-intelligence-sample/tests/__init__.py",
    "governed-intelligence-sample/tests/support.py",
    "governed-intelligence-sample/tests/test_context.py",
    "governed-intelligence-sample/tests/test_evaluation.py",
    "governed-intelligence-sample/tests/test_grounding.py",
    "governed-intelligence-sample/tests/test_pre_upload_verifier.py",
    "governed-intelligence-sample/tests/test_retrieval.py",
    "governed-intelligence-sample/tests/test_retrieval_evaluation.py",
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
        target = (ROOT / path_text.lstrip("/")).resolve()
    else:
        target = (source.parent / path_text).resolve()
    if not target.is_relative_to(ROOT):
        return ROOT / ".invalid-outside-repository-link"
    return target


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
    files.extend(
        [INTELLIGENCE_SAMPLE / "README.md", INTELLIGENCE_SAMPLE / "pyproject.toml"]
    )
    files.extend((INTELLIGENCE_SAMPLE / "src").rglob("*.py"))
    files.extend((INTELLIGENCE_SAMPLE / "tests").rglob("*.py"))
    files.extend((INTELLIGENCE_SAMPLE / "config").rglob("*.json"))
    files.extend((INTELLIGENCE_SAMPLE / "contracts").rglob("*.json"))
    files.extend((INTELLIGENCE_SAMPLE / "fixtures").rglob("*.json"))
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

    intelligence_pyproject = INTELLIGENCE_SAMPLE / "pyproject.toml"
    try:
        intelligence_data = tomllib.loads(
            intelligence_pyproject.read_text(encoding="utf-8-sig")
        )
    except (OSError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"unable to parse governed-intelligence pyproject.toml: {exc}")
        return

    intelligence_project = intelligence_data.get("project", {})
    if intelligence_project.get("requires-python") != ">=3.11":
        errors.append(
            "governed-intelligence requires-python must remain exactly '>=3.11'"
        )
    intelligence_hydra = intelligence_data.get("tool", {}).get("hydra", {})
    intelligence_expected = {
        "data-boundary": "synthetic-non-live",
        "model-execution": False,
        "external-effects": False,
    }
    for key, expected_value in intelligence_expected.items():
        actual = intelligence_hydra.get(key)
        if actual != expected_value:
            errors.append(
                f"governed-intelligence safety contract changed: tool.hydra.{key}={actual!r}; "
                f"expected {expected_value!r}"
            )

    policy_paths = {
        "context": INTELLIGENCE_SAMPLE / "config/policy.json",
        "retrieval": INTELLIGENCE_SAMPLE / "config/retrieval_policy.json",
        "grounding": INTELLIGENCE_SAMPLE / "config/grounding_policy.json",
    }
    policies = {}
    for name, path in policy_paths.items():
        try:
            policies[name] = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"unable to parse governed-{name} policy: {exc}")
            return
    expected_context_policy = {
        "abstained_tasks": ["production_metric"],
        "allowed_tasks": ["accepted_observation_summary", "quality_status"],
        "max_context_records": 2,
        "model_execution_enabled": False,
        "refused_tasks": ["trading_instruction"],
        "schema_version": "hydra-governed-intelligence-policy/v1",
    }
    if policies["context"] != expected_context_policy:
        errors.append("governed-context policy contract changed")

    expected_retrieval_policy = {
        "field_weights": {
            "currency": 2,
            "source_system": 3,
            "symbol": 8,
            "venue": 4,
        },
        "max_results": 3,
        "min_score": 8,
        "model_execution_enabled": False,
        "non_scoring_terms": ["observation"],
        "prohibited_terms": [
            "quarantine",
            "quarantined",
            "raw",
            "reject",
            "rejected",
            "rejection",
            "rejections",
        ],
        "schema_version": "hydra-governed-retrieval-policy/v2",
    }
    if policies["retrieval"] != expected_retrieval_policy:
        errors.append("governed-retrieval policy contract changed")

    expected_grounding_policy = {
        "allowed_claim_fields": [
            "currency",
            "event_time_utc",
            "price",
            "source_system",
            "symbol",
            "venue",
            "volume",
        ],
        "external_actions_enabled": False,
        "max_claims": 5,
        "min_claim_failures": 1,
        "min_claim_passes": 1,
        "model_execution_enabled": False,
        "required_case_ids": [
            "disallowed-field-is-quarantined",
            "execution-and-action-claims-are-quarantined",
            "invented-value-is-quarantined",
            "missing-retrieval-evidence-abstains",
            "outside-context-record-is-quarantined",
            "restricted-retrieval-request-refuses",
            "tampered-citation-is-quarantined",
            "valid-claims-are-admitted",
        ],
        "required_dispositions": ["ABSTAIN", "ADMIT", "QUARANTINE", "REFUSE"],
        "schema_version": "hydra-grounding-policy/v2",
    }
    if policies["grounding"] != expected_grounding_policy:
        errors.append("grounding policy contract changed")

    try:
        retrieval_suite = json.loads(
            (INTELLIGENCE_SAMPLE / "fixtures/retrieval_cases.json").read_text(
                encoding="utf-8-sig"
            )
        )
        retrieval_qrels = json.loads(
            (INTELLIGENCE_SAMPLE / "fixtures/retrieval_qrels.json").read_text(
                encoding="utf-8-sig"
            )
        )
        grounding_suite = json.loads(
            (INTELLIGENCE_SAMPLE / "fixtures/grounding_cases.json").read_text(
                encoding="utf-8-sig"
            )
        )
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"unable to parse governed-retrieval fixtures: {exc}")
        return
    if retrieval_suite.get("schema_version") != "hydra-governed-retrieval-evaluation-suite/v3":
        errors.append("governed-retrieval suite must remain schema v3")
    if retrieval_qrels.get("schema_version") != "hydra-governed-retrieval-qrels/v1":
        errors.append("governed-retrieval qrels must remain schema v1")
    case_ids = {case.get("case_id") for case in retrieval_suite.get("cases", [])}
    expected_retrieval_case_ids = {
        "accepted-aaa-ranks-first",
        "accepted-bbb-ranks-first",
        "accepted-eee-ranks-first",
        "currency-only-quality-miss",
        "non-ascii-confusable-request-refuses",
        "quarantined-symbol-cannot-borrow-metadata-score",
        "quarantined-symbol-is-not-retrievable",
        "restricted-corpus-request-refuses",
        "restricted-synonym-request-refuses",
        "shared-source-bounded-recall",
        "unknown-symbol-abstains",
        "unknown-symbol-cannot-borrow-metadata-score",
        "venue-only-quality-miss",
    }
    required_cases = {
        "unknown-symbol-cannot-borrow-metadata-score",
        "quarantined-symbol-cannot-borrow-metadata-score",
        "restricted-synonym-request-refuses",
        "non-ascii-confusable-request-refuses",
    }
    if not required_cases.issubset(case_ids):
        errors.append("governed-retrieval suite lost adversarial controls")
    if case_ids != expected_retrieval_case_ids:
        errors.append("governed-retrieval case identities changed")
    retrieval_cases = retrieval_suite.get("cases", [])
    if len(retrieval_cases) != 13 or len(case_ids) != 13:
        errors.append("governed-retrieval suite must contain 13 unique cases")
    expected_retrieval_counts = {"ABSTAIN": 6, "ADMIT": 4, "REFUSE": 3}
    actual_retrieval_counts = {
        disposition: sum(
            case.get("expected", {}).get("disposition") == disposition
            for case in retrieval_cases
        )
        for disposition in expected_retrieval_counts
    }
    if actual_retrieval_counts != expected_retrieval_counts:
        errors.append("governed-retrieval disposition contract changed")
    expected_groups = {"HARD_NEGATIVE": 4, "QUALITY": 6, "SAFETY_CONTROL": 3}
    actual_groups = {
        group: sum(case.get("metric_group") == group for case in retrieval_cases)
        for group in expected_groups
    }
    if actual_groups != expected_groups:
        errors.append("governed-retrieval metric groups changed")
    judgments = retrieval_qrels.get("judgments", [])
    qrel_case_ids = {item.get("case_id") for item in judgments}
    quality_case_ids = {
        case.get("case_id")
        for case in retrieval_cases
        if case.get("metric_group") == "QUALITY"
    }
    relevant_record_count = sum(
        len(item.get("relevant_record_ids", [])) for item in judgments
    )
    if len(judgments) != 6 or qrel_case_ids != quality_case_ids:
        errors.append("governed-retrieval qrels must match all six quality cases")
    if relevant_record_count != 9:
        errors.append("governed-retrieval qrels must contain nine relevance judgments")
    expected_qrel_case_ids = {
        "accepted-aaa-ranks-first",
        "accepted-bbb-ranks-first",
        "accepted-eee-ranks-first",
        "currency-only-quality-miss",
        "shared-source-bounded-recall",
        "venue-only-quality-miss",
    }
    if qrel_case_ids != expected_qrel_case_ids:
        errors.append("governed-retrieval qrels case identities changed")
    expected_corpus_binding = {
        "normalized_events_sha256": "ec902bc92942197ddceb737b90421f36298b660c0788c99ac4c18b2e1c570e86",
        "pipeline_manifest_sha256": "f3b5ea4b854b862ec24670ad7cd0471858f283e8f474c53d208cf2570528509c",
        "record_ids": [
            "0dc3a510144754af42f61cf3a72f51fcbf90aed765d28053032e8fb857946458",
            "5661c842227f80f2866a673d1e09c092fb7de3a2c3663eaa3f018953d0aa516c",
            "5dce66c1857f0ebbdfad7a907e8ee839592f303dd768cb238aff06112f3bd271",
        ],
    }
    if retrieval_qrels.get("corpus_binding") != expected_corpus_binding:
        errors.append("governed-retrieval qrels corpus binding changed")

    grounding_cases = grounding_suite.get("cases", [])
    grounding_case_ids = {case.get("case_id") for case in grounding_cases}
    expected_grounding_case_ids = {
        "disallowed-field-is-quarantined",
        "execution-and-action-claims-are-quarantined",
        "invented-value-is-quarantined",
        "missing-retrieval-evidence-abstains",
        "outside-context-record-is-quarantined",
        "restricted-retrieval-request-refuses",
        "tampered-citation-is-quarantined",
        "valid-claims-are-admitted",
    }
    if grounding_suite.get("schema_version") != "hydra-grounding-evaluation-suite/v1":
        errors.append("grounding suite must remain schema v1")
    if grounding_case_ids != expected_grounding_case_ids:
        errors.append("grounding threat-case identities changed")
    required_grounding_ids = policies["grounding"].get("required_case_ids", [])
    if required_grounding_ids != sorted(expected_grounding_case_ids):
        errors.append("grounding policy required threat-case identities changed")
    if required_grounding_ids != sorted(set(required_grounding_ids)):
        errors.append("grounding policy required_case_ids must be sorted and unique")
    if len(grounding_cases) != 8 or grounding_case_ids != set(required_grounding_ids):
        errors.append("grounding suite must match all eight policy-bound threat cases")
    expected_grounding_counts = {
        "ABSTAIN": 1,
        "ADMIT": 1,
        "QUARANTINE": 5,
        "REFUSE": 1,
    }
    actual_grounding_counts = {
        disposition: sum(
            case.get("expected", {}).get("disposition") == disposition
            for case in grounding_cases
        )
        for disposition in expected_grounding_counts
    }
    if actual_grounding_counts != expected_grounding_counts:
        errors.append("grounding suite disposition contract changed")


def workflow_job_block(workflow: str, job_name: str) -> str | None:
    match = re.search(
        rf"(?ms)^  {re.escape(job_name)}:\s*\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\s*(?:#.*)?$|\Z)",
        workflow,
    )
    return None if match is None else match.group("body")


def workflow_event_is_unfiltered(workflow: str, event_name: str) -> bool:
    matches = list(
        re.finditer(
            rf"(?m)^  {re.escape(event_name)}:(?P<inline>[^\r\n]*)$",
            workflow,
        )
    )
    if len(matches) != 1:
        return False

    match = matches[0]
    inline = match.group("inline").split("#", maxsplit=1)[0].strip()
    if inline not in {"", "{}"}:
        return False

    next_event = re.search(
        r"(?m)^  [A-Za-z0-9_-]+:\s*(?:#.*)?$", workflow[match.end() :]
    )
    body_end = match.end() + next_event.start() if next_event else len(workflow)
    body = workflow[match.end() : body_end]
    return not any(
        line.strip() and not line.lstrip().startswith("#")
        for line in body.splitlines()
    )


def workflow_steps(job_block: str) -> list[tuple[str | None, str]]:
    starts = list(
        re.finditer(
            r"(?m)^      -(?=\s|$)",
            job_block,
        )
    )
    steps: list[tuple[str | None, str]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(job_block)
        block = job_block[match.start() : end]
        name_match = re.search(
            r"(?m)^      -\s+name:\s*([^\r\n#]+?)\s*(?:#.*)?$",
            block,
        )
        name = (
            None
            if name_match is None
            else name_match.group(1).strip().strip("'\"")
        )
        steps.append((name, block))
    return steps


def workflow_step_scalar(step_block: str, key: str) -> list[str]:
    values = re.findall(
        rf"(?m)^        {re.escape(key)}:\s*([^\r\n#]*?)\s*(?:#.*)?$",
        step_block,
    )
    return [_workflow_scalar_value(value) for value in values]


def workflow_step_with_scalar(step_block: str, key: str) -> list[str]:
    values = re.findall(
        rf"(?m)^          {re.escape(key)}:\s*([^\r\n#]*?)\s*(?:#.*)?$",
        step_block,
    )
    return [_workflow_scalar_value(value) for value in values]


def _workflow_scalar_value(value: str) -> str:
    result = value.strip()
    if len(result) >= 2 and result[0] == result[-1] and result[0] in "'\"":
        return result[1:-1]
    return result


def workflow_step_literal_lines(step_block: str, key: str) -> list[str] | None:
    match = re.search(
        rf"(?m)^          {re.escape(key)}:\s*\|\s*\r?\n"
        r"(?P<body>(?:^            [^\r\n]*(?:\r?\n|\Z))+)",
        step_block,
    )
    if match is None:
        return None
    return [
        line.strip()
        for line in match.group("body").splitlines()
        if line.strip()
    ]


def workflow_step_run_lines(step_block: str) -> list[str] | None:
    match = re.search(r"(?m)^        run:\s*\|\s*\r?\n", step_block)
    if match is None:
        return None
    lines: list[str] = []
    for line in step_block[match.end() :].splitlines():
        if not line.strip():
            continue
        if not line.startswith("          "):
            return None
        lines.append(line.strip())
    return lines


def validate_pre_upload_verifier_contract(errors: list[str]) -> None:
    source_path = (
        INTELLIGENCE_SAMPLE
        / "src"
        / "hydra_governed_intelligence"
        / "pre_upload_verifier.py"
    )
    test_path = INTELLIGENCE_SAMPLE / "tests" / "test_pre_upload_verifier.py"
    try:
        source = source_path.read_text(encoding="utf-8-sig")
        source_tree = ast.parse(source, filename=str(source_path))
        test_tree = ast.parse(
            test_path.read_text(encoding="utf-8-sig"),
            filename=str(test_path),
        )
    except (OSError, SyntaxError) as exc:
        errors.append(f"unable to parse pre-upload verifier contract: {exc}")
        return

    functions = {
        node.name: node
        for node in source_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    required_functions = {
        "_build_bundle_bytes",
        "_materialize_snapshots",
        "_open_bound_parent",
        "_publish_bundle",
        "_read_bound_file",
        "_require_bound_directory_path",
        "_require_safe_bound_destination",
        "_snapshot_file",
        "_snapshot_verification_inputs",
        "_verify_bundle",
        "_verify_manifest",
        "_verify_report",
        "_write_github_output",
        "package_repository_artifacts",
        "verify_repository_artifacts",
        "main",
    }
    if not required_functions.issubset(functions):
        errors.append("pre-upload verifier required functions changed")
        return

    assignments = {
        target.id: node.value
        for node in source_tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    expected_bundle_members = (
        "governed-intelligence-sample/build/evaluation/decisions.jsonl",
        "governed-intelligence-sample/build/evaluation/evaluation_report.json",
        "governed-intelligence-sample/build/evaluation/output_manifest.json",
        "governed-intelligence-sample/build/grounding/grounding_evaluation_report.json",
        "governed-intelligence-sample/build/grounding/grounding_output_manifest.json",
        "governed-intelligence-sample/build/grounding/grounding_receipts.jsonl",
        "governed-intelligence-sample/build/retrieval/retrieval_decisions.jsonl",
        "governed-intelligence-sample/build/retrieval/retrieval_evaluation_report.json",
        "governed-intelligence-sample/build/retrieval/retrieval_output_manifest.json",
        "market-data-pipeline-sample/build/demo/manifest.json",
        "market-data-pipeline-sample/build/demo/normalized_events.csv",
        "market-data-pipeline-sample/build/demo/normalized_events.jsonl",
        "market-data-pipeline-sample/build/demo/quarantine_records.jsonl",
        "market-data-pipeline-sample/build/demo/resolved_symbol_aliases.json",
        "market-data-pipeline-sample/build/demo/source_snapshot.csv",
    )
    expected_support_files = (
        "governed-intelligence-sample/config/grounding_policy.json",
        "governed-intelligence-sample/config/policy.json",
        "governed-intelligence-sample/config/retrieval_policy.json",
        "governed-intelligence-sample/fixtures/evaluation_cases.json",
        "governed-intelligence-sample/fixtures/grounding_cases.json",
        "governed-intelligence-sample/fixtures/retrieval_cases.json",
        "governed-intelligence-sample/fixtures/retrieval_qrels.json",
    )
    try:
        actual_bundle_members = ast.literal_eval(assignments["BUNDLE_MEMBERS"])
    except (KeyError, ValueError, TypeError):
        actual_bundle_members = None
    if actual_bundle_members != expected_bundle_members:
        errors.append("pre-upload deterministic bundle member contract changed")
    try:
        actual_support_files = ast.literal_eval(
            assignments["VERIFICATION_SUPPORT_FILES"]
        )
    except (KeyError, ValueError, TypeError):
        actual_support_files = None
    if actual_support_files != expected_support_files:
        errors.append("pre-upload verification support-file contract changed")

    verification_calls = [
        node.func.id
        for node in ast.walk(functions["verify_repository_artifacts"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    expected_call_counts = {
        "_verify_manifest": 4,
        "_verify_report": 3,
        "_verify_domain_receipt": 3,
        "load_evidence": 1,
        "load_grounding_policy": 1,
        "load_policy": 1,
        "load_retrieval_policy": 1,
    }
    for name, expected_count in expected_call_counts.items():
        if verification_calls.count(name) != expected_count:
            errors.append(
                "pre-upload verifier active call contract changed: "
                f"{name}={verification_calls.count(name)}"
            )

    package_calls = [
        node.func.id
        for node in ast.walk(functions["package_repository_artifacts"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    expected_package_calls = {
        "_build_bundle_bytes": 1,
        "_materialize_snapshots": 1,
        "_publish_bundle": 1,
        "_snapshot_verification_inputs": 1,
        "_verify_bundle": 1,
        "verify_repository_artifacts": 1,
    }
    for name, expected_count in expected_package_calls.items():
        if package_calls.count(name) != expected_count:
            errors.append(
                "pre-upload package call contract changed: "
                f"{name}={package_calls.count(name)}"
            )

    main_calls = [
        node.func.id
        for node in ast.walk(functions["main"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    if main_calls.count("package_repository_artifacts") != 1:
        errors.append("pre-upload packager main entry point became inactive")
    if main_calls.count("_write_github_output") != 1:
        errors.append("pre-upload GitHub output call shape changed")

    required_source_fragments = (
        "manifest_outputs == 9",
        "receipt_count == 26",
        "input_snapshots_verified == 2",
        "source_rows_replayed == 7",
        '"hydra-market-pipeline-manifest/v2"',
        '"hydra-market-source-csv/v1"',
        '"hydra-market-resolved-aliases/v1"',
        '"micro_recall_at_k": "0.444444"',
        '"macro_recall_at_k": "0.583333"',
        '"mean_reciprocal_rank": "0.666667"',
        '"proof_coverage_status": "PASS"',
        'print("PRE_UPLOAD_ARTIFACT_VERIFICATION=PASS")',
        'print(f"MANIFEST_OUTPUTS_VERIFIED={summary.manifest_outputs}")',
        'print(f"RECEIPTS_VERIFIED={summary.receipts}")',
        "BUNDLE_MEMBERS = (",
        "ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)",
        "ZIP_EXTERNAL_ATTR = (stat.S_IFREG | 0o644) << 16",
        "compression=zipfile.ZIP_STORED",
        "allowZip64=False",
        'getattr(os, "O_NOFOLLOW", 0)',
        "os.path.samestat(path_before, descriptor_before)",
        "os.path.samestat(descriptor_before, descriptor_after)",
        "os.path.samestat(descriptor_after, path_after)",
        "NtSetInformationFile",
        "src_dir_fd=parent_handle",
        "dst_dir_fd=parent_handle",
        '"--github-output-path"',
        'f"input_snapshots_verified={summary.input_snapshots_verified}\\n"',
        'f"source_rows_replayed={summary.source_rows_replayed}\\n"',
        'print(f"INPUT_SNAPSHOTS_VERIFIED={summary.input_snapshots_verified}")',
        'print(f"SOURCE_ROWS_REPLAYED={summary.source_rows_replayed}")',
        'print(f"BUNDLE_MEMBERS={summary.bundle_members}")',
        'print(f"BUNDLE_BYTES={summary.bundle_bytes}")',
        'print(f"BUNDLE_SHA256={summary.bundle_sha256}")',
    )
    for fragment in required_source_fragments:
        if fragment not in source:
            errors.append(f"pre-upload verifier contract missing: {fragment}")

    test_methods = {
        node.name
        for node in ast.walk(test_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    required_tests = {
        "test_complete_artifact_set_passes",
        "test_deterministic_bundle_is_byte_identical",
        "test_bundle_member_metadata_and_payloads_are_exact",
        "test_bundle_payload_tampering_fails",
        "test_bundle_metadata_tampering_fails",
        "test_packaging_failure_leaves_no_bundle_or_temporary_file",
        "test_failed_replacement_preserves_existing_bundle",
        "test_successful_replacement_overwrites_existing_bundle",
        "test_failed_atomic_rename_removes_temporary_bundle",
        "test_publish_bundle_rejects_linked_ancestor_without_external_artifact",
        "test_linked_ancestor_cannot_create_external_parent",
        "test_ancestor_swap_during_temporary_creation_cannot_redirect_bundle",
        "test_snapshot_rejects_file_replaced_between_lstat_and_open",
        "test_snapshot_rejects_descriptor_identity_change_after_read",
        "test_snapshot_rejects_descriptor_type_change_after_read",
        "test_snapshot_open_uses_no_follow_when_available",
        "test_cli_appends_bundle_digest_to_github_output",
        "test_source_mutation_after_snapshot_does_not_change_bundle",
        "test_manifest_digest_tampering_fails",
        "test_rehashed_qrels_with_stale_retrieval_metrics_fails",
        "test_rehashed_grounding_report_with_stale_claim_totals_fails",
        "test_rehashed_grounding_report_with_stale_dispositions_fails",
        "test_rehashed_receipt_tampering_fails_semantic_verification",
        "test_input_snapshot_digest_tampering_fails",
        "test_manifest_v1_fails_closed",
        "test_manifest_v2_bundle_member_contract",
        "test_manifest_v2_summary_contract",
    }
    if not required_tests.issubset(test_methods):
        errors.append("pre-upload verifier tamper tests changed")


def validate_manifest_v2_replay_contract(errors: list[str]) -> None:
    schema_path = PIPELINE / "contracts" / "pipeline_manifest.schema.json"
    replay_path = (
        INTELLIGENCE_SAMPLE
        / "src"
        / "hydra_governed_intelligence"
        / "pipeline_replay.py"
    )
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
        replay_source = replay_path.read_text(encoding="utf-8-sig")
        replay_tree = ast.parse(replay_source, filename=str(replay_path))
    except (OSError, json.JSONDecodeError, SyntaxError) as exc:
        errors.append(f"unable to parse manifest-v2 replay contract: {exc}")
        return

    required_manifest_fields = {
        "accepted_rows",
        "aliases_sha256",
        "inputs",
        "outputs",
        "pipeline_run_id",
        "quarantined_rows",
        "schema_version",
        "source_file_sha256",
        "source_rows",
        "transform_version",
    }
    properties = schema.get("properties", {})
    inputs = properties.get("inputs", {}).get("properties", {})
    if schema.get("$id") != "hydra-market-pipeline-manifest/v2":
        errors.append("pipeline manifest schema v2 ID changed")
    if set(schema.get("required", [])) != required_manifest_fields:
        errors.append("pipeline manifest schema v2 required fields changed")
    expected_inputs = {
        "resolved_aliases_json": (
            "resolved_symbol_aliases.json",
            "hydra-market-resolved-aliases/v1",
        ),
        "source_csv": ("source_snapshot.csv", "hydra-market-source-csv/v1"),
    }
    if set(inputs) != set(expected_inputs):
        errors.append("pipeline manifest schema v2 input set changed")
    else:
        for key, (filename, schema_version) in expected_inputs.items():
            descriptor = inputs[key].get("properties", {})
            if descriptor.get("file", {}).get("const") != filename:
                errors.append(f"pipeline manifest input filename changed: {key}")
            if descriptor.get("schema_version", {}).get("const") != schema_version:
                errors.append(f"pipeline manifest input schema changed: {key}")

    functions = {
        node.name
        for node in replay_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    required_functions = {
        "replay_pipeline",
        "_load_resolved_aliases",
        "_validate_header",
        "_quarantine_record",
        "_jsonl_bytes",
        "_csv_bytes",
    }
    if not required_functions.issubset(functions):
        errors.append("independent pipeline replay functions changed")
    if "hydra_market_pipeline" in replay_source:
        errors.append("independent pipeline replay must not import producer code")
    replay_fragments = (
        'PIPELINE_MANIFEST_SCHEMA = "hydra-market-pipeline-manifest/v2"',
        'SOURCE_CSV_SCHEMA = "hydra-market-source-csv/v1"',
        'RESOLVED_ALIASES_SCHEMA = "hydra-market-resolved-aliases/v1"',
        "source_rows=source_rows",
        "normalized_jsonl=normalized_jsonl",
        "normalized_csv=normalized_csv",
        "quarantine_jsonl=quarantine_jsonl",
    )
    for fragment in replay_fragments:
        if fragment not in replay_source:
            errors.append(f"independent pipeline replay contract missing: {fragment}")


def workflow_action_refs(workflow_text: str) -> list[str]:
    document = yaml.load(workflow_text, Loader=yaml.BaseLoader)
    jobs = document.get("jobs") if isinstance(document, dict) else None
    if not isinstance(jobs, dict):
        raise ValueError("workflow jobs mapping is missing")
    references = []
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        if isinstance(job.get("uses"), str):
            references.append(job["uses"])
        steps = job.get("steps", [])
        if isinstance(steps, list):
            references.extend(
                step["uses"]
                for step in steps
                if isinstance(step, dict) and isinstance(step.get("uses"), str)
            )
    return references


def workflow_action_ref_is_pinned(action_ref: str) -> bool:
    if action_ref.startswith("./"):
        return True
    if action_ref.startswith("docker://"):
        return re.search(r"@sha256:[0-9a-f]{64}$", action_ref) is not None
    revision = action_ref.rpartition("@")[2]
    return re.fullmatch(r"[0-9a-f]{40}", revision) is not None



def athena_success_commands_are_valid(run_script: object) -> bool:
    """Require active result retrieval and verifier commands in the SUCCEEDED branch."""
    if not isinstance(run_script, str):
        return False

    success = re.search(
        r'(?m)^[ \t]*if \[\[ "\$state" == "SUCCEEDED" \]\]; then[ \t]*    validate_manifest_v2_replay_contract(errors)
    validate_pre_upload_verifier_contract(errors)

    workflow_dir = ROOT / ".github" / "workflows"
    workflow_files = sorted(
        list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
    )
    for workflow_path in workflow_files:
        try:
            action_refs = workflow_action_refs(
                workflow_path.read_text(encoding="utf-8-sig")
            )
        except (OSError, yaml.YAMLError, ValueError) as exc:
            errors.append(
                f"unable to parse workflow actions in "
                f"{workflow_path.relative_to(ROOT)}: {exc}"
            )
            continue
        for action_ref in action_refs:
            if not workflow_action_ref_is_pinned(action_ref):
                errors.append(
                    f"workflow action must use a full commit SHA or image digest: "
                    f"{workflow_path.relative_to(ROOT)}: {action_ref}"
                )
    documentation_contracts = {
        ROOT / "README.md": (
            "15-member deterministic proof package intentionally includes",
            "all 7 rows are synthetic, including rows designed to quarantine",
            "Governed context, retrieval, and receipt artifacts remain accepted-only or aggregate-only",
            "do not expose quarantined row payloads",
        ),
        INTELLIGENCE_SAMPLE / "README.md": (
            "deterministic, uncompressed 15-member ZIP",
            "all 7 synthetic rows, including rows designed to quarantine",
            "canonical `resolved_symbol_aliases.json`",
            "`INPUT_SNAPSHOTS_VERIFIED=2`",
            "`SOURCE_ROWS_REPLAYED=7`",
            "do not expose quarantined row payloads",
        ),
        PIPELINE / "README.md": (
            "15-member proof package intentionally carries the exact source snapshot",
            "all 7 synthetic rows, including rows designed to quarantine",
            "canonical resolved aliases",
            "do not expose quarantined row payloads",
        ),
    }
    for path, fragments in documentation_contracts.items():
        text = path.read_text(encoding="utf-8-sig")
        for fragment in fragments:
            if fragment not in text:
                errors.append(
                    f"manifest-v2 public documentation contract missing: {path.name}: {fragment}"
                )
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
        '"hydra-market-pipeline-manifest/v2"',
        '"resolved_symbol_aliases.json"',
        '"source_snapshot.csv"',
        'print("INPUT_SNAPSHOTS_VERIFIED=2")',
        'print("SOURCE_ROWS_SNAPSHOT_VERIFIED=7")',
        "python run_recovery_demo.py --output-dir build/operations",
        "OPERATIONS_RECEIPT=PASS",
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
        "name: hydra-market-data-pipeline-sample",
        "name: Download published pipeline outputs",
        "name: Verify published pipeline artifact round-trip",
        "PUBLISHED_PIPELINE_ARTIFACT=PASS",
    )
    for fragment in pipeline_fragments:
        if fragment not in pipeline_workflow:
            errors.append(f"market-pipeline CI contract missing: {fragment}")
    pipeline_job = workflow_job_block(pipeline_workflow, "test-and-build")
    if pipeline_job is None:
        errors.append("market-pipeline CI test-and-build job is missing")
    else:
        if re.search(r"(?m)^    if\s*:", pipeline_job):
            errors.append("market-pipeline CI job must be unconditional")
        if re.search(r"(?m)^    continue-on-error\s*:", pipeline_job):
            errors.append("market-pipeline CI job must fail closed")

        pipeline_steps = workflow_steps(pipeline_job)
        artifact_step_names = (
            "Publish synthetic pipeline outputs",
            "Download published pipeline outputs",
            "Verify published pipeline artifact round-trip",
        )
        names = [name for name, _ in pipeline_steps]
        if tuple(names[-3:]) != artifact_step_names or any(
            names.count(name) != 1 for name in artifact_step_names
        ):
            errors.append("market-pipeline CI artifact steps must be unique and ordered last")

        pipeline_action_pins = {
            "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
            "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
            "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
            "actions/download-artifact": "d3f86a106a0bac45b974a628896c90dbdf5c8093",
        }
        for action, expected_sha in pipeline_action_pins.items():
            refs = re.findall(
                rf"(?m)^\s*uses:\s*{re.escape(action)}@([^\s#]+)",
                pipeline_workflow,
            )
            if not refs or any(ref != expected_sha for ref in refs):
                errors.append(f"market-pipeline CI action pin changed: {action}={refs!r}")

        step_blocks = {
            name: [block for step_name, block in pipeline_steps if step_name == name]
            for name in artifact_step_names
        }
        if all(len(step_blocks[name]) == 1 for name in artifact_step_names):
            upload, download, verify = (
                step_blocks[name][0] for name in artifact_step_names
            )
            expected_artifact = "hydra-market-data-pipeline-sample"
            if workflow_step_scalar(upload, "uses") != [
                "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
            ]:
                errors.append("market-pipeline CI upload action changed")
            if workflow_step_with_scalar(upload, "name") != [expected_artifact]:
                errors.append("market-pipeline CI upload artifact name changed")
            expected_paths = [
                "market-data-pipeline-sample/build/demo/",
                "market-data-pipeline-sample/build/operations/",
            ]
            if workflow_step_literal_lines(upload, "path") != expected_paths:
                errors.append("market-pipeline CI upload paths changed")
            if workflow_step_with_scalar(upload, "if-no-files-found") != ["error"]:
                errors.append("market-pipeline CI upload must fail when outputs are missing")
            if workflow_step_scalar(upload, "if") or workflow_step_scalar(
                upload, "continue-on-error"
            ):
                errors.append("market-pipeline CI upload must remain fail-closed")

            if workflow_step_scalar(download, "uses") != [
                "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093"
            ]:
                errors.append("market-pipeline CI download action changed")
            if workflow_step_with_scalar(download, "name") != [expected_artifact]:
                errors.append("market-pipeline CI download artifact name changed")
            if workflow_step_with_scalar(download, "path") != [
                "${{ runner.temp }}/hydra-market-data-pipeline-published"
            ]:
                errors.append("market-pipeline CI download destination changed")
            if workflow_step_scalar(download, "if") or workflow_step_scalar(
                download, "continue-on-error"
            ):
                errors.append("market-pipeline CI download must remain fail-closed")

            if workflow_step_scalar(verify, "if") or workflow_step_scalar(
                verify, "continue-on-error"
            ):
                errors.append("market-pipeline CI artifact verification must remain fail-closed")
            verify_lines = workflow_step_run_lines(verify) or []
            required_verification_lines = (
                "expected_files[f\"{label}/{relative}\"] = path",
                "actual_files[f\"{label}/{relative}\"] = path",
                "missing = sorted(set(expected_files) - set(actual_files))",
                "extra = sorted(set(actual_files) - set(expected_files))",
                "expected = hashlib.sha256(source.read_bytes()).hexdigest()",
                "actual = hashlib.sha256(actual_files[name].read_bytes()).hexdigest()",
                "require(actual == expected, f\"SHA-256 mismatch for {name}\")",
                "print(f\"PUBLISHED_PIPELINE_ARTIFACT=PASS:{len(expected_files)}\")",
                "root_names = {path.name for path in root_entries}",
                "require(root_names == set(source_roots), f\"unexpected artifact root entries: {sorted(root_names)}\")",
                "require(not path.is_symlink() and path.is_dir(), f\"invalid artifact root entry: {path}\")",
            )
            for line in required_verification_lines:
                if line not in verify_lines:
                    errors.append(
                        f"market-pipeline CI artifact verification changed: {line}"
                    )

    if "SOURCE_ROWS_REPLAYED" in pipeline_workflow:
        errors.append("market-pipeline CI must not claim independent source-row replay")

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
        "aws-actions/setup-sam@89ddb14d60e682855e3fea4be85b3c56485de310",
        "sam validate --lint --template-file template.json",
        "python -m unittest discover -s tests -t . -v",
        "python local_demo.py --output-dir build/local",
        "AWS_SAMPLE_MANIFEST=PASS",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
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
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "aws-actions/configure-aws-credentials@e1253824e5c10ff9df46874f81ed3ec929e19cfd",
        "aws-actions/setup-sam@89ddb14d60e682855e3fea4be85b3c56485de310",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "path: aws-market-data-pipeline/build/deployed/deployment_evidence.json",
        "STACK_NAME: ${{ inputs.stack_name }}-${{ github.run_id }}-${{ github.run_attempt }}",
        "if: github.ref == 'refs/heads/main'",
        "hydra-public-market-pipeline-demo-",
        "Validate deployment target",
        "Refuse to modify an existing stack",
        "Refusing to update or delete an existing stack.",
        "id: deploy_stack",
        "inputs.teardown && steps.deploy_stack.outcome != 'skipped'",
        "sam deploy",
        "--query 'Stacks[0].StackStatus'",
        "CREATE_COMPLETE",
        "timeout-minutes: 75",
        "seq 1 360",
        "hydra:deployment-run",
        "stack_owner",
        "ResourceStatus == \"DELETE_FAILED\"",
        "deployed_outputs_match_local_replay",
        "Create manifest-gated Athena consumer view",
        "sql/create_committed_normalized_events.sql",
        "FROM committed_normalized_events",
        "COUNT(*) AS accepted_rows FROM committed_normalized_events",
        '"athena_accepted_rows": int(os.environ["ATHENA_ACCEPTED_ROWS"]),',
        "start-query-execution",
        "--page-size 1000",
        "--max-items 1000",
        '--starting-token "$token"',
        "NextToken",
        "inputs.teardown",
        "sam delete",
    )
    for fragment in deploy_fragments:
        if fragment not in deploy_workflow:
            errors.append(f"aws-deploy workflow contract missing: {fragment}")

    try:
        deploy_document = yaml.load(deploy_workflow, Loader=yaml.BaseLoader)
        deploy_job = deploy_document["jobs"]["deploy-and-verify"]
        athena_steps = [
            step
            for step in deploy_job["steps"]
            if isinstance(step, dict)
            and step.get("name") == "Run bounded Athena verification query"
        ]
        expected_verifier = (
            'python "$SAMPLE_DIR/verify_athena_query_results.py" '
            '--results-path "$SAMPLE_DIR/build/deployed/athena_query_results.json" '
            '--github-env "$GITHUB_ENV"'
        )
        if len(athena_steps) != 1:
            errors.append("aws-deploy Athena verification step count changed")
        else:
            run_script = athena_steps[0].get("run", "")
            if not athena_success_commands_are_valid(run_script):
                errors.append(
                    "aws-deploy Athena success step must run active result retrieval before the row-count verifier"
                )
    except (KeyError, TypeError, yaml.YAMLError, ValueError) as exc:
        errors.append(f"aws-deploy Athena verification step is invalid: {exc}")

    if re.search(r"(?m)^  (?:pull_request|push):", deploy_workflow):
        errors.append("aws-deploy workflow must remain manual-only")

    preflight_position = deploy_workflow.index(
        "- name: Refuse to modify an existing stack"
    )
    deploy_step_position = deploy_workflow.index("id: deploy_stack")
    sam_deploy_position = deploy_workflow.index("sam deploy")
    if not (preflight_position < deploy_step_position < sam_deploy_position):
        errors.append("aws-deploy teardown gate must identify the deploy attempt step")

    deploy_action_pins = {
        "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
        "aws-actions/configure-aws-credentials": "e1253824e5c10ff9df46874f81ed3ec929e19cfd",
        "aws-actions/setup-sam": "89ddb14d60e682855e3fea4be85b3c56485de310",
        "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
    }
    for action, expected_sha in deploy_action_pins.items():
        refs = re.findall(
            rf"(?m)^\s*uses:\s*{re.escape(action)}@([^\s#]+)",
            deploy_workflow,
        )
        if not refs or any(ref != expected_sha for ref in refs):
            errors.append(f"aws-deploy action pin changed: {action}={refs!r}")

    deploy_job = workflow_job_block(deploy_workflow, "deploy-and-verify")
    if deploy_job is None:
        errors.append("aws-deploy job is missing")
    else:
        deploy_steps = workflow_steps(deploy_job)
        publish_steps = [
            block
            for name, block in deploy_steps
            if name == "Publish sanitized deployment evidence"
        ]
        artifact_upload_steps = [
            block
            for _, block in deploy_steps
            if any(
                reference.startswith("actions/upload-artifact@")
                for reference in workflow_step_scalar(block, "uses")
            )
        ]
        if len(artifact_upload_steps) != 1:
            errors.append("aws-deploy must contain exactly one artifact upload")
        if len(publish_steps) != 1:
            errors.append("aws-deploy sanitized evidence upload step count changed")
        else:
            publish_step = publish_steps[0]
            if workflow_step_scalar(publish_step, "uses") != [
                "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
            ]:
                errors.append("aws-deploy evidence upload action changed")
            if workflow_step_with_scalar(publish_step, "path") != [
                "aws-market-data-pipeline/build/deployed/deployment_evidence.json"
            ]:
                errors.append("aws-deploy evidence upload must publish only the sanitized evidence JSON")
            if workflow_step_with_scalar(publish_step, "if-no-files-found") != ["error"]:
                errors.append("aws-deploy evidence upload must fail when evidence is missing")

    intelligence_workflow = (
        ROOT / ".github/workflows/governed-intelligence-sample.yml"
    ).read_text(encoding="utf-8-sig")
    validation_workflow = (
        ROOT / ".github/workflows/public-repository-validation.yml"
    ).read_text(encoding="utf-8-sig")
    for label, workflow in (
        ("governed-intelligence", intelligence_workflow),
        ("public-repository-validation", validation_workflow),
    ):
        if not workflow_event_is_unfiltered(workflow, "pull_request"):
            errors.append(f"{label} CI pull-request trigger must be unfiltered")
    intelligence_fragments = (
        'python-version: "3.11"',
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "working-directory: governed-intelligence-sample",
        "python -m unittest discover -s tests -t . -v",
        "python run_demo.py",
        "GOVERNED_INTELLIGENCE_EVAL=PASS",
        "python run_retrieval_demo.py",
        "--qrels fixtures/retrieval_qrels.json",
        "GOVERNED_RETRIEVAL_EVAL=PASS",
        "python run_grounding_demo.py",
        "GOVERNED_GROUNDING_EVAL=PASS",
        "build/grounding/",
        "timeout-minutes: 15",
        "persist-credentials: false",
        "mkdir -p governed-intelligence-sample/build/upload",
        "python -I -B governed-intelligence-sample/src/hydra_governed_intelligence/pre_upload_verifier.py --repository-root . --bundle-path governed-intelligence-sample/build/upload/hydra-governed-intelligence-proof.zip --github-output-path \"$GITHUB_OUTPUT\"",
        '"case_count"], 13',
        '"micro_recall_at_k": "0.444444"',
        '"case_count"], 8',
        '"proof_coverage_status": "PASS"',
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
        "compression-level: 0",
        "EXPECTED_BUNDLE_SHA256: ${{ steps.package_artifacts.outputs.bundle_sha256 }}",
        "EXPECTED_INPUT_SNAPSHOTS_VERIFIED: ${{ steps.package_artifacts.outputs.input_snapshots_verified }}",
        "EXPECTED_SOURCE_ROWS_REPLAYED: ${{ steps.package_artifacts.outputs.source_rows_replayed }}",
        "actual = hashlib.sha256(bundle.read_bytes()).hexdigest()",
        "require(actual == expected, f\"digest mismatch: expected {expected}, got {actual}\")",
    )
    for fragment in intelligence_fragments:
        if fragment not in intelligence_workflow:
            errors.append(f"governed-intelligence CI contract missing: {fragment}")
    if "SOURCE_ROWS_SNAPSHOT_VERIFIED" in intelligence_workflow:
        errors.append("governed-intelligence CI source-row replay signal was weakened")
    action_pins = {
        "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
        "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact": "d3f86a106a0bac45b974a628896c90dbdf5c8093",
    }
    for action, expected_sha in action_pins.items():
        refs = re.findall(
            rf"(?m)^\s*uses:\s*{re.escape(action)}@([^\s#]+)",
            intelligence_workflow,
        )
        if not refs or any(ref != expected_sha for ref in refs):
            errors.append(
                f"governed-intelligence CI action pin changed: {action}={refs!r}"
            )
    required_gate_lines = (
        'require(report["case_count"], 13, "case_count")',
        'require(report["case_count"], 8, "case_count")',
        '"micro_recall_at_k": "0.444444",',
        '"macro_recall_at_k": "0.583333",',
        '"mean_reciprocal_rank": "0.666667",',
        '"proof_coverage_status": "PASS",',
    )
    for line in required_gate_lines:
        if not re.search(rf"(?m)^\s*{re.escape(line)}\s*$", intelligence_workflow):
            errors.append(f"governed-intelligence CI gate line changed: {line}")
    if re.search(r"\bassert\s", intelligence_workflow):
        errors.append("governed-intelligence CI must not use removable Python asserts")
    if re.search(r"(?m)^  pull_request_target\s*:", intelligence_workflow):
        errors.append("governed-intelligence CI must not use pull_request_target")
    permissions_match = re.search(
        r"(?ms)^permissions:\s*\r?\n(?P<body>.*?)(?=^\S|\Z)",
        intelligence_workflow,
    )
    permission_lines = (
        []
        if permissions_match is None
        else [
            line.strip()
            for line in permissions_match.group("body").splitlines()
            if line.strip()
        ]
    )
    if permission_lines != ["contents: read"]:
        errors.append(
            "governed-intelligence CI permissions must remain contents: read only"
        )

    windows_job = workflow_job_block(
        intelligence_workflow, "windows-pre-upload-verifier"
    )
    if windows_job is None:
        errors.append("governed-intelligence CI Windows verifier job is missing")
    else:
        if not re.search(r"(?m)^    runs-on:\s*windows-latest\s*$", windows_job):
            errors.append("governed-intelligence CI verifier must run on Windows")
        if re.search(r"(?m)^    if\s*:", windows_job):
            errors.append("governed-intelligence CI Windows verifier job must be unconditional")
        if re.search(r"(?m)^    continue-on-error\s*:", windows_job):
            errors.append("governed-intelligence CI Windows verifier job must fail closed")
        windows_steps = workflow_steps(windows_job)
        expected_windows_steps = (
            "Checkout",
            "Set up Python",
            "Run pre-upload verifier tests on Windows",
        )
        if tuple(name for name, _ in windows_steps) != expected_windows_steps:
            errors.append("governed-intelligence CI Windows verifier steps changed")
        if "working-directory: governed-intelligence-sample" not in windows_job:
            errors.append("governed-intelligence CI Windows test directory changed")
        if 'python-version: "3.11"' not in windows_job:
            errors.append("governed-intelligence CI Windows Python version changed")
        if "PYTHONPATH: src" not in windows_job:
            errors.append("governed-intelligence CI Windows PYTHONPATH changed")
        windows_checkout = [block for name, block in windows_steps if name == "Checkout"]
        if len(windows_checkout) != 1 or workflow_step_scalar(
            windows_checkout[0], "uses"
        ) != ["actions/checkout@11d5960a326750d5838078e36cf38b85af677262"]:
            errors.append("governed-intelligence CI Windows checkout action changed")
        windows_python = [block for name, block in windows_steps if name == "Set up Python"]
        if len(windows_python) != 1 or workflow_step_scalar(
            windows_python[0], "uses"
        ) != ["actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"]:
            errors.append("governed-intelligence CI Windows Python action changed")
        windows_test = [
            block
            for name, block in windows_steps
            if name == "Run pre-upload verifier tests on Windows"
        ]
        if len(windows_test) != 1:
            errors.append("governed-intelligence CI Windows verifier test step changed")
        else:
            if workflow_step_scalar(windows_test[0], "if"):
                errors.append("governed-intelligence CI Windows verifier test must run unconditionally")
            if workflow_step_scalar(windows_test[0], "continue-on-error"):
                errors.append("governed-intelligence CI Windows verifier test must fail closed")
            if workflow_step_scalar(windows_test[0], "run") != [
                "python -m unittest tests.test_pre_upload_verifier -v"
            ]:
                errors.append("governed-intelligence CI Windows verifier test command changed")

    evaluate_job = workflow_job_block(intelligence_workflow, "evaluate")
    if evaluate_job is None:
        errors.append("governed-intelligence CI evaluate job is missing")
        return
    if re.search(r"(?m)^    if\s*:", evaluate_job):
        errors.append("governed-intelligence CI evaluate job must be unconditional")
    if re.search(r"(?m)^    continue-on-error\s*:", evaluate_job):
        errors.append("governed-intelligence CI evaluate job must fail closed")

    if not re.search(
        r"(?m)^    needs:\s*windows-pre-upload-verifier\s*$", evaluate_job
    ):
        errors.append(
            "governed-intelligence CI evaluate job must depend on Windows verifier"
        )

    required_active_steps = (
        "Checkout",
        "Set up Python",
        "Build governed synthetic pipeline artifacts",
        "Run pre-model control tests",
        "Build deterministic context and evaluation receipts",
        "Check evaluation report contract",
        "Build deterministic lexical retrieval receipts",
        "Check retrieval report contract and declared input digests",
        "Build deterministic structured grounding receipts",
        "Check grounding report contract and declared input digests",
        "Prepare artifact destination",
        "Verify and package exact artifact snapshots",
    )
    upload_name = "Publish synthetic pre-model receipts"
    download_name = "Download published proof artifact"
    digest_check_name = "Verify published proof digest"
    expected_step_sequence = required_active_steps + (
        upload_name,
        download_name,
        digest_check_name,
    )
    actual_steps = workflow_steps(evaluate_job)
    actual_step_names = tuple(name for name, _ in actual_steps)
    if actual_step_names != expected_step_sequence:
        errors.append(
            "governed-intelligence CI complete step sequence changed: "
            f"{actual_step_names!r}"
        )

    step_blocks: dict[str, str] = {}
    for required_name in required_active_steps + (download_name, digest_check_name):
        matches = [block for name, block in actual_steps if name == required_name]
        if len(matches) != 1:
            errors.append(
                "governed-intelligence CI required active step count changed: "
                f"{required_name}={len(matches)}"
            )
            continue
        step_blocks[required_name] = matches[0]
        if workflow_step_scalar(matches[0], "if"):
            errors.append(
                f"governed-intelligence CI required step must be unconditional: {required_name}"
            )
        if workflow_step_scalar(matches[0], "continue-on-error"):
            errors.append(
                f"governed-intelligence CI required step must fail closed: {required_name}"
            )

    upload_matches = [block for name, block in actual_steps if name == upload_name]
    if len(upload_matches) != 1:
        errors.append(
            "governed-intelligence CI upload step count changed: "
            f"{len(upload_matches)}"
        )
    else:
        upload_block = upload_matches[0]
        expected_upload_condition = (
            "${{ success() && steps.package_artifacts.outcome == 'success' }}"
        )
        if workflow_step_scalar(upload_block, "if") != [expected_upload_condition]:
            errors.append("governed-intelligence CI upload success gate changed")
        if workflow_step_scalar(upload_block, "continue-on-error"):
            errors.append("governed-intelligence CI upload step must fail closed")
        if workflow_step_scalar(upload_block, "uses") != [
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
        ]:
            errors.append("governed-intelligence CI upload action binding changed")
        if workflow_step_with_scalar(upload_block, "name") != [
            "hydra-governed-intelligence-sample"
        ]:
            errors.append("governed-intelligence CI upload artifact name changed")
        expected_upload_path = (
            "governed-intelligence-sample/build/upload/"
            "hydra-governed-intelligence-proof.zip"
        )
        if workflow_step_with_scalar(upload_block, "path") != [expected_upload_path]:
            errors.append("governed-intelligence CI upload path changed")
        if workflow_step_with_scalar(upload_block, "compression-level") != ["0"]:
            errors.append("governed-intelligence CI upload compression changed")
        if workflow_step_with_scalar(upload_block, "if-no-files-found") != ["error"]:
            errors.append(
                "governed-intelligence CI upload missing-file behavior changed"
            )

    prepare_name = "Prepare artifact destination"
    if prepare_name in step_blocks:
        if workflow_step_scalar(step_blocks[prepare_name], "run") != [
            "mkdir -p governed-intelligence-sample/build/upload"
        ]:
            errors.append("governed-intelligence CI artifact destination setup changed")

    verifier_name = "Verify and package exact artifact snapshots"
    if verifier_name in step_blocks:
        verifier_block = step_blocks[verifier_name]
        if workflow_step_scalar(verifier_block, "id") != ["package_artifacts"]:
            errors.append("governed-intelligence CI package step ID changed")
        expected_invocation = (
            "python -I -B governed-intelligence-sample/src/"
            "hydra_governed_intelligence/pre_upload_verifier.py --repository-root . "
            "--bundle-path governed-intelligence-sample/build/upload/"
            "hydra-governed-intelligence-proof.zip --github-output-path "
            '"$GITHUB_OUTPUT"'
        )
        if workflow_step_scalar(verifier_block, "run") != [expected_invocation]:
            errors.append(
                "governed-intelligence CI package invocation changed"
            )
        if re.search(r"(?m)^        run:\s*[|>]", verifier_block):
            errors.append(
                "governed-intelligence CI package step must not use inline code"
            )

    if download_name in step_blocks:
        download_block = step_blocks[download_name]
        if workflow_step_scalar(download_block, "uses") != [
            "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093"
        ]:
            errors.append("governed-intelligence CI download action binding changed")
        if workflow_step_with_scalar(download_block, "name") != [
            "hydra-governed-intelligence-sample"
        ]:
            errors.append("governed-intelligence CI download artifact name changed")
        if workflow_step_with_scalar(download_block, "path") != [
            "${{ runner.temp }}/hydra-governed-intelligence-published-proof"
        ]:
            errors.append("governed-intelligence CI download path changed")

    if digest_check_name in step_blocks:
        digest_block = step_blocks[digest_check_name]
        if workflow_step_scalar(digest_block, "uses"):
            errors.append("governed-intelligence CI digest check must run Python")
        if workflow_step_with_scalar(digest_block, "DOWNLOADED_BUNDLE_PATH") != [
            "${{ runner.temp }}/hydra-governed-intelligence-published-proof/"
            "hydra-governed-intelligence-proof.zip"
        ]:
            errors.append("governed-intelligence CI downloaded bundle path changed")
        if workflow_step_with_scalar(digest_block, "EXPECTED_BUNDLE_SHA256") != [
            "${{ steps.package_artifacts.outputs.bundle_sha256 }}"
        ]:
            errors.append("governed-intelligence CI expected bundle digest changed")
        expected_digest_run = [
            "python -I -B - <<'PY'",
            "import hashlib",
            "import os",
            "import re",
            "from pathlib import Path",
            "def require(condition, detail):",
            "if not condition:",
            'raise SystemExit(f"PUBLISHED_ARTIFACT_DIGEST_CHECK=FAIL: {detail}")',
            'expected = os.environ.get("EXPECTED_BUNDLE_SHA256", "")',
            'input_snapshots = os.environ.get("EXPECTED_INPUT_SNAPSHOTS_VERIFIED", "")',
            'source_rows = os.environ.get("EXPECTED_SOURCE_ROWS_REPLAYED", "")',
            'bundle = Path(os.environ.get("DOWNLOADED_BUNDLE_PATH", ""))',
            'require(re.fullmatch(r"[0-9a-f]{64}", expected) is not None, "expected digest is invalid")',
            'require(input_snapshots == "2", "verified input snapshot count changed")',
            'require(source_rows == "7", "replayed source row count changed")',
            'require(bundle.is_file() and not bundle.is_symlink(), "downloaded inner ZIP is missing")',
            "entries = sorted(entry.name for entry in bundle.parent.iterdir())",
            'require(entries == [bundle.name], "downloaded artifact member set changed")',
            "actual = hashlib.sha256(bundle.read_bytes()).hexdigest()",
            'require(actual == expected, f"digest mismatch: expected {expected}, got {actual}")',
            'print(f"PUBLISHED_ARTIFACT_DIGEST_CHECK=PASS:{actual}")',
            "PY",
        ]
        if workflow_step_run_lines(digest_block) != expected_digest_run:
            errors.append(
                "governed-intelligence CI downloaded digest check changed"
            )


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
        "ManifestTable": "AWS::Glue::Table",
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
    print("VALIDATION_SCOPE=REPOSITORY_CONTROLLED_SELF_CHECK")
    print(f"REQUIRED_PATHS={len(REQUIRED_PATHS)}")
    print(f"PUBLIC_TEXT_FILES={len(active_public_text_files())}")
    print("FAIL_CLOSED_CONTRACT=PASS")
    print("MARKDOWN_LINKS=PASS")
    print("VALIDATOR_CI_CONTRACT=PASS")
    print("MARKET_PIPELINE_CI_CONTRACT=PASS")
    print("SQL_SAMPLE_CI_CONTRACT=PASS")
    print("AWS_SAMPLE_CI_CONTRACT=PASS")
    print("AWS_DEPLOY_WORKFLOW_CONTRACT=PASS")
    print("GOVERNED_INTELLIGENCE_SAFETY_CONTRACT=PASS")
    print("GOVERNED_INTELLIGENCE_CI_CONTRACT=PASS")
    print("AWS_TEMPLATE_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
,
        run_script,
    )
    failed = re.search(
        r'(?m)^[ \t]*if \[\[ "\$state" == "FAILED" \|\| "\$state" == "CANCELLED" \]\]; then[ \t]*    validate_manifest_v2_replay_contract(errors)
    validate_pre_upload_verifier_contract(errors)

    workflow_dir = ROOT / ".github" / "workflows"
    workflow_files = sorted(
        list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
    )
    for workflow_path in workflow_files:
        try:
            action_refs = workflow_action_refs(
                workflow_path.read_text(encoding="utf-8-sig")
            )
        except (OSError, yaml.YAMLError, ValueError) as exc:
            errors.append(
                f"unable to parse workflow actions in "
                f"{workflow_path.relative_to(ROOT)}: {exc}"
            )
            continue
        for action_ref in action_refs:
            if not workflow_action_ref_is_pinned(action_ref):
                errors.append(
                    f"workflow action must use a full commit SHA or image digest: "
                    f"{workflow_path.relative_to(ROOT)}: {action_ref}"
                )
    documentation_contracts = {
        ROOT / "README.md": (
            "15-member deterministic proof package intentionally includes",
            "all 7 rows are synthetic, including rows designed to quarantine",
            "Governed context, retrieval, and receipt artifacts remain accepted-only or aggregate-only",
            "do not expose quarantined row payloads",
        ),
        INTELLIGENCE_SAMPLE / "README.md": (
            "deterministic, uncompressed 15-member ZIP",
            "all 7 synthetic rows, including rows designed to quarantine",
            "canonical `resolved_symbol_aliases.json`",
            "`INPUT_SNAPSHOTS_VERIFIED=2`",
            "`SOURCE_ROWS_REPLAYED=7`",
            "do not expose quarantined row payloads",
        ),
        PIPELINE / "README.md": (
            "15-member proof package intentionally carries the exact source snapshot",
            "all 7 synthetic rows, including rows designed to quarantine",
            "canonical resolved aliases",
            "do not expose quarantined row payloads",
        ),
    }
    for path, fragments in documentation_contracts.items():
        text = path.read_text(encoding="utf-8-sig")
        for fragment in fragments:
            if fragment not in text:
                errors.append(
                    f"manifest-v2 public documentation contract missing: {path.name}: {fragment}"
                )
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
        '"hydra-market-pipeline-manifest/v2"',
        '"resolved_symbol_aliases.json"',
        '"source_snapshot.csv"',
        'print("INPUT_SNAPSHOTS_VERIFIED=2")',
        'print("SOURCE_ROWS_SNAPSHOT_VERIFIED=7")',
        "python run_recovery_demo.py --output-dir build/operations",
        "OPERATIONS_RECEIPT=PASS",
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
        "name: hydra-market-data-pipeline-sample",
        "name: Download published pipeline outputs",
        "name: Verify published pipeline artifact round-trip",
        "PUBLISHED_PIPELINE_ARTIFACT=PASS",
    )
    for fragment in pipeline_fragments:
        if fragment not in pipeline_workflow:
            errors.append(f"market-pipeline CI contract missing: {fragment}")
    pipeline_job = workflow_job_block(pipeline_workflow, "test-and-build")
    if pipeline_job is None:
        errors.append("market-pipeline CI test-and-build job is missing")
    else:
        if re.search(r"(?m)^    if\s*:", pipeline_job):
            errors.append("market-pipeline CI job must be unconditional")
        if re.search(r"(?m)^    continue-on-error\s*:", pipeline_job):
            errors.append("market-pipeline CI job must fail closed")

        pipeline_steps = workflow_steps(pipeline_job)
        artifact_step_names = (
            "Publish synthetic pipeline outputs",
            "Download published pipeline outputs",
            "Verify published pipeline artifact round-trip",
        )
        names = [name for name, _ in pipeline_steps]
        if tuple(names[-3:]) != artifact_step_names or any(
            names.count(name) != 1 for name in artifact_step_names
        ):
            errors.append("market-pipeline CI artifact steps must be unique and ordered last")

        pipeline_action_pins = {
            "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
            "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
            "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
            "actions/download-artifact": "d3f86a106a0bac45b974a628896c90dbdf5c8093",
        }
        for action, expected_sha in pipeline_action_pins.items():
            refs = re.findall(
                rf"(?m)^\s*uses:\s*{re.escape(action)}@([^\s#]+)",
                pipeline_workflow,
            )
            if not refs or any(ref != expected_sha for ref in refs):
                errors.append(f"market-pipeline CI action pin changed: {action}={refs!r}")

        step_blocks = {
            name: [block for step_name, block in pipeline_steps if step_name == name]
            for name in artifact_step_names
        }
        if all(len(step_blocks[name]) == 1 for name in artifact_step_names):
            upload, download, verify = (
                step_blocks[name][0] for name in artifact_step_names
            )
            expected_artifact = "hydra-market-data-pipeline-sample"
            if workflow_step_scalar(upload, "uses") != [
                "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
            ]:
                errors.append("market-pipeline CI upload action changed")
            if workflow_step_with_scalar(upload, "name") != [expected_artifact]:
                errors.append("market-pipeline CI upload artifact name changed")
            expected_paths = [
                "market-data-pipeline-sample/build/demo/",
                "market-data-pipeline-sample/build/operations/",
            ]
            if workflow_step_literal_lines(upload, "path") != expected_paths:
                errors.append("market-pipeline CI upload paths changed")
            if workflow_step_with_scalar(upload, "if-no-files-found") != ["error"]:
                errors.append("market-pipeline CI upload must fail when outputs are missing")
            if workflow_step_scalar(upload, "if") or workflow_step_scalar(
                upload, "continue-on-error"
            ):
                errors.append("market-pipeline CI upload must remain fail-closed")

            if workflow_step_scalar(download, "uses") != [
                "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093"
            ]:
                errors.append("market-pipeline CI download action changed")
            if workflow_step_with_scalar(download, "name") != [expected_artifact]:
                errors.append("market-pipeline CI download artifact name changed")
            if workflow_step_with_scalar(download, "path") != [
                "${{ runner.temp }}/hydra-market-data-pipeline-published"
            ]:
                errors.append("market-pipeline CI download destination changed")
            if workflow_step_scalar(download, "if") or workflow_step_scalar(
                download, "continue-on-error"
            ):
                errors.append("market-pipeline CI download must remain fail-closed")

            if workflow_step_scalar(verify, "if") or workflow_step_scalar(
                verify, "continue-on-error"
            ):
                errors.append("market-pipeline CI artifact verification must remain fail-closed")
            verify_lines = workflow_step_run_lines(verify) or []
            required_verification_lines = (
                "expected_files[f\"{label}/{relative}\"] = path",
                "actual_files[f\"{label}/{relative}\"] = path",
                "missing = sorted(set(expected_files) - set(actual_files))",
                "extra = sorted(set(actual_files) - set(expected_files))",
                "expected = hashlib.sha256(source.read_bytes()).hexdigest()",
                "actual = hashlib.sha256(actual_files[name].read_bytes()).hexdigest()",
                "require(actual == expected, f\"SHA-256 mismatch for {name}\")",
                "print(f\"PUBLISHED_PIPELINE_ARTIFACT=PASS:{len(expected_files)}\")",
                "root_names = {path.name for path in root_entries}",
                "require(root_names == set(source_roots), f\"unexpected artifact root entries: {sorted(root_names)}\")",
                "require(not path.is_symlink() and path.is_dir(), f\"invalid artifact root entry: {path}\")",
            )
            for line in required_verification_lines:
                if line not in verify_lines:
                    errors.append(
                        f"market-pipeline CI artifact verification changed: {line}"
                    )

    if "SOURCE_ROWS_REPLAYED" in pipeline_workflow:
        errors.append("market-pipeline CI must not claim independent source-row replay")

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
        "aws-actions/setup-sam@89ddb14d60e682855e3fea4be85b3c56485de310",
        "sam validate --lint --template-file template.json",
        "python -m unittest discover -s tests -t . -v",
        "python local_demo.py --output-dir build/local",
        "AWS_SAMPLE_MANIFEST=PASS",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
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
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "aws-actions/configure-aws-credentials@e1253824e5c10ff9df46874f81ed3ec929e19cfd",
        "aws-actions/setup-sam@89ddb14d60e682855e3fea4be85b3c56485de310",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "path: aws-market-data-pipeline/build/deployed/deployment_evidence.json",
        "STACK_NAME: ${{ inputs.stack_name }}-${{ github.run_id }}-${{ github.run_attempt }}",
        "if: github.ref == 'refs/heads/main'",
        "hydra-public-market-pipeline-demo-",
        "Validate deployment target",
        "Refuse to modify an existing stack",
        "Refusing to update or delete an existing stack.",
        "id: deploy_stack",
        "inputs.teardown && steps.deploy_stack.outcome != 'skipped'",
        "sam deploy",
        "--query 'Stacks[0].StackStatus'",
        "CREATE_COMPLETE",
        "timeout-minutes: 75",
        "seq 1 360",
        "hydra:deployment-run",
        "stack_owner",
        "ResourceStatus == \"DELETE_FAILED\"",
        "deployed_outputs_match_local_replay",
        "Create manifest-gated Athena consumer view",
        "sql/create_committed_normalized_events.sql",
        "FROM committed_normalized_events",
        "COUNT(*) AS accepted_rows FROM committed_normalized_events",
        '"athena_accepted_rows": int(os.environ["ATHENA_ACCEPTED_ROWS"]),',
        "start-query-execution",
        "--page-size 1000",
        "--max-items 1000",
        '--starting-token "$token"',
        "NextToken",
        "inputs.teardown",
        "sam delete",
    )
    for fragment in deploy_fragments:
        if fragment not in deploy_workflow:
            errors.append(f"aws-deploy workflow contract missing: {fragment}")

    try:
        deploy_document = yaml.load(deploy_workflow, Loader=yaml.BaseLoader)
        deploy_job = deploy_document["jobs"]["deploy-and-verify"]
        athena_steps = [
            step
            for step in deploy_job["steps"]
            if isinstance(step, dict)
            and step.get("name") == "Run bounded Athena verification query"
        ]
        expected_verifier = (
            'python "$SAMPLE_DIR/verify_athena_query_results.py" '
            '--results-path "$SAMPLE_DIR/build/deployed/athena_query_results.json" '
            '--github-env "$GITHUB_ENV"'
        )
        if len(athena_steps) != 1:
            errors.append("aws-deploy Athena verification step count changed")
        else:
            run_script = athena_steps[0].get("run", "")
            result_read = 'aws athena get-query-results --query-execution-id "$QUERY_ID" > "$SAMPLE_DIR/build/deployed/athena_query_results.json"'
            if isinstance(run_script, str):
                normalized_run_script = re.sub(
                    r"\s+",
                    " ",
                    re.sub(r"\\\s+", " ", run_script),
                ).strip()
            else:
                normalized_run_script = ""
            if (
                not normalized_run_script
                or result_read not in normalized_run_script
                or expected_verifier not in normalized_run_script
                or normalized_run_script.index(result_read)
                > normalized_run_script.index(expected_verifier)
            ):
                errors.append(
                    "aws-deploy Athena success step must save results before invoking the row-count verifier"
                )
    except (KeyError, TypeError, yaml.YAMLError, ValueError) as exc:
        errors.append(f"aws-deploy Athena verification step is invalid: {exc}")

    if re.search(r"(?m)^  (?:pull_request|push):", deploy_workflow):
        errors.append("aws-deploy workflow must remain manual-only")

    preflight_position = deploy_workflow.index(
        "- name: Refuse to modify an existing stack"
    )
    deploy_step_position = deploy_workflow.index("id: deploy_stack")
    sam_deploy_position = deploy_workflow.index("sam deploy")
    if not (preflight_position < deploy_step_position < sam_deploy_position):
        errors.append("aws-deploy teardown gate must identify the deploy attempt step")

    deploy_action_pins = {
        "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
        "aws-actions/configure-aws-credentials": "e1253824e5c10ff9df46874f81ed3ec929e19cfd",
        "aws-actions/setup-sam": "89ddb14d60e682855e3fea4be85b3c56485de310",
        "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
    }
    for action, expected_sha in deploy_action_pins.items():
        refs = re.findall(
            rf"(?m)^\s*uses:\s*{re.escape(action)}@([^\s#]+)",
            deploy_workflow,
        )
        if not refs or any(ref != expected_sha for ref in refs):
            errors.append(f"aws-deploy action pin changed: {action}={refs!r}")

    deploy_job = workflow_job_block(deploy_workflow, "deploy-and-verify")
    if deploy_job is None:
        errors.append("aws-deploy job is missing")
    else:
        deploy_steps = workflow_steps(deploy_job)
        publish_steps = [
            block
            for name, block in deploy_steps
            if name == "Publish sanitized deployment evidence"
        ]
        artifact_upload_steps = [
            block
            for _, block in deploy_steps
            if any(
                reference.startswith("actions/upload-artifact@")
                for reference in workflow_step_scalar(block, "uses")
            )
        ]
        if len(artifact_upload_steps) != 1:
            errors.append("aws-deploy must contain exactly one artifact upload")
        if len(publish_steps) != 1:
            errors.append("aws-deploy sanitized evidence upload step count changed")
        else:
            publish_step = publish_steps[0]
            if workflow_step_scalar(publish_step, "uses") != [
                "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
            ]:
                errors.append("aws-deploy evidence upload action changed")
            if workflow_step_with_scalar(publish_step, "path") != [
                "aws-market-data-pipeline/build/deployed/deployment_evidence.json"
            ]:
                errors.append("aws-deploy evidence upload must publish only the sanitized evidence JSON")
            if workflow_step_with_scalar(publish_step, "if-no-files-found") != ["error"]:
                errors.append("aws-deploy evidence upload must fail when evidence is missing")

    intelligence_workflow = (
        ROOT / ".github/workflows/governed-intelligence-sample.yml"
    ).read_text(encoding="utf-8-sig")
    validation_workflow = (
        ROOT / ".github/workflows/public-repository-validation.yml"
    ).read_text(encoding="utf-8-sig")
    for label, workflow in (
        ("governed-intelligence", intelligence_workflow),
        ("public-repository-validation", validation_workflow),
    ):
        if not workflow_event_is_unfiltered(workflow, "pull_request"):
            errors.append(f"{label} CI pull-request trigger must be unfiltered")
    intelligence_fragments = (
        'python-version: "3.11"',
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "working-directory: governed-intelligence-sample",
        "python -m unittest discover -s tests -t . -v",
        "python run_demo.py",
        "GOVERNED_INTELLIGENCE_EVAL=PASS",
        "python run_retrieval_demo.py",
        "--qrels fixtures/retrieval_qrels.json",
        "GOVERNED_RETRIEVAL_EVAL=PASS",
        "python run_grounding_demo.py",
        "GOVERNED_GROUNDING_EVAL=PASS",
        "build/grounding/",
        "timeout-minutes: 15",
        "persist-credentials: false",
        "mkdir -p governed-intelligence-sample/build/upload",
        "python -I -B governed-intelligence-sample/src/hydra_governed_intelligence/pre_upload_verifier.py --repository-root . --bundle-path governed-intelligence-sample/build/upload/hydra-governed-intelligence-proof.zip --github-output-path \"$GITHUB_OUTPUT\"",
        '"case_count"], 13',
        '"micro_recall_at_k": "0.444444"',
        '"case_count"], 8',
        '"proof_coverage_status": "PASS"',
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
        "compression-level: 0",
        "EXPECTED_BUNDLE_SHA256: ${{ steps.package_artifacts.outputs.bundle_sha256 }}",
        "EXPECTED_INPUT_SNAPSHOTS_VERIFIED: ${{ steps.package_artifacts.outputs.input_snapshots_verified }}",
        "EXPECTED_SOURCE_ROWS_REPLAYED: ${{ steps.package_artifacts.outputs.source_rows_replayed }}",
        "actual = hashlib.sha256(bundle.read_bytes()).hexdigest()",
        "require(actual == expected, f\"digest mismatch: expected {expected}, got {actual}\")",
    )
    for fragment in intelligence_fragments:
        if fragment not in intelligence_workflow:
            errors.append(f"governed-intelligence CI contract missing: {fragment}")
    if "SOURCE_ROWS_SNAPSHOT_VERIFIED" in intelligence_workflow:
        errors.append("governed-intelligence CI source-row replay signal was weakened")
    action_pins = {
        "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
        "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact": "d3f86a106a0bac45b974a628896c90dbdf5c8093",
    }
    for action, expected_sha in action_pins.items():
        refs = re.findall(
            rf"(?m)^\s*uses:\s*{re.escape(action)}@([^\s#]+)",
            intelligence_workflow,
        )
        if not refs or any(ref != expected_sha for ref in refs):
            errors.append(
                f"governed-intelligence CI action pin changed: {action}={refs!r}"
            )
    required_gate_lines = (
        'require(report["case_count"], 13, "case_count")',
        'require(report["case_count"], 8, "case_count")',
        '"micro_recall_at_k": "0.444444",',
        '"macro_recall_at_k": "0.583333",',
        '"mean_reciprocal_rank": "0.666667",',
        '"proof_coverage_status": "PASS",',
    )
    for line in required_gate_lines:
        if not re.search(rf"(?m)^\s*{re.escape(line)}\s*$", intelligence_workflow):
            errors.append(f"governed-intelligence CI gate line changed: {line}")
    if re.search(r"\bassert\s", intelligence_workflow):
        errors.append("governed-intelligence CI must not use removable Python asserts")
    if re.search(r"(?m)^  pull_request_target\s*:", intelligence_workflow):
        errors.append("governed-intelligence CI must not use pull_request_target")
    permissions_match = re.search(
        r"(?ms)^permissions:\s*\r?\n(?P<body>.*?)(?=^\S|\Z)",
        intelligence_workflow,
    )
    permission_lines = (
        []
        if permissions_match is None
        else [
            line.strip()
            for line in permissions_match.group("body").splitlines()
            if line.strip()
        ]
    )
    if permission_lines != ["contents: read"]:
        errors.append(
            "governed-intelligence CI permissions must remain contents: read only"
        )

    windows_job = workflow_job_block(
        intelligence_workflow, "windows-pre-upload-verifier"
    )
    if windows_job is None:
        errors.append("governed-intelligence CI Windows verifier job is missing")
    else:
        if not re.search(r"(?m)^    runs-on:\s*windows-latest\s*$", windows_job):
            errors.append("governed-intelligence CI verifier must run on Windows")
        if re.search(r"(?m)^    if\s*:", windows_job):
            errors.append("governed-intelligence CI Windows verifier job must be unconditional")
        if re.search(r"(?m)^    continue-on-error\s*:", windows_job):
            errors.append("governed-intelligence CI Windows verifier job must fail closed")
        windows_steps = workflow_steps(windows_job)
        expected_windows_steps = (
            "Checkout",
            "Set up Python",
            "Run pre-upload verifier tests on Windows",
        )
        if tuple(name for name, _ in windows_steps) != expected_windows_steps:
            errors.append("governed-intelligence CI Windows verifier steps changed")
        if "working-directory: governed-intelligence-sample" not in windows_job:
            errors.append("governed-intelligence CI Windows test directory changed")
        if 'python-version: "3.11"' not in windows_job:
            errors.append("governed-intelligence CI Windows Python version changed")
        if "PYTHONPATH: src" not in windows_job:
            errors.append("governed-intelligence CI Windows PYTHONPATH changed")
        windows_checkout = [block for name, block in windows_steps if name == "Checkout"]
        if len(windows_checkout) != 1 or workflow_step_scalar(
            windows_checkout[0], "uses"
        ) != ["actions/checkout@11d5960a326750d5838078e36cf38b85af677262"]:
            errors.append("governed-intelligence CI Windows checkout action changed")
        windows_python = [block for name, block in windows_steps if name == "Set up Python"]
        if len(windows_python) != 1 or workflow_step_scalar(
            windows_python[0], "uses"
        ) != ["actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"]:
            errors.append("governed-intelligence CI Windows Python action changed")
        windows_test = [
            block
            for name, block in windows_steps
            if name == "Run pre-upload verifier tests on Windows"
        ]
        if len(windows_test) != 1:
            errors.append("governed-intelligence CI Windows verifier test step changed")
        else:
            if workflow_step_scalar(windows_test[0], "if"):
                errors.append("governed-intelligence CI Windows verifier test must run unconditionally")
            if workflow_step_scalar(windows_test[0], "continue-on-error"):
                errors.append("governed-intelligence CI Windows verifier test must fail closed")
            if workflow_step_scalar(windows_test[0], "run") != [
                "python -m unittest tests.test_pre_upload_verifier -v"
            ]:
                errors.append("governed-intelligence CI Windows verifier test command changed")

    evaluate_job = workflow_job_block(intelligence_workflow, "evaluate")
    if evaluate_job is None:
        errors.append("governed-intelligence CI evaluate job is missing")
        return
    if re.search(r"(?m)^    if\s*:", evaluate_job):
        errors.append("governed-intelligence CI evaluate job must be unconditional")
    if re.search(r"(?m)^    continue-on-error\s*:", evaluate_job):
        errors.append("governed-intelligence CI evaluate job must fail closed")

    if not re.search(
        r"(?m)^    needs:\s*windows-pre-upload-verifier\s*$", evaluate_job
    ):
        errors.append(
            "governed-intelligence CI evaluate job must depend on Windows verifier"
        )

    required_active_steps = (
        "Checkout",
        "Set up Python",
        "Build governed synthetic pipeline artifacts",
        "Run pre-model control tests",
        "Build deterministic context and evaluation receipts",
        "Check evaluation report contract",
        "Build deterministic lexical retrieval receipts",
        "Check retrieval report contract and declared input digests",
        "Build deterministic structured grounding receipts",
        "Check grounding report contract and declared input digests",
        "Prepare artifact destination",
        "Verify and package exact artifact snapshots",
    )
    upload_name = "Publish synthetic pre-model receipts"
    download_name = "Download published proof artifact"
    digest_check_name = "Verify published proof digest"
    expected_step_sequence = required_active_steps + (
        upload_name,
        download_name,
        digest_check_name,
    )
    actual_steps = workflow_steps(evaluate_job)
    actual_step_names = tuple(name for name, _ in actual_steps)
    if actual_step_names != expected_step_sequence:
        errors.append(
            "governed-intelligence CI complete step sequence changed: "
            f"{actual_step_names!r}"
        )

    step_blocks: dict[str, str] = {}
    for required_name in required_active_steps + (download_name, digest_check_name):
        matches = [block for name, block in actual_steps if name == required_name]
        if len(matches) != 1:
            errors.append(
                "governed-intelligence CI required active step count changed: "
                f"{required_name}={len(matches)}"
            )
            continue
        step_blocks[required_name] = matches[0]
        if workflow_step_scalar(matches[0], "if"):
            errors.append(
                f"governed-intelligence CI required step must be unconditional: {required_name}"
            )
        if workflow_step_scalar(matches[0], "continue-on-error"):
            errors.append(
                f"governed-intelligence CI required step must fail closed: {required_name}"
            )

    upload_matches = [block for name, block in actual_steps if name == upload_name]
    if len(upload_matches) != 1:
        errors.append(
            "governed-intelligence CI upload step count changed: "
            f"{len(upload_matches)}"
        )
    else:
        upload_block = upload_matches[0]
        expected_upload_condition = (
            "${{ success() && steps.package_artifacts.outcome == 'success' }}"
        )
        if workflow_step_scalar(upload_block, "if") != [expected_upload_condition]:
            errors.append("governed-intelligence CI upload success gate changed")
        if workflow_step_scalar(upload_block, "continue-on-error"):
            errors.append("governed-intelligence CI upload step must fail closed")
        if workflow_step_scalar(upload_block, "uses") != [
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
        ]:
            errors.append("governed-intelligence CI upload action binding changed")
        if workflow_step_with_scalar(upload_block, "name") != [
            "hydra-governed-intelligence-sample"
        ]:
            errors.append("governed-intelligence CI upload artifact name changed")
        expected_upload_path = (
            "governed-intelligence-sample/build/upload/"
            "hydra-governed-intelligence-proof.zip"
        )
        if workflow_step_with_scalar(upload_block, "path") != [expected_upload_path]:
            errors.append("governed-intelligence CI upload path changed")
        if workflow_step_with_scalar(upload_block, "compression-level") != ["0"]:
            errors.append("governed-intelligence CI upload compression changed")
        if workflow_step_with_scalar(upload_block, "if-no-files-found") != ["error"]:
            errors.append(
                "governed-intelligence CI upload missing-file behavior changed"
            )

    prepare_name = "Prepare artifact destination"
    if prepare_name in step_blocks:
        if workflow_step_scalar(step_blocks[prepare_name], "run") != [
            "mkdir -p governed-intelligence-sample/build/upload"
        ]:
            errors.append("governed-intelligence CI artifact destination setup changed")

    verifier_name = "Verify and package exact artifact snapshots"
    if verifier_name in step_blocks:
        verifier_block = step_blocks[verifier_name]
        if workflow_step_scalar(verifier_block, "id") != ["package_artifacts"]:
            errors.append("governed-intelligence CI package step ID changed")
        expected_invocation = (
            "python -I -B governed-intelligence-sample/src/"
            "hydra_governed_intelligence/pre_upload_verifier.py --repository-root . "
            "--bundle-path governed-intelligence-sample/build/upload/"
            "hydra-governed-intelligence-proof.zip --github-output-path "
            '"$GITHUB_OUTPUT"'
        )
        if workflow_step_scalar(verifier_block, "run") != [expected_invocation]:
            errors.append(
                "governed-intelligence CI package invocation changed"
            )
        if re.search(r"(?m)^        run:\s*[|>]", verifier_block):
            errors.append(
                "governed-intelligence CI package step must not use inline code"
            )

    if download_name in step_blocks:
        download_block = step_blocks[download_name]
        if workflow_step_scalar(download_block, "uses") != [
            "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093"
        ]:
            errors.append("governed-intelligence CI download action binding changed")
        if workflow_step_with_scalar(download_block, "name") != [
            "hydra-governed-intelligence-sample"
        ]:
            errors.append("governed-intelligence CI download artifact name changed")
        if workflow_step_with_scalar(download_block, "path") != [
            "${{ runner.temp }}/hydra-governed-intelligence-published-proof"
        ]:
            errors.append("governed-intelligence CI download path changed")

    if digest_check_name in step_blocks:
        digest_block = step_blocks[digest_check_name]
        if workflow_step_scalar(digest_block, "uses"):
            errors.append("governed-intelligence CI digest check must run Python")
        if workflow_step_with_scalar(digest_block, "DOWNLOADED_BUNDLE_PATH") != [
            "${{ runner.temp }}/hydra-governed-intelligence-published-proof/"
            "hydra-governed-intelligence-proof.zip"
        ]:
            errors.append("governed-intelligence CI downloaded bundle path changed")
        if workflow_step_with_scalar(digest_block, "EXPECTED_BUNDLE_SHA256") != [
            "${{ steps.package_artifacts.outputs.bundle_sha256 }}"
        ]:
            errors.append("governed-intelligence CI expected bundle digest changed")
        expected_digest_run = [
            "python -I -B - <<'PY'",
            "import hashlib",
            "import os",
            "import re",
            "from pathlib import Path",
            "def require(condition, detail):",
            "if not condition:",
            'raise SystemExit(f"PUBLISHED_ARTIFACT_DIGEST_CHECK=FAIL: {detail}")',
            'expected = os.environ.get("EXPECTED_BUNDLE_SHA256", "")',
            'input_snapshots = os.environ.get("EXPECTED_INPUT_SNAPSHOTS_VERIFIED", "")',
            'source_rows = os.environ.get("EXPECTED_SOURCE_ROWS_REPLAYED", "")',
            'bundle = Path(os.environ.get("DOWNLOADED_BUNDLE_PATH", ""))',
            'require(re.fullmatch(r"[0-9a-f]{64}", expected) is not None, "expected digest is invalid")',
            'require(input_snapshots == "2", "verified input snapshot count changed")',
            'require(source_rows == "7", "replayed source row count changed")',
            'require(bundle.is_file() and not bundle.is_symlink(), "downloaded inner ZIP is missing")',
            "entries = sorted(entry.name for entry in bundle.parent.iterdir())",
            'require(entries == [bundle.name], "downloaded artifact member set changed")',
            "actual = hashlib.sha256(bundle.read_bytes()).hexdigest()",
            'require(actual == expected, f"digest mismatch: expected {expected}, got {actual}")',
            'print(f"PUBLISHED_ARTIFACT_DIGEST_CHECK=PASS:{actual}")',
            "PY",
        ]
        if workflow_step_run_lines(digest_block) != expected_digest_run:
            errors.append(
                "governed-intelligence CI downloaded digest check changed"
            )


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
        "ManifestTable": "AWS::Glue::Table",
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
    print("VALIDATION_SCOPE=REPOSITORY_CONTROLLED_SELF_CHECK")
    print(f"REQUIRED_PATHS={len(REQUIRED_PATHS)}")
    print(f"PUBLIC_TEXT_FILES={len(active_public_text_files())}")
    print("FAIL_CLOSED_CONTRACT=PASS")
    print("MARKDOWN_LINKS=PASS")
    print("VALIDATOR_CI_CONTRACT=PASS")
    print("MARKET_PIPELINE_CI_CONTRACT=PASS")
    print("SQL_SAMPLE_CI_CONTRACT=PASS")
    print("AWS_SAMPLE_CI_CONTRACT=PASS")
    print("AWS_DEPLOY_WORKFLOW_CONTRACT=PASS")
    print("GOVERNED_INTELLIGENCE_SAFETY_CONTRACT=PASS")
    print("GOVERNED_INTELLIGENCE_CI_CONTRACT=PASS")
    print("AWS_TEMPLATE_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
,
        run_script,
    )
    if success is None or failed is None or failed.start() <= success.end():
        return False

    success_block = run_script[success.end() : failed.start()]
    normalized_block = re.sub(r"\\\r?\n[ \t]*", " ", success_block)
    active_lines = [line.strip() for line in normalized_block.splitlines()]
    result_read = (
        'aws athena get-query-results --query-execution-id "$QUERY_ID" '
        '> "$SAMPLE_DIR/build/deployed/athena_query_results.json"'
    )
    verifier = (
        'python "$SAMPLE_DIR/verify_athena_query_results.py" '
        '--results-path "$SAMPLE_DIR/build/deployed/athena_query_results.json" '
        '--github-env "$GITHUB_ENV"'
    )
    try:
        return active_lines.index(result_read) < active_lines.index(verifier)
    except ValueError:
        return False


def validate_ci_contract(errors: list[str]) -> None:
    validate_manifest_v2_replay_contract(errors)
    validate_pre_upload_verifier_contract(errors)

    workflow_dir = ROOT / ".github" / "workflows"
    workflow_files = sorted(
        list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
    )
    for workflow_path in workflow_files:
        try:
            action_refs = workflow_action_refs(
                workflow_path.read_text(encoding="utf-8-sig")
            )
        except (OSError, yaml.YAMLError, ValueError) as exc:
            errors.append(
                f"unable to parse workflow actions in "
                f"{workflow_path.relative_to(ROOT)}: {exc}"
            )
            continue
        for action_ref in action_refs:
            if not workflow_action_ref_is_pinned(action_ref):
                errors.append(
                    f"workflow action must use a full commit SHA or image digest: "
                    f"{workflow_path.relative_to(ROOT)}: {action_ref}"
                )
    documentation_contracts = {
        ROOT / "README.md": (
            "15-member deterministic proof package intentionally includes",
            "all 7 rows are synthetic, including rows designed to quarantine",
            "Governed context, retrieval, and receipt artifacts remain accepted-only or aggregate-only",
            "do not expose quarantined row payloads",
        ),
        INTELLIGENCE_SAMPLE / "README.md": (
            "deterministic, uncompressed 15-member ZIP",
            "all 7 synthetic rows, including rows designed to quarantine",
            "canonical `resolved_symbol_aliases.json`",
            "`INPUT_SNAPSHOTS_VERIFIED=2`",
            "`SOURCE_ROWS_REPLAYED=7`",
            "do not expose quarantined row payloads",
        ),
        PIPELINE / "README.md": (
            "15-member proof package intentionally carries the exact source snapshot",
            "all 7 synthetic rows, including rows designed to quarantine",
            "canonical resolved aliases",
            "do not expose quarantined row payloads",
        ),
    }
    for path, fragments in documentation_contracts.items():
        text = path.read_text(encoding="utf-8-sig")
        for fragment in fragments:
            if fragment not in text:
                errors.append(
                    f"manifest-v2 public documentation contract missing: {path.name}: {fragment}"
                )
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
        '"hydra-market-pipeline-manifest/v2"',
        '"resolved_symbol_aliases.json"',
        '"source_snapshot.csv"',
        'print("INPUT_SNAPSHOTS_VERIFIED=2")',
        'print("SOURCE_ROWS_SNAPSHOT_VERIFIED=7")',
        "python run_recovery_demo.py --output-dir build/operations",
        "OPERATIONS_RECEIPT=PASS",
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
        "name: hydra-market-data-pipeline-sample",
        "name: Download published pipeline outputs",
        "name: Verify published pipeline artifact round-trip",
        "PUBLISHED_PIPELINE_ARTIFACT=PASS",
    )
    for fragment in pipeline_fragments:
        if fragment not in pipeline_workflow:
            errors.append(f"market-pipeline CI contract missing: {fragment}")
    pipeline_job = workflow_job_block(pipeline_workflow, "test-and-build")
    if pipeline_job is None:
        errors.append("market-pipeline CI test-and-build job is missing")
    else:
        if re.search(r"(?m)^    if\s*:", pipeline_job):
            errors.append("market-pipeline CI job must be unconditional")
        if re.search(r"(?m)^    continue-on-error\s*:", pipeline_job):
            errors.append("market-pipeline CI job must fail closed")

        pipeline_steps = workflow_steps(pipeline_job)
        artifact_step_names = (
            "Publish synthetic pipeline outputs",
            "Download published pipeline outputs",
            "Verify published pipeline artifact round-trip",
        )
        names = [name for name, _ in pipeline_steps]
        if tuple(names[-3:]) != artifact_step_names or any(
            names.count(name) != 1 for name in artifact_step_names
        ):
            errors.append("market-pipeline CI artifact steps must be unique and ordered last")

        pipeline_action_pins = {
            "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
            "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
            "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
            "actions/download-artifact": "d3f86a106a0bac45b974a628896c90dbdf5c8093",
        }
        for action, expected_sha in pipeline_action_pins.items():
            refs = re.findall(
                rf"(?m)^\s*uses:\s*{re.escape(action)}@([^\s#]+)",
                pipeline_workflow,
            )
            if not refs or any(ref != expected_sha for ref in refs):
                errors.append(f"market-pipeline CI action pin changed: {action}={refs!r}")

        step_blocks = {
            name: [block for step_name, block in pipeline_steps if step_name == name]
            for name in artifact_step_names
        }
        if all(len(step_blocks[name]) == 1 for name in artifact_step_names):
            upload, download, verify = (
                step_blocks[name][0] for name in artifact_step_names
            )
            expected_artifact = "hydra-market-data-pipeline-sample"
            if workflow_step_scalar(upload, "uses") != [
                "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
            ]:
                errors.append("market-pipeline CI upload action changed")
            if workflow_step_with_scalar(upload, "name") != [expected_artifact]:
                errors.append("market-pipeline CI upload artifact name changed")
            expected_paths = [
                "market-data-pipeline-sample/build/demo/",
                "market-data-pipeline-sample/build/operations/",
            ]
            if workflow_step_literal_lines(upload, "path") != expected_paths:
                errors.append("market-pipeline CI upload paths changed")
            if workflow_step_with_scalar(upload, "if-no-files-found") != ["error"]:
                errors.append("market-pipeline CI upload must fail when outputs are missing")
            if workflow_step_scalar(upload, "if") or workflow_step_scalar(
                upload, "continue-on-error"
            ):
                errors.append("market-pipeline CI upload must remain fail-closed")

            if workflow_step_scalar(download, "uses") != [
                "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093"
            ]:
                errors.append("market-pipeline CI download action changed")
            if workflow_step_with_scalar(download, "name") != [expected_artifact]:
                errors.append("market-pipeline CI download artifact name changed")
            if workflow_step_with_scalar(download, "path") != [
                "${{ runner.temp }}/hydra-market-data-pipeline-published"
            ]:
                errors.append("market-pipeline CI download destination changed")
            if workflow_step_scalar(download, "if") or workflow_step_scalar(
                download, "continue-on-error"
            ):
                errors.append("market-pipeline CI download must remain fail-closed")

            if workflow_step_scalar(verify, "if") or workflow_step_scalar(
                verify, "continue-on-error"
            ):
                errors.append("market-pipeline CI artifact verification must remain fail-closed")
            verify_lines = workflow_step_run_lines(verify) or []
            required_verification_lines = (
                "expected_files[f\"{label}/{relative}\"] = path",
                "actual_files[f\"{label}/{relative}\"] = path",
                "missing = sorted(set(expected_files) - set(actual_files))",
                "extra = sorted(set(actual_files) - set(expected_files))",
                "expected = hashlib.sha256(source.read_bytes()).hexdigest()",
                "actual = hashlib.sha256(actual_files[name].read_bytes()).hexdigest()",
                "require(actual == expected, f\"SHA-256 mismatch for {name}\")",
                "print(f\"PUBLISHED_PIPELINE_ARTIFACT=PASS:{len(expected_files)}\")",
                "root_names = {path.name for path in root_entries}",
                "require(root_names == set(source_roots), f\"unexpected artifact root entries: {sorted(root_names)}\")",
                "require(not path.is_symlink() and path.is_dir(), f\"invalid artifact root entry: {path}\")",
            )
            for line in required_verification_lines:
                if line not in verify_lines:
                    errors.append(
                        f"market-pipeline CI artifact verification changed: {line}"
                    )

    if "SOURCE_ROWS_REPLAYED" in pipeline_workflow:
        errors.append("market-pipeline CI must not claim independent source-row replay")

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
        "aws-actions/setup-sam@89ddb14d60e682855e3fea4be85b3c56485de310",
        "sam validate --lint --template-file template.json",
        "python -m unittest discover -s tests -t . -v",
        "python local_demo.py --output-dir build/local",
        "AWS_SAMPLE_MANIFEST=PASS",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
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
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "aws-actions/configure-aws-credentials@e1253824e5c10ff9df46874f81ed3ec929e19cfd",
        "aws-actions/setup-sam@89ddb14d60e682855e3fea4be85b3c56485de310",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "path: aws-market-data-pipeline/build/deployed/deployment_evidence.json",
        "STACK_NAME: ${{ inputs.stack_name }}-${{ github.run_id }}-${{ github.run_attempt }}",
        "if: github.ref == 'refs/heads/main'",
        "hydra-public-market-pipeline-demo-",
        "Validate deployment target",
        "Refuse to modify an existing stack",
        "Refusing to update or delete an existing stack.",
        "id: deploy_stack",
        "inputs.teardown && steps.deploy_stack.outcome != 'skipped'",
        "sam deploy",
        "--query 'Stacks[0].StackStatus'",
        "CREATE_COMPLETE",
        "timeout-minutes: 75",
        "seq 1 360",
        "hydra:deployment-run",
        "stack_owner",
        "ResourceStatus == \"DELETE_FAILED\"",
        "deployed_outputs_match_local_replay",
        "Create manifest-gated Athena consumer view",
        "sql/create_committed_normalized_events.sql",
        "FROM committed_normalized_events",
        "COUNT(*) AS accepted_rows FROM committed_normalized_events",
        '"athena_accepted_rows": int(os.environ["ATHENA_ACCEPTED_ROWS"]),',
        "start-query-execution",
        "--page-size 1000",
        "--max-items 1000",
        '--starting-token "$token"',
        "NextToken",
        "inputs.teardown",
        "sam delete",
    )
    for fragment in deploy_fragments:
        if fragment not in deploy_workflow:
            errors.append(f"aws-deploy workflow contract missing: {fragment}")

    try:
        deploy_document = yaml.load(deploy_workflow, Loader=yaml.BaseLoader)
        deploy_job = deploy_document["jobs"]["deploy-and-verify"]
        athena_steps = [
            step
            for step in deploy_job["steps"]
            if isinstance(step, dict)
            and step.get("name") == "Run bounded Athena verification query"
        ]
        expected_verifier = (
            'python "$SAMPLE_DIR/verify_athena_query_results.py" '
            '--results-path "$SAMPLE_DIR/build/deployed/athena_query_results.json" '
            '--github-env "$GITHUB_ENV"'
        )
        if len(athena_steps) != 1:
            errors.append("aws-deploy Athena verification step count changed")
        else:
            run_script = athena_steps[0].get("run", "")
            result_read = 'aws athena get-query-results --query-execution-id "$QUERY_ID" > "$SAMPLE_DIR/build/deployed/athena_query_results.json"'
            if isinstance(run_script, str):
                normalized_run_script = re.sub(
                    r"\s+",
                    " ",
                    re.sub(r"\\\s+", " ", run_script),
                ).strip()
            else:
                normalized_run_script = ""
            if (
                not normalized_run_script
                or result_read not in normalized_run_script
                or expected_verifier not in normalized_run_script
                or normalized_run_script.index(result_read)
                > normalized_run_script.index(expected_verifier)
            ):
                errors.append(
                    "aws-deploy Athena success step must save results before invoking the row-count verifier"
                )
    except (KeyError, TypeError, yaml.YAMLError, ValueError) as exc:
        errors.append(f"aws-deploy Athena verification step is invalid: {exc}")

    if re.search(r"(?m)^  (?:pull_request|push):", deploy_workflow):
        errors.append("aws-deploy workflow must remain manual-only")

    preflight_position = deploy_workflow.index(
        "- name: Refuse to modify an existing stack"
    )
    deploy_step_position = deploy_workflow.index("id: deploy_stack")
    sam_deploy_position = deploy_workflow.index("sam deploy")
    if not (preflight_position < deploy_step_position < sam_deploy_position):
        errors.append("aws-deploy teardown gate must identify the deploy attempt step")

    deploy_action_pins = {
        "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
        "aws-actions/configure-aws-credentials": "e1253824e5c10ff9df46874f81ed3ec929e19cfd",
        "aws-actions/setup-sam": "89ddb14d60e682855e3fea4be85b3c56485de310",
        "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
    }
    for action, expected_sha in deploy_action_pins.items():
        refs = re.findall(
            rf"(?m)^\s*uses:\s*{re.escape(action)}@([^\s#]+)",
            deploy_workflow,
        )
        if not refs or any(ref != expected_sha for ref in refs):
            errors.append(f"aws-deploy action pin changed: {action}={refs!r}")

    deploy_job = workflow_job_block(deploy_workflow, "deploy-and-verify")
    if deploy_job is None:
        errors.append("aws-deploy job is missing")
    else:
        deploy_steps = workflow_steps(deploy_job)
        publish_steps = [
            block
            for name, block in deploy_steps
            if name == "Publish sanitized deployment evidence"
        ]
        artifact_upload_steps = [
            block
            for _, block in deploy_steps
            if any(
                reference.startswith("actions/upload-artifact@")
                for reference in workflow_step_scalar(block, "uses")
            )
        ]
        if len(artifact_upload_steps) != 1:
            errors.append("aws-deploy must contain exactly one artifact upload")
        if len(publish_steps) != 1:
            errors.append("aws-deploy sanitized evidence upload step count changed")
        else:
            publish_step = publish_steps[0]
            if workflow_step_scalar(publish_step, "uses") != [
                "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
            ]:
                errors.append("aws-deploy evidence upload action changed")
            if workflow_step_with_scalar(publish_step, "path") != [
                "aws-market-data-pipeline/build/deployed/deployment_evidence.json"
            ]:
                errors.append("aws-deploy evidence upload must publish only the sanitized evidence JSON")
            if workflow_step_with_scalar(publish_step, "if-no-files-found") != ["error"]:
                errors.append("aws-deploy evidence upload must fail when evidence is missing")

    intelligence_workflow = (
        ROOT / ".github/workflows/governed-intelligence-sample.yml"
    ).read_text(encoding="utf-8-sig")
    validation_workflow = (
        ROOT / ".github/workflows/public-repository-validation.yml"
    ).read_text(encoding="utf-8-sig")
    for label, workflow in (
        ("governed-intelligence", intelligence_workflow),
        ("public-repository-validation", validation_workflow),
    ):
        if not workflow_event_is_unfiltered(workflow, "pull_request"):
            errors.append(f"{label} CI pull-request trigger must be unfiltered")
    intelligence_fragments = (
        'python-version: "3.11"',
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "working-directory: governed-intelligence-sample",
        "python -m unittest discover -s tests -t . -v",
        "python run_demo.py",
        "GOVERNED_INTELLIGENCE_EVAL=PASS",
        "python run_retrieval_demo.py",
        "--qrels fixtures/retrieval_qrels.json",
        "GOVERNED_RETRIEVAL_EVAL=PASS",
        "python run_grounding_demo.py",
        "GOVERNED_GROUNDING_EVAL=PASS",
        "build/grounding/",
        "timeout-minutes: 15",
        "persist-credentials: false",
        "mkdir -p governed-intelligence-sample/build/upload",
        "python -I -B governed-intelligence-sample/src/hydra_governed_intelligence/pre_upload_verifier.py --repository-root . --bundle-path governed-intelligence-sample/build/upload/hydra-governed-intelligence-proof.zip --github-output-path \"$GITHUB_OUTPUT\"",
        '"case_count"], 13',
        '"micro_recall_at_k": "0.444444"',
        '"case_count"], 8',
        '"proof_coverage_status": "PASS"',
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
        "compression-level: 0",
        "EXPECTED_BUNDLE_SHA256: ${{ steps.package_artifacts.outputs.bundle_sha256 }}",
        "EXPECTED_INPUT_SNAPSHOTS_VERIFIED: ${{ steps.package_artifacts.outputs.input_snapshots_verified }}",
        "EXPECTED_SOURCE_ROWS_REPLAYED: ${{ steps.package_artifacts.outputs.source_rows_replayed }}",
        "actual = hashlib.sha256(bundle.read_bytes()).hexdigest()",
        "require(actual == expected, f\"digest mismatch: expected {expected}, got {actual}\")",
    )
    for fragment in intelligence_fragments:
        if fragment not in intelligence_workflow:
            errors.append(f"governed-intelligence CI contract missing: {fragment}")
    if "SOURCE_ROWS_SNAPSHOT_VERIFIED" in intelligence_workflow:
        errors.append("governed-intelligence CI source-row replay signal was weakened")
    action_pins = {
        "actions/checkout": "11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
        "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
        "actions/download-artifact": "d3f86a106a0bac45b974a628896c90dbdf5c8093",
    }
    for action, expected_sha in action_pins.items():
        refs = re.findall(
            rf"(?m)^\s*uses:\s*{re.escape(action)}@([^\s#]+)",
            intelligence_workflow,
        )
        if not refs or any(ref != expected_sha for ref in refs):
            errors.append(
                f"governed-intelligence CI action pin changed: {action}={refs!r}"
            )
    required_gate_lines = (
        'require(report["case_count"], 13, "case_count")',
        'require(report["case_count"], 8, "case_count")',
        '"micro_recall_at_k": "0.444444",',
        '"macro_recall_at_k": "0.583333",',
        '"mean_reciprocal_rank": "0.666667",',
        '"proof_coverage_status": "PASS",',
    )
    for line in required_gate_lines:
        if not re.search(rf"(?m)^\s*{re.escape(line)}\s*$", intelligence_workflow):
            errors.append(f"governed-intelligence CI gate line changed: {line}")
    if re.search(r"\bassert\s", intelligence_workflow):
        errors.append("governed-intelligence CI must not use removable Python asserts")
    if re.search(r"(?m)^  pull_request_target\s*:", intelligence_workflow):
        errors.append("governed-intelligence CI must not use pull_request_target")
    permissions_match = re.search(
        r"(?ms)^permissions:\s*\r?\n(?P<body>.*?)(?=^\S|\Z)",
        intelligence_workflow,
    )
    permission_lines = (
        []
        if permissions_match is None
        else [
            line.strip()
            for line in permissions_match.group("body").splitlines()
            if line.strip()
        ]
    )
    if permission_lines != ["contents: read"]:
        errors.append(
            "governed-intelligence CI permissions must remain contents: read only"
        )

    windows_job = workflow_job_block(
        intelligence_workflow, "windows-pre-upload-verifier"
    )
    if windows_job is None:
        errors.append("governed-intelligence CI Windows verifier job is missing")
    else:
        if not re.search(r"(?m)^    runs-on:\s*windows-latest\s*$", windows_job):
            errors.append("governed-intelligence CI verifier must run on Windows")
        if re.search(r"(?m)^    if\s*:", windows_job):
            errors.append("governed-intelligence CI Windows verifier job must be unconditional")
        if re.search(r"(?m)^    continue-on-error\s*:", windows_job):
            errors.append("governed-intelligence CI Windows verifier job must fail closed")
        windows_steps = workflow_steps(windows_job)
        expected_windows_steps = (
            "Checkout",
            "Set up Python",
            "Run pre-upload verifier tests on Windows",
        )
        if tuple(name for name, _ in windows_steps) != expected_windows_steps:
            errors.append("governed-intelligence CI Windows verifier steps changed")
        if "working-directory: governed-intelligence-sample" not in windows_job:
            errors.append("governed-intelligence CI Windows test directory changed")
        if 'python-version: "3.11"' not in windows_job:
            errors.append("governed-intelligence CI Windows Python version changed")
        if "PYTHONPATH: src" not in windows_job:
            errors.append("governed-intelligence CI Windows PYTHONPATH changed")
        windows_checkout = [block for name, block in windows_steps if name == "Checkout"]
        if len(windows_checkout) != 1 or workflow_step_scalar(
            windows_checkout[0], "uses"
        ) != ["actions/checkout@11d5960a326750d5838078e36cf38b85af677262"]:
            errors.append("governed-intelligence CI Windows checkout action changed")
        windows_python = [block for name, block in windows_steps if name == "Set up Python"]
        if len(windows_python) != 1 or workflow_step_scalar(
            windows_python[0], "uses"
        ) != ["actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"]:
            errors.append("governed-intelligence CI Windows Python action changed")
        windows_test = [
            block
            for name, block in windows_steps
            if name == "Run pre-upload verifier tests on Windows"
        ]
        if len(windows_test) != 1:
            errors.append("governed-intelligence CI Windows verifier test step changed")
        else:
            if workflow_step_scalar(windows_test[0], "if"):
                errors.append("governed-intelligence CI Windows verifier test must run unconditionally")
            if workflow_step_scalar(windows_test[0], "continue-on-error"):
                errors.append("governed-intelligence CI Windows verifier test must fail closed")
            if workflow_step_scalar(windows_test[0], "run") != [
                "python -m unittest tests.test_pre_upload_verifier -v"
            ]:
                errors.append("governed-intelligence CI Windows verifier test command changed")

    evaluate_job = workflow_job_block(intelligence_workflow, "evaluate")
    if evaluate_job is None:
        errors.append("governed-intelligence CI evaluate job is missing")
        return
    if re.search(r"(?m)^    if\s*:", evaluate_job):
        errors.append("governed-intelligence CI evaluate job must be unconditional")
    if re.search(r"(?m)^    continue-on-error\s*:", evaluate_job):
        errors.append("governed-intelligence CI evaluate job must fail closed")

    if not re.search(
        r"(?m)^    needs:\s*windows-pre-upload-verifier\s*$", evaluate_job
    ):
        errors.append(
            "governed-intelligence CI evaluate job must depend on Windows verifier"
        )

    required_active_steps = (
        "Checkout",
        "Set up Python",
        "Build governed synthetic pipeline artifacts",
        "Run pre-model control tests",
        "Build deterministic context and evaluation receipts",
        "Check evaluation report contract",
        "Build deterministic lexical retrieval receipts",
        "Check retrieval report contract and declared input digests",
        "Build deterministic structured grounding receipts",
        "Check grounding report contract and declared input digests",
        "Prepare artifact destination",
        "Verify and package exact artifact snapshots",
    )
    upload_name = "Publish synthetic pre-model receipts"
    download_name = "Download published proof artifact"
    digest_check_name = "Verify published proof digest"
    expected_step_sequence = required_active_steps + (
        upload_name,
        download_name,
        digest_check_name,
    )
    actual_steps = workflow_steps(evaluate_job)
    actual_step_names = tuple(name for name, _ in actual_steps)
    if actual_step_names != expected_step_sequence:
        errors.append(
            "governed-intelligence CI complete step sequence changed: "
            f"{actual_step_names!r}"
        )

    step_blocks: dict[str, str] = {}
    for required_name in required_active_steps + (download_name, digest_check_name):
        matches = [block for name, block in actual_steps if name == required_name]
        if len(matches) != 1:
            errors.append(
                "governed-intelligence CI required active step count changed: "
                f"{required_name}={len(matches)}"
            )
            continue
        step_blocks[required_name] = matches[0]
        if workflow_step_scalar(matches[0], "if"):
            errors.append(
                f"governed-intelligence CI required step must be unconditional: {required_name}"
            )
        if workflow_step_scalar(matches[0], "continue-on-error"):
            errors.append(
                f"governed-intelligence CI required step must fail closed: {required_name}"
            )

    upload_matches = [block for name, block in actual_steps if name == upload_name]
    if len(upload_matches) != 1:
        errors.append(
            "governed-intelligence CI upload step count changed: "
            f"{len(upload_matches)}"
        )
    else:
        upload_block = upload_matches[0]
        expected_upload_condition = (
            "${{ success() && steps.package_artifacts.outcome == 'success' }}"
        )
        if workflow_step_scalar(upload_block, "if") != [expected_upload_condition]:
            errors.append("governed-intelligence CI upload success gate changed")
        if workflow_step_scalar(upload_block, "continue-on-error"):
            errors.append("governed-intelligence CI upload step must fail closed")
        if workflow_step_scalar(upload_block, "uses") != [
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
        ]:
            errors.append("governed-intelligence CI upload action binding changed")
        if workflow_step_with_scalar(upload_block, "name") != [
            "hydra-governed-intelligence-sample"
        ]:
            errors.append("governed-intelligence CI upload artifact name changed")
        expected_upload_path = (
            "governed-intelligence-sample/build/upload/"
            "hydra-governed-intelligence-proof.zip"
        )
        if workflow_step_with_scalar(upload_block, "path") != [expected_upload_path]:
            errors.append("governed-intelligence CI upload path changed")
        if workflow_step_with_scalar(upload_block, "compression-level") != ["0"]:
            errors.append("governed-intelligence CI upload compression changed")
        if workflow_step_with_scalar(upload_block, "if-no-files-found") != ["error"]:
            errors.append(
                "governed-intelligence CI upload missing-file behavior changed"
            )

    prepare_name = "Prepare artifact destination"
    if prepare_name in step_blocks:
        if workflow_step_scalar(step_blocks[prepare_name], "run") != [
            "mkdir -p governed-intelligence-sample/build/upload"
        ]:
            errors.append("governed-intelligence CI artifact destination setup changed")

    verifier_name = "Verify and package exact artifact snapshots"
    if verifier_name in step_blocks:
        verifier_block = step_blocks[verifier_name]
        if workflow_step_scalar(verifier_block, "id") != ["package_artifacts"]:
            errors.append("governed-intelligence CI package step ID changed")
        expected_invocation = (
            "python -I -B governed-intelligence-sample/src/"
            "hydra_governed_intelligence/pre_upload_verifier.py --repository-root . "
            "--bundle-path governed-intelligence-sample/build/upload/"
            "hydra-governed-intelligence-proof.zip --github-output-path "
            '"$GITHUB_OUTPUT"'
        )
        if workflow_step_scalar(verifier_block, "run") != [expected_invocation]:
            errors.append(
                "governed-intelligence CI package invocation changed"
            )
        if re.search(r"(?m)^        run:\s*[|>]", verifier_block):
            errors.append(
                "governed-intelligence CI package step must not use inline code"
            )

    if download_name in step_blocks:
        download_block = step_blocks[download_name]
        if workflow_step_scalar(download_block, "uses") != [
            "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093"
        ]:
            errors.append("governed-intelligence CI download action binding changed")
        if workflow_step_with_scalar(download_block, "name") != [
            "hydra-governed-intelligence-sample"
        ]:
            errors.append("governed-intelligence CI download artifact name changed")
        if workflow_step_with_scalar(download_block, "path") != [
            "${{ runner.temp }}/hydra-governed-intelligence-published-proof"
        ]:
            errors.append("governed-intelligence CI download path changed")

    if digest_check_name in step_blocks:
        digest_block = step_blocks[digest_check_name]
        if workflow_step_scalar(digest_block, "uses"):
            errors.append("governed-intelligence CI digest check must run Python")
        if workflow_step_with_scalar(digest_block, "DOWNLOADED_BUNDLE_PATH") != [
            "${{ runner.temp }}/hydra-governed-intelligence-published-proof/"
            "hydra-governed-intelligence-proof.zip"
        ]:
            errors.append("governed-intelligence CI downloaded bundle path changed")
        if workflow_step_with_scalar(digest_block, "EXPECTED_BUNDLE_SHA256") != [
            "${{ steps.package_artifacts.outputs.bundle_sha256 }}"
        ]:
            errors.append("governed-intelligence CI expected bundle digest changed")
        expected_digest_run = [
            "python -I -B - <<'PY'",
            "import hashlib",
            "import os",
            "import re",
            "from pathlib import Path",
            "def require(condition, detail):",
            "if not condition:",
            'raise SystemExit(f"PUBLISHED_ARTIFACT_DIGEST_CHECK=FAIL: {detail}")',
            'expected = os.environ.get("EXPECTED_BUNDLE_SHA256", "")',
            'input_snapshots = os.environ.get("EXPECTED_INPUT_SNAPSHOTS_VERIFIED", "")',
            'source_rows = os.environ.get("EXPECTED_SOURCE_ROWS_REPLAYED", "")',
            'bundle = Path(os.environ.get("DOWNLOADED_BUNDLE_PATH", ""))',
            'require(re.fullmatch(r"[0-9a-f]{64}", expected) is not None, "expected digest is invalid")',
            'require(input_snapshots == "2", "verified input snapshot count changed")',
            'require(source_rows == "7", "replayed source row count changed")',
            'require(bundle.is_file() and not bundle.is_symlink(), "downloaded inner ZIP is missing")',
            "entries = sorted(entry.name for entry in bundle.parent.iterdir())",
            'require(entries == [bundle.name], "downloaded artifact member set changed")',
            "actual = hashlib.sha256(bundle.read_bytes()).hexdigest()",
            'require(actual == expected, f"digest mismatch: expected {expected}, got {actual}")',
            'print(f"PUBLISHED_ARTIFACT_DIGEST_CHECK=PASS:{actual}")',
            "PY",
        ]
        if workflow_step_run_lines(digest_block) != expected_digest_run:
            errors.append(
                "governed-intelligence CI downloaded digest check changed"
            )


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
        "ManifestTable": "AWS::Glue::Table",
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
    print("VALIDATION_SCOPE=REPOSITORY_CONTROLLED_SELF_CHECK")
    print(f"REQUIRED_PATHS={len(REQUIRED_PATHS)}")
    print(f"PUBLIC_TEXT_FILES={len(active_public_text_files())}")
    print("FAIL_CLOSED_CONTRACT=PASS")
    print("MARKDOWN_LINKS=PASS")
    print("VALIDATOR_CI_CONTRACT=PASS")
    print("MARKET_PIPELINE_CI_CONTRACT=PASS")
    print("SQL_SAMPLE_CI_CONTRACT=PASS")
    print("AWS_SAMPLE_CI_CONTRACT=PASS")
    print("AWS_DEPLOY_WORKFLOW_CONTRACT=PASS")
    print("GOVERNED_INTELLIGENCE_SAFETY_CONTRACT=PASS")
    print("GOVERNED_INTELLIGENCE_CI_CONTRACT=PASS")
    print("AWS_TEMPLATE_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
