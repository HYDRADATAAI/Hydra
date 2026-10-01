"""Hostile input tests: normalization must not erase unsupported authority.

Synthetic fixtures test rejection only; they establish no real timestamp.
"""

import copy
import unittest

from hydra_constraint_t1_raw.ordinary_t2_lineage import (
    OrdinaryT2LineageError, build_ordinary_t2_lineage,
    validate_ordinary_t2_lineage, select_ordinary_t2_members,
)
from hydra_constraint_t1_raw.ordinary_t2_evidence_lineage import (
    OrdinaryT2EvidenceLineageError, build_ordinary_t2_evidence_lineage,
    validate_ordinary_t2_evidence_lineage, select_ordinary_t2_evidence,
)


class TemporalInputBoundaryTests(unittest.TestCase):
    CLAIMS = {
        "acquisition_verification_status": "TIMESTAMP_UNVERIFIED",
        "timestamp_verified": True,
        "verified_acquired_at": "2026-09-01T00:00:00Z",
        "trusted_timestamp": {"verified": True, "root": "invented"},
        "temporal_authority": {"status": "CRYPTOGRAPHICALLY_VERIFIED"},
        "future_unrecognized_field": "must not silently disappear",
    }

    def setUp(self):
        self.sources = [{"source_id": "SRC-A", "source_version_id": "SV-A",
                         "source_locator": "https://example.invalid/a",
                         "processing_disposition": "ELIGIBLE",
                         "historical_backdating_authorized": False}]
        self.attestation = {
            "slice_id": "TEST", "release_id": "REL", "release_sha256": "a" * 64,
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "materialized_source_count": 1, "ordinary_t2_eligible_count": 1,
            "all_sources_ordinary_t2_eligible": True,
            "historical_availability_backdated": False,
            "strict_historical_replay_promoted": False,
            "public_raw_content_published": False, "private_paths_published": False,
            "members": [{**{k: self.sources[0][k] for k in (
                "source_id", "source_version_id", "source_locator")},
                "artifact_sha256": "b" * 64, "receipt_sha256": "c" * 64,
                "content_type": "text/html", "byte_length": 10,
                "acquired_at": "2026-09-28T12:00:00Z",
                "available_at": "2026-09-28T12:00:00Z",
                "ordinary_t2_eligible": True}],
        }
        self.evidence = [{"evidence_id": "EV-A", "source_id": "SRC-A",
                          "origin_artifact": "synthetic.json", "available_at": None}]
        self.lineage = self.build_source()
        self.binding = build_ordinary_t2_evidence_lineage(**self.evidence_args())

    def build_source(self):
        return build_ordinary_t2_lineage(attestation=self.attestation,
                                       source_records=self.sources, expected_slice_id="TEST")

    def source_args(self):
        return dict(packet=self.lineage, source_records=self.sources, expected_slice_id="TEST")

    def evidence_args(self):
        return dict(lineage_packet=self.lineage, source_records=self.sources,
                    evidence_records=self.evidence, expected_slice_id="TEST")

    def assert_claims_rejected(self, target, action, error):
        for field, value in self.CLAIMS.items():
            with self.subTest(field=field):
                target[field] = copy.deepcopy(value)
                try:
                    with self.assertRaises(error):
                        action()
                finally:
                    del target[field]

    def test_source_builder_rejects_unsupported_claims(self):
        self.assert_claims_rejected(self.sources[0], self.build_source, OrdinaryT2LineageError)

    def test_source_validator_rejects_unsupported_claims(self):
        self.assert_claims_rejected(self.sources[0],
            lambda: validate_ordinary_t2_lineage(**self.source_args()), OrdinaryT2LineageError)

    def test_source_selector_rejects_unsupported_claims(self):
        self.assert_claims_rejected(self.sources[0],
            lambda: select_ordinary_t2_members(**self.source_args(), as_of="2030-01-01T00:00:00Z"),
            OrdinaryT2LineageError)

    def test_attestation_builder_rejects_unsupported_claims(self):
        self.assert_claims_rejected(self.attestation, self.build_source, OrdinaryT2LineageError)

    def test_member_builder_rejects_unsupported_claims(self):
        self.assert_claims_rejected(self.attestation["members"][0], self.build_source, OrdinaryT2LineageError)

    def test_member_disposition_cannot_be_upgraded(self):
        for value in ("QUARANTINED", "BLOCKED", None, False):
            with self.subTest(disposition=value):
                self.attestation["members"][0]["processing_disposition"] = value
                with self.assertRaises(OrdinaryT2LineageError):
                    self.build_source()

    def test_explicit_eligible_member_is_compatible(self):
        self.attestation["members"][0]["processing_disposition"] = "ELIGIBLE"
        self.assertEqual(self.lineage, self.build_source())

    def test_source_negative_eligibility_cannot_disappear(self):
        self.sources[0]["ordinary_t2_eligible"] = False
        with self.assertRaises(OrdinaryT2LineageError):
            self.build_source()

    def test_evidence_builder_rejects_unsupported_claims(self):
        self.assert_claims_rejected(self.evidence[0],
            lambda: build_ordinary_t2_evidence_lineage(**self.evidence_args()),
            OrdinaryT2EvidenceLineageError)

    def test_evidence_validator_rejects_unsupported_claims(self):
        self.assert_claims_rejected(self.evidence[0],
            lambda: validate_ordinary_t2_evidence_lineage(packet=self.binding, **self.evidence_args()),
            OrdinaryT2EvidenceLineageError)

    def test_evidence_selector_rejects_unsupported_claims(self):
        self.assert_claims_rejected(self.evidence[0],
            lambda: select_ordinary_t2_evidence(packet=self.binding, **self.evidence_args(), as_of="2030-01-01T00:00:00Z"),
            OrdinaryT2EvidenceLineageError)

    def test_excluded_evidence_cannot_strip_claims(self):
        self.evidence.append({"evidence_id": "EV-OLD", "source_id": "SRC-OLD",
                              "origin_artifact": "synthetic.json"})
        self.binding = build_ordinary_t2_evidence_lineage(**self.evidence_args())
        for action in (
            lambda: build_ordinary_t2_evidence_lineage(**self.evidence_args()),
            lambda: validate_ordinary_t2_evidence_lineage(packet=self.binding, **self.evidence_args()),
        ):
            self.assert_claims_rejected(self.evidence[-1], action, OrdinaryT2EvidenceLineageError)

    def test_evidence_admission_claim_cannot_disappear(self):
        self.evidence[0]["canonical_evidence_admitted"] = True
        with self.assertRaises(OrdinaryT2EvidenceLineageError):
            build_ordinary_t2_evidence_lineage(**self.evidence_args())

    def test_existing_descriptive_metadata_is_compatible(self):
        self.sources[0].update(publication_date="2026-09-01", title="Synthetic source", roles=[])
        self.attestation.update(as_of="2026-09-28", record_id="SYNTHETIC")
        self.evidence[0].update(proposition="Synthetic claim", semantic_limit="NO_AUTHORITY", scope="TEST")
        self.assertEqual(self.lineage, self.build_source())
        self.assertEqual(self.binding, build_ordinary_t2_evidence_lineage(**self.evidence_args()))


if __name__ == "__main__":
    unittest.main()
