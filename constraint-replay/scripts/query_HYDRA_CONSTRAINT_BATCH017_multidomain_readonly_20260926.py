from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from hydra_constraint_replay.multidomain import (
    ConstraintMultiDomainQueryService,
    MultiDomainQueryError,
)

ROOT=Path(__file__).resolve().parents[2]


def main() -> int:
    parser=argparse.ArgumentParser(
        description="Read-only multi-domain HYDRA Constraint historical query surface."
    )
    sub=parser.add_subparsers(dest="operation",required=True)

    sub.add_parser("summary")
    sub.add_parser("integrity")

    case_parser=sub.add_parser("case")
    case_parser.add_argument("case_id")
    case_parser.add_argument("--max-depth",type=int,default=3)

    entity_parser=sub.add_parser("entity")
    entity_parser.add_argument("entity_id")
    entity_parser.add_argument("--max-depth",type=int,default=3)

    list_parser=sub.add_parser("list")
    list_parser.add_argument("--outcome-class",choices=["PARTIAL_REALIZATION","UNEVALUABLE"])
    list_parser.add_argument("--event-type")
    list_parser.add_argument("--physical-entity-id")
    list_parser.add_argument("--limit",type=int)

    args=parser.parse_args()

    try:
        service=ConstraintMultiDomainQueryService(ROOT)
        if args.operation=="summary":
            result=service.summary()
        elif args.operation=="integrity":
            result=service.integrity()
        elif args.operation=="case":
            result=service.case(args.case_id,max_depth=args.max_depth)
        elif args.operation=="entity":
            result=service.entity_usage(args.entity_id,max_depth=args.max_depth)
        else:
            result=service.list_cases(
                outcome_class=args.outcome_class,
                event_type=args.event_type,
                physical_entity_id=args.physical_entity_id,
                limit=args.limit,
            )
    except MultiDomainQueryError as exc:
        print(str(exc),file=sys.stderr)
        return 2

    sys.stdout.write(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
