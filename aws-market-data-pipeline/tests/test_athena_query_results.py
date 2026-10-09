from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from verify_athena_query_results import verify_accepted_row_count, verify_result_file


def result_with_count(value: str) -> dict[str, object]:
    return {
        "ResultSet": {
            "Rows": [
                {"Data": [{"VarCharValue": "accepted_rows"}]},
                {"Data": [{"VarCharValue": value}]},
            ]
        }
    }


class AthenaQueryResultTests(unittest.TestCase):
    def test_expected_count_is_accepted(self):
        self.assertEqual(verify_accepted_row_count(result_with_count("3")), 3)

    def test_wrong_count_is_rejected(self):
        for value in ("0", "2", "4"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "expected 3 accepted rows"):
                    verify_accepted_row_count(result_with_count(value))

    def test_malformed_count_and_shape_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid accepted-row count"):
            verify_accepted_row_count(result_with_count("three"))
        with self.assertRaisesRegex(ValueError, "one header and one value row"):
            verify_accepted_row_count({"ResultSet": {"Rows": []}})

    def test_missing_result_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with self.assertRaisesRegex(ValueError, "unable to read Athena result JSON"):
                verify_result_file(missing)


if __name__ == "__main__":
    unittest.main()
