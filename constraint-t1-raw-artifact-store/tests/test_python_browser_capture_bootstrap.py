from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = (
    ROOT
    / "tools"
    / "private"
    / "HYDRA_CONSTRAINT_T1_WINDOWS_PYTHON_BROWSER_CAPTURE_BOOTSTRAP_V001_20260926.py"
)
SPEC = importlib.util.spec_from_file_location(
    "hydra_constraint_python_browser_bootstrap",
    BOOTSTRAP,
)
assert SPEC is not None and SPEC.loader is not None
bootstrap = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bootstrap
SPEC.loader.exec_module(bootstrap)


class PythonBrowserCaptureBootstrapTests(unittest.TestCase):
    def test_bootstrap_requires_explicit_public_acquisition_authorization(self) -> None:
        parser = bootstrap.build_parser()
        args = parser.parse_args([])
        self.assertFalse(args.authorized_public_acquisition)

    def test_bootstrap_defaults_to_current_private_root_and_resume_mode(self) -> None:
        parser = bootstrap.build_parser()
        args = parser.parse_args([])
        self.assertEqual(args.private_root, r"D:\HYDRA\_PRIVATE\constraint")
        self.assertFalse(args.fresh)
        self.assertIsNone(args.resume_journal)
        self.assertEqual(args.browser_restart_retries, 2)

    def test_bootstrap_is_repo_anchored_not_drive_scan_based(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("Path(__file__).resolve().parents[2]", text)
        self.assertNotIn("os.walk", text)
        self.assertIn("AUDIT_RESULTS", text)
        self.assertIn("REMOTE_RUNTIME_SNAPSHOT", text)

    def test_bootstrap_only_installs_python_client_not_browser_bundle(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8").lower()
        self.assertIn('"pip"', text)
        self.assertIn('"install"', text)
        self.assertNotIn("playwright install", text)
        self.assertIn("site-packages", text)

    def test_bootstrap_invokes_authoritative_runner_and_forwards_resume_controls(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn(
            "HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_FIRST_SLICE_CAPTURE_V001_20260926.py",
            text,
        )
        self.assertIn('"--resume-journal"', text)
        self.assertIn('"--fresh"', text)
        self.assertIn('"--browser-restart-retries"', text)

    def test_bootstrap_uses_longpaths_and_fast_forward_only_update(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn('"core.longpaths"', text)
        self.assertIn('"--ff-only"', text)


if __name__ == "__main__":
    unittest.main()
