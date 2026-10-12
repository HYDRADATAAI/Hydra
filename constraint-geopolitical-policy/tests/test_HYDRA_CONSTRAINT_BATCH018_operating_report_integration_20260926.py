import unittest
from collections import Counter
from pathlib import Path

from hydra_constraint_replay.operating import (
    ConstraintOperatingReportService,
    OperatingReportError,
)
from hydra_constraint_replay.query import READ_ONLY_CAPABILITIES


ROOT=Path(__file__).resolve().parents[2]


class Batch018OperatingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=ConstraintOperatingReportService(ROOT)
        cls.snapshot=cls.service.snapshot()

    def test_snapshot_is_current_and_self_verified(self):
        self.assertEqual("PASS_WITH_EXPLICIT_BLOCKERS",self.snapshot["operating_status"])
        self.assertEqual(
            "6d767e34f1f644ae5e4716d907c887425fdce0c15fbf521af530d5e50f0891b0",
            self.snapshot["snapshot_digest_sha256"],
        )
        state=self.snapshot["current_state"]
        self.assertEqual(22,state["case_count"])
        self.assertEqual(82,state["replay_cut_count"])
        self.assertEqual(31,state["policy_event_count"])
        self.assertEqual(9,state["policy_observation_count"])
        self.assertEqual(51,state["physical_binding_count"])
        self.assertEqual(47,state["unique_bound_entity_count"])

    def test_readiness_distribution_is_exact(self):
        counts=Counter(row["status"] for row in self.snapshot["readiness_dimensions"])
        self.assertEqual(
            {"FULL":4,"THIN":1,"EMPTY":1,"MISSING":3,"DUPLICATE_STALE":1},
            dict(counts),
        )

    def test_full_dimensions_are_scope_bounded(self):
        full={row["dimension"] for row in self.snapshot["readiness_dimensions"] if row["status"]=="FULL"}
        self.assertEqual(
            {
                "historical_case_classification",
                "deterministic_historical_replay_execution",
                "policy_physical_binding",
                "read_only_query_access",
            },
            full,
        )

    def test_taxonomy_gap_is_thin_not_hidden(self):
        row=self.service.dimension("policy_event_taxonomy_sourced_coverage")["result"]
        self.assertEqual("THIN",row["status"])
        self.assertEqual(["SUPPLY_AFFECTING_CONFLICT"],row["evidence"]["missing_event_types"])
        self.assertEqual("NO_SOURCED_SUPPLY_AFFECTING_CONFLICT_CASE",row["blocker"])

    def test_calibration_is_empty_not_green(self):
        row=self.service.dimension("probabilistic_calibration")["result"]
        self.assertEqual("EMPTY",row["status"])
        self.assertEqual(0,row["evidence"]["calibrated_case_count"])
        self.assertIsNone(row["evidence"]["brier_score"])

    def test_live_and_mutation_readiness_remain_missing(self):
        live=self.service.dimension("live_current_data_ingestion")["result"]
        mutation=self.service.dimension("canonical_mutation_runtime")["result"]
        self.assertEqual("MISSING",live["status"])
        self.assertFalse(live["evidence"]["live_ingestion_proof_present"])
        self.assertEqual("MISSING",mutation["status"])
        self.assertTrue(mutation["intentional"])
        self.assertFalse(mutation["evidence"]["canonical_promotion_authorized"])

    def test_t6_remains_intentionally_missing_and_dormant(self):
        row=self.service.dimension("t6_activation")["result"]
        self.assertEqual("MISSING",row["status"])
        self.assertTrue(row["intentional"])
        self.assertEqual("DORMANT_NOT_ACTIVATED",row["evidence"]["status"])

    def test_legacy_evaluation_report_is_stale(self):
        row=self.service.dimension("legacy_replay_evaluation_report")["result"]
        self.assertEqual("DUPLICATE_STALE",row["status"])
        self.assertEqual(22,row["evidence"]["current_classified_case_count"])

    def test_unevaluable_reason_codes_are_exact(self):
        self.assertEqual(
            {
                "eastern-mediterranean-offshore-drilling-dispute-2019-2020":
                    "UNRESOLVED_LEGAL_TERRITORIAL_RESOURCE_DISPUTE",
                "eu-cbam-transitional-phase-2023":
                    "INCOMPLETE_MODELED_ECONOMIC_OUTCOME_WINDOW",
                "japan-korea-export-control-relations-2019":
                    "CONFLICTING_OFFICIAL_NORMALIZATION_CHARACTERIZATION",
                "us-chips-act-2022":"OPEN_EXPLICIT_HORIZON",
                "wto-china-rare-earths-resource-dispute-2014-2015":
                    "CONTESTED_IMPLEMENTATION_COMPLIANCE",
            },
            {row["case_id"]:row["reason_code"] for row in self.snapshot["unevaluable_cases"]},
        )

    def test_gap_query_contains_only_nonfull_dimensions(self):
        gaps=self.service.gaps()
        self.assertEqual(READ_ONLY_CAPABILITIES,gaps["capabilities"])
        self.assertEqual(6,len(gaps["result"]))
        self.assertTrue(all(row["status"]!="FULL" for row in gaps["result"]))

    def test_unknown_dimension_fails_closed(self):
        with self.assertRaisesRegex(OperatingReportError,"unknown operating dimension"):
            self.service.dimension("invented_dimension")


if __name__=="__main__":
    unittest.main()
