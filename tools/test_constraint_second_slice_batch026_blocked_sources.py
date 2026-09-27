#!/usr/bin/env python3
"""Offline regressions for operator-blocked Batch026 capture sources."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py"
QUEUE = ROOT / (
    "docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/"
    "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH026_SEMICONDUCTOR_PRIVATE_T1_CAPTURE_QUEUE_V001_20260926.json"
)

EXPECTED_BLOCKED_SOURCE_IDS = (
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


def import_runner() -> Any:
    spec = importlib.util.spec_from_file_location("hydra_batch026_blocked_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to import Batch026 capture runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakePlaywrightManager:
    def __enter__(self) -> object:
        return object()

    def __exit__(self, *_args: Any) -> None:
        return None


class FakeCaptureContext:
    def close(self) -> None:
        return None


class BlockedSourceExecutionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = import_runner()
        cls.queue_doc = json.loads(QUEUE.read_text(encoding="utf-8"))
        cls.queue = cls.runner.validate_queue(cls.queue_doc)

    def test_canonical_queue_is_validated_and_partitioned_41_9_32(self) -> None:
        self.assertEqual(len(self.queue), 41)
        self.assertEqual(set(self.runner.OPERATOR_BLOCKED_SOURCE_IDS), set(EXPECTED_BLOCKED_SOURCE_IDS))
        blocked, eligible = self.runner.partition_capture_queue(
            self.queue,
            self.runner.OPERATOR_BLOCKED_SOURCE_IDS,
        )
        self.assertEqual(len(blocked), 9)
        self.assertEqual(len(eligible), 32)
        self.assertEqual(
            tuple(item["source_id"] for item in blocked),
            tuple(source_id for source_id in EXPECTED_BLOCKED_SOURCE_IDS),
        )
        self.assertEqual(len(blocked) + len(eligible), len(self.queue))

    def test_unknown_blocked_source_id_fails_closed(self) -> None:
        blocked = list(self.runner.OPERATOR_BLOCKED_SOURCE_IDS) + ["SRC-UNKNOWN"]
        with self.assertRaisesRegex(self.runner.CaptureError, "unknown blocked source ID"):
            self.runner.partition_capture_queue(self.queue, blocked)

    def test_duplicate_blocked_source_id_fails_closed(self) -> None:
        blocked = list(self.runner.OPERATOR_BLOCKED_SOURCE_IDS)
        blocked.append(blocked[0])
        with self.assertRaisesRegex(self.runner.CaptureError, "duplicate blocked source ID"):
            self.runner.partition_capture_queue(self.queue, blocked)

    def test_malformed_blocked_source_set_fails_closed(self) -> None:
        for blocked in ("not-a-list", [None], [""]):
            with self.subTest(blocked=blocked):
                with self.assertRaises(self.runner.CaptureError):
                    self.runner.partition_capture_queue(self.queue, blocked)

    def test_removing_required_blocked_source_is_detected(self) -> None:
        blocked = self.runner.OPERATOR_BLOCKED_SOURCE_IDS[:-1]
        with self.assertRaisesRegex(self.runner.CaptureError, "required blocked-source set mismatch"):
            self.runner.partition_capture_queue(self.queue, blocked)

    def run_fake_capture(self, capture_behavior: Any) -> tuple[int, dict[str, Any], list[str], set[str]]:
        blocked_ids = set(self.runner.OPERATOR_BLOCKED_SOURCE_IDS)
        seen_source_ids: list[str] = []

        def fake_capture_one(**kwargs: Any) -> dict[str, Any]:
            source_id = kwargs["item"]["source_id"]
            self.assertNotIn(source_id, blocked_ids)
            seen_source_ids.append(source_id)
            return capture_behavior(kwargs)

        fake_playwright = types.ModuleType("playwright")
        fake_sync_api = types.ModuleType("playwright.sync_api")
        fake_sync_api.sync_playwright = FakePlaywrightManager
        fake_playwright.sync_api = fake_sync_api

        with tempfile.TemporaryDirectory() as temporary_directory:
            temp_root = Path(temporary_directory)
            private_root = temp_root / "private"
            inbox_root = temp_root / "inbox"
            args = [
                str(RUNNER),
                "--authorized-public-acquisition",
                "--repo-root", str(ROOT),
                "--private-root", str(private_root),
                "--inbox-root", str(inbox_root),
                "--challenge-wait-seconds", "0",
            ]
            output = io.StringIO()
            with (
                patch.object(self.runner, "launch_context", return_value=(FakeCaptureContext(), "fake")),
                patch.object(self.runner, "capture_one", side_effect=fake_capture_one),
                patch.object(
                    self.runner,
                    "resolve_remediated_locator",
                    side_effect=AssertionError("blocked remediated source reached locator resolution"),
                ) as resolve_spy,
                patch.dict(sys.modules, {"playwright": fake_playwright, "playwright.sync_api": fake_sync_api}),
                patch.object(sys, "argv", args),
                contextlib.redirect_stdout(output),
            ):
                result = self.runner.main()
            journal = json.loads(
                (inbox_root / "HYDRA_CONSTRAINT_SEMI_B026_BROWSER_CAPTURE_JOURNAL_V001.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertFalse(resolve_spy.called)
            for item in self.queue:
                if item["source_id"] in blocked_ids:
                    self.assertFalse((inbox_root / item["inbox_filename"]).exists())
                    self.assertFalse(Path(str(inbox_root / item["inbox_filename"]) + ".capture.json").exists())
            inbox_names = {path.name for path in inbox_root.iterdir()}
            return result, journal, seen_source_ids, inbox_names

    def test_blocked_sources_never_reach_capture_and_eligible_sources_do(self) -> None:
        def successful_capture(kwargs: dict[str, Any]) -> dict[str, Any]:
            item = kwargs["item"]
            return {
                "source_id": item["source_id"],
                "source_version_id": item["source_version_id"],
                "byte_length": 0,
                "artifact_sha256": "0" * 64,
                "status": "CAPTURED",
            }

        result, journal, seen, inbox_names = self.run_fake_capture(successful_capture)
        blocked_ids = set(EXPECTED_BLOCKED_SOURCE_IDS)
        eligible_ids = [item["source_id"] for item in self.queue if item["source_id"] not in blocked_ids]
        self.assertEqual(result, 0)
        self.assertEqual(seen, eligible_ids)
        self.assertTrue(blocked_ids.isdisjoint(seen))
        self.assertEqual(
            journal["source_accounting"],
            {
                "total": 41,
                "blocked_by_operator": 9,
                "eligible": 32,
                "attempted": 32,
                "completed": 32,
                "failed": 0,
                "pending": 0,
            },
        )
        self.assertEqual(
            {entry["source_id"] for entry in journal["blocked_sources"]},
            blocked_ids,
        )
        self.assertTrue(all(entry["status"] == "BLOCKED_BY_OPERATOR" for entry in journal["blocked_sources"]))
        self.assertTrue(all(entry["acquisition_attempted"] is False for entry in journal["blocked_sources"]))
        self.assertFalse(journal["complete"])
        self.assertTrue(journal["eligible_complete"])
        self.assertEqual(
            inbox_names,
            {"HYDRA_CONSTRAINT_SEMI_B026_BROWSER_CAPTURE_JOURNAL_V001.json"},
        )

    def test_failed_eligible_capture_is_accounted_and_other_sources_continue(self) -> None:
        eligible_ids = [
            item["source_id"]
            for item in self.queue
            if item["source_id"] not in set(EXPECTED_BLOCKED_SOURCE_IDS)
        ]
        failed_source_id = eligible_ids[0]

        def one_failed_capture(kwargs: dict[str, Any]) -> dict[str, Any]:
            item = kwargs["item"]
            if item["source_id"] == failed_source_id:
                raise self.runner.CaptureError("offline simulated acquisition failure")
            return {
                "source_id": item["source_id"],
                "source_version_id": item["source_version_id"],
                "byte_length": 0,
                "artifact_sha256": "0" * 64,
                "status": "CAPTURED",
            }

        result, journal, seen, _inbox_names = self.run_fake_capture(one_failed_capture)
        self.assertEqual(result, 1)
        self.assertEqual(len(seen), 32)
        self.assertEqual(journal["source_accounting"]["attempted"], 32)
        self.assertEqual(journal["source_accounting"]["completed"], 31)
        self.assertEqual(journal["source_accounting"]["failed"], 1)
        self.assertEqual(journal["source_accounting"]["pending"], 0)
        self.assertEqual([row["source_id"] for row in journal["failed_sources"]], [failed_source_id])
        self.assertFalse(journal["eligible_complete"])


if __name__ == "__main__":
    unittest.main()
