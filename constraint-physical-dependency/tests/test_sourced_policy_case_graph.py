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
