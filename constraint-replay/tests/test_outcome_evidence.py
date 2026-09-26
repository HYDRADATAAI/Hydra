import json
import tempfile
import unittest
from pathlib import Path

from hydra_constraint_replay.outcome_evidence import (
    EvidenceRole,
    OutcomeEvidenceError,
    load_outcome_enrichment_bundle,
)


ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/"constraint-replay"/"corpus"/"HYDRA_CONSTRAINT_REPLAY_OUTCOME_ENRICHMENT_BATCH007_20260926.json"


class OutcomeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources,cls.cases=load_outcome_enrichment_bundle(BUNDLE)

    def by_id(self,case_id):
        return next(c for c in self.cases if c.case_id==case_id)

    def test_bundle_shape(self):
        self.assertEqual(10,len(self.sources))
        self.assertEqual(3,len(self.cases))

    def test_hypothesis_sources_predate_outcome_sources(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                first_outcome=min(self.sources[s].available_at for s in case.outcome_source_ids)
                self.assertLess(case.hypothesis_available_at,first_outcome)
                self.assertTrue(all(
                    self.sources[s].role==EvidenceRole.HISTORICAL_HYPOTHESIS
                    for s in case.historical_hypothesis_source_ids
                ))
                self.assertTrue(all(
                    self.sources[s].role==EvidenceRole.OUTCOME
                    for s in case.outcome_source_ids
                ))

    def test_suez_has_operational_metrics_and_market_outcome(self):
        case=self.by_id("suez-ever-given-2021")
        metrics={m.metric:m.value for m in case.metrics}
        self.assertEqual(81,metrics["vessels_transited_day"])
        self.assertEqual(4.8,metrics["net_tonnage_transited_day"])
        self.assertTrue(case.qualitative_outcomes)

    def test_black_sea_has_price_and_throughput_series(self):
        case=self.by_id("black-sea-grain-corridor-2022")
        metrics={m.metric:m.value for m in case.metrics}
        self.assertEqual(-14.5,metrics["world_wheat_price_change"])
        self.assertEqual(9729083,metrics["cumulative_exports"])
        series=case.time_series[0]
        self.assertEqual(9,len(series.points))
        self.assertEqual(4241809,next(p.value for p in series.points if p.period=="2022-10"))

    def test_wilhelmshaven_has_year_one_quantitative_outcomes(self):
        case=self.by_id("germany-wilhelmshaven-lng-commissioning-2022-2023")
        metrics={m.metric:m.value for m in case.metrics}
        self.assertEqual(42,metrics["lng_carriers_received"])
        self.assertEqual(4,metrics["natural_gas_fed_to_grid"])
        self.assertEqual(6,metrics["share_of_german_gas_consumption_2023"])

    def test_digest_tampering_fails_closed(self):
        raw=json.loads(BUNDLE.read_text(encoding="utf-8"))
        raw["sources"][0]["normalized_evidence"] += " tampered"
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"
            p.write_text(json.dumps(raw),encoding="utf-8")
            with self.assertRaisesRegex(OutcomeEvidenceError,"digest mismatch"):
                load_outcome_enrichment_bundle(p)

    def test_hypothesis_after_outcome_fails_closed(self):
        raw=json.loads(BUNDLE.read_text(encoding="utf-8"))
        case=raw["cases"][0]
        case["hypothesis_available_at"]="2021-05-01T00:00:00Z"
        hyp_id=case["historical_hypothesis_source_ids"][0]
        source=next(s for s in raw["sources"] if s["source_id"]==hyp_id)
        source["published_at"]="2021-05-01T00:00:00Z"
        source["available_at"]="2021-05-01T00:00:00Z"
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"
            p.write_text(json.dumps(raw),encoding="utf-8")
            with self.assertRaisesRegex(OutcomeEvidenceError,"not prior to outcome evidence"):
                load_outcome_enrichment_bundle(p)

    def test_metric_source_role_fails_closed(self):
        raw=json.loads(BUNDLE.read_text(encoding="utf-8"))
        case=raw["cases"][0]
        case["metrics"][0]["source_id"]=case["historical_hypothesis_source_ids"][0]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bad.json"
            p.write_text(json.dumps(raw),encoding="utf-8")
            with self.assertRaisesRegex(OutcomeEvidenceError,"metric source not admitted"):
                load_outcome_enrichment_bundle(p)


if __name__=="__main__":
    unittest.main()
