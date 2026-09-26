from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"docs"/"constraint"/"first_slice"/"ai_data_center_power_infrastructure_v1"

def load(name):
    return json.loads((BASE/name).read_text(encoding="utf-8"))

class ClaimCandidateBeneficiaryPopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.claims=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_CLAIM_REGISTRY_V001_20260925.json")
        cls.candidates=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_T5_CANDIDATE_PROPOSALS_V001_20260925.json")
        cls.relief=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_RELIEF_PATHS_V001_20260925.json")
        cls.beneficiaries=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_BENEFICIARY_EVALUATIONS_V001_20260925.json")
        cls.status=load("HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH010_AI_DATA_CENTER_POWER_INFRASTRUCTURE_CLAIM_CANDIDATE_BENEFICIARY_STATUS_V001_20260925.json")

    def test_three_candidates_have_explicit_mechanism_scope_and_no_canonical_id(self):
        self.assertEqual(3,len(self.candidates["candidates"]))
        for candidate in self.candidates["candidates"]:
            self.assertTrue(candidate["constraining_mechanism"])
            self.assertTrue(candidate["constrained_target"])
            self.assertTrue(candidate["material_scope"])
            self.assertIsNone(candidate["canonical_constraint_id"])
            self.assertFalse(candidate["ordinary_t6_eligible"])

    def test_interconnection_classification_ambiguity_is_preserved(self):
        candidate=self.candidates["candidates"][0]
        self.assertEqual("AMBIGUOUS",candidate["classification_status"])
        self.assertEqual({"CAPACITY","REGULATORY"},set(candidate["classification_candidates"]))
        self.assertIsNone(candidate["constraint_class"])

    def test_dependencies_are_not_promoted_to_constraints(self):
        self.assertIn("water_cooling_dependency",self.candidates["explicitly_not_formed_as_constraints"])
        self.assertIn("fiber_connectivity_dependency",self.candidates["explicitly_not_formed_as_constraints"])

    def test_relief_paths_do_not_fabricate_resolution(self):
        self.assertEqual(5,len(self.relief["relief_paths"]))
        self.assertTrue(all(not path["invalidates_constraint"] for path in self.relief["relief_paths"]))

    def test_beneficiary_relationships_are_separate_objects_and_not_qualified(self):
        self.assertEqual(4,len(self.beneficiaries["relationships"]))
        ids=set()
        for relation in self.beneficiaries["relationships"]:
            self.assertNotIn(relation["beneficiary_relationship_id"],ids)
            ids.add(relation["beneficiary_relationship_id"])
            self.assertEqual("INELIGIBLE_TO_EVALUATE",relation["qualification_state"])
            self.assertIsNone(relation["constraint_id"])
            self.assertIsNone(relation["beneficiary_confidence"])
            self.assertEqual("BLOCKED",relation["eligibility_state"])
        self.assertEqual(0,self.beneficiaries["qualified_relationship_count"])

    def test_constraint_and_beneficiary_evidence_roles_are_separate(self):
        for relation in self.beneficiaries["relationships"]:
            lineage=relation["evidence_lineage"]
            self.assertIn("constraint_evidence",lineage)
            self.assertIn("entity_connection",lineage)
            self.assertIn("advantage_mechanism",lineage)
            self.assertIn("capacity_or_availability",lineage)
            self.assertIn("economic_or_strategic_capture",lineage)
            self.assertIn("disconfirming_or_blocking",lineage)

    def test_no_t5_candidate_contains_authoritative_beneficiary_field(self):
        for candidate in self.candidates["candidates"]:
            self.assertNotIn("beneficiary",candidate)
            self.assertNotIn("beneficiaries",candidate)

    def test_status_preserves_real_blockers_and_no_run_readiness(self):
        self.assertEqual("YES_SHADOW",self.status["results"]["T5_CONSTRAINT_CANDIDATE_LAYER_POPULATED"])
        self.assertEqual("YES_BLOCKED_EVALUATIONS",self.status["results"]["T6_BENEFICIARY_RELATIONSHIP_LAYER_POPULATED"])
        self.assertEqual("NO",self.status["results"]["CANONICAL_CONSTRAINTS_MINTED"])
        self.assertEqual("NO",self.status["results"]["QUALIFIED_BENEFICIARIES_MINTED"])
        self.assertEqual("BLOCKED",self.status["results"]["FIRST_SERIOUS_CONSTRAINT_RUN"])
        self.assertIn("PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION",self.status["remaining_blockers"])
        self.assertIn("CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT",self.status["remaining_blockers"])

if __name__=="__main__":
    unittest.main()
