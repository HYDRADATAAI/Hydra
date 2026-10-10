from datetime import date

import pytest

from hydra_constraint_physical import DependencyGraph, Node, Provenance, Snapshot, validate_graph


P = Provenance("fixture", "https://example.invalid/source", "fixture", date(2026, 9, 25), date(2020, 1, 1))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("utilization", -0.01),
        ("utilization", 1.01),
        ("utilization", float("nan")),
        ("utilization", float("inf")),
        ("utilization", float("-inf")),
        ("market_share", -0.01),
        ("market_share", 1.01),
        ("market_share", float("nan")),
        ("market_share", float("inf")),
        ("market_share", float("-inf")),
    ],
)
def test_snapshot_fractions_reject_values_outside_unit_interval(field, value):
    snapshot = Snapshot(date(2020, 1, 1), known_at=date(2020, 1, 1), **{field: value})
    graph = DependencyGraph(
        [Node("n", "resource", "Resource", snapshots=(snapshot,), provenance=(P,))],
        [],
    )

    assert f"n: snapshot {field} outside [0,1]" in validate_graph(graph)


@pytest.mark.parametrize("field", ["utilization", "market_share"])
@pytest.mark.parametrize("value", [None, 0.0, 1.0])
def test_snapshot_fraction_boundaries_remain_valid(field, value):
    snapshot = Snapshot(date(2020, 1, 1), known_at=date(2020, 1, 1), **{field: value})
    graph = DependencyGraph(
        [Node("n", "resource", "Resource", snapshots=(snapshot,), provenance=(P,))],
        [],
    )

    assert validate_graph(graph) == []
