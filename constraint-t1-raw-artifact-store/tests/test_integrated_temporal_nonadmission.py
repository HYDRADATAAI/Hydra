"""Integration regressions: synthetic metadata never grants authority.

Synthetic fixtures test combined containment and consistency; they provide
no historical acquisition or timestamp evidence.
"""

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


class IntegratedTemporalNonadmissionTests(unittest.TestCase):
    def setUp(self):
        self.registry = {
            "slice_id": "SYNTHETIC-INTEGRATED-TEMPORAL",
            "sources": [
                {"source_id": "SRC-A", "url": "https://example.invalid/a"},
                {"source_id": "SRC-B", "url": "https://example.invalid/b"},
            ],
        }

    @staticmethod
    def rebind_release(record):
        release = build_release_manifest(
            release_id=record["release_id"], created_at=record["release_created_at"],
            receipts=record["members"],
        )
        record["release_sha256"] = release["release_sha256"]

    @staticmethod
    def rehash_packet(packet):
        payload = {key: value for key, value in packet.items() if key != "packet_sha256"}
        packet["packet_sha256"] = hashlib.sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()

    def attestation(self, second_time="2026-09-26T13:01:00Z"):
        members = []
        for name, instant, artifact, receipt in (
            ("A", "2026-09-26T13:00:00Z", "a", "b"),
            ("B", second_time, "c", "d"),
        ):
            members.append({
                "source_id": "SRC-" + name, "source_version_id": "SV-" + name,
                "artifact_sha256": artifact * 64, "receipt_sha256": receipt * 64,
                "byte_length": 1, "content_type": "text/plain",
                "acquired_at": instant, "available_at": instant,
                "processing_disposition": "ELIGIBLE", "ordinary_t2_eligible": False,
            })
        attestation = {
            "schema_version": ATTESTATION_SCHEMA,
            "slice_id": self.registry["slice_id"],
            "capture_mode": "OFFLINE_REVIEWED_LOCAL_BYTES",
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "network_acquisition_performed_by_materializer": False,
            "public_raw_content_published": False,
            "release_id": "REL-SYNTHETIC-INTEGRATED-TEMPORAL",
            "release_created_at": "2026-09-26T13:10:00Z",
            "registry_source_count": 2, "materialized_source_count": 2,
            "ordinary_t2_eligible_count": 0, "ordinary_t2_blocked_count": 2,
            "all_registry_sources_materialized": True,
            "all_sources_ordinary_t2_eligible": False,
            "strict_historical_replay_promoted": False,
            "historical_availability_backdated": False,
            "members": members,
        }
        self.rebind_release(attestation)
        return attestation

    def packet(self, attestation=None):
        return build_replay_lineage_packet(
            attestation=self.attestation() if attestation is None else attestation,
            registry=self.registry,
        )

    def assert_blocked(self, packet):
        self.assertIs(packet["ordinary_current_source_set_ready"], False)
        self.assertIs(packet["strict_historical_replay_ready"], False)
        self.assertIs(packet["historical_availability_backdated"], False)
        self.assertTrue(all(
            boundary["eligible_source_ids"] == []
            for boundary in packet["availability_boundaries"]
        ))
        validate_replay_lineage_packet(packet=packet, registry=self.registry)
        for cutoff in (
            "2026-09-26T12:59:59Z", "2026-09-26T13:00:00Z",
            "2026-09-26T13:01:00Z", "2099-01-01T00:00:00Z",
        ):
            with self.subTest(cutoff=cutoff):
                with self.assertRaisesRegex(ReplayLineageError, "TIMESTAMP_UNVERIFIED"):
                    select_replay_members(packet=packet, registry=self.registry, as_of=cutoff)

    def assert_validator_and_selector_reject(self, packet, message):
        with self.assertRaisesRegex(ReplayLineageError, message):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)
        with self.assertRaisesRegex(ReplayLineageError, message):
            select_replay_members(
                packet=packet, registry=self.registry, as_of="2099-01-01T00:00:00Z",
            )

    def test_equal_instants_preserve_literals_empty_boundary_and_blocked_selection(self):
        for second_time in ("2026-09-26T09:00:00-04:00", "2026-09-26T13:00:00.000000Z"):
            with self.subTest(second_time=second_time):
                attestation = self.attestation(second_time)
                before = copy.deepcopy(attestation)
                packet = self.packet(attestation)
                self.assertEqual(before, attestation)
                self.assertEqual(1, len(packet["availability_boundaries"]))
                self.assertEqual(
                    datetime.fromisoformat("2026-09-26T13:00:00+00:00"),
                    datetime.fromisoformat(packet["availability_boundaries"][0]["as_of"].replace("Z", "+00:00")),
                )
                expected = {row["source_id"]: (row["acquired_at"], row["available_at"]) for row in before["members"]}
                observed = {row["source_id"]: (row["acquired_at"], row["available_at"]) for row in packet["members"]}
                self.assertEqual(expected, observed)
                self.assert_blocked(packet)

    def test_equal_instant_grouping_is_deterministic_under_member_order(self):
        attestation = self.attestation("2026-09-26T09:00:00-04:00")
        forward = self.packet(attestation)
        attestation["members"].reverse()
        self.rebind_release(attestation)
        self.registry["sources"].reverse()
        reverse = self.packet(attestation)
        self.assertEqual(forward, reverse)
        self.assert_blocked(reverse)

    def test_distinct_transitions_remain_nonadmitting(self):
        packet = self.packet()
        self.assertEqual(
            ["2026-09-26T13:00:00Z", "2026-09-26T13:01:00Z"],
            [row["as_of"] for row in packet["availability_boundaries"]],
        )
        self.assert_blocked(packet)

    def test_missing_transition_is_rejected_before_nonadmitting_selection(self):
        packet = self.packet()
        del packet["availability_boundaries"][0]
        self.rehash_packet(packet)
        self.assert_validator_and_selector_reject(packet, "availability boundar")

    def test_extra_empty_transition_is_rejected_before_nonadmitting_selection(self):
        packet = self.packet()
        packet["availability_boundaries"].insert(1, {
            "as_of": "2026-09-26T13:00:30Z", "eligible_source_ids": [],
        })
        self.rehash_packet(packet)
        self.assert_validator_and_selector_reject(packet, "availability boundar")

    def test_rehashed_early_release_cannot_pass_any_entry(self):
        attestation = self.attestation()
        attestation["release_created_at"] = "2026-09-26T13:00:30Z"
        self.rebind_release(attestation)
        for operation in (validate_public_materialization_attestation, build_replay_lineage_packet):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(FirstSliceMaterializationError, "release.*precede"):
                    operation(attestation=attestation, registry=self.registry)
        packet = self.packet()
        packet["release_created_at"] = "2026-09-26T13:00:30Z"
        self.rebind_release(packet)
        self.rehash_packet(packet)
        self.assert_validator_and_selector_reject(packet, "release.*precede")

    def test_equal_or_later_release_keeps_selection_blocked(self):
        for release_time in ("2026-09-26T09:01:00-04:00", "2026-09-26T13:10:00Z"):
            with self.subTest(release_time=release_time):
                attestation = self.attestation()
                attestation["release_created_at"] = release_time
                self.rebind_release(attestation)
                validate_public_materialization_attestation(attestation=attestation, registry=self.registry)
                packet = self.packet(attestation)
                self.assertEqual(release_time, packet["release_created_at"])
                self.assert_blocked(packet)

    def test_rehashed_ready_claim_cannot_reopen_selection(self):
        packet = self.packet()
        packet["ordinary_current_source_set_ready"] = True
        self.rehash_packet(packet)
        self.assert_validator_and_selector_reject(packet, "TIMESTAMP_UNVERIFIED")

    def test_rehashed_nonempty_eligibility_cannot_admit_sources(self):
        packet = self.packet()
        packet["availability_boundaries"][-1]["eligible_source_ids"] = ["SRC-A", "SRC-B"]
        self.rehash_packet(packet)
        self.assert_validator_and_selector_reject(packet, "eligibility.*empty")

    def test_rehashed_authority_promotions_remain_rejected(self):
        for field in ("strict_historical_replay_ready", "historical_availability_backdated", "timestamp_verified"):
            with self.subTest(field=field):
                packet = self.packet()
                packet[field] = True
                self.rehash_packet(packet)
                self.assert_validator_and_selector_reject(packet, ".+")


if __name__ == "__main__":
    unittest.main()
