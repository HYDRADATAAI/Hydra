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
        ("utilization", True),
        ("utilization", "0.5"),
        ("market_share", -0.01),
        ("market_share", 1.01),
        ("market_share", float("nan")),
        ("market_share", float("inf")),
        ("market_share", float("-inf")),
        ("market_share", True),
        ("market_share", "0.5"),
    ],
)
def test_snapshot_fractions_reject_invalid_values(field, value):
    snapshot = Snapshot(date(2020, 1, 1), known_at=date(2020, 1, 1), **{field: value})
    graph = DependencyGraph(
        [Node("n", "resource", "Resource", snapshots=(snapshot,), provenance=(P,))],
        [],
    )

    assert f"n: snapshot {field} must be a numeric fraction in [0,1]" in validate_graph(graph)


@pytest.mark.parametrize("field", ["utilization", "market_share"])
@pytest.mark.parametrize("value", [None, 0.0, 1.0])
def test_snapshot_fraction_boundaries_remain_valid(field, value):
    snapshot = Snapshot(date(2020, 1, 1), known_at=date(2020, 1, 1), **{field: value})
    graph = DependencyGraph(
        [Node("n", "resource", "Resource", snapshots=(snapshot,), provenance=(P,))],
        [],
    )

    assert validate_graph(graph) == []
