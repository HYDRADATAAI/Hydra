"""Command-line entry point for the governed-intelligence evaluation sample."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .context import ContractError, IntegrityError, load_evidence, load_policy
from .evaluation import run_evaluation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and evaluate deterministic pre-model HYDRA context packets."
    )
    parser.add_argument("--pipeline-output-dir", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        evidence = load_evidence(args.pipeline_output_dir)
        policy = load_policy(args.policy)
        report = run_evaluation(
            cases_path=args.cases,
            evidence=evidence,
            policy=policy,
            output_dir=args.output_dir,
        )
    except (ContractError, IntegrityError) as exc:
        print("GOVERNED_INTELLIGENCE_STATUS=FAIL_CLOSED", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 2

    print(f"GOVERNED_INTELLIGENCE_STATUS={report['status']}")
    print(f"EVALUATION_CASES={report['case_count']}")
    print(f"MODEL_EXECUTIONS={report['checks']['unauthorized_model_execution_count']}")
    print(f"REPORT={args.output_dir / 'evaluation_report.json'}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
