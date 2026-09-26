import hashlib
import json
import unittest
from pathlib import Path

from hydra_constraint_replay.operating import (
    OPERATING_CONTRACT_VERSION,
    OPERATING_MODE,
    STATUS_VALUES,
)
from hydra_constraint_replay.query import READ_ONLY_CAPABILITIES


ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"constraint-replay"/"operating"/"HYDRA_CONSTRAINT_BATCH018_OPERATING_MANIFEST_20260926.json"
SNAPSHOT=ROOT/"constraint-replay"/"operating"/"HYDRA_CONSTRAINT_BATCH018_OPERATING_SNAPSHOT_20260926.json"


def git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()


class Batch018OperatingManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.snapshot=json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    def test_contract_identity(self):
        self.assertEqual(OPERATING_CONTRACT_VERSION,self.manifest["contract_version"])
        self.assertEqual(OPERATING_MODE,self.manifest["mode"])
        self.assertEqual(
            "db28edfea01800cf85dd234edb99d003d0a185ab39f7ba8cd31af416542890f1",
            self.manifest["source_run_digest_sha256"],
        )

    def test_implementation_pins_match(self):
        for item in self.manifest["implementation"].values():
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_source_authority_pins_match(self):
        for item in self.manifest["source_authority"].values():
            with self.subTest(path=item["path"]):
                self.assertEqual(item["git_blob_sha"],git_blob_sha(ROOT/item["path"]))

    def test_snapshot_pin_and_digest_match(self):
        output=self.manifest["snapshot_output"]
        self.assertEqual(output["git_blob_sha"],git_blob_sha(ROOT/output["path"]))
        self.assertEqual(output["snapshot_digest_sha256"],self.snapshot["snapshot_digest_sha256"])
        self.assertEqual(
            "6d767e34f1f644ae5e4716d907c887425fdce0c15fbf521af530d5e50f0891b0",
            self.snapshot["snapshot_digest_sha256"],
        )

    def test_expected_current_state_is_frozen(self):
        expected=self.manifest["expected"]
        self.assertEqual(22,expected["case_count"])
        self.assertEqual(82,expected["replay_cut_count"])
        self.assertEqual(31,expected["policy_event_count"])
        self.assertEqual(9,expected["policy_observation_count"])
        self.assertEqual(51,expected["physical_binding_count"])
        self.assertEqual(47,expected["unique_bound_entity_count"])
        self.assertEqual(4,expected["source_pair_count"])
        self.assertEqual(17,expected["partial_realization_count"])
        self.assertEqual(5,expected["unevaluable_count"])
        self.assertEqual(0,expected["calibrated_case_count"])

    def test_readiness_status_counts_are_frozen(self):
        self.assertEqual(
            {"FULL":4,"THIN":1,"EMPTY":1,"MISSING":3,"DUPLICATE_STALE":1},
            self.manifest["expected"]["readiness_status_counts"],
        )
        self.assertTrue(
            set(self.manifest["expected"]["readiness_status_counts"]) <= STATUS_VALUES
        )

    def test_taxonomy_gap_is_explicit(self):
        expected=self.manifest["expected"]
        self.assertEqual(18,expected["taxonomy_event_type_count"])
        self.assertEqual(17,expected["sourced_event_type_count"])
        self.assertEqual(["SUPPLY_AFFECTING_CONFLICT"],expected["missing_event_types"])

    def test_legacy_evaluation_report_is_explicitly_stale(self):
        legacy=self.manifest["source_authority"]["legacy_evaluation_report"]
        self.assertEqual("DUPLICATE_STALE",legacy["classification"])

    def test_capabilities_and_t6_boundary_are_inert(self):
        self.assertEqual(READ_ONLY_CAPABILITIES,self.manifest["read_only_capabilities"])
        self.assertTrue(all(v is False for v in self.manifest["read_only_capabilities"].values()))
        t6=self.manifest["t6_boundary"]
        self.assertEqual("DORMANT_NOT_ACTIVATED",t6["status"])
        self.assertFalse(t6["runtime_binding_created"])
        self.assertFalse(t6["activation_authority_granted"])


if __name__=="__main__":
    unittest.main()
