import copy
import json
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_replay.outcome_mapping import (
    OutcomeMappingError,
    POSITIVE_CONSTRAINT_RULESET_V1,
    load_outcome_mapping_bundle,
    map_positive_constraint_outcome,
)


ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_OUTCOME_MAPPING_BATCH008_20260926.json"


class OutcomeMappingGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.declared_at,cls.records=load_outcome_mapping_bundle(BUNDLE)

    def by_id(self,case_id):
        return next(r for r in self.records if r.case_id==case_id)

    def test_three_candidates_map_conservatively_to_partial_realization(self):
        self.assertEqual(3,len(self.records))
        for record in self.records:
            with self.subTest(case=record.case_id):
                decision=map_positive_constraint_outcome(record)
                self.assertEqual(POSITIVE_CONSTRAINT_RULESET_V1,decision.rule_set_id)
                self.assertEqual("PARTIAL_REALIZATION",decision.outcome_class)

    def test_true_positive_requires_explicit_target_and_clean_attribution(self):
        r=self.records[0]
        synthetic=type(r)(
            case_id="synthetic-contract-test",
            rule_set_id=r.rule_set_id,
            mechanism_observed=True,
            direction_consistent=True,
            explicit_numeric_target_defined=True,
            target_met=True,
            explicit_horizon_defined=False,
            horizon_met=None,
            causal_attribution_clean=True,
            outcome_observation_complete=True,
            contradiction_open=False,
            evidence_source_ids=("synthetic-source",),
            rationale="Synthetic contract test only.",
        )
        self.assertEqual("TRUE_POSITIVE",map_positive_constraint_outcome(synthetic).outcome_class)

    def test_missing_target_cannot_smuggle_target_met(self):
        raw=json.loads(BUNDLE.read_text(encoding="utf-8"))
        raw["cases"][0]["target_met"]=True
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"
            p.write_text(json.dumps(raw),encoding="utf-8")
            with self.assertRaisesRegex(OutcomeMappingError,"target_met forbidden"):
                load_outcome_mapping_bundle(p)

    def test_open_contradiction_maps_to_unevaluable(self):
        r=self.records[0]
        synthetic=type(r)(
            case_id="synthetic-contradiction-test",
            rule_set_id=r.rule_set_id,
            mechanism_observed=True,
            direction_consistent=True,
            explicit_numeric_target_defined=False,
            target_met=None,
            explicit_horizon_defined=False,
            horizon_met=None,
            causal_attribution_clean=True,
            outcome_observation_complete=True,
            contradiction_open=True,
            evidence_source_ids=("synthetic-source",),
            rationale="Synthetic contract test only.",
        )
        self.assertEqual("UNEVALUABLE",map_positive_constraint_outcome(synthetic).outcome_class)

    def test_wrong_timing_requires_explicit_horizon(self):
        r=self.records[0]
        synthetic=type(r)(
            case_id="synthetic-timing-test",
            rule_set_id=r.rule_set_id,
            mechanism_observed=True,
            direction_consistent=True,
            explicit_numeric_target_defined=False,
            target_met=None,
            explicit_horizon_defined=True,
            horizon_met=False,
            causal_attribution_clean=True,
            outcome_observation_complete=True,
            contradiction_open=False,
            evidence_source_ids=("synthetic-source",),
            rationale="Synthetic contract test only.",
        )
        self.assertEqual("RIGHT_MECHANISM_WRONG_TIMING",map_positive_constraint_outcome(synthetic).outcome_class)


if __name__=="__main__":
    unittest.main()
