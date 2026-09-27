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
QUEUE = ROOT / (
    "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/"
    "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
)

SPEC = importlib.util.spec_from_file_location("batch030_tsmc_403_fallback_runner", RUNNER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to import Batch026/B030 capture runner")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

EXPECTED_TSMC_FALLBACK_IDS = (
    "SRC-SEMI-TSMC-Q1-2025-TRANSCRIPT-2025-04-17",
    "SRC-SEMI-B020-TSMC-Q2-2023-TRANSCRIPT-2023-07-20",
    "SRC-SEMI-B022-TSMC-2025-ANNUAL-EQUIPMENT-RISK",
    "SRC-SEMI-B022-TSMC-Q2-2026-TRANSCRIPT-2026-07-16",
)

EXPECTED_BLOCKED_MICRON_IDS = (
    "SRC-SEMI-MICRON-Q2FY25-REMARKS-2025-03-20",
    "SRC-SEMI-B021-MICRON-Q1FY26-REMARKS-2025-12-17",
    "SRC-SEMI-B021-MICRON-Q3FY24-REMARKS-2024-06-26",
    "SRC-SEMI-B021-MICRON-Q3FY25-REMARKS-2025-06-25",
    "SRC-SEMI-B021-MICRON-Q4FY25-REMARKS-2025-09-23",
    "SRC-SEMI-B022-GLOBENEWSWIRE-MICRON-HBM3E-2024-02-26",
    "SRC-SEMI-B022-MICRON-HBM3E-VOLUME-2024-02-26",
    "SRC-SEMI-B023-MICRON-Q1FY24-REMARKS-2023-12-20",
    "SRC-SEMI-B023-MICRON-Q2FY26-MARKET-OUTLOOK-2026-03-18",
)


class FakeRequest:
    def __init__(self, url: str, redirected_from: "FakeRequest | None" = None) -> None:
        self.url = url
        self.redirected_from = redirected_from


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
        self.status = status
        self.url = url
        prior = FakeRequest(redirected_from_url) if redirected_from_url else None
        self.request = FakeRequest(url, prior)
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

    def on(self, _event: str, _callback: Any) -> None:
        return None

    def goto(self, url: str, *, wait_until: str, timeout: int) -> FakeResponse:
        self.goto_calls.append((url, wait_until, timeout))
        return self.response

    def wait_for_timeout(self, _milliseconds: int) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self, *, api_responses: list[FakeResponse], navigation_response: FakeResponse) -> None:
        self.request = FakeRequestContext(api_responses)
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

    def run_capture(
        self,
        *,
        source_id: str,
        api_response: FakeResponse,
        browser_response: FakeResponse,
        policy: str = "exact",
    ) -> tuple[dict[str, Any], dict[str, Any], FakeContext]:
        context = FakeContext(
            api_responses=[api_response],
            navigation_response=browser_response,
        )
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
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual(capture_path.read_bytes(), browser_response._body if result.get("capture_transport") else api_response._body)
            return result, sidecar, context

    def test_authorized_tsmc_403_uses_validated_browser_200_and_preserves_failed_attempt(self) -> None:
        source_id = EXPECTED_TSMC_FALLBACK_IDS[1]
        api = FakeResponse(
            status=403,
            url=self.locator,
            body=b"forbidden",
            content_type="text/html",
        )
        browser = FakeResponse(
            status=200,
            url=self.locator,
            body=valid_pdf(b"a"),
            content_type="application/pdf",
        )
        result, sidecar, context = self.run_capture(
            source_id=source_id,
            api_response=api,
            browser_response=browser,
        )

        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["capture_transport"], "BROWSER_NAVIGATION_RESPONSE_FALLBACK")
        self.assertEqual(result["prior_failed_acquisition_attempt"]["http_status"], 403)
        self.assertFalse(result["prior_failed_acquisition_attempt"]["accepted"])
        self.assertEqual(
            sidecar["capture_transport"],
            "BROWSER_NAVIGATION_RESPONSE_FALLBACK",
        )
        self.assertEqual(sidecar["prior_failed_acquisition_attempt"]["http_status"], 403)
        self.assertEqual(api.body_calls, 0)
        self.assertEqual(browser.body_calls, 1)
        self.assertTrue(api.disposed)
        self.assertEqual(len(context.request.calls), 1)

    def test_invalid_redirect_content_or_mime_remains_fail_closed(self) -> None:
        source_id = EXPECTED_TSMC_FALLBACK_IDS[1]
        cases = [
            (
                "redirect",
                FakeResponse(
                    status=200,
                    url="https://elsewhere.example/tsmc.pdf",
                    body=valid_pdf(b"r"),
                    content_type="application/pdf",
                    redirected_from_url=self.locator,
                ),
                "exact redirect policy rejected",
            ),
            (
                "mime",
                FakeResponse(
                    status=200,
                    url=self.locator,
                    body=valid_pdf(b"m"),
                    content_type="text/html",
                ),
                "expected PDF content type",
            ),
            (
                "content",
                FakeResponse(
                    status=200,
                    url=self.locator,
                    body=b"not-a-pdf" * 200,
                    content_type="application/pdf",
                ),
                "invalid or suspiciously small PDF body",
            ),
        ]
        for name, browser, expected in cases:
            with self.subTest(name=name):
                api = FakeResponse(
                    status=403,
                    url=self.locator,
                    body=b"forbidden",
                    content_type="text/html",
                )
                context = FakeContext(api_responses=[api], navigation_response=browser)
                with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(runner.CaptureError, expected):
                        runner.capture_one(
                            context=context,
                            browser_channel="chrome",
                            item=self.item(source_id),
                            capture_path=Path(td) / "test.pdf",
                            sidecar_path=Path(td) / "test.pdf.capture.json",
                            capture_locator=self.locator,
                            redirect_policy="exact",
                            challenge_wait_seconds=0,
                            navigation_timeout_seconds=5,
                        )
                self.assertTrue(api.disposed)

    def test_non_authorized_source_cannot_enter_fallback(self) -> None:
        source_id = "SRC-SEMI-USGS-MCS-SILICON-2024-01-31"
        api = FakeResponse(
            status=403,
            url=self.locator,
            body=b"forbidden" * 300,
            content_type="application/pdf",
        )
        browser = FakeResponse(
            status=200,
            url=self.locator,
            body=valid_pdf(b"b"),
            content_type="application/pdf",
        )
        context = FakeContext(api_responses=[api], navigation_response=browser)
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(runner.CaptureError, "HTTP status 403 is not acceptable"):
                runner.capture_one(
                    context=context,
                    browser_channel="chrome",
                    item=self.item(source_id),
                    capture_path=Path(td) / "test.pdf",
                    sidecar_path=Path(td) / "test.pdf.capture.json",
                    capture_locator=self.locator,
                    redirect_policy="exact",
                    challenge_wait_seconds=0,
                    navigation_timeout_seconds=5,
                )
        self.assertEqual(api.body_calls, 1)
        self.assertEqual(browser.body_calls, 0)
        self.assertTrue(api.disposed)

    def test_prohibited_micron_set_remains_untouched_and_disjoint(self) -> None:
        queue_doc = json.loads(QUEUE.read_text(encoding="utf-8"))
        queue = runner.validate_queue(queue_doc)
        self.assertEqual(tuple(runner.OPERATOR_BLOCKED_SOURCE_IDS), EXPECTED_BLOCKED_MICRON_IDS)
        self.assertEqual(tuple(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS), EXPECTED_TSMC_FALLBACK_IDS)
        self.assertTrue(
            set(runner.OPERATOR_BLOCKED_SOURCE_IDS).isdisjoint(
                runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS
            )
        )
        blocked, eligible = runner.partition_capture_queue(
            queue,
            runner.OPERATOR_BLOCKED_SOURCE_IDS,
        )
        self.assertEqual(len(blocked), 9)
        self.assertEqual(len(eligible), 32)
        eligible_ids = {item["source_id"] for item in eligible}
        self.assertEqual(
            set(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS),
            set(EXPECTED_TSMC_FALLBACK_IDS),
        )
        self.assertTrue(set(EXPECTED_TSMC_FALLBACK_IDS).issubset(eligible_ids))

    def test_ordinary_api_200_behavior_is_unchanged(self) -> None:
        source_id = EXPECTED_TSMC_FALLBACK_IDS[1]
        api = FakeResponse(
            status=200,
            url=self.locator,
            body=valid_pdf(b"o"),
            content_type="application/pdf",
        )
        browser = FakeResponse(
            status=200,
            url=self.locator,
            body=valid_pdf(b"n"),
            content_type="application/pdf",
        )
        result, sidecar, _context = self.run_capture(
            source_id=source_id,
            api_response=api,
            browser_response=browser,
        )

        self.assertEqual(result["http_status"], 200)
        self.assertNotIn("capture_transport", result)
        self.assertNotIn("prior_failed_acquisition_attempt", result)
        self.assertNotIn("capture_transport", sidecar)
        self.assertNotIn("prior_failed_acquisition_attempt", sidecar)
        self.assertEqual(api.body_calls, 1)
        self.assertEqual(browser.body_calls, 0)
        self.assertTrue(api.disposed)


if __name__ == "__main__":
    unittest.main()
