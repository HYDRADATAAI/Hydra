"""Command-line entry point for synthetic structured-output grounding checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .context import ContractError, IntegrityError, load_evidence
from .grounding import load_grounding_policy, run_grounding_evaluation
from .retrieval import load_retrieval_policy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate synthetic structured candidate claims against governed retrieval."
    )
    parser.add_argument("--pipeline-output-dir", required=True, type=Path)
    parser.add_argument("--retrieval-policy", required=True, type=Path)
    parser.add_argument("--grounding-policy", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        evidence = load_evidence(args.pipeline_output_dir)
        retrieval_policy = load_retrieval_policy(args.retrieval_policy)
        grounding_policy = load_grounding_policy(args.grounding_policy)
        report = run_grounding_evaluation(
            cases_path=args.cases,
            evidence=evidence,
            retrieval_policy=retrieval_policy,
            grounding_policy=grounding_policy,
            output_dir=args.output_dir,
        )
    except (ContractError, IntegrityError) as exc:
        print("GROUNDING_VALIDATION_STATUS=FAIL_CLOSED", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 2

    print(f"GROUNDING_VALIDATION_STATUS={report['status']}")
    print(f"GROUNDING_CASES={report['case_count']}")
    print(f"CLAIM_PASSES={report['checks']['claim_pass_count']}")
    print(f"CLAIM_FAILURES={report['checks']['claim_fail_count']}")
    print(f"MODEL_EXECUTIONS={report['checks']['unauthorized_model_execution_count']}")
    print(f"EXTERNAL_ACTIONS={report['checks']['unauthorized_external_action_count']}")
    print(f"REPORT={args.output_dir / 'grounding_evaluation_report.json'}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
