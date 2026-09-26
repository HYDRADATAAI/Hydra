from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "private" / "Test-HYDRAConstraintThreeSourceSanitizedHarPreflight_V001_20260926.py"

spec = importlib.util.spec_from_file_location("three_har_preflight", TOOL)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

validate_three_hars = module.validate_three_hars
BrowserResponseCaptureError = module.BrowserResponseCaptureError


SOURCES = {
    "lbnl": (
        "https://emp.lbl.gov/publications/queued-2025-edition-characteristics",
        "Queued Up: 2025 Edition",
    ),
    "ferc": (
        "https://www.ferc.gov/news-events/news/fact-sheet-improvements-generator-interconnection-procedures-and-agreements",
        "Fact Sheet | Improvements to Generator Interconnection Procedures and Agreements",
    ),
    "pjm": (
        "https://insidelines.pjm.com/2025-year-in-review-planning-prepares-for-burgeoning-electricity-demand/",
        "2025 Year in Review: Planning Prepares for Burgeoning Electricity Demand",
    ),
}


def entry(url: str, marker: str, *, status=200, headers=None, body=None):
    if body is None:
        body = f"<html><h1>{marker}</h1></html>"
    return {
        "startedDateTime": "2026-09-26T19:30:00.000Z",
        "request": {"url": url, "headers": headers or []},
        "response": {
            "status": status,
            "headers": [],
            "content": {"mimeType": "text/html", "text": body},
        },
    }


def write_har(path: Path, row: dict):
    path.write_text(json.dumps({"log": {"entries": [row]}}), encoding="utf-8")


class ThreeSourceHarPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.private = self.base / "private"
        self.private.mkdir()
        self.paths = {}
        for key, (url, marker) in SOURCES.items():
            path = self.private / f"{key}.har"
            write_har(path, entry(url, marker))
            self.paths[key] = path

    def tearDown(self):
        self.temp.cleanup()

    def run_valid(self):
        return validate_three_hars(
            lbnl_har=self.paths["lbnl"],
            ferc_har=self.paths["ferc"],
            pjm_har=self.paths["pjm"],
            public_repo_root=self.repo,
        )

    def test_all_three_exact_responses_pass_without_creating_authority(self):
        summary = self.run_valid()
        self.assertEqual(3, summary["source_count"])
        self.assertTrue(summary["preflight_only"])
        self.assertFalse(summary["capture_plan_created"])
        self.assertFalse(summary["t1_objects_created"])
        self.assertFalse(summary["t1_receipts_created"])
        self.assertFalse(summary["t1_release_created"])
        self.assertFalse(summary["raw_bodies_written_by_preflight"])
        self.assertFalse(summary["ordinary_replay_promoted"])
        self.assertFalse(summary["canonical_admission_promoted"])
        self.assertEqual(3, len(summary["results"]))

    def test_missing_har_fails_closed(self):
        self.paths["ferc"].unlink()
        with self.assertRaisesRegex(BrowserResponseCaptureError, "sanitized HAR file not found"):
            self.run_valid()

    def test_alternate_registered_source_url_is_rejected(self):
        url, marker = SOURCES["pjm"]
        write_har(
            self.paths["pjm"],
            entry("https://www.pjm.com/related.pdf", marker),
        )
        with self.assertRaisesRegex(BrowserResponseCaptureError, "exact registered URL not present"):
            self.run_valid()

    def test_403_challenge_response_is_rejected(self):
        url, marker = SOURCES["lbnl"]
        write_har(
            self.paths["lbnl"],
            entry(url, marker, status=403, body="<html>Attention Required! | Cloudflare</html>"),
        )
        with self.assertRaisesRegex(BrowserResponseCaptureError, "no acceptable exact-URL"):
            self.run_valid()

    def test_sensitive_cookie_header_is_rejected(self):
        url, marker = SOURCES["ferc"]
        write_har(
            self.paths["ferc"],
            entry(url, marker, headers=[{"name": "Cookie", "value": "secret"}]),
        )
        with self.assertRaisesRegex(BrowserResponseCaptureError, "sensitive header"):
            self.run_valid()

    def test_wrong_body_marker_is_rejected(self):
        url, marker = SOURCES["pjm"]
        write_har(
            self.paths["pjm"],
            entry(url, marker, body="<html><h1>Different article</h1></html>"),
        )
        with self.assertRaisesRegex(BrowserResponseCaptureError, "missing expected source marker"):
            self.run_valid()

    def test_har_inside_public_repo_is_rejected(self):
        url, marker = SOURCES["lbnl"]
        inside = self.repo / "lbnl.har"
        write_har(inside, entry(url, marker))
        with self.assertRaisesRegex(BrowserResponseCaptureError, "outside the public repository"):
            validate_three_hars(
                lbnl_har=inside,
                ferc_har=self.paths["ferc"],
                pjm_har=self.paths["pjm"],
                public_repo_root=self.repo,
            )

    def test_summary_contains_hashes_not_raw_bodies_or_private_paths(self):
        summary = self.run_valid()
        rendered = json.dumps(summary)
        self.assertNotIn(str(self.private), rendered)
        self.assertNotIn("<html>", rendered)
        for row in summary["results"]:
            self.assertEqual(64, len(row["body_sha256"]))
            self.assertGreater(row["byte_length"], 0)


if __name__ == "__main__":
    unittest.main()
