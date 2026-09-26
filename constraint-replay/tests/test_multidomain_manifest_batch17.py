import hashlib
import json
import unittest
from pathlib import Path

from hydra_constraint_replay.multidomain import (
    MULTIDOMAIN_CONTRACT_VERSION,
    MULTIDOMAIN_MODE,
    SOURCE_PAIRS,
)
from hydra_constraint_replay.query import READ_ONLY_CAPABILITIES


ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"constraint-replay"/"runtime"/"HYDRA_CONSTRAINT_BATCH017_MULTIDOMAIN_READONLY_MANIFEST_20260926.json"


def git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()


class Batch017MultiDomainManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_contract_identity(self):
        self.assertEqual(MULTIDOMAIN_CONTRACT_VERSION,self.manifest["contract_version"])
        self.assertEqual(MULTIDOMAIN_MODE,self.manifest["mode"])
        self.assertEqual(
            "db28edfea01800cf85dd234edb99d003d0a185ab39f7ba8cd31af416542890f1",
            self.manifest["source_run_digest_sha256"],
        )

    def test_implementation_pins_match(self):
        for item in self.manifest["implementation"].values():
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_contract_pins_match(self):
        for item in self.manifest["contracts"]:
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_replay_query_manifest_pin_matches(self):
        item=self.manifest["replay_query_manifest"]
        self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_source_pair_paths_and_pins_match(self):
        expected={
            batch_id:(policy,physical)
            for batch_id,policy,physical in SOURCE_PAIRS
        }
        self.assertEqual(set(expected),{x["batch_id"] for x in self.manifest["source_pairs"]})
        for item in self.manifest["source_pairs"]:
            batch=item["batch_id"]
            policy_path,physical_path=expected[batch]
            self.assertEqual(policy_path,item["policy"]["path"])
            self.assertEqual(physical_path,item["physical"]["path"])
            self.assertEqual(item["policy"]["git_blob_sha"],git_blob_sha(ROOT/policy_path))
            self.assertEqual(item["physical"]["git_blob_sha"],git_blob_sha(ROOT/physical_path))

    def test_expected_join_counts_are_frozen(self):
        expected=self.manifest["expected"]
        self.assertEqual(22,expected["case_count"])
        self.assertEqual(31,expected["policy_event_count"])
        self.assertEqual(9,expected["policy_observation_count"])
        self.assertEqual(51,expected["physical_binding_count"])
        self.assertEqual(47,expected["unique_bound_entity_count"])
        self.assertEqual(4,expected["source_pair_count"])
        self.assertEqual(82,expected["replay_cut_count"])
        self.assertEqual(17,expected["partial_realization_count"])
        self.assertEqual(5,expected["unevaluable_count"])
        self.assertEqual(0,expected["calibrated_case_count"])

    def test_capabilities_are_inert(self):
        self.assertEqual(READ_ONLY_CAPABILITIES,self.manifest["read_only_capabilities"])
        self.assertTrue(all(value is False for value in self.manifest["read_only_capabilities"].values()))

    def test_t6_boundary_remains_dormant(self):
        t6=self.manifest["t6_boundary"]
        self.assertEqual("DORMANT_NOT_ACTIVATED",t6["status"])
        self.assertFalse(t6["runtime_binding_created"])
        self.assertFalse(t6["activation_authority_granted"])


if __name__=="__main__":
    unittest.main()
