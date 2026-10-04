"""Bounded normalization regressions for Mapping document inputs."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from hydra_t6_failclosed.documents import canonical_json_bytes, parse_json_document


class DocumentMappingBoundsTests(unittest.TestCase):
    def test_oversized_raw_text_is_rejected_before_encode(self):
        class HugeText(str):
            def encode(self, *args, **kwargs):
                raise AssertionError("subclass encoder must not run")

        document = parse_json_document(HugeText("x" * 1_000_000), label="input", max_bytes=64)

        self.assertEqual([issue.code for issue in document.issues], ["document_too_large"])

    def test_oversized_bytearray_is_rejected_before_copy(self):
        document = parse_json_document(bytearray(65), label="input", max_bytes=64)

        self.assertEqual([issue.code for issue in document.issues], ["document_too_large"])
        self.assertEqual(document.issues[0].evidence["size_bytes"], 65)

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

    def test_oversized_string_subclass_stops_during_base_measurement(self):
        class HugeString(str):
            def __iter__(self):
                return iter("x")

        value = {"payload": HugeString("x" * 1_000_000)}

        with patch(
            "hydra_t6_failclosed.documents.json.dumps",
            side_effect=AssertionError("encoding must not run"),
        ):
            document = parse_json_document(value, label="input", max_bytes=64)

        self.assertEqual([issue.code for issue in document.issues], ["document_too_large"])

    def test_empty_mapping_over_limit_stops_before_encoding(self):
        with patch(
            "hydra_t6_failclosed.documents.json.dumps",
            side_effect=AssertionError("encoding must not run"),
        ):
            document = parse_json_document({}, label="input", max_bytes=1)

        self.assertEqual([issue.code for issue in document.issues], ["document_too_large"])
        self.assertEqual(document.issues[0].evidence["size_bytes"], 2)

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

        value = {"number": HostileInt(10**1_000_000)}

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

    def test_control_escapes_at_exact_byte_limit_keep_canonical_size(self):
        value = {"x": "\n"}

        document = parse_json_document(value, label="input", max_bytes=10)

        self.assertEqual(document.issues, ())
        self.assertEqual(document.raw, canonical_json_bytes(value))
        self.assertEqual(len(document.raw), 10)

    def test_distinct_string_keys_that_normalize_to_duplicates_are_rejected(self):
        class IdentityString(str):
            __hash__ = object.__hash__
            __eq__ = object.__eq__

        def colliding_mapping():
            return {IdentityString("field"): 1, IdentityString("field"): 2}

        for value in (colliding_mapping(), {"nested": colliding_mapping()}):
            with self.subTest(value=value):
                document = parse_json_document(value, label="input", max_bytes=128)
                self.assertIsNone(document.value)
                self.assertEqual([issue.code for issue in document.issues], ["document_type_invalid"])

    def test_numeric_subclass_keys_that_become_equal_are_rejected(self):
        class IdentityInt(int):
            __hash__ = object.__hash__
            __eq__ = object.__eq__

        class IdentityFloat(float):
            __hash__ = object.__hash__
            __eq__ = object.__eq__

        value = {IdentityInt(1): "integer", IdentityFloat(1.0): "float"}

        document = parse_json_document(value, label="input", max_bytes=128)

        self.assertIsNone(document.value)
        self.assertEqual([issue.code for issue in document.issues], ["document_type_invalid"])

    def test_boolean_mapping_key_keeps_json_encoder_coercion(self):
        value = {True: "yes"}

        document = parse_json_document(value, label="input", max_bytes=32)

        self.assertEqual(document.issues, ())
        self.assertEqual(document.raw, b'{"true":"yes"}')

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
