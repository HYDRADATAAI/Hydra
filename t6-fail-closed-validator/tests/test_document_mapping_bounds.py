"""Bounded normalization regressions for Mapping document inputs."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from hydra_t6_failclosed.documents import canonical_json_bytes, parse_json_document


class DocumentMappingBoundsTests(unittest.TestCase):
    def test_oversized_nested_string_stops_before_copy_or_encoding(self):
        value = {"nested": {"payload": "\\n" * 100}}

        with (
            patch("copy.deepcopy", side_effect=AssertionError("deepcopy must not run")),
            patch("hydra_t6_failclosed.documents.json.dumps", side_effect=AssertionError("encoding must not run")),
        ):
            document = parse_json_document(value, label="input", max_bytes=64)

        self.assertIsNone(document.value)
        self.assertEqual([issue.code for issue in document.issues], ["document_too_large"])
        self.assertGreater(document.issues[0].evidence["size_bytes"], 64)

    def test_escape_expansion_is_counted_before_encoding(self):
        value = {"payload": "\\\\" * 40}

        with patch(
            "hydra_t6_failclosed.documents.json.dumps",
            side_effect=AssertionError("encoding must not run"),
        ):
            document = parse_json_document(value, label="input", max_bytes=64)

        self.assertEqual([issue.code for issue in document.issues], ["document_too_large"])

    def test_hostile_integer_subclass_cannot_override_size_check(self):
        class HostileInt(int):
            def bit_length(self):
                return 0

        value = {"number": HostileInt(10**1000)}

        with patch(
            "hydra_t6_failclosed.documents.json.dumps",
            side_effect=AssertionError("encoding must not run"),
        ):
            document = parse_json_document(value, label="input", max_bytes=64)

        self.assertEqual([issue.code for issue in document.issues], ["document_too_large"])

    def test_string_subclass_keys_and_values_use_their_full_builtin_text(self):
        class HostileString(str):
            def __iter__(self):
                return iter("x")

        value = {HostileString("actual-key"): HostileString("actual-value")}

        document = parse_json_document(value, label="input", max_bytes=128)

        self.assertEqual(document.issues, ())
        self.assertEqual(document.raw, b'{"actual-key":"actual-value"}')
        self.assertEqual(document.value, {"actual-key": "actual-value"})

    def test_ordinary_mapping_keeps_canonical_bytes_and_value(self):
        value = {
            "z": [1, True, None],
            "a": {"text": "café\\n", "number": 2.5},
        }

        document = parse_json_document(value, label="input", max_bytes=256)

        self.assertEqual(document.issues, ())
        self.assertEqual(document.raw, canonical_json_bytes(value))
        self.assertEqual(document.value, value)


if __name__ == "__main__":
    unittest.main()
