import hashlib
import json
import unittest
from pathlib import Path

from hydra_constraint_replay.operating_taxonomy import (
    OPERATING_V2_CONTRACT_VERSION,
    OPERATING_V2_MODE,
)
from hydra_constraint_replay.query import READ_ONLY_CAPABILITIES


ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"constraint-replay"/"operating"/"HYDRA_CONSTRAINT_BATCH019_OPERATING_MANIFEST_20260926.json"
SNAPSHOT=ROOT/"constraint-replay"/"operating"/"HYDRA_CONSTRAINT_BATCH019_OPERATING_SNAPSHOT_20260926.json"


def git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()


class Batch019OperatingManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.snapshot=json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    def test_contract_identity(self):
        self.assertEqual(OPERATING_V2_CONTRACT_VERSION,self.manifest["contract_version"])
        self.assertEqual(OPERATING_V2_MODE,self.manifest["mode"])
        self.assertEqual(
            "db28edfea01800cf85dd234edb99d003d0a185ab39f7ba8cd31af416542890f1",
            self.manifest["source_run_digest_sha256"],
        )

    def test_implementation_pins_match(self):
        for item in self.manifest["implementation"].values():
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_batch018_source_authority_pins_match(self):
        for item in self.manifest["source_authority"].values():
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_taxonomy_supplement_pins_match(self):
        supplement=self.manifest["taxonomy_supplement"]
        for key in ("policy","physical"):
            item=supplement[key]
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))
        self.assertEqual(
            "EXCLUDED_FROM_FROZEN_BATCH015_REPLAY",
            supplement["replay_case_membership"],
        )

    def test_snapshot_pin_and_digest_match(self):
        output=self.manifest["snapshot_output"]
        self.assertEqual(output["git_blob_sha"],git_blob_sha(ROOT/output["path"]))
        self.assertEqual(output["snapshot_digest_sha256"],self.snapshot["snapshot_digest_sha256"])
        self.assertEqual(
            "4e6d3de489457c125d27aa243f983891c0ee988a4b0671b6d496d4c00125fa03",
            self.snapshot["snapshot_digest_sha256"],
        )

    def test_taxonomy_closure_workflow_pin_matches(self):
        item=self.manifest["ci_contract"]
        self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_taxonomy_is_fully_sourced(self):
        expected=self.manifest["expected"]
        self.assertEqual(18,expected["taxonomy_event_type_count"])
        self.assertEqual(18,expected["taxonomy_sourced_event_type_count"])
        self.assertEqual([],expected["missing_event_types"])
        self.assertEqual(1,expected["supplement_event_count"])
        self.assertEqual(3,expected["supplement_physical_binding_count"])

    def test_frozen_replay_counts_are_unchanged(self):
        expected=self.manifest["expected"]
        self.assertEqual(22,expected["base_case_count"])
        self.assertEqual(31,expected["base_policy_event_count"])
        self.assertEqual(9,expected["base_policy_observation_count"])
        self.assertEqual(51,expected["base_physical_binding_count"])

    def test_readiness_distribution_closes_thin_gap_only(self):
        self.assertEqual(
            {"FULL":5,"EMPTY":1,"MISSING":3,"DUPLICATE_STALE":1},
            self.manifest["expected"]["readiness_status_counts"],
        )

    def test_capabilities_and_t6_remain_inert(self):
        self.assertEqual(READ_ONLY_CAPABILITIES,self.manifest["read_only_capabilities"])
        self.assertTrue(all(v is False for v in self.manifest["read_only_capabilities"].values()))
        t6=self.manifest["t6_boundary"]
        self.assertEqual("DORMANT_NOT_ACTIVATED",t6["status"])
        self.assertFalse(t6["runtime_binding_created"])
        self.assertFalse(t6["activation_authority_granted"])


if __name__=="__main__":
    unittest.main()
