from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "constraint-t1-raw-artifact-store" / "src"
sys.path.insert(0, str(SRC))

from hydra_constraint_t1_raw.first_slice_materialization import (  # noqa: E402
    FirstSliceMaterializationError,
    validate_public_materialization_attestation,
)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FirstSliceMaterializationError(f"top-level object required: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a sanitized public first-slice T1 materialization attestation."
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
    args = parser.parse_args()

    try:
        validate_public_materialization_attestation(
            attestation=load(Path(args.attestation)),
            registry=load(Path(args.registry)),
        )
    except (OSError, json.JSONDecodeError, FirstSliceMaterializationError) as exc:
        print("CONSTRAINT_T1_FIRST_SLICE_ATTESTATION=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("CONSTRAINT_T1_FIRST_SLICE_ATTESTATION=PASS")
    print("RAW_BYTES_REQUIRED_FOR_PUBLIC_VALIDATION=NO")
    print("PRIVATE_PATHS_ALLOWED_IN_ATTESTATION=NO")
    print("HISTORICAL_BACKDATING_ALLOWED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
