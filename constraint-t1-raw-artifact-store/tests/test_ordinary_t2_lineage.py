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

    def test_builder_rejects_whitespace_only_content_type(self):
        for content_type in ("   ", "\t\n", "\u2003", "\u00a0"):
            with self.subTest(content_type=repr(content_type)):
                bad = copy.deepcopy(self.attestation)
                bad["members"][0]["content_type"] = content_type
                with self.assertRaisesRegex(OrdinaryT2LineageError, "content_type required"):
                    build_ordinary_t2_lineage(
                        attestation=bad,
                        source_records=self.records,
                        expected_slice_id=self.slice_id,
                    )

    def test_validator_rejects_whitespace_only_content_type(self):
        for content_type in ("   ", "\t\n", "\u2003", "\u00a0"):
            with self.subTest(content_type=repr(content_type)):
                packet = self.build()
                packet["members"][0]["content_type"] = content_type
                with self.assertRaisesRegex(OrdinaryT2LineageError, "content_type invalid"):
                    validate_ordinary_t2_lineage(
                        packet=packet,
                        source_records=self.records,
                        expected_slice_id=self.slice_id,
                    )

    def test_source_identifiers_and_release_id_must_be_nonblank(self):
        for field in ("source_id", "source_version_id"):
            records = copy.deepcopy(self.records)
            records[0][field] = " \t\u2003 "
            with self.subTest(field=field):
                with self.assertRaises(OrdinaryT2LineageError):
                    build_ordinary_t2_lineage(
                        attestation=self.attestation,
                        source_records=records,
                        expected_slice_id=self.slice_id,
                    )

        bad_attestation = copy.deepcopy(self.attestation)
        bad_attestation["release_id"] = " \t\u2003 "
        with self.assertRaisesRegex(OrdinaryT2LineageError, "release_id required"):
            build_ordinary_t2_lineage(
                attestation=bad_attestation,
                source_records=self.records,
                expected_slice_id=self.slice_id,
            )

        packet = self.build()
        packet["release_id"] = " \t\u2003 "
        with self.assertRaisesRegex(OrdinaryT2LineageError, "release_id required"):
            validate_ordinary_t2_lineage(
                packet=packet,
                source_records=self.records,
                expected_slice_id=self.slice_id,
            )

    def test_https_source_locator_requires_a_hostname_and_valid_authority(self):
        accepted_locator = "https://[2001:db8::1]:8443/a/b?x=one#part"
        records = copy.deepcopy(self.records)
        records[0]["source_locator"] = accepted_locator
        attestation = copy.deepcopy(self.attestation)
        attestation["members"][1]["source_locator"] = accepted_locator
        packet = build_ordinary_t2_lineage(
            attestation=attestation,
            source_records=records,
            expected_slice_id=self.slice_id,
        )
        self.assertEqual(accepted_locator, packet["members"][0]["source_locator"])

        for locator in (
            "https://",
            "https:///path",
            "https://?query=value",
            "https://bad host/path",
            "https://example.invalid:99999/path",
            "https://[broken/path",
            "HTTPS://example.invalid/path",
        ):
            bad_records = copy.deepcopy(self.records)
            bad_records[0]["source_locator"] = locator
            with self.subTest(locator=locator):
                with self.assertRaisesRegex(OrdinaryT2LineageError, "HTTPS source_locator"):
                    build_ordinary_t2_lineage(
                        attestation=self.attestation,
                        source_records=bad_records,
                        expected_slice_id=self.slice_id,
                    )

    def test_validator_rejects_non_mapping_packet_with_lineage_error(self):
        with self.assertRaisesRegex(OrdinaryT2LineageError, "packet must be an object"):
            validate_ordinary_t2_lineage(
                packet=None,
                source_records=self.records,
                expected_slice_id=self.slice_id,
            )

    def test_builder_and_validator_require_nonblank_slice_ids(self):
        with self.assertRaisesRegex(OrdinaryT2LineageError, "expected_slice_id"):
            build_ordinary_t2_lineage(
                attestation=self.attestation,
                source_records=self.records,
                expected_slice_id=" \t\u2003 ",
            )

        bad_attestation = copy.deepcopy(self.attestation)
        bad_attestation["slice_id"] = " \t\u2003 "
        with self.assertRaisesRegex(OrdinaryT2LineageError, "slice_id"):
            build_ordinary_t2_lineage(
                attestation=bad_attestation,
                source_records=self.records,
                expected_slice_id=self.slice_id,
            )

        packet = self.build()
        with self.assertRaisesRegex(OrdinaryT2LineageError, "expected_slice_id"):
            validate_ordinary_t2_lineage(
                packet=packet,
                source_records=self.records,
                expected_slice_id=" \t\u2003 ",
            )
        packet["slice_id"] = " \t\u2003 "
        with self.assertRaisesRegex(OrdinaryT2LineageError, "slice_id"):
            validate_ordinary_t2_lineage(
                packet=packet,
                source_records=self.records,
                expected_slice_id=self.slice_id,
            )

    def test_attestation_source_counts_reject_float_and_boolean_aliases(self):
        for field in ("ordinary_t2_eligible_count", "materialized_source_count"):
            attestation = copy.deepcopy(self.attestation)
            attestation[field] = float(attestation[field])
            with self.subTest(field=field, alias="float"):
                with self.assertRaisesRegex(OrdinaryT2LineageError, "must be an integer"):
                    build_ordinary_t2_lineage(
                        attestation=attestation,
                        source_records=self.records,
                        expected_slice_id=self.slice_id,
                    )

        one_source_records = copy.deepcopy(self.records[:1])
        one_source_attestation = copy.deepcopy(self.attestation)
        one_source_attestation["ordinary_t2_eligible_count"] = 1
        one_source_attestation["materialized_source_count"] = 1
        one_source_attestation["members"] = [
            row for row in one_source_attestation["members"]
            if row["source_id"] == "SRC-A"
        ]
        for field in ("ordinary_t2_eligible_count", "materialized_source_count"):
            for alias in (1.0, True):
                bad = copy.deepcopy(one_source_attestation)
                bad[field] = alias
                with self.subTest(field=field, alias=alias):
                    with self.assertRaisesRegex(OrdinaryT2LineageError, "must be an integer"):
                        build_ordinary_t2_lineage(
                            attestation=bad,
                            source_records=one_source_records,
                            expected_slice_id=self.slice_id,
                        )

    def test_validator_source_counts_reject_float_and_boolean_aliases(self):
        packet = self.build()
        for field in ("source_count", "normalized_source_version_count"):
            bad = copy.deepcopy(packet)
            bad[field] = float(bad[field])
            with self.subTest(field=field, alias="float"):
                with self.assertRaisesRegex(OrdinaryT2LineageError, "must be an integer"):
                    validate_ordinary_t2_lineage(
                        packet=bad,
                        source_records=self.records,
                        expected_slice_id=self.slice_id,
                    )

        one_source_records = copy.deepcopy(self.records[:1])
        one_source_attestation = copy.deepcopy(self.attestation)
        one_source_attestation["ordinary_t2_eligible_count"] = 1
        one_source_attestation["materialized_source_count"] = 1
        one_source_attestation["members"] = [
            row for row in one_source_attestation["members"]
            if row["source_id"] == "SRC-A"
        ]
        one_source_packet = build_ordinary_t2_lineage(
            attestation=one_source_attestation,
            source_records=one_source_records,
            expected_slice_id=self.slice_id,
        )
        for field in ("source_count", "normalized_source_version_count"):
            bad = copy.deepcopy(one_source_packet)
            bad[field] = True
            with self.subTest(field=field, alias="bool"):
                with self.assertRaisesRegex(OrdinaryT2LineageError, "must be an integer"):
                    validate_ordinary_t2_lineage(
                        packet=bad,
                        source_records=one_source_records,
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

