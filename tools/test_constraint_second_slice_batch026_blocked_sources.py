#!/usr/bin/env python3
"""Offline regressions for retired Batch026 operational entrypoints."""

from __future__ import annotations

import json
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from constraint_source_quarantine import (
    EXPECTED_MICRON_QUARANTINED_SOURCE_IDS,
    QuarantinePolicyError,
    reject_retired_batch026,
)

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
CAPTURE_RUNNER = TOOLS / "private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py"


def import_capture_runner():
    spec = importlib.util.spec_from_file_location("hydra_batch026_quarantine_api_test", CAPTURE_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to import Batch026 capture runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def test_capture_api_rejects_each_quarantined_id_before_page_or_file_creation(self) -> None:
        runner = import_capture_runner()
        queue_doc = json.loads((ROOT / QUEUE_REL).read_text(encoding="utf-8"))
        blocked_rows = {
            row["source_id"]: row
            for row in queue_doc["queue"]
            if row["source_id"] in set(EXPECTED_MICRON_QUARANTINED_SOURCE_IDS)
        }
        self.assertEqual(set(blocked_rows), set(EXPECTED_MICRON_QUARANTINED_SOURCE_IDS))

        class ContextSpy:
            def __init__(self) -> None:
                self.new_page_calls = 0

            def new_page(self):
                self.new_page_calls += 1
                raise AssertionError("quarantined capture reached browser context")

        test_cases = []
        for index, source_id in enumerate(EXPECTED_MICRON_QUARANTINED_SOURCE_IDS):
            canonical_row = blocked_rows[source_id]
            test_cases.append((f"canonical-{index}", canonical_row, canonical_row["source_locator"]))
            spoofed_row = dict(canonical_row)
            spoofed_row["source_id"] = f"SRC-SEMI-TEST-SPOOF-{index:02d}"
            test_cases.append((f"spoofed-id-{index}", spoofed_row, canonical_row["source_locator"]))

        # A caller cannot evade the row identity check by replacing both the
        # source ID and item locator while passing the canonical locator via
        # capture_one's separate effective-locator argument.
        first_blocked = next(iter(blocked_rows.values()))
        locator_override_item = {
            "source_id": "SRC-SEMI-TEST-CAPTURE-LOCATOR-OVERRIDE",
            "source_version_id": "SV-SEMI-TEST-CAPTURE-LOCATOR-OVERRIDE",
            "capture_intent_id": "CAP-SEMI-TEST-CAPTURE-LOCATOR-OVERRIDE",
            "source_locator": "https://example.invalid/benign.pdf",
            "inbox_filename": "benign.pdf",
            "content_type_hint": "application/pdf",
        }
        test_cases.append(("effective-locator-override", locator_override_item, first_blocked["source_locator"]))

        for index, (case_name, item, capture_locator) in enumerate(test_cases):
            with self.subTest(case=case_name):
                context = ContextSpy()
                capture_path = Path(tempfile.gettempdir()) / "hydra-quarantine-api-test" / f"{index}.pdf"
                sidecar_path = Path(str(capture_path) + ".capture.json")
                with self.assertRaisesRegex(runner.CaptureError, RETIREMENT_TOKEN):
                    runner.capture_one(
                        context=context,
                        browser_channel="test",
                        item=item,
                        capture_path=capture_path,
                        sidecar_path=sidecar_path,
                        capture_locator=capture_locator,
                        redirect_policy="exact",
                        challenge_wait_seconds=0,
                        navigation_timeout_seconds=1,
                    )
                self.assertEqual(context.new_page_calls, 0)
                self.assertFalse(capture_path.exists())
                self.assertFalse(sidecar_path.exists())

    def test_capture_api_guard_allows_current_batch030_and_batch031_ids(self) -> None:
        runner = import_capture_runner()
        base = QUEUE_REL.parent
        successor_queues = (
            base / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH030_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V002_20260927.json",
            base / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH031_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V003_20260928.json",
        )
        for queue_path in successor_queues:
            document = json.loads((ROOT / queue_path).read_text(encoding="utf-8"))
            self.assertTrue(document["queue"], queue_path.name)
            for item in document["queue"]:
                with self.subTest(queue=queue_path.name, source_id=item["source_id"]):
                    runner.reject_quarantined_capture_item(item, item["source_locator"])

    def test_capture_api_rejects_quarantined_provider_hosts_before_page_or_file_creation(self) -> None:
        runner = import_capture_runner()
        host_cases = (
            ("source_locator", "https://micron.com/source.pdf"),
            ("source_locator", "https://Investors.Micron.Com./source.pdf"),
            ("source_locator", "https://globenewswire.com/news"),
            ("source_locator", "https://www.globenewswire.com/news"),
            ("capture_locator", "https://micron.com/source.pdf"),
            ("capture_locator", "https://Investors.Micron.Com./source.pdf"),
            ("capture_locator", "https://globenewswire.com/news"),
            ("capture_locator", "https://www.globenewswire.com/news"),
            ("source_locator", "https://micron.com\\@evil.com/source.pdf"),
            ("source_locator", "https://%6dicron.com/source.pdf"),
            ("source_locator", "https://micron%2ecom/source.pdf"),
            ("source_locator", "https://%67lobenews%77ire.com/news"),
            ("source_locator", "https:/micron.com/source.pdf"),
            ("source_locator", "https:////micron.com/source.pdf"),
            ("source_locator", "https:micron.com/source.pdf"),
            ("source_locator", "https:\\micron.com\\source.pdf"),
            ("capture_locator", "https://micron.com\\@evil.com/source.pdf"),
            ("capture_locator", "https://%6dicron.com/source.pdf"),
            ("capture_locator", "https://micron%2ecom/source.pdf"),
            ("capture_locator", "https://%67lobenews%77ire.com/news"),
            ("capture_locator", "https:/micron.com/source.pdf"),
            ("capture_locator", "https:////micron.com/source.pdf"),
            ("capture_locator", "https:micron.com/source.pdf"),
            ("capture_locator", "https:\\micron.com\\source.pdf"),
        )

        class ContextSpy:
            def __init__(self) -> None:
                self.new_page_calls = 0

            def new_page(self):
                self.new_page_calls += 1
                raise AssertionError("forbidden provider reached browser context")

        for index, (field, locator) in enumerate(host_cases):
            with self.subTest(field=field, locator=locator):
                item = {
                    "source_id": f"SRC-SEMI-TEST-FORBIDDEN-HOST-{index:02d}",
                    "source_version_id": f"SV-SEMI-TEST-FORBIDDEN-HOST-{index:02d}",
                    "capture_intent_id": f"CAP-SEMI-TEST-FORBIDDEN-HOST-{index:02d}",
                    "source_locator": "https://example.com/source.pdf",
                    "inbox_filename": f"source-{index:02d}.pdf",
                    "content_type_hint": "application/pdf",
                }
                capture_locator = "https://example.com/effective.pdf"
                if field == "source_locator":
                    item["source_locator"] = locator
                else:
                    capture_locator = locator
                context = ContextSpy()
                capture_path = Path(tempfile.gettempdir()) / "hydra-provider-domain-test" / f"{index}.pdf"
                sidecar_path = Path(str(capture_path) + ".capture.json")
                with self.assertRaisesRegex(runner.CaptureError, RETIREMENT_TOKEN):
                    runner.capture_one(
                        context=context,
                        browser_channel="test",
                        item=item,
                        capture_path=capture_path,
                        sidecar_path=sidecar_path,
                        capture_locator=capture_locator,
                        redirect_policy="exact",
                        challenge_wait_seconds=0,
                        navigation_timeout_seconds=1,
                    )
                self.assertEqual(context.new_page_calls, 0)
                self.assertFalse(capture_path.exists())
                self.assertFalse(sidecar_path.exists())

    def test_capture_api_blocks_forbidden_redirect_before_request_dispatch(self) -> None:
        runner = import_capture_runner()

        class FakeRoute:
            def __init__(self, url: str) -> None:
                self.request = type("Request", (), {"url": url})()
                self.aborted = False
                self.continued = False

            def abort(self, _reason: str = "") -> None:
                self.aborted = True

            def continue_(self) -> None:
                self.continued = True

        class RedirectPage:
            def __init__(self) -> None:
                self.route_handler = None
                self.goto_calls = 0
                self.routes: list[FakeRoute] = []
                self.closed = False

            def route(self, _pattern: str, handler) -> None:
                self.route_handler = handler

            def on(self, *_args) -> None:
                pass

            def goto(self, _url: str, **_kwargs):
                self.goto_calls += 1
                if self.route_handler is None:
                    raise AssertionError("provider guard was not installed before navigation")
                redirected = FakeRoute("https://micron.com/redirected.pdf")
                self.routes.append(redirected)
                self.route_handler(redirected)
                if redirected.aborted:
                    raise RuntimeError("blocked before network dispatch")
                return None

            def close(self) -> None:
                self.closed = True

        class ContextSpy:
            def __init__(self) -> None:
                self.page = RedirectPage()
                self.new_page_calls = 0

            def new_page(self):
                self.new_page_calls += 1
                return self.page

        context = ContextSpy()
        item = {
            "source_id": "SRC-SEMI-TEST-REDIRECT-GUARD",
            "source_version_id": "SV-SEMI-TEST-REDIRECT-GUARD",
            "capture_intent_id": "CAP-SEMI-TEST-REDIRECT-GUARD",
            "source_locator": "https://example.com/start.html",
            "inbox_filename": "redirect.html",
            "content_type_hint": "text/html",
        }
        capture_path = Path(tempfile.gettempdir()) / "hydra-redirect-guard" / "redirect.html"
        sidecar_path = Path(str(capture_path) + ".capture.json")
        with self.assertRaisesRegex(runner.CaptureError, "blocked forbidden provider request before dispatch"):
            runner.capture_one(
                context=context,
                browser_channel="test",
                item=item,
                capture_path=capture_path,
                sidecar_path=sidecar_path,
                capture_locator="https://example.com/start.html",
                redirect_policy="exact",
                challenge_wait_seconds=0,
                navigation_timeout_seconds=1,
            )
        self.assertEqual(context.new_page_calls, 1)
        self.assertEqual(context.page.goto_calls, 1)
        self.assertEqual(len(context.page.routes), 1)
        self.assertTrue(context.page.routes[0].aborted)
        self.assertFalse(context.page.routes[0].continued)
        self.assertTrue(context.page.closed)
        self.assertFalse(capture_path.exists())
        self.assertFalse(sidecar_path.exists())

    def test_provider_domain_guard_uses_suffix_safe_hostname_matching(self) -> None:
        runner = import_capture_runner()
        item = {
            "source_id": "SRC-SEMI-TEST-HOST-SUFFIX-BOUNDARY",
            "source_version_id": "SV-SEMI-TEST-HOST-SUFFIX-BOUNDARY",
            "capture_intent_id": "CAP-SEMI-TEST-HOST-SUFFIX-BOUNDARY",
            "source_locator": "https://investors.micron.com.example.com/source.pdf",
            "inbox_filename": "suffix-boundary.pdf",
            "content_type_hint": "application/pdf",
        }
        runner.reject_quarantined_capture_item(
            item,
            "https://www.globenewswire.com.example.com/effective.pdf",
        )

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
