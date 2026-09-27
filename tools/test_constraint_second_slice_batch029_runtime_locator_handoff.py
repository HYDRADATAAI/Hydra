#!/usr/bin/env python3
"""Offline regression test for the Batch029 capture-locator handoff."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

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

    def __init__(self, url: str, frame: object, body: bytes) -> None:
        self.url = url
        self.request = FakeRequest(url, frame)
        self._body = body

    def body(self) -> bytes:
        return self._body

    def header_value(self, name: str) -> str | None:
        return "application/pdf" if name.lower() == "content-type" else None


class FakePage:
    def __init__(self) -> None:
        self.main_frame = object()
        self.response_handler: Any = None
        self.navigated_to: list[str] = []
        self.closed = False

    def on(self, event: str, handler: Any) -> None:
        if event != "response":
            raise AssertionError(f"unexpected event subscription: {event}")
        self.response_handler = handler

    def goto(self, locator: str, **_kwargs: Any) -> None:
        self.navigated_to.append(locator)
        body = b"%PDF-1.7\n" + b"offline fake PDF body\n" * 100
        self.response_handler(FakeResponse(locator, self.main_frame, body))

    def wait_for_timeout(self, _milliseconds: int) -> None:
        raise AssertionError("the fake response should be processed without waiting")

    def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self) -> None:
        self.page = FakePage()

    def new_page(self) -> FakePage:
        return self.page


class RuntimeLocatorHandoffTest(unittest.TestCase):
    def test_remediated_locator_is_used_for_navigation_receipt_and_sidecar(self) -> None:
        runner = import_runner()
        registered_locator = "https://investors.micron.com/static-files/stale-prepared-remarks.pdf"
        capture_locator = (
            "https://s25.q4cdn.com/621799436/files/doc_financials/2025/q4/"
            "Prepared-Remarks.pdf"
        )
        item = {
            "capture_intent_id": "intent-1",
            "source_id": "micron-quarterly-prepared-remarks",
            "source_version_id": "source-version-1",
            "source_locator": registered_locator,
            "content_type_hint": "application/pdf",
        }
        context = FakeContext()

        with tempfile.TemporaryDirectory() as temporary_directory:
            capture_path = Path(temporary_directory) / "capture.pdf"
            sidecar_path = Path(temporary_directory) / "capture.pdf.capture.json"
            receipt = runner.capture_one(
                context=context,
                browser_channel="fake",
                item=item,
                capture_path=capture_path,
                sidecar_path=sidecar_path,
                capture_locator=capture_locator,
                redirect_policy="exact",
                challenge_wait_seconds=0,
                navigation_timeout_seconds=1,
            )

            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))

        self.assertEqual(context.page.navigated_to, [capture_locator])
        self.assertEqual(receipt["registered_source_locator"], registered_locator)
        self.assertEqual(receipt["capture_locator"], capture_locator)
        self.assertEqual(sidecar["source_locator"], capture_locator)
        self.assertTrue(context.page.closed)


if __name__ == "__main__":
    unittest.main()
