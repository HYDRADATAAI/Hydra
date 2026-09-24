from __future__ import annotations

import unittest

from hydra_t6_failclosed.documents import canonical_json_bytes, parse_json_document


class DocumentContractTests(unittest.TestCase):
    def test_canonical_json_is_deterministic(self) -> None:
        left = canonical_json_bytes({"b": 2, "a": 1})
        right = canonical_json_bytes({"a": 1, "b": 2})
        self.assertEqual(left, right)
        self.assertEqual(left, b'{"a":1,"b":2}')

    def test_duplicate_json_keys_are_rejected(self) -> None:
        document = parse_json_document('{"a": 1, "a": 2}', label="$.document")
        self.assertIsNone(document.value)
        self.assertIn("document_json_invalid", {issue.code for issue in document.issues})

    def test_nonfinite_numbers_are_rejected(self) -> None:
        document = parse_json_document('{"value": NaN}', label="$.document")
        self.assertIsNone(document.value)
        self.assertIn("document_json_invalid", {issue.code for issue in document.issues})

    def test_root_must_be_an_object(self) -> None:
        document = parse_json_document('[]', label="$.document")
        self.assertIsNone(document.value)
        self.assertIn("document_root_invalid", {issue.code for issue in document.issues})


if __name__ == "__main__":
    unittest.main()
