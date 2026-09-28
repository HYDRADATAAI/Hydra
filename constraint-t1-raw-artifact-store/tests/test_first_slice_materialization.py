from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_t1_raw.first_slice_materialization import (
    FirstSliceMaterializationError,
    materialize_capture_plan,
    validate_public_materialization_attestation,
)


class FirstSliceMaterializationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "public-repo"
        self.repo.mkdir()
        self.private = self.base / "private"
        self.captures = self.base / "captures"
        self.captures.mkdir()

        (self.captures / "a.html").write_bytes(b"<html>A</html>\n")
        (self.captures / "b.pdf").write_bytes(b"%PDF-synthetic-B\n")

        self.registry = {
            "slice_id": "SLICE-X",
            "sources": [
                {"source_id": "SRC-A", "url": "https://example.invalid/a"},
                {"source_id": "SRC-B", "url": "https://example.invalid/b"},
            ],
        }
        self.plan = {
            "schema_version": "hydra-constraint-first-slice-local-capture-plan/v1",
            "slice_id": "SLICE-X",
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "release_id": "REL-SLICE-X-001",
            "release_created_at": "2026-09-26T13:10:00Z",
            "captures": [
                {
                    "source_id": "SRC-A",
                    "source_version_id": "SV-A-001",
                    "input_file": str(self.captures / "a.html"),
                    "content_type": "text/html",
                    "source_locator": "https://example.invalid/a",
                    "acquired_at": "2026-09-26T13:00:00Z",
                    "processing_disposition": "ELIGIBLE",
                },
                {
                    "source_id": "SRC-B",
                    "source_version_id": "SV-B-001",
                    "input_file": str(self.captures / "b.pdf"),
                    "content_type": "application/pdf",
                    "source_locator": "https://example.invalid/b",
                    "acquired_at": "2026-09-26T13:01:00Z",
                    "processing_disposition": "ELIGIBLE",
                },
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def run_plan(self, plan=None):
        return materialize_capture_plan(
            registry=self.registry,
            plan=self.plan if plan is None else plan,
            private_root=self.private,
            public_repo_root=self.repo,
        )

    def test_complete_source_set_materializes_and_becomes_persisted_t2_eligible(self):
        attestation = self.run_plan()
        self.assertEqual(2, attestation["registry_source_count"])
        self.assertEqual(2, attestation["materialized_source_count"])
        self.assertEqual(2, attestation["ordinary_t2_eligible_count"])
        self.assertEqual(0, attestation["ordinary_t2_blocked_count"])
        self.assertTrue(attestation["all_registry_sources_materialized"])
        self.assertTrue(attestation["all_sources_ordinary_t2_eligible"])
        self.assertFalse(attestation["strict_historical_replay_promoted"])
        self.assertFalse(attestation["historical_availability_backdated"])
        self.assertTrue(all(
            row["available_at"] == row["acquired_at"]
            for row in attestation["members"]
        ))

    def test_capture_plan_must_cover_exact_registry_source_set(self):
        bad = copy.deepcopy(self.plan)
        bad["captures"] = bad["captures"][:1]
        with self.assertRaisesRegex(FirstSliceMaterializationError, "exactly match registry"):
            self.run_plan(bad)

    def test_unregistered_source_is_rejected(self):
        bad = copy.deepcopy(self.plan)
        bad["captures"][0]["source_id"] = "SRC-UNKNOWN"
        with self.assertRaisesRegex(FirstSliceMaterializationError, "unregistered source"):
            self.run_plan(bad)

    def test_registry_locator_substitution_is_rejected(self):
        bad = copy.deepcopy(self.plan)
        bad["captures"][0]["source_locator"] = "https://example.invalid/imposter"
        with self.assertRaisesRegex(FirstSliceMaterializationError, "exactly match registry URL"):
            self.run_plan(bad)

    def test_raw_input_inside_public_repo_is_rejected(self):
        bad = copy.deepcopy(self.plan)
        public_capture = self.repo / "raw-source.html"
        public_capture.write_bytes(b"should-not-be-public\n")
        bad["captures"][0]["input_file"] = str(public_capture)
        with self.assertRaisesRegex(FirstSliceMaterializationError, "must not live inside"):
            self.run_plan(bad)

    def test_caller_cannot_backdate_available_at_in_conservative_mode(self):
        bad = copy.deepcopy(self.plan)
        bad["captures"][0]["available_at"] = "2023-01-01T00:00:00Z"
        with self.assertRaisesRegex(FirstSliceMaterializationError, "must not be supplied"):
            self.run_plan(bad)

    def test_historical_availability_mode_is_not_silently_supported(self):
        bad = copy.deepcopy(self.plan)
        bad["availability_mode"] = "HISTORICAL_PROOF"
        with self.assertRaisesRegex(FirstSliceMaterializationError, "only ACQUISITION_TIME_CONSERVATIVE"):
            self.run_plan(bad)

    def test_release_cannot_precede_latest_acquisition(self):
        bad = copy.deepcopy(self.plan)
        bad["release_created_at"] = "2026-09-26T13:00:30Z"
        with self.assertRaisesRegex(FirstSliceMaterializationError, "cannot precede"):
            self.run_plan(bad)

    def test_quarantined_member_materializes_but_does_not_become_t2_eligible(self):
        plan = copy.deepcopy(self.plan)
        plan["captures"][1]["processing_disposition"] = "QUARANTINED"
        attestation = self.run_plan(plan)
        self.assertEqual(2, attestation["materialized_source_count"])
        self.assertEqual(1, attestation["ordinary_t2_eligible_count"])
        self.assertEqual(1, attestation["ordinary_t2_blocked_count"])
        self.assertFalse(attestation["all_sources_ordinary_t2_eligible"])


    def test_public_attestation_validates_without_private_raw_bytes(self):
        attestation = self.run_plan()
        validate_public_materialization_attestation(
            attestation=attestation,
            registry=self.registry,
        )

    def test_public_attestation_rejects_private_path_leakage(self):
        attestation = self.run_plan()
        attestation["members"][0]["input_file"] = str(self.captures / "a.html")
        with self.assertRaisesRegex(FirstSliceMaterializationError, "private/raw path"):
            validate_public_materialization_attestation(
                attestation=attestation,
                registry=self.registry,
            )

    def test_public_attestation_rejects_member_digest_tamper(self):
        attestation = self.run_plan()
        attestation["members"][0]["artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(FirstSliceMaterializationError, "release SHA"):
            validate_public_materialization_attestation(
                attestation=attestation,
                registry=self.registry,
            )

    def test_replay_of_identical_capture_plan_is_idempotent(self):
        left = self.run_plan()
        right = self.run_plan()
        self.assertEqual(left, right)


if __name__ == "__main__":
    unittest.main()
