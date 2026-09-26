from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "private" / "Test-HYDRAConstraintThreeSourceSanitizedHarPreflight_V001_20260926.ps1"


class ThreeSourceHarPreflightWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_default_private_har_paths_are_exact(self):
        self.assertIn(
            'D:\\HYDRA_PRIVATE\\constraint\\metadata\\lbnl-queued-up-sanitized.har',
            self.text,
        )
        self.assertIn(
            'D:\\HYDRA_PRIVATE\\constraint\\metadata\\ferc-order-2023-sanitized.har',
            self.text,
        )
        self.assertIn(
            'D:\\HYDRA_PRIVATE\\constraint\\metadata\\pjm-2025-year-review-sanitized.har',
            self.text,
        )

    def test_wrapper_checks_all_three_hars_exist_before_invocation(self):
        self.assertIn('Label = "LBNL HAR"', self.text)
        self.assertIn('Label = "FERC HAR"', self.text)
        self.assertIn('Label = "PJM HAR"', self.text)
        self.assertIn('Test-Path -LiteralPath $entry.Path -PathType Leaf', self.text)

    def test_wrapper_calls_only_read_only_preflight_tool(self):
        self.assertIn(
            "Test-HYDRAConstraintThreeSourceSanitizedHarPreflight_V001_20260926.py",
            self.text,
        )
        self.assertNotIn("first_slice_cli", self.text)
        self.assertNotIn("RawArtifactStore", self.text)
        self.assertNotIn("release_id", self.text)

    def test_wrapper_explicitly_reports_no_t1_creation(self):
        self.assertIn("CAPTURE_PLAN_CREATED=NO", self.text)
        self.assertIn("T1_OBJECTS_CREATED=NO", self.text)
        self.assertIn("T1_RELEASE_CREATED=NO", self.text)


if __name__ == "__main__":
    unittest.main()
