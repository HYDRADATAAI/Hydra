"""Require Batch034 CLI output to preserve the exact reviewed Git blob bytes."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_constraint_second_slice_batch034_t2_evidence_lineage.py"
BINDING = "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_SEMICONDUCTOR_ORDINARY_T2_EVIDENCE_LINEAGE_BINDING_V001_20260928.json"
REVIEWED_BLOB = "9cff667fabcf2a10025dc7c6466b99676470dfea"


class Batch034BuilderBytesTests(unittest.TestCase):
    def test_cli_output_matches_exact_reviewed_blob(self):
        # Hashes identify these bytes; they do not prove historical time or authority.
        expected = subprocess.check_output(["git", "cat-file", "blob", REVIEWED_BLOB], cwd=ROOT)
        tracked = subprocess.check_output(["git", "rev-parse", "HEAD:" + BINDING], cwd=ROOT, text=True).strip()
        self.assertEqual(tracked, REVIEWED_BLOB)
        with tempfile.TemporaryDirectory(prefix="batch034-byte-test-") as temp:
            output = Path(temp) / "rebuilt.json"
            process = subprocess.run(
                [sys.executable, "-B", str(BUILDER), "--output", str(output)],
                cwd=temp, capture_output=True, text=True, timeout=60,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            actual = output.read_bytes()
            self.assertTrue(actual == expected,
                            f"Exact reviewed bytes differ: expected={len(expected)}, actual={len(actual)}, "
                            f"expected_CRLF={expected.count(bytes([13, 10]))}, actual_CRLF={actual.count(bytes([13, 10]))}")


if __name__ == "__main__":
    unittest.main()
