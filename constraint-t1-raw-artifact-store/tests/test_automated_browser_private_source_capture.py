from __future__ import annotations

import importlib.util
import shutil
import subprocess
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
LAUNCHER = (
    ROOT
    / "tools"
    / "private"
    / "Invoke-HYDRAConstraintFirstSliceAutomatedBrowserCapture_V001_20260926.ps1"
)
SPEC = importlib.util.spec_from_file_location("hydra_constraint_automated_browser_capture", TOOL)
assert SPEC is not None and SPEC.loader is not None
capture = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = capture
SPEC.loader.exec_module(capture)


def source(source_id: str, url: str) -> dict:
    return {"source_id": source_id, "url": url}


def registry(rows: list[dict]) -> dict:
    return {"slice_id": capture.EXPECTED_SLICE_ID, "sources": rows}


def nine_sources() -> list[dict]:
    return [
        source(f"SRC-{index}", f"https://example.com/source-{index}.html")
        for index in range(9)
    ]


class AutomatedBrowserPrivateSourceCaptureTests(unittest.TestCase):
    def test_parser_requires_explicit_authorized_public_acquisition_for_run(self) -> None:
        parser = capture.build_parser()
        args = parser.parse_args([])
        self.assertFalse(args.authorized_public_acquisition)
        self.assertEqual(args.private_root, r"D:\HYDRA\_PRIVATE\constraint")

        with self.assertRaisesRegex(capture.CaptureError, "explicit --authorized-public-acquisition"):
            capture.run(args)

    def test_parser_accepts_explicit_authorization_switch(self) -> None:
        parser = capture.build_parser()
        args = parser.parse_args(["--authorized-public-acquisition"])
        self.assertTrue(args.authorized_public_acquisition)

    def test_target_closed_errors_are_classified_for_browser_restart(self) -> None:
        self.assertTrue(
            capture._is_target_closed_error(
                RuntimeError("Target page, context or browser has been closed")
            )
        )
        self.assertTrue(
            capture._is_target_closed_error(
                RuntimeError("TargetClosedError: browser has been closed")
            )
        )
        self.assertFalse(
            capture._is_target_closed_error(
                RuntimeError("response MIME type did not match")
            )
        )

    def test_parser_defaults_two_browser_restart_retries(self) -> None:
        parser = capture.build_parser()
        args = parser.parse_args([])
        self.assertEqual(args.browser_restart_retries, 2)

    def test_capture_metadata_contains_private_body_path_only_for_private_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            row = capture.CapturedDocument(
                source_id="SRC-X",
                source_locator="https://example.com/x",
                source_version_id="SV-X-1",
                acquired_at="2026-09-26T20:00:00Z",
                status=200,
                content_type="text/html",
                byte_length=1234,
                artifact_sha256="a" * 64,
                body_path=Path(tmp) / "x.html",
                capture_method="PLAYWRIGHT_INSTALLED_BROWSER_MAIN_DOCUMENT",
                browser_channel="chrome",
                redirect_chain=("https://example.com/x",),
            )
            metadata = capture._capture_metadata(row)
            self.assertEqual(metadata["body_path"], str(row.body_path))
            self.assertEqual(metadata["source_id"], "SRC-X")
            self.assertEqual(metadata["http_status"], 200)

    def test_runner_wires_post_capture_status_into_final_validation(self) -> None:
        text = TOOL.read_text(encoding="utf-8")
        self.assertIn(
            "_validate_post_outputs(attestation_path, replay_path, post_capture_status_path)",
            text,
        )
        self.assertIn("CAPTURE_JOURNAL_SCHEMA", text)
        self.assertIn("t1_release_written", text)

    def test_registry_requires_exact_nine_unique_source_ids_and_locators(self) -> None:
        rows = nine_sources()
        self.assertEqual(len(capture.validate_registry(registry(rows))), 9)

        duplicate_id = nine_sources()
        duplicate_id[-1]["source_id"] = duplicate_id[0]["source_id"]
        with self.assertRaisesRegex(capture.CaptureError, "duplicate source identity"):
            capture.validate_registry(registry(duplicate_id))

        duplicate_locator = nine_sources()
        duplicate_locator[-1]["url"] = duplicate_locator[0]["url"]
        with self.assertRaisesRegex(capture.CaptureError, "duplicate exact source locator"):
            capture.validate_registry(registry(duplicate_locator))

    def test_exact_html_main_document_is_accepted(self) -> None:
        locator = "https://example.com/source.html"
        body = (
            b"<!doctype html><html><head><title>source</title></head><body>"
            + b"x" * 600
            + b"</body></html>"
        )
        observed = capture.validate_main_document(
            source_id="SRC-TEST",
            exact_locator=locator,
            response_url=locator,
            redirect_chain=[locator],
            status=200,
            observed_content_type="text/html; charset=utf-8",
            body=body,
        )
        self.assertEqual(observed, "text/html")

    def test_redirect_or_wrong_url_fails_closed(self) -> None:
        locator = "https://example.com/source.html"
        body = b"<!doctype html><html><body>" + b"x" * 600 + b"</body></html>"
        with self.assertRaisesRegex(capture.CaptureError, "response URL drifted"):
            capture.validate_main_document(
                source_id="SRC-TEST",
                exact_locator=locator,
                response_url="https://mirror.example/source.html",
                redirect_chain=[locator, "https://mirror.example/source.html"],
                status=200,
                observed_content_type="text/html",
                body=body,
            )

        with self.assertRaisesRegex(capture.CaptureError, "redirect chain is not authorized"):
            capture.validate_main_document(
                source_id="SRC-TEST",
                exact_locator=locator,
                response_url=locator,
                redirect_chain=["https://example.com/start", locator],
                status=200,
                observed_content_type="text/html",
                body=body,
            )

    def test_challenge_page_fails_closed(self) -> None:
        locator = "https://example.com/source.html"
        body = (
            b"<!doctype html><html><head><title>Just a moment...</title></head>"
            b"<body>Enable JavaScript and cookies to continue"
            + b"x" * 600
            + b"</body></html>"
        )
        with self.assertRaisesRegex(capture.CaptureError, "challenge/error/interstitial marker"):
            capture.validate_main_document(
                source_id="SRC-TEST",
                exact_locator=locator,
                response_url=locator,
                redirect_chain=[locator],
                status=200,
                observed_content_type="text/html",
                body=body,
            )

    def test_pdf_requires_pdf_mime_and_signature(self) -> None:
        locator = "https://example.com/report.pdf"
        valid_pdf = b"%PDF-1.7\n" + b"x" * 2048
        observed = capture.validate_main_document(
            source_id="SRC-PDF",
            exact_locator=locator,
            response_url=locator,
            redirect_chain=[locator],
            status=200,
            observed_content_type="application/pdf",
            body=valid_pdf,
        )
        self.assertEqual(observed, "application/pdf")

        with self.assertRaisesRegex(capture.CaptureError, "lacks PDF signature"):
            capture.validate_main_document(
                source_id="SRC-PDF",
                exact_locator=locator,
                response_url=locator,
                redirect_chain=[locator],
                status=200,
                observed_content_type="application/pdf",
                body=b"not-a-pdf" + b"x" * 2048,
            )

    def test_windows_launcher_uses_private_runtime_and_no_manual_har(self) -> None:
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn(r'D:\HYDRA\_PRIVATE\constraint', text)
        self.assertIn(
            "HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_FIRST_SLICE_CAPTURE_V001_20260926.py",
            text,
        )
        self.assertIn("AuthorizedPublicAcquisition", text)
        self.assertIn("--authorized-public-acquisition", text)
        self.assertNotIn("SanitizedHar", text)
        self.assertNotIn("playwright install", text.lower())

    def test_windows_launcher_powershell_syntax_when_pwsh_available(self) -> None:
        pwsh = shutil.which("pwsh")
        if pwsh is None:
            self.skipTest("pwsh is not available")
        launcher = str(LAUNCHER).replace("'", "''")
        script = (
            "$tokens=$null; $errors=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{launcher}',[ref]$tokens,[ref]$errors) | Out-Null; "
            "if ($errors.Count -gt 0) { "
            "$errors | ForEach-Object { Write-Error $_.Message }; exit 1 }; exit 0"
        )
        completed = subprocess.run(
            [pwsh, "-NoProfile", "-Command", script],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=(completed.stdout + "\n" + completed.stderr),
        )

    def test_capture_plan_never_supplies_available_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            captured = []
            for index in range(9):
                captured.append(
                    capture.CapturedDocument(
                        source_id=f"SRC-{index}",
                        source_locator=f"https://example.com/{index}.html",
                        source_version_id=f"SV-SRC-{index}-20260926T000000Z-123456789abc",
                        acquired_at="2026-09-26T20:00:00.000000Z",
                        status=200,
                        content_type="text/html",
                        byte_length=1000,
                        artifact_sha256="a" * 64,
                        body_path=root / f"{index}.html",
                        capture_method="PLAYWRIGHT_INSTALLED_BROWSER_MAIN_DOCUMENT",
                        browser_channel="chrome",
                        redirect_chain=(f"https://example.com/{index}.html",),
                    )
                )
            plan = capture._build_capture_plan(
                captured,
                release_id="REL-TEST",
                release_created_at="2026-09-26T20:00:01.000000Z",
            )
            self.assertEqual(plan["availability_mode"], "ACQUISITION_TIME_CONSERVATIVE")
            self.assertEqual(len(plan["captures"]), 9)
            self.assertTrue(all("available_at" not in row for row in plan["captures"]))


if __name__ == "__main__":
    unittest.main()
