from __future__ import annotations

import json
import unittest

from hydra_constraint.operations import DriftGuard


ROOT_KEYS = ["cik", "name", "filings"]
RECENT_KEYS = [
    "accessionNumber",
    "filingDate",
    "reportDate",
    "form",
    "primaryDocument",
]


def guard():
    return DriftGuard({
        "sec": {
            "required_root_keys": ROOT_KEYS,
            "required_recent_keys": RECENT_KEYS,
        }
    })


def payload(recent=None, **changes):
    value = {
        "cik": "1",
        "name": "Example Company",
        "filings": {
            "recent": recent if recent is not None else {
                "accessionNumber": ["0000000001-26-000001"],
                "filingDate": ["2026-10-01"],
                "reportDate": ["2026-09-30"],
                "form": ["10-Q"],
                "primaryDocument": ["report.htm"],
            }
        },
    }
    value.update(changes)
    return value


class SecJsonDriftShapeTests(unittest.TestCase):
    def inspect(self, value):
        body = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
        return guard().inspect("sec", "sec_json", body)

    def test_parallel_recent_columns_with_equal_lengths_pass(self):
        result = self.inspect(payload())
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.parser_version, "1.0.1")

    def test_empty_parallel_recent_columns_are_valid(self):
        recent = {key: [] for key in RECENT_KEYS}
        self.assertEqual(self.inspect(payload(recent)).status, "PASS")

    def test_non_object_root_and_filings_shapes_freeze_without_crashing(self):
        malformed = [
            [],
            None,
            True,
            {"cik": "1", "name": "Example Company", "filings": None},
            {"cik": "1", "name": "Example Company", "filings": []},
            {"cik": "1", "name": "Example Company", "filings": {"recent": None}},
            {"cik": "1", "name": "Example Company", "filings": {"recent": []}},
        ]
        for value in malformed:
            with self.subTest(value=value):
                result = self.inspect(value)
                self.assertEqual(result.status, "FROZEN")

    def test_non_array_recent_columns_freeze(self):
        for malformed in (None, {}, 17, False, "10-Q"):
            recent = payload()["filings"]["recent"]
            recent["form"] = malformed
            with self.subTest(value=malformed):
                result = self.inspect(payload(recent))
                self.assertEqual(result.status, "FROZEN")
                self.assertIn("invalid_recent_array:form", result.issues)

    def test_misaligned_columns_freeze(self):
        recent = payload()["filings"]["recent"]
        recent["form"] = ["10-Q", "8-K"]
        result = self.inspect(payload(recent))
        self.assertEqual(result.status, "FROZEN")
        self.assertIn("inconsistent_recent_array_lengths", result.issues)

    def test_non_string_column_values_freeze(self):
        recent = payload()["filings"]["recent"]
        recent["accessionNumber"] = [17]
        result = self.inspect(payload(recent))
        self.assertEqual(result.status, "FROZEN")
        self.assertIn("invalid_recent_value_type:accessionNumber", result.issues)

    def test_critical_root_value_types_freeze(self):
        for changes in ({"cik": True}, {"cik": ""}, {"name": 17}, {"name": ""}):
            with self.subTest(changes=changes):
                result = self.inspect(payload(**changes))
                self.assertEqual(result.status, "FROZEN")


if __name__ == "__main__":
    unittest.main()
