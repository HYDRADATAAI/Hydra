from __future__ import annotations

import copy
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
        self.assertTrue(left["ordinary_current_source_set_ready"])
        self.assertFalse(left["strict_historical_replay_ready"])
        validate_replay_lineage_packet(packet=left, registry=self.registry)

    def test_as_of_selection_enforces_no_lookahead(self):
        packet = build_replay_lineage_packet(
            attestation=self.attestation,
            registry=self.registry,
        )
        before = select_replay_members(
            packet=packet,
            registry=self.registry,
            as_of="2026-09-26T12:59:59Z",
        )
        first = select_replay_members(
            packet=packet,
            registry=self.registry,
            as_of="2026-09-26T13:00:00Z",
        )
        both = select_replay_members(
            packet=packet,
            registry=self.registry,
            as_of="2026-09-26T13:01:00Z",
        )
        self.assertEqual([], before)
        self.assertEqual(["SRC-A"], [row["source_id"] for row in first])
        self.assertEqual(["SRC-A", "SRC-B"], [row["source_id"] for row in both])

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
        with self.assertRaisesRegex(ReplayLineageError, "all sources must be ordinary-T2 eligible"):
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


if __name__ == "__main__":
    unittest.main()
