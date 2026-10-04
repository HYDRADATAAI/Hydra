from __future__ import annotations

import copy
import unittest

from hydra_constraint_t1_raw.ordinary_t2_evidence_lineage import (
    OrdinaryT2EvidenceLineageError,
    build_ordinary_t2_evidence_lineage,
    select_ordinary_t2_evidence,
    validate_ordinary_t2_evidence_lineage,
)


class OrdinaryT2EvidenceLineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.slice_id = "SLICE-X"
        self.source_records = [
            {
                "source_id": "SRC-A",
                "source_version_id": "SV-A",
                "source_locator": "https://example.invalid/a",
                "processing_disposition": "ELIGIBLE",
                "historical_backdating_authorized": False,
            },
            {
                "source_id": "SRC-B",
                "source_version_id": "SV-B",
                "source_locator": "https://example.invalid/b",
                "processing_disposition": "ELIGIBLE",
                "historical_backdating_authorized": False,
            },
        ]
        self.lineage = {
            "schema_version": "hydra-constraint-ordinary-t2-source-version-lineage/v1",
            "slice_id": self.slice_id,
            "release_id": "REL-X",
            "release_sha256": "a" * 64,
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "source_count": 2,
            "normalized_source_version_count": 2,
            "ordinary_source_version_hash_lineage_complete": True,
            "ordinary_current_source_set_ready": True,
            "strict_historical_replay_ready": False,
            "historical_availability_backdated": False,
            "canonical_evidence_admission_promoted": False,
            "canonical_t5_t6_admission_promoted": False,
            "no_lookahead_rule": "SOURCE_VISIBLE_IFF_AVAILABLE_AT_LTE_AS_OF",
            "historical_replay_blocker": "PRE_ACQUISITION_HISTORICAL_VERSION_AVAILABILITY_NOT_ESTABLISHED",
            "members": [
                {
                    "source_id": "SRC-A",
                    "source_version_id": "SV-A",
                    "artifact_sha256": "b" * 64,
                    "receipt_sha256": "c" * 64,
                    "source_locator": "https://example.invalid/a",
                    "content_type": "text/html",
                    "byte_length": 100,
                    "acquired_at": "2026-09-28T12:00:00Z",
                    "available_at": "2026-09-28T12:00:00Z",
                    "processing_disposition": "ELIGIBLE",
                    "ordinary_t2_eligible": True,
                },
                {
                    "source_id": "SRC-B",
                    "source_version_id": "SV-B",
                    "artifact_sha256": "d" * 64,
                    "receipt_sha256": "e" * 64,
                    "source_locator": "https://example.invalid/b",
                    "content_type": "application/pdf",
                    "byte_length": 200,
                    "acquired_at": "2026-09-28T12:01:00Z",
                    "available_at": "2026-09-28T12:01:00Z",
                    "processing_disposition": "ELIGIBLE",
                    "ordinary_t2_eligible": True,
                },
            ],
            "availability_boundaries": [
                {"as_of": "2026-09-28T12:00:00Z", "eligible_source_ids": ["SRC-A"]},
                {"as_of": "2026-09-28T12:01:00Z", "eligible_source_ids": ["SRC-A", "SRC-B"]},
            ],
        }
        self.evidence = [
            {
                "evidence_id": "EV-A",
                "source_id": "SRC-A",
                "origin_artifact": "evidence-a.json",
                "available_at": "2026-09-27T00:00:00Z",
            },
            {
                "evidence_id": "EV-B",
                "source_id": "SRC-B",
                "origin_artifact": "evidence-b.json",
                "available_at": None,
            },
            {
                "evidence_id": "EV-OLD",
                "source_id": "SRC-QUARANTINED",
                "origin_artifact": "old-evidence.json",
                "available_at": "2026-09-20T00:00:00Z",
            },
        ]

    def build(self):
        return build_ordinary_t2_evidence_lineage(
            lineage_packet=self.lineage,
            source_records=self.source_records,
            evidence_records=self.evidence,
            expected_slice_id=self.slice_id,
        )

    def one_source_fixture(self, evidence_records=None):
        source_records = copy.deepcopy(self.source_records[:1])
        lineage_packet = copy.deepcopy(self.lineage)
        lineage_packet["source_count"] = 1
        lineage_packet["normalized_source_version_count"] = 1
        lineage_packet["members"] = lineage_packet["members"][:1]
        lineage_packet["availability_boundaries"] = lineage_packet["availability_boundaries"][:1]
        if evidence_records is None:
            evidence_records = copy.deepcopy(self.evidence[:1])
        return lineage_packet, source_records, copy.deepcopy(evidence_records)

    def test_binding_uses_exact_source_versions_and_conservative_availability(self):
        packet = self.build()
        self.assertEqual(2, packet["bound_evidence_count"])
        self.assertEqual(1, packet["excluded_evidence_count"])
        self.assertTrue(packet["all_active_sources_have_bound_evidence"])
        by_id = {row["evidence_id"]: row for row in packet["bindings"]}
        self.assertEqual("SV-A", by_id["EV-A"]["source_version_id"])
        self.assertEqual("b" * 64, by_id["EV-A"]["artifact_sha256"])
        self.assertEqual("2026-09-28T12:00:00Z", by_id["EV-A"]["ordinary_t2_available_at"])
        self.assertTrue(by_id["EV-A"]["availability_adjusted_to_source_version"])
        self.assertEqual("2026-09-28T12:01:00Z", by_id["EV-B"]["ordinary_t2_available_at"])
        self.assertEqual("SOURCE_VERSION_AVAILABLE_AT_ONLY", by_id["EV-B"]["availability_basis"])
        self.assertEqual("SOURCE_NOT_IN_ACTIVE_RELEASE", packet["excluded_evidence"][0]["exclusion_reason"])

    def test_selection_enforces_evidence_no_lookahead(self):
        packet = self.build()
        before = select_ordinary_t2_evidence(
            packet=packet,
            lineage_packet=self.lineage,
            source_records=self.source_records,
            evidence_records=self.evidence,
            expected_slice_id=self.slice_id,
            as_of="2026-09-28T11:59:59Z",
        )
        first = select_ordinary_t2_evidence(
            packet=packet,
            lineage_packet=self.lineage,
            source_records=self.source_records,
            evidence_records=self.evidence,
            expected_slice_id=self.slice_id,
            as_of="2026-09-28T12:00:00Z",
        )
        both = select_ordinary_t2_evidence(
            packet=packet,
            lineage_packet=self.lineage,
            source_records=self.source_records,
            evidence_records=self.evidence,
            expected_slice_id=self.slice_id,
            as_of="2026-09-28T12:01:00Z",
        )
        self.assertEqual([], before)
        self.assertEqual(["EV-A"], [row["evidence_id"] for row in first])
        self.assertEqual(["EV-A", "EV-B"], [row["evidence_id"] for row in both])

    def test_duplicate_evidence_id_is_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        evidence[1]["evidence_id"] = "EV-A"
        with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "duplicate evidence_id"):
            build_ordinary_t2_evidence_lineage(
                lineage_packet=self.lineage,
                source_records=self.source_records,
                evidence_records=evidence,
                expected_slice_id=self.slice_id,
            )

    def test_canonical_evidence_promotion_is_rejected(self):
        packet = self.build()
        packet["canonical_evidence_admission_promoted"] = True
        with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "canonical evidence admission promoted"):
            validate_ordinary_t2_evidence_lineage(
                packet=packet,
                lineage_packet=self.lineage,
                source_records=self.source_records,
                evidence_records=self.evidence,
                expected_slice_id=self.slice_id,
            )

    def test_bound_evidence_cannot_claim_canonical_admission(self):
        packet = self.build()
        packet["bindings"][0]["canonical_evidence_admitted"] = True
        with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "canonical evidence admitted"):
            validate_ordinary_t2_evidence_lineage(
                packet=packet,
                lineage_packet=self.lineage,
                source_records=self.source_records,
                evidence_records=self.evidence,
                expected_slice_id=self.slice_id,
            )

    def test_evidence_identifiers_must_be_nonblank_in_builder_and_validator(self):
        packet = self.build()
        for field in ("evidence_id", "source_id", "origin_artifact"):
            evidence = copy.deepcopy(self.evidence)
            evidence[0][field] = " \t\u2003 "
            with self.subTest(field=field, entry="builder"):
                with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "nonblank string"):
                    build_ordinary_t2_evidence_lineage(
                        lineage_packet=self.lineage,
                        source_records=self.source_records,
                        evidence_records=evidence,
                        expected_slice_id=self.slice_id,
                    )
            with self.subTest(field=field, entry="validator"):
                with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "nonblank string"):
                    validate_ordinary_t2_evidence_lineage(
                        packet=packet,
                        lineage_packet=self.lineage,
                        source_records=self.source_records,
                        evidence_records=evidence,
                        expected_slice_id=self.slice_id,
                    )

    def test_all_evidence_counts_reject_float_aliases(self):
        count_fields = (
            "input_evidence_record_count",
            "active_source_count",
            "bound_evidence_count",
            "excluded_evidence_count",
            "active_source_count_with_bound_evidence",
        )
        for field in count_fields:
            packet = self.build()
            packet[field] = float(packet[field])
            with self.subTest(field=field):
                with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "must be an integer"):
                    validate_ordinary_t2_evidence_lineage(
                        packet=packet,
                        lineage_packet=self.lineage,
                        source_records=self.source_records,
                        evidence_records=self.evidence,
                        expected_slice_id=self.slice_id,
                    )

    def test_all_evidence_counts_reject_boolean_aliases_with_one_source(self):
        lineage_packet, source_records, evidence_records = self.one_source_fixture()
        packet = build_ordinary_t2_evidence_lineage(
            lineage_packet=lineage_packet,
            source_records=source_records,
            evidence_records=evidence_records,
            expected_slice_id=self.slice_id,
        )
        for field in (
            "input_evidence_record_count",
            "active_source_count",
            "bound_evidence_count",
            "active_source_count_with_bound_evidence",
        ):
            bad_packet = copy.deepcopy(packet)
            bad_packet[field] = True
            with self.subTest(field=field):
                with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "must be an integer"):
                    validate_ordinary_t2_evidence_lineage(
                        packet=bad_packet,
                        lineage_packet=lineage_packet,
                        source_records=source_records,
                        evidence_records=evidence_records,
                        expected_slice_id=self.slice_id,
                    )

        zero_exclusion_packet = copy.deepcopy(packet)
        zero_exclusion_packet["excluded_evidence_count"] = False
        with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "must be an integer"):
            validate_ordinary_t2_evidence_lineage(
                packet=zero_exclusion_packet,
                lineage_packet=lineage_packet,
                source_records=source_records,
                evidence_records=evidence_records,
                expected_slice_id=self.slice_id,
            )

        evidence_with_exclusion = [*evidence_records, copy.deepcopy(self.evidence[2])]
        packet_with_exclusion = build_ordinary_t2_evidence_lineage(
            lineage_packet=lineage_packet,
            source_records=source_records,
            evidence_records=evidence_with_exclusion,
            expected_slice_id=self.slice_id,
        )
        packet_with_exclusion["excluded_evidence_count"] = True
        with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "must be an integer"):
            validate_ordinary_t2_evidence_lineage(
                packet=packet_with_exclusion,
                lineage_packet=lineage_packet,
                source_records=source_records,
                evidence_records=evidence_with_exclusion,
                expected_slice_id=self.slice_id,
            )

    def test_builder_and_validator_require_nonblank_slice_ids(self):
        with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "expected_slice_id"):
            build_ordinary_t2_evidence_lineage(
                lineage_packet=self.lineage,
                source_records=self.source_records,
                evidence_records=self.evidence,
                expected_slice_id=" \t\u2003 ",
            )

        bad_lineage = copy.deepcopy(self.lineage)
        bad_lineage["slice_id"] = " \t\u2003 "
        with self.assertRaises(OrdinaryT2EvidenceLineageError):
            build_ordinary_t2_evidence_lineage(
                lineage_packet=bad_lineage,
                source_records=self.source_records,
                evidence_records=self.evidence,
                expected_slice_id=self.slice_id,
            )

        packet = self.build()
        with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "expected_slice_id"):
            validate_ordinary_t2_evidence_lineage(
                packet=packet,
                lineage_packet=self.lineage,
                source_records=self.source_records,
                evidence_records=self.evidence,
                expected_slice_id=" \t\u2003 ",
            )
        packet["slice_id"] = " \t\u2003 "
        with self.assertRaisesRegex(OrdinaryT2EvidenceLineageError, "slice_id"):
            validate_ordinary_t2_evidence_lineage(
                packet=packet,
                lineage_packet=self.lineage,
                source_records=self.source_records,
                evidence_records=self.evidence,
                expected_slice_id=self.slice_id,
            )

    def test_validator_malformed_roots_and_evidence_records_use_domain_error(self):
        packet = self.build()
        for bad_packet in (None, []):
            with self.subTest(packet=bad_packet):
                with self.assertRaises(OrdinaryT2EvidenceLineageError):
                    validate_ordinary_t2_evidence_lineage(
                        packet=bad_packet,
                        lineage_packet=self.lineage,
                        source_records=self.source_records,
                        evidence_records=self.evidence,
                        expected_slice_id=self.slice_id,
                    )

        with self.assertRaises(OrdinaryT2EvidenceLineageError):
            validate_ordinary_t2_evidence_lineage(
                packet=packet,
                lineage_packet=None,
                source_records=self.source_records,
                evidence_records=self.evidence,
                expected_slice_id=self.slice_id,
            )

        for bad_evidence_records in (None, {}, "evidence", []):
            with self.subTest(evidence_records=bad_evidence_records):
                with self.assertRaises(OrdinaryT2EvidenceLineageError):
                    validate_ordinary_t2_evidence_lineage(
                        packet=packet,
                        lineage_packet=self.lineage,
                        source_records=self.source_records,
                        evidence_records=bad_evidence_records,
                        expected_slice_id=self.slice_id,
                    )


if __name__ == "__main__":
    unittest.main()

