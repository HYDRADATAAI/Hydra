from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from hydra_constraint_replay.operating import (
    ConstraintOperatingReportService,
    OperatingReportError,
)

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_EXPECTED=(
    "constraint-replay/operating/"
    "HYDRA_CONSTRAINT_BATCH018_OPERATING_SNAPSHOT_20260926.json"
)


def main() -> int:
    parser=argparse.ArgumentParser(
        description="Generate/query the HYDRA Constraint Batch 018 operating snapshot."
    )
    sub=parser.add_subparsers(dest="operation",required=True)

    snapshot_parser=sub.add_parser("snapshot")
    snapshot_parser.add_argument("--check")
    snapshot_parser.add_argument("--output")

    sub.add_parser("readiness")
    sub.add_parser("gaps")

    dimension_parser=sub.add_parser("dimension")
    dimension_parser.add_argument("dimension")

    args=parser.parse_args()

    try:
        service=ConstraintOperatingReportService(ROOT)
        if args.operation=="snapshot":
            result=service.snapshot()
        elif args.operation=="readiness":
            result=service.readiness()
        elif args.operation=="gaps":
            result=service.gaps()
        else:
            result=service.dimension(args.dimension)
    except OperatingReportError as exc:
        print(str(exc),file=sys.stderr)
        return 2

    rendered=json.dumps(result,indent=2,sort_keys=True)+"\n"

    if args.operation=="snapshot" and args.output:
        target=ROOT/args.output
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(rendered,encoding="utf-8")

    if args.operation=="snapshot" and args.check:
        expected=(ROOT/args.check).read_text(encoding="utf-8")
        if expected!=rendered:
            print(f"Batch 018 operating snapshot mismatch: {args.check}",file=sys.stderr)
            return 3

    sys.stdout.write(rendered)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
