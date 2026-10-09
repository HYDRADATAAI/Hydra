import json
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_replay.confidence import (
    ConfidenceEvidence,
    ConfidenceEvidenceError,
    ConfidenceSemantics,
    admissible_confidence_value,
    load_confidence_audit,
    summarize_confidence_audit,
)


ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_CONFIDENCE_ADMISSIBILITY_BATCH008_20260926.json"


class ConfidenceAdmissibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence,cls.mappings=load_confidence_audit(AUDIT)

    def test_current_three_cases_have_no_admissible_numeric_confidence(self):
        summary=summarize_confidence_audit(self.evidence,self.mappings)
        self.assertEqual(3,summary["evidence_count"])
        self.assertEqual(0,summary["admissible_numeric_confidence_count"])
        self.assertEqual(3,summary["nonprobabilistic_or_blocked_count"])
        self.assertTrue(all(admissible_confidence_value(e,self.mappings) is None for e in self.evidence))

    def test_operational_100_percent_is_not_probability(self):
        e=next(x for x in self.evidence if x.case_id=="germany-wilhelmshaven-lng-commissioning-2022-2023")
        self.assertEqual(ConfidenceSemantics.OPERATIONAL_COMMITMENT,e.semantics)
        self.assertIsNone(admissible_confidence_value(e,self.mappings))
        self.assertIn("100 percent",e.statement)

    def test_qualitative_expected_is_not_probability(self):
        e=next(x for x in self.evidence if x.case_id=="suez-ever-given-2021")
        self.assertEqual(ConfidenceSemantics.QUALITATIVE_EXPECTATION,e.semantics)
        self.assertIsNone(admissible_confidence_value(e,self.mappings))

    def test_nonprobabilistic_semantics_reject_numeric_value(self):
        e=self.evidence[0]
        bad=ConfidenceEvidence(
            evidence_id=e.evidence_id+"-bad",
            case_id=e.case_id,
            source_id=e.source_id,
            known_at=e.known_at,
            semantics=e.semantics,
            statement=e.statement,
            numeric_value=0.8,
        )
        with self.assertRaisesRegex(ConfidenceEvidenceError,"non-probabilistic semantics"):
            bad.validate()

    def test_explicit_probability_is_admissible_only_when_declared_as_probability(self):
        e=self.evidence[0]
        good=ConfidenceEvidence(
            evidence_id="synthetic-explicit-probability-contract-test",
            case_id=e.case_id,
            source_id="synthetic-source",
            known_at=e.known_at,
            semantics=ConfidenceSemantics.NUMERIC_PROBABILITY,
            statement="Synthetic contract test only: explicit probability 0.7.",
            numeric_value=0.7,
        )
        self.assertEqual(0.7,admissible_confidence_value(good,{}))

    def test_invalid_probability_range_fails_closed(self):
        e=self.evidence[0]
        bad=ConfidenceEvidence(
            evidence_id="synthetic-invalid-range",
            case_id=e.case_id,
            source_id="synthetic-source",
            known_at=e.known_at,
            semantics=ConfidenceSemantics.NUMERIC_PROBABILITY_RANGE,
            statement="Synthetic contract test only.",
            numeric_low=0.8,
            numeric_high=0.2,
        )
        with self.assertRaisesRegex(ConfidenceEvidenceError,"outside \[0,1\]"):
            bad.validate()


if __name__=="__main__":
    unittest.main()
