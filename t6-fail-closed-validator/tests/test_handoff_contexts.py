from __future__ import annotations

import unittest
from copy import deepcopy

from hydra_t6_failclosed.handoff import (
    CANDIDATE_SCHEMA,
    HANDOFF_CONTRACT,
    HANDOFF_SCHEMA,
    validate_handoff,
)
from hydra_t6_failclosed.models import Issue


class HandoffContextTests(unittest.TestCase):
    def test_valid_empty_contexts_are_accepted(self) -> None:
        candidate_ids, issues = validate_handoff(_handoff(_candidate()))

        self.assertEqual(candidate_ids, ("candidate-001",))
        self.assertEqual(issues, ())

    def test_malformed_evidence_context_is_rejected(self) -> None:
        cases = [
            "active",
            {"stale": 1},
            {"withdrawn": "false"},
        ]

        for active_context in cases:
            with self.subTest(active_context=active_context):
                candidate = _candidate()
                candidate["evidence"] = [{"id": "evidence-001", "active_context": active_context}]
                _, issues = validate_handoff(_handoff(candidate))

                self.assertIn("candidate_evidence_context_invalid", _codes(issues))

    def test_malformed_trust_context_is_rejected(self) -> None:
        cases = [
            {"conflicts": "source disagreement", "contradiction_context": {"unresolved": []}},
            {"conflicts": [], "contradiction_context": []},
            {"conflicts": [], "contradiction_context": {"nested": {"unresolved": True}}},
        ]

        for trust in cases:
            with self.subTest(trust=trust):
                candidate = _candidate()
                candidate["trust"] = deepcopy(trust)
                _, issues = validate_handoff(_handoff(candidate))

                self.assertIn("candidate_trust_context_invalid", _codes(issues))

    def test_well_formed_open_trust_state_remains_rejected(self) -> None:
        cases = [
            (
                {"conflicts": ["source disagreement"], "contradiction_context": {"unresolved": []}},
                "candidate_trust_conflict",
            ),
            (
                {"conflicts": [], "contradiction_context": {"nested": {"unresolved": ["open contradiction"]}}},
                "candidate_contradiction_unresolved",
            ),
        ]

        for trust, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                candidate = _candidate()
                candidate["trust"] = deepcopy(trust)
                _, issues = validate_handoff(_handoff(candidate))

                self.assertIn(expected_code, _codes(issues))

    def test_blank_identifiers_and_statement_are_rejected(self) -> None:
        candidate = _candidate()
        candidate["candidate_id"] = "   "
        candidate_ids, issues = validate_handoff(_handoff(candidate))
        self.assertEqual(candidate_ids, ())
        self.assertIn("candidate_id_invalid", _codes(issues))

        candidate = _candidate()
        candidate["statement"] = "\t"
        _, issues = validate_handoff(_handoff(candidate))
        self.assertIn("candidate_statement_invalid", _codes(issues))

        candidate = _candidate()
        candidate["evidence"] = [{"id": "\n", "active_context": {}}]
        _, issues = validate_handoff(_handoff(candidate))
        self.assertIn("candidate_evidence_id_invalid", _codes(issues))

        handoff = _handoff(_candidate())
        handoff["handoff_id"] = " "
        _, issues = validate_handoff(handoff)
        self.assertIn("handoff_id_invalid", _codes(issues))

    def test_candidate_collections_require_arrays(self) -> None:
        for field in ("beneficiaries", "forced_expenditures", "relations"):
            with self.subTest(field=field):
                candidate = _candidate()
                candidate[field] = {}
                _, issues = validate_handoff(_handoff(candidate))

                self.assertIn("candidate_collection_invalid", _codes(issues))

    def test_temporal_context_requires_an_object(self) -> None:
        candidate = _candidate()
        candidate["temporal"] = []
        _, issues = validate_handoff(_handoff(candidate))

        self.assertIn("candidate_context_invalid", _codes(issues))

    def test_every_lifecycle_event_requires_a_nonempty_state(self) -> None:
        cases = [
            ["created", {"state": "handed_off"}],
            [{"state": 1}, {"state": "handed_off"}],
            [{"state": " "}, {"state": "handed_off"}],
        ]

        for lifecycle in cases:
            with self.subTest(lifecycle=lifecycle):
                candidate = _candidate()
                candidate["lifecycle"] = lifecycle
                _, issues = validate_handoff(_handoff(candidate))

                self.assertIn("candidate_lifecycle_history_invalid", _codes(issues))

    def test_duplicate_evidence_ids_are_rejected(self) -> None:
        candidate = _candidate()
        candidate["evidence"] = [
            {"id": "evidence-001", "active_context": {}},
            {"id": "evidence-001", "active_context": {}},
        ]
        _, issues = validate_handoff(_handoff(candidate))

        self.assertIn("candidate_evidence_id_duplicate", _codes(issues))


def _handoff(candidate: dict[str, object]) -> dict[str, object]:
    return {
        "schema": HANDOFF_SCHEMA,
        "handoff_id": "handoff-001",
        "created_at": "2026-09-24T12:00:00Z",
        "contract": HANDOFF_CONTRACT,
        "candidates": [candidate],
    }


def _candidate() -> dict[str, object]:
    return {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": "candidate-001",
        "statement": "Synthetic candidate statement.",
        "canonicality": "candidate_only",
        "lifecycle_state": "handed_off",
        "lifecycle": [{"state": "created"}, {"state": "handed_off"}],
        "evidence": [{"id": "evidence-001", "active_context": {}}],
        "provenance": {"created_by_stage": "T5"},
        "trust": {"conflicts": [], "contradiction_context": {"unresolved": []}},
        "uncertainty": {"confidence": "medium"},
        "beneficiaries": [],
        "forced_expenditures": [],
        "relations": [],
        "temporal": {"observed_at": "2026-09-24T11:00:00Z"},
    }


def _codes(issues: tuple[Issue, ...]) -> set[str]:
    return {issue.code for issue in issues}


if __name__ == "__main__":
    unittest.main()
