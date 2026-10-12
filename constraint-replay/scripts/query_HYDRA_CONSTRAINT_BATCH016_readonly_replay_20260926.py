from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from hydra_constraint_replay.query import ConstraintQueryError, ConstraintReplayQueryService


ROOT=Path(__file__).resolve().parents[2]


def _bool(value: str) -> bool:
    lowered=value.strip().lower()
    if lowered=="true":
        return True
    if lowered=="false":
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def main() -> int:
    parser=argparse.ArgumentParser(
        description="Read-only query surface over the frozen HYDRA Constraint Batch 015 replay."
    )
    sub=parser.add_subparsers(dest="operation",required=True)

    sub.add_parser("summary")
    sub.add_parser("integrity")

    case_parser=sub.add_parser("case")
    case_parser.add_argument("case_id")

    list_parser=sub.add_parser("list")
    list_parser.add_argument("--outcome-class",choices=["PARTIAL_REALIZATION","UNEVALUABLE"])
    list_parser.add_argument("--calibrated",type=_bool)
    list_parser.add_argument("--min-lead-days",type=float)
    list_parser.add_argument("--max-lead-days",type=float)
    list_parser.add_argument("--calibration-blocker")
    list_parser.add_argument(
        "--sort-by",
        choices=["case_id","lead_time_asc","lead_time_desc"],
        default="case_id",
    )
    list_parser.add_argument("--limit",type=int)

    args=parser.parse_args()

    try:
        service=ConstraintReplayQueryService(ROOT)
        if args.operation=="summary":
            result=service.summary()
        elif args.operation=="integrity":
            result=service.integrity()
        elif args.operation=="case":
            result=service.case(args.case_id)
        else:
            result=service.list_cases(
                outcome_class=args.outcome_class,
                calibrated=args.calibrated,
                min_lead_days=args.min_lead_days,
                max_lead_days=args.max_lead_days,
                calibration_blocker=args.calibration_blocker,
                sort_by=args.sort_by,
                limit=args.limit,
            )
    except ConstraintQueryError as exc:
        print(str(exc),file=sys.stderr)
        return 2

    sys.stdout.write(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
