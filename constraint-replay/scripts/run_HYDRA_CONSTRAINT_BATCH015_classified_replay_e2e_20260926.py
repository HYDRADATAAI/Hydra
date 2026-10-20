from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from hydra_constraint_replay.end_to_end import run_classified_replay_e2e


ROOT=Path(__file__).resolve().parents[2]
DEFAULT_REPLAY="constraint-replay/corpus/HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl"
DEFAULT_CLASSIFIED="constraint-replay/corpus/HYDRA_CONSTRAINT_CLASSIFIED_GOLD_UNCALIBRATED_BATCH014_20260926.jsonl"
DEFAULT_PROMOTION="constraint-replay/corpus/HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH014_20260926.json"
DEFAULT_EXPECTED="constraint-replay/runs/HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_RUN_20260926.json"


def main() -> int:
    parser=argparse.ArgumentParser(
        description="Run the HYDRA Constraint Batch 015 classified historical replay."
    )
    parser.add_argument("--replay-ready",default=DEFAULT_REPLAY)
    parser.add_argument("--classified-gold",default=DEFAULT_CLASSIFIED)
    parser.add_argument("--promotion-audit",default=DEFAULT_PROMOTION)
    parser.add_argument("--output")
    parser.add_argument("--check",default=None)
    args=parser.parse_args()

    result=run_classified_replay_e2e(
        ROOT,args.replay_ready,args.classified_gold,args.promotion_audit
    )
    rendered=json.dumps(result,indent=2,sort_keys=True)+"\n"

    if args.output:
        target=ROOT/args.output
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(rendered,encoding="utf-8")

    if args.check:
        expected_path=ROOT/args.check
        expected=expected_path.read_text(encoding="utf-8")
        if expected != rendered:
            print(
                f"Batch 015 E2E output mismatch: {args.check}",
                file=sys.stderr,
            )
            return 2

    if not args.output:
        sys.stdout.write(rendered)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
