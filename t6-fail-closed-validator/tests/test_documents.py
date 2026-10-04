from __future__ import annotations

import unittest
from unittest.mock import patch

import hydra_t6_failclosed.documents as documents
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

    def test_malformed_json_is_rejected(self) -> None:
        document = parse_json_document('{"a":', label="$.document")
        self.assertIsNone(document.value)
        self.assertIn("document_json_invalid", {issue.code for issue in document.issues})

    def test_invalid_utf8_is_rejected(self) -> None:
        document = parse_json_document(b"\xff", label="$.document")
        self.assertIsNone(document.value)
        self.assertIn("document_json_invalid", {issue.code for issue in document.issues})

    def test_missing_document_is_rejected(self) -> None:
        document = parse_json_document(None, label="$.document")
        self.assertIsNone(document.value)
        self.assertIn("document_missing", {issue.code for issue in document.issues})

    def test_unsupported_document_type_is_rejected(self) -> None:
        document = parse_json_document([], label="$.document")  # type: ignore[arg-type]
        self.assertIsNone(document.value)
        self.assertIn("document_type_invalid", {issue.code for issue in document.issues})

    def test_oversized_document_is_rejected_before_parsing(self) -> None:
        document = parse_json_document('{"a":1}', label="$.document", max_bytes=2)
        self.assertIsNone(document.value)
        self.assertIn("document_too_large", {issue.code for issue in document.issues})

    def test_excessive_structural_depth_is_rejected_before_downstream_recursion(self) -> None:
        payload = '{"a":' * 140 + '0' + '}' * 140
        document = parse_json_document(payload, label="$.document")
        self.assertIsNone(document.value)
        self.assertIn("document_too_deep", {issue.code for issue in document.issues})

    def test_extreme_json_nesting_fails_closed_instead_of_raising_recursion_error(self) -> None:
        payload = '{"a":' * 2000 + '0' + '}' * 2000
        document = parse_json_document(payload, label="$.document")
        self.assertIsNone(document.value)
        self.assertTrue(
            {"document_json_invalid", "document_too_deep"} &
            {issue.code for issue in document.issues}
        )


    def test_mapping_input_matches_canonical_json_bytes(self) -> None:
        value = {"z": ["λ", True, None, 3.5], "a": {"b": 2}}
        document = parse_json_document(value, label="$.document")
        self.assertEqual(document.raw, canonical_json_bytes(value))
        self.assertEqual(document.value, value)

    def test_oversized_mapping_is_rejected_before_copy_or_json_serialization(self) -> None:
        value = {"outer": {"inner": "x" * 4096}}
        with (
            patch.object(documents, "deepcopy") as copier,
            patch.object(documents, "canonical_json_bytes") as encoder,
        ):
            document = parse_json_document(value, label="$.document", max_bytes=32)
        self.assertIsNone(document.value)
        self.assertIn("document_too_large", {issue.code for issue in document.issues})
        copier.assert_not_called()
        encoder.assert_not_called()

    def test_escaped_mapping_string_is_bounded_by_encoded_bytes(self) -> None:
        value = {"text": "\\\\" * 128}
        with patch.object(documents, "canonical_json_bytes") as encoder:
            document = parse_json_document(value, label="$.document", max_bytes=64)
        self.assertIsNone(document.value)
        self.assertIn("document_too_large", {issue.code for issue in document.issues})
        encoder.assert_not_called()

    def test_string_subclass_values_and_keys_fail_closed(self) -> None:
        class HostileString(str):
            def __iter__(self):
                return iter(())

        cases = (
            {"value": HostileString("x" * 128)},
            {HostileString("k" * 128): "value"},
        )
        for value in cases:
            with self.subTest(value="hostile string subclass"), patch.object(
                documents, "canonical_json_bytes"
            ) as encoder:
                document = parse_json_document(value, label="$.document", max_bytes=32)
            self.assertIsNone(document.value)
            self.assertIn("document_too_large", {issue.code for issue in document.issues})
            encoder.assert_not_called()

    def test_int_subclass_cannot_override_size_preflight(self) -> None:
        class HostileInt(int):
            def bit_length(self) -> int:
                return 0

        value = {"value": HostileInt(10**1000)}
        with patch.object(documents, "canonical_json_bytes") as encoder:
            document = parse_json_document(value, label="$.document", max_bytes=32)
        self.assertIsNone(document.value)
        self.assertIn("document_too_large", {issue.code for issue in document.issues})
        encoder.assert_not_called()


    def test_scalar_mapping_keys_match_canonical_json(self) -> None:
        for value in ({1: "integer"}, {True: "boolean"}, {None: "null"}):
            with self.subTest(key=next(iter(value))):
                document = parse_json_document(value, label="$.document")
            self.assertEqual(document.raw, canonical_json_bytes(value))


    def test_oversized_raw_text_and_bytearray_fail_before_copy(self) -> None:
        for value in (bytearray(b"x" * 128), "x" * 128):
            with self.subTest(value_type=type(value).__name__):
                document = parse_json_document(value, label="$.document", max_bytes=16)
            self.assertIsNone(document.value)
            self.assertIn("document_too_large", {issue.code for issue in document.issues})
            self.assertEqual(document.raw, b"")

    def test_empty_mapping_respects_smaller_configured_limit_before_encoding(self) -> None:
        with patch.object(documents, "canonical_json_bytes") as encoder:
            document = parse_json_document({}, label="$.document", max_bytes=1)
        self.assertIsNone(document.value)
        self.assertIn("document_too_large", {issue.code for issue in document.issues})
        encoder.assert_not_called()


    def test_distinct_hostile_string_keys_with_same_text_fail_closed(self) -> None:
        class DistinctHostileString(str):
            def __iter__(self):
                return iter(())

            def __hash__(self) -> int:
                return object.__hash__(self)

            def __eq__(self, other: object) -> bool:
                return self is other

        first = DistinctHostileString("same")
        second = DistinctHostileString("same")
        value = {first: 1, second: 2}
        self.assertEqual(len(value), 2)
        with patch.object(documents, "canonical_json_bytes") as encoder:
            document = parse_json_document(value, label="$.document", max_bytes=64)
        self.assertIsNone(document.value)
        self.assertIn("document_type_invalid", {issue.code for issue in document.issues})
        encoder.assert_not_called()


    def test_distinct_numeric_keys_that_compare_equal_fail_closed(self) -> None:
        from collections.abc import Mapping

        class HostileFloat(float):
            def __float__(self) -> float:
                return 999.0

        class PairMapping(Mapping):
            def __iter__(self):
                return iter((1, HostileFloat(1.0)))

            def __getitem__(self, key):
                return "first" if type(key) is int else "second"

            def __len__(self) -> int:
                return 2

        with patch.object(documents, "canonical_json_bytes") as encoder:
            document = parse_json_document(PairMapping(), label="$.document", max_bytes=64)
        self.assertIsNone(document.value)
        self.assertIn("document_type_invalid", {issue.code for issue in document.issues})
        encoder.assert_not_called()


    def test_string_subclass_key_and_value_normalize_to_plain_text(self) -> None:
        class HostileString(str):
            def __iter__(self):
                return iter(())

        value = {HostileString("field"): HostileString("value")}
        document = parse_json_document(value, label="$.document")
        self.assertEqual(document.raw, b'{"field":"value"}')
        self.assertEqual(document.value, {"field": "value"})
        self.assertIs(type(next(iter(document.value))), str)
        self.assertIs(type(document.value["field"]), str)


    def test_oversized_bytes_are_rejected_before_hashing_or_parsing(self) -> None:
        payload = b'{"value":"' + b"x" * 4096 + b'"}'
        document = parse_json_document(payload, label="$.document", max_bytes=32)
        self.assertIsNone(document.value)
        self.assertIn("document_too_large", {issue.code for issue in document.issues})
        self.assertEqual(document.raw, b"")

    def test_multibyte_raw_text_uses_utf8_byte_count(self) -> None:
        payload = '{"é":"é"}'
        encoded = payload.encode("utf-8")
        too_small = parse_json_document(payload, label="$.document", max_bytes=len(encoded) - 1)
        self.assertIsNone(too_small.value)
        self.assertIn("document_too_large", {issue.code for issue in too_small.issues})

        exact = parse_json_document(payload, label="$.document", max_bytes=len(encoded))
        self.assertEqual(exact.raw, encoded)
        self.assertEqual(exact.value, {"é": "é"})


    def test_bytes_subclass_cannot_spoof_length_or_decode(self) -> None:
        class HostileBytes(bytes):
            def __len__(self) -> int:
                return 1

            def decode(self, *args, **kwargs) -> str:
                return '{"decoy":true}'

        too_large = HostileBytes(b'{"value":"' + b"x" * 128 + b'"}')
        rejected = parse_json_document(too_large, label="$.document", max_bytes=32)
        self.assertIsNone(rejected.value)
        self.assertIn("document_too_large", {issue.code for issue in rejected.issues})

        small = HostileBytes(b'{"actual":true}')
        accepted = parse_json_document(small, label="$.document", max_bytes=64)
        self.assertEqual(accepted.value, {"actual": True})

    def test_bytearray_subclass_cannot_spoof_length_or_bytes(self) -> None:
        class HostileBytearray(bytearray):
            def __len__(self) -> int:
                return 1

            def __bytes__(self) -> bytes:
                return b"{}"

        payload = HostileBytearray(b'{"value":"' + b"x" * 128 + b'"}')
        document = parse_json_document(payload, label="$.document", max_bytes=32)
        self.assertIsNone(document.value)
        self.assertIn("document_too_large", {issue.code for issue in document.issues})


if __name__ == "__main__":
    unittest.main()
