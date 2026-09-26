"""Deterministic shadow replay for the first Constraint slice.

Operates only on normalized reviewed artifacts. It grants no ordinary T1/T2
lineage, native T5->T6 admission, canonical promotion, or live-source authority.
"""
from __future__ import annotations
from datetime import datetime
import hashlib, json
from typing import Any, Mapping

def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload=json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def build_shadow_snapshot(*, as_of: str, claim_registry: Mapping[str, Any], candidates: Mapping[str, Any], relief_paths: Mapping[str, Any], beneficiaries: Mapping[str, Any], outcomes: Mapping[str, Any]) -> dict[str, Any]:
    cutoff=_dt(as_of)
    eligible={row["claim_id"] for row in claim_registry["claims"] if _dt(row["available_at"]) <= cutoff}
    candidate_ids=[row["constraint_candidate_id"] for row in candidates["candidates"]]
    relief=[]
    for row in relief_paths["relief_paths"]:
        support=set(row.get("support_claim_ids", []))
        if not support or support.issubset(eligible):
            relief.append(row["relief_path_id"])
    bens=[row["beneficiary_relationship_id"] for row in beneficiaries["relationships"] if _dt(row["available_at"]) <= cutoff]
    outs=[row["outcome_id"] for row in outcomes["records"] if _dt(row["hydra_available_at"]) <= cutoff]
    return {"as_of":as_of,"eligible_claim_ids":sorted(eligible),"constraint_candidate_ids":candidate_ids,"relief_path_ids":relief,"beneficiary_relationship_ids":bens,"outcome_ids":outs}

def future_leaks(snapshot: Mapping[str, Any], claim_registry: Mapping[str, Any], outcomes: Mapping[str, Any]) -> tuple[str, ...]:
    cutoff=_dt(snapshot["as_of"]); leaks=[]; visible=set(snapshot["eligible_claim_ids"])
    for row in claim_registry["claims"]:
        if row["claim_id"] in visible and _dt(row["available_at"]) > cutoff:
            leaks.append("claim:"+row["claim_id"])
    visible_out=set(snapshot["outcome_ids"])
    for row in outcomes["records"]:
        if row["outcome_id"] in visible_out and _dt(row["hydra_available_at"]) > cutoff:
            leaks.append("outcome:"+row["outcome_id"])
    return tuple(sorted(leaks))
