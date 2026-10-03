"""Synthetic consistency probes; these fixtures establish no trusted time."""

import copy
import unittest
from datetime import datetime

from hydra_constraint_t1_raw.ordinary_t2_lineage import (
    OrdinaryT2LineageError,
    build_ordinary_t2_lineage,
    select_ordinary_t2_members,
    validate_ordinary_t2_lineage,
)
from hydra_constraint_t1_raw.ordinary_t2_evidence_lineage import (
    OrdinaryT2EvidenceLineageError,
    build_ordinary_t2_evidence_lineage,
    select_ordinary_t2_evidence,
    validate_ordinary_t2_evidence_lineage,
)


class TemporalConsistencyBoundaryTests(unittest.TestCase):
    INVALID_REQUIRED_VALUES = (
        None, False, 0, "", [],
        {"acquisition_verification_status": "TIMESTAMP_UNVERIFIED"},
    )
    EQUIVALENT_SOURCE_TIMES = (
        ("2026-09-28T12:00:00Z", "2026-09-28T08:00:00-04:00"),
        ("2026-09-28T12:00:00Z", "2026-09-28T12:00:00.000Z"),
        ("2026-09-28T12:00:00.000000+00:00", "2026-09-28T12:00:00Z"),
    )
    EQUIVALENT_EVIDENCE_TIMES = (
        ("2026-09-28T13:00:00Z", "2026-09-28T09:00:00-04:00"),
        ("2026-09-28T13:00:00Z", "2026-09-28T13:00:00.000Z"),
        ("2026-09-28T13:00:00.000000+00:00", "2026-09-28T13:00:00Z"),
    )

    def setUp(self):
        self.sources = [
            {"source_id": "SRC-A", "source_version_id": "SV-A",
             "source_locator": "https://example.invalid/a",
             "processing_disposition": "ELIGIBLE",
             "historical_backdating_authorized": False},
            {"source_id": "SRC-B", "source_version_id": "SV-B",
             "source_locator": "https://example.invalid/b",
             "processing_disposition": "ELIGIBLE",
             "historical_backdating_authorized": False},
        ]
        self.attestation = {
            "slice_id": "SYNTHETIC", "release_id": "REL-SYNTHETIC",
            "release_sha256": "a" * 64,
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "materialized_source_count": 2, "ordinary_t2_eligible_count": 2,
            "all_sources_ordinary_t2_eligible": True,
            "historical_availability_backdated": False,
            "strict_historical_replay_promoted": False,
            "public_raw_content_published": False,
            "private_paths_published": False,
            "members": [
                {"source_id": source["source_id"],
                 "source_version_id": source["source_version_id"],
                 "source_locator": source["source_locator"],
                 "artifact_sha256": artifact * 64,
                 "receipt_sha256": receipt * 64,
                 "content_type": "text/html", "byte_length": 10,
                 "acquired_at": instant, "available_at": instant,
                 "ordinary_t2_eligible": True}
                for source, artifact, receipt, instant in (
                    (self.sources[0], "b", "c", "2026-09-28T12:00:00Z"),
                    (self.sources[1], "d", "e", "2026-09-28T12:01:00Z"),
                )
            ],
        }
        self.evidence = [
            {"evidence_id": "EV-A", "source_id": "SRC-A",
             "origin_artifact": "synthetic-a.json", "available_at": None},
            {"evidence_id": "EV-B", "source_id": "SRC-B",
             "origin_artifact": "synthetic-b.json", "available_at": None},
            {"evidence_id": "EV-OLD", "source_id": "SRC-EXCLUDED",
             "origin_artifact": "synthetic-old.json", "available_at": None},
        ]
        self.lineage = self.build_source(self.attestation)
        self.binding = build_ordinary_t2_evidence_lineage(**self.evidence_args())

    def build_source(self, attestation):
        return build_ordinary_t2_lineage(
            attestation=attestation, source_records=self.sources,
            expected_slice_id="SYNTHETIC",
        )

    def source_args(self, packet):
        return dict(packet=packet, source_records=self.sources,
                    expected_slice_id="SYNTHETIC")

    def evidence_args(self, evidence=None):
        return dict(lineage_packet=self.lineage, source_records=self.sources,
                    evidence_records=self.evidence if evidence is None else evidence,
                    expected_slice_id="SYNTHETIC")

    def assert_required_field_rejected(self, field, operation):
        for index, section in ((0, "bindings"), (2, "excluded_evidence")):
            for value in self.INVALID_REQUIRED_VALUES:
                with self.subTest(field=field, disposition=section, value=value):
                    evidence = copy.deepcopy(self.evidence)
                    packet = copy.deepcopy(self.binding)
                    evidence[index][field] = copy.deepcopy(value)
                    # Match the hostile input and output to probe value validation,
                    # rather than the separate input/output equality check.
                    packet[section][0][field] = copy.deepcopy(value)
                    args = self.evidence_args(evidence)
                    with self.assertRaises(OrdinaryT2EvidenceLineageError):
                        if operation == "build":
                            build_ordinary_t2_evidence_lineage(**args)
                        elif operation == "validate":
                            validate_ordinary_t2_evidence_lineage(packet=packet, **args)
                        else:
                            select_ordinary_t2_evidence(
                                packet=packet, **args, as_of="2026-09-28T12:02:00Z",
                            )

    def test_evidence_builder_rejects_invalid_source_id(self):
        self.assert_required_field_rejected("source_id", "build")

    def test_evidence_validator_rejects_invalid_source_id(self):
        self.assert_required_field_rejected("source_id", "validate")

    def test_evidence_selector_rejects_invalid_source_id(self):
        self.assert_required_field_rejected("source_id", "select")

    def test_evidence_builder_rejects_invalid_origin_artifact(self):
        self.assert_required_field_rejected("origin_artifact", "build")

    def test_evidence_validator_rejects_invalid_origin_artifact(self):
        self.assert_required_field_rejected("origin_artifact", "validate")

    def test_evidence_selector_rejects_invalid_origin_artifact(self):
        self.assert_required_field_rejected("origin_artifact", "select")

    def test_explicit_valid_receipt_count_cannot_be_discarded(self):
        for value in (0, 1, 3, True, False, 2.0, "2", None):
            with self.subTest(valid_receipt_count=value):
                attestation = copy.deepcopy(self.attestation)
                attestation["valid_receipt_count"] = value
                with self.assertRaises(OrdinaryT2LineageError):
                    self.build_source(attestation)
        # True == 1 in Python: matching cardinality must not admit a boolean.
        with self.subTest(valid_receipt_count=True, source_count=1):
            attestation = copy.deepcopy(self.attestation)
            attestation["members"] = attestation["members"][:1]
            attestation["materialized_source_count"] = 1
            attestation["ordinary_t2_eligible_count"] = 1
            attestation["valid_receipt_count"] = True
            with self.assertRaises(OrdinaryT2LineageError):
                build_ordinary_t2_lineage(
                    attestation=attestation, source_records=self.sources[:1],
                    expected_slice_id="SYNTHETIC",
                )

    def test_absent_or_consistent_valid_receipt_count_is_compatible(self):
        self.assertNotIn("valid_receipt_count", self.attestation)
        self.assertEqual(self.lineage, self.build_source(self.attestation))
        attestation = copy.deepcopy(self.attestation)
        attestation["valid_receipt_count"] = 2
        self.assertEqual(self.lineage, self.build_source(attestation))

    def assert_source_boundary_rejected(self, alteration, operation):
        packet = copy.deepcopy(self.lineage)
        if alteration == "missing":
            del packet["availability_boundaries"][0]
        else:
            packet["availability_boundaries"].insert(1, {
                "as_of": "2026-09-28T12:00:30Z", "eligible_source_ids": ["SRC-A"],
            })
        with self.assertRaises(OrdinaryT2LineageError):
            if operation == "validate":
                validate_ordinary_t2_lineage(**self.source_args(packet))
            else:
                select_ordinary_t2_members(
                    **self.source_args(packet), as_of="2026-09-28T12:02:00Z",
                )

    def assert_evidence_boundary_rejected(self, alteration, operation):
        packet = copy.deepcopy(self.binding)
        if alteration == "missing":
            del packet["availability_boundaries"][0]
        else:
            packet["availability_boundaries"].insert(1, {
                "as_of": "2026-09-28T12:00:30Z", "eligible_evidence_ids": ["EV-A"],
            })
        with self.assertRaises(OrdinaryT2EvidenceLineageError):
            if operation == "validate":
                validate_ordinary_t2_evidence_lineage(packet=packet, **self.evidence_args())
            else:
                select_ordinary_t2_evidence(
                    packet=packet, **self.evidence_args(), as_of="2026-09-28T12:02:00Z",
                )

    def test_source_validator_rejects_missing_availability_boundary(self):
        self.assert_source_boundary_rejected("missing", "validate")

    def test_source_selector_rejects_missing_availability_boundary(self):
        self.assert_source_boundary_rejected("missing", "select")

    def test_source_validator_rejects_extra_availability_boundary(self):
        self.assert_source_boundary_rejected("extra", "validate")

    def test_source_selector_rejects_extra_availability_boundary(self):
        self.assert_source_boundary_rejected("extra", "select")

    def test_evidence_validator_rejects_missing_availability_boundary(self):
        self.assert_evidence_boundary_rejected("missing", "validate")

    def test_evidence_selector_rejects_missing_availability_boundary(self):
        self.assert_evidence_boundary_rejected("missing", "select")

    def test_evidence_validator_rejects_extra_availability_boundary(self):
        self.assert_evidence_boundary_rejected("extra", "validate")

    def test_evidence_selector_rejects_extra_availability_boundary(self):
        self.assert_evidence_boundary_rejected("extra", "select")

    def test_source_builder_groups_equivalent_instants_without_rewriting_literals(self):
        for literals in self.EQUIVALENT_SOURCE_TIMES:
            with self.subTest(literals=literals):
                attestation = copy.deepcopy(self.attestation)
                for member, instant in zip(attestation["members"], literals):
                    member["acquired_at"] = instant
                    member["available_at"] = instant
                packet = self.build_source(attestation)
                self.assertEqual(1, len(packet["availability_boundaries"]))
                boundary = packet["availability_boundaries"][0]
                self.assertEqual(["SRC-A", "SRC-B"], boundary["eligible_source_ids"])
                self.assertEqual(
                    datetime.fromisoformat("2026-09-28T12:00:00+00:00"),
                    datetime.fromisoformat(boundary["as_of"].replace("Z", "+00:00")),
                )
                by_id = {row["source_id"]: row for row in packet["members"]}
                for source_id, instant in zip(("SRC-A", "SRC-B"), literals):
                    self.assertEqual(instant, by_id[source_id]["acquired_at"])
                    self.assertEqual(instant, by_id[source_id]["available_at"])

    def test_evidence_builder_groups_equivalent_instants_without_rewriting_literals(self):
        for literals in self.EQUIVALENT_EVIDENCE_TIMES:
            with self.subTest(literals=literals):
                evidence = copy.deepcopy(self.evidence)
                for record, instant in zip(evidence[:2], literals):
                    record["available_at"] = instant
                packet = build_ordinary_t2_evidence_lineage(**self.evidence_args(evidence))
                self.assertEqual(1, len(packet["availability_boundaries"]))
                boundary = packet["availability_boundaries"][0]
                self.assertEqual(["EV-A", "EV-B"], boundary["eligible_evidence_ids"])
                self.assertEqual(
                    datetime.fromisoformat("2026-09-28T13:00:00+00:00"),
                    datetime.fromisoformat(boundary["as_of"].replace("Z", "+00:00")),
                )
                by_id = {row["evidence_id"]: row for row in packet["bindings"]}
                for evidence_id, instant in zip(("EV-A", "EV-B"), literals):
                    self.assertEqual(instant, by_id[evidence_id]["reviewed_evidence_available_at"])
                    self.assertEqual(instant, by_id[evidence_id]["ordinary_t2_available_at"])


if __name__ == "__main__":
    unittest.main()
