import unittest

from hydra_constraint.event_stream import EventNormalizer, IngestError, TargetResolver
from hydra_constraint.runtime import ConstraintRuntime, Node


DUPLICATE_GRAPH = {
    "nodes": [
        {"node_id": "N1", "name": "Original", "jurisdiction": "US"},
        {"node_id": "N1", "name": "Replacement", "jurisdiction": "CN"},
    ],
    "edges": [],
}


class EventStreamDuplicateNodeIdTests(unittest.TestCase):
    def test_event_normalizer_rejects_duplicate_graph_ids(self):
        with self.assertRaisesRegex(IngestError, "duplicate node_id: N1"):
            EventNormalizer(DUPLICATE_GRAPH)

    def test_core_runtime_rejects_duplicate_node_ids(self):
        nodes = [
            Node(node_id="N1", node_class="supplier", name="Original"),
            Node(node_id="N1", node_class="supplier", name="Replacement"),
        ]
        with self.assertRaisesRegex(ValueError, "duplicate node_id: N1"):
            ConstraintRuntime(nodes, [])

    def test_from_dict_rejects_duplicate_node_ids(self):
        graph = {
            "nodes": [
                {"node_id": "N1", "node_class": "supplier", "name": "Original"},
                {"node_id": "N1", "node_class": "supplier", "name": "Replacement"},
            ],
            "edges": [],
        }
        with self.assertRaisesRegex(ValueError, "duplicate node_id: N1"):
            ConstraintRuntime.from_dict(graph)

    def test_target_resolver_rejects_duplicate_graph_ids(self):
        with self.assertRaisesRegex(IngestError, "duplicate node_id: N1"):
            TargetResolver(DUPLICATE_GRAPH)


if __name__ == "__main__":
    unittest.main()
