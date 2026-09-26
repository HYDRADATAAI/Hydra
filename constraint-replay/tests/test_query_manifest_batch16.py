import hashlib
import json
import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"constraint-replay"/"runtime"/"HYDRA_CONSTRAINT_BATCH016_READONLY_QUERY_MANIFEST_20260926.json"


def git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()


class Batch016QueryManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_contract_identity(self):
        self.assertEqual("hydra-constraint-readonly-query/v1",self.manifest["contract_version"])
        self.assertEqual("READ_ONLY_HISTORICAL_REPLAY",self.manifest["mode"])
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

    def test_authority_input_pins_match(self):
        for item in self.manifest["authority_inputs"]:
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_operations_are_bounded(self):
        self.assertEqual(
            ["summary","integrity","case","list_cases"],
            self.manifest["operations"],
        )

    def test_all_runtime_capabilities_are_read_only(self):
        caps=self.manifest["read_only_capabilities"]
        self.assertTrue(caps)
        self.assertTrue(all(value is False for value in caps.values()))

    def test_t6_remains_dormant(self):
        boundary=self.manifest["t6_boundary"]
        self.assertEqual("DORMANT_NOT_ACTIVATED",boundary["t6_fail_closed_validator_status"])
        self.assertFalse(boundary["query_surface_activates_t6"])
        self.assertFalse(boundary["query_surface_registers_runtime_binding"])

    def test_expected_aggregate_matches_batch15(self):
        expected=self.manifest["expected"]
        self.assertEqual(22,expected["case_count"])
        self.assertEqual(17,expected["partial_realization_count"])
        self.assertEqual(5,expected["unevaluable_count"])
        self.assertEqual(0,expected["calibrated_case_count"])
        self.assertEqual(82,expected["replay_cut_count"])


if __name__=="__main__":
    unittest.main()
