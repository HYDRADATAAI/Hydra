"""Deterministic, lineage-closed shadow replay of normalized reviewed artifacts.

This is a knowledge-availability view, NOT effective-state or ordinary replay.
No canonical promotion, live-source authority, or native admission is granted.
Historical Batch011 receipts describe the predecessor algorithm, not this repair.
"""
from __future__ import annotations
from datetime import datetime
import hashlib
import json
from typing import Any, Mapping


def _dt(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("valid timezone-aware timestamp required") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return result


def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _index(rows, key):
    result = {}
    for row in rows:
        identity = row.get(key)
        if not isinstance(identity, str) or not identity or identity in result:
            raise ValueError(f"missing or duplicate {key}")
        result[identity] = row
    return result


def build_shadow_snapshot(*, as_of: str, claim_registry: Mapping[str, Any],
                          candidates: Mapping[str, Any], relief_paths: Mapping[str, Any],
                          beneficiaries: Mapping[str, Any], outcomes: Mapping[str, Any],
                          candidate_overlay: Mapping[str, Any] | None = None) -> dict[str, Any]:
    cutoff = _dt(as_of)
    claims = _index(claim_registry["claims"], "claim_id")
    candidate_rows = _index(candidates["candidates"], "constraint_candidate_id")
    relief_rows = _index(relief_paths["relief_paths"], "relief_path_id")
    beneficiary_rows = _index(beneficiaries["relationships"], "beneficiary_relationship_id")
    outcome_rows = _index(outcomes["records"], "outcome_id")
    overlays = _index((candidate_overlay or {}).get("candidates", []), "constraint_candidate_id")
    if candidate_overlay is not None and set(overlays) != set(candidate_rows):
        raise ValueError("candidate overlay universe differs from T5 candidates")
    eligible = {cid for cid, row in claims.items() if _dt(row["available_at"]) <= cutoff}
    evidence = {}
    for cid, row in claims.items():
        for field in ("support_evidence_ids", "disconfirming_evidence_ids"):
            for eid in row.get(field, []):
                evidence.setdefault(eid, set()).add(cid)

    def references(refs):
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
            raise ValueError("lineage must be a list of nonempty reference IDs")
        return refs

    def claims_supported(refs):
        refs = references(refs)
        return bool(refs) and all(ref in eligible for ref in refs)

    def supported(refs):
        refs = references(refs)
        # Unknown references never count as evidence; empty lineage is not proof.
        return bool(refs) and all(
            ref in eligible or (ref in evidence and bool(evidence[ref] & eligible))
            for ref in refs
        )

    visible_candidates = set()
    for cid, row in candidate_rows.items():
        temporal = overlays.get(cid, row)
        available = temporal.get("available_at")
        # Missing candidate knowledge time is unknown, not a timeless candidate.
        if available is None:
            continue
        if _dt(available) <= cutoff and claims_supported(row.get("claim_ids", [])):
            visible_candidates.add(cid)
    relief = []
    for rid, row in relief_rows.items():
        claim_refs = references(row.get("support_claim_ids", []))
        evidence_refs = references(row.get("support_evidence_ids", []))
        lineage_available = (bool(claim_refs or evidence_refs)
                             and all(ref in eligible for ref in claim_refs)
                             and all(ref in evidence and bool(evidence[ref] & eligible) for ref in evidence_refs))
        if (row.get("constraint_candidate_id") in visible_candidates and lineage_available
                and (row.get("available_at") is None or _dt(row["available_at"]) <= cutoff)):
            relief.append(rid)
    bens = []
    for bid, row in beneficiary_rows.items():
        lineage = row.get("evidence_lineage", {})
        refs = [ref for role, values in lineage.items() if role != "disconfirming_or_blocking" for ref in values]
        if (_dt(row["available_at"]) <= cutoff
                and row.get("constraint_candidate_id") in visible_candidates and supported(refs)):
            bens.append(bid)
    # An observed fact can remain visible independently of an admitted constraint.
    outs = [oid for oid, row in outcome_rows.items()
            if _dt(row["hydra_available_at"]) <= cutoff and claims_supported([row.get("claim_id")])]
    return {"as_of": as_of, "eligible_claim_ids": sorted(eligible),
            "constraint_candidate_ids": sorted(visible_candidates), "relief_path_ids": sorted(relief),
            "beneficiary_relationship_ids": sorted(bens), "outcome_ids": sorted(outs)}


def future_leaks(snapshot: Mapping[str, Any], claim_registry: Mapping[str, Any],
                 outcomes: Mapping[str, Any], **lineage_inputs) -> tuple[str, ...]:
    """Check claims/outcomes, optionally all dependent IDs using full replay inputs.

    Without lineage inputs this remains the historical limited check; callers
    must not interpret it as validation of candidate/relief/beneficiary lineage.
    """
    cutoff = _dt(snapshot["as_of"])
    claims = _index(claim_registry["claims"], "claim_id")
    records = _index(outcomes["records"], "outcome_id")
    leaks = []
    for cid in snapshot["eligible_claim_ids"]:
        if cid not in claims or _dt(claims[cid]["available_at"]) > cutoff:
            leaks.append("claim:" + cid)
    for oid in snapshot["outcome_ids"]:
        if oid not in records or _dt(records[oid]["hydra_available_at"]) > cutoff:
            leaks.append("outcome:" + oid)
    if lineage_inputs:
        expected = build_shadow_snapshot(as_of=snapshot["as_of"], claim_registry=claim_registry,
                                         outcomes=outcomes, **lineage_inputs)
        for field, prefix in (("constraint_candidate_ids", "candidate"), ("relief_path_ids", "relief"),
                              ("beneficiary_relationship_ids", "beneficiary"), ("outcome_ids", "outcome")):
            leaks.extend(prefix + ":" + identity for identity in set(snapshot[field]) - set(expected[field]))
    return tuple(sorted(set(leaks)))
