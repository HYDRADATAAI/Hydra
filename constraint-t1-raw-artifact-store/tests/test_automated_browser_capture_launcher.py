from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = (
    ROOT
    / "tools"
    / "private"
    / "Invoke-HYDRAConstraintFirstSliceAutomatedBrowserCapture_V001_20260926.ps1"
)
RUNNER = (
    ROOT
    / "tools"
    / "private"
    / "HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_FIRST_SLICE_CAPTURE_V001_20260926.py"
)


class AutomatedBrowserCaptureLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.launcher = LAUNCHER.read_text(encoding="utf-8")
        cls.runner = RUNNER.read_text(encoding="utf-8")

    def test_launcher_requires_explicit_authorization(self):
        self.assertIn("[switch]$AuthorizedPublicAcquisition", self.launcher)
        self.assertIn('"--authorized-public-acquisition"', self.launcher)

    def test_private_root_matches_current_hydra_private_root(self):
        self.assertIn('D:\\HYDRA\\_PRIVATE\\constraint', self.launcher)
        self.assertIn(r'D:\HYDRA\_PRIVATE\constraint', self.runner)
        self.assertNotIn(r'D:\HYDRA_PRIVATE\constraint', self.launcher)
        self.assertNotIn(r'D:\HYDRA_PRIVATE\constraint', self.runner)

    def test_launcher_bootstrap_does_not_import_playwright_as_native_probe(self):
        self.assertNotIn('& $VenvPython -c "import playwright"', self.launcher)
        self.assertIn('Lib\\site-packages\\playwright\\__init__.py', self.launcher)
        self.assertIn('$PipExitCode = $LASTEXITCODE', self.launcher)
        self.assertIn('$ErrorActionPreference = "Continue"', self.launcher)

    def test_runner_requires_authorization_even_when_invoked_directly(self):
        self.assertIn(
            'explicit --authorized-public-acquisition is required',
            self.runner,
        )
        self.assertIn(
            'parser.add_argument("--authorized-public-acquisition", action="store_true")',
            self.runner,
        )

    def test_runner_uses_installed_browser_channels_not_playwright_browser_download(self):
        self.assertIn('channels = ("chrome", "msedge")', self.runner)
        self.assertIn("launch_persistent_context", self.runner)
        self.assertNotIn("playwright install", self.launcher)
        self.assertNotIn("playwright install", self.runner)

    def test_runner_requires_exact_main_document_response(self):
        self.assertIn("response_url != exact_locator", self.runner)
        self.assertIn("list(redirect_chain) != [exact_locator]", self.runner)
        self.assertIn("status != 200", self.runner)
        self.assertIn("SOURCE_TEXT_MARKERS", self.runner)
        self.assertIn("HTML_BLOCK_MARKERS", self.runner)

    def test_runner_invokes_existing_post_capture_status_builder(self):
        self.assertIn(
            'POST_CAPTURE_STATUS_BUILDER_RELATIVE_PATH = Path("tools/build_constraint_t1_post_capture_public_status.py")',
            self.runner,
        )
        self.assertIn('"post-capture sanitized status builder"', self.runner)
        self.assertIn('print("POST_CAPTURE_SANITIZED_STATUS=PASS")', self.runner)

    def test_runner_still_blocks_historical_and_native_admission(self):
        self.assertIn('print("STRICT_HISTORICAL_REPLAY=BLOCKED")', self.runner)
        self.assertIn('print("NATIVE_T5_T6_ADMISSION=BLOCKED")', self.runner)
        self.assertIn('print("RAW_SOURCE_PUBLICATION=NO")', self.runner)


if __name__ == "__main__":
    unittest.main()
