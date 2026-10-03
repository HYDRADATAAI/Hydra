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
SPEC = importlib.util.spec_from_file_location("batch030_pdf_raw_response_runner", RUNNER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to import Batch026 browser engine")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class FakeAPIResponse:
    def __init__(
        self,
        *,
        status: int,
        url: str,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> None:
        self.status = status
        self.url = url
        self.headers = {key.lower(): value for key, value in (headers or {}).items()}
        self._body = body
        self.body_calls = 0
        self.disposed = False

    def body(self) -> bytes:
        self.body_calls += 1
        return self._body

    def dispose(self) -> None:
        self.disposed = True


class FakeRequestContext:
    def __init__(self, responses: list[FakeAPIResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeAPIResponse:
        self.calls.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected raw HTTP request")
        return self.responses.pop(0)


class FakeNavigationRequest:
    def __init__(self, url: str, frame: object, redirected_from: "FakeNavigationRequest | None" = None) -> None:
        self.url = url
        self.frame = frame
        self.redirected_from = redirected_from

    def is_navigation_request(self) -> bool:
        return True


class FakeNavigationResponse:
    def __init__(
        self,
        *,
        url: str,
        frame: object,
        body: bytes,
        content_type: str,
        status: int = 200,
    ) -> None:
        self.status = status
        self.url = url
        self.request = FakeNavigationRequest(url, frame)
        self._body = body
        self._headers = {
            "content-type": content_type,
            "content-length": str(len(body)),
        }
        self.body_calls = 0

    def body(self) -> bytes:
        self.body_calls += 1
        return self._body

    def header_value(self, name: str) -> str | None:
        return self._headers.get(name.lower())


class FakePage:
    def __init__(self, locator: str, body: bytes, content_type: str) -> None:
        self.main_frame = object()
        self.response = FakeNavigationResponse(
            url=locator,
            frame=self.main_frame,
            body=body,
            content_type=content_type,
        )
        self._response_callback: Any | None = None
        self.closed = False

    def on(self, event: str, callback: Any) -> None:
        if event == "response":
            self._response_callback = callback

    def goto(self, _url: str, **_kwargs: Any) -> FakeNavigationResponse:
        if self._response_callback is not None:
            self._response_callback(self.response)
        return self.response

    def wait_for_timeout(self, _milliseconds: int) -> None:
        raise AssertionError("successful capture should not wait after processing the response")

    def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self, request: FakeRequestContext, page: FakePage) -> None:
        self.request = request
        self.page = page

    def new_page(self) -> FakePage:
        return self.page


class Batch030RawPDFTests(unittest.TestCase):
    locator = "https://public-inspection.federalregister.gov/2024-28270.pdf"
    source_id = "SRC-SEMI-B020-BIS-FDP-HBM-SME-IFR-2024-12-02"

    def item(self, content_type: str = "application/pdf") -> dict[str, str]:
        return {
            "capture_intent_id": "CAP-SEMI-B030-005",
            "source_id": self.source_id,
            "source_version_id": "SV-SEMI-B030-005",
            "source_locator": self.locator,
            "inbox_filename": "source.pdf",
            "content_type_hint": content_type,
        }

    def valid_pdf(self) -> bytes:
        return b"%PDF-1.7\n" + (b"federal-register-pdf-bytes\n" * 100)

    def test_federal_register_536_byte_browser_stub_uses_raw_pdf_bytes(self) -> None:
        browser_stub = b"%PDF-1.7\n" + (b"x" * (536 - len(b"%PDF-1.7\n")))
        raw_body = self.valid_pdf()
        raw_response = FakeAPIResponse(
            status=200,
            url=self.locator,
            headers={
                "Content-Type": "application/pdf",
                "Content-Length": str(len(raw_body)),
            },
            body=raw_body,
        )
        request = FakeRequestContext([raw_response])
        page = FakePage(self.locator, browser_stub, "application/pdf")
        context = FakeContext(request, page)

        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            capture_path = Path(td) / "source.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            result = runner.capture_one(
                context=context,
                browser_channel="chrome",
                item=self.item(),
                capture_path=capture_path,
                sidecar_path=sidecar_path,
                capture_locator=self.locator,
                redirect_policy="exact",
                challenge_wait_seconds=0,
                navigation_timeout_seconds=90,
            )
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))

            self.assertEqual(capture_path.read_bytes(), raw_body)
            self.assertEqual(result["byte_length"], len(raw_body))
            self.assertEqual(result["http_status"], 200)
            self.assertEqual(result["redirect_chain"], [self.locator])
            self.assertEqual(sidecar["source_locator"], self.locator)

        self.assertEqual(page.response.body_calls, 0)
        self.assertEqual(raw_response.body_calls, 1)
        self.assertTrue(raw_response.disposed)
        self.assertEqual(request.calls[0]["url"], self.locator)
        self.assertEqual(request.calls[0]["max_redirects"], 0)
        self.assertEqual(request.calls[0]["max_retries"], 0)
        self.assertFalse(request.calls[0]["fail_on_status_code"])

    def test_exact_policy_rejects_raw_pdf_redirect(self) -> None:
        redirect = FakeAPIResponse(
            status=302,
            url=self.locator,
            headers={"Location": "/2024-28270-final.pdf"},
        )
        context = type("Context", (), {"request": FakeRequestContext([redirect])})()
        with self.assertRaisesRegex(runner.CaptureError, "exact redirect policy rejected"):
            runner.fetch_pdf_response(
                context=context,
                exact_locator=self.locator,
                policy="exact",
                timeout_milliseconds=5000,
            )
        self.assertTrue(redirect.disposed)

    def test_same_origin_policy_follows_bounded_relative_redirect(self) -> None:
        final_url = "https://public-inspection.federalregister.gov/2024-28270-final.pdf"
        redirect = FakeAPIResponse(
            status=302,
            url=self.locator,
            headers={"Location": "/2024-28270-final.pdf"},
        )
        final = FakeAPIResponse(
            status=200,
            url=final_url,
            headers={"Content-Type": "application/pdf"},
            body=self.valid_pdf(),
        )
        request = FakeRequestContext([redirect, final])
        context = type("Context", (), {"request": request})()
        response, chain = runner.fetch_pdf_response(
            context=context,
            exact_locator=self.locator,
            policy="same-origin",
            timeout_milliseconds=5000,
        )
        self.assertIs(response, final)
        self.assertEqual(chain, (self.locator, final_url))
        self.assertEqual([call["url"] for call in request.calls], [self.locator, final_url])
        self.assertTrue(redirect.disposed)

    def test_invalid_raw_pdf_remains_fail_closed(self) -> None:
        browser_stub = b"%PDF-1.7\n" + (b"x" * 526)
        invalid_raw = FakeAPIResponse(
            status=200,
            url=self.locator,
            headers={"Content-Type": "application/pdf", "Content-Length": "536"},
            body=browser_stub,
        )
        request = FakeRequestContext([invalid_raw])
        page = FakePage(self.locator, browser_stub, "application/pdf")
        context = FakeContext(request, page)

        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            capture_path = Path(td) / "source.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            with self.assertRaisesRegex(runner.CaptureError, "invalid or suspiciously small PDF body"):
                runner.capture_one(
                    context=context,
                    browser_channel="chrome",
                    item=self.item(),
                    capture_path=capture_path,
                    sidecar_path=sidecar_path,
                    capture_locator=self.locator,
                    redirect_policy="exact",
                    challenge_wait_seconds=0,
                    navigation_timeout_seconds=90,
                )
            self.assertFalse(capture_path.exists())
            self.assertFalse(sidecar_path.exists())
        self.assertTrue(invalid_raw.disposed)

    def test_html_capture_does_not_use_raw_pdf_transport(self) -> None:
        html = b"<!doctype html><html><body>" + (b"safe " * 120) + b"</body></html>"
        request = FakeRequestContext([])
        page = FakePage("https://example.test/source.html", html, "text/html")
        context = FakeContext(request, page)
        item = self.item(content_type="text/html")
        item["source_locator"] = "https://example.test/source.html"

        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            result = runner.capture_one(
                context=context,
                browser_channel="chrome",
                item=item,
                capture_path=Path(td) / "source.html",
                sidecar_path=Path(td) / "source.html.capture.json",
                capture_locator=item["source_locator"],
                redirect_policy="exact",
                challenge_wait_seconds=0,
                navigation_timeout_seconds=90,
            )
        self.assertEqual(result["content_type"], "text/html")
        self.assertEqual(request.calls, [])
        self.assertEqual(page.response.body_calls, 1)


if __name__ == "__main__":
    unittest.main()
