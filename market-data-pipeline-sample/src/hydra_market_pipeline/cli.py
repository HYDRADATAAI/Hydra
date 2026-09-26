"""Command-line entry point for the public synthetic pipeline sample."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import ContractError, run_pipeline
from .writers import write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the HYDRA synthetic market-data pipeline sample."
    )
    parser.add_argument("--input", required=True, type=Path, help="Input CSV path.")
    parser.add_argument(
        "--aliases",
        required=True,
        type=Path,
        help="JSON symbol-alias map.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory for JSONL, CSV, quarantine, and manifest outputs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_pipeline(input_csv=args.input, aliases_path=args.aliases)
        outputs = write_outputs(result, output_dir=args.output_dir)
    except ContractError as exc:
        print("PIPELINE_STATUS=CONTRACT_ERROR", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 2

    print("PIPELINE_STATUS=PASS")
    print(f"PIPELINE_RUN_ID={result.pipeline_run_id}")
    print(f"ACCEPTED_ROWS={len(result.accepted)}")
    print(f"QUARANTINED_ROWS={len(result.quarantined)}")
    print(f"MANIFEST={outputs['manifest']}")
    print(f"NORMALIZED_CSV={outputs['normalized_csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
