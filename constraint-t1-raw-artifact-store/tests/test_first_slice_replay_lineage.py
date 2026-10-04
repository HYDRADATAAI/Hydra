from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_t1_raw.first_slice_materialization import materialize_capture_plan
from hydra_constraint_t1_raw.replay_lineage import (
    ReplayLineageError,
    build_replay_lineage_packet,
    select_replay_members,
    validate_replay_lineage_packet,
)


class FirstSliceReplayLineageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "public-repo"
        self.repo.mkdir()
        self.private = self.base / "private"
        self.captures = self.base / "captures"
        self.captures.mkdir()
        (self.captures / "a.html").write_bytes(b"<html>A</html>\n")
        (self.captures / "b.pdf").write_bytes(b"%PDF-synthetic-B\n")
        self.registry = {
            "slice_id": "SLICE-X",
            "sources": [
                {"source_id": "SRC-A", "url": "https://example.invalid/a"},
                {"source_id": "SRC-B", "url": "https://example.invalid/b"},
            ],
        }
        self.plan = {
            "schema_version": "hydra-constraint-first-slice-local-capture-plan/v1",
            "slice_id": "SLICE-X",
            "availability_mode": "ACQUISITION_TIME_CONSERVATIVE",
            "release_id": "REL-SLICE-X-001",
            "release_created_at": "2026-09-26T13:10:00Z",
            "captures": [
                {
                    "source_id": "SRC-A",
                    "source_version_id": "SV-A-001",
                    "input_file": str(self.captures / "a.html"),
                    "content_type": "text/html",
                    "source_locator": "https://example.invalid/a",
                    "acquired_at": "2026-09-26T13:00:00Z",
                    "processing_disposition": "ELIGIBLE",
                },
                {
                    "source_id": "SRC-B",
                    "source_version_id": "SV-B-001",
                    "input_file": str(self.captures / "b.pdf"),
                    "content_type": "application/pdf",
                    "source_locator": "https://example.invalid/b",
                    "acquired_at": "2026-09-26T13:01:00Z",
                    "processing_disposition": "ELIGIBLE",
                },
            ],
        }
        self.attestation = materialize_capture_plan(
            registry=self.registry,
            plan=self.plan,
            private_root=self.private,
            public_repo_root=self.repo,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_packet_is_deterministic_and_preserves_exact_source_versions(self):
        left = build_replay_lineage_packet(
            attestation=self.attestation,
            registry=self.registry,
        )
        right = build_replay_lineage_packet(
            attestation=self.attestation,
            registry=self.registry,
        )
        self.assertEqual(left, right)
        self.assertEqual(2, left["source_count"])
        self.assertTrue(left["ordinary_source_version_hash_lineage_complete"])
        self.assertFalse(left["ordinary_current_source_set_ready"])
        self.assertFalse(left["strict_historical_replay_ready"])
        self.assertEqual(["SV-A-001", "SV-B-001"], [row["source_version_id"] for row in left["members"]])
        for packet_member, receipt_member in zip(left["members"], self.attestation["members"]):
            for field in ("artifact_sha256", "receipt_sha256", "acquired_at", "available_at"):
                self.assertEqual(receipt_member[field], packet_member[field])
        self.assertTrue(all(row["eligible_source_ids"] == [] for row in left["availability_boundaries"]))
        validate_replay_lineage_packet(packet=left, registry=self.registry)

    def test_as_of_selection_enforces_no_lookahead(self):
        packet = build_replay_lineage_packet(
            attestation=self.attestation,
            registry=self.registry,
        )
        self.assertEqual(
            ["2026-09-26T13:00:00Z", "2026-09-26T13:01:00Z"],
            [row["as_of"] for row in packet["availability_boundaries"]],
        )
        for cutoff in ("2026-09-26T12:59:59Z", "2026-09-26T13:00:00Z",
                       "2026-09-26T13:01:00Z", "2099-01-01T00:00:00Z"):
            with self.subTest(cutoff=cutoff), self.assertRaisesRegex(ReplayLineageError, "TIMESTAMP_UNVERIFIED"):
                select_replay_members(packet=packet, registry=self.registry, as_of=cutoff)

    def test_quarantined_source_blocks_replay_lineage_completion(self):
        plan = copy.deepcopy(self.plan)
        plan["release_id"] = "REL-SLICE-X-Q"
        plan["captures"][1]["processing_disposition"] = "QUARANTINED"
        private = self.base / "private-q"
        attestation = materialize_capture_plan(
            registry=self.registry,
            plan=plan,
            private_root=private,
            public_repo_root=self.repo,
        )
        with self.assertRaisesRegex(ReplayLineageError, "ELIGIBLE disposition required"):
            build_replay_lineage_packet(
                attestation=attestation,
                registry=self.registry,
            )

    def test_packet_digest_tamper_is_rejected(self):
        packet = build_replay_lineage_packet(
            attestation=self.attestation,
            registry=self.registry,
        )
        packet["members"][0]["artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(ReplayLineageError, "packet digest mismatch"):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)

    def test_source_count_requires_an_exact_integer(self):
        packet = build_replay_lineage_packet(
            attestation=self.attestation,
            registry=self.registry,
        )
        packet["source_count"] = float(packet["source_count"])
        from hydra_constraint_t1_raw.replay_lineage import _packet_digest
        packet["packet_sha256"] = _packet_digest(packet)
        with self.assertRaisesRegex(ReplayLineageError, "source_count drifted"):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)

        one_source_registry = copy.deepcopy(self.registry)
        one_source_registry["sources"] = one_source_registry["sources"][:1]
        one_source_plan = copy.deepcopy(self.plan)
        one_source_plan["release_id"] = "REL-SLICE-X-ONE"
        one_source_plan["captures"] = one_source_plan["captures"][:1]
        one_source_attestation = materialize_capture_plan(
            registry=one_source_registry,
            plan=one_source_plan,
            private_root=self.base / "private-one-source",
            public_repo_root=self.repo,
        )
        one_source_packet = build_replay_lineage_packet(
            attestation=one_source_attestation,
            registry=one_source_registry,
        )
        one_source_packet["source_count"] = True
        one_source_packet["packet_sha256"] = _packet_digest(one_source_packet)
        with self.assertRaisesRegex(ReplayLineageError, "source_count drifted"):
            validate_replay_lineage_packet(
                packet=one_source_packet,
                registry=one_source_registry,
            )

    def test_packet_validator_rejects_non_mapping_roots(self):
        packet = build_replay_lineage_packet(
            attestation=self.attestation,
            registry=self.registry,
        )
        with self.assertRaisesRegex(ReplayLineageError, "packet object required"):
            validate_replay_lineage_packet(packet=None, registry=self.registry)
        with self.assertRaisesRegex(ReplayLineageError, "registry object required"):
            validate_replay_lineage_packet(packet=packet, registry=None)

    def test_replay_builder_rejects_non_mapping_roots(self):
        with self.assertRaisesRegex(ReplayLineageError, "attestation object required"):
            build_replay_lineage_packet(attestation=None, registry=self.registry)
        with self.assertRaisesRegex(ReplayLineageError, "registry object required"):
            build_replay_lineage_packet(attestation=self.attestation, registry=None)

    def test_packet_rejects_missing_root_field(self):
        packet = build_replay_lineage_packet(
            attestation=self.attestation,
            registry=self.registry,
        )
        required_root_fields = {
            "schema_version",
            "slice_id",
            "release_id",
            "release_sha256",
            "release_created_at",
            "availability_mode",
            "source_count",
            "ordinary_source_version_hash_lineage_complete",
            "ordinary_current_source_set_ready",
            "strict_historical_replay_ready",
            "historical_availability_backdated",
            "no_lookahead_rule",
            "historical_replay_blocker",
            "members",
            "availability_boundaries",
            "packet_sha256",
        }
        self.assertEqual(set(packet), required_root_fields)
        for field in sorted(required_root_fields):
            with self.subTest(field=field):
                incomplete = dict(packet)
                del incomplete[field]
                with self.assertRaises(ReplayLineageError) as raised:
                    validate_replay_lineage_packet(
                        packet=incomplete,
                        registry=self.registry,
                    )
                self.assertEqual(
                    str(raised.exception),
                    "replay-lineage root field set invalid",
                )

    def test_replay_does_not_drop_unverified_acquisition_status(self):
        from hydra_constraint_t1_raw.first_slice_materialization import FirstSliceMaterializationError
        bad = copy.deepcopy(self.attestation)
        bad["members"][0]["verification_status"] = "TIMESTAMP_UNVERIFIED"
        with self.assertRaises(FirstSliceMaterializationError):
            build_replay_lineage_packet(attestation=bad, registry=self.registry)

    def test_rehashed_packet_rejects_extra_authority_claim(self):
        from hydra_constraint_t1_raw.replay_lineage import _packet_digest
        packet = build_replay_lineage_packet(attestation=self.attestation, registry=self.registry)
        packet["canonical_admission_promoted"] = True
        packet["packet_sha256"] = _packet_digest(packet)
        with self.assertRaises(ReplayLineageError):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)

    def test_historical_replay_cannot_be_promoted(self):
        packet = build_replay_lineage_packet(
            attestation=self.attestation,
            registry=self.registry,
        )
        packet["strict_historical_replay_ready"] = True
        packet["packet_sha256"] = __import__("hashlib").sha256(
            __import__("json").dumps(
                {k: v for k, v in packet.items() if k != "packet_sha256"},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        with self.assertRaisesRegex(ReplayLineageError, "improperly promoted"):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)

    def test_self_declared_eligibility_cannot_reopen_the_builder(self):
        bad = copy.deepcopy(self.attestation)
        bad["all_sources_ordinary_t2_eligible"] = True
        bad["ordinary_t2_eligible_count"] = 2
        bad["ordinary_t2_blocked_count"] = 0
        for member in bad["members"]:
            member["ordinary_t2_eligible"] = True
        with self.assertRaisesRegex(ReplayLineageError, "TIMESTAMP_UNVERIFIED"):
            build_replay_lineage_packet(attestation=bad, registry=self.registry)

    def test_non_boolean_member_eligibility_cannot_reopen_the_builder(self):
        for value in (1, "true", None):
            bad = copy.deepcopy(self.attestation)
            bad["members"][0]["ordinary_t2_eligible"] = value
            with self.subTest(value=value), self.assertRaisesRegex(
                ReplayLineageError,
                "ordinary-T2 eligibility must be a boolean",
            ):
                build_replay_lineage_packet(attestation=bad, registry=self.registry)

    def test_rehashed_ready_claim_cannot_reopen_selection(self):
        from hydra_constraint_t1_raw.replay_lineage import _packet_digest
        packet = build_replay_lineage_packet(attestation=self.attestation, registry=self.registry)
        packet["ordinary_current_source_set_ready"] = True
        packet["packet_sha256"] = _packet_digest(packet)
        with self.assertRaisesRegex(ReplayLineageError, "TIMESTAMP_UNVERIFIED"):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)
        with self.assertRaisesRegex(ReplayLineageError, "TIMESTAMP_UNVERIFIED"):
            select_replay_members(packet=packet, registry=self.registry, as_of="2099-01-01T00:00:00Z")

    def test_rehashed_eligible_boundary_cannot_admit_sources(self):
        from hydra_constraint_t1_raw.replay_lineage import _packet_digest
        packet = build_replay_lineage_packet(attestation=self.attestation, registry=self.registry)
        packet["availability_boundaries"][-1]["eligible_source_ids"] = ["SRC-A", "SRC-B"]
        packet["packet_sha256"] = _packet_digest(packet)
        with self.assertRaisesRegex(ReplayLineageError, "eligibility must remain empty"):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)

    def test_rehashed_recorded_boundary_drift_is_rejected(self):
        from hydra_constraint_t1_raw.replay_lineage import _packet_digest
        packet = build_replay_lineage_packet(attestation=self.attestation, registry=self.registry)
        packet["availability_boundaries"][0]["as_of"] = "2000-01-01T00:00:00Z"
        packet["packet_sha256"] = _packet_digest(packet)
        with self.assertRaisesRegex(ReplayLineageError, "recorded availability boundary drifted"):
            validate_replay_lineage_packet(packet=packet, registry=self.registry)

    def test_cli_reports_non_admitting_lineage_without_claiming_readiness(self):
        registry = self.base / "registry.json"
        attestation = self.base / "attestation.json"
        output = self.base / "lineage.json"
        registry.write_text(json.dumps(self.registry), encoding="utf-8")
        attestation.write_text(json.dumps(self.attestation), encoding="utf-8")
        script = Path(__file__).resolve().parents[2] / "tools/build_constraint_t1_first_slice_replay_lineage.py"
        args = [sys.executable, "-I", "-B", str(script), "--registry", str(registry),
                "--attestation", str(attestation), "--output", str(output)]
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("ORDINARY_CURRENT_SOURCE_SET_READY=NO", result.stdout)
        self.assertNotIn("ORDINARY_CURRENT_SOURCE_SET_READY=YES", result.stdout)
        self.assertFalse(json.loads(output.read_text(encoding="utf-8"))["ordinary_current_source_set_ready"])
        blocked = subprocess.run(args + ["--as-of", "2099-01-01T00:00:00Z"],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(1, blocked.returncode)
        self.assertIn("TIMESTAMP_UNVERIFIED", blocked.stdout)
        self.assertNotIn("ORDINARY_CURRENT_SOURCE_SET_READY=YES", blocked.stdout)


if __name__ == "__main__":
    unittest.main()
