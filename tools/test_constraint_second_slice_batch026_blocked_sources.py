#!/usr/bin/env python3
"""Offline regressions for retired Batch026 operational entrypoints."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from constraint_source_quarantine import QuarantinePolicyError, reject_retired_batch026

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
QUEUE_REL = Path(
    "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/"
    "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
)
MANUAL_LAUNCHER = TOOLS / "Invoke-HydraConstraintSemiconductorBatch026PrivateT1.ps1"
PRIVATE_LAUNCHER = TOOLS / "private/Invoke-HYDRAConstraintSemiconductorBatch026BrowserCapture_V001_20260927.ps1"
PYTHON_ENTRYPOINTS = (
    (
        TOOLS / "private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py",
        "browser capture",
    ),
    (TOOLS / "materialize_constraint_second_slice_batch026_private_t1.py", "materialization"),
    (TOOLS / "verify_constraint_second_slice_batch026_private_t1.py", "verification"),
    (TOOLS / "build_constraint_second_slice_batch026_private_t1_handback.py", "handback generation"),
)
PWSH = shutil.which("pwsh")
RETIREMENT_TOKEN = "SUPERSEDED_BY_BATCH030_QUARANTINE"


def run_python_entrypoint(script: Path, operation: str, temp_root: Path) -> subprocess.CompletedProcess[str]:
    private_root = temp_root / "private"
    inbox_root = temp_root / "inbox"
    args = [sys.executable, "-B", str(script), "--repo-root", str(ROOT), "--private-root", str(private_root)]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if operation == "browser capture":
        stub_root = temp_root / "playwright_stub"
        package_root = stub_root / "playwright"
        package_root.mkdir(parents=True)
        (package_root / "__init__.py").write_text("", encoding="utf-8")
        (package_root / "sync_api.py").write_text(
            "def sync_playwright():\n"
            "    raise RuntimeError('TEST_SENTINEL_PLAYWRIGHT_REACHED')\n",
            encoding="utf-8",
        )
        env["PYTHONPATH"] = os.pathsep.join(
            part for part in (str(stub_root), env.get("PYTHONPATH", "")) if part
        )
        private_root.mkdir(parents=True)
        inbox_root.mkdir(parents=True)
        (private_root / "preserve-sentinel.txt").write_text("private root untouched", encoding="utf-8")
        (inbox_root / "preserve-sentinel.txt").write_text("inbox untouched", encoding="utf-8")
        args.extend(("--authorized-public-acquisition", "--fresh", "--inbox-root", str(inbox_root)))
    elif operation == "materialization":
        args.extend(("--inbox-root", str(inbox_root), "--dry-run"))
    elif operation == "handback generation":
        args.extend(("--output-path", str(temp_root / "output" / "handback.json")))
    return subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True, check=False)


class RetiredBatch026EntrypointTest(unittest.TestCase):
    def test_quarantine_policy_fails_closed_on_manifest_drift(self) -> None:
        queue_doc = json.loads((ROOT / QUEUE_REL).read_text(encoding="utf-8"))
        queue = queue_doc["queue"]
        with self.assertRaisesRegex(QuarantinePolicyError, RETIREMENT_TOKEN):
            reject_retired_batch026(ROOT, queue, operation="test")

        with tempfile.TemporaryDirectory(prefix="hydra-retired-b026-policy-") as temporary_directory:
            temp_root = Path(temporary_directory)
            manifest_path = temp_root / "docs" / "constraint" / "second_slice" / "semiconductor_advanced_packaging_critical_materials_v1" / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001_20260927.json"
            manifest_path.parent.mkdir(parents=True)
            manifest = json.loads((ROOT / QUEUE_REL.parent / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_MICRON_SOURCE_QUARANTINE_V001_20260927.json").read_text(encoding="utf-8"))
            manifest["retry_authorized"] = True
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(QuarantinePolicyError, "mutation/retry policy drift"):
                reject_retired_batch026(temp_root, queue, operation="test")

    def test_python_capture_requires_its_existing_authorization_switch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hydra-retired-b026-no-auth-") as temporary_directory:
            temp_root = Path(temporary_directory)
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(PYTHON_ENTRYPOINTS[0][0]),
                    "--repo-root",
                    str(ROOT),
                    "--private-root",
                    str(temp_root / "private"),
                    "--inbox-root",
                    str(temp_root / "inbox"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 2, output)
            self.assertIn("explicit --authorized-public-acquisition is required", output)
            self.assertFalse((temp_root / "private").exists())
            self.assertFalse((temp_root / "inbox").exists())

    def test_python_cli_entrypoints_reject_before_private_side_effects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hydra-retired-b026-") as temporary_directory:
            temp_root = Path(temporary_directory)
            for script, operation in PYTHON_ENTRYPOINTS:
                with self.subTest(entrypoint=script.name):
                    result = run_python_entrypoint(script, operation, temp_root / script.stem)
                    output = result.stdout + result.stderr
                    self.assertEqual(result.returncode, 1, output)
                    self.assertIn(RETIREMENT_TOKEN, output)
                    self.assertIn(f"Batch026 {operation} is closed", output)
                    if operation == "browser capture":
                        self.assertEqual(
                            (temp_root / script.stem / "private" / "preserve-sentinel.txt").read_text(encoding="utf-8"),
                            "private root untouched",
                        )
                        self.assertEqual(
                            (temp_root / script.stem / "inbox" / "preserve-sentinel.txt").read_text(encoding="utf-8"),
                            "inbox untouched",
                        )
                        self.assertNotIn("TEST_SENTINEL_PLAYWRIGHT_REACHED", output)
                    else:
                        self.assertFalse((temp_root / script.stem / "private").exists())
                        self.assertFalse((temp_root / script.stem / "inbox").exists())
                    self.assertFalse((temp_root / script.stem / "output").exists())

    @unittest.skipUnless(PWSH, "PowerShell Core is unavailable")
    def test_manual_launcher_closes_all_operational_modes_but_keeps_contract_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hydra-retired-b026-ps-") as temporary_directory:
            temp_root = Path(temporary_directory)
            for mode in ("Prep", "Status", "Materialize", "Verify", "All"):
                roots = temp_root / mode
                result = subprocess.run(
                    [
                        PWSH,
                        "-NoProfile",
                        "-File",
                        str(MANUAL_LAUNCHER),
                        "-Mode",
                        mode,
                        "-RepoRoot",
                        str(ROOT),
                        "-PrivateRoot",
                        str(roots / "private"),
                        "-InboxRoot",
                        str(roots / "inbox"),
                        "-HandbackRoot",
                        str(roots / "handback"),
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 1, output)
                self.assertIn("BATCH027_WORKSTATION_LAUNCHER=FAIL", output)
                self.assertIn(RETIREMENT_TOKEN, output)
                self.assertFalse((roots / "private").exists())
                self.assertFalse((roots / "inbox").exists())
                self.assertFalse((roots / "handback").exists())

            contract_check = subprocess.run(
                [PWSH, "-NoProfile", "-File", str(MANUAL_LAUNCHER), "-Mode", "ContractCheck", "-RepoRoot", str(ROOT)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(contract_check.returncode, 0, contract_check.stdout + contract_check.stderr)
            self.assertIn("BATCH026_OPERATIONAL_MODES=CLOSED", contract_check.stdout)

    @unittest.skipUnless(PWSH, "PowerShell Core is unavailable")
    def test_private_capture_launcher_exits_before_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory(prefix="hydra-retired-b026-bootstrap-") as temporary_directory:
            temp_root = Path(temporary_directory)
            private_root = temp_root / "private"
            inbox_root = temp_root / "inbox"
            result = subprocess.run(
                [
                    PWSH,
                    "-NoProfile",
                    "-File",
                    str(PRIVATE_LAUNCHER),
                    "-AuthorizedPublicAcquisition",
                    "-RepoRoot",
                    str(ROOT),
                    "-PrivateRoot",
                    str(private_root),
                    "-InboxRoot",
                    str(inbox_root),
                    "-NoBootstrap",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 1, output)
            self.assertIn("HYDRA_CONSTRAINT_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE=FAIL", output)
            self.assertIn(RETIREMENT_TOKEN, output)
            self.assertNotIn("STARTING_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE=YES", output)
            self.assertFalse(private_root.exists())
            self.assertFalse(inbox_root.exists())


if __name__ == "__main__":
    unittest.main()
