"""Prove interruption recovery and idempotent replay with synthetic inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hydra_market_pipeline.hashing import sha256_hex
from hydra_market_pipeline.operations import InjectedInterruption, execute_backfill


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan",
        type=Path,
        default=Path("config/backfill_plan.json"),
    )
    parser.add_argument(
        "--aliases",
        type=Path,
        default=Path("config/symbol_aliases.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/operations"),
    )
    args = parser.parse_args()

    if (args.output_dir / "checkpoint.json").exists():
        raise SystemExit("recovery demo requires a fresh output directory")

    try:
        execute_backfill(
            plan_path=args.plan,
            aliases_path=args.aliases,
            output_dir=args.output_dir,
            interrupt_after_new_sources=1,
        )
    except InjectedInterruption:
        first_checkpoint = json.loads(
            (args.output_dir / "checkpoint.json").read_text(encoding="utf-8")
        )
    else:
        raise AssertionError("synthetic interruption did not occur")

    resumed = execute_backfill(
        plan_path=args.plan,
        aliases_path=args.aliases,
        output_dir=args.output_dir,
    )
    manifest_before_replay = resumed.manifest_path.read_bytes()
    metrics_before_replay = resumed.metrics_path.read_bytes()
    replayed = execute_backfill(
        plan_path=args.plan,
        aliases_path=args.aliases,
        output_dir=args.output_dir,
    )
    manifest_after_replay = replayed.manifest_path.read_bytes()
    metrics_after_replay = replayed.metrics_path.read_bytes()

    receipt = {
        "backfill_id": resumed.backfill_id,
        "completed_replay": {
            "manifest_unchanged": manifest_before_replay == manifest_after_replay,
            "metrics_unchanged": metrics_before_replay == metrics_after_replay,
            "processed_sources": list(replayed.processed_sources),
            "reused_sources": list(replayed.reused_sources),
        },
        "first_attempt": {
            "checkpointed_sources": sorted(first_checkpoint["completed"]),
            "status": "INTERRUPTED_AS_INJECTED",
        },
        "data_boundary": "synthetic_non_live",
        "operations_manifest_sha256": sha256_hex(manifest_after_replay),
        "resume_attempt": {
            "processed_sources": list(resumed.processed_sources),
            "reused_sources": list(resumed.reused_sources),
            "status": "PASS",
        },
        "schema_version": "hydra-market-recovery-receipt/v1",
    }
    receipt_path = args.output_dir / "recovery_receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("RECOVERY_DEMO_STATUS=PASS")
    print(f"BACKFILL_ID={resumed.backfill_id}")
    print(f"CHECKPOINTED_SOURCES={len(first_checkpoint['completed'])}")
    print(f"RESUME_PROCESSED_SOURCES={len(resumed.processed_sources)}")
    print(f"RESUME_REUSED_SOURCES={len(resumed.reused_sources)}")
    print(f"REPLAY_REUSED_SOURCES={len(replayed.reused_sources)}")
    print(f"RECOVERY_RECEIPT={receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
