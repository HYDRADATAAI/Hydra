from __future__ import annotations

import base64
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
SPEC = importlib.util.spec_from_file_location("batch030_tsmc_response_stage_runner", RUNNER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to import shared Batch030 browser engine")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

AUTHORIZED = (
    "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17",
    "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20",
    "SRC-SEMI-B022-TSMC-2025-ANNUAL-EQUIPMENT-RISK",
    "SRC-SEMI-B022-TSMC-Q2-2026-TRANSCRIPT-2026-07-16",
)


class FakeRequest:
    def __init__(self, url: str, frame: object, redirected_from: "FakeRequest | None" = None) -> None:
        self.url = url
        self.frame = frame
        self.redirected_from = redirected_from

    def is_navigation_request(self) -> bool:
        return True


class FakeResponse:
    def __init__(
        self,
        *,
        status: int,
        url: str,
        body: bytes,
        content_type: str,
        frame: object | None = None,
        redirected_from_url: str | None = None,
        content_length: int | None = None,
    ) -> None:
        self.status = status
        self.url = url
        response_frame = frame if frame is not None else object()
        prior = FakeRequest(redirected_from_url, response_frame) if redirected_from_url else None
        self.request = FakeRequest(url, response_frame, prior)
        self._body = body
        self._headers = {
            "content-type": content_type,
            "content-length": str(content_length if content_length is not None else len(body)),
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


class FakeCDPSession:
    def __init__(self, page: "FakePage") -> None:
        self.page = page
        self.handler: Any | None = None
        self.fetch_enabled = False
        self.detached = False

    def on(self, event: str, callback: Any) -> None:
        if event == "Fetch.requestPaused":
            self.handler = callback

    def send(self, method: str, _params: dict[str, Any] | None = None) -> dict[str, Any]:
        if method == "Fetch.enable":
            self.fetch_enabled = True
        elif method == "Fetch.disable":
            self.fetch_enabled = False
        elif method == "Fetch.getResponseBody":
            return {
                "body": base64.b64encode(self.page.response_stage_body).decode("ascii"),
                "base64Encoded": True,
            }
        return {}

    def detach(self) -> None:
        self.detached = True
        self.fetch_enabled = False


class FakePage:
    def __init__(self, response: FakeResponse) -> None:
        self.main_frame = object()
        response.request.frame = self.main_frame
        self.response = response
        self.response_stage_body = response._body
        self.response_callback: Any | None = None
        self.cdp_session: FakeCDPSession | None = None
        self.goto_calls: list[tuple[str, str, int]] = []
        self.closed = False

    def route(self, _pattern: str, _handler: Any) -> None:
        pass

    def on(self, event: str, callback: Any) -> None:
        if event == "response":
            self.response_callback = callback

    def goto(self, url: str, *, wait_until: str, timeout: int) -> FakeResponse:
        self.goto_calls.append((url, wait_until, timeout))
        if self.response_callback is not None:
            self.response_callback(self.response)
        if self.cdp_session is not None and self.cdp_session.fetch_enabled:
            if self.cdp_session.handler is None:
                raise AssertionError("CDP Fetch handler missing")
            self.cdp_session.handler(
                {
                    "requestId": "fake-request",
                    "request": {"url": url},
                    "responseStatusCode": self.response.status,
                    "responseHeaders": [
                        {"name": name, "value": value}
                        for name, value in self.response.headers.items()
                    ],
                }
            )
        return self.response

    def wait_for_timeout(self, _milliseconds: int) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self, *, api_responses: list[FakeResponse], browser_response: FakeResponse) -> None:
        self.request = FakeRequestContext(api_responses)
        self.page = FakePage(browser_response)

    def new_page(self) -> FakePage:
        return self.page

    def new_cdp_session(self, page: FakePage) -> FakeCDPSession:
        session = FakeCDPSession(page)
        page.cdp_session = session
        return session


def valid_pdf(tag: bytes = b"x") -> bytes:
    return b"%PDF-1.7\n" + (tag * 4096)


class TSMC403ResponseStageTests(unittest.TestCase):
    locator = (
        "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/"
        "2023-07/7ec677062ca442e429b632ccd6d4f31ad53b1ce7/TSMC%202Q23%20Transcript.pdf"
    )
    source_id = "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20"

    def item(self, source_id: str | None = None) -> dict[str, str]:
        return {
            "capture_intent_id": "CAP-SEMI-B030-010",
            "source_id": source_id or self.source_id,
            "source_version_id": "SV-SEMI-B030-010",
            "source_locator": self.locator,
            "inbox_filename": "source.pdf",
            "content_type_hint": "application/pdf",
        }

    def capture(
        self,
        *,
        source_id: str,
        api_response: FakeResponse,
        browser_response: FakeResponse,
        response_stage_body: bytes | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], FakeContext, bytes]:
        context = FakeContext(api_responses=[api_response], browser_response=browser_response)
        if response_stage_body is not None:
            context.page.response_stage_body = response_stage_body
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            capture_path = Path(td) / "source.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            result = runner.capture_one(
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
            captured = capture_path.read_bytes()
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        return result, sidecar, context, captured

    def test_exact_four_source_allowlist(self) -> None:
        self.assertEqual(tuple(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS), AUTHORIZED)

    def test_tsmc_raw_403_uses_validated_response_stage_pdf(self) -> None:
        pdf = valid_pdf(b"a")
        api = FakeResponse(
            status=403,
            url=self.locator,
            body=b"forbidden",
            content_type="text/html",
        )
        viewer_shell = b"<!doctype html><html><body>Chromium PDF viewer</body></html>"
        browser = FakeResponse(
            status=200,
            url=self.locator,
            body=viewer_shell,
            content_type="application/pdf",
            content_length=len(pdf),
        )
        result, sidecar, context, captured = self.capture(
            source_id=self.source_id,
            api_response=api,
            browser_response=browser,
            response_stage_body=pdf,
        )

        self.assertEqual(captured, pdf)
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["capture_transport"], "BROWSER_NAVIGATION_RESPONSE_FALLBACK")
        self.assertEqual(result["prior_failed_acquisition_attempt"]["http_status"], 403)
        self.assertFalse(result["prior_failed_acquisition_attempt"]["accepted"])
        evidence = result["browser_response_stage_evidence"]["validated_navigation_response"]
        self.assertEqual(evidence["transport"], "CHROMIUM_FETCH_RESPONSE_STAGE")
        self.assertTrue(evidence["signature_hex"].startswith(b"%PDF-".hex()))
        self.assertEqual(sidecar["source_locator"], self.locator)
        self.assertEqual(api.body_calls, 0)
        self.assertTrue(api.disposed)
        self.assertEqual(browser.body_calls, 0)
        self.assertEqual(len(context.page.goto_calls), 2)
        self.assertTrue(context.page.cdp_session is not None and context.page.cdp_session.detached)

    def test_non_allowlisted_403_remains_fail_closed(self) -> None:
        api = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
        browser = FakeResponse(
            status=200,
            url=self.locator,
            body=valid_pdf(b"b"),
            content_type="application/pdf",
        )
        context = FakeContext(api_responses=[api], browser_response=browser)
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(runner.CaptureError, "HTTP status 403 is not acceptable"):
                runner.capture_one(
                    context=context,
                    browser_channel="chrome",
                    item=self.item("SRC-SEMI-USGS-MCS-SILICON-2024-01-31"),
                    capture_path=Path(td) / "source.pdf",
                    sidecar_path=Path(td) / "source.pdf.capture.json",
                    capture_locator=self.locator,
                    redirect_policy="exact",
                    challenge_wait_seconds=0,
                    navigation_timeout_seconds=5,
                )
        self.assertEqual(browser.body_calls, 0)
        self.assertIsNone(context.page.cdp_session)
        self.assertTrue(api.disposed)

    def test_tsmc_fallback_browser_non_200_fails_closed(self) -> None:
        api = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
        browser = FakeResponse(status=403, url=self.locator, body=b"denied", content_type="text/html")
        context = FakeContext(api_responses=[api], browser_response=browser)
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(runner.CaptureError, "authorized browser fallback requires HTTP 200"):
                runner.capture_one(
                    context=context,
                    browser_channel="chrome",
                    item=self.item(),
                    capture_path=Path(td) / "source.pdf",
                    sidecar_path=Path(td) / "source.pdf.capture.json",
                    capture_locator=self.locator,
                    redirect_policy="exact",
                    challenge_wait_seconds=0,
                    navigation_timeout_seconds=5,
                )
        self.assertTrue(api.disposed)
        self.assertIsNone(context.page.cdp_session)

    def test_invalid_response_stage_body_fails_closed(self) -> None:
        api = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
        stage_body = b"<!doctype html><html><body>not a PDF</body></html>" * 40
        browser = FakeResponse(
            status=200,
            url=self.locator,
            body=b"viewer shell",
            content_type="application/pdf",
            content_length=len(stage_body),
        )
        context = FakeContext(api_responses=[api], browser_response=browser)
        context.page.response_stage_body = stage_body
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(runner.CaptureError, "invalid or suspiciously small PDF body"):
                runner.capture_one(
                    context=context,
                    browser_channel="chrome",
                    item=self.item(),
                    capture_path=Path(td) / "source.pdf",
                    sidecar_path=Path(td) / "source.pdf.capture.json",
                    capture_locator=self.locator,
                    redirect_policy="exact",
                    challenge_wait_seconds=0,
                    navigation_timeout_seconds=5,
                )
        self.assertTrue(api.disposed)
        self.assertEqual(browser.body_calls, 0)


if __name__ == "__main__":
    unittest.main()
