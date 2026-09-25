# HYDRA Constraint — Historical Physical Dependency Layer

This package adds an isolated historical physical-evidence graph without replacing existing HYDRA systems.

## Scope

It represents the chain:

RESOURCE → SOURCE/DEPOSIT → EXTRACTION → PROCESSING → TRANSPORT → INFRASTRUCTURE → MANUFACTURING → PRODUCT/TECHNOLOGY → COMPANY/COUNTRY DEPENDENCY → BOTTLENECK → SUBSTITUTE → BENEFICIARY.

The model is deliberately evidence-first and non-predictive.

## Temporal semantics

Every historical fact can carry both a validity interval and `known_at`. `DependencyGraph.as_of(T, knowledge_cutoff=T)` therefore excludes evidence not reasonably known by T, supporting point-in-time replay without lookahead.

## Capacity and concentration

Snapshots distinguish nameplate from usable capacity. Edges can carry dependency share/capacity. `hhi()` computes normalized Herfindahl-Hirschman concentration across documented incoming shares.

## Substitution

Substitution is a first-class edge with `substitution_time_days`. This prevents "a substitute exists" from being treated as equivalent to "a substitute can replace lost capacity immediately."

## Failure propagation

`loss_impact(node_id)` returns downstream graph reachability after a physical node is removed. It is structural exposure, not a forecast.

## Provenance and validation

Edges require provenance. Provenance includes publisher, URL, retrieval date, historical `known_at`, optional publication date/locator, and optional evidence hash. Validation rejects dangling edges, invalid temporal intervals, impossible shares/capacities, and unprovenanced edges.

## Historical datasets

`data/historical_physical_dependency.schema.json` is the ingestion contract for sourced historical capacity/dependency records. This commit intentionally does **not** fabricate historical observations merely to populate the schema. Real records should enter only with attributable evidence and historical knowledge dates.

## Coverage gaps

Current implementation is a graph/evidence foundation, not complete domain coverage. Still required before a serious Constraint run:

- sourced historical critical-mineral extraction/refining series;
- oil/gas/refining and pipeline/LNG capacity histories;
- semiconductor fab, packaging and equipment dependencies;
- bulk industrial materials;
- agriculture, fertilizer and water dependencies;
- generation, grid and transmission capacity;
- ports, rail, shipping corridors and chokepoint capacity;
- compute/data-center power and capacity history;
- company/product bill-of-material dependency mappings;
- country/company control and ownership histories;
- measured substitution lead times and qualification constraints.

These are explicitly recorded as gaps rather than silently represented as complete.
