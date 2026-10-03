from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = (
    ROOT
    / "docs"
    / "constraint"
    / "first_slice"
    / "ai_data_center_power_infrastructure_v1"
    / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"
)
PUBLIC_STATUS = (
    ROOT
    / "docs"
    / "constraint"
    / "architecture"
    / "HYDRA_CONSTRAINT_BATCH017_POST_CAPTURE_PUBLIC_STATUS_V001_20260926.json"
)
SUCCESSOR_STATUS = (
    ROOT
    / "docs"
    / "constraint"
    / "architecture"
    / "HYDRA_CONSTRAINT_BATCH017_NINE_SOURCE_PRIVATE_RECORD_STATUS_V002_20260928.json"
)

HEX64 = re.compile(r"^[0-9a-f]{64}$")


class Batch017PostCapturePublicStatusIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.status = json.loads(PUBLIC_STATUS.read_text(encoding="utf-8"))
        cls.successor = json.loads(SUCCESSOR_STATUS.read_text(encoding="utf-8"))

    def test_exact_registered_source_set_is_materialized(self) -> None:
        registered = self.registry["sources"]
        expected_ids = {row["source_id"] for row in registered}
        members = self.status["members"]
        observed_ids = {row["source_id"] for row in members}

        self.assertEqual(len(registered), 9)
        self.assertEqual(self.status["source_count"], 9)
        self.assertEqual(self.status["materialized_source_count"], 9)
        self.assertEqual(self.status["ordinary_t2_eligible_count"], 9)
        self.assertEqual(len(members), 9)
        self.assertEqual(observed_ids, expected_ids)
        self.assertEqual(len(observed_ids), 9)

    def test_member_metadata_is_current_capture_only_and_fail_closed(self) -> None:
        locators = {row["source_id"]: row["url"] for row in self.registry["sources"]}

        for member in self.status["members"]:
            source_id = member["source_id"]
            locator = locators[source_id]
            expected_type = (
                "application/pdf"
                if locator.lower().endswith(".pdf")
                else "text/html"
            )
            self.assertEqual(member["content_type"], expected_type)
            self.assertEqual(member["available_at"], member["acquired_at"])
            self.assertTrue(member["ordinary_t2_eligible"])
            self.assertEqual(member["processing_disposition"], "ELIGIBLE")
            self.assertIsInstance(member["byte_length"], int)
            self.assertGreater(member["byte_length"], 0)
            self.assertRegex(member["artifact_sha256"], HEX64)
            self.assertRegex(member["receipt_sha256"], HEX64)
            self.assertTrue(
                member["source_version_id"].startswith(f"SV-{source_id}-")
            )
            self.assertFalse(any(key.endswith("_path") for key in member))
            self.assertNotIn("raw_bytes", member)
            self.assertNotIn("body", member)

    def test_materialization_blocker_is_closed_without_historical_promotion(self) -> None:
        closure = self.status["closure"]
        self.assertEqual(
            closure[
                "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"
            ],
            "CLOSED_BY_VALIDATED_PRIVATE_T1_ATTESTATION",
        )
        self.assertEqual(
            closure["ORDINARY_SOURCE_VERSION_HASHES"],
            "COMPLETE_FOR_CAPTURED_SOURCE_VERSIONS",
        )
        self.assertEqual(
            closure["PERSISTED_T1_T2_CURRENT_CUSTODY"],
            "COMPLETE",
        )
        self.assertFalse(self.status["historical_backdating_performed"])
        self.assertFalse(self.status["strict_historical_replay_promoted"])
        self.assertFalse(self.status["native_signed_t5_t6_receipt_present"])
        self.assertFalse(self.status["canonical_admission_promoted"])
        self.assertFalse(self.status["private_paths_published"])
        self.assertFalse(self.status["public_raw_content_published"])
        self.assertEqual(
            self.status["still_blocked"]["HISTORICAL_AVAILABLE_AT_BEFORE_CAPTURE"],
            "UNPROVEN",
        )
        self.assertEqual(
            self.status["still_blocked"]["ORDINARY_POINT_IN_TIME_REPLAY_READY"],
            "NO",
        )

    def test_release_and_attestation_digests_are_well_formed(self) -> None:
        self.assertRegex(self.status["release_sha256"], HEX64)
        self.assertRegex(self.status["source_attestation_sha256"], HEX64)
        self.assertEqual(
            self.status["release_id"],
            "REL-AIDC-FIRST-SLICE-20260928T212825Z",
        )

    def test_successor_preserves_v001_and_closes_only_current_custody_gate(self) -> None:
        self.assertEqual(
            self.successor["predecessor_status"],
            "HYDRA_CONSTRAINT_BATCH017_NINE_SOURCE_PRIVATE_RECORD_STATUS_V001_20260926",
        )
        results = self.successor["results"]
        self.assertEqual(results["ACTUAL_NINE_SOURCE_PRIVATE_MATERIALIZATION"], "YES")
        self.assertEqual(
            results["ORDINARY_SOURCE_VERSION_HASH_LINEAGE_COMPLETE"],
            "COMPLETE_FOR_CAPTURED_SOURCE_VERSIONS",
        )
        self.assertEqual(results["PERSISTED_T1_T2_CURRENT_CUSTODY"], "COMPLETE")
        self.assertEqual(results["ORDINARY_POINT_IN_TIME_REPLAY_READY"], "NO")
        self.assertEqual(results["HISTORICAL_AVAILABLE_AT_BEFORE_CAPTURE"], "UNPROVEN")
        self.assertEqual(results["NATIVE_SIGNED_T5_T6_RECEIPT_PRESENT"], "NO")
        self.assertEqual(results["CANONICAL_ADMISSION_AUTHORIZED"], "NO")
        self.assertEqual(
            self.successor["closed_blockers"],
            ["PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"],
        )


if __name__ == "__main__":
    unittest.main()
