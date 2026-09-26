#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/materialize_constraint_first_slice_private_t1.py"
REGISTRY = (
    ROOT
    / "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
    / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"
)


class PrivateMaterializationRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.staging = self.base / "staging"
        self.private = self.base / "private"
        self.summary = self.base / "safe-summary.json"
        self.staging.mkdir()
        self.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for source in self.registry["sources"]:
            sid = source["source_id"]
            url = source["url"]
            if url.lower().split("?", 1)[0].endswith(".pdf"):
                payload = b"%PDF-1.7\n" + (b"synthetic-private-test-pdf\n" * 32)
            else:
                payload = (
                    b"<!doctype html><html><head><title>synthetic</title></head><body>"
                    + sid.encode("ascii")
                    + (b" synthetic-private-test-body" * 20)
                    + b"</body></html>"
                )
            (self.staging / f"{sid}.raw").write_bytes(payload)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_tool(self):
        return subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--staging-root",
                str(self.staging),
                "--private-root",
                str(self.private),
                "--public-repo-root",
                str(ROOT),
                "--summary",
                str(self.summary),
                "--acquired-at",
                "2026-09-26T14:30:00Z",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_nine_source_materialization_is_persisted_and_idempotent(self):
        first = self.run_tool()
        self.assertEqual(0, first.returncode, first.stdout + first.stderr)
        summary1 = json.loads(self.summary.read_text(encoding="utf-8"))
        self.assertEqual(9, summary1["source_count"])
        self.assertEqual(9, summary1["eligible_source_count"])
        self.assertFalse(summary1["raw_source_content_published"])
        self.assertEqual(9, len(summary1["receipts"]))

        second = self.run_tool()
        self.assertEqual(0, second.returncode, second.stdout + second.stderr)
        summary2 = json.loads(self.summary.read_text(encoding="utf-8"))
        self.assertEqual(summary1["release_sha256"], summary2["release_sha256"])

    def test_missing_source_fails_before_private_store_write(self):
        sid = self.registry["sources"][0]["source_id"]
        (self.staging / f"{sid}.raw").unlink()
        result = self.run_tool()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("exact staged body missing", result.stdout)
        self.assertFalse(self.private.exists())

    def test_error_page_is_rejected(self):
        sid = self.registry["sources"][1]["source_id"]
        (self.staging / f"{sid}.raw").write_bytes(
            b"<!doctype html><html><body>403 Forbidden Access Denied"
            + (b"x" * 512)
            + b"</body></html>"
        )
        result = self.run_tool()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("error/interstitial", result.stdout)
        self.assertFalse(self.private.exists())


if __name__ == "__main__":
    unittest.main()
