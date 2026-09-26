import unittest
from pathlib import Path

from hydra_constraint_replay.multidomain import (
    ConstraintMultiDomainQueryService,
    MultiDomainQueryError,
)
from hydra_constraint_replay.query import READ_ONLY_CAPABILITIES


ROOT=Path(__file__).resolve().parents[2]


class Batch017MultiDomainIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=ConstraintMultiDomainQueryService(ROOT)

    def test_summary_joins_all_three_domains(self):
        response=self.service.summary()
        result=response["result"]
        self.assertEqual("hydra-constraint-multidomain-readonly/v1",response["contract_version"])
        self.assertEqual("READ_ONLY_MULTIDOMAIN_HISTORICAL",response["mode"])
        self.assertEqual(22,result["replay"]["coverage"]["case_count"])
        self.assertEqual(31,result["policy"]["event_count"])
        self.assertEqual(9,result["policy"]["observation_count"])
        self.assertEqual(51,result["physical"]["binding_count"])
        self.assertEqual(47,result["physical"]["unique_bound_entity_count"])
        self.assertEqual(4,result["physical"]["source_pair_count"])
        self.assertEqual("PASS",result["join_integrity"]["status"])

    def test_every_response_is_inert(self):
        for response in (
            self.service.summary(),
            self.service.integrity(),
            self.service.case("suez-ever-given-2021"),
        ):
            self.assertEqual(READ_ONLY_CAPABILITIES,response["capabilities"])
            self.assertTrue(all(value is False for value in response["capabilities"].values()))

    def test_suez_case_joins_replay_policy_and_physical_state(self):
        result=self.service.case("suez-ever-given-2021",max_depth=3)["result"]
        self.assertEqual("batch001",result["source_pair"])
        self.assertEqual("suez-ever-given-2021",result["replay"]["case_id"])
        self.assertEqual("PARTIAL_REALIZATION",result["replay"]["outcome_class"])
        self.assertTrue(result["policy_events"])
        entity_ids={
            binding["entity_id"]
            for event in result["policy_events"]
            for binding in event["physical_bindings"]
        }
        self.assertIn("infrastructure:suez-canal",entity_ids)
        self.assertIn("transport:maritime-traffic-via-suez",entity_ids)

    def test_suez_entity_usage_resolves_canonical_physical_reference(self):
        result=self.service.entity_usage("infrastructure:suez-canal",max_depth=3)["result"]
        self.assertEqual("infrastructure:suez-canal",result["entity_id"])
        self.assertGreaterEqual(result["usage_count"],1)
        self.assertEqual(
            {"suez-ever-given-2021"},
            {row["case_id"] for row in result["usages"]},
        )
        self.assertTrue(all(row["reference_type"]=="node" for row in result["usages"]))

    def test_export_control_event_filter_crosses_policy_and_replay(self):
        result=self.service.list_cases(event_type="EXPORT_CONTROL")["result"]
        ids={row["case_id"] for row in result["cases"]}
        self.assertEqual(
            {
                "bis-semiconductor-controls-2022",
                "china-gallium-germanium-controls-2023",
            },
            ids,
        )

    def test_physical_entity_filter_is_exact(self):
        result=self.service.list_cases(
            physical_entity_id="infrastructure:suez-canal"
        )["result"]
        self.assertEqual(1,result["matched_count"])
        self.assertEqual("suez-ever-given-2021",result["cases"][0]["case_id"])

    def test_unevaluable_filter_preserves_replay_classification(self):
        result=self.service.list_cases(outcome_class="UNEVALUABLE")["result"]
        self.assertEqual(5,result["matched_count"])

    def test_unknown_case_and_entity_fail_closed(self):
        with self.assertRaisesRegex(MultiDomainQueryError,"unknown case_id"):
            self.service.case("invented-case")
        with self.assertRaisesRegex(MultiDomainQueryError,"unknown physical entity_id"):
            self.service.entity_usage("infrastructure:invented")

    def test_invalid_depth_and_authority_smuggling_fail_closed(self):
        with self.assertRaises(MultiDomainQueryError):
            self.service.case("suez-ever-given-2021",max_depth=13)
        with self.assertRaisesRegex(MultiDomainQueryError,"unsupported query fields"):
            self.service.query({
                "operation":"list_cases",
                "trading_authorized":True,
            })
        with self.assertRaisesRegex(MultiDomainQueryError,"unsupported or missing"):
            self.service.query({"operation":"promote"})

    def test_integrity_keeps_t6_dormant(self):
        result=self.service.integrity()["result"]
        self.assertEqual("PASS",result["multidomain"]["status"])
        self.assertEqual("DORMANT_NOT_ACTIVATED",result["t6_status"])
        self.assertEqual(
            "db28edfea01800cf85dd234edb99d003d0a185ab39f7ba8cd31af416542890f1",
            result["replay"]["run_digest_sha256"],
        )


if __name__=="__main__":
    unittest.main()
