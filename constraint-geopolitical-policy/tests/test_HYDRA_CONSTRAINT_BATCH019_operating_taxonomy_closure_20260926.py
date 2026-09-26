import unittest
from collections import Counter
from pathlib import Path

from hydra_constraint_replay.operating_taxonomy import (
    ConstraintOperatingReportV2Service,
)
from hydra_constraint_replay.query import READ_ONLY_CAPABILITIES


ROOT=Path(__file__).resolve().parents[2]


class Batch019OperatingTaxonomyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=ConstraintOperatingReportV2Service(ROOT)
        cls.snapshot=cls.service.snapshot()

    def test_snapshot_closes_taxonomy_gap_without_changing_replay_membership(self):
        self.assertEqual(
            "4e6d3de489457c125d27aa243f983891c0ee988a4b0671b6d496d4c00125fa03",
            self.snapshot["snapshot_digest_sha256"],
        )
        state=self.snapshot["current_state"]
        self.assertEqual(22,state["case_count"])
        self.assertEqual(31,state["policy_event_count"])
        self.assertEqual(9,state["policy_observation_count"])
        self.assertEqual(51,state["physical_binding_count"])
        self.assertEqual(18,state["taxonomy_event_type_count"])
        self.assertEqual(18,state["taxonomy_sourced_event_type_count"])
        self.assertEqual(1,state["taxonomy_supplement_case_count"])
        self.assertEqual(1,state["taxonomy_supplement_event_count"])
        self.assertEqual(3,state["taxonomy_supplement_physical_binding_count"])

    def test_taxonomy_dimension_is_now_full(self):
        row=self.service.dimension("policy_event_taxonomy_sourced_coverage")["result"]
        self.assertEqual("FULL",row["status"])
        self.assertEqual(18,row["evidence"]["taxonomy_event_type_count"])
        self.assertEqual(18,row["evidence"]["sourced_event_type_count"])
        self.assertEqual([],row["evidence"]["missing_event_types"])
        self.assertEqual(
            "ukraine-war-agricultural-supply-shock-2022-taxonomy-supplement",
            row["evidence"]["taxonomy_supplement_case_id"],
        )
        self.assertFalse(row["evidence"]["taxonomy_supplement_replay_case_admitted"])
        self.assertNotIn("blocker",row)

    def test_supply_affecting_conflict_is_present_exactly_once_in_taxonomy_view(self):
        row=self.service.dimension("policy_event_taxonomy_sourced_coverage")["result"]
        self.assertEqual(
            1,
            row["evidence"]["event_type_counts"]["SUPPLY_AFFECTING_CONFLICT"],
        )

    def test_readiness_distribution_has_no_thin_dimension(self):
        counts=Counter(row["status"] for row in self.snapshot["readiness_dimensions"])
        self.assertEqual(
            {"FULL":5,"EMPTY":1,"MISSING":3,"DUPLICATE_STALE":1},
            dict(counts),
        )
        self.assertNotIn("THIN",counts)

    def test_remaining_gaps_are_unchanged_non_taxonomy_blockers(self):
        gaps=self.service.gaps()["result"]
        self.assertEqual(5,len(gaps))
        self.assertEqual(
            {
                "probabilistic_calibration",
                "live_current_data_ingestion",
                "canonical_mutation_runtime",
                "t6_activation",
                "legacy_replay_evaluation_report",
            },
            {row["dimension"] for row in gaps},
        )

    def test_calibration_and_t6_boundaries_are_unchanged(self):
        calibration=self.service.dimension("probabilistic_calibration")["result"]
        self.assertEqual("EMPTY",calibration["status"])
        self.assertEqual(0,calibration["evidence"]["calibrated_case_count"])
        t6=self.service.dimension("t6_activation")["result"]
        self.assertEqual("MISSING",t6["status"])
        self.assertTrue(t6["intentional"])
        self.assertEqual("DORMANT_NOT_ACTIVATED",t6["evidence"]["status"])

    def test_supplement_metadata_proves_non_replay_admission(self):
        supplement=self.snapshot["taxonomy_supplement"]
        self.assertEqual("SUPPLY_AFFECTING_CONFLICT",supplement["event_type"])
        self.assertFalse(supplement["replay_case_admitted"])
        self.assertEqual(3,supplement["physical_binding_count"])
        self.assertEqual(
            {
                "resource:ukraine-grain-supply-conflict-2022",
                "extraction:ukraine-agricultural-production-conflict-2022",
                "bottleneck:ukraine-war-agricultural-supply-shock-2022",
            },
            set(supplement["physical_entity_ids"]),
        )

    def test_all_capabilities_remain_read_only(self):
        for response in (
            self.service.readiness(),
            self.service.gaps(),
            self.service.dimension("policy_event_taxonomy_sourced_coverage"),
        ):
            self.assertEqual(READ_ONLY_CAPABILITIES,response["capabilities"])
            self.assertTrue(all(v is False for v in response["capabilities"].values()))


if __name__=="__main__":
    unittest.main()
