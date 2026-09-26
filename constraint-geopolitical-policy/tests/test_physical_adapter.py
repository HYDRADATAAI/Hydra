import unittest
from datetime import date, datetime, timezone

from hydra_constraint_physical import DependencyGraph, Edge, Node, Provenance as PhysicalProvenance
from hydra_constraint_policy.model import (
    EventType, HistoricalEvent, Provenance, Relation, TemporalFacts,
)
from hydra_constraint_policy.physical_adapter import (
    PhysicalBindingError, bind_event_to_physical_graph, trace_event_downstream,
)

UTC=timezone.utc
def dt(s): return datetime.fromisoformat(s).replace(tzinfo=UTC)

P=PhysicalProvenance(
    "physical-fixture","https://example.invalid/physical","fixture",
    date(2026,9,25),date(2020,1,1)
)


def graph():
    nodes=[
        Node("resource:r","resource","Resource R",provenance=(P,)),
        Node("processor:p","processing","Processor P",provenance=(P,)),
        Node("infra:i","infrastructure","Infrastructure I",provenance=(P,)),
        Node("company:c","company","Company C",provenance=(P,)),
        Node("bottleneck:b","bottleneck","Bottleneck B",provenance=(P,)),
        Node(
            "infra:future","infrastructure","Future-only-known asset",
            provenance=(PhysicalProvenance(
                "future","https://example.invalid/future","fixture",
                date(2026,9,25),date(2024,1,1)
            ),)
        ),
    ]
    edges=[
        Edge("dep:e1","resource:r","processor:p","feeds",date(2020,1,1),known_at=date(2020,1,1),provenance=(P,)),
        Edge("dep:e2","processor:p","infra:i","supplies",date(2020,1,1),known_at=date(2020,1,1),provenance=(P,)),
        Edge("dep:e3","infra:i","company:c","supplies",date(2020,1,1),known_at=date(2020,1,1),provenance=(P,)),
        Edge("constraint:e4","bottleneck:b","infra:i","constrains",date(2020,1,1),known_at=date(2020,1,1),provenance=(P,)),
    ]
    return DependencyGraph(nodes,edges)


def policy_event(relations):
    p=Provenance(
        "official","doc-1",dt("2022-01-01T12:00:00"),dt("2022-01-01T12:00:00"),
        "1","sha256:policy"
    )
    return HistoricalEvent(
        "evt-policy",EventType.EXPORT_CONTROL,"Policy event",
        TemporalFacts(dt("2022-01-01T12:00:00"),dt("2022-02-01T00:00:00")),
        (p,),tuple(relations),
    )


def rel(kind, entity):
    return Relation(kind,entity,.9,("doc-1",))


class PhysicalAdapterTests(unittest.TestCase):
    def test_real_physical_ids_bind_by_kind(self):
        e=policy_event([
            rel("RESOURCE","resource:r"),
            rel("INFRASTRUCTURE","infra:i"),
            rel("DEPENDENCY","dep:e3"),
            rel("CONSTRAINT","bottleneck:b"),
        ])
        bindings=bind_event_to_physical_graph(e,graph())
        self.assertEqual(4,len(bindings))
        self.assertEqual(
            {"node","edge"},
            {b.reference_type for b in bindings},
        )

    def test_unknown_reference_fails_closed(self):
        e=policy_event([rel("RESOURCE","resource:missing")])
        with self.assertRaises(PhysicalBindingError):
            bind_event_to_physical_graph(e,graph())

    def test_wrong_physical_kind_fails_closed(self):
        e=policy_event([rel("RESOURCE","company:c")])
        with self.assertRaises(PhysicalBindingError):
            bind_event_to_physical_graph(e,graph())

    def test_future_known_physical_identity_cannot_leak(self):
        e=policy_event([rel("INFRASTRUCTURE","infra:future")])
        with self.assertRaises(PhysicalBindingError):
            bind_event_to_physical_graph(e,graph())

    def test_constraint_can_reference_constrains_edge(self):
        e=policy_event([rel("CONSTRAINT","constraint:e4")])
        b=bind_event_to_physical_graph(e,graph())[0]
        self.assertEqual("edge",b.reference_type)
        self.assertEqual("constrains",b.physical_kind)

    def test_policy_event_traverses_downstream_physical_chain(self):
        e=policy_event([rel("RESOURCE","resource:r")])
        traced=trace_event_downstream(e,graph())
        self.assertIn(("dep:e1","dep:e2","dep:e3"),traced["resource:r"])

if __name__=="__main__":
    unittest.main()
