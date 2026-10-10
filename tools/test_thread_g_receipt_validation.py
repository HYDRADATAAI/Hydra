import json
from pathlib import Path
import tempfile
import unittest

from tools.thread_g_receipt_validation import (
    conditional_receipt_outputs,
    main,
)


BASELINE = "a" * 64
CANDIDATE = "b" * 64
REPAIR_OUTPUTS = [
    "repaired_types.json",
    "repaired_types.log",
    "existing_admission.json",
    "existing_admission.log",
    "existing_bridge.json",
    "existing_bridge.log",
]


class ThreadGReceiptValidationTests(unittest.TestCase):
    def test_valid_equal_hashes_require_only_baseline_receipts(self):
        report = {
            "baseline_source_sha256": BASELINE,
            "candidate_source_sha256": BASELINE,
        }

        self.assertEqual(conditional_receipt_outputs(report), [])

    def test_valid_mismatched_hashes_require_every_repair_receipt(self):
        report = {
            "baseline_source_sha256": BASELINE,
            "candidate_source_sha256": CANDIDATE,
        }

        self.assertEqual(conditional_receipt_outputs(report), REPAIR_OUTPUTS)

    def test_invalid_hash_reports_fail_closed(self):
        invalid_values = (None, 42, True, "", "A" * 64, "g" * 64, "a" * 63, "a" * 65)
        for field in ("baseline_source_sha256", "candidate_source_sha256"):
            for value in invalid_values:
                with self.subTest(field=field, value=value):
                    report = {
                        "baseline_source_sha256": BASELINE,
                        "candidate_source_sha256": BASELINE,
                    }
                    report[field] = value
                    with self.assertRaises(ValueError):
                        conditional_receipt_outputs(report)

    def test_missing_hashes_and_non_object_reports_fail_closed(self):
        for report in ({}, {"baseline_source_sha256": BASELINE}, [], None):
            with self.subTest(report=report), self.assertRaises(ValueError):
                conditional_receipt_outputs(report)

    def test_cli_reads_the_same_json_contract_used_by_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "RESULT.json"
            path.write_text(
                json.dumps({
                    "baseline_source_sha256": BASELINE,
                    "candidate_source_sha256": CANDIDATE,
                }),
                encoding="utf-8",
            )
            # The workflow consumes this CLI's JSON output and treats any
            # nonzero exit code as a failed receipt validation.
            from contextlib import redirect_stderr, redirect_stdout
            from io import StringIO

            stdout = StringIO()
            with redirect_stdout(stdout):
                status = main([str(path)])

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout.getvalue()), REPAIR_OUTPUTS)


if __name__ == "__main__":
    unittest.main()
