"""Command-line entry point for the governed lexical retrieval benchmark."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .context import ContractError, IntegrityError, load_evidence
from .retrieval import load_retrieval_policy
from .retrieval_evaluation import run_retrieval_evaluation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic lexical retrieval over governed HYDRA records."
    )
    parser.add_argument("--pipeline-output-dir", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--qrels", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        evidence = load_evidence(args.pipeline_output_dir)
        policy = load_retrieval_policy(args.policy)
        report = run_retrieval_evaluation(
            cases_path=args.cases,
            qrels_path=args.qrels,
            evidence=evidence,
            policy=policy,
            output_dir=args.output_dir,
        )
    except (ContractError, IntegrityError) as exc:
        print("GOVERNED_RETRIEVAL_STATUS=FAIL_CLOSED", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 2

    print(f"GOVERNED_RETRIEVAL_STATUS={report['status']}")
    print(f"RETRIEVAL_CASES={report['case_count']}")
    print(f"MICRO_RECALL_AT_K={report['checks']['micro_recall_at_k']}")
    print(f"MACRO_RECALL_AT_K={report['checks']['macro_recall_at_k']}")
    print(f"MEAN_RECIPROCAL_RANK={report['checks']['mean_reciprocal_rank']}")
    print(f"MODEL_EXECUTIONS={report['checks']['unauthorized_model_execution_count']}")
    print(f"REPORT={args.output_dir / 'retrieval_evaluation_report.json'}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
