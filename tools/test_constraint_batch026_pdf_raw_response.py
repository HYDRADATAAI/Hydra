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
        self.headers = {key.lower(): value for key, value in (headers or {}).items()}
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
    tsmc_pdf = b"%PDF-1.7\n" + (b"x" * 2048)

    def authorized_tsmc_item(self, source_id: str) -> tuple[dict[str, str], str]:
        source_version_id, locator = runner.B030_AUTHORIZED_TSMC_BROWSER_FALLBACKS[source_id]
        return (
            {
                "capture_intent_id": f"intent-{source_version_id}",
                "source_id": source_id,
                "source_version_id": source_version_id,
                "source_locator": locator,
                "inbox_filename": f"{source_version_id}.pdf",
                "content_type_hint": "application/pdf",
            },
            locator,
        )

    def capture_with_responses(
        self,
        *,
        item: dict[str, str],
        locator: str,
        api_response: FakeAPIResponse,
        navigation_response: FakeNavigationResponse,
        redirect_policy: str = "exact",
    ) -> dict[str, Any]:
        context = FakeCaptureContext(
            FakeRequestContext([api_response]),
            FakePage(navigation_response),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            capture_path = Path(temporary_directory) / "capture.pdf"
            sidecar_path = Path(str(capture_path) + ".capture.json")
            output = io.StringIO()
            try:
                with contextlib.redirect_stdout(output):
                    receipt = runner.capture_one(
                        context=context,
                        browser_channel="chrome",
                        item=item,
                        capture_path=capture_path,
                        sidecar_path=sidecar_path,
                        capture_locator=locator,
                        redirect_policy=redirect_policy,
                        challenge_wait_seconds=0,
                        navigation_timeout_seconds=90,
                    )
                error = None
            except runner.CaptureError as exc:
                receipt = None
                error = str(exc)

            return {
                "receipt": receipt,
                "error": error,
                "capture_exists": capture_path.exists(),
                "sidecar_exists": sidecar_path.exists(),
                "body": capture_path.read_bytes() if capture_path.exists() else None,
                "sidecar": (
                    json.loads(sidecar_path.read_text(encoding="utf-8"))
                    if sidecar_path.exists()
                    else None
                ),
                "output": output.getvalue(),
                "api_response": api_response,
                "navigation_response": navigation_response,
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

    def test_authorized_tsmc_403_uses_validated_browser_200_for_all_four_exact_identities(self) -> None:
        for source_id, (_version_id, locator) in runner.B030_AUTHORIZED_TSMC_BROWSER_FALLBACKS.items():
            with self.subTest(source_id=source_id):
                item, item_locator = self.authorized_tsmc_item(source_id)
                self.assertEqual(item_locator, locator)
                raw_response = FakeAPIResponse(
                    status=403,
                    url=locator,
                    headers={"Content-Type": "text/html", "Content-Length": "24"},
                    body=b"access denied by API",
                )
                browser_response = FakeNavigationResponse(
                    status=200,
                    url=locator,
                    headers={
                        "Content-Type": "application/pdf",
                        "Content-Length": str(len(self.tsmc_pdf)),
                    },
                    body=self.tsmc_pdf,
                )

                result = self.capture_with_responses(
                    item=item,
                    locator=locator,
                    api_response=raw_response,
                    navigation_response=browser_response,
                )

                self.assertIsNone(result["error"])
                self.assertEqual(result["body"], self.tsmc_pdf)
                self.assertEqual(result["receipt"]["http_status"], 200)
                self.assertEqual(result["receipt"]["status"], "CAPTURED")
                self.assertEqual(
                    result["receipt"]["transport_provenance"]["primary_attempt"]["http_status"],
                    403,
                )
                self.assertEqual(
                    result["receipt"]["transport_provenance"]["primary_attempt"]["response_url"],
                    locator,
                )
                self.assertEqual(
                    result["receipt"]["transport_provenance"]["primary_attempt"]["redirect_chain"],
                    [locator],
                )
                self.assertEqual(
                    result["receipt"]["transport_provenance"]["primary_attempt"]["content_type"],
                    "text/html",
                )
                self.assertEqual(
                    result["receipt"]["transport_provenance"]["primary_attempt"]["content_length"],
                    "24",
                )
                self.assertEqual(
                    result["receipt"]["transport_provenance"]["accepted_response"]["http_status"],
                    200,
                )
                self.assertEqual(result["sidecar"]["schema_version"], runner.SIDECAR_SCHEMA)
                self.assertEqual(result["sidecar"]["source_id"], source_id)
                self.assertEqual(browser_response.body_calls, 1)
                self.assertTrue(raw_response.disposed)

    def test_authorized_tsmc_fallback_rejects_bad_navigation_redirect(self) -> None:
        source_id = "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17"
        item, locator = self.authorized_tsmc_item(source_id)
        raw_response = FakeAPIResponse(status=403, url=locator)
        redirected_from = FakeNavigationRequest(locator)
        browser_response = FakeNavigationResponse(
            status=200,
            url="https://elsewhere.example.test/transcript.pdf",
            headers={"Content-Type": "application/pdf"},
            body=self.tsmc_pdf,
            redirected_from=redirected_from,
        )

        result = self.capture_with_responses(
            item=item,
            locator=locator,
            api_response=raw_response,
            navigation_response=browser_response,
        )

        self.assertIn("exact redirect policy rejected", result["error"])
        self.assertIn("HTTP 403", result["error"])
        self.assertFalse(result["capture_exists"])
        self.assertFalse(result["sidecar_exists"])
        self.assertTrue(raw_response.disposed)

    def test_authorized_tsmc_fallback_rejects_wrong_mime(self) -> None:
        source_id = "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17"
        item, locator = self.authorized_tsmc_item(source_id)
        raw_response = FakeAPIResponse(status=403, url=locator)
        browser_response = FakeNavigationResponse(
            status=200,
            url=locator,
            headers={"Content-Type": "text/html"},
            body=b"<!doctype html><html><body>" + (b"challenge " * 100),
        )

        result = self.capture_with_responses(
            item=item,
            locator=locator,
            api_response=raw_response,
            navigation_response=browser_response,
        )

        self.assertIn("expected PDF content type", result["error"])
        self.assertIn("HTTP 403", result["error"])
        self.assertFalse(result["capture_exists"])
        self.assertFalse(result["sidecar_exists"])

    def test_authorized_tsmc_fallback_rejects_invalid_pdf_content(self) -> None:
        source_id = "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17"
        item, locator = self.authorized_tsmc_item(source_id)
        raw_response = FakeAPIResponse(status=403, url=locator)
        browser_response = FakeNavigationResponse(
            status=200,
            url=locator,
            headers={"Content-Type": "application/pdf"},
            body=b"%PDF-1.7\n" + (b"x" * 400),
        )

        result = self.capture_with_responses(
            item=item,
            locator=locator,
            api_response=raw_response,
            navigation_response=browser_response,
        )

        self.assertIn("invalid or suspiciously small PDF body", result["error"])
        self.assertIn("HTTP 403", result["error"])
        self.assertFalse(result["capture_exists"])
        self.assertFalse(result["sidecar_exists"])

    def test_authorized_source_with_mismatched_locator_cannot_fallback(self) -> None:
        source_id = "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17"
        item, locator = self.authorized_tsmc_item(source_id)
        item["source_locator"] = locator + "?unregistered=1"
        raw_response = FakeAPIResponse(status=403, url=locator)
        browser_response = FakeNavigationResponse(
            status=200,
            url=locator,
            headers={"Content-Type": "application/pdf"},
            body=self.tsmc_pdf,
        )

        result = self.capture_with_responses(
            item=item,
            locator=locator,
            api_response=raw_response,
            navigation_response=browser_response,
        )

        self.assertIn("HTTP status 403 is not acceptable", result["error"])
        self.assertFalse(result["capture_exists"])
        self.assertFalse(result["sidecar_exists"])
        self.assertEqual(browser_response.body_calls, 0)

    def test_unauthorized_source_cannot_use_browser_200_after_api_403(self) -> None:
        locator = next(iter(runner.B030_AUTHORIZED_TSMC_BROWSER_FALLBACKS.values()))[1]
        item = {
            "capture_intent_id": "unauthorized-intent",
            "source_id": "SRC-SEMI-TSMC-NOT-AUTHORIZED",
            "source_version_id": "SV-SEMI-NOT-AUTHORIZED",
            "source_locator": locator,
            "inbox_filename": "unauthorized.pdf",
            "content_type_hint": "application/pdf",
        }
        raw_response = FakeAPIResponse(status=403, url=locator)
        browser_response = FakeNavigationResponse(
            status=200,
            url=locator,
            headers={"Content-Type": "application/pdf"},
            body=self.tsmc_pdf,
        )

        result = self.capture_with_responses(
            item=item,
            locator=locator,
            api_response=raw_response,
            navigation_response=browser_response,
        )

        self.assertIn("HTTP status 403 is not acceptable", result["error"])
        self.assertFalse(result["capture_exists"])
        self.assertFalse(result["sidecar_exists"])
        self.assertEqual(browser_response.body_calls, 0)

    def test_authorized_source_with_non_200_navigation_stays_fail_closed(self) -> None:
        source_id = "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17"
        item, locator = self.authorized_tsmc_item(source_id)
        raw_response = FakeAPIResponse(status=403, url=locator)
        browser_response = FakeNavigationResponse(
            status=403,
            url=locator,
            headers={"Content-Type": "application/pdf"},
            body=self.tsmc_pdf,
        )

        result = self.capture_with_responses(
            item=item,
            locator=locator,
            api_response=raw_response,
            navigation_response=browser_response,
        )

        self.assertIn("requires HTTP 200 navigation response, observed 403", result["error"])
        self.assertIn("HTTP 403", result["error"])
        self.assertFalse(result["capture_exists"])
        self.assertFalse(result["sidecar_exists"])
        self.assertEqual(browser_response.body_calls, 0)

    def test_authorized_tsmc_non_403_api_failure_cannot_use_browser_fallback(self) -> None:
        source_id = "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17"
        item, locator = self.authorized_tsmc_item(source_id)
        raw_response = FakeAPIResponse(status=500, url=locator)
        browser_response = FakeNavigationResponse(
            status=200,
            url=locator,
            headers={"Content-Type": "application/pdf"},
            body=self.tsmc_pdf,
        )

        result = self.capture_with_responses(
            item=item,
            locator=locator,
            api_response=raw_response,
            navigation_response=browser_response,
        )

        self.assertIn("HTTP status 500 is not acceptable", result["error"])
        self.assertFalse(result["capture_exists"])
        self.assertFalse(result["sidecar_exists"])
        self.assertEqual(browser_response.body_calls, 0)
        self.assertTrue(raw_response.disposed)

    def test_fallback_allowlist_remains_disjoint_from_all_nine_blocked_micron_sources(self) -> None:
        queue = runner.validate_queue(runner.load_json(ROOT / runner.QUEUE_RELATIVE_PATH))
        blocked, eligible = runner.partition_capture_queue(queue)
        blocked_ids = {str(item["source_id"]) for item in blocked}
        eligible_ids = {str(item["source_id"]) for item in eligible}

        self.assertEqual(len(blocked_ids), 9)
        self.assertEqual(blocked_ids, set(runner.OPERATOR_BLOCKED_SOURCE_IDS))
        self.assertEqual(len(eligible_ids), 32)
        self.assertTrue(blocked_ids.isdisjoint(runner.B030_AUTHORIZED_TSMC_BROWSER_FALLBACKS))
        self.assertTrue(set(runner.B030_AUTHORIZED_TSMC_BROWSER_FALLBACKS).issubset(eligible_ids))


if __name__ == "__main__":
    unittest.main()
