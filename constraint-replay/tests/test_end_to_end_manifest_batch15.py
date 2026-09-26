import hashlib
import json
import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"constraint-replay"/"runs"/"HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_MANIFEST_20260926.json"


def git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()


class Batch015ExecutionManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_run_digest_is_expected(self):
        self.assertEqual(
            "db28edfea01800cf85dd234edb99d003d0a185ab39f7ba8cd31af416542890f1",
            self.manifest["run_digest_sha256"],
        )

    def test_runner_and_cli_pins_match(self):
        for item in self.manifest["runner"].values():
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_input_pins_match(self):
        for item in self.manifest["inputs"]:
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_output_pin_matches(self):
        item=self.manifest["output"]
        self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_ci_contract_pins_match(self):
        for item in self.manifest["ci_contracts"]:
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_expected_contract_shape(self):
        expected=self.manifest["expected"]
        self.assertEqual(22,expected["case_count"])
        self.assertEqual(82,expected["replay_cut_count"])
        self.assertEqual(1.0,expected["classification_coverage"])
        self.assertEqual(17,expected["partial_realization_count"])
        self.assertEqual(5,expected["unevaluable_count"])
        self.assertEqual(0,expected["calibrated_case_count"])
        self.assertIsNone(expected["brier_score"])


if __name__=="__main__":
    unittest.main()
