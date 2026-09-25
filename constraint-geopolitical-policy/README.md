# HYDRA Constraint — Geopolitical & Policy Historical Layer

Status: **bounded source implementation; not a claim of production integration**.

This component models historical policy/geopolitical evidence for Constraint without political prediction. It is deliberately point-in-time and provenance-first.

## Audit / authority map

Repository inspection on 2026-09-25 found the public HYDRA root README and its documented authority/provenance/fail-closed contracts. GitHub reported the repository code-search index unavailable, so absence of search hits was **not** treated as proof that private/local Constraint implementations do not exist. Root-level `src/`, `constraint/`, `tests/`, and `docs/` paths were not present on the public default branch.

Accordingly this pass does **not** replace or claim authority over the full Constraint runtime. It creates a bounded component that is designed to bind to the existing canonical entity/provenance/history systems when those are present in the integration workspace.

Reuse contract:
- canonical entity IDs remain owned by existing HYDRA entity resolution;
- geography/resources/infrastructure/dependencies remain references, not copied entities;
- provenance remains explicit and source-versioned;
- replay is fail-closed at `known_at` / `available_at`;
- unsupported causality and motive claims are rejected.

## Event chain

`EVENT → ACTOR → LOCATION → STRATEGIC_ASSET → RESOURCE/INFRASTRUCTURE → DEPENDENCY → POLICY/CONFLICT ACTION → CONSTRAINT → OBSERVED OUTCOME`

Relations are sparse: unknown values are not converted to false or zero.

## Four clocks

- `known_at`: when evidence was legitimately knowable.
- `effective_at`: when an action became legally/operationally effective.
- `observed_at`: when a consequence was observed.
- `resolved_at`: when the action/disruption ended where applicable.

They are independent semantic clocks. Replay eligibility is governed by evidence availability, not hindsight.

## Claim discipline

Claims are classified as documented action, documented effect, attributed explanation, analytical inference, or unknown. Motive/explanatory claims require attribution. Causal edges require explicit evidence IDs.

## Historical fixtures

`data/historical_case_studies.json` intentionally contains **case shapes only**, not invented geopolitical facts. Factual population belongs in a sourced ingestion pass.

## Tests

From this directory:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\\src').Path
python -m unittest discover -s tests -t . -v
```

The tests exercise point-in-time cutoff, clock separation, provenance, causal/motive quarantine, relationship evidence, warning-sign replay, and determinism.

## Physical dependency integration

This PR is stacked on the historical physical dependency foundation. Physical `Relation.entity_id` references are resolved through `DependencyGraph.resolve_reference(...)` rather than by reading graph internals or copying its schema.

`physical_adapter.py` enforces point-in-time resolution and type compatibility for resource, infrastructure, strategic-asset, dependency, and bottleneck/constraint references. A policy event can then traverse the real physical graph structurally through `trace_event_downstream()`.

The binding uses the event's `KNOWN_AT` as the knowledge cutoff while physical validity defaults to `EFFECTIVE_AT` (then `OBSERVED_AT`, then `KNOWN_AT`). This lets an already-announced future-effective action bind to evidence that was genuinely known at announcement time without importing later evidence.

The component remains **THIN in historical domain coverage** until sourced geopolitical case records are populated. That is a data-coverage gap, not an unresolved policy↔physical API gap.
