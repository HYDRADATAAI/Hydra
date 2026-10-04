from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_t1_raw.browser_response_capture import (
    BrowserResponseCaptureError,
    capture_from_har,
    extract_exact_response,
)


URL = "https://emp.lbl.gov/publications/queued-2025-edition-characteristics"
FERC_URL = "https://www.ferc.gov/news-events/news/fact-sheet-improvements-generator-interconnection-procedures-and-agreements"
PJM_URL = "https://insidelines.pjm.com/2025-year-in-review-planning-prepares-for-burgeoning-electricity-demand/"


def har_entry(*, url=URL, status=200, mime="text/html", body="<html><h1>Queued Up: 2025 Edition</h1></html>", headers=None, encoding=None):
    content = {"mimeType": mime, "text": body}
    if encoding is not None:
        content["encoding"] = encoding
    return {
        "startedDateTime": "2026-09-26T14:40:00.000Z",
        "request": {"url": url, "headers": headers or []},
        "response": {
            "status": status,
            "headers": [],
            "content": content,
        },
    }


def har(*entries):
    return {"log": {"entries": list(entries)}}


class BrowserResponseCaptureTests(unittest.TestCase):
    def test_exact_registered_200_html_response_is_accepted(self):
        body, metadata = extract_exact_response(
            har=har(har_entry()),
            exact_url=URL,
            expected_mime_prefix="text/html",
            expected_text="Queued Up: 2025 Edition",
        )
        self.assertIn(b"Queued Up: 2025 Edition", body)
        self.assertEqual(200, metadata["status"])
        self.assertFalse(metadata["rendered_dom_used"])
        self.assertFalse(metadata["linked_file_substituted"])
        self.assertFalse(metadata["cloudflare_bypass_attempted"])

    def test_ferc_exact_registered_response_and_title_marker_are_accepted(self):
        title = "Fact Sheet | Improvements to Generator Interconnection Procedures and Agreements"
        body, metadata = extract_exact_response(
            har=har(har_entry(url=FERC_URL, body=f"<html><h1>{title}</h1></html>")),
            exact_url=FERC_URL,
            expected_mime_prefix="text/html",
            expected_text=title,
        )
        self.assertIn(title.encode("utf-8"), body)
        self.assertEqual(FERC_URL, metadata["exact_url"])
        self.assertEqual(200, metadata["status"])

    def test_pjm_exact_registered_response_and_title_marker_are_accepted(self):
        title = "2025 Year in Review: Planning Prepares for Burgeoning Electricity Demand"
        body, metadata = extract_exact_response(
            har=har(har_entry(url=PJM_URL, body=f"<html><h1>{title}</h1></html>")),
            exact_url=PJM_URL,
            expected_mime_prefix="text/html",
            expected_text=title,
        )
        self.assertIn(title.encode("utf-8"), body)
        self.assertEqual(PJM_URL, metadata["exact_url"])
        self.assertEqual(200, metadata["status"])

    def test_ferc_or_pjm_alternate_url_cannot_substitute(self):
        cases = [
            (
                FERC_URL,
                "https://www.ferc.gov/news-events/news/some-other-interconnection-page",
                "Fact Sheet | Improvements to Generator Interconnection Procedures and Agreements",
            ),
            (
                PJM_URL,
                "https://www.pjm.com/some-related-year-in-review.pdf",
                "2025 Year in Review: Planning Prepares for Burgeoning Electricity Demand",
            ),
        ]
        for exact_url, alternate_url, title in cases:
            with self.subTest(exact_url=exact_url):
                with self.assertRaisesRegex(BrowserResponseCaptureError, "exact registered URL not present"):
                    extract_exact_response(
                        har=har(har_entry(url=alternate_url, body=f"<html>{title}</html>")),
                        exact_url=exact_url,
                        expected_mime_prefix="text/html",
                        expected_text=title,
                    )

    def test_base64_har_content_is_decoded(self):
        raw = b"<html>Queued Up: 2025 Edition</html>"
        body, _ = extract_exact_response(
            har=har(har_entry(body=base64.b64encode(raw).decode("ascii"), encoding="base64")),
            exact_url=URL,
            expected_mime_prefix="text/html",
            expected_text="Queued Up: 2025 Edition",
        )
        self.assertEqual(raw, body)

    def test_cloudflare_403_block_body_is_rejected(self):
        with self.assertRaisesRegex(BrowserResponseCaptureError, "no acceptable exact-URL"):
            extract_exact_response(
                har=har(har_entry(status=403, body="<html>Attention Required! | Cloudflare</html>")),
                exact_url=URL,
                expected_mime_prefix="text/html",
                expected_text="Queued Up: 2025 Edition",
            )

    def test_cloudflare_challenge_body_is_rejected_even_with_200(self):
        with self.assertRaisesRegex(BrowserResponseCaptureError, "Cloudflare challenge"):
            extract_exact_response(
                har=har(har_entry(status=200, body="<html>Just a moment... cf-chl-token</html>")),
                exact_url=URL,
                expected_mime_prefix="text/html",
                expected_text=None,
            )

    def test_linked_report_pdf_cannot_substitute_for_registered_html_locator(self):
        linked_pdf = "https://eta-publications.lbl.gov/sites/default/files/queued-up-2025.pdf"
        with self.assertRaisesRegex(BrowserResponseCaptureError, "exact registered URL not present"):
            extract_exact_response(
                har=har(har_entry(url=linked_pdf, mime="application/pdf", body="JVBERi0x")),
                exact_url=URL,
                expected_mime_prefix="text/html",
                expected_text="Queued Up: 2025 Edition",
            )

    def test_sanitized_har_is_required(self):
        with self.assertRaisesRegex(BrowserResponseCaptureError, "sensitive header"):
            extract_exact_response(
                har=har(har_entry(headers=[{"name": "Cookie", "value": "cf_clearance=secret"}])),
                exact_url=URL,
                expected_mime_prefix="text/html",
                expected_text="Queued Up: 2025 Edition",
            )

    def test_har_with_initial_block_then_later_success_uses_success_response(self):
        body, _ = extract_exact_response(
            har=har(
                har_entry(status=403, body="<html>Attention Required! | Cloudflare</html>"),
                har_entry(status=200, body="<html>Queued Up: 2025 Edition</html>"),
            ),
            exact_url=URL,
            expected_mime_prefix="text/html",
            expected_text="Queued Up: 2025 Edition",
        )
        self.assertEqual(b"<html>Queued Up: 2025 Edition</html>", body)

    def test_capture_requires_har_and_outputs_outside_public_repo(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir()
            har_path = private / "capture.har"
            har_path.write_text(json.dumps(har(har_entry())), encoding="utf-8")

            with self.assertRaisesRegex(BrowserResponseCaptureError, "outside the public repository"):
                capture_from_har(
                    har_path=har_path,
                    output_path=repo / "body.html",
                    metadata_output_path=private / "metadata.json",
                    exact_url=URL,
                    expected_mime_prefix="text/html",
                    expected_text="Queued Up: 2025 Edition",
                    public_repo_root=repo,
                )

    def test_capture_writes_only_body_and_private_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            private = root / "private"
            private.mkdir()
            har_path = private / "capture.har"
            output = private / "body.html"
            metadata = private / "metadata.json"
            har_path.write_text(json.dumps(har(har_entry())), encoding="utf-8")

            result = capture_from_har(
                har_path=har_path,
                output_path=output,
                metadata_output_path=metadata,
                exact_url=URL,
                expected_mime_prefix="text/html",
                expected_text="Queued Up: 2025 Edition",
                public_repo_root=repo,
            )

            self.assertTrue(output.is_file())
            self.assertTrue(metadata.is_file())
            self.assertEqual("SANITIZED_BROWSER_HAR_EXACT_RESPONSE_BODY", result["capture_method"])
            self.assertFalse(result["rendered_dom_used"])


if __name__ == "__main__":
    unittest.main()
