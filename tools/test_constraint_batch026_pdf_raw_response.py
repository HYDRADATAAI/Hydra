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
SPEC = importlib.util.spec_from_file_location("batch026_pdf_raw_response_runner", RUNNER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to import Batch026 capture runner")
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
        self.disposed = False

    def body(self) -> bytes:
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


class FakeNavigationResponse:
    status = 200

    def __init__(self) -> None:
        self.body_calls = 0

    def body(self) -> bytes:
        self.body_calls += 1
        raise AssertionError("Chromium PDF viewer body must not be used as the captured PDF")


class FakePage:
    def __init__(self, navigation_response: FakeNavigationResponse) -> None:
        self.main_frame = object()
        self.navigation_response = navigation_response
        self.closed = False

    def on(self, _event: str, _callback: Any) -> None:
        return None

    def goto(self, _url: str, **_kwargs: Any) -> FakeNavigationResponse:
        return self.navigation_response

    def wait_for_timeout(self, _milliseconds: int) -> None:
        raise AssertionError("successful raw PDF response should not wait for another browser response")

    def close(self) -> None:
        self.closed = True


class FakeCaptureContext:
    def __init__(self, request: FakeRequestContext, page: FakePage) -> None:
        self.request = request
        self.page = page

    def new_page(self) -> FakePage:
        return self.page


class RawPDFResponseTests(unittest.TestCase):
    locator = "https://cdn.example.test/reports/source.pdf"

    def pdf_response(self, *, url: str | None = None) -> FakeAPIResponse:
        body = b"%PDF-1.7\n" + (b"x" * 2048)
        return FakeAPIResponse(
            status=200,
            url=url or self.locator,
            headers={
                "Content-Type": "application/pdf",
                "Content-Length": str(len(body)),
            },
            body=body,
        )

    def test_raw_pdf_fetch_is_bounded_and_disables_automatic_redirects(self) -> None:
        response = self.pdf_response()
        request = FakeRequestContext([response])
        context = FakeCaptureContext(request, FakePage(FakeNavigationResponse()))

        fetched, chain = runner.fetch_pdf_response(
            context=context,
            exact_locator=self.locator,
            policy="exact",
            timeout_milliseconds=90_000,
        )

        self.assertIs(fetched, response)
        self.assertEqual(chain, (self.locator,))
        self.assertEqual(request.calls[0]["url"], self.locator)
        self.assertGreater(request.calls[0]["timeout"], 0)
        self.assertLessEqual(request.calls[0]["timeout"], 90_000)
        self.assertEqual(request.calls[0]["max_redirects"], 0)
        self.assertEqual(request.calls[0]["max_retries"], 0)
        self.assertFalse(request.calls[0]["fail_on_status_code"])

    def test_same_origin_redirects_are_followed_manually_and_bounded(self) -> None:
        final_url = "https://cdn.example.test/reports/final.pdf"
        redirect = FakeAPIResponse(
            status=302,
            url=self.locator,
            headers={"Location": "/reports/final.pdf"},
        )
        final = self.pdf_response(url=final_url)
        request = FakeRequestContext([redirect, final])
        context = FakeCaptureContext(request, FakePage(FakeNavigationResponse()))

        response, chain = runner.fetch_pdf_response(
            context=context,
            exact_locator=self.locator,
            policy="same-origin",
            timeout_milliseconds=5_000,
        )

        self.assertIs(response, final)
        self.assertEqual(chain, (self.locator, final_url))
        self.assertEqual([call["url"] for call in request.calls], [self.locator, final_url])
        self.assertTrue(redirect.disposed)
        self.assertEqual(request.calls[0]["max_redirects"], 0)

    def test_exact_policy_rejects_redirect_without_following_it(self) -> None:
        redirect = FakeAPIResponse(
            status=302,
            url=self.locator,
            headers={"Location": "/other.pdf"},
        )
        request = FakeRequestContext([redirect])
        context = FakeCaptureContext(request, FakePage(FakeNavigationResponse()))

        with self.assertRaisesRegex(runner.CaptureError, "exact redirect policy rejected"):
            runner.fetch_pdf_response(
                context=context,
                exact_locator=self.locator,
                policy="exact",
                timeout_milliseconds=5_000,
            )

        self.assertTrue(redirect.disposed)
        self.assertEqual(len(request.calls), 1)

    def test_same_origin_policy_rejects_cross_origin_redirect(self) -> None:
        redirect = FakeAPIResponse(
            status=302,
            url=self.locator,
            headers={"Location": "https://elsewhere.example.test/file.pdf"},
        )
        request = FakeRequestContext([redirect])
        context = FakeCaptureContext(request, FakePage(FakeNavigationResponse()))

        with self.assertRaisesRegex(runner.CaptureError, "host change"):
            runner.fetch_pdf_response(
                context=context,
                exact_locator=self.locator,
                policy="same-origin",
                timeout_milliseconds=5_000,
            )

        self.assertTrue(redirect.disposed)
        self.assertEqual(len(request.calls), 1)

    def test_pdf_capture_uses_raw_api_bytes_not_chromium_viewer_body(self) -> None:
        raw_response = self.pdf_response()
        browser_response = FakeNavigationResponse()
        context = FakeCaptureContext(
            FakeRequestContext([raw_response]),
            FakePage(browser_response),
        )
        item = {
            "capture_intent_id": "intent-001",
            "source_id": "SRC-PDF-TEST",
            "source_version_id": "version-001",
            "source_locator": self.locator,
            "inbox_filename": "source.pdf",
            "content_type_hint": "application/pdf",
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            capture_path = Path(temporary_directory) / "source.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            with contextlib.redirect_stdout(io.StringIO()):
                result = runner.capture_one(
                    context=context,
                    browser_channel="chrome",
                    item=item,
                    capture_path=capture_path,
                    sidecar_path=sidecar_path,
                    capture_locator=self.locator,
                    redirect_policy="exact",
                    challenge_wait_seconds=0,
                    navigation_timeout_seconds=90,
                )

            expected_body = raw_response._body
            self.assertEqual(capture_path.read_bytes(), expected_body)
            self.assertEqual(result["byte_length"], len(expected_body))
            self.assertEqual(result["http_status"], 200)
            self.assertEqual(result["redirect_chain"], [self.locator])
            self.assertEqual(result["final_response_url"], self.locator)
            self.assertEqual(
                json.loads(sidecar_path.read_text(encoding="utf-8"))["content_type"],
                "application/pdf",
            )
            self.assertEqual(browser_response.body_calls, 0)
            self.assertTrue(raw_response.disposed)


if __name__ == "__main__":
    unittest.main()
