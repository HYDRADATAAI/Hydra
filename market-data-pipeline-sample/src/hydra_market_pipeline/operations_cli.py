"""CLI for the checkpointed synthetic backfill sample."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .operations import OperationsError, execute_backfill
from .pipeline import ContractError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the HYDRA synthetic checkpointed backfill sample."
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--aliases", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        outcome = execute_backfill(
            plan_path=args.plan,
            aliases_path=args.aliases,
            output_dir=args.output_dir,
        )
    except (ContractError, OperationsError) as exc:
        print("BACKFILL_STATUS=CONTRACT_ERROR", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 2

    print("BACKFILL_STATUS=PASS")
    print(f"BACKFILL_ID={outcome.backfill_id}")
    print(f"PROCESSED_SOURCES={len(outcome.processed_sources)}")
    print(f"REUSED_SOURCES={len(outcome.reused_sources)}")
    print(f"OPERATIONS_MANIFEST={outcome.manifest_path}")
    print(f"METRICS={outcome.metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
