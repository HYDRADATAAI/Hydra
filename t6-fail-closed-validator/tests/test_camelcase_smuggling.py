from __future__ import annotations

import unittest

from hydra_t6_failclosed.handoff import (
    FORBIDDEN_FIELDS,
    FORBIDDEN_VALUE_MARKERS,
    _scan_authority_smuggling,
)


class CamelCaseAuthoritySmugglingTests(unittest.TestCase):
    def assert_smuggling_rejected(self, attack):
        issues = _scan_authority_smuggling(
            {"provenance": {"nested": [attack]}},
            path="$.handoff.candidates[0]",
            candidate_id="candidate-001",
        )
        self.assertIn("candidate_authority_smuggling", {issue.code for issue in issues})

    def test_authority_field_spelling_variants_are_rejected(self):
        fullwidth = "".join(chr(ord(character) + 0xFEE0) for character in "canonicalTruthSelected")
        dense_confusables = "canonicaltruthselected".translate(str.maketrans({
            "a": "\u0430", "c": "\u0441", "e": "\u0435", "i": "\u0456", "o": "\u043e",
        }))
        attacks = [
            {"canonicalTruthSelected": True},
            {"CanonicalTruthSelected": True},
            {"CANONICALTruthSelected": True},
            {"canonicaltruthselected": True},
            {"canonical.Truth-Selected": True},
            {"canon\u00edcalTruthSelected": True},
            {"canon\u0456calTruthSelected": True},
            {dense_confusables: True},
            {fullwidth: True},
            {"canonicalStoreMutationAuthorized": True},
            {"promotionAuthorized": True},
        ]
        for attack in attacks:
            with self.subTest(attack=attack):
                self.assert_smuggling_rejected(attack)

    def test_authority_value_spelling_variants_are_rejected(self):
        fullwidth = "".join(chr(ord(character) + 0xFEE0) for character in "canonicalTruth")
        dense_confusables = "canonicaltruth".translate(str.maketrans({
            "a": "\u03b1", "c": "\u03f2", "i": "\u03b9", "o": "\u03bf",
        }))
        attacks = [
            {"contextId": "canonicalTruth"},
            {"contextId": "CANONICALTruth"},
            {"contextId": "canonicaltruth"},
            {"contextId": "canon\u00edcalTruth"},
            {"contextId": "canon\u0456calTruth"},
            {"contextId": dense_confusables},
            {"contextId": fullwidth},
        ]
        for attack in attacks:
            with self.subTest(attack=attack):
                self.assert_smuggling_rejected(attack)

    def test_all_forbidden_fields_reject_compacted_and_acronym_forms(self):
        for marker in sorted(FORBIDDEN_FIELDS):
            words = marker.split("_")
            spellings = {
                marker.replace("_", ""),
                words[0].upper() + "".join(word.title() for word in words[1:]),
            }
            for spelling in spellings:
                with self.subTest(marker=marker, spelling=spelling):
                    self.assert_smuggling_rejected({spelling: True})

    def test_all_forbidden_values_reject_compacted_forms(self):
        for marker in sorted(FORBIDDEN_VALUE_MARKERS):
            with self.subTest(marker=marker):
                self.assert_smuggling_rejected({"contextId": marker.replace("_", "")})


    def test_all_forbidden_fields_reject_dense_common_confusables(self):
        dense_map = str.maketrans({
            "a": "\u0430", "c": "\u0441", "e": "\u0435", "i": "\u0456",
            "o": "\u043e", "p": "\u0440", "x": "\u0445", "y": "\u0443",
        })
        for marker in sorted(FORBIDDEN_FIELDS):
            spelling = marker.replace("_", "").translate(dense_map)
            with self.subTest(marker=marker, spelling=spelling):
                self.assert_smuggling_rejected({spelling: True})

    def test_all_forbidden_values_reject_dense_common_confusables(self):
        dense_map = str.maketrans({
            "a": "\u03b1", "c": "\u03f2", "e": "\u03b5", "i": "\u03b9",
            "o": "\u03bf", "p": "\u03c1", "x": "\u03c7",
        })
        for marker in sorted(FORBIDDEN_VALUE_MARKERS):
            spelling = marker.replace("_", "").translate(dense_map)
            with self.subTest(marker=marker, spelling=spelling):
                self.assert_smuggling_rejected({"contextId": spelling})

    def test_non_authority_camel_case_metadata_is_allowed(self):
        issues = _scan_authority_smuggling(
            {
                "provenance": {
                    "createdByStage": "T5",
                    "canonicalReviewer": "Ren\u00e9",
                    "truthConfidence": "high",
                    "\u65e5\u672c\u8a9e": "review metadata",
                }
            },
            path="$.handoff.candidates[0]",
            candidate_id="candidate-001",
        )
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
