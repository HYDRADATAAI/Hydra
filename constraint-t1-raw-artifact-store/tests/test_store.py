from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_t1_raw import (
    ImmutableRecordError,
    PublicRepositoryRootError,
    RawArtifactStore,
    build_release_manifest,
    is_ordinary_t2_eligible,
    validate_release_manifest,
)


class RawArtifactStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "public-repo"
        self.repo.mkdir()
        self.private_root = self.base / "private-hydra-raw"
        self.store = RawArtifactStore(self.private_root, public_repo_root=self.repo)
        self.when = "2026-09-25T23:52:01.573251Z"

    def tearDown(self):
        self.temp.cleanup()

    def persist(self, *, payload=b"synthetic-public-source-payload\n", version="SV-001", disposition="ELIGIBLE"):
        return self.store.persist(
            raw_bytes=payload,
            source_id="SRC-TEST-001",
            source_version_id=version,
            content_type="application/octet-stream",
            acquired_at=self.when,
            available_at=self.when,
            source_locator="synthetic://public-test/001",
            processing_disposition=disposition,
        )

    def test_private_root_inside_public_repo_is_rejected(self):
        with self.assertRaises(PublicRepositoryRootError):
            RawArtifactStore(self.repo / "raw", public_repo_root=self.repo)

    def test_persist_writes_content_addressed_immutable_bytes_and_receipt(self):
        receipt = self.persist()
        self.assertEqual((), self.store.validate_receipt(receipt))
        artifact = self.private_root / receipt["artifact_relpath"]
        self.assertTrue(artifact.is_file())
        self.assertEqual(b"synthetic-public-source-payload\n", artifact.read_bytes())

    def test_identical_replay_is_idempotent(self):
        left = self.persist()
        right = self.persist()
        self.assertEqual(left, right)

    def test_receipt_path_cannot_be_rewritten_for_same_version(self):
        self.persist(payload=b"first\n")
        with self.assertRaises(ImmutableRecordError):
            self.persist(payload=b"second\n")

    def test_corrupted_artifact_fails_integrity_validation(self):
        receipt = self.persist()
        artifact = self.private_root / receipt["artifact_relpath"]
        artifact.write_bytes(b"corrupted\n")
        self.assertIn("artifact_digest_mismatch", self.store.validate_receipt(receipt))

    def test_release_manifest_is_deterministic_and_membership_bound(self):
        r1 = self.persist(version="SV-001")
        r2 = self.store.persist(
            raw_bytes=b"second synthetic payload\n",
            source_id="SRC-TEST-002",
            source_version_id="SV-002",
            content_type="application/octet-stream",
            acquired_at=self.when,
            available_at=self.when,
            source_locator="synthetic://public-test/002",
        )
        left = build_release_manifest(release_id="REL-001", created_at=self.when, receipts=[r2, r1])
        right = build_release_manifest(release_id="REL-001", created_at=self.when, receipts=[r1, r2])
        self.assertEqual(left, right)
        self.assertEqual((), validate_release_manifest(left))
        self.assertTrue(is_ordinary_t2_eligible(receipt=r1, release_manifest=left, store=self.store))
        self.assertTrue(is_ordinary_t2_eligible(receipt=r2, release_manifest=left, store=self.store))

    def test_missing_manifest_membership_blocks_ordinary_t2_eligibility(self):
        receipt = self.persist()
        other = self.store.persist(
            raw_bytes=b"other\n",
            source_id="SRC-OTHER",
            source_version_id="SV-OTHER",
            content_type="application/octet-stream",
            acquired_at=self.when,
            available_at=self.when,
            source_locator="synthetic://other",
        )
        manifest = build_release_manifest(release_id="REL-OTHER", created_at=self.when, receipts=[other])
        self.assertFalse(is_ordinary_t2_eligible(receipt=receipt, release_manifest=manifest, store=self.store))

    def test_quarantine_blocks_ordinary_t2_eligibility(self):
        receipt = self.persist(disposition="QUARANTINED")
        manifest = build_release_manifest(release_id="REL-Q", created_at=self.when, receipts=[receipt])
        self.assertFalse(is_ordinary_t2_eligible(receipt=receipt, release_manifest=manifest, store=self.store))

    def test_receipt_tamper_is_detected(self):
        receipt = self.persist()
        tampered = json.loads(json.dumps(receipt))
        tampered["available_at"] = "2025-01-01T00:00:00Z"
        self.assertIn("receipt_digest_invalid", self.store.validate_receipt(tampered))


if __name__ == "__main__":
    unittest.main()
