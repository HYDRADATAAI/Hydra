from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "t6-fail-closed-validator" / "src"
sys.path.insert(0, str(SRC))

from hydra_t6_failclosed.owner_seam_conformance import (  # noqa: E402
    OwnerSeamConformanceError,
    validate_owner_seams,
)


SLICE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"
PATHS = {
    "claims": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_CLAIM_REGISTRY_V001_20260925.json",
    "candidates": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_T5_CANDIDATE_PROPOSALS_V001_20260925.json",
    "beneficiaries": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BENEFICIARY_EVALUATIONS_V001_20260925.json",
    "overlay": SLICE / "HYDRA_CONSTRAINT_LILY_OWNER_SEAM_RECONCILIATION_T5_CANDIDATE_TEMPORAL_IDENTITY_OVERLAY_V001_20260926.json",
    "batch13": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_AI_DATA_CENTER_POWER_INFRASTRUCTURE_EATON_TRANSFORMER_PREQUALIFICATION_OVERLAY_V001_20260925.json",
    "batch14": SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def main() -> int:
    try:
        docs = {name: load(path) for name, path in PATHS.items()}
        predecessor_pin = docs["overlay"]["predecessor"]["git_blob_sha"]
        actual_predecessor = git_blob_sha(PATHS["candidates"])
        if predecessor_pin != actual_predecessor:
            raise OwnerSeamConformanceError(
                "successor overlay predecessor blob pin does not match committed Batch010 candidate artifact"
            )

        result = validate_owner_seams(
            claims=docs["claims"],
            candidates=docs["candidates"],
            beneficiaries=docs["beneficiaries"],
            overlay=docs["overlay"],
            batch13_beneficiary_overlay=docs["batch13"],
            batch14_strict_gate=docs["batch14"],
        )
    except (OSError, KeyError, json.JSONDecodeError, OwnerSeamConformanceError) as exc:
        print("CONSTRAINT_LILY_OWNER_SEAM_CONFORMANCE=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("CONSTRAINT_LILY_OWNER_SEAM_CONFORMANCE=PASS")
    print(f"CLAIMS={result['claim_count']}")
    print(f"T5_CANDIDATES={result['candidate_count']}")
    print(f"T6_BENEFICIARY_EVALUATIONS={result['beneficiary_relationship_count']}")
    print(f"CANONICAL_CONSTRAINTS={result['canonical_constraint_count']}")
    print(f"QUALIFIED_BENEFICIARIES={result['qualified_beneficiary_count']}")
    print("CANDIDATE_TEMPORAL_OVERLAY=EXPLICIT_NOT_BACKDATED")
    print("FORMATION_CONFIDENCE_STATE=NOT_EVALUATED")
    print("CANONICAL_IDENTITY_STATE=NOT_EVALUATED")
    print("RAW_LINEAGE=BLOCKED_INCOMPLETE_T1_T2")
    print("STRICT_ACCEPTANCE=BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
