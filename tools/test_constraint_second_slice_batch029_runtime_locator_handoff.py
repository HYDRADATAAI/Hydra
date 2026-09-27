#!/usr/bin/env python3
"""Offline regression test for the Batch029 capture-locator handoff."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py"


def import_runner() -> Any:
    spec = importlib.util.spec_from_file_location("hydra_batch026_capture_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to import Batch026 capture runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeRequest:
    def __init__(self, url: str, frame: object) -> None:
        self.url = url
        self.frame = frame
        self.redirected_from = None

    def is_navigation_request(self) -> bool:
        return True


class FakeResponse:
    status = 200

    def __init__(self, url: str, frame: object, body: bytes, content_type: str) -> None:
        self.url = url
        self.request = FakeRequest(url, frame)
        self._body = body
        self._content_type = content_type
        self.body_calls = 0

    def body(self) -> bytes:
        self.body_calls += 1
        return self._body

    def header_value(self, name: str) -> str | None:
        return self._content_type if name.lower() == "content-type" else None


class FakePage:
    def __init__(self, *, emit_response_event: bool, content_type: str, body: bytes) -> None:
        self.main_frame = object()
        self.response_handler: Any = None
        self.emit_response_event = emit_response_event
        self.content_type = content_type
        self.body = body
        self.goto_calls: list[tuple[str, str, int]] = []
        self.response: FakeResponse | None = None
        self.closed = False

    def on(self, event: str, handler: Any) -> None:
        if event != "response":
            raise AssertionError(f"unexpected event subscription: {event}")
        self.response_handler = handler

    def goto(self, locator: str, *, wait_until: str, timeout: int) -> FakeResponse:
        self.goto_calls.append((locator, wait_until, timeout))
        self.response = FakeResponse(locator, self.main_frame, self.body, self.content_type)
        if self.emit_response_event:
            if self.response_handler is None:
                raise AssertionError("response listener was not registered before navigation")
            self.response_handler(self.response)
        return self.response

    def wait_for_timeout(self, _milliseconds: int) -> None:
        raise AssertionError("the fake response should be processed without waiting")

    def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    def new_page(self) -> FakePage:
        return self.page


class RuntimeLocatorHandoffTest(unittest.TestCase):
    def capture(self, *, content_type: str, body: bytes, registered_locator: str, capture_locator: str, emit_response_event: bool):
        runner = import_runner()
        item = {
            "capture_intent_id": "intent-1",
            "source_id": "SRC-SEMI-MICRON-Q2FY25-REMARKS-2025-03-20",
            "source_version_id": "SV-SEMI-B026-001",
            "source_locator": registered_locator,
            "content_type_hint": content_type,
        }
        page = FakePage(
            emit_response_event=emit_response_event,
            content_type=content_type,
            body=body,
        )
        context = FakeContext(page)
        output = io.StringIO()

        with tempfile.TemporaryDirectory() as temporary_directory:
            capture_path = Path(temporary_directory) / "capture.bin"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            with contextlib.redirect_stdout(output), patch("builtins.print", wraps=print) as print_spy:
                receipt = runner.capture_one(
                    context=context,
                    browser_channel="fake",
                    item=item,
                    capture_path=capture_path,
                    sidecar_path=sidecar_path,
                    capture_locator=capture_locator,
                    redirect_policy="exact",
                    challenge_wait_seconds=0,
                    navigation_timeout_seconds=12,
                )
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            saved_body = capture_path.read_bytes()

        self.assertTrue(page.closed)
        self.assertEqual(saved_body, body)
        self.assertEqual(receipt["artifact_sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(receipt["registered_source_locator"], registered_locator)
        self.assertEqual(receipt["capture_locator"], capture_locator)
        self.assertEqual(sidecar["source_locator"], capture_locator)
        self.assertIsNotNone(page.response)
        self.assertEqual(page.response.body_calls, 1)
        return page, output.getvalue(), print_spy

    def test_pdf_navigation_response_and_flushed_markers(self) -> None:
        registered_locator = "https://investors.micron.com/static-files/stale-prepared-remarks.pdf"
        capture_locator = (
            "https://s25.q4cdn.com/621799436/files/doc_financials/2025/q2/"
            "Micron_FY25_Q2_Prepared_Remarks_2-1.pdf"
        )
        body = b"%PDF-1.7\n" + b"offline fake PDF body\n" * 100
        page, output, print_spy = self.capture(
            content_type="application/pdf",
            body=body,
            registered_locator=registered_locator,
            capture_locator=capture_locator,
            emit_response_event=False,
        )

        self.assertEqual(page.goto_calls, [(capture_locator, "load", 12_000)])
        self.assertEqual(page.response.url, capture_locator)
        expected_markers = (
            "PDF_NAV_BEGIN",
            "PDF_NAV_COMPLETE",
            "PDF_BODY_BEGIN",
            "PDF_BODY_COMPLETE",
            "PDF_VALIDATION_BEGIN",
            "PDF_VALIDATION_COMPLETE",
        )
        marker_calls = [
            call for call in print_spy.call_args_list
            if call.args and str(call.args[0]).startswith("PDF_")
        ]
        self.assertEqual(
            tuple(str(call.args[0]).split()[0] for call in marker_calls),
            expected_markers,
        )
        for call in marker_calls:
            self.assertIn("SRC-SEMI-MICRON-Q2FY25-REMARKS-2025-03-20", call.args[0])
            self.assertIn(capture_locator, call.args[0])
            self.assertIs(call.kwargs.get("flush"), True)
        marker_positions = [output.index(marker) for marker in expected_markers]
        self.assertEqual(marker_positions, sorted(marker_positions))

    def test_html_path_keeps_commit_navigation_without_pdf_markers(self) -> None:
        locator = "https://example.com/report.html"
        body = b"<!doctype html><html><body>" + b"safe " * 120 + b"</body></html>"
        page, output, _ = self.capture(
            content_type="text/html",
            body=body,
            registered_locator=locator,
            capture_locator=locator,
            emit_response_event=True,
        )

        self.assertEqual(page.goto_calls, [(locator, "commit", 12_000)])
        self.assertNotIn("PDF_", output)


if __name__ == "__main__":
    unittest.main()
