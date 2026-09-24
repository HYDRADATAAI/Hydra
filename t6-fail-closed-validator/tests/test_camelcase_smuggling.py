from __future__ import annotations

import unittest

from hydra_t6_failclosed.handoff import _scan_authority_smuggling


class CamelCaseAuthoritySmugglingTests(unittest.TestCase):
    def test_camel_case_authority_markers_are_rejected(self):
        attacks = [
            {"canonicalTruthSelected": True},
            {"canonicalStoreMutationAuthorized": True},
            {"promotionAuthorized": True},
            {"contextId": "canonicalTruth"},
        ]
        for attack in attacks:
            with self.subTest(attack=attack):
                issues = _scan_authority_smuggling(
                    {"provenance": {"nested": attack}},
                    path="$.handoff.candidates[0]",
                    candidate_id="candidate-001",
                )
                self.assertIn("candidate_authority_smuggling", {issue.code for issue in issues})

    def test_non_authority_camel_case_metadata_is_allowed(self):
        issues = _scan_authority_smuggling(
            {"provenance": {"createdByStage": "T5"}},
            path="$.handoff.candidates[0]",
            candidate_id="candidate-001",
        )
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
