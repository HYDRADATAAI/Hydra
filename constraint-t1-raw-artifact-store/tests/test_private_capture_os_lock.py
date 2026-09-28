from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = (
    ROOT
    / "tools"
    / "private"
    / "HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_FIRST_SLICE_CAPTURE_V001_20260926.py"
)
SPEC = importlib.util.spec_from_file_location("hydra_constraint_capture_lock", TOOL)
assert SPEC is not None and SPEC.loader is not None
capture = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capture
SPEC.loader.exec_module(capture)


class PrivateCaptureOsLockTests(unittest.TestCase):
    def test_preexisting_stale_lock_file_does_not_block_without_active_os_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            private_root = Path(tmp)
            lock_dir = private_root / "locks"
            lock_dir.mkdir(parents=True)
            lock_path = (
                lock_dir
                / "HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_CAPTURE.lock"
            )
            lock_path.write_text(
                "pid=999999\n"
                "acquired_at=2026-09-25T00:00:00Z\n"
                "private_root=stale\n",
                encoding="utf-8",
            )

            with capture._exclusive_private_capture_lock(private_root) as acquired:
                self.assertEqual(acquired, lock_path)
                text = lock_path.read_text(encoding="utf-8")
                self.assertIn("pid=", text)
                self.assertIn("acquired_at=", text)
                self.assertIn(f"private_root={private_root}", text)

    def test_lock_can_be_reacquired_after_previous_owner_releases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            private_root = Path(tmp)
            with capture._exclusive_private_capture_lock(private_root):
                pass
            with capture._exclusive_private_capture_lock(private_root) as acquired:
                self.assertTrue(acquired.is_file())


if __name__ == "__main__":
    unittest.main()
