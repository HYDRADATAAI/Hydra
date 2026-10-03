"""Hostile checks for the exact Batch033 source-metadata continuation."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "batch033_continuation_hostile", Path(__file__).with_name("_batch033_custody_continuation.py"))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class Batch033CustodyContinuationTests(unittest.TestCase):
    def test_exact_prior_byte_pins_are_preserved(self):
        expected = {
            "HYDRA_CONSTRAINT_T1_T2_PERSISTED_CUSTODY_SUPERSESSION_V001_20260926.json":
                "03e54ee2a1e0bbae2a7392ff2b274d10c1863dd494b75d41b7aa65eccb0a38d4",
            "HYDRA_CONSTRAINT_BATCH017_T1_PRIVATE_RECORD_SUPERSESSION_MAP_V001_20260926.json":
                "9f214731ff90b9690a3e25d730fe22ae275be988ce7bbd8edd252ec640eb8bbe",
            "HYDRA_CONSTRAINT_FIRST_SLICE_THREAD6_SUCCESSOR_BATCH018_ARTIFACT_MANIFEST_V001_20260926.json":
                "bcf73e2977654aff87e34cd629089f59e7a41ae282c697e079257c3bdb06208b",
        }
        records = guard.verified_record()["transitions"]
        self.assertEqual(set(expected), {Path(t["path"]).name for t in records})
        for row in records:
            with self.subTest(path=row["path"]):
                result = guard.recover_predecessor_bytes(guard.ROOT / row["path"])
                self.assertEqual(expected[Path(row["path"]).name], hashlib.sha256(result).hexdigest())

    def test_record_drift_and_authority_extensions_are_rejected(self):
        mutations = [
            lambda d: d.update(schema="UNKNOWN"),
            lambda d: d.update(authoritative_main_commit="0" * 40),
            lambda d: d.update(predecessor_main_commit="0" * 40),
            lambda d: d.update(original_timestamp_integration_head="0" * 40),
            lambda d: d.update(purpose="ACCEPT_CURRENT_BYTES"),
            lambda d: d.update(acceptance_effect="PASS"),
            lambda d: d.update(trusted_timestamp_verifier="IMPLEMENTED"),
            lambda d: d.update(historical_availability_promoted=True),
            lambda d: d.update(ordinary_replay_promoted=True),
            lambda d: d.update(canonical_admission_promoted=True),
            lambda d: d.update(private_capture_authorized=True),
            lambda d: d.update(ordinary_replay_promoted=0),
            lambda d: d.update(owner_signature="self-asserted"),
            lambda d: d["transitions"].pop(),
            lambda d: d["transitions"].append(copy.deepcopy(d["transitions"][0])),
            lambda d: d["transitions"][0].update(path="../outside.json"),
            lambda d: d["transitions"][0].update(predecessor_sha256="0" * 64),
            lambda d: d["transitions"][0].update(successor_sha256="0" * 64),
            lambda d: d["transitions"][0]["replacement"].update(before=""),
            lambda d: d["transitions"][0]["replacement"].update(after=""),
            lambda d: d["preserved_records"].pop(),
            lambda d: d["api_export_binding"].update(git_blob_sha="0" * 40),
        ]
        original = guard.load_record()
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                doc = copy.deepcopy(original)
                mutate(doc)
                with patch.object(guard, "load_record", return_value=doc):
                    with self.assertRaisesRegex(AssertionError, "record drifted"):
                        guard.verified_record()

    def test_changed_artifacts_api_and_historical_records_are_rejected(self):
        doc = guard.load_record()
        paths = [guard.ROOT / r["path"] for r in doc["transitions"] + doc["preserved_records"]]
        paths.append(guard.ROOT / doc["api_export_binding"]["path"])
        original = Path.read_bytes
        probe = guard.ROOT / doc["transitions"][0]["path"]
        for target in paths:
            with self.subTest(path=target.relative_to(guard.ROOT).as_posix()):
                with patch.object(Path, "read_bytes", lambda p: original(p) + b" " if p == target else original(p)):
                    with self.assertRaises(AssertionError):
                        guard.recover_predecessor_bytes(target if target in paths[:3] else probe)

    def test_coordinated_document_and_record_repin_is_rejected(self):
        original = guard.load_record()
        for index in range(3):
            with self.subTest(transition=index):
                doc = copy.deepcopy(original)
                row = doc["transitions"][index]
                path = guard.ROOT / row["path"]
                changed = path.read_bytes() + b" "
                row["successor_sha256"] = guard.digest(changed)
                row["successor_git_blob_sha"] = guard.git_blob(changed)
                with patch.object(guard, "load_record", return_value=doc):
                    with self.assertRaisesRegex(AssertionError, "record drifted"):
                        guard.recover_predecessor_bytes(path, changed)

    def test_unrelated_and_parent_paths_are_rejected(self):
        for path in (guard.ROOT / "unrelated.json", guard.ROOT / "../outside.json"):
            with self.subTest(path=str(path)):
                with self.assertRaisesRegex(AssertionError, "outside the exact"):
                    guard.recover_predecessor_bytes(path, b"untrusted")

    def test_missing_and_malformed_continuation_records_are_rejected(self):
        with patch.object(guard, "RECORD", guard.ROOT / "absent-continuation.json"):
            with self.assertRaisesRegex(AssertionError, "record unavailable"):
                guard.verified_record()
        with patch.object(Path, "read_text", return_value="{invalid-json"):
            with self.assertRaisesRegex(AssertionError, "record unavailable"):
                guard.verified_record()


if __name__ == "__main__":
    unittest.main()
