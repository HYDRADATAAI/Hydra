#!/usr/bin/env python3
"""Build Batch033 ordinary-T2 source-version lineage from public Batch032 custody."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "constraint-t1-raw-artifact-store" / "src"
sys.path.insert(0, str(SRC))

from hydra_constraint_t1_raw.ordinary_t2_lineage import (  # noqa: E402
    OrdinaryT2LineageError,
    build_ordinary_t2_lineage,
)

SLICE_ID = "SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
QUEUE = (
    ROOT
    / "docs"
    / "constraint"
    / "second_slice"
    / "semiconductor_advanced_packaging_critical_materials_v1"
    / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json"
)
ATTESTATION = (
    ROOT
    / "docs"
    / "constraint"
    / "validation"
    / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH032_SEMICONDUCTOR_T1_MATERIALIZATION_ATTESTATION_V001_20260928.json"
)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OrdinaryT2LineageError(f"top-level object required: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        queue = load(QUEUE)
        rows = queue.get("queue")
        if not isinstance(rows, list):
            raise OrdinaryT2LineageError("Batch031 queue missing")
        packet = build_ordinary_t2_lineage(
            attestation=load(ATTESTATION),
            source_records=rows,
            expected_slice_id=SLICE_ID,
        )
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(
            (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
    except (OSError, json.JSONDecodeError, OrdinaryT2LineageError) as exc:
        print("BATCH033_ORDINARY_T2_NORMALIZATION=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("BATCH033_ORDINARY_T2_NORMALIZATION=PASS")
    print(f"SOURCE_COUNT={packet['source_count']}")
    print(f"NORMALIZED_SOURCE_VERSIONS={packet['normalized_source_version_count']}")
    print("ORDINARY_CURRENT_SOURCE_SET_READY=YES")
    print("STRICT_HISTORICAL_REPLAY_READY=NO")
    print("CANONICAL_EVIDENCE_ADMISSION_PROMOTED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
