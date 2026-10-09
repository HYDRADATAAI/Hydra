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


_BENEFICIARY_LINEAGE_KEYS = {
    "constraint_evidence",
    "entity_connection",
    "advantage_mechanism",
    "capacity_or_availability",
    "economic_or_strategic_capture",
    "disconfirming_or_blocking",
}
_BENEFICIARY_CLAIM_ROLE_ALLOWLIST = {
    "entity_connection": {"ENTITY_CAPABILITY", "ENTITY_CAPACITY_RELIEF", "SUBSTITUTION_RELIEF"},
    "advantage_mechanism": {"ENTITY_CAPABILITY", "ENTITY_CAPACITY_RELIEF", "SUBSTITUTION_RELIEF"},
    "capacity_or_availability": {"ENTITY_CAPABILITY", "ENTITY_CAPACITY_RELIEF"},
    "economic_or_strategic_capture": {"ENTITY_CAPABILITY"},
}


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
    def references(refs):
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
            raise ValueError("lineage must be a list of nonempty reference IDs")
        return refs

    evidence = {}
    constraint_evidence = {}
    for cid, row in claims.items():
        support_ids = references(row.get("support_evidence_ids", []))
        disconfirming_ids = set(references(row.get("disconfirming_evidence_ids", [])))
        for eid in support_ids:
            evidence.setdefault(eid, set()).add(cid)
            if (row.get("claim_role") == "CONSTRAINT_EXISTENCE"
                    and eid not in disconfirming_ids):
                constraint_evidence.setdefault(eid, set()).add(cid)
        for eid in disconfirming_ids:
            evidence.setdefault(eid, set()).add(cid)

    def claims_supported(refs):
        refs = references(refs)
        return bool(refs) and all(ref in eligible for ref in refs)

    def beneficiary_lineage_supported(lineage, parent_candidate):
        if not lineage:
            return False
        if set(lineage) != _BENEFICIARY_LINEAGE_KEYS:
            raise ValueError("beneficiary evidence lineage roles differ from the declared schema")
        parent_roles = parent_candidate.get("evidence_roles", {})
        parent_constraint_refs = (
            references(parent_roles.get("constraint_support", []))
            if isinstance(parent_roles, Mapping) else []
        )
        parent_claim_ids = set(references(parent_candidate.get("claim_ids", [])))
        has_support = False
        for role, raw_refs in lineage.items():
            refs = references(raw_refs)
            if role == "disconfirming_or_blocking" or not refs:
                continue
            if role == "constraint_evidence":
                available = all(
                    ref in parent_constraint_refs
                    and ref in constraint_evidence
                    and bool(constraint_evidence[ref] & eligible & parent_claim_ids)
                    for ref in refs
                )
            else:
                allowed_roles = _BENEFICIARY_CLAIM_ROLE_ALLOWLIST[role]
                available = all(
                    ref in eligible and claims[ref].get("claim_role") in allowed_roles
                    for ref in refs
                )
            if not available:
                return False
            has_support = True
        # Empty positive lineage is not proof. Claim references also need to
        # match the semantics of the lineage field that contains them.
        return has_support

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
        if not isinstance(lineage, Mapping):
            raise ValueError("beneficiary evidence lineage must be a mapping")
        if (_dt(row["available_at"]) <= cutoff
                and row.get("constraint_candidate_id") in visible_candidates
                and beneficiary_lineage_supported(
                    lineage, candidate_rows[row["constraint_candidate_id"]]
                )):
            bens.append(bid)
    # An observed fact can remain visible independently of an admitted constraint.
    # Unknown Hydra availability is not evidence that the outcome was visible.
    outs = []
    for oid, row in outcome_rows.items():
        available_at = row["hydra_available_at"]
        if available_at is None:
            continue
        if _dt(available_at) <= cutoff and claims_supported([row.get("claim_id")]):
            outs.append(oid)
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
        if oid not in records:
            leaks.append("outcome:" + oid)
            continue
        record = records[oid]
        available_at = record["hydra_available_at"]
        if available_at is None or _dt(available_at) > cutoff:
            leaks.append("outcome:" + oid)
            continue
        claim_id = record.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id or claim_id not in claims:
            leaks.append("outcome:" + oid)
            continue
        if _dt(claims[claim_id]["available_at"]) > cutoff:
            leaks.append("outcome:" + oid)
    if lineage_inputs:
        expected = build_shadow_snapshot(as_of=snapshot["as_of"], claim_registry=claim_registry,
                                         outcomes=outcomes, **lineage_inputs)
        for field, prefix in (("constraint_candidate_ids", "candidate"), ("relief_path_ids", "relief"),
                              ("beneficiary_relationship_ids", "beneficiary"), ("outcome_ids", "outcome")):
            leaks.extend(prefix + ":" + identity for identity in set(snapshot[field]) - set(expected[field]))
    return tuple(sorted(set(leaks)))
