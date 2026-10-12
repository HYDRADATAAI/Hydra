from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from hydra_constraint_replay.operating_taxonomy import (
    ConstraintOperatingReportV2Service,
    OperatingTaxonomyClosureError,
)

ROOT=Path(__file__).resolve().parents[2]


def main() -> int:
    parser=argparse.ArgumentParser(
        description="Generate/query the HYDRA Constraint Batch 019 operating taxonomy-closure snapshot."
    )
    sub=parser.add_subparsers(dest="operation",required=True)

    snapshot=sub.add_parser("snapshot")
    snapshot.add_argument("--check")
    snapshot.add_argument("--output")

    sub.add_parser("readiness")
    sub.add_parser("gaps")

    dimension=sub.add_parser("dimension")
    dimension.add_argument("dimension")

    args=parser.parse_args()

    try:
        service=ConstraintOperatingReportV2Service(ROOT)
        if args.operation=="snapshot":
            result=service.snapshot()
        elif args.operation=="readiness":
            result=service.readiness()
        elif args.operation=="gaps":
            result=service.gaps()
        else:
            result=service.dimension(args.dimension)
    except OperatingTaxonomyClosureError as exc:
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
            print(
                f"Batch 019 operating snapshot mismatch: {args.check}",
                file=sys.stderr,
            )
            return 3

    sys.stdout.write(rendered)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
