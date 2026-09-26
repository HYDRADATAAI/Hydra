"""Run the cloud transform locally without AWS credentials or network access."""

from __future__ import annotations

import argparse
from pathlib import Path

from function.processor import process_csv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("fixtures/synthetic_market_events.csv"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("build/local"))
    args = parser.parse_args()

    batch = process_csv(args.input.read_bytes())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in batch.artifacts.items():
        (args.output_dir / name).write_bytes(content)

    print("AWS_SAMPLE_LOCAL_STATUS=PASS")
    print(f"PIPELINE_RUN_ID={batch.run_id}")
    print(f"ACCEPTED_ROWS={len(batch.accepted)}")
    print(f"QUARANTINED_ROWS={len(batch.quarantined)}")
    print(f"OUTPUT_DIR={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
