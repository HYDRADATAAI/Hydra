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
)
from hydra_constraint_t1_raw.replay_lineage import (  # noqa: E402
    ReplayLineageError,
    build_replay_lineage_packet,
    select_replay_members,
)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReplayLineageError(f"top-level object required: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic replay lineage from a sanitized T1 attestation."
    )
    parser.add_argument("--attestation", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--as-of")
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
        registry = load(Path(args.registry))
        packet = build_replay_lineage_packet(
            attestation=load(Path(args.attestation)),
            registry=registry,
        )
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        visible = None
        if args.as_of:
            visible = select_replay_members(
                packet=packet,
                registry=registry,
                as_of=args.as_of,
            )
    except (OSError, json.JSONDecodeError, FirstSliceMaterializationError, ReplayLineageError) as exc:
        print("CONSTRAINT_T1_FIRST_SLICE_REPLAY_LINEAGE=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("CONSTRAINT_T1_FIRST_SLICE_REPLAY_LINEAGE=PASS")
    print(f"SOURCE_VERSION_LINEAGE_COUNT={packet['source_count']}")
    print("ORDINARY_SOURCE_VERSION_HASH_LINEAGE_COMPLETE=YES")
    print("ORDINARY_CURRENT_SOURCE_SET_READY=YES")
    print("STRICT_HISTORICAL_REPLAY_READY=NO")
    print("HISTORICAL_BACKDATING_PERFORMED=NO")
    if visible is not None:
        print(f"AS_OF_VISIBLE_SOURCE_COUNT={len(visible)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
