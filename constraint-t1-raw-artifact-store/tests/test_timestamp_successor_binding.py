"""Exact timestamp custody continuation; hostile changes never become authority."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "timestamp_successor_guard", ROOT / "tools/validate_constraint_first_slice_successor.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
PRIVATE_MAP = ROOT / "docs/constraint/validation/HYDRA_CONSTRAINT_BATCH017_T1_PRIVATE_RECORD_SUPERSESSION_MAP_V001_20260926.json"
STORE = "constraint-t1-raw-artifact-store/src/hydra_constraint_t1_raw/store.py"
TEST_STORE = "constraint-t1-raw-artifact-store/tests/test_store.py"


class TimestampSuccessorBindingTests(unittest.TestCase):
    def test_exact_continuation_preserves_original_and_previous_tips(self):
        rows = guard.load_supersessions(guard.CUSTODY_SUPERSESSION)
        expected = {
            STORE: ("c360aff06500ef19ac2f76e3b5efb9ef7debd90d",
                    "e6b8757b7dc24039d93caf33a26c8d0e3373ee63",
                    "5973067fdbe8b52b89fd22da53a6c7f67c5fa91a"),
            TEST_STORE: ("4a2bbd00189ac7b62f338cf7a21062f35ba1c31f",
                         "32a4116e6872ef5a844c6c5f7411423817b45de6",
                         "d94d1e7cdfd55e820fe531ddb2ede5ff54a89e5e"),
        }
        for relative, values in expected.items():
            with self.subTest(path=relative):
                self.assertEqual(values, tuple(rows[relative][key] for key in (
                    "predecessor_git_blob_sha", "intermediate_git_blob_sha", "successor_git_blob_sha")))

    def test_historical_custody_records_remain_byte_pinned(self):
        expected = {
            guard.CUSTODY_SUPERSESSION: "03e54ee2a1e0bbae2a7392ff2b274d10c1863dd494b75d41b7aa65eccb0a38d4",
            PRIVATE_MAP: "9f214731ff90b9690a3e25d730fe22ae275be988ce7bbd8edd252ec640eb8bbe",
        }
        for path, digest in expected.items():
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_hostile_timestamp_record_changes_are_rejected(self):
        original = guard.load_json
        mutations = [
            lambda d: d["transitions"].pop(),
            lambda d: d["transitions"].append(copy.deepcopy(d["transitions"][0])),
            lambda d: d["transitions"][0].update(path="../outside.py"),
            lambda d: d["transitions"][0].update(predecessor_git_blob_sha="0" * 40),
            lambda d: d["transitions"][0].update(successor_git_blob_sha="0" * 40),
            lambda d: d.update(base_commit="0" * 40),
            lambda d: d.update(scope="CANONICAL_ADMISSION"),
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
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                doc = original(guard.TIMESTAMP_SUPERSESSION)
                mutate(doc)
                with patch.object(guard, "load_json", side_effect=lambda p: doc if p == guard.TIMESTAMP_SUPERSESSION else original(p)):
                    with self.assertRaisesRegex(guard.ValidationFailure, "timestamp supersession record drifted"):
                        guard.load_supersessions(guard.CUSTODY_SUPERSESSION)

    def test_source_drift_cannot_be_accepted_by_an_unchanged_record(self):
        original = guard.git_blob_sha
        for relative in (STORE, TEST_STORE):
            with self.subTest(path=relative):
                with patch.object(guard, "git_blob_sha", side_effect=lambda p: "0" * 40 if p == ROOT / relative else original(p)):
                    with self.assertRaisesRegex(guard.ValidationFailure, "timestamp supersession successor mismatch"):
                        guard.load_supersessions(guard.CUSTODY_SUPERSESSION)

    def test_historical_private_pin_cannot_be_replaced_with_current_tip(self):
        original = guard.load_json
        for relative in (STORE, TEST_STORE):
            with self.subTest(path=relative):
                doc = original(PRIVATE_MAP)
                row = next(r for r in doc["transitions"] if r["path"] == relative)
                row["successor_git_blob_sha"] = guard.git_blob_sha(ROOT / relative)
                with patch.object(guard, "load_json", side_effect=lambda p: doc if p == PRIVATE_MAP else original(p)):
                    with self.assertRaisesRegex(guard.ValidationFailure, "private supersession successor mismatch"):
                        guard.load_supersessions(guard.CUSTODY_SUPERSESSION)

    def test_manifest_continuation_accepts_only_the_two_recorded_predecessors(self):
        rows = guard.load_supersessions(guard.CUSTODY_SUPERSESSION)
        manifest_path = ROOT / "test-only-manifest.json"
        for relative in (STORE, TEST_STORE):
            for key in ("predecessor_git_blob_sha", "intermediate_git_blob_sha"):
                manifest = {"artifacts": [{"path": relative, "git_blob_sha": rows[relative][key]}]}
                with patch.object(guard, "load_json", return_value=manifest):
                    self.assertEqual(1, guard.validate_manifest(manifest_path, supersessions=rows))
            manifest = {"artifacts": [{"path": relative, "git_blob_sha": "0" * 40}]}
            with patch.object(guard, "load_json", return_value=manifest):
                with self.assertRaisesRegex(guard.ValidationFailure, "custody supersession predecessor mismatch"):
                    guard.validate_manifest(manifest_path, supersessions=rows)

    def test_unrelated_manifest_drift_is_not_covered_by_timestamp_continuation(self):
        rows = guard.load_supersessions(guard.CUSTODY_SUPERSESSION)
        manifest = {"artifacts": [{"path": "tools/build_constraint_t1_first_slice_replay_lineage.py", "git_blob_sha": "0" * 40}]}
        with patch.object(guard, "load_json", return_value=manifest):
            with self.assertRaisesRegex(guard.ValidationFailure, "manifest blob mismatch without declared supersession"):
                guard.validate_manifest(ROOT / "test-only-manifest.json", supersessions=rows)

    def test_missing_timestamp_record_and_missing_history_are_rejected(self):
        with patch.object(guard, "TIMESTAMP_SUPERSESSION", ROOT / "absent-timestamp-record.json"):
            with self.assertRaisesRegex(guard.ValidationFailure, "required artifact missing"):
                guard.load_supersessions(guard.CUSTODY_SUPERSESSION)
        original = Path.is_file
        with patch.object(Path, "is_file", lambda p: False if p == PRIVATE_MAP else original(p)):
            with self.assertRaisesRegex(guard.ValidationFailure, "requires the historical private supersession map"):
                guard.load_supersessions(guard.CUSTODY_SUPERSESSION)


if __name__ == "__main__":
    unittest.main()
