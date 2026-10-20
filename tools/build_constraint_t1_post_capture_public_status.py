from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "constraint-t1-raw-artifact-store" / "src"
sys.path.insert(0, str(SRC))

from hydra_constraint_t1_raw.post_capture_status import (  # noqa: E402
    PostCaptureStatusError,
    build_public_status_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a repo-safe public status from a validated private T1 materialization attestation."
    )
    parser.add_argument("--attestation", required=True)
    parser.add_argument(
        "--registry",
        default=str(
            ROOT
            / "docs"
            / "constraint"
            / "first_slice"
            / "ai_data_center_power_infrastructure_v1"
            / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"
        ),
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        status = build_public_status_file(
            attestation_path=args.attestation,
            registry_path=args.registry,
            output_path=args.output,
        )
    except (OSError, PostCaptureStatusError) as exc:
        print("CONSTRAINT_T1_POST_CAPTURE_PUBLIC_STATUS=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("CONSTRAINT_T1_POST_CAPTURE_PUBLIC_STATUS=PASS")
    print(f"SOURCE_COUNT={status['source_count']}")
    print(f"ORDINARY_T2_ELIGIBLE_COUNT={status['ordinary_t2_eligible_count']}")
    print("RAW_MATERIALIZATION_BLOCKER=CLOSED_BY_VALIDATED_PRIVATE_T1_ATTESTATION")
    print("ORDINARY_POINT_IN_TIME_REPLAY_READY=NO")
    print("NATIVE_SIGNED_T5_T6_RECEIPT_PRESENT=NO")
    print("CANONICAL_ADMISSION_PROMOTED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
