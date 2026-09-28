from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py"
SPEC = importlib.util.spec_from_file_location("batch030_tsmc_browser_403_runner", RUNNER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to import Batch026 capture runner")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

AUTHORIZED = {
    "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17",
    "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20",
    "SRC-SEMI-B022-TSMC-2025-ANNUAL-EQUIPMENT-RISK",
    "SRC-SEMI-B022-TSMC-Q2-2026-TRANSCRIPT-2026-07-16",
}


class FakeRequest:
    def __init__(self, url: str, redirected_from: "FakeRequest | None" = None) -> None:
        self.url = url
        self.redirected_from = redirected_from
        self._frame = None

    def is_navigation_request(self) -> bool:
        return True

    @property
    def frame(self) -> Any:
        return self._frame


class FakeResponse:
    def __init__(
        self,
        *,
        status: int,
        url: str,
        body: bytes,
        content_type: str,
        redirected_from_url: str | None = None,
    ) -> None:
        prior = FakeRequest(redirected_from_url) if redirected_from_url else None
        self.request = FakeRequest(url, prior)
        self.status = status
        self.url = url
        self._body = body
        self._headers = {
            "content-type": content_type,
            "content-length": str(len(body)),
        }
        self.body_calls = 0
        self.disposed = False

    @property
    def headers(self) -> dict[str, str]:
        return dict(self._headers)

    def body(self) -> bytes:
        self.body_calls += 1
        return self._body

    def header_value(self, name: str) -> str | None:
        return self._headers.get(name.lower())

    def dispose(self) -> None:
        self.disposed = True


class FakeRequestContext:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected API request")
        return self.responses.pop(0)


class FakePage:
    def __init__(self, response: FakeResponse) -> None:
        self.main_frame = object()
        self.response = response
        self.goto_calls: list[tuple[str, str, int]] = []
        self.closed = False
        self._response_callback: Any | None = None
        response.request._frame = self.main_frame

    def on(self, event: str, callback: Any) -> None:
        if event == "response":
            self._response_callback = callback

    def goto(self, url: str, *, wait_until: str, timeout: int) -> FakeResponse:
        self.goto_calls.append((url, wait_until, timeout))
        if self._response_callback is not None:
            self._response_callback(self.response)
        return self.response

    def wait_for_timeout(self, _milliseconds: int) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self, *, api_response: FakeResponse, navigation_response: FakeResponse) -> None:
        self.request = FakeRequestContext([api_response])
        self.page = FakePage(navigation_response)

    def new_page(self) -> FakePage:
        return self.page


def valid_pdf(tag: bytes = b"x") -> bytes:
    return b"%PDF-1.7\n" + (tag * 2048)


