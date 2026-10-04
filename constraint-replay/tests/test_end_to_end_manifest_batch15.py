import hashlib
import json
import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"constraint-replay"/"runs"/"HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_MANIFEST_20260926.json"
SUCCESSOR_RECORD=ROOT/"constraint-replay"/"runtime"/"HYDRA_CONSTRAINT_BATCH015_CI_CONTRACT_SUCCESSOR_V001_20261003.json"
CI_CONTRACT_SUCCESSORS={
    ".github/workflows/constraint-policy-integration.yml":{
        "predecessor_git_blob_sha":"5dbbd09dbcaac4741a6fa7bd6bac432e466f0f62",
        "successor_git_blob_sha":"b270e37e5d8e00d509ea5c883c17b6887d2aa491",
    }
}


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
                expected=item["git_blob_sha"]
                actual=git_blob_sha(ROOT/item["path"])
                if actual == expected:
                    continue
                successor=CI_CONTRACT_SUCCESSORS.get(item["path"])
                self.assertIsNotNone(successor)
                self.assertEqual(expected,successor["predecessor_git_blob_sha"])
                self.assertEqual(actual,successor["successor_git_blob_sha"])

    def test_ci_contract_successor_record_is_exact(self):
        record=json.loads(SUCCESSOR_RECORD.read_text(encoding="utf-8"))
        self.assertEqual(
            {
                "schema_version":"hydra-constraint-ci-contract-successor/v1",
                "scope":"BATCH015_CI_CONTRACT_CONTINUATION_ONLY",
                "historical_manifest_path":"constraint-replay/runs/HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_MANIFEST_20260926.json",
                "historical_manifest_git_blob_sha":"7d2deb998e8c3362cea861f48909b78c1c00a42d",
                "predecessor_artifacts_rewritten":False,
                "acceptance_effect":"NONE",
                "transitions":[{
                    "path":".github/workflows/constraint-policy-integration.yml",
                    **CI_CONTRACT_SUCCESSORS[".github/workflows/constraint-policy-integration.yml"],
                }],
            },
            record,
        )

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
