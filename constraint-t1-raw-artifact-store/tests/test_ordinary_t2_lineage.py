from __future__ import annotations

import copy
import unittest

from hydra_constraint_t1_raw.ordinary_t2_lineage import (
    OrdinaryT2LineageError,
    build_ordinary_t2_lineage,
    select_ordinary_t2_members,
    validate_ordinary_t2_lineage,
)


class OrdinaryT2LineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.slice_id = "SLICE-X"
        self.records = [
            {
                "source_id": "SRC-A",
                "source_version_id": "SV-A-001",
                "source_locator": "https://example.invalid/a",
                "processing_disposition": "ELIGIBLE",
                "historical_backdating_authorized": False,
            },
            {
                "source_id": "SRC-B",
                "source_version_id": "SV-B-001",
                "source_locator": "https://example.invalid/b",
                "processing_disposition": "ELIGIBLE",
                "historical_backdating_authorized": False,
            },
        ]
        self.attestation = {
            "slice_id": self.slice_id,
            "release_id": "REL-X",
            "release_sha256": "a" * 64,
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "materialized_source_count": 2,
            "ordinary_t2_eligible_count": 2,
            "all_sources_ordinary_t2_eligible": True,
            "historical_availability_backdated": False,
            "strict_historical_replay_promoted": False,
            "public_raw_content_published": False,
            "private_paths_published": False,
            "members": [
                {
                    "source_id": "SRC-B",
                    "source_version_id": "SV-B-001",
                    "artifact_sha256": "b" * 64,
                    "receipt_sha256": "c" * 64,
                    "source_locator": "https://example.invalid/b",
                    "content_type": "application/pdf",
                    "byte_length": 200,
                    "acquired_at": "2026-09-28T12:01:00Z",
                    "available_at": "2026-09-28T12:01:00Z",
                    "ordinary_t2_eligible": True,
                },
                {
                    "source_id": "SRC-A",
                    "source_version_id": "SV-A-001",
                    "artifact_sha256": "d" * 64,
                    "receipt_sha256": "e" * 64,
                    "source_locator": "https://example.invalid/a",
                    "content_type": "text/html",
                    "byte_length": 100,
                    "acquired_at": "2026-09-28T12:00:00Z",
                    "available_at": "2026-09-28T12:00:00Z",
                    "ordinary_t2_eligible": True,
                },
            ],
        }

    def build(self):
        return build_ordinary_t2_lineage(
            attestation=self.attestation,
            source_records=self.records,
            expected_slice_id=self.slice_id,
        )

    def test_build_is_deterministic_and_normalizes_sort_order(self):
        left = self.build()
        right = self.build()
        self.assertEqual(left, right)
        self.assertEqual(["SRC-A", "SRC-B"], [row["source_id"] for row in left["members"]])
        self.assertEqual(2, left["source_count"])
        self.assertEqual(2, left["normalized_source_version_count"])
        self.assertTrue(left["ordinary_source_version_hash_lineage_complete"])
        self.assertTrue(left["ordinary_current_source_set_ready"])
        self.assertFalse(left["strict_historical_replay_ready"])
        self.assertFalse(left["canonical_evidence_admission_promoted"])
        validate_ordinary_t2_lineage(
            packet=left,
            source_records=self.records,
            expected_slice_id=self.slice_id,
        )

    def test_attestation_counts_require_exact_integer_types(self):
        valid_one_source_attestation = copy.deepcopy(self.attestation)
        valid_one_source_attestation["members"] = valid_one_source_attestation["members"][:1]
        valid_one_source_attestation["materialized_source_count"] = 1
        valid_one_source_attestation["ordinary_t2_eligible_count"] = 1
        valid_one_source_packet = build_ordinary_t2_lineage(
            attestation=valid_one_source_attestation,
            source_records=self.records[:1],
            expected_slice_id=self.slice_id,
        )
        self.assertEqual(1, valid_one_source_packet["source_count"])

        for field in ("materialized_source_count", "ordinary_t2_eligible_count"):
            for value in (True, 1.0):
                with self.subTest(field=field, value=value):
                    attestation = copy.deepcopy(valid_one_source_attestation)
                    attestation[field] = value
                    with self.assertRaises(OrdinaryT2LineageError):
                        build_ordinary_t2_lineage(
                            attestation=attestation,
                            source_records=self.records[:1],
                            expected_slice_id=self.slice_id,
                        )

    def test_packet_counts_require_exact_integer_types(self):
        one_source_attestation = copy.deepcopy(self.attestation)
        one_source_attestation["members"] = one_source_attestation["members"][:1]
        one_source_attestation["materialized_source_count"] = 1
        one_source_attestation["ordinary_t2_eligible_count"] = 1
        packet = build_ordinary_t2_lineage(
            attestation=one_source_attestation,
            source_records=self.records[:1],
            expected_slice_id=self.slice_id,
        )
        for field in ("source_count", "normalized_source_version_count"):
            for value in (True, 1.0):
                with self.subTest(field=field, value=value):
                    malformed = copy.deepcopy(packet)
                    malformed[field] = value
                    with self.assertRaises(OrdinaryT2LineageError):
                        validate_ordinary_t2_lineage(
                            packet=malformed,
                            source_records=self.records[:1],
                            expected_slice_id=self.slice_id,
                        )

    def test_no_lookahead_selection(self):
        packet = self.build()
        self.assertEqual(
            [],
            select_ordinary_t2_members(
                packet=packet,
                source_records=self.records,
                expected_slice_id=self.slice_id,
                as_of="2026-09-28T11:59:59Z",
            ),
        )
        self.assertEqual(
            ["SRC-A"],
            [
                row["source_id"]
                for row in select_ordinary_t2_members(
                    packet=packet,
                    source_records=self.records,
                    expected_slice_id=self.slice_id,
                    as_of="2026-09-28T12:00:00Z",
                )
            ],
        )
        self.assertEqual(
            ["SRC-A", "SRC-B"],
            [
                row["source_id"]
                for row in select_ordinary_t2_members(
                    packet=packet,
                    source_records=self.records,
                    expected_slice_id=self.slice_id,
                    as_of="2026-09-28T12:01:00Z",
                )
            ],
        )

    def test_backdating_is_rejected(self):
        bad = copy.deepcopy(self.attestation)
        bad["members"][0]["available_at"] = "2020-01-01T00:00:00Z"
        with self.assertRaisesRegex(OrdinaryT2LineageError, "AVAILABLE_AT"):
            build_ordinary_t2_lineage(
                attestation=bad,
                source_records=self.records,
                expected_slice_id=self.slice_id,
            )

    def test_quarantined_source_record_is_rejected(self):
        records = copy.deepcopy(self.records)
        records[0]["processing_disposition"] = "QUARANTINED"
        with self.assertRaisesRegex(OrdinaryT2LineageError, "must remain ELIGIBLE"):
            build_ordinary_t2_lineage(
                attestation=self.attestation,
                source_records=records,
                expected_slice_id=self.slice_id,
            )

    def test_source_version_mismatch_is_rejected(self):
        bad = copy.deepcopy(self.attestation)
        bad["members"][0]["source_version_id"] = "SV-B-OTHER"
        with self.assertRaisesRegex(OrdinaryT2LineageError, "source_version_id mismatch"):
            build_ordinary_t2_lineage(
                attestation=bad,
                source_records=self.records,
                expected_slice_id=self.slice_id,
            )

    def test_replay_promotion_is_rejected(self):
        packet = self.build()
        packet["strict_historical_replay_ready"] = True
        with self.assertRaisesRegex(OrdinaryT2LineageError, "strict historical replay promoted"):
            validate_ordinary_t2_lineage(
                packet=packet,
                source_records=self.records,
                expected_slice_id=self.slice_id,
            )

    def test_canonical_evidence_promotion_is_rejected(self):
        packet = self.build()
        packet["canonical_evidence_admission_promoted"] = True
        with self.assertRaisesRegex(OrdinaryT2LineageError, "canonical evidence admission promoted"):
            validate_ordinary_t2_lineage(
                packet=packet,
                source_records=self.records,
                expected_slice_id=self.slice_id,
            )


if __name__ == "__main__":
    unittest.main()
