from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "docs/constraint/authority"
R = ROOT / "docs/constraint/architecture"
V = ROOT / "docs/constraint/validation"
PRED = "LILY_THREAD_6_BATCH_008_FINAL_CLOSURE_DELTA.zip"
PRED_SHA = "8ded0061f63dc79a7e74cf6ff0a5d2c179e5c52b057939283786ab80377699ba"

def load(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

class Thread6SuccessorReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.auth = load(A / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH001_AUTHORITY_MAP_V001_20260925.json")
        cls.current = load(A / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH001_CURRENT_STATE_REGISTER_V001_20260925.json")
        cls.stale = load(A / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH001_STALE_SUPERSEDED_REGISTER_V001_20260925.json")
        cls.cap = load(R / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH001_CAPABILITY_LEDGER_LINKAGE_V001_20260925.json")
        cls.slice = load(R / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH001_FIRST_SLICE_AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1_20260925.json")
        cls.master = load(R / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH001_MASTER_STATUS_V001_20260925.json")
        cls.gate = load(V / "HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH001_RUN_READINESS_MATRIX_V001_20260925.json")

    def test_predecessor_preserved(self):
        self.assertEqual(PRED, self.auth["predecessor"]["artifact"])
        self.assertEqual(PRED_SHA, self.auth["predecessor"]["sha256"])
        self.assertFalse(self.auth["predecessor"]["mutation_allowed"])
        self.assertTrue(self.current["predecessor"]["preserved"])

    def test_no_latest_wins(self):
        self.assertEqual("EXPLICIT_SUCCESSOR_RELATIONSHIP_OR_RECEIPT_ONLY", self.auth["authority_resolution"])
        self.assertEqual("PROHIBITED", self.auth["latest_wins"])

    def test_closure_propagation(self):
        c = self.current["current"]
        self.assertEqual("SEMANTIC_CORE_CLOSED", c["THREAD2"])
        self.assertEqual("SEMANTIC_CONTRACT_CLOSED_FOR_NYX_CONFORMANCE", c["THREAD3"])
        self.assertEqual("CLOSED_V1_DESIGN_FROZEN_V1", c["THREAD5_SOURCE_DESIGN"])
        self.assertEqual("V825_DOMAIN_SCOPED_CURRENT", c["TRUST_GOVERNANCE"])
        self.assertEqual("NOT_AUTHORIZED", c["LIVE_SOURCE"])

    def test_stale_only_current_view_is_superseded(self):
        states = {x["stale"]: x["current"] for x in self.stale["records"]}
        self.assertEqual("SUPERSEDED_CLOSED", states["BATCH008_THREAD2_FIVE_OPEN_POLICY_ITEMS"])
        self.assertEqual("SUPERSEDED_CLOSED", states["BATCH008_THREAD3_CANONICAL_BENEFICIARY_OPEN"])
        self.assertEqual("SUPERSEDED_CLOSED_DESIGN_ONLY", states["BATCH008_THREAD5_SOURCE_DESIGN_OPEN"])
        self.assertEqual("SUPERSEDED_AS_CURRENT_PIN", states["TRUST_GOVERNANCE_V805_CURRENT_PIN"])

    def test_dimensions_are_separate_and_truthful(self):
        d = self.master["readiness"]
        self.assertEqual("YES", d["SEMANTIC_ARCHITECTURE_READY"]["status"])
        self.assertEqual("NO", d["IMPLEMENTATION_ADMITTED"]["status"])
        self.assertEqual("YES", d["SOURCE_DESIGN_READY"]["status"])
        self.assertEqual("NO", d["LIVE_SOURCE_READY"]["status"])
        self.assertEqual("PARTIAL", d["DOMAIN_DATA_POPULATED"]["status"])
        self.assertEqual("NO", d["FULL_CONSTRAINT_RUN_READY"]["status"])

    def test_capability_linkage_reuses_architecture(self):
        self.assertEqual("FULL", self.cap["capabilities"]["entity_resolution"])
        self.assertEqual("FULL", self.cap["capabilities"]["provenance"])
        self.assertEqual("EMPTY", self.cap["capabilities"]["historical_outcomes"])
        self.assertEqual([], self.cap["missing"])
        self.assertTrue(all(x["mode"] == "DEEPEN_EXISTING" for x in self.cap["expansion_lanes"]))

    def test_first_slice_frozen_not_run(self):
        self.assertEqual("AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1", self.slice["slice_id"])
        self.assertFalse(self.slice["execute_full_real_data_run"])
        self.assertEqual("AI_COMPUTE_DEMAND", self.slice["path"][0])
        self.assertEqual("HISTORICAL_OUTCOME", self.slice["path"][-1])

    def test_gate_is_blocked_not_fabricated_ready(self):
        required = {"AUTHORITY_CURRENT","SCHEMA_COMPATIBLE","IMPLEMENTATION_ADMITTED","PROVENANCE_READY","ENTITY_RESOLUTION_READY","GRAPH_PATH_READY","CONTRADICTION_READY","CONFIDENCE_READY","HISTORICAL_AS_OF_READY","NO_LOOKAHEAD_READY","OUTCOME_LABELS_READY","REPLAY_READY","EVALUATION_READY"}
        self.assertEqual(required, set(self.gate["dimensions"]))
        self.assertEqual("BLOCKED", self.gate["overall"])
        self.assertEqual("BLOCKED", self.gate["dimensions"]["IMPLEMENTATION_ADMITTED"]["state"])
        self.assertEqual("CI-TEST-008-BLOCKER-001-NATIVE-T5-T6-AUTHORITY-ABSENT", self.gate["next_blocker"])

    def test_reconciliation_pass_is_not_run_ready(self):
        self.assertEqual("PASS", self.master["reconciliation"]["THREAD6_SUCCESSOR_RECONCILIATION"])
        self.assertEqual("BLOCKED", self.master["run_gate"])
        self.assertEqual("BLOCKED", self.master["first_serious_constraint_run"])

if __name__ == "__main__":
    unittest.main()
