from __future__ import annotations

from datetime import datetime
from typing import Any


class OwnerSeamConformanceError(ValueError):
    pass


_REQUIRED_BENEFICIARY_LINEAGE = {
    "constraint_evidence",
    "entity_connection",
    "advantage_mechanism",
    "capacity_or_availability",
    "economic_or_strategic_capture",
    "disconfirming_or_blocking",
}

RAW_BLOCKER = "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"
ADMISSION_BLOCKER = "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT"


def _fail(message: str) -> None:
    raise OwnerSeamConformanceError(message)


def _aware_dt(value: str, label: str) -> datetime:
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise OwnerSeamConformanceError(f"{label}: invalid timestamp") from exc
    if ts.tzinfo is None or ts.utcoffset() is None:
        _fail(f"{label}: timezone-aware timestamp required")
    return ts


def _unique_ids(rows: list[dict[str, Any]], field: str, label: str) -> set[str]:
    values: list[str] = []
    for index, row in enumerate(rows):
        value = row.get(field)
        if not isinstance(value, str) or not value:
            _fail(f"{label}[{index}].{field}: non-empty string required")
        values.append(value)
    if len(values) != len(set(values)):
        _fail(f"{label}.{field}: duplicate IDs")
    return set(values)


def validate_owner_seams(
    *,
    claims: dict[str, Any],
    candidates: dict[str, Any],
    beneficiaries: dict[str, Any],
    temporal_identity_overlay: dict[str, Any],
    typed_confidence: dict[str, Any],
    batch13_beneficiary_overlay: dict[str, Any],
    batch16_strict_gate: dict[str, Any],
) -> dict[str, int | str]:
    if candidates.get("producer_namespace") != "PIPELINE_T5_CONSTRAINT_FORMATION":
        _fail("candidate producer namespace is not authoritative T5")
    if candidates.get("canonicalization_performed") is not False:
        _fail("T5 candidate artifact performed canonicalization")
    if beneficiaries.get("consumer_namespace") != "PIPELINE_T6_CANONICAL_CANDIDATE_GOVERNANCE":
        _fail("beneficiary consumer namespace is not authoritative T6")

    claim_rows = claims.get("claims")
    candidate_rows = candidates.get("candidates")
    beneficiary_rows = beneficiaries.get("relationships")
    overlay_rows = temporal_identity_overlay.get("candidates")
    candidate_confidence = typed_confidence.get("candidate_confidence")
    beneficiary_confidence = typed_confidence.get("beneficiary_confidence")
    if not all(
        isinstance(rows, list)
        for rows in (
            claim_rows,
            candidate_rows,
            beneficiary_rows,
            overlay_rows,
            candidate_confidence,
            beneficiary_confidence,
        )
    ):
        _fail("owner-seam inputs must contain list rows")

    claim_ids = _unique_ids(claim_rows, "claim_id", "claims")
    candidate_ids = _unique_ids(candidate_rows, "constraint_candidate_id", "candidates")
    relationship_ids = _unique_ids(beneficiary_rows, "beneficiary_relationship_id", "beneficiaries")
    overlay_ids = _unique_ids(overlay_rows, "constraint_candidate_id", "overlay.candidates")
    candidate_confidence_ids = _unique_ids(
        candidate_confidence, "constraint_candidate_id", "candidate_confidence"
    )
    beneficiary_confidence_ids = _unique_ids(
        beneficiary_confidence, "beneficiary_relationship_id", "beneficiary_confidence"
    )

    if overlay_ids != candidate_ids:
        _fail("successor overlay candidate universe differs from predecessor T5 candidate universe")
    if candidate_confidence_ids != candidate_ids:
        _fail("typed formation-confidence universe differs from T5 candidate universe")
    if beneficiary_confidence_ids != relationship_ids:
        _fail("typed beneficiary-confidence universe differs from T6 relationship universe")

    known_evidence_ids: set[str] = set()
    claim_available_at: dict[str, datetime] = {}
    for claim in claim_rows:
        cid = claim["claim_id"]
        claim_available_at[cid] = _aware_dt(claim["available_at"], f"{cid}.available_at")
        for field in ("support_evidence_ids", "disconfirming_evidence_ids"):
            for evidence_id in claim.get(field, []):
                if not isinstance(evidence_id, str) or not evidence_id.startswith("EV-"):
                    _fail(f"{cid}.{field}: invalid evidence reference")
                known_evidence_ids.add(evidence_id)

    candidate_by_id = {row["constraint_candidate_id"]: row for row in candidate_rows}
    overlay_by_id = {row["constraint_candidate_id"]: row for row in overlay_rows}
    confidence_by_id = {
        row["constraint_candidate_id"]: row for row in candidate_confidence
    }

    for cid, candidate in candidate_by_id.items():
        if not candidate.get("constraining_mechanism"):
            _fail(f"{cid}: missing constraining mechanism")
        if not candidate.get("constrained_target"):
            _fail(f"{cid}: missing constrained target")
        if not isinstance(candidate.get("material_scope"), dict) or not candidate["material_scope"]:
            _fail(f"{cid}: missing material scope")
        if candidate.get("canonical_constraint_id") is not None:
            _fail(f"{cid}: T5 candidate already has canonical constraint ID")
        if candidate.get("ordinary_t6_eligible") is not False:
            _fail(f"{cid}: candidate escaped ordinary-T6 fail-closed state")
        if "beneficiary" in candidate or "beneficiaries" in candidate:
            _fail(f"{cid}: T5 candidate contains authoritative beneficiary field")

        refs = candidate.get("claim_ids")
        if not isinstance(refs, list) or not refs:
            _fail(f"{cid}: claim lineage required")
        if not set(refs) <= claim_ids:
            _fail(f"{cid}: candidate cites unknown claim")
        for role, values in candidate.get("evidence_roles", {}).items():
            if not isinstance(values, list):
                _fail(f"{cid}.{role}: role values must be a list")
            for value in values:
                if value.startswith("EV-") and value not in known_evidence_ids:
                    _fail(f"{cid}.{role}: unknown evidence {value}")
                if value.startswith("CLM-") and value not in claim_ids:
                    _fail(f"{cid}.{role}: unknown claim {value}")

        successor = overlay_by_id[cid]
        overlay_available = _aware_dt(
            successor.get("available_at", ""), f"{cid}.overlay.available_at"
        )
        latest_parent_claim = max(claim_available_at[claim_id] for claim_id in refs)
        if overlay_available < latest_parent_claim:
            _fail(f"{cid}: successor overlay backdates availability before parent claim lineage")
        if successor.get("effective_from") is not None or successor.get("effective_to") is not None:
            _fail(f"{cid}: overlay fabricated candidate effective interval")
        if successor.get("effective_state") != "UNRESOLVED_NOT_FABRICATED":
            _fail(f"{cid}: unknown effective state was not preserved")
        if successor.get("canonical_constraint_id") is not None:
            _fail(f"{cid}: overlay minted canonical constraint ID")
        if successor.get("canonical_identity_state") != "NOT_EVALUATED":
            _fail(f"{cid}: unresolved canonical identity state not explicit")
        if successor.get("lineage_state") != "BLOCKED_INCOMPLETE_T1_T2":
            _fail(f"{cid}: incomplete upstream lineage was not preserved as blocking")
        if successor.get("ordinary_t6_eligible") is not False:
            _fail(f"{cid}: overlay admitted ordinary T6 eligibility")
        if set(successor.get("source_ineligibility_reasons", [])) != {
            RAW_BLOCKER,
            ADMISSION_BLOCKER,
        }:
            _fail(f"{cid}: overlay blocker set drifted")

        confidence = confidence_by_id[cid]
        if confidence.get("confidence_type") != "FORMATION_CONFIDENCE":
            _fail(f"{cid}: wrong formation confidence type")
        if confidence.get("semantic_owner_id") != "PIPELINE_T5_CONSTRAINT_FORMATION":
            _fail(f"{cid}: formation confidence owner drifted")
        if confidence.get("measurement_state") != "UNKNOWN_NOT_MEASURED":
            _fail(f"{cid}: formation confidence is not explicit unknown")
        if confidence.get("value") is not None:
            _fail(f"{cid}: numeric formation confidence was invented")

    beneficiary_confidence_by_id = {
        row["beneficiary_relationship_id"]: row for row in beneficiary_confidence
    }
    for relation in beneficiary_rows:
        rid = relation["beneficiary_relationship_id"]
        parent_id = relation.get("constraint_candidate_id")
        if parent_id not in candidate_by_id:
            _fail(f"{rid}: beneficiary references unknown T5 candidate")
        if rid in candidate_ids or rid == relation.get("beneficiary_entity_id"):
            _fail(f"{rid}: beneficiary relationship identity collided with another namespace")
        parent = candidate_by_id[parent_id]
        if parent.get("ordinary_t6_eligible") is False:
            if relation.get("constraint_id") is not None:
                _fail(f"{rid}: blocked beneficiary references canonical constraint")
            if relation.get("qualification_state") != "INELIGIBLE_TO_EVALUATE":
                _fail(f"{rid}: blocked parent candidate did not force ineligible beneficiary evaluation")
            if relation.get("eligibility_state") != "BLOCKED":
                _fail(f"{rid}: beneficiary eligibility escaped BLOCKED")
        if not relation.get("benefit_transmission_mechanism"):
            _fail(f"{rid}: missing beneficiary transmission mechanism")
        lineage = relation.get("evidence_lineage")
        if not isinstance(lineage, dict) or not _REQUIRED_BENEFICIARY_LINEAGE <= set(lineage):
            _fail(f"{rid}: incomplete beneficiary evidence-role lineage")
        if not set(lineage["constraint_evidence"]) <= set(
            parent.get("evidence_roles", {}).get("constraint_support", [])
        ):
            _fail(f"{rid}: beneficiary constraint evidence is not inherited from parent constraint support")
        for field in (
            "entity_connection",
            "advantage_mechanism",
            "capacity_or_availability",
            "economic_or_strategic_capture",
        ):
            for claim_id in lineage[field]:
                if claim_id not in claim_ids:
                    _fail(f"{rid}.{field}: unknown claim {claim_id}")

        confidence = beneficiary_confidence_by_id[rid]
        if confidence.get("confidence_type") != "BENEFICIARY_CONFIDENCE":
            _fail(f"{rid}: wrong beneficiary confidence type")
        if confidence.get("semantic_owner_id") != "PIPELINE_T6_CANONICAL_CANDIDATE_GOVERNANCE":
            _fail(f"{rid}: beneficiary confidence owner drifted")
        if confidence.get("measurement_state") != "UNKNOWN_INELIGIBLE_TO_EVALUATE":
            _fail(f"{rid}: beneficiary confidence is not explicit ineligible unknown")
        if confidence.get("value") is not None:
            _fail(f"{rid}: numeric beneficiary confidence was invented")
        if confidence.get("qualification_state") != "INELIGIBLE_TO_EVALUATE":
            _fail(f"{rid}: typed beneficiary confidence escaped qualification block")

    if beneficiaries.get("qualified_relationship_count") != 0:
        _fail("qualified beneficiary count is nonzero while candidate admission is blocked")

    predecessor_relationship = batch13_beneficiary_overlay.get("predecessor_relationship")
    if predecessor_relationship not in relationship_ids:
        _fail("Batch013 beneficiary overlay references unknown predecessor relationship")
    if batch13_beneficiary_overlay.get("canonical_constraint_id") is not None:
        _fail("Batch013 beneficiary overlay minted canonical constraint")
    if batch13_beneficiary_overlay.get("ordinary_t6_eligible") is not False:
        _fail("Batch013 beneficiary overlay escaped ordinary-T6 gate")
    if batch13_beneficiary_overlay.get("canonical_qualification_state") != "BLOCKED":
        _fail("Batch013 beneficiary overlay escaped blocked qualification state")

    dimensions = batch16_strict_gate.get("dimensions", {})
    if dimensions.get("IMPLEMENTATION_ADMITTED", {}).get("status") != "BLOCKED":
        _fail("Batch016 implementation admission escaped BLOCKED")
    if dimensions.get("PROVENANCE_READY", {}).get("status") != "BLOCKED":
        _fail("Batch016 provenance gate escaped BLOCKED")
    if dimensions.get("CONFIDENCE_READY", {}).get("status") != "READY_WITH_NONBLOCKING_GAPS":
        _fail("Batch016 confidence semantics regressed")
    if dimensions.get("REPLAY_READY", {}).get("status") != "BLOCKED":
        _fail("Batch016 replay gate escaped BLOCKED")
    if dimensions.get("EVALUATION_READY", {}).get("status") != "BLOCKED":
        _fail("Batch016 evaluation gate escaped BLOCKED")
    if batch16_strict_gate.get("overall_status") != "BLOCKED":
        _fail("Batch016 overall strict acceptance escaped BLOCKED")
    if batch16_strict_gate.get("full_constraint_run_allowed") is not False:
        _fail("Batch016 full constraint run was authorized")

    if temporal_identity_overlay.get("original_candidate_availability_reconstructed") is not False:
        _fail("overlay claims retroactive reconstruction of original candidate availability")
    result = temporal_identity_overlay.get("result", {})
    if result.get("predecessor_rewritten") is not False:
        _fail("overlay rewrote predecessor")
    if result.get("confidence_semantics_reimplemented") is not False:
        _fail("overlay duplicated Batch015 confidence semantics")
    if result.get("t1_custody_reimplemented") is not False:
        _fail("overlay duplicated T1 custody hardening")
    if result.get("canonical_constraints_minted") != 0:
        _fail("overlay minted canonical constraints")
    if result.get("qualified_beneficiaries_minted") != 0:
        _fail("overlay minted qualified beneficiaries")
    if result.get("ordinary_t6_candidates_admitted") != 0:
        _fail("overlay admitted ordinary T6 candidates")

    return {
        "claim_count": len(claim_rows),
        "candidate_count": len(candidate_rows),
        "beneficiary_relationship_count": len(beneficiary_rows),
        "qualified_beneficiary_count": beneficiaries.get("qualified_relationship_count", 0),
        "canonical_constraint_count": 0,
        "status": "PASS_CURRENT_FAIL_CLOSED_OWNER_SEAMS",
    }
