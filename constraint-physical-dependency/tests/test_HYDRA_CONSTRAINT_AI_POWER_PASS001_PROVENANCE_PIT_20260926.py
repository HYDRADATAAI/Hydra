"""Synthetic regression fixtures; never historical evidence or production population."""
from dataclasses import replace
from datetime import date
import unittest
from hydra_constraint_physical.models import Node, Edge, Snapshot, Provenance
from hydra_constraint_physical.graph import DependencyGraph

PAST = date(2024, 1, 1)
CUT = date(2024, 6, 1)
FUTURE = date(2025, 1, 1)
OLD = Provenance('TEST_FIXTURE_OLD', 'https://example.invalid/fixture', 'TEST_FIXTURE', PAST, PAST)
NEW = replace(OLD, source_id='TEST_FIXTURE_FUTURE', known_at=FUTURE, retrieved_at=FUTURE)

class TestAiPowerOwnerPit(unittest.TestCase):
    def nodes(self):
        return [Node('grid', 'infrastructure', 'SYNTHETIC grid', provenance=(OLD,)),
                Node('compute', 'product_technology', 'SYNTHETIC compute', provenance=(OLD,))]

    def edge(self, **kw):
        return replace(Edge('dependency', 'grid', 'compute', 'supplies', PAST,
                            known_at=PAST, provenance=(OLD,)), **kw)

    def test_snapshot_with_only_future_provenance_is_excluded(self):
        n = Node('facility', 'infrastructure', 'SYNTHETIC facility',
                 snapshots=(Snapshot(PAST, known_at=PAST),), provenance=(NEW,))
        g = DependencyGraph([n])
        self.assertNotIn('facility', g.as_of(CUT, CUT).nodes)
        self.assertEqual('UNKNOWN', g.reference_state_as_of('facility', CUT, CUT))

    def test_snapshot_without_provenance_is_unknown(self):
        n = Node('facility', 'infrastructure', 'SYNTHETIC facility',
                 snapshots=(Snapshot(PAST, known_at=PAST),))
        self.assertEqual('UNKNOWN', DependencyGraph([n]).reference_state_as_of('facility', CUT, CUT))

    def test_future_provenance_not_returned_in_visible_objects(self):
        nodes = [replace(n, provenance=(OLD, NEW)) for n in self.nodes()]
        g = DependencyGraph(nodes, [self.edge(provenance=(OLD, NEW))]).as_of(CUT, CUT)
        for item in [*g.nodes.values(), *g.edges.values()]:
            self.assertEqual((OLD,), item.provenance)

    def test_edge_with_future_only_source_is_unknown(self):
        g = DependencyGraph(self.nodes(), [self.edge(provenance=(NEW,))])
        self.assertNotIn('dependency', g.as_of(CUT, CUT).edges)
        self.assertEqual('UNKNOWN', g.reference_state_as_of('dependency', CUT, CUT))

    def test_missing_endpoint_cannot_report_present(self):
        g = DependencyGraph(self.nodes()[:1], [self.edge()])
        self.assertIsNone(g.resolve_reference('dependency', CUT, CUT))
        self.assertEqual('UNKNOWN', g.reference_state_as_of('dependency', CUT, CUT))

    def test_later_known_revisions_excluded(self):
        # Ten requested attack classes mapped to the existing structural edge clock.
        for attack in ['facility_capacity','completed_project','ownership','power_agreement',
                       'semiconductor_capacity','export_control','water_restriction',
                       'network_upgrade','completion_revision','cancellation']:
            with self.subTest(attack=attack):
                e = self.edge(known_at=FUTURE, attributes={'fixture_attack': attack})
                g = DependencyGraph(self.nodes(), [e])
                self.assertNotIn(e.edge_id, g.as_of(CUT, CUT).edges)
                self.assertEqual('UNKNOWN', g.reference_state_as_of(e.edge_id, CUT, CUT))
                self.assertIn(e.edge_id, g.as_of(FUTURE, FUTURE).edges)

    def test_unknown_and_known_absent_remain_distinct(self):
        g = DependencyGraph(self.nodes(), [self.edge(valid_to=date(2024, 2, 1))])
        self.assertEqual('ABSENT', g.reference_state_as_of('dependency', CUT, CUT))
        self.assertEqual('UNKNOWN', g.reference_state_as_of('unknown-expansion', CUT, CUT))

    def test_conflicting_capacity_snapshots_preserved_with_units(self):
        snapshots = tuple(Snapshot(PAST, known_at=PAST, capacity_nameplate=x, capacity_unit='MW') for x in (100, 85))
        n = replace(self.nodes()[0], snapshots=snapshots)
        view = DependencyGraph([n]).as_of(CUT, CUT)
        self.assertEqual([100, 85], [s.capacity_nameplate for s in view.nodes['grid'].snapshots])
        self.assertTrue(all(s.capacity_unit == 'MW' for s in view.nodes['grid'].snapshots))

    def test_one_expired_constraint_does_not_remove_another(self):
        nodes = self.nodes() + [Node('transformer', 'infrastructure', 'SYNTHETIC transformer', provenance=(OLD,))]
        edges = [self.edge(valid_to=date(2024, 2, 1)),
                 self.edge(edge_id='transformer-dependency', source_id='transformer')]
        view = DependencyGraph(nodes, edges).as_of(CUT, CUT)
        self.assertNotIn('dependency', view.edges)
        self.assertIn('compute', view.loss_impact('transformer'))

if __name__ == '__main__':
    unittest.main()
