#!/usr/bin/env python3
"""Build Batch034 semiconductor T2 evidence lineage from Batch033 source versions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"constraint-t1-raw-artifact-store"/"src"
sys.path.insert(0,str(SRC))

from hydra_constraint_t1_raw.evidence_lineage_binding import (  # noqa: E402
    EvidenceLineageBindingError,
    build_evidence_lineage_binding,
)

BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
LINEAGE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH033_SEMICONDUCTOR_ORDINARY_T2_SOURCE_VERSION_LINEAGE_V001_20260928.json"
EVIDENCE_FILES=[
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_EVIDENCE_SEED_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_EVIDENCE_SUPPLEMENT_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_POLICY_SUBSTITUTION_OUTCOME_EVIDENCE_SUPPLEMENT_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_SUBSTITUTION_MIGRATION_POWER_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_YIELD_TOOL_MATERIAL_DUPLICATE_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_HBM_YIELD_MIGRATION_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_CONTINUOUS_CROSS_SLICE_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_NON_MICRON_REPLACEMENT_EVIDENCE_V001_20260927.json",
]
SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"

def load(path:Path)->dict:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise EvidenceLineageBindingError(f"top-level object required: {path}")
    return value

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    try:
        packet=build_evidence_lineage_binding(
            source_lineage=load(LINEAGE),
            evidence_documents=[load(path) for path in EVIDENCE_FILES],
            expected_slice_id=SLICE,
        )
        output=Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(packet,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    except (OSError,json.JSONDecodeError,EvidenceLineageBindingError) as exc:
        print("BATCH034_T2_EVIDENCE_LINEAGE=FAIL")
        print(f"ERROR={exc}")
        return 1

    print("BATCH034_T2_EVIDENCE_LINEAGE=PASS")
    print(f"ACTIVE_SOURCES={packet['source_count']}")
    print(f"REVIEWED_EVIDENCE={packet['reviewed_evidence_record_count']}")
    print(f"BOUND_EVIDENCE={packet['bound_evidence_count']}")
    print(f"UNBOUND_EVIDENCE={packet['unbound_evidence_count']}")
    print(f"BOUND_ACTIVE_SOURCES={packet['bound_active_source_count']}")
    print("ACTIVE_SOURCE_COVERAGE_COMPLETE=YES")
    print("STRICT_HISTORICAL_REPLAY_READY=NO")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
