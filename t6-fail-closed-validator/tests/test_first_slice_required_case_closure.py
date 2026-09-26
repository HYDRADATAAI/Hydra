from __future__ import annotations
import json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
ARCH=ROOT/"docs/constraint/architecture"

def load(base,name):
    return json.loads((base/name).read_text(encoding="utf-8"))

class FirstSliceRequiredCaseClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.neg=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_AI_DATA_CENTER_POWER_INFRASTRUCTURE_FALSE_CONSTRAINT_NEGATIVE_CONTROL_V001_20260925.json")
        cls.closure=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_AI_DATA_CENTER_POWER_INFRASTRUCTURE_REQUIRED_CASE_001_002_006_CLOSURE_V001_20260925.json")
        cls.matrix=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_AI_DATA_CENTER_POWER_INFRASTRUCTURE_REQUIRED_CASE_MATRIX_V001_20260925.json")
        cls.beneficiary=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_AI_DATA_CENTER_POWER_INFRASTRUCTURE_EATON_TRANSFORMER_PREQUALIFICATION_OVERLAY_V001_20260925.json")
        cls.master=load(ARCH,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH013_MASTER_STATUS_V001_20260925.json")

    def test_case1_named_project_has_traceable_capacity_mechanism_without_fake_date(self):
        row=next(x for x in self.closure["cases"] if x["case_id"]==1)
        self.assertEqual("COVERED_REVIEWED_SHADOW_NAMED_PROJECT_CAPACITY_LIMIT",row["successor_status"])
        self.assertTrue(row["named_project"])
        self.assertEqual(960,row["planned_power_state_mw"])
        self.assertFalse(row["current_unconditional_960mw_transfer_supported"])
        self.assertFalse(row["missed_energization_date_asserted"])
        self.assertFalse(row["canonical_constraint_minted"])
        self.assertIn("SYSTEM_UPGRADES",row["limiting_mechanism"])

    def test_case2_negative_control_is_synthetic_and_never_ingested_as_evidence(self):
        self.assertTrue(self.neg["synthetic_fixture"])
        self.assertTrue(self.neg["not_historical_evidence"])
        self.assertTrue(self.neg["do_not_ingest_as_claim"])
        governed=self.neg["governed_evaluation"]
        self.assertEqual("NO",governed["constraint_promotion"])
        self.assertTrue(governed["invalidator_recorded"])
        self.assertEqual("UNKNOWN_UNSPECIFIED",governed["exact_site_capacity_state"])
        self.assertFalse(governed["adequate_numeric_capacity_claimed"])
        self.assertFalse(governed["zero_capacity_imputed"])

    def test_case6_supports_shadow_inputs_but_not_qualified_beneficiary(self):
        row=next(x for x in self.closure["cases"] if x["case_id"]==6)
        self.assertTrue(row["evidence_roles_separated"])
        self.assertTrue(all(row["input_tests"].values()))
        self.assertTrue(row["shadow_candidate_pattern_satisfied"])
        self.assertEqual("BLOCKED",row["canonical_qualification_state"])
        self.assertFalse(row["qualified_relationship_minted"])
        self.assertEqual("BLOCKED",self.beneficiary["canonical_qualification_state"])
        self.assertFalse(self.beneficiary["ordinary_t6_eligible"])
        self.assertEqual([],self.beneficiary["evidence_roles"]["economic_capture"])

    def test_all_ten_functional_cases_have_governed_coverage(self):
        self.assertEqual(10,self.matrix["functional_case_coverage_count"])
        self.assertEqual(set(range(1,11)),{row["case_id"] for row in self.matrix["cases"]})
        self.assertEqual(0,self.matrix["ordinary_replay_admitted_case_count"])
        self.assertEqual(1,self.matrix["synthetic_negative_control_case_count"])
        self.assertEqual(1,self.matrix["normalized_replay_fixture_case_count"])

    def test_functional_coverage_does_not_unlock_acceptance(self):
        self.assertEqual("BLOCKED",self.master["first_serious_constraint_run"])
        self.assertEqual("NO",self.master["readiness"]["QUALIFIED_BENEFICIARY_RELATIONSHIPS"]["status"])
        self.assertEqual("NO",self.master["readiness"]["CANONICAL_CONSTRAINTS_MINTED"]["status"])
        self.assertEqual("NO",self.master["readiness"]["LINEAGE_COMPLETE"]["status"])
        self.assertEqual("NO_ORDINARY",self.master["readiness"]["POINT_IN_TIME_REPLAY_READY"]["status"])
        self.assertEqual("NO",self.master["readiness"]["IMPLEMENTATION_ADMITTED"]["status"])

if __name__=="__main__":
    unittest.main()
