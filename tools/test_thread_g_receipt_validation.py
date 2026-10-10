import json
from pathlib import Path
import tempfile
import unittest

from tools.thread_g_receipt_validation import main, validate_receipt_outputs


BASELINE = "a" * 64
CANDIDATE = "b" * 64
BASE_OUTPUTS = (
    "baseline.json",
    "baseline.log",
    "RESULT.json",
    "SOURCE_HASHES.json",
)
REPAIR_OUTPUTS = (
    "repaired_types.json",
    "repaired_types.log",
    "existing_admission.json",
    "existing_admission.log",
    "existing_bridge.json",
    "existing_bridge.log",
)


class ThreadGReceiptValidationTests(unittest.TestCase):
    def write_fixture(self, root, baseline=BASELINE, candidate=BASELINE):
        root.mkdir(parents=True, exist_ok=True)
        report = {
            "baseline_source_sha256": baseline,
            "candidate_source_sha256": candidate,
        }
        (root / "RESULT.json").write_text(json.dumps(report), encoding="utf-8")
        for name in BASE_OUTPUTS:
            (root / name).touch()

    def test_equal_valid_hashes_accept_baseline_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_fixture(root)

            validate_receipt_outputs(root)

    def test_valid_mismatch_requires_all_repair_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_fixture(root, candidate=CANDIDATE)
            for name in REPAIR_OUTPUTS:
                (root / name).touch()

            validate_receipt_outputs(root)

    def test_mismatch_with_missing_repair_receipt_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_fixture(root, candidate=CANDIDATE)
            for name in REPAIR_OUTPUTS[:-1]:
                (root / name).touch()

            with self.assertRaisesRegex(ValueError, "existing_bridge.log"):
                validate_receipt_outputs(root)

    def test_invalid_hashes_fail_closed_even_if_repair_files_exist(self):
        invalid_values = (None, 42, True, "", "A" * 64, "g" * 64, "a" * 63, "a" * 65)
        for field in ("baseline_source_sha256", "candidate_source_sha256"):
            for value in invalid_values:
                with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    report = {
                        "baseline_source_sha256": BASELINE,
                        "candidate_source_sha256": CANDIDATE,
                    }
                    report[field] = value
                    self.write_fixture(root, report[field] if field == "baseline_source_sha256" else BASELINE,
                                        report[field] if field == "candidate_source_sha256" else BASELINE)
                    for name in REPAIR_OUTPUTS:
                        (root / name).touch()
                    with self.assertRaises(ValueError):
                        validate_receipt_outputs(root)

    def test_missing_malformed_non_object_and_ambiguous_reports_fail(self):
        cases = (
            ("missing", None),
            ("malformed", "{"),
            ("non-object", "[]"),
            (
                "duplicate",
                json.dumps({
                    "baseline_source_sha256": BASELINE,
                    "candidate_source_sha256": BASELINE,
                })[:-1] + ', "candidate_source_sha256": "' + CANDIDATE + '"}',
            ),
        )
        for name, contents in cases:
            with self.subTest(report=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for output in BASE_OUTPUTS:
                    if output != "RESULT.json":
                        (root / output).touch()
                if contents is not None:
                    (root / "RESULT.json").write_text(contents, encoding="utf-8")
                with self.assertRaises((OSError, ValueError)):
                    validate_receipt_outputs(root)

    def test_cli_returns_failure_for_missing_required_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_fixture(root)
            (root / "baseline.log").unlink()
            from contextlib import redirect_stderr
            from io import StringIO

            stderr = StringIO()
            with redirect_stderr(stderr):
                status = main([str(root)])

        self.assertEqual(status, 1)
        self.assertIn("baseline.log", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
