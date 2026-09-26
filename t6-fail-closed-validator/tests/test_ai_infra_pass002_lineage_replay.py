"""Adversarial tests of existing shadow owner; all mutations are test fixtures."""
import copy
import unittest
import test_first_slice_outcome_shadow_replay as existing
from hydra_t6_failclosed.first_slice_shadow_replay import build_shadow_snapshot, future_leaks


class LineageReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        existing.FirstSliceOutcomeShadowReplayTests.setUpClass()
        cls.base = existing.FirstSliceOutcomeShadowReplayTests

    def setUp(self):
        b = self.base
        self.inputs = copy.deepcopy(dict(claim_registry=b.claims, candidates=b.candidates,
            relief_paths=b.relief, beneficiaries=b.beneficiaries, outcomes=b.outcomes,
            candidate_overlay=b.overlay))

    def snap(self, at="2026-09-26T12:47:00Z"):
        return build_shadow_snapshot(as_of=at, **self.inputs)

    def test_before_any_knowledge_is_empty(self):
        self.assertTrue(all(not value for key, value in self.snap("2020-01-01T00:00:00Z").items() if key != "as_of"))

    def test_overlay_boundary(self):
        self.assertEqual([], self.snap("2026-09-26T12:46:59Z")["constraint_candidate_ids"])
        self.assertEqual(3, len(self.snap()["constraint_candidate_ids"]))
        self.assertEqual(4, len(self.snap()["beneficiary_relationship_ids"]))

    def test_missing_candidate_time_excludes_dependents(self):
        self.inputs.pop("candidate_overlay")
        result = self.snap()
        for key in ("constraint_candidate_ids", "relief_path_ids", "beneficiary_relationship_ids"):
            self.assertEqual([], result[key])

    def test_future_parent_cascades_without_erasing_other_constraints(self):
        self.inputs["claim_registry"]["claims"][2]["available_at"] = "2027-01-01T00:00:00Z"
        result = self.snap()
        self.assertEqual(2, len(result["constraint_candidate_ids"]))
        self.assertNotIn("BEN-AIDC-EATON-TRANSFORMER-001", result["beneficiary_relationship_ids"])
        self.assertNotIn("REL-AIDC-004", result["relief_path_ids"])

    def test_unknown_and_empty_candidate_lineage(self):
        for refs in ([], ["CLM-UNKNOWN"]):
            with self.subTest(refs=refs):
                self.inputs["candidates"]["candidates"][0]["claim_ids"] = refs
                self.assertNotIn("T5C-AIDC-US-INTERCONNECTION-THROUGHPUT-001", self.snap()["constraint_candidate_ids"])

    def test_evidence_only_relief_requires_visible_evidence(self):
        self.inputs["relief_paths"]["relief_paths"][0]["support_evidence_ids"] = ["EV-NOT-KNOWN"]
        self.assertNotIn("REL-AIDC-001", self.snap()["relief_path_ids"])

    def test_beneficiary_cannot_backdate_parent_claim(self):
        self.inputs["claim_registry"]["claims"][4]["available_at"] = "2027-01-01T00:00:00Z"
        result = self.snap()
        self.assertNotIn("BEN-AIDC-EATON-TRANSFORMER-001", result["beneficiary_relationship_ids"])
        self.assertEqual([], result["outcome_ids"])

    def test_injected_downstream_ids_detected(self):
        result = self.snap("2020-01-01T00:00:00Z")
        for key, identity in (("constraint_candidate_ids", "T5C-AIDC-US-TRANSFORMER-SUPPLY-001"),
                              ("relief_path_ids", "REL-AIDC-004"),
                              ("beneficiary_relationship_ids", "BEN-AIDC-EATON-TRANSFORMER-001")):
            result[key] = [identity]
        self.assertEqual(3, len(future_leaks(result, **self.inputs)))

    def test_naive_and_invalid_time_rejected(self):
        for stamp in ("2026-09-26", "2026-09-26T12:47:00", "garbage", None):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                self.snap(stamp)

    def test_timezone_equivalence(self):
        a, b = self.snap(), self.snap("2026-09-26T08:47:00-04:00")
        a.pop("as_of"); b.pop("as_of")
        self.assertEqual(a, b)

    def test_duplicate_identity_rejected(self):
        self.inputs["claim_registry"]["claims"].append(self.inputs["claim_registry"]["claims"][0])
        with self.assertRaises(ValueError): self.snap()

    def test_missing_overlay_identity_rejected(self):
        self.inputs["candidate_overlay"]["candidates"].pop()
        with self.assertRaises(ValueError): self.snap()

    def test_order_does_not_change_snapshot(self):
        before = self.snap()
        for document, key in (("candidates", "candidates"), ("claim_registry", "claims"),
                              ("relief_paths", "relief_paths"), ("beneficiaries", "relationships")):
            self.inputs[document][key].reverse()
        self.assertEqual(before, self.snap())

    def test_relief_never_invalidates_other_constraints(self):
        self.inputs["relief_paths"]["relief_paths"] = []
        self.assertEqual(3, len(self.snap()["constraint_candidate_ids"]))

    def test_unknown_outcome_id_detected(self):
        result = self.snap()
        result["outcome_ids"].append("OUT-UNKNOWN")
        self.assertIn("outcome:OUT-UNKNOWN", future_leaks(result, **self.inputs))

    def test_evidence_id_cannot_substitute_for_candidate_claim(self):
        evidence = self.inputs["claim_registry"]["claims"][0]["support_evidence_ids"][0]
        row = self.inputs["candidates"]["candidates"][0]
        row["claim_ids"] = [evidence]
        self.assertNotIn(row["constraint_candidate_id"], self.snap()["constraint_candidate_ids"])

    def test_evidence_id_cannot_substitute_for_outcome_claim(self):
        evidence = self.inputs["claim_registry"]["claims"][0]["support_evidence_ids"][0]
        self.inputs["outcomes"]["records"][0]["claim_id"] = evidence
        self.assertEqual([], self.snap()["outcome_ids"])

    def test_scalar_lineage_is_rejected(self):
        row = self.inputs["candidates"]["candidates"][0]
        row["claim_ids"] = row["claim_ids"][0]
        with self.assertRaises(ValueError):
            self.snap()

    def test_relief_reference_namespaces_are_not_interchangeable(self):
        row = self.inputs["relief_paths"]["relief_paths"][0]
        evidence = self.inputs["claim_registry"]["claims"][0]["support_evidence_ids"][0]
        row["support_claim_ids"] = [evidence]
        row["support_evidence_ids"] = []
        self.assertNotIn(row["relief_path_id"], self.snap()["relief_path_ids"])
        row["support_claim_ids"] = []
        row["support_evidence_ids"] = [self.inputs["claim_registry"]["claims"][0]["claim_id"]]
        self.assertNotIn(row["relief_path_id"], self.snap()["relief_path_ids"])
