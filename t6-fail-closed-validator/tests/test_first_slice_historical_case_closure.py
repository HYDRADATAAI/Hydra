from __future__ import annotations
import json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
ARCH=ROOT/"docs/constraint/architecture"

def load(base,name):
    return json.loads((base/name).read_text(encoding="utf-8"))

class FirstSliceHistoricalCaseClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_AI_DATA_CENTER_POWER_INFRASTRUCTURE_HISTORICAL_CASE_SOURCE_REGISTRY_EXTENSION_V001_20260925.json")
        cls.evidence=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_AI_DATA_CENTER_POWER_INFRASTRUCTURE_HISTORICAL_CASE_EVIDENCE_SUPPLEMENT_V001_20260925.json")
        cls.cases=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_AI_DATA_CENTER_POWER_INFRASTRUCTURE_HISTORICAL_CASE_REGISTRY_V001_20260925.json")
        cls.outcomes=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_AI_DATA_CENTER_POWER_INFRASTRUCTURE_OUTCOME_RECORDS_SUPPLEMENT_V001_20260925.json")
        cls.overlay=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_AI_DATA_CENTER_POWER_INFRASTRUCTURE_REQUIRED_CASES_HISTORICAL_CLOSURE_OVERLAY_V001_20260925.json")
        cls.master=load(ARCH,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH012_MASTER_STATUS_V001_20260925.json")

    def test_new_sources_never_backdate_hydra_availability(self):
        self.assertFalse(self.sources["runtime_live_source_authority_used"])
        self.assertFalse(self.sources["source_content_persisted"])
        self.assertFalse(self.sources["exact_hydra_acquisition_timestamp_persisted"])
        for row in self.sources["sources"]:
            self.assertIsNone(row["acquired_at"])
            self.assertIsNone(row["available_at"])
            self.assertFalse(row["historical_backdating_authorized"])
            self.assertFalse(row["ordinary_raw_lineage_eligible"])

    def test_loudoun_constraint_is_not_overpromoted_to_named_project_delay(self):
        row=next(x for x in self.cases["records"] if x["required_case_id"]==1)
        self.assertEqual("PARTIAL_STRENGTHENED_REAL_LOCALIZED_CONSTRAINT",row["status"])
        self.assertEqual("TRANSMISSION_CAPACITY",row["limiting_mechanism"])
        self.assertIn("NO_NAMED_PROJECT",row["unresolved_requirement"])
        self.assertTrue(row["overpromotion_prohibited"])

    def test_corporate_plan_and_regulatory_state_are_both_preserved(self):
        row=next(x for x in self.cases["records"] if x["required_case_id"]==4)
        self.assertEqual("COVERED_REVIEWED_SHADOW",row["status"])
        self.assertEqual("PRESERVE_BOTH_SCOPE_STATES_NO_FABRICATED_CONSENSUS",row["contradiction_state"])
        self.assertIn("960MW",row["corporate_state"])
        self.assertIn("300MW_TO_480MW_REJECTED",row["regulatory_state"])
        self.assertIn("NOT_APPROVED_INTERCONNECTION",row["semantic_resolution"])
        self.assertFalse(row["ordinary_replay_eligible"])

    def test_cancelled_project_preserves_prior_history_and_bounds_scope(self):
        row=next(x for x in self.cases["records"] if x["required_case_id"]==10)
        self.assertEqual("COVERED_REVIEWED_SHADOW",row["status"])
        self.assertTrue(row["prior_state_preserved"])
        self.assertFalse(row["historical_rewrite"])
        self.assertEqual("PROJECT_CANCELLED_AT_SITE_APPLICATION_SCOPE",row["successor_state"])
        self.assertIn("DO_NOT_GENERALIZE",row["semantic_limit"])

    def test_project_cancelled_outcome_does_not_resolve_constraint_or_beneficiary(self):
        self.assertEqual(1,len(self.outcomes["records"]))
        row=self.outcomes["records"][0]
        self.assertEqual("PROJECT_CANCELLED",row["outcome_label"])
        self.assertIsNone(row["hydra_available_at"])
        self.assertFalse(row["ordinary_replay_eligible"])
        self.assertEqual(2,self.outcomes["current_slice_outcome_count_after"])
        self.assertEqual(0,self.outcomes["constraint_resolutions_total"])
        self.assertEqual(0,self.outcomes["beneficiary_capture_confirmed_total"])

    def test_case_queue_truthfully_retains_unclosed_cases(self):
        state=self.overlay["current_case_state"]
        self.assertIn(4,state["covered_or_shadow_covered"])
        self.assertIn(10,state["covered_or_shadow_covered"])
        self.assertIn(1,state["partial"])
        self.assertIn(6,state["partial"])
        self.assertEqual([2],state["gap"])

    def test_master_remains_blocked(self):
        self.assertEqual("BLOCKED",self.master["first_serious_constraint_run"])
        self.assertEqual("NO",self.master["readiness"]["IMPLEMENTATION_ADMITTED"]["status"])
        self.assertEqual("NO",self.master["readiness"]["FIRST_SLICE_RAW_ARTIFACTS_MATERIALIZED"]["status"])
        self.assertEqual("NO_ORDINARY",self.master["readiness"]["POINT_IN_TIME_REPLAY_READY"]["status"])
        self.assertIn("REQUIRED-CASE-002-MATCHED-FALSE-CONSTRAINT-PRIMARY-COUNTEREVIDENCE-ABSENT",self.master["remaining_blockers"])

if __name__=="__main__":
    unittest.main()
