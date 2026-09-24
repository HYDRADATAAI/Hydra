from __future__ import annotations

import unittest
from collections.abc import Iterable
from copy import deepcopy

from hydra_t6_failclosed.handoff import (
    CANDIDATE_SCHEMA,
    HANDOFF_CONTRACT,
    HANDOFF_SCHEMA,
    parse_handoff_document,
    validate_handoff,
)
from hydra_t6_failclosed.models import Issue


class HandoffContractTests(unittest.TestCase):
    def test_valid_candidate_only_handoff_is_accepted(self) -> None:
        candidate_ids, issues = validate_handoff(_valid_handoff())

        self.assertEqual(candidate_ids, ("candidate-001",))
        self.assertEqual(issues, ())

    def test_binding_and_candidate_order_are_deterministic(self) -> None:
        candidates = [
            _valid_candidate("candidate-002"),
            _valid_candidate("candidate-001"),
        ]
        left = _valid_handoff(candidates)
        right = _valid_handoff(list(reversed(candidates)))

        left_document = parse_handoff_document(left)
        right_document = parse_handoff_document(right)
        candidate_ids, issues = validate_handoff(left_document.document.value)

        self.assertEqual(left_document.binding_sha256, right_document.binding_sha256)
        self.assertEqual(candidate_ids, ("candidate-001", "candidate-002"))
        self.assertEqual(issues, ())

    def test_duplicate_candidate_ids_are_rejected(self) -> None:
        candidate = _valid_candidate("candidate-001")
        candidate_ids, issues = validate_handoff(_valid_handoff([candidate, deepcopy(candidate)]))

        self.assertEqual(candidate_ids, ("candidate-001",))
        self.assertIn("candidate_id_duplicate", _issue_codes(issues))

    def test_candidate_fail_closed_invariants_are_enforced(self) -> None:
        cases: list[tuple[str, dict[str, object], str]] = []

        canonical = _valid_candidate()
        canonical["canonicality"] = "canonical"
        cases.append(("canonicality", canonical, "candidate_canonicality_escalation"))

        lifecycle = _valid_candidate()
        lifecycle["lifecycle_state"] = "draft"
        lifecycle["lifecycle"] = [{"state": "draft"}]
        cases.append(("lifecycle", lifecycle, "candidate_lifecycle_invalid"))

        evidence_missing = _valid_candidate()
        evidence_missing["evidence"] = []
        cases.append(("evidence_missing", evidence_missing, "candidate_evidence_missing"))

        evidence_inactive = _valid_candidate()
        evidence_inactive["evidence"] = [{"id": "evidence-001", "active_context": {"stale": True}}]
        cases.append(("evidence_inactive", evidence_inactive, "candidate_evidence_inactive"))

        trust_conflict = _valid_candidate()
        trust_conflict["trust"] = {"conflicts": ["source disagreement"], "contradiction_context": {"unresolved": []}}
        cases.append(("trust_conflict", trust_conflict, "candidate_trust_conflict"))

        contradiction = _valid_candidate()
        contradiction["trust"] = {
            "conflicts": [],
            "contradiction_context": {"nested": {"unresolved": ["open contradiction"]}},
        }
        cases.append(("contradiction", contradiction, "candidate_contradiction_unresolved"))

        authority_smuggling = _valid_candidate()
        authority_smuggling["provenance"] = {"promotionAuthorized": True}
        cases.append(("authority_smuggling", authority_smuggling, "candidate_authority_smuggling"))

        for label, candidate, expected_code in cases:
            with self.subTest(case=label):
                _, issues = validate_handoff(_valid_handoff([candidate]))
                self.assertIn(expected_code, _issue_codes(issues))

    def test_handoff_envelope_invariants_are_enforced(self) -> None:
        cases: list[tuple[str, dict[str, object], str]] = []

        wrong_schema = _valid_handoff()
        wrong_schema["schema"] = "unsupported"
        cases.append(("schema", wrong_schema, "handoff_schema_unsupported"))

        wrong_contract = _valid_handoff()
        wrong_contract["contract"] = "Candidates are canonical."
        cases.append(("contract", wrong_contract, "handoff_contract_invalid"))

        naive_time = _valid_handoff()
        naive_time["created_at"] = "2026-09-24T12:00:00"
        cases.append(("created_at", naive_time, "handoff_created_at_invalid"))

        extra_field = _valid_handoff()
        extra_field["activation"] = True
        cases.append(("extra_field", extra_field, "handoff_extra_field"))

        missing_id = _valid_handoff()
        del missing_id["handoff_id"]
        cases.append(("missing_id", missing_id, "handoff_field_missing"))

        invalid_candidates = _valid_handoff()
        invalid_candidates["candidates"] = "candidate-001"
        cases.append(("invalid_candidates", invalid_candidates, "handoff_candidates_invalid"))

        empty = _valid_handoff([])
        cases.append(("empty", empty, "handoff_empty"))

        for label, handoff, expected_code in cases:
            with self.subTest(case=label):
                _, issues = validate_handoff(handoff)
                self.assertIn(expected_code, _issue_codes(issues))

    def test_non_object_candidate_is_rejected(self) -> None:
        _, issues = validate_handoff(_valid_handoff([42]))
        self.assertIn("candidate_not_object", _issue_codes(issues))


def _valid_handoff(candidates: list[object] | None = None) -> dict[str, object]:
    return {
        "schema": HANDOFF_SCHEMA,
        "handoff_id": "handoff-001",
        "created_at": "2026-09-24T12:00:00Z",
        "contract": HANDOFF_CONTRACT,
        "candidates": candidates if candidates is not None else [_valid_candidate()],
    }


def _valid_candidate(candidate_id: str = "candidate-001") -> dict[str, object]:
    return {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": candidate_id,
        "statement": "Synthetic candidate statement.",
        "canonicality": "candidate_only",
        "lifecycle_state": "handed_off",
        "lifecycle": [{"state": "created"}, {"state": "handed_off"}],
        "evidence": [{"id": f"evidence-{candidate_id}", "active_context": {}}],
        "provenance": {"created_by_stage": "T5"},
        "trust": {"conflicts": [], "contradiction_context": {"unresolved": []}},
        "uncertainty": {"confidence": "medium"},
        "beneficiaries": [],
        "forced_expenditures": [],
        "relations": [],
        "temporal": {"observed_at": "2026-09-24T11:00:00Z"},
    }


def _issue_codes(issues: Iterable[Issue]) -> set[str]:
    return {issue.code for issue in issues}


if __name__ == "__main__":
    unittest.main()
