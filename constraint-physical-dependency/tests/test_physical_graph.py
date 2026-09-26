from datetime import date
from hydra_constraint_physical import DependencyGraph, Edge, Node, Provenance, Snapshot, validate_graph

P=Provenance("fixture","https://example.invalid/source","fixture",date(2026,9,25),date(2020,1,1))

def fixture():
    nodes=[
      Node("r","resource","Resource",snapshots=(Snapshot(date(2019,1,1),known_at=date(2019,2,1)),)),
      Node("p","processing","Processor"),
      Node("m","manufacturing","Manufacturer"),
      Node("s","substitute","Substitute"),
      Node("b","beneficiary","Beneficiary"),
    ]
    edges=[
      Edge("e1","r","p","feeds",date(2019,1,1),known_at=date(2019,2,1),share=.7,provenance=(P,)),
      Edge("e2","p","m","supplies",date(2019,1,1),known_at=date(2019,2,1),provenance=(P,)),
      Edge("e3","r","s","substitutable_by",date(2019,1,1),known_at=date(2019,2,1),substitution_time_days=180,provenance=(P,)),
      Edge("e4","s","b","benefits",date(2019,1,1),known_at=date(2019,2,1),provenance=(P,))
    ]
    return DependencyGraph(nodes,edges)

def test_trace_and_impact():
    g=fixture()
    assert any(path[-1].target_id=="m" for path in g.trace("r"))
    assert "m" in g.loss_impact("r")

def test_point_in_time_blocks_lookahead():
    g=fixture()
    assert "r" not in g.as_of(date(2019,1,15),knowledge_cutoff=date(2019,1,15)).nodes
    assert "r" in g.as_of(date(2019,3,1),knowledge_cutoff=date(2019,3,1)).nodes

def test_substitution_time_and_validation():
    g=fixture()
    assert g.substitutes("r")[0].substitution_time_days==180
    assert validate_graph(g)==[]

def test_hhi():
    p=P
    g=fixture()
    g.edges["e5"]=Edge("e5","s","p","feeds",date(2019,1,1),share=.3,provenance=(p,))
    assert round(g.hhi("p","feeds"),2)==.58

def test_point_in_time_reference_resolver():
    g=fixture()
    assert g.resolve_reference("e1", date(2019,1,15), date(2019,1,15)) is None
    kind,obj=g.resolve_reference("e1", date(2019,3,1), date(2019,3,1))
    assert kind=="edge" and obj.edge_id=="e1"

def test_identity_only_node_respects_provenance_knowledge_cutoff():
    future_p=Provenance(
        "future-fixture","https://example.invalid/future","fixture",
        date(2026,9,25),date(2025,1,1)
    )
    g=DependencyGraph([Node("future","infrastructure","Future asset",provenance=(future_p,))],[])
    assert g.resolve_reference("future",date(2020,1,1),date(2020,1,1)) is None
    kind,obj=g.resolve_reference("future",date(2026,1,1),date(2026,1,1))
    assert kind=="node" and obj.node_id=="future"
