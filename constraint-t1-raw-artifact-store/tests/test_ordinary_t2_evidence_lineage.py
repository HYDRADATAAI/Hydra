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


if __name__ == "__main__":
    unittest.main()
