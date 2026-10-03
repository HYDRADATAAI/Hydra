from __future__ import annotations

import json
import copy
import hashlib
import importlib.util
import re
import subprocess
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


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
TIMESTAMP_VALIDATOR_SUCCESSOR = ROOT / "docs/constraint/validation/HYDRA_CONSTRAINT_T1_TIMESTAMP_VALIDATOR_SUCCESSOR_V001_20260927.json"

PUBLIC_HASH_SUCCESSOR = ROOT / "docs/constraint/validation/HYDRA_CONSTRAINT_T1_BATCH018_PUBLIC_HASH_SUCCESSOR_V001_20260928.json"

_custody_spec = importlib.util.spec_from_file_location(
    "batch033_custody_pin_guard", Path(__file__).with_name("_batch033_custody_continuation.py"))
_custody_continuation = importlib.util.module_from_spec(_custody_spec)
_custody_spec.loader.exec_module(_custody_continuation)


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

    def _public_hash_predecessor_bytes(self):
        # This exact continuation records the PR109 public metadata repair.
        # Reverse only its five fixed substitutions to recover the historical
        # bytes; current and predecessor whole-file digests must both match.
        expected = {
            "schema": "HYDRA_CONSTRAINT_T1_BATCH018_PUBLIC_HASH_SUCCESSOR_V1",
            "scope": "THREE_PUBLIC_SHA256_REFERENCES_AND_TWO_MANIFEST_BLOB_BINDINGS",
            "donor_commit": "0db6181f332f3219372553442e0646ffecb78942",
            "historical_base_commit": "684f59ceea89114f6ac8b356e9b4dfb2b9cafa89",
            "timestamp_validator_record": "docs/constraint/validation/HYDRA_CONSTRAINT_T1_TIMESTAMP_VALIDATOR_SUCCESSOR_V001_20260927.json",
            "timestamp_validator_record_sha256": "a2e7fcbb185ac7fbb89da3f8b919519322286487e0070a309b02aac186fb5d9f",
            "historical_predecessor_bytes_recoverable_exactly": True,
            "public_hash_metadata_rewritten": True,
            "attestation_rewritten": False,
            "source_members_rewritten": False,
            "release_identity_rewritten": False,
            "timestamp_validator_record_rewritten": False,
            "trusted_timestamp_verifier": "NOT_IMPLEMENTED",
            "ordinary_replay_promoted": False,
            "historical_availability_promoted": False,
            "canonical_admission_promoted": False,
            "acceptance_effect": "NONE",
            "transitions": [
                {
                    "path": "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_HASH_INVENTORY_V001_20260926.json",
                    "predecessor_sha256": "c42cc9252a1c540032442141f3356c83f674e2631de50a46cd0f354361ed252d",
                    "successor_sha256": "3b169a75ea846673f33939270ff6d1700d1fc5159446490c81ae26357195e531",
                    "predecessor_git_blob_sha": "245746d059cf4000f5b3fd465fe004b9b8d5bd76",
                    "successor_git_blob_sha": "75b640792e95a18de5b0cf0bdf674a12edb241e0",
                    "replacements": [
                        {
                            "before": "74e3b4ef710f1da8910d5588882cfa0672b59f93e8636ce902e3fa34237ad05e",
                            "after": "fe68784920a6b5437457792fc0c2cd410269f991be76ad85cff766e8df84d81b"
                        }
                    ]
                },
                {
                    "path": "docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_MATERIALIZATION_STATUS_V001_20260926.json",
                    "predecessor_sha256": "8137cd3aaf079d409bd34c68b6892b2d18e7a6e66592be9f7bee16aab991bfa7",
                    "successor_sha256": "049152fe7cf510ea3ffb2469e5f7117b4b879b425535c88a9bd04c82a91ed937",
                    "predecessor_git_blob_sha": "083f83ccf8729e503c74c437bf2db73ccbc9e483",
                    "successor_git_blob_sha": "114e3488e7ce8dded96a3f5b55cedabafe2cb421",
                    "replacements": [
                        {
                            "before": "74e3b4ef710f1da8910d5588882cfa0672b59f93e8636ce902e3fa34237ad05e",
                            "after": "fe68784920a6b5437457792fc0c2cd410269f991be76ad85cff766e8df84d81b"
                        },
                        {
                            "before": "82bde12a0715938d873cb7b9222c7d83d82992b9c1ee12438a6d5180a56fb3de",
                            "after": "3b169a75ea846673f33939270ff6d1700d1fc5159446490c81ae26357195e531"
                        }
                    ]
                },
                {
                    "path": "docs/constraint/validation/HYDRA_CONSTRAINT_FIRST_SLICE_THREAD6_SUCCESSOR_BATCH018_ARTIFACT_MANIFEST_V001_20260926.json",
                    "predecessor_sha256": "6b1b2aac10077dde2ceffbd155419d52c228b3f35a4f3039316fe289339812bd",
                    "successor_sha256": "bcf73e2977654aff87e34cd629089f59e7a41ae282c697e079257c3bdb06208b",
                    "predecessor_git_blob_sha": "28d5abdbdb1941f4227c90f747c91787d5d257c0",
                    "successor_git_blob_sha": "4cfd44eb9362fafd18680501327b70d446a38273",
                    "replacements": [
                        {
                            "before": "245746d059cf4000f5b3fd465fe004b9b8d5bd76",
                            "after": "75b640792e95a18de5b0cf0bdf674a12edb241e0"
                        },
                        {
                            "before": "083f83ccf8729e503c74c437bf2db73ccbc9e483",
                            "after": "114e3488e7ce8dded96a3f5b55cedabafe2cb421"
                        }
                    ]
                }
            ]
        }
        self.assertEqual(json.dumps(expected, sort_keys=True),
                         json.dumps(load(PUBLIC_HASH_SUCCESSOR), sort_keys=True))
        self.assertEqual(expected["timestamp_validator_record_sha256"],
                         hashlib.sha256(TIMESTAMP_VALIDATOR_SUCCESSOR.read_bytes()).hexdigest())
        historical = {}
        for transition in expected["transitions"]:
            path = ROOT / transition["path"]
            current = path.read_bytes()
            if path == ARTIFACT_MANIFEST:
                current = _custody_continuation.recover_predecessor_bytes(path, current)
            self.assertEqual(transition["successor_sha256"], hashlib.sha256(current).hexdigest(), str(path))
            current_blob = hashlib.sha1(b"blob " + str(len(current)).encode() + b"\0" + current).hexdigest()
            self.assertEqual(transition["successor_git_blob_sha"], current_blob, str(path))
            prior = current
            for edit in transition["replacements"]:
                old, new = edit["before"].encode("ascii"), edit["after"].encode("ascii")
                self.assertEqual(1, prior.count(new), str(path))
                prior = prior.replace(new, old, 1)
            self.assertEqual(transition["predecessor_sha256"], hashlib.sha256(prior).hexdigest(), str(path))
            prior_blob = hashlib.sha1(b"blob " + str(len(prior)).encode() + b"\0" + prior).hexdigest()
            self.assertEqual(transition["predecessor_git_blob_sha"], prior_blob, str(path))
            historical[path] = prior
        return historical

    def _timestamp_validator_continuation(self):
        expected = {
            "schema": "HYDRA_CONSTRAINT_T1_TIMESTAMP_VALIDATOR_SUCCESSOR_V1",
            "scope": "EXACT_TIMESTAMP_VALIDATOR_CONTINUATION",
            "base_commit": "684f59ceea89114f6ac8b356e9b4dfb2b9cafa89",
            "historical_manifest": "docs/constraint/validation/HYDRA_CONSTRAINT_FIRST_SLICE_THREAD6_SUCCESSOR_BATCH018_ARTIFACT_MANIFEST_V001_20260926.json",
            "historical_manifest_sha256": "6b1b2aac10077dde2ceffbd155419d52c228b3f35a4f3039316fe289339812bd",
            "predecessor_artifacts_rewritten": False,
            "acceptance_effect": "NONE",
            "trusted_timestamp_verifier": "NOT_IMPLEMENTED",
            "ordinary_replay_promoted": False,
            "historical_availability_promoted": False,
            "canonical_admission_promoted": False,
            "network_acquisition_authorized": False,
            "transition": {
                "path": "tools/validate_constraint_first_slice_successor.py",
                "predecessor_git_blob_sha": "43f81e4a2e0e0aa3e4f58140b4b54e97b2c0c676",
                "successor_git_blob_sha": "44bfe9c51cb5a3013d7a1a0bec9f79b1adcb9a73",
            },
        }
        # Exact JSON types and fields matter; neither observed bytes nor a
        # self-edited record can nominate a different successor.
        self.assertEqual(json.dumps(expected, sort_keys=True),
                         json.dumps(load(TIMESTAMP_VALIDATOR_SUCCESSOR), sort_keys=True))
        self.assertEqual(expected["historical_manifest_sha256"],
                         hashlib.sha256(self._public_hash_predecessor_bytes()[ARTIFACT_MANIFEST]).hexdigest())
        return expected["transition"]

    def test_successor_artifact_manifest_binds_committed_blob_contents(self):
        continuation = self._timestamp_validator_continuation()
        for artifact in self.artifact_manifest.get("superseded_artifacts", []):
            actual = subprocess.check_output(["git", "hash-object", str(ROOT / artifact["path"])], cwd=ROOT, text=True).strip()
            if artifact["path"] == continuation["path"]:
                self.assertEqual(artifact["successor_git_blob_sha"], continuation["predecessor_git_blob_sha"])
                self.assertEqual(actual, continuation["successor_git_blob_sha"], artifact["path"])
            else:
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

    def test_public_hash_continuation_rejects_record_drift(self):
        original = load
        mutations = [
            lambda d: d.update(donor_commit="0" * 40),
            lambda d: d.update(timestamp_validator_record_sha256="0" * 64),
            lambda d: d.update(attestation_rewritten=True),
            lambda d: d.update(source_members_rewritten=True),
            lambda d: d.update(release_identity_rewritten=True),
            lambda d: d.update(timestamp_validator_record_rewritten=True),
            lambda d: d.update(trusted_timestamp_verifier="IMPLEMENTED"),
            lambda d: d.update(ordinary_replay_promoted=True),
            lambda d: d.update(historical_availability_promoted=True),
            lambda d: d.update(canonical_admission_promoted=True),
            lambda d: d.update(ordinary_replay_promoted=0),
            lambda d: d.update(acceptance_effect="PASS"),
            lambda d: d.update(owner_signature="self-asserted"),
            lambda d: d["transitions"].pop(),
            lambda d: d["transitions"].append(copy.deepcopy(d["transitions"][0])),
            lambda d: d["transitions"][0].update(path="../another-artifact.json"),
            lambda d: d["transitions"][0].update(predecessor_sha256="0" * 64),
            lambda d: d["transitions"][0].update(successor_sha256="0" * 64),
            lambda d: d["transitions"][0]["replacements"][0].update(before="0" * 64),
            lambda d: d["transitions"][0]["replacements"][0].update(after="0" * 64),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                doc = original(PUBLIC_HASH_SUCCESSOR)
                mutate(doc)
                with patch(__name__ + ".load", side_effect=lambda p: doc if p == PUBLIC_HASH_SUCCESSOR else original(p)):
                    with self.assertRaises(AssertionError):
                        self._public_hash_predecessor_bytes()

    def test_public_hash_continuation_rejects_current_artifact_drift(self):
        original = Path.read_bytes
        for target in (INVENTORY, STATUS, ARTIFACT_MANIFEST, TIMESTAMP_VALIDATOR_SUCCESSOR):
            with self.subTest(path=target.relative_to(ROOT).as_posix()):
                with patch.object(Path, "read_bytes", lambda p: original(p) + b" " if p == target else original(p)):
                    with self.assertRaises(AssertionError):
                        self._public_hash_predecessor_bytes()

    def test_public_hash_continuation_rejects_coordinated_artifact_and_record_repin(self):
        original_load, original_bytes = load, Path.read_bytes
        for target in (INVENTORY, STATUS, ARTIFACT_MANIFEST):
            with self.subTest(path=target.relative_to(ROOT).as_posix()):
                data = original_bytes(target) + b" "
                doc = original_load(PUBLIC_HASH_SUCCESSOR)
                transition = next(row for row in doc["transitions"] if row["path"] == target.relative_to(ROOT).as_posix())
                transition["successor_sha256"] = hashlib.sha256(data).hexdigest()
                transition["successor_git_blob_sha"] = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                with patch.object(Path, "read_bytes", lambda p: data if p == target else original_bytes(p)):
                    with patch(__name__ + ".load", side_effect=lambda p: doc if p == PUBLIC_HASH_SUCCESSOR else original_load(p)):
                        with self.assertRaises(AssertionError):
                            self._public_hash_predecessor_bytes()

    def test_timestamp_validator_continuation_rejects_record_drift(self):
        original = load
        changes = [
            lambda d: d["transition"].update(path="../another-validator.py"),
            lambda d: d["transition"].update(predecessor_git_blob_sha="0" * 40),
            lambda d: d["transition"].update(successor_git_blob_sha="0" * 40),
            lambda d: d.update(historical_manifest_sha256="0" * 64),
            lambda d: d.update(predecessor_artifacts_rewritten=True),
            lambda d: d.update(acceptance_effect="PASS"),
            lambda d: d.update(trusted_timestamp_verifier="IMPLEMENTED"),
            lambda d: d.update(ordinary_replay_promoted=True),
            lambda d: d.update(historical_availability_promoted=True),
            lambda d: d.update(canonical_admission_promoted=True),
            lambda d: d.update(network_acquisition_authorized=True),
            lambda d: d.update(ordinary_replay_promoted=0),
            lambda d: d.update(owner_signature="self-asserted"),
        ]
        for index, change in enumerate(changes):
            with self.subTest(mutation=index):
                doc = original(TIMESTAMP_VALIDATOR_SUCCESSOR); change(doc)
                with patch(__name__ + ".load", side_effect=lambda p: doc if p == TIMESTAMP_VALIDATOR_SUCCESSOR else original(p)):
                    with self.assertRaises(AssertionError):
                        self.test_successor_artifact_manifest_binds_committed_blob_contents()

    def test_timestamp_validator_continuation_rejects_source_drift(self):
        original = subprocess.check_output
        target = str(ROOT / "tools/validate_constraint_first_slice_successor.py")
        with patch.object(subprocess, "check_output", side_effect=lambda args, **kwargs: "0" * 40 if args[-1] == target else original(args, **kwargs)):
            with self.assertRaises(AssertionError):
                self.test_successor_artifact_manifest_binds_committed_blob_contents()

    def test_timestamp_validator_continuation_rejects_historical_repin(self):
        manifest = copy.deepcopy(self.artifact_manifest)
        row = next(r for r in manifest["superseded_artifacts"] if r["path"] == "tools/validate_constraint_first_slice_successor.py")
        row["successor_git_blob_sha"] = "44bfe9c51cb5a3013d7a1a0bec9f79b1adcb9a73"
        with patch.object(self, "artifact_manifest", manifest):
            with self.assertRaises(AssertionError):
                self.test_successor_artifact_manifest_binds_committed_blob_contents()

    def test_timestamp_validator_continuation_keeps_unrelated_bindings_strict(self):
        original = subprocess.check_output
        target = str(README)
        with patch.object(subprocess, "check_output", side_effect=lambda args, **kwargs: "0" * 40 if args[-1] == target else original(args, **kwargs)):
            with self.assertRaises(AssertionError):
                self.test_successor_artifact_manifest_binds_committed_blob_contents()


if __name__ == "__main__":
    unittest.main()