class Batch030TSMC403FallbackTests(unittest.TestCase):
    locator = (
        "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/"
        "2023-07/7ec677062ca442e429b632ccd6d4f31ad53b1ce7/TSMC%202Q23%20Transcript.pdf"
    )

    def item(self, source_id: str) -> dict[str, Any]:
        return {
            "capture_intent_id": "CAP-TEST",
            "source_id": source_id,
            "source_version_id": "SV-TEST",
            "source_locator": self.locator,
            "inbox_filename": "test.pdf",
            "content_type_hint": "application/pdf",
        }

    def capture(
        self,
        *,
        source_id: str,
        api: FakeResponse,
        browser: FakeResponse,
        policy: str = "exact",
    ) -> tuple[dict[str, Any], dict[str, Any], FakeContext, bytes]:
        context = FakeContext(api_response=api, navigation_response=browser)
        with tempfile.TemporaryDirectory() as td:
            capture_path = Path(td) / "test.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            with contextlib.redirect_stdout(io.StringIO()):
                result = runner.capture_one(
                    context=context,
                    browser_channel="chrome",
                    item=self.item(source_id),
                    capture_path=capture_path,
                    sidecar_path=sidecar_path,
                    capture_locator=self.locator,
                    redirect_policy=policy,
                    challenge_wait_seconds=0,
                    navigation_timeout_seconds=5,
                )
            body = capture_path.read_bytes()
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            return result, sidecar, context, body

    def test_qualifying_tsmc_403_reuses_valid_browser_200_and_preserves_403_evidence(self) -> None:
        source_id = "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20"
        api = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
        pdf = valid_pdf(b"a")
        browser = FakeResponse(status=200, url=self.locator, body=pdf, content_type="application/pdf")
        result, sidecar, context, body = self.capture(source_id=source_id, api=api, browser=browser)

        self.assertEqual(body, pdf)
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["capture_transport"], "BROWSER_NAVIGATION_RESPONSE_FALLBACK")
        self.assertEqual(result["prior_failed_acquisition_attempt"]["http_status"], 403)
        self.assertFalse(result["prior_failed_acquisition_attempt"]["accepted"])
        self.assertEqual(
            result["browser_response_stage_evidence"]["transport"],
            "PLAYWRIGHT_BROWSER_NAVIGATION_RESPONSE",
        )
        self.assertEqual(result["browser_response_stage_evidence"]["http_status"], 200)
        self.assertEqual(result["redirect_chain"], [self.locator])
        self.assertEqual(result["final_response_url"], self.locator)
        self.assertEqual(sidecar["content_type"], "application/pdf")
        self.assertEqual(api.body_calls, 0)
        self.assertEqual(browser.body_calls, 1)
        self.assertEqual(len(context.request.calls), 1)
        self.assertEqual(len(context.page.goto_calls), 1)
        self.assertTrue(api.disposed)

    def test_invalid_redirect_mime_and_content_fail_closed(self) -> None:
        source_id = "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20"
        cases = [
            (
                FakeResponse(
                    status=200,
                    url="https://other.example/tsmc.pdf",
                    body=valid_pdf(b"r"),
                    content_type="application/pdf",
                    redirected_from_url=self.locator,
                ),
                "exact redirect policy rejected",
            ),
            (
                FakeResponse(
                    status=200,
                    url=self.locator,
                    body=valid_pdf(b"m"),
                    content_type="text/html",
                ),
                "expected PDF content type",
            ),
            (
                FakeResponse(
                    status=200,
                    url=self.locator,
                    body=b"not-pdf" * 400,
                    content_type="application/pdf",
                ),
                "invalid or suspiciously small PDF body",
            ),
        ]
        for browser, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as td:
                api = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
                context = FakeContext(api_response=api, navigation_response=browser)
                capture_path = Path(td) / "test.pdf"
                sidecar_path = Path(str(capture_path) + ".capture.json")
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(runner.CaptureError, expected):
                        runner.capture_one(
                            context=context,
                            browser_channel="chrome",
                            item=self.item(source_id),
                            capture_path=capture_path,
                            sidecar_path=sidecar_path,
                            capture_locator=self.locator,
                            redirect_policy="exact",
                            challenge_wait_seconds=0,
                            navigation_timeout_seconds=5,
                        )
                self.assertFalse(capture_path.exists())
                self.assertFalse(sidecar_path.exists())
                self.assertTrue(api.disposed)

    def test_non_authorized_source_cannot_enter_fallback(self) -> None:
        api = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
        browser = FakeResponse(status=200, url=self.locator, body=valid_pdf(b"u"), content_type="application/pdf")
        with tempfile.TemporaryDirectory() as td:
            capture_path = Path(td) / "test.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(runner.CaptureError, "HTTP status 403 is not acceptable"):
                    runner.capture_one(
                        context=FakeContext(api_response=api, navigation_response=browser),
                        browser_channel="chrome",
                        item=self.item("SRC-SEMI-USGS-MCS-SILICON-2024-01-31"),
                        capture_path=capture_path,
                        sidecar_path=sidecar_path,
                        capture_locator=self.locator,
                        redirect_policy="exact",
                        challenge_wait_seconds=0,
                        navigation_timeout_seconds=5,
                    )
            self.assertFalse(capture_path.exists())
            self.assertFalse(sidecar_path.exists())
            self.assertEqual(browser.body_calls, 0)

    def test_authorized_set_is_exact_four_and_prohibited_micron_set_is_disjoint_untouched(self) -> None:
        self.assertEqual(set(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS), AUTHORIZED)
        self.assertEqual(len(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS), 4)
        self.assertEqual(len(runner.OPERATOR_BLOCKED_SOURCE_IDS), 9)
        self.assertEqual(set(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS) & set(runner.OPERATOR_BLOCKED_SOURCE_IDS), set())
        queue = runner.validate_queue(runner.load_json(ROOT / runner.QUEUE_RELATIVE_PATH))
        blocked, eligible = runner.partition_capture_queue(queue)
        self.assertEqual({x["source_id"] for x in blocked}, set(runner.OPERATOR_BLOCKED_SOURCE_IDS))
        self.assertTrue(AUTHORIZED.issubset({x["source_id"] for x in eligible}))

    def test_ordinary_api_200_behavior_is_unchanged(self) -> None:
        source_id = "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20"
        api_pdf = valid_pdf(b"o")
        api = FakeResponse(status=200, url=self.locator, body=api_pdf, content_type="application/pdf")
        browser = FakeResponse(status=200, url=self.locator, body=valid_pdf(b"n"), content_type="application/pdf")
        result, sidecar, context, body = self.capture(source_id=source_id, api=api, browser=browser)

        self.assertEqual(body, api_pdf)
        self.assertNotIn("capture_transport", result)
        self.assertNotIn("prior_failed_acquisition_attempt", result)
        self.assertNotIn("capture_transport", sidecar)
        self.assertEqual(api.body_calls, 1)
        self.assertEqual(browser.body_calls, 0)
        self.assertEqual(len(context.page.goto_calls), 1)
        self.assertTrue(api.disposed)

    def test_browser_non_200_after_authorized_403_fails_closed(self) -> None:
        source_id = "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20"
        api = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
        browser = FakeResponse(status=403, url=self.locator, body=b"denied", content_type="text/html")
        with tempfile.TemporaryDirectory() as td:
            capture_path = Path(td) / "test.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(runner.CaptureError, "authorized browser fallback requires HTTP 200"):
                    runner.capture_one(
                        context=FakeContext(api_response=api, navigation_response=browser),
                        browser_channel="chrome",
                        item=self.item(source_id),
                        capture_path=capture_path,
                        sidecar_path=sidecar_path,
                        capture_locator=self.locator,
                        redirect_policy="exact",
                        challenge_wait_seconds=0,
                        navigation_timeout_seconds=5,
                    )
            self.assertFalse(capture_path.exists())
            self.assertFalse(sidecar_path.exists())
            self.assertEqual(browser.body_calls, 0)


if __name__ == "__main__":
    unittest.main()
