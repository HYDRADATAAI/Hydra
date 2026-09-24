from __future__ import annotations

import unittest

from hydra_t6_failclosed.documents import (
    MAX_DOCUMENT_DEPTH,
    canonical_json_bytes,
    parse_json_document,
)


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

    def test_depth_limit_accepts_boundary_and_rejects_next_level(self) -> None:
        accepted = parse_json_document(_nested_object(MAX_DOCUMENT_DEPTH), label="$.document")
        rejected = parse_json_document(_nested_object(MAX_DOCUMENT_DEPTH + 1), label="$.document")

        self.assertIsNotNone(accepted.value)
        self.assertEqual(accepted.issues, ())
        self.assertIsNone(rejected.value)
        self.assertIn("document_too_deep", {issue.code for issue in rejected.issues})

    def test_parser_recursion_is_reported_fail_closed(self) -> None:
        deeply_nested = 1_200
        inputs = [
            '{"nested":' * deeply_nested + "0" + "}" * deeply_nested,
            _nested_object(deeply_nested),
        ]
        for value in inputs:
            with self.subTest(input_type=type(value).__name__):
                document = parse_json_document(value, label="$.document")
                self.assertIsNone(document.value)
                self.assertIn("document_too_deep", {issue.code for issue in document.issues})


def _nested_object(depth: int) -> dict[str, object]:
    value: dict[str, object] = {}
    for _ in range(depth - 1):
        value = {"nested": value}
    return value


if __name__ == "__main__":
    unittest.main()
