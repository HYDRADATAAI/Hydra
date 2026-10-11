from __future__ import annotations

import unittest

from hydra_constraint.runtime import ConstraintRuntime, Node


class DuplicateNodeIdTests(unittest.TestCase):
    def test_constructor_rejects_conflicting_duplicate_node_ids(self) -> None:
        nodes = [
            Node(node_id="N1", node_class="material", name="First"),
            Node(node_id="N1", node_class="facility", name="Conflicting duplicate"),
        ]

        with self.assertRaisesRegex(ValueError, "duplicate node_id: N1"):
            ConstraintRuntime(nodes, [])

    def test_from_dict_rejects_duplicate_node_ids(self) -> None:
        graph = {
            "nodes": [
                {"node_id": "N1", "node_class": "material", "name": "First"},
                {"node_id": "N1", "node_class": "facility", "name": "Conflicting duplicate"},
            ],
            "edges": [],
        }

        with self.assertRaisesRegex(ValueError, "duplicate node_id: N1"):
            ConstraintRuntime.from_dict(graph)


if __name__ == "__main__":
    unittest.main()
