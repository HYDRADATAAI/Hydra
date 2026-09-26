from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_t1_raw import (
    ArtifactIntegrityError,
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
        persisted = self.store.write_release_manifest(
            release_id="REL-001",
            created_at=self.when,
            receipts=[r2, r1],
        )
        self.assertEqual(left, persisted)
        self.assertTrue(is_ordinary_t2_eligible(receipt=r1, release_manifest=persisted, store=self.store))
        self.assertTrue(is_ordinary_t2_eligible(receipt=r2, release_manifest=persisted, store=self.store))

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
        manifest = self.store.write_release_manifest(
            release_id="REL-OTHER",
            created_at=self.when,
            receipts=[other],
        )
        self.assertFalse(is_ordinary_t2_eligible(receipt=receipt, release_manifest=manifest, store=self.store))

    def test_quarantine_blocks_ordinary_t2_eligibility(self):
        receipt = self.persist(disposition="QUARANTINED")
        manifest = self.store.write_release_manifest(
            release_id="REL-Q",
            created_at=self.when,
            receipts=[receipt],
        )
        self.assertFalse(is_ordinary_t2_eligible(receipt=receipt, release_manifest=manifest, store=self.store))

    def test_receipt_tamper_is_detected(self):
        receipt = self.persist()
        tampered = json.loads(json.dumps(receipt))
        tampered["available_at"] = "2025-01-01T00:00:00Z"
        self.assertIn("receipt_digest_invalid", self.store.validate_receipt(tampered))

    def _record_digest(self, record):
        payload = {
            key: value
            for key, value in record.items()
            if key not in {"receipt_sha256", "release_sha256"}
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _symlink(self, link: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlinks unavailable: {exc}")

    def test_unpersisted_release_manifest_cannot_grant_ordinary_t2_eligibility(self):
        receipt = self.persist()
        fabricated = build_release_manifest(
            release_id="REL-FABRICATED",
            created_at=self.when,
            receipts=[receipt],
        )
        self.assertEqual((), validate_release_manifest(fabricated))
        self.assertIn(
            "release_record_missing",
            self.store.validate_stored_release_manifest(fabricated),
        )
        self.assertFalse(
            is_ordinary_t2_eligible(
                receipt=receipt,
                release_manifest=fabricated,
                store=self.store,
            )
        )

    def test_reconstructed_receipt_cannot_upgrade_quarantine_to_eligible(self):
        persisted_receipt = self.persist(disposition="QUARANTINED")
        forged = json.loads(json.dumps(persisted_receipt))
        forged["processing_disposition"] = "ELIGIBLE"
        forged["receipt_sha256"] = self._record_digest(forged)

        self.assertIn("receipt_record_mismatch", self.store.validate_receipt(forged))
        fabricated_release = build_release_manifest(
            release_id="REL-FORGED-UPGRADE",
            created_at=self.when,
            receipts=[forged],
        )
        self.assertFalse(
            is_ordinary_t2_eligible(
                receipt=forged,
                release_manifest=fabricated_release,
                store=self.store,
            )
        )
        with self.assertRaises(ArtifactIntegrityError):
            self.store.write_release_manifest(
                release_id="REL-FORGED-UPGRADE",
                created_at=self.when,
                receipts=[forged],
            )

    def test_release_with_same_id_but_unpersisted_membership_change_is_rejected(self):
        first = self.persist(version="SV-001")
        persisted = self.store.write_release_manifest(
            release_id="REL-STABLE",
            created_at=self.when,
            receipts=[first],
        )
        second = self.store.persist(
            raw_bytes=b"second synthetic payload\n",
            source_id="SRC-TEST-002",
            source_version_id="SV-002",
            content_type="application/octet-stream",
            acquired_at=self.when,
            available_at=self.when,
            source_locator="synthetic://public-test/002",
        )
        forged = build_release_manifest(
            release_id="REL-STABLE",
            created_at=self.when,
            receipts=[first, second],
        )
        self.assertEqual((), validate_release_manifest(forged))
        self.assertIn(
            "release_record_mismatch",
            self.store.validate_stored_release_manifest(forged),
        )
        self.assertTrue(
            is_ordinary_t2_eligible(
                receipt=first,
                release_manifest=persisted,
                store=self.store,
            )
        )
        self.assertFalse(
            is_ordinary_t2_eligible(
                receipt=second,
                release_manifest=forged,
                store=self.store,
            )
        )

    def test_missing_persisted_receipt_record_blocks_validation(self):
        receipt = self.persist()
        receipt_path = (
            self.private_root
            / "receipts"
            / receipt["source_id"]
            / f"{receipt['source_version_id']}.json"
        )
        receipt_path.unlink()
        self.assertIn("receipt_record_missing", self.store.validate_receipt(receipt))

    def test_symlinked_object_tree_into_public_repo_is_rejected(self):
        self._symlink(self.private_root / "objects", self.repo / "escaped-objects")
        with self.assertRaises(PublicRepositoryRootError):
            self.persist()
        self.assertEqual(list((self.repo / "escaped-objects").rglob("*.raw")), [])

    def test_symlinked_receipt_tree_into_public_repo_is_rejected(self):
        self._symlink(self.private_root / "receipts", self.repo / "escaped-receipts")
        with self.assertRaises(PublicRepositoryRootError):
            self.persist()
        self.assertEqual(list((self.repo / "escaped-receipts").rglob("*.json")), [])

    def test_symlinked_release_tree_into_public_repo_is_rejected(self):
        receipt = self.persist()
        self._symlink(self.private_root / "releases", self.repo / "escaped-releases")
        with self.assertRaises(PublicRepositoryRootError):
            self.store.write_release_manifest(
                release_id="REL-SYMLINK",
                created_at=self.when,
                receipts=[receipt],
            )
        self.assertEqual(list((self.repo / "escaped-releases").rglob("*.json")), [])

    def test_symlinked_object_tree_outside_private_root_is_rejected(self):
        self._symlink(self.private_root / "objects", self.base / "escaped-private-root")
        with self.assertRaises(PublicRepositoryRootError):
            self.persist()


if __name__ == "__main__":
    unittest.main()
