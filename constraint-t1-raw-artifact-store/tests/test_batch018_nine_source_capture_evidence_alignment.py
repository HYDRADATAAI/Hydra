from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SLICE = ROOT / "docs" / "constraint" / "first_slice" / "ai_data_center_power_infrastructure_v1"
REGISTRY = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json"
INVENTORY = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_HASH_INVENTORY_V001_20260926.json"
STATUS = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_MATERIALIZATION_STATUS_V001_20260926.json"
BLOCKERS = SLICE / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BLOCKER_REGISTER_V001_20260926.json"
ATTESTATION = ROOT / "docs" / "constraint" / "validation" / "HYDRA_CONSTRAINT_BATCH018_T1_NINE_SOURCE_MATERIALIZATION_ATTESTATION_V001_20260926.json"
MASTER_STATUS = ROOT / "docs" / "constraint" / "architecture" / "HYDRA_CONSTRAINT_FIRST_SLICE_THREAD6_SUCCESSOR_BATCH018_MASTER_STATUS_V001_20260926.json"
ARTIFACT_MANIFEST = ROOT / "docs" / "constraint" / "validation" / "HYDRA_CONSTRAINT_FIRST_SLICE_THREAD6_SUCCESSOR_BATCH018_ARTIFACT_MANIFEST_V001_20260926.json"
PATH_AUTHORITY = ROOT / "docs" / "constraint" / "implementation" / "HYDRA_CONSTRAINT_T1_PRIVATE_RAW_STORE_PATH_AUTHORITY_V001_20260926.md"
RUNBOOK = ROOT / "docs" / "constraint" / "implementation" / "HYDRA_CONSTRAINT_AI_DATA_CENTER_POWER_INFRASTRUCTURE_PRIVATE_T1_MATERIALIZATION_RUNBOOK_V001_20260926.md"
README = ROOT / "constraint-t1-raw-artifact-store" / "README.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Batch018NineSourceCaptureEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load(REGISTRY)
        cls.inventory = load(INVENTORY)
        cls.status = load(STATUS)
        cls.blockers = load(BLOCKERS)
        cls.attestation = load(ATTESTATION)
        cls.master_status = load(MASTER_STATUS)
        cls.artifact_manifest = load(ARTIFACT_MANIFEST)

    def test_exact_registered_nine_sources_bind_to_persisted_attestation(self):
        expected = {row["source_id"]: row for row in self.registry["sources"]}
        inventory = {row["source_id"]: row for row in self.inventory["members"]}
        attested = {row["source_id"]: row for row in self.attestation["members"]}
        self.assertEqual(9, len(expected))
        self.assertEqual(set(expected), set(inventory))
        self.assertEqual(set(expected), set(attested))
        for source_id, source in expected.items():
            row = inventory[source_id]
            receipt = attested[source_id]
            self.assertEqual(source["url"], row["source_url"])
            self.assertEqual(row["source_version_id"], receipt["source_version_id"])
            self.assertEqual(row["artifact_sha256"], receipt["artifact_sha256"])
            self.assertEqual(row["receipt_sha256"], receipt["receipt_sha256"])
            self.assertEqual(row["byte_length"], receipt["byte_length"])
            self.assertEqual(row["content_type"], receipt["content_type"])
            self.assertTrue(receipt["ordinary_t2_eligible"], source_id)

    def test_hash_key_and_acquisition_time_are_reproducible(self):
        for row in self.inventory["members"]:
            digest = row["artifact_sha256"]
            self.assertRegex(digest, re.compile(r"^[0-9a-f]{64}$"))
            self.assertEqual(
                f"objects/sha256/{digest[:2]}/{digest[2:4]}/{digest}.raw",
                row["private_object_key"],
            )
            self.assertEqual(row["acquired_at"], row["available_at"])
            datetime.fromisoformat(row["acquired_at"].replace("Z", "+00:00"))
            self.assertEqual(200, row["http_status"])
            self.assertGreater(row["byte_length"], 0)
            self.assertTrue(row["capture_method"].startswith("PLAYWRIGHT_INSTALLED_"))

    def test_historical_availability_is_not_backdated_or_overclaimed(self):
        self.assertFalse(self.inventory["strict_historical_replay_promoted"])
        for row in self.inventory["members"]:
            evidence = row["historical_availability"]
            self.assertEqual("ACQUISITION_TIME_ONLY", evidence["status"])
            self.assertFalse(evidence["exact_pre_acquisition_available_at_proven"])
            self.assertFalse(evidence["strict_original_as_of_eligible"])
        self.assertEqual(
            "INSUFFICIENT_FOR_INTENDED_HISTORICAL_CUTOFFS",
            self.status["historical_availability"]["status"],
        )
        self.assertFalse(self.status["historical_availability"]["exact_pre_acquisition_source_version_availability_proven"])
        self.assertFalse(self.status["historical_availability"]["historical_backdating_performed"])

    def test_sanitized_inventory_contains_no_private_paths_or_raw_body_fields(self):
        encoded = json.dumps(self.inventory)
        for forbidden in ("D:\\\\HYDRA", "D:\\\\HYDRA_PRIVATE", "raw_bytes", "input_file", "private_root", "body_path"):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(self.inventory["raw_source_bodies_published"])
        self.assertEqual("HYDRA_CONSTRAINT_T1_RAW_STORE_V1", self.inventory["private_store_id"])

    def test_release_identity_and_scoped_blocker_status(self):
        self.assertEqual(self.attestation["release_id"], self.inventory["materialization_attestation"]["release_id"])
        self.assertEqual(self.attestation["release_sha256"], self.inventory["materialization_attestation"]["release_sha256"])
        self.assertTrue(self.inventory["all_exact_source_versions_resolve_to_persisted_receipt_and_release"])
        self.assertEqual("ALL_NINE_COMPLETE", self.blockers["source_version_hash_status"])
        blocking = {row["blocker_id"]: row for row in self.blockers["blocking_items"]}
        pit = blocking["PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION"]
        self.assertEqual("RAW_T1_MATERIALIZATION_COMPLETE_HISTORICAL_AVAILABILITY_EVIDENCE_INCOMPLETE", pit["state"])
        reconciliation = self.status["private_store_path_reconciliation"]
        self.assertTrue(reconciliation["stale_sibling_raw_subtree_removed"])
        self.assertFalse(reconciliation["stale_sibling_contents_admitted"])
        self.assertEqual(8, reconciliation["stale_objects_excluded_count"])

    def test_operational_path_docs_use_only_the_canonical_raw_root(self):
        authority = PATH_AUTHORITY.read_text(encoding="utf-8")
        runbook = RUNBOOK.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
        canonical = r"D:\HYDRA\_PRIVATE\constraint\raw"
        self.assertIn(canonical, authority)
        self.assertIn(canonical, runbook)
        self.assertIn(canonical, readme)
        self.assertNotIn(r"D:\HYDRA_PRIVATE\constraint\raw", runbook)
        self.assertNotIn(r"D:\HYDRA_PRIVATE\constraint\raw", readme)

    def test_master_status_keeps_historical_readiness_and_admission_blocked(self):
        readiness = self.master_status["readiness"]
        self.assertEqual("YES_9_OF_9_PRIVATE_T1", readiness["FIRST_SLICE_RAW_ARTIFACTS_MATERIALIZED"]["status"])
        self.assertEqual("NO", readiness["HISTORICAL_AVAILABILITY_READY"]["status"])
        self.assertEqual("NO", readiness["IMPLEMENTATION_ADMITTED"]["status"])
        self.assertFalse(self.master_status["t5_to_t6_admission_receipt_issued"])
        self.assertEqual("BLOCKED", self.master_status["first_serious_constraint_run"])


    def test_public_json_hash_references_bind_exact_committed_bytes(self):
        """Public file digests bind Git blob bytes, independent of checkout EOL."""
        self.assertEqual(
            ATTESTATION.relative_to(ROOT).as_posix(),
            self.inventory["materialization_attestation"]["repository_copy"],
        )
        self.assertEqual(
            INVENTORY.relative_to(ROOT).as_posix(),
            self.status["source_hash_inventory"]["path"],
        )
        references = (
            ("inventory.materialization_attestation.sha256",
             self.inventory["materialization_attestation"]["sha256"], ATTESTATION),
            ("status.materialization_attestation_sha256",
             self.status["materialization_attestation_sha256"], ATTESTATION),
            ("status.source_hash_inventory.sha256",
             self.status["source_hash_inventory"]["sha256"], INVENTORY),
        )
        for label, recorded_sha256, target in references:
            with self.subTest(reference=label):
                # Do not normalize newlines or accept a worktree serialization.
                # Private artifact, receipt and release digests are separate.
                committed_bytes = subprocess.check_output(
                    ["git", "cat-file", "blob",
                     f"HEAD:{target.relative_to(ROOT).as_posix()}"],
                    cwd=ROOT,
                )
                self.assertEqual(
                    hashlib.sha256(committed_bytes).hexdigest(),
                    recorded_sha256,
                    f"{label} must bind the exact committed public file bytes",
                )

    def test_successor_artifact_manifest_binds_committed_blob_contents(self):
        for artifact in self.artifact_manifest.get("superseded_artifacts", []):
            actual = subprocess.check_output(["git", "hash-object", str(ROOT / artifact["path"])], cwd=ROOT, text=True).strip()
            self.assertEqual(actual, artifact["successor_git_blob_sha"], artifact["path"])
        for artifact in self.artifact_manifest["artifacts"]:
            expected = subprocess.run(
                [
                    "git",
                    "hash-object",
                    f"--path={artifact['path']}",
                    str(ROOT / artifact["path"]),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(expected, artifact["git_blob_sha"], artifact["path"])


if __name__ == "__main__":
    unittest.main()
