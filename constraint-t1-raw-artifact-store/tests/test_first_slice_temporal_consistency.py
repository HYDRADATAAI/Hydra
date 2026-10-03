from __future__ import annotations

import copy
import hashlib
import json
import unittest
from datetime import datetime

from hydra_constraint_t1_raw.first_slice_materialization import (
    ATTESTATION_SCHEMA,
    FirstSliceMaterializationError,
    validate_public_materialization_attestation,
)
from hydra_constraint_t1_raw.replay_lineage import (
    ReplayLineageError,
    build_replay_lineage_packet,
    select_replay_members,
    validate_replay_lineage_packet,
)
from hydra_constraint_t1_raw.store import build_release_manifest


class FirstSliceTemporalConsistencyTests(unittest.TestCase):
    """Synthetic public metadata checks; no acquisition or timestamp proof."""

    def setUp(self):
        self.registry = {
            "slice_id": "SLICE-TEMPORAL-CONSISTENCY",
            "sources": [
                {"source_id": "SRC-A", "url": "https://example.invalid/a"},
                {"source_id": "SRC-B", "url": "https://example.invalid/b"},
            ],
        }

    @staticmethod
    def _rebind_release(record):
        release = build_release_manifest(
            release_id=record["release_id"],
            created_at=record["release_created_at"],
            receipts=record["members"],
        )
        record["release_sha256"] = release["release_sha256"]

    @staticmethod
    def _rehash_packet(packet):
        payload = {key: value for key, value in packet.items() if key != "packet_sha256"}
        packet["packet_sha256"] = hashlib.sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()

    def _attestation(self, second_acquired_at="2026-09-26T13:01:00Z"):
        members = []
        for name, acquired_at, artifact_char, receipt_char in (
            ("A", "2026-09-26T13:00:00Z", "a", "b"),
            ("B", second_acquired_at, "c", "d"),
        ):
            members.append({
                "source_id": f"SRC-{name}",
                "source_version_id": f"SV-{name}-001",
                "artifact_sha256": artifact_char * 64,
                "receipt_sha256": receipt_char * 64,
                "byte_length": 1,
                "content_type": "text/plain",
                "acquired_at": acquired_at,
                "available_at": acquired_at,
                "processing_disposition": "ELIGIBLE",
                "ordinary_t2_eligible": True,
            })
        attestation = {
            "schema_version": ATTESTATION_SCHEMA,
            "slice_id": self.registry["slice_id"],
            "capture_mode": "OFFLINE_REVIEWED_LOCAL_BYTES",
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "network_acquisition_performed_by_materializer": False,
            "public_raw_content_published": False,
            "release_id": "REL-TEMPORAL-CONSISTENCY-001",
            "release_created_at": "2026-09-26T13:10:00Z",
            "registry_source_count": 2,
            "materialized_source_count": 2,
            "ordinary_t2_eligible_count": 2,
            "ordinary_t2_blocked_count": 0,
            "all_registry_sources_materialized": True,
            "all_sources_ordinary_t2_eligible": True,
            "strict_historical_replay_promoted": False,
            "historical_availability_backdated": False,
            "members": members,
        }
        self._rebind_release(attestation)
        return attestation

    def _early_release_attestation(self):
        attestation = self._attestation()
        attestation["release_created_at"] = "2026-09-26T13:00:30Z"
        self._rebind_release(attestation)
        return attestation

    def _early_release_packet(self):
        packet = build_replay_lineage_packet(
            attestation=self._attestation(), registry=self.registry,
        )
        packet["release_created_at"] = "2026-09-26T13:00:30Z"
        self._rebind_release(packet)
        self._rehash_packet(packet)
        return packet

    def test_public_attestation_rejects_rehashed_release_before_latest_acquisition(self):
        with self.assertRaisesRegex(FirstSliceMaterializationError, "release.*precede"):
            validate_public_materialization_attestation(
                attestation=self._early_release_attestation(), registry=self.registry,
            )

    def test_replay_builder_rejects_rehashed_release_before_latest_acquisition(self):
        with self.assertRaisesRegex(FirstSliceMaterializationError, "release.*precede"):
            build_replay_lineage_packet(
                attestation=self._early_release_attestation(), registry=self.registry,
            )

    def test_direct_replay_validator_rejects_rehashed_early_release(self):
        packet = self._early_release_packet()
        with self.assertRaisesRegex(ReplayLineageError, "release.*precede"):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)

    def test_replay_selector_rejects_rehashed_early_release(self):
        packet = self._early_release_packet()
        with self.assertRaisesRegex(ReplayLineageError, "release.*precede"):
            select_replay_members(
                packet=packet, registry=self.registry, as_of="2026-09-26T13:10:00Z",
            )

    def _noncanonical_boundaries_packet(self, *, remove_transition):
        packet = build_replay_lineage_packet(
            attestation=self._attestation(), registry=self.registry,
        )
        if remove_transition:
            packet["availability_boundaries"].pop(0)
        else:
            packet["availability_boundaries"].insert(1, {
                "as_of": "2026-09-26T13:00:30Z",
                "eligible_source_ids": ["SRC-A"],
            })
        self._rehash_packet(packet)
        return packet

    def test_direct_replay_validator_rejects_missing_availability_transition(self):
        packet = self._noncanonical_boundaries_packet(remove_transition=True)
        with self.assertRaisesRegex(ReplayLineageError, "availability boundar"):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)

    def test_replay_selector_rejects_missing_availability_transition(self):
        packet = self._noncanonical_boundaries_packet(remove_transition=True)
        with self.assertRaisesRegex(ReplayLineageError, "availability boundar"):
            select_replay_members(
                packet=packet, registry=self.registry, as_of="2026-09-26T13:10:00Z",
            )

    def test_direct_replay_validator_rejects_extra_availability_transition(self):
        packet = self._noncanonical_boundaries_packet(remove_transition=False)
        with self.assertRaisesRegex(ReplayLineageError, "availability boundar"):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)

    def test_replay_selector_rejects_extra_availability_transition(self):
        packet = self._noncanonical_boundaries_packet(remove_transition=False)
        with self.assertRaisesRegex(ReplayLineageError, "availability boundar"):
            select_replay_members(
                packet=packet, registry=self.registry, as_of="2026-09-26T13:10:00Z",
            )

    def _assert_one_instant_boundary(self, second_acquired_at):
        attestation = self._attestation(second_acquired_at)
        original_members = copy.deepcopy(attestation["members"])
        validate_public_materialization_attestation(
            attestation=attestation, registry=self.registry,
        )
        packet = build_replay_lineage_packet(
            attestation=attestation, registry=self.registry,
        )
        self.assertEqual(original_members, attestation["members"])
        expected_times = {
            row["source_id"]: (row["acquired_at"], row["available_at"])
            for row in original_members
        }
        actual_times = {
            row["source_id"]: (row["acquired_at"], row["available_at"])
            for row in packet["members"]
        }
        self.assertEqual(expected_times, actual_times)
        self.assertEqual(1, len(packet["availability_boundaries"]))
        boundary = packet["availability_boundaries"][0]
        self.assertEqual(
            datetime.fromisoformat("2026-09-26T13:00:00+00:00"),
            datetime.fromisoformat(boundary["as_of"].replace("Z", "+00:00")),
        )
        self.assertEqual(["SRC-A", "SRC-B"], boundary["eligible_source_ids"])
        validate_replay_lineage_packet(packet=packet, registry=self.registry)
        self.assertEqual([], select_replay_members(
            packet=packet, registry=self.registry, as_of="2026-09-26T12:59:59Z",
        ))
        self.assertEqual(["SRC-A", "SRC-B"], [row["source_id"] for row in select_replay_members(
            packet=packet, registry=self.registry, as_of="2026-09-26T13:00:00Z",
        )])
        self.assertFalse(packet["strict_historical_replay_ready"])
        self.assertFalse(packet["historical_availability_backdated"])

    def test_equivalent_offsets_form_one_boundary_and_preserve_member_literals(self):
        self._assert_one_instant_boundary("2026-09-26T09:00:00-04:00")

    def test_equivalent_fractional_spelling_forms_one_boundary_and_preserves_literals(self):
        self._assert_one_instant_boundary("2026-09-26T13:00:00.000000Z")

    def test_release_after_latest_acquisition_remains_valid(self):
        attestation = self._attestation()
        validate_public_materialization_attestation(
            attestation=attestation, registry=self.registry,
        )
        packet = build_replay_lineage_packet(attestation=attestation, registry=self.registry)
        validate_replay_lineage_packet(packet=packet, registry=self.registry)
        self.assertEqual(2, len(packet["availability_boundaries"]))
        self.assertFalse(packet["strict_historical_replay_ready"])

    def test_release_equal_to_latest_acquisition_in_another_offset_remains_valid(self):
        attestation = self._attestation()
        attestation["release_created_at"] = "2026-09-26T09:01:00-04:00"
        self._rebind_release(attestation)
        validate_public_materialization_attestation(
            attestation=attestation, registry=self.registry,
        )
        packet = build_replay_lineage_packet(attestation=attestation, registry=self.registry)
        validate_replay_lineage_packet(packet=packet, registry=self.registry)
        self.assertEqual(attestation["release_created_at"], packet["release_created_at"])


if __name__ == "__main__":
    unittest.main()
