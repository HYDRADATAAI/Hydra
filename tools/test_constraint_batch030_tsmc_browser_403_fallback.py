# B030 regression policy: fallback is limited to the four explicitly authorized TSMC PDF source IDs.
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
MATERIALIZER = ROOT / "tools/materialize_constraint_second_slice_batch026_private_t1.py"
QUEUE = ROOT / (
    "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/"
    "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
)

SPEC = importlib.util.spec_from_file_location("batch030_tsmc_403_fallback_runner", RUNNER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to import Batch026/B030 capture runner")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
MATERIALIZER_SPEC = importlib.util.spec_from_file_location(
    "batch030_tsmc_t1_materializer", MATERIALIZER
)
if MATERIALIZER_SPEC is None or MATERIALIZER_SPEC.loader is None:
    raise RuntimeError("unable to import Batch026 private T1 materializer")
materializer = importlib.util.module_from_spec(MATERIALIZER_SPEC)
MATERIALIZER_SPEC.loader.exec_module(materializer)

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
        content_length: int | None = None,
        content_disposition: str | None = None,
    ) -> None:
        self.status = status
        self.url = url
        prior = FakeRequest(redirected_from_url) if redirected_from_url else None
        self.request = FakeRequest(url, prior)
        self._body = body
        self._headers = {
            "content-type": content_type,
            "content-length": str(content_length if content_length is not None else len(body)),
        }
        if content_disposition is not None:
            self._headers["content-disposition"] = content_disposition
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

    def send(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
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
        self.response = response
        self.response_stage_body = response._body
        self.goto_calls: list[tuple[str, str, int]] = []
        self.closed = False
        self.cdp_session: FakeCDPSession | None = None

    def route(self, _pattern: str, _handler: Any) -> None:
        pass

    def on(self, _event: str, _callback: Any) -> None:
        return None

    def goto(self, url: str, *, wait_until: str, timeout: int) -> FakeResponse:
        self.goto_calls.append((url, wait_until, timeout))
        if self.cdp_session is not None and self.cdp_session.fetch_enabled:
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
    def __init__(self, *, api_responses: list[FakeResponse], navigation_response: FakeResponse) -> None:
        self.request = FakeRequestContext(api_responses)
        self.page = FakePage(navigation_response)

    def new_page(self) -> FakePage:
        return self.page

    def new_cdp_session(self, page: FakePage) -> FakeCDPSession:
        session = FakeCDPSession(page)
        page.cdp_session = session
        return session


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
        browser_response_stage_body: bytes | None = None,
        policy: str = "exact",
    ) -> tuple[dict[str, Any], dict[str, Any], FakeContext]:
        context = FakeContext(
            api_responses=[api_response],
            navigation_response=browser_response,
        )
        if browser_response_stage_body is not None:
            context.page.response_stage_body = browser_response_stage_body
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
            expected_body = (
                context.page.response_stage_body
                if result.get("capture_transport")
                else api_response._body
            )
            self.assertEqual(capture_path.read_bytes(), expected_body)
            resumed = runner.validate_existing_pair(
                item=self.item(source_id),
                capture_path=capture_path,
                sidecar_path=sidecar_path,
                remediation=None,
            )
            self.assertIsNotNone(resumed)
            return result, sidecar, context

    def test_403_fallback_uses_validated_response_stage_pdf_not_the_348_byte_viewer_shell(self) -> None:
        source_id = EXPECTED_TSMC_FALLBACK_IDS[1]
        pdf = valid_pdf(b"a")
        viewer_shell = b"<!doctype html><html><body>Chromium PDF viewer bootstrap</body></html>"
        api = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
        browser = FakeResponse(
            status=200,
            url=self.locator,
            body=viewer_shell,
            content_type="application/pdf",
            content_length=len(pdf),
        )
        result, sidecar, context = self.run_capture(
            source_id=source_id,
            api_response=api,
            browser_response=browser,
            browser_response_stage_body=pdf,
        )

        self.assertEqual(result["source_id"], source_id)
        self.assertEqual(sidecar["source_id"], source_id)
        self.assertEqual(result["capture_locator"], self.locator)
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["capture_transport"], "BROWSER_NAVIGATION_RESPONSE_FALLBACK")
        self.assertEqual(result["prior_failed_acquisition_attempt"]["http_status"], 403)
        self.assertFalse(result["prior_failed_acquisition_attempt"]["accepted"])
        self.assertEqual(
            result["browser_response_stage_evidence"]["validated_navigation_response"]["transport"],
            "CHROMIUM_FETCH_RESPONSE_STAGE",
        )
        self.assertTrue(
            result["browser_response_stage_evidence"]["validated_navigation_response"]["signature_hex"].startswith(
                b"%PDF-".hex()
            )
        )
        self.assertEqual(
            set(sidecar),
            {
                "schema_version",
                "capture_intent_id",
                "source_id",
                "source_version_id",
                "source_locator",
                "capture_completed_at",
                "content_type",
                "processing_disposition",
                "historical_backdating_authorized",
            },
        )
        self.assertEqual(api.body_calls, 0)
        self.assertEqual(browser.body_calls, 0)
        self.assertEqual(len(context.page.goto_calls), 2)
        self.assertTrue(context.page.cdp_session is not None and context.page.cdp_session.detached)
        self.assertTrue(api.disposed)
        self.assertEqual(len(context.request.calls), 1)

    def test_html_redirect_and_download_trampoline_bodies_fail_closed(self) -> None:
        source_id = EXPECTED_TSMC_FALLBACK_IDS[1]
        html_body = b"<!doctype html><html><body>" + (b"download this document " * 100) + b"</body></html>"
        cases = [
            (
                "redirect",
                FakeResponse(
                    status=200,
                    url="https://unapproved.example/tsmc.pdf",
                    body=valid_pdf(b"r"),
                    content_type="application/pdf",
                    redirected_from_url=self.locator,
                ),
                None,
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
                None,
                "expected PDF content type",
            ),
            (
                "invalid-content",
                FakeResponse(
                    status=200,
                    url=self.locator,
                    body=b"not-a-pdf " * 300,
                    content_type="application/pdf",
                ),
                None,
                "invalid or suspiciously small PDF body",
            ),
            (
                "viewer-shell",
                FakeResponse(
                    status=200,
                    url=self.locator,
                    body=b"<!doctype html><html><body>viewer</body></html>",
                    content_type="application/pdf",
                ),
                b"<!doctype html><html><body>viewer</body></html>",
                "invalid or suspiciously small PDF body",
            ),
            (
                "download-trampoline",
                FakeResponse(
                    status=200,
                    url=self.locator,
                    body=html_body,
                    content_type="application/pdf",
                    content_disposition='attachment; filename="TSMC.pdf"',
                ),
                html_body,
                "invalid or suspiciously small PDF body",
            ),
        ]
        for name, browser, stage_body, expected in cases:
            with self.subTest(name=name):
                api = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
                context = FakeContext(api_responses=[api], navigation_response=browser)
                if stage_body is not None:
                    context.page.response_stage_body = stage_body
                with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
                    capture_path = Path(td) / "test.pdf"
                    sidecar_path = Path(td) / "test.pdf.capture.json"
                    with self.assertRaisesRegex(runner.CaptureError, expected) as raised:
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
                    self.assertIn("prior raw API request returned HTTP 403", str(raised.exception))
                    self.assertFalse(capture_path.exists())
                    self.assertFalse(sidecar_path.exists())
                self.assertTrue(api.disposed)
                self.assertEqual(browser.body_calls, 0)

    def test_non_200_browser_navigation_and_non_authorized_sources_fail_closed(self) -> None:
        api = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
        browser = FakeResponse(status=403, url=self.locator, body=b"denied", content_type="text/html")
        context = FakeContext(api_responses=[api], navigation_response=browser)
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(runner.CaptureError, "requires HTTP 200"):
                runner.capture_one(
                    context=context,
                    browser_channel="chrome",
                    item=self.item(EXPECTED_TSMC_FALLBACK_IDS[1]),
                    capture_path=Path(td) / "test.pdf",
                    sidecar_path=Path(td) / "test.pdf.capture.json",
                    capture_locator=self.locator,
                    redirect_policy="exact",
                    challenge_wait_seconds=0,
                    navigation_timeout_seconds=5,
                )
        self.assertFalse(api.disposed is False)
        self.assertEqual(browser.body_calls, 0)
        self.assertEqual(context.page.goto_calls.__len__(), 1)

        not_authorized = "SRC-SEMI-USGS-MCS-SILICON-2024-01-31"
        api2 = FakeResponse(status=403, url=self.locator, body=b"forbidden", content_type="text/html")
        browser2 = FakeResponse(
            status=200,
            url=self.locator,
            body=valid_pdf(b"b"),
            content_type="application/pdf",
        )
        context2 = FakeContext(api_responses=[api2], navigation_response=browser2)
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(runner.CaptureError, "HTTP status 403 is not acceptable"):
                runner.capture_one(
                    context=context2,
                    browser_channel="chrome",
                    item=self.item(not_authorized),
                    capture_path=Path(td) / "test.pdf",
                    sidecar_path=Path(td) / "test.pdf.capture.json",
                    capture_locator=self.locator,
                    redirect_policy="exact",
                    challenge_wait_seconds=0,
                    navigation_timeout_seconds=5,
                )
        self.assertEqual(api2.body_calls, 1)
        self.assertEqual(browser2.body_calls, 0)
        self.assertIsNone(context2.page.cdp_session)

    def test_exact_four_locator_corrections_preserve_source_identity_and_provenance(self) -> None:
        queue_doc = json.loads(QUEUE.read_text(encoding="utf-8"))
        queue = runner.validate_queue(queue_doc)
        items = {item["source_id"]: item for item in queue}
        self.assertEqual(set(runner.TSMC_LOCATOR_REMEDIATIONS), set(EXPECTED_TSMC_FALLBACK_IDS))
        self.assertEqual(
            set(runner.TSMC_LOCATOR_REMEDIATIONS),
            set(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS),
        )
        for source_id in EXPECTED_TSMC_FALLBACK_IDS:
            remediation = runner.TSMC_LOCATOR_REMEDIATIONS[source_id]
            self.assertEqual(
                runner.resolve_tsmc_effective_locator(item=items[source_id], remediation=remediation),
                remediation["effective_locator"],
            )
            self.assertTrue(remediation["effective_locator"].startswith("https://investor.tsmc.com/"))
            self.assertTrue(remediation["authority_page"].startswith("https://investor.tsmc.com/"))

        q1_id = EXPECTED_TSMC_FALLBACK_IDS[0]
        q1_item = items[q1_id]
        q1_remediation = runner.TSMC_LOCATOR_REMEDIATIONS[q1_id]
        q1_effective = runner.resolve_tsmc_effective_locator(item=q1_item, remediation=q1_remediation)
        pdf = valid_pdf(b"p")
        api = FakeResponse(status=403, url=q1_effective, body=b"forbidden", content_type="text/html")
        viewer_shell = b"<!doctype html><html><body>viewer</body></html>"
        browser = FakeResponse(
            status=200,
            url=q1_effective,
            body=viewer_shell,
            content_type="application/pdf",
            content_length=len(pdf),
        )
        context = FakeContext(api_responses=[api], navigation_response=browser)
        context.page.response_stage_body = pdf
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            capture_path = Path(td) / q1_item["inbox_filename"]
            sidecar_path = Path(str(capture_path) + ".capture.json")
            result = runner.capture_one(
                context=context,
                browser_channel="msedge",
                item=q1_item,
                capture_path=capture_path,
                sidecar_path=sidecar_path,
                capture_locator=q1_effective,
                redirect_policy="exact",
                challenge_wait_seconds=0,
                navigation_timeout_seconds=5,
                locator_remediation=q1_remediation,
            )
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            resumed = runner.validate_existing_pair(
                item=q1_item,
                capture_path=capture_path,
                sidecar_path=sidecar_path,
                remediation=q1_remediation,
            )
            captured_bytes = capture_path.read_bytes()

        self.assertEqual(captured_bytes, pdf)
        self.assertEqual(sidecar["source_locator"], q1_effective)
        self.assertEqual(result["registered_source_locator"], q1_item["source_locator"])
        self.assertEqual(result["capture_locator"], q1_effective)
        self.assertEqual(result["locator_resolution"]["requested_locator"], q1_item["source_locator"])
        self.assertEqual(result["locator_resolution"]["effective_locator"], q1_effective)
        self.assertEqual(result["locator_resolution"]["authority_page"], q1_remediation["authority_page"])
        self.assertEqual(resumed["locator_resolution"]["requested_locator"], q1_item["source_locator"])
        self.assertEqual(resumed["locator_resolution"]["effective_locator"], q1_effective)

    def test_locator_correction_cannot_change_source_identity_or_use_unapproved_endpoint(self) -> None:
        queue_doc = json.loads(QUEUE.read_text(encoding="utf-8"))
        queue = runner.validate_queue(queue_doc)
        item = next(row for row in queue if row["source_id"] == EXPECTED_TSMC_FALLBACK_IDS[0])
        remediation = runner.TSMC_LOCATOR_REMEDIATIONS[item["source_id"]]

        changed_identity = dict(item)
        changed_identity["title"] = "Different TSMC document"
        with self.assertRaisesRegex(runner.CaptureError, "change document identity"):
            runner.resolve_tsmc_effective_locator(item=changed_identity, remediation=remediation)

        changed_date = dict(item)
        changed_date["publication_date"] = "2025-04-18"
        with self.assertRaisesRegex(runner.CaptureError, "change publication date"):
            runner.resolve_tsmc_effective_locator(item=changed_date, remediation=remediation)

        changed_requested = dict(item)
        changed_requested["source_locator"] = "https://investor.tsmc.com/english/unrelated.pdf"
        with self.assertRaisesRegex(runner.CaptureError, "registered TSMC source locator mismatch"):
            runner.resolve_tsmc_effective_locator(item=changed_requested, remediation=remediation)

        cross_domain = dict(remediation)
        cross_domain["effective_locator"] = "https://unapproved.example/tsmc.pdf"
        with self.assertRaisesRegex(runner.CaptureError, "approved official host"):
            runner.resolve_tsmc_effective_locator(item=item, remediation=cross_domain)

        unapproved_same_domain = dict(remediation)
        unapproved_same_domain["effective_locator"] = "https://investor.tsmc.com/other/tsmc.pdf"
        with self.assertRaisesRegex(runner.CaptureError, "exact authorized mapping"):
            runner.resolve_tsmc_effective_locator(item=item, remediation=unapproved_same_domain)

        with self.assertRaisesRegex(runner.CaptureError, "not authorized"):
            runner.resolve_tsmc_effective_locator(
                item={**item, "source_id": "SRC-SEMI-MICRON-PROHIBITED"},
                remediation=remediation,
            )

    def test_prohibited_micron_set_remains_unattempted_and_disjoint(self) -> None:
        queue_doc = json.loads(QUEUE.read_text(encoding="utf-8"))
        queue = runner.validate_queue(queue_doc)
        self.assertEqual(tuple(runner.OPERATOR_BLOCKED_SOURCE_IDS), EXPECTED_BLOCKED_MICRON_IDS)
        self.assertEqual(tuple(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS), EXPECTED_TSMC_FALLBACK_IDS)
        self.assertTrue(
            set(runner.OPERATOR_BLOCKED_SOURCE_IDS).isdisjoint(runner.TSMC_BROWSER_403_FALLBACK_SOURCE_IDS)
        )
        blocked, eligible = runner.partition_capture_queue(queue, runner.OPERATOR_BLOCKED_SOURCE_IDS)
        self.assertEqual(len(blocked), 9)
        self.assertEqual(len(eligible), 32)
        journal_blocked = [
            {"source_id": item["source_id"], "status": runner.BLOCKED_SOURCE_STATUS, "acquisition_attempted": False}
            for item in blocked
        ]
        self.assertEqual({row["source_id"] for row in journal_blocked}, set(EXPECTED_BLOCKED_MICRON_IDS))
        self.assertTrue(all(row["acquisition_attempted"] is False for row in journal_blocked))
        eligible_ids = {item["source_id"] for item in eligible}
        self.assertTrue(set(EXPECTED_TSMC_FALLBACK_IDS).issubset(eligible_ids))

    def test_private_t1_gate_accepts_only_exact_four_tsmc_locator_pairs(self) -> None:
        queue_doc = json.loads(QUEUE.read_text(encoding="utf-8"))
        queue = runner.validate_queue(queue_doc)
        items = {item["source_id"]: item for item in queue}
        self.assertEqual(
            set(materializer.TSMC_EFFECTIVE_LOCATOR_OVERRIDES),
            set(EXPECTED_TSMC_FALLBACK_IDS),
        )
        for source_id in EXPECTED_TSMC_FALLBACK_IDS:
            with self.subTest(source_id=source_id):
                item = items[source_id]
                runtime_remediation = runner.TSMC_LOCATOR_REMEDIATIONS[source_id]
                requested, effective = materializer.TSMC_EFFECTIVE_LOCATOR_OVERRIDES[source_id]
                self.assertEqual(item["source_locator"], requested)
                self.assertEqual(effective, runtime_remediation["effective_locator"])
                self.assertTrue(materializer.locator_allowed(item, requested, None))
                self.assertTrue(materializer.locator_allowed(item, effective, None))
                self.assertFalse(
                    materializer.locator_allowed(item, "https://unapproved.example/tsmc.pdf", None)
                )
                sidecar = {
                    "schema_version": materializer.SIDECAR_SCHEMA,
                    "capture_intent_id": item["capture_intent_id"],
                    "source_id": source_id,
                    "source_version_id": item["source_version_id"],
                    "source_locator": effective,
                    "capture_completed_at": "2026-09-27T22:00:00Z",
                    "content_type": "application/pdf",
                    "processing_disposition": "ELIGIBLE",
                    "historical_backdating_authorized": False,
                }
                self.assertEqual(
                    materializer.validate_sidecar(item, sidecar, None)[2],
                    effective,
                )

        unauthorized = dict(items["SRC-SEMI-USGS-MCS-SILICON-2024-01-31"])
        unauthorized["source_locator"] = materializer.TSMC_EFFECTIVE_LOCATOR_OVERRIDES[
            EXPECTED_TSMC_FALLBACK_IDS[0]
        ][0]
        self.assertFalse(
            materializer.locator_allowed(
                unauthorized,
                materializer.TSMC_EFFECTIVE_LOCATOR_OVERRIDES[EXPECTED_TSMC_FALLBACK_IDS[0]][1],
                None,
            )
        )
        wrong_identity = dict(items[EXPECTED_TSMC_FALLBACK_IDS[0]])
        wrong_identity["source_id"] = "SRC-SEMI-MICRON-PROHIBITED"
        effective = materializer.TSMC_EFFECTIVE_LOCATOR_OVERRIDES[EXPECTED_TSMC_FALLBACK_IDS[0]][1]
        self.assertFalse(materializer.locator_allowed(wrong_identity, effective, None))

    def test_ordinary_api_200_behavior_is_unchanged(self) -> None:
        source_id = EXPECTED_TSMC_FALLBACK_IDS[1]
        api = FakeResponse(status=200, url=self.locator, body=valid_pdf(b"o"), content_type="application/pdf")
        browser = FakeResponse(status=200, url=self.locator, body=valid_pdf(b"n"), content_type="application/pdf")
        result, sidecar, context = self.run_capture(
            source_id=source_id,
            api_response=api,
            browser_response=browser,
        )
        self.assertEqual(result["http_status"], 200)
        self.assertNotIn("capture_transport", result)
        self.assertNotIn("prior_failed_acquisition_attempt", result)
        self.assertNotIn("capture_transport", sidecar)
        self.assertEqual(api.body_calls, 1)
        self.assertEqual(browser.body_calls, 0)
        self.assertEqual(len(context.page.goto_calls), 1)
        self.assertIsNone(context.page.cdp_session)
        self.assertTrue(api.disposed)


if __name__ == "__main__":
    unittest.main()
