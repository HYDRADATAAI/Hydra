import json
import shutil
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_replay.query import (
    ConstraintQueryError,
    ConstraintReplayQueryService,
    READ_ONLY_CAPABILITIES,
)


ROOT=Path(__file__).resolve().parents[2]


class Batch016ReadOnlyQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service=ConstraintReplayQueryService(ROOT)
        cls.acceptance=json.loads(
            (ROOT/"constraint-replay"/"runtime"/
             "HYDRA_CONSTRAINT_BATCH016_READONLY_QUERY_ACCEPTANCE_20260926.json"
            ).read_text(encoding="utf-8")
        )

    def test_acceptance_snapshot_matches_live_service(self):
        expected=self.acceptance["queries"]
        self.assertEqual(expected["summary"],self.service.summary())
        self.assertEqual(expected["integrity"],self.service.integrity())
        self.assertEqual(
            expected["case_suez"],
            self.service.case("suez-ever-given-2021"),
        )
        self.assertEqual(
            expected["list_unevaluable"],
            self.service.list_cases(outcome_class="UNEVALUABLE"),
        )

    def test_summary_exposes_frozen_batch15_aggregate(self):
        response=self.service.summary()
        self.assertEqual("hydra-constraint-readonly-query/v1",response["contract_version"])
        self.assertEqual("READ_ONLY_HISTORICAL_REPLAY",response["mode"])
        self.assertEqual("summary",response["operation"])
        self.assertEqual(
            "db28edfea01800cf85dd234edb99d003d0a185ab39f7ba8cd31af416542890f1",
            response["source_run_digest_sha256"],
        )
        self.assertEqual(22,response["result"]["coverage"]["case_count"])
        self.assertEqual(82,response["result"]["coverage"]["replay_cut_count"])
        self.assertEqual(
            {"PARTIAL_REALIZATION":17,"UNEVALUABLE":5},
            response["result"]["outcomes"]["class_counts"],
        )
        self.assertEqual(
            "BLOCKED_NO_ADMISSIBLE_NUMERIC_CONFIDENCE",
            response["result"]["calibration"]["status"],
        )

    def test_all_capabilities_are_inert(self):
        for response in (
            self.service.summary(),
            self.service.integrity(),
            self.service.case("suez-ever-given-2021"),
        ):
            self.assertEqual(READ_ONLY_CAPABILITIES,response["capabilities"])
            self.assertTrue(all(value is False for value in response["capabilities"].values()))

    def test_exact_case_lookup(self):
        response=self.service.case("suez-ever-given-2021")
        row=response["result"]
        self.assertEqual("suez-ever-given-2021",row["case_id"])
        self.assertEqual("PARTIAL_REALIZATION",row["outcome_class"])
        self.assertAlmostEqual(5.346516203703704,row["evidence_availability_lead_days"])

    def test_unknown_case_fails_closed(self):
        with self.assertRaisesRegex(ConstraintQueryError,"unknown case_id"):
            self.service.case("invented-case")

    def test_list_unevaluable_cases_is_exact(self):
        response=self.service.list_cases(outcome_class="UNEVALUABLE")
        rows=response["result"]["cases"]
        self.assertEqual(5,response["result"]["matched_count"])
        self.assertEqual({
            "eastern-mediterranean-offshore-drilling-dispute-2019-2020",
            "eu-cbam-transitional-phase-2023",
            "japan-korea-export-control-relations-2019",
            "us-chips-act-2022",
            "wto-china-rare-earths-resource-dispute-2014-2015",
        },{row["case_id"] for row in rows})

    def test_shortest_lead_filter_is_deterministic(self):
        response=self.service.list_cases(sort_by="lead_time_asc",limit=3)
        self.assertEqual(
            [
                "suez-ever-given-2021",
                "black-sea-grain-corridor-2022",
                "panama-canal-drought-transit-policy-2023",
            ],
            [row["case_id"] for row in response["result"]["cases"]],
        )

    def test_calibration_blocker_filter_matches_all_cases(self):
        response=self.service.list_cases(
            calibration_blocker="NO_SOURCE_GROUNDED_CONFIDENCE_VALUE"
        )
        self.assertEqual(22,response["result"]["matched_count"])

    def test_invalid_filters_fail_closed(self):
        with self.assertRaises(ConstraintQueryError):
            self.service.list_cases(outcome_class="TRUE_POSITIVE")
        with self.assertRaises(ConstraintQueryError):
            self.service.list_cases(min_lead_days=10,max_lead_days=5)
        with self.assertRaises(ConstraintQueryError):
            self.service.list_cases(limit=0)
        with self.assertRaises(ConstraintQueryError):
            self.service.list_cases(calibrated="false")
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ConstraintQueryError):
                    self.service.list_cases(min_lead_days=value)
                with self.assertRaises(ConstraintQueryError):
                    self.service.list_cases(max_lead_days=value)

    def test_query_contract_rejects_authority_smuggling_fields(self):
        with self.assertRaisesRegex(ConstraintQueryError,"unsupported query fields"):
            self.service.query({
                "operation":"list_cases",
                "canonical_promotion_authorized":True,
            })
        with self.assertRaisesRegex(ConstraintQueryError,"fields must be exactly"):
            self.service.query({
                "operation":"case",
                "case_id":"suez-ever-given-2021",
                "trading_authorized":True,
            })

    def test_query_contract_rejects_unknown_operation(self):
        with self.assertRaisesRegex(ConstraintQueryError,"unsupported or missing"):
            self.service.query({"operation":"promote"})

    def test_integrity_reports_pinned_batch15_state(self):
        response=self.service.integrity()
        result=response["result"]
        self.assertEqual("PASS",result["status"])
        self.assertEqual(
            "db28edfea01800cf85dd234edb99d003d0a185ab39f7ba8cd31af416542890f1",
            result["run_digest_sha256"],
        )
        self.assertGreaterEqual(result["pinned_artifact_count"],8)

    def test_tampered_run_bytes_fail_before_query_service_starts(self):
        manifest=json.loads(
            (ROOT/"constraint-replay"/"runs"/
             "HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_MANIFEST_20260926.json"
            ).read_text(encoding="utf-8")
        )
        paths=set()
        paths.add(manifest["output"]["path"])
        paths.update(item["path"] for item in manifest["inputs"])
        paths.update(item["path"] for item in manifest["ci_contracts"])
        paths.update(item["path"] for item in manifest["runner"].values())
        manifest_rel=(
            "constraint-replay/runs/"
            "HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_MANIFEST_20260926.json"
        )
        paths.add(manifest_rel)

        with tempfile.TemporaryDirectory() as td:
            temp_root=Path(td)
            for relative in paths:
                source=ROOT/relative
                target=temp_root/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target)

            run_rel=manifest["output"]["path"]
            run_path=temp_root/run_rel
            run=json.loads(run_path.read_text(encoding="utf-8"))
            run["coverage"]["case_count"]=999
            run_path.write_text(json.dumps(run,sort_keys=True),encoding="utf-8")

            with self.assertRaisesRegex(
                ConstraintQueryError,
                "run output Git blob pin mismatch",
            ):
                ConstraintReplayQueryService(temp_root)


if __name__=="__main__":
    unittest.main()
