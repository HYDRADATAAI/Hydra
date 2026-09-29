#!/usr/bin/env python3
"""Build Batch034 evidence-to-source-version lineage from public second-slice artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"constraint-t1-raw-artifact-store"/"src"
sys.path.insert(0,str(SRC))

from hydra_constraint_t1_raw.ordinary_t2_evidence_lineage import (  # noqa: E402
    OrdinaryT2EvidenceLineageError,
    build_ordinary_t2_evidence_lineage,
)

SLICE="SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1"
BASE=ROOT/"docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
QUEUE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json"
LINEAGE=BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH033_SEMICONDUCTOR_ORDINARY_T2_SOURCE_VERSION_LINEAGE_V001_20260928.json"
EVIDENCE_PATHS=(
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_EVIDENCE_SEED_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_EVIDENCE_SUPPLEMENT_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH020_SEMICONDUCTOR_POLICY_SUBSTITUTION_OUTCOME_EVIDENCE_SUPPLEMENT_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH021_SEMICONDUCTOR_VALID_BENEFICIARY_SUBSTITUTION_MIGRATION_POWER_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH022_SEMICONDUCTOR_YIELD_TOOL_MATERIAL_DUPLICATE_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH023_SEMICONDUCTOR_HBM_YIELD_MIGRATION_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH025_SEMICONDUCTOR_CONTINUOUS_CROSS_SLICE_EVIDENCE_V001_20260926.json",
    BASE/"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_NON_MICRON_REPLACEMENT_EVIDENCE_V001_20260927.json",
)

def load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise OrdinaryT2EvidenceLineageError(f"object required: {path}")
    return value

def collect(value:Any, *, origin:str, out:list[dict[str,Any]])->None:
    if isinstance(value,list):
        for item in value: collect(item,origin=origin,out=out)
        return
    if not isinstance(value,dict): return
    if isinstance(value.get("evidence_id"),str) and isinstance(value.get("source_id"),str):
        row=dict(value)
        row["origin_artifact"]=origin
        out.append(row)
    for item in value.values():
        collect(item,origin=origin,out=out)

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    try:
        queue=load(QUEUE).get("queue")
        if not isinstance(queue,list) or len(queue)!=30:
            raise OrdinaryT2EvidenceLineageError("Batch031 active queue must contain 30 sources")
        evidence:list[dict[str,Any]]=[]
        for path in EVIDENCE_PATHS:
            collect(load(path),origin=path.relative_to(ROOT).as_posix(),out=evidence)
        packet=build_ordinary_t2_evidence_lineage(
            lineage_packet=load(LINEAGE),
            source_records=queue,
            evidence_records=evidence,
            expected_slice_id=SLICE,
        )
        output=Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(packet,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    except (OSError,json.JSONDecodeError,OrdinaryT2EvidenceLineageError) as exc:
        print("BATCH034_T2_EVIDENCE_LINEAGE=FAIL"); print(f"ERROR={exc}"); return 1
    print("BATCH034_T2_EVIDENCE_LINEAGE=PASS")
    print(f"INPUT_EVIDENCE_RECORDS={packet['input_evidence_record_count']}")
    print(f"BOUND_EVIDENCE={packet['bound_evidence_count']}")
    print(f"EXCLUDED_EVIDENCE={packet['excluded_evidence_count']}")
    print(f"ACTIVE_SOURCES_WITH_BOUND_EVIDENCE={packet['active_source_count_with_bound_evidence']}")
    print("ALL_ACTIVE_SOURCES_HAVE_BOUND_EVIDENCE="+("YES" if packet["all_active_sources_have_bound_evidence"] else "NO"))
    print("STRICT_HISTORICAL_REPLAY_READY=NO")
    print("CANONICAL_EVIDENCE_ADMISSION_PROMOTED=NO")
    return 0

if __name__=="__main__": raise SystemExit(main())
