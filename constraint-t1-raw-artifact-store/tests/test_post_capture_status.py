from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_t1_raw.first_slice_materialization import materialize_capture_plan
from hydra_constraint_t1_raw.post_capture_status import (
    PostCaptureStatusError,
    build_public_status,
)


class PostCaptureStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.private = self.base / "private"
        self.captures = self.base / "captures"
        self.captures.mkdir()

        sources = []
        captures = []
        for index in range(9):
            source_id = f"SRC-{index:02d}"
            url = f"https://example.invalid/{index}"
            file_path = self.captures / f"{index}.html"
            file_path.write_text(f"<html>{index}</html>\n", encoding="utf-8")
            sources.append({"source_id": source_id, "url": url})
            captures.append({
                "source_id": source_id,
                "source_version_id": f"SV-{index:02d}-001",
                "input_file": str(file_path),
                "content_type": "text/html",
                "source_locator": url,
                "acquired_at": f"2026-09-26T15:{index:02d}:00Z",
                "processing_disposition": "ELIGIBLE",
            })

        self.registry = {
            "slice_id": "AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1",
            "sources": sources,
        }
        self.plan = {
            "schema_version": "hydra-constraint-first-slice-local-capture-plan/v1",
            "slice_id": "AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1",
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "release_id": "REL-AIDC-TEST-001",
            "release_created_at": "2026-09-26T16:00:00Z",
            "captures": captures,
        }
        self.attestation = materialize_capture_plan(
            registry=self.registry,
            plan=self.plan,
            private_root=self.private,
            public_repo_root=self.repo,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_nine_source_attestation_closes_raw_materialization_only(self):
        status = build_public_status(
            attestation=self.attestation,
            registry=self.registry,
        )
        self.assertEqual(9, status["source_count"])
        self.assertEqual(9, status["materialized_source_count"])
        self.assertEqual(
            self.attestation["ordinary_t2_eligible_count"],
            status["ordinary_t2_eligible_count"],
        )
        self.assertEqual(
            self.attestation["ordinary_t2_blocked_count"],
            status["ordinary_t2_blocked_count"],
        )
        self.assertEqual(
            "CLOSED_BY_VALIDATED_PRIVATE_T1_ATTESTATION",
            status["closure"]["PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"],
        )
        self.assertEqual(
            "COMPLETE_FOR_CAPTURED_SOURCE_VERSIONS",
            status["closure"]["ORDINARY_SOURCE_VERSION_HASHES"],
        )
        self.assertEqual(
            "NO",
            status["still_blocked"]["ORDINARY_POINT_IN_TIME_REPLAY_READY"],
        )
        self.assertEqual(
            "UNPROVEN",
            status["still_blocked"]["HISTORICAL_AVAILABLE_AT_BEFORE_CAPTURE"],
        )
        self.assertFalse(status["strict_historical_replay_promoted"])
        self.assertFalse(status["canonical_admission_promoted"])
        self.assertFalse(status["native_signed_t5_t6_receipt_present"])

    def test_incomplete_source_set_cannot_close_materialization(self):
        bad = copy.deepcopy(self.attestation)
        bad["members"] = bad["members"][:8]
        bad["materialized_source_count"] = 8
        with self.assertRaises(PostCaptureStatusError):
            build_public_status(attestation=bad, registry=self.registry)

    def test_ineligible_members_do_not_reopen_raw_materialization(self):
        status = build_public_status(
            attestation=self.attestation,
            registry=self.registry,
        )
        self.assertEqual(
            "CLOSED_BY_VALIDATED_PRIVATE_T1_ATTESTATION",
            status["closure"]["PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"],
        )
        self.assertGreater(status["ordinary_t2_blocked_count"], 0)
        self.assertFalse(status["all_sources_ordinary_t2_eligible"])
        self.assertEqual(
            "BLOCKED_UNLESS_MEMBER_TIMESTAMP_AUTHORITY_IS_VERIFIED",
            status["still_blocked"]["ORDINARY_T1_T2_ELIGIBILITY"],
        )

    def test_output_contains_no_private_paths_or_raw_bytes(self):
        status = build_public_status(
            attestation=self.attestation,
            registry=self.registry,
        )
        rendered = str(status)
        self.assertNotIn(str(self.private), rendered)
        self.assertNotIn(str(self.captures), rendered)
        self.assertNotIn("artifact_relpath", rendered)
        self.assertNotIn("raw_bytes", rendered)

    def test_combined_replay_blocker_is_only_partially_satisfied(self):
        status = build_public_status(
            attestation=self.attestation,
            registry=self.registry,
        )
        self.assertEqual(
            "HASH_COMPONENT_COMPLETE_HISTORICAL_AS_OF_COMPONENT_REMAINS_BLOCKED",
            status["still_blocked"]["ORDINARY-POINT-IN-TIME-REPLAY-SOURCE-VERSION-HASHES-INCOMPLETE"],
        )


if __name__ == "__main__":
    unittest.main()
