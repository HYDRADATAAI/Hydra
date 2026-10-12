import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from hydra_constraint_physical.sourced_case_graph import (
    SourcedGraphValidationError,
    load_sourced_policy_case_graph,
)

DATA_PATH=(
    Path(__file__).resolve().parents[1]
    / "data"
    / "sourced_policy_case_physical_graph.json"
)


class SourcedPolicyCaseGraphTests(unittest.TestCase):
    def test_committed_graph_loads(self):
        g=load_sourced_policy_case_graph(DATA_PATH)
        self.assertIn("infrastructure:suez-canal",g.nodes)
        self.assertIn("resource:russian-origin-crude-oil",g.nodes)
        self.assertIn("manufacturing:prc-semiconductor-fabrication",g.nodes)
        self.assertIn("manufacturing:us-semiconductor-manufacturing",g.nodes)

    def test_point_in_time_hides_future_known_physical_entities(self):
        g=load_sourced_policy_case_graph(DATA_PATH)
        self.assertIsNone(
            g.resolve_reference(
                "manufacturing:prc-semiconductor-fabrication",
                date(2022,10,6),
                date(2022,10,6),
            )
        )
        self.assertIsNotNone(
            g.resolve_reference(
                "manufacturing:prc-semiconductor-fabrication",
                date(2022,10,7),
                date(2022,10,7),
            )
        )

    def test_suez_constraint_traces_to_maritime_traffic(self):
        g=load_sourced_policy_case_graph(DATA_PATH)
        view=g.as_of(date(2021,3,26),date(2021,3,26))
        paths=view.trace("bottleneck:suez-canal-grounding-2021")
        self.assertTrue(any(
            tuple(e.edge_id for e in path)==(
                "edge:suez-grounding-constrains-canal",
                "edge:suez-canal-supplies-maritime-traffic",
            )
            for path in paths
        ))

    def test_resolved_suez_bottleneck_expires(self):
        g=load_sourced_policy_case_graph(DATA_PATH)
        self.assertIsNone(
            g.resolve_reference(
                "bottleneck:suez-canal-grounding-2021",
                date(2021,4,1),
                date(2021,4,1),
            )
        )

    def test_chips_manufacturing_path_is_structural(self):
        g=load_sourced_policy_case_graph(DATA_PATH)
        paths=g.as_of(date(2022,8,9),date(2022,8,9)).trace(
            "manufacturing:us-semiconductor-manufacturing"
        )
        self.assertTrue(any(
            path[-1].target_id=="product:semiconductors"
            for path in paths
        ))

    def test_required_source_dates_are_validated(self):
        cases = (
            ("retrieved_at missing", "retrieved_at", "missing"),
            ("retrieved_at null", "retrieved_at", None),
            ("retrieved_at empty", "retrieved_at", ""),
            ("retrieved_at malformed", "retrieved_at", "not-a-date"),
            ("retrieved_at non-string", "retrieved_at", 20260925),
            ("known_at missing", "known_at", "missing"),
            ("known_at null", "known_at", None),
            ("known_at empty", "known_at", ""),
            ("known_at malformed", "known_at", "not-a-date"),
            ("known_at non-string", "known_at", 20260925),
        )
        for label, field, value in cases:
            with self.subTest(date=label):
                bundle=json.loads(DATA_PATH.read_text(encoding="utf-8"))
                source=bundle["sources"][0]
                if value == "missing":
                    source.pop(field)
                else:
                    source[field]=value
                with tempfile.TemporaryDirectory() as td:
                    path=Path(td)/"invalid-source-date.json"
                    path.write_text(json.dumps(bundle),encoding="utf-8")
                    with self.assertRaisesRegex(
                        SourcedGraphValidationError, field
                    ):
                        load_sourced_policy_case_graph(path)

    def test_malformed_optional_published_at_is_rejected(self):
        bundle=json.loads(DATA_PATH.read_text(encoding="utf-8"))
        bundle["sources"][0]["published_at"]="not-a-date"
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"invalid-published-date.json"
            path.write_text(json.dumps(bundle),encoding="utf-8")
            with self.assertRaisesRegex(
                SourcedGraphValidationError, "published_at"
            ):
                load_sourced_policy_case_graph(path)

    def test_optional_published_at_may_be_absent_or_null(self):
        for mode in ("absent", "null"):
            with self.subTest(mode=mode):
                bundle=json.loads(DATA_PATH.read_text(encoding="utf-8"))
                source=bundle["sources"][0]
                if mode == "absent":
                    source.pop("published_at")
                else:
                    source["published_at"]=None
                with tempfile.TemporaryDirectory() as td:
                    path=Path(td)/"optional-published-date.json"
                    path.write_text(json.dumps(bundle),encoding="utf-8")
                    graph=load_sourced_policy_case_graph(path)
                self.assertIn("infrastructure:suez-canal", graph.nodes)

    def test_digest_tampering_fails_closed(self):
        bundle=json.loads(DATA_PATH.read_text(encoding="utf-8"))
        bundle["sources"][0]["normalized_evidence"] += " tampered"
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"tampered.json"
            path.write_text(json.dumps(bundle),encoding="utf-8")
            with self.assertRaisesRegex(SourcedGraphValidationError,"digest mismatch"):
                load_sourced_policy_case_graph(path)


if __name__=="__main__":
    unittest.main()
