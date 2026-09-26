from __future__ import annotations
import json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs/constraint/first_slice/ai_data_center_power_infrastructure_v1"
ARCH=ROOT/"docs/constraint/architecture"

def load(base,name):
    return json.loads((base/name).read_text(encoding="utf-8"))

class FirstSliceStrictAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gates=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json")
        cls.final=load(BASE,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_AI_DATA_CENTER_POWER_INFRASTRUCTURE_FINAL_RETURN_V001_20260925.json")
        cls.cap=load(ARCH,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_AI_DATA_CENTER_POWER_INFRASTRUCTURE_CAPABILITY_LEDGER_CURRENT_SUMMARY_V001_20260925.json")
        cls.master=load(ARCH,"HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_MASTER_STATUS_V001_20260925.json")

    def test_strict_gate_counts_and_overall_blocked(self):
        vals=[row["strict_gate_result"] for row in self.gates["gates"].values()]
        self.assertEqual(8,vals.count("PASS"))
        self.assertEqual(7,vals.count("FAIL"))
        self.assertEqual("BLOCKED",self.gates["overall_result"])

    def test_shadow_replay_cannot_satisfy_strict_replay_gates(self):
        self.assertEqual("PASS",self.gates["shadow_results"]["NO_LOOKAHEAD"])
        self.assertEqual("PASS",self.gates["shadow_results"]["DETERMINISTIC_REPLAY"])
        self.assertEqual("FAIL",self.gates["gates"]["NO_LOOKAHEAD"]["strict_gate_result"])
        self.assertEqual("FAIL",self.gates["gates"]["DETERMINISTIC_REPLAY"]["strict_gate_result"])
        self.assertEqual("FAIL",self.gates["gates"]["POINT_IN_TIME_RECONSTRUCTION"]["strict_gate_result"])
        self.assertEqual("FAIL",self.gates["gates"]["LINEAGE"]["strict_gate_result"])

    def test_no_canonical_constraint_or_qualified_beneficiary_is_smuggled(self):
        self.assertEqual(0,self.final["CONSTRAINTS_FORMED"])
        self.assertEqual(3,self.final["clarifications"]["SHADOW_CONSTRAINT_CANDIDATES"])
        self.assertEqual(4,self.final["BENEFICIARY_CANDIDATES"])
        self.assertEqual(0,self.final["clarifications"]["QUALIFIED_BENEFICIARIES"])
        self.assertEqual("FAIL",self.gates["gates"]["CONSTRAINT_FORMATION"]["strict_gate_result"])
        self.assertEqual("FAIL",self.gates["gates"]["BENEFICIARY_QUALIFICATION"]["strict_gate_result"])

    def test_outcomes_and_capability_updates_are_bounded(self):
        self.assertEqual(2,self.final["OUTCOMES_CAPTURED"])
        self.assertEqual(4,self.final["CAPABILITY_LEDGER_UPDATES"])
        self.assertEqual(4,self.cap["cumulative_update_count"])
        self.assertEqual({"historical_outcomes","confidence_contradictions","beneficiaries","evaluation"},{row["capability"] for row in self.cap["cumulative_successor_updates"]})

    def test_exact_blockers_and_next_action_are_preserved(self):
        expected=[
            "PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION",
            "CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT",
            "ORDINARY-POINT-IN-TIME-REPLAY-SOURCE-VERSION-HASHES-INCOMPLETE",
            "CANONICAL-T5-T6-CONSTRAINT-AND-BENEFICIARY-ADMISSION-NOT-AUTHORIZED",
        ]
        self.assertEqual(expected,self.final["blockers"])
        self.assertIn("MATERIALIZE_THE_NINE_ORIGINAL_FIRST_SLICE_SOURCE_BODIES",self.final["next_recommended_action"])
        self.assertTrue(self.master["hard_stop_second_ecosystem"])
        self.assertEqual("BLOCKED",self.master["acceptance_state"]["overall"])

if __name__=="__main__":
    unittest.main()
