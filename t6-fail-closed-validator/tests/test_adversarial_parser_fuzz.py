from __future__ import annotations

import unittest

from hydra_t6_failclosed.handoff import (
    FORBIDDEN_FIELDS,
    _scan_authority_smuggling,
)


class AdversarialParserFuzzTests(unittest.TestCase):
    def _issues_for(self, value):
        return _scan_authority_smuggling(
            {"provenance": {"layers": [value]}},
            path="$.handoff.candidates[0]",
            candidate_id="candidate-001",
        )

    def assert_rejected(self, value):
        self.assertIn(
            "candidate_authority_smuggling",
            {issue.code for issue in self._issues_for(value)},
        )

    def test_strong_authority_markers_cannot_hide_behind_prefixes_or_suffixes(self):
        for marker in sorted(item for item in FORBIDDEN_FIELDS if "_" in item):
            compact = marker.replace("_", "")
            for spelling in (
                f"metadata{compact}Flag",
                f"x_{marker}_audit",
                f"pre.{compact}.post",
            ):
                with self.subTest(marker=marker, spelling=spelling):
                    self.assert_rejected({spelling: True})

    def test_format_controls_and_punctuation_cannot_split_authority_marker(self):
        marker = "canonicaltruthselected"
        separators = ("\u200b", "\u2060", "\u202e", ".", "-", "/", ":", " ")
        for separator in separators:
            spelling = separator.join(marker)
            with self.subTest(separator=repr(separator)):
                self.assert_rejected({spelling: True})

    def test_dense_confusable_marker_with_wrapper_is_rejected(self):
        spelling = "canonicaltruthselected".translate(str.maketrans({
            "a": "\u0430",
            "c": "\u0441",
            "e": "\u0435",
            "i": "\u0456",
            "o": "\u043e",
        }))
        self.assert_rejected({f"meta{spelling}Flag": True})

    def test_deep_nested_arrays_do_not_hide_authority_marker(self):
        value = {"safeMetadata": [[[{"canonicalTruthSelected": True}]]]}
        self.assert_rejected(value)

    def test_near_miss_metadata_remains_allowed(self):
        benign = {
            "canonicalReviewer": "Rene",
            "winnerSourceLabel": "historical-column-name",
            "truthConfidence": "high",
            "executionWindowNotes": "descriptive prose only",
        }
        issues = self._issues_for(benign)
        self.assertEqual(issues, [])

    def test_heterogeneous_payload_scan_is_deterministic_and_inert(self):
        payload = {
            "createdByStage": "T5",
            "counts": [0, 1, None, False, 3.5],
            "nested": [{"reviewWindow": "2026-09-25"}, ["text", {"safe": True}]],
        }
        first = self._issues_for(payload)
        second = self._issues_for(payload)
        self.assertEqual(first, second)
        self.assertEqual(first, [])


if __name__ == "__main__":
    unittest.main()
