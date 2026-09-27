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


class FakeNavigationRequest:
    def __init__(self, url: str, redirected_from: "FakeNavigationRequest | None" = None) -> None:
        self.url = url
        self.redirected_from = redirected_from


class FakeNavigationResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        url: str = "https://cdn.example.test/reports/source.pdf",
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        redirected_from: FakeNavigationRequest | None = None,
    ) -> None:
        self.status = status
        self.url = url
        self.headers = {
            key.lower(): value
            for key, value in (
                headers
                or {
                    "Content-Type": "application/pdf",
                    "Content-Length": str(len(body or b"")),
                }
            ).items()
        }
        self.request = FakeNavigationRequest(url, redirected_from)
        self._body = body
        self.body_calls = 0

    def body(self) -> bytes:
        self.body_calls += 1
        if self._body is None:
            raise AssertionError("Chromium PDF viewer body must not be used as the captured PDF")
        return self._body


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
    authorized_fallback_source_ids = {
        "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17",
        "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20",
        "SRC-SEMI-B022-TSMC-2025-ANNUAL-EQUIPMENT-RISK",
        "SRC-SEMI-B022-TSMC-Q2-2026-TRANSCRIPT-2026-07-16",
    }

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

    def forbidden_response(self) -> FakeAPIResponse:
        return FakeAPIResponse(
            status=403,
            url=self.locator,
            headers={"Content-Type": "text/html", "Content-Length": "6"},
            body=b"denied",
        )

    def capture_item(self, source_id: str) -> dict[str, str]:
        return {
            "capture_intent_id": "intent-001",
            "source_id": source_id,
            "source_version_id": "version-001",
            "source_locator": self.locator,
            "inbox_filename": "source.pdf",
            "content_type_hint": "application/pdf",
        }

    def run_capture(
        self,
        *,
        source_id: str,
        api_response: FakeAPIResponse,
        browser_response: FakeNavigationResponse,
        capture_path: Path,
        sidecar_path: Path,
    ) -> dict[str, Any]:
        return runner.capture_one(
            context=FakeCaptureContext(
                FakeRequestContext([api_response]),
                FakePage(browser_response),
            ),
            browser_channel="chrome",
            item=self.capture_item(source_id),
            capture_path=capture_path,
            sidecar_path=sidecar_path,
            capture_locator=self.locator,
            redirect_policy="exact",
            challenge_wait_seconds=0,
            navigation_timeout_seconds=90,
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
        item = self.capture_item("SRC-PDF-TEST")

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

    def test_authorized_tsmc_403_uses_validated_browser_200_and_records_original_attempt(self) -> None:
        api_response = self.forbidden_response()
        body = b"%PDF-1.7\n" + (b"validated browser response\n" * 100)
        browser_response = FakeNavigationResponse(
            url=self.locator,
            headers={"Content-Type": "application/pdf", "Content-Length": str(len(body))},
            body=body,
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            capture_path = Path(temporary_directory) / "source.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            with contextlib.redirect_stdout(io.StringIO()):
                result = self.run_capture(
                    source_id=next(iter(sorted(self.authorized_fallback_source_ids))),
                    api_response=api_response,
                    browser_response=browser_response,
                    capture_path=capture_path,
                    sidecar_path=sidecar_path,
                )

            self.assertEqual(capture_path.read_bytes(), body)
            self.assertEqual(result["http_status"], 200)
            self.assertEqual(result["capture_locator"], self.locator)
            self.assertEqual(result["redirect_chain"], [self.locator])
            self.assertEqual(
                result["prior_failed_acquisition_attempt"],
                {
                    "transport": "PLAYWRIGHT_API_REQUEST",
                    "http_status": 403,
                    "final_response_url": self.locator,
                    "redirect_chain": [self.locator],
                    "accepted": False,
                    "reason": "HTTP_403_AUTHORIZED_TSMC_BROWSER_NAVIGATION_FALLBACK",
                },
            )
            self.assertEqual(
                json.loads(sidecar_path.read_text(encoding="utf-8"))["source_id"],
                result["source_id"],
            )
            self.assertTrue(api_response.disposed)
            self.assertEqual(browser_response.body_calls, 1)

    def test_invalid_browser_fallback_redirect_mime_and_content_fail_closed(self) -> None:
        valid_pdf = b"%PDF-1.7\n" + (b"valid-looking body\n" * 100)
        cases = (
            (
                "redirect",
                FakeNavigationResponse(
                    url="https://elsewhere.example.test/reports/source.pdf",
                    headers={"Content-Type": "application/pdf", "Content-Length": str(len(valid_pdf))},
                    body=valid_pdf,
                    redirected_from=FakeNavigationRequest(self.locator),
                ),
                "exact redirect policy rejected",
            ),
            (
                "mime",
                FakeNavigationResponse(
                    url=self.locator,
                    headers={"Content-Type": "text/html", "Content-Length": str(len(valid_pdf))},
                    body=valid_pdf,
                ),
                "expected PDF content type",
            ),
            (
                "content",
                FakeNavigationResponse(
                    url=self.locator,
                    headers={"Content-Type": "application/pdf", "Content-Length": "2048"},
                    body=b"<html>" + (b"not a PDF " * 300),
                ),
                "invalid or suspiciously small PDF body",
            ),
        )
        for case_name, browser_response, expected_error in cases:
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as temporary_directory:
                api_response = self.forbidden_response()
                capture_path = Path(temporary_directory) / "source.pdf"
                sidecar_path = Path(str(capture_path) + ".capture.json")
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(runner.CaptureError, expected_error) as raised:
                        self.run_capture(
                            source_id=next(iter(sorted(self.authorized_fallback_source_ids))),
                            api_response=api_response,
                            browser_response=browser_response,
                            capture_path=capture_path,
                            sidecar_path=sidecar_path,
                        )
                self.assertIn("prior raw API request returned HTTP 403", str(raised.exception))
                self.assertFalse(capture_path.exists())
                self.assertFalse(sidecar_path.exists())
                self.assertTrue(api_response.disposed)
                self.assertEqual(browser_response.body_calls, 0 if case_name == "redirect" else 1)

    def test_unauthorized_source_cannot_use_browser_200_fallback(self) -> None:
        api_response = self.forbidden_response()
        body = b"%PDF-1.7\n" + (b"valid PDF body\n" * 100)
        browser_response = FakeNavigationResponse(
            url=self.locator,
            headers={"Content-Type": "application/pdf", "Content-Length": str(len(body))},
            body=body,
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            capture_path = Path(temporary_directory) / "source.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(runner.CaptureError, "HTTP status 403"):
                    self.run_capture(
                        source_id="SRC-PDF-NOT-AUTHORIZED",
                        api_response=api_response,
                        browser_response=browser_response,
                        capture_path=capture_path,
                        sidecar_path=sidecar_path,
                    )
            self.assertFalse(capture_path.exists())
            self.assertFalse(sidecar_path.exists())
            self.assertTrue(api_response.disposed)
            self.assertEqual(browser_response.body_calls, 0)

    def test_fallback_allowlist_is_exactly_four_and_excludes_prohibited_micron_set(self) -> None:
        self.assertEqual(set(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS), self.authorized_fallback_source_ids)
        self.assertEqual(len(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS), 4)
        self.assertEqual(len(runner.OPERATOR_BLOCKED_SOURCE_IDS), 9)
        self.assertEqual(
            set(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS)
            & set(runner.OPERATOR_BLOCKED_SOURCE_IDS),
            set(),
        )
        queue = runner.validate_queue(runner.load_json(ROOT / runner.QUEUE_RELATIVE_PATH))
        blocked, eligible = runner.partition_capture_queue(queue)
        eligible_by_id = {item["source_id"]: item for item in eligible}
        self.assertEqual(
            set(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS),
            set(eligible_by_id) & self.authorized_fallback_source_ids,
        )
        self.assertEqual(
            {item["source_id"] for item in blocked},
            set(runner.OPERATOR_BLOCKED_SOURCE_IDS),
        )
        self.assertTrue(
            all(
                eligible_by_id[source_id]["content_type_hint"] == "application/pdf"
                for source_id in runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS
            )
        )

    def test_navigation_non_200_after_authorized_403_fails_closed(self) -> None:
        api_response = self.forbidden_response()
        browser_response = FakeNavigationResponse(status=403, url=self.locator, body=b"denied")

        with tempfile.TemporaryDirectory() as temporary_directory:
            capture_path = Path(temporary_directory) / "source.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(runner.CaptureError, "authorized browser fallback requires HTTP 200"):
                    self.run_capture(
                        source_id=next(iter(sorted(self.authorized_fallback_source_ids))),
                        api_response=api_response,
                        browser_response=browser_response,
                        capture_path=capture_path,
                        sidecar_path=sidecar_path,
                    )
            self.assertFalse(capture_path.exists())
            self.assertFalse(sidecar_path.exists())
            self.assertTrue(api_response.disposed)
            self.assertEqual(browser_response.body_calls, 0)


if __name__ == "__main__":
    unittest.main()
