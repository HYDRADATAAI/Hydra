# HYDRA Constraint — Geopolitical & Policy Historical Layer

Status: **bounded source implementation; not a claim of production integration**.

This component models historical policy/geopolitical evidence for Constraint without political prediction. It is deliberately point-in-time and provenance-first.

## Audit / authority map

Repository inspection on 2026-09-25 found the public HYDRA root README and its documented authority/provenance/fail-closed contracts. GitHub reported the repository code-search index unavailable, so absence of search hits was **not** treated as proof that private/local Constraint implementations do not exist. Root-level `src/`, `constraint/`, `tests/`, and `docs/` paths were not present on the public default branch.

Accordingly this pass does **not** replace or claim authority over the full Constraint runtime. On the stacked integration branch it binds directly to the current historical physical-dependency package and historical replay package while preserving their ownership of physical IDs and replay evidence semantics.

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

## Historical case studies

Two data surfaces are intentionally separate:

- `data/historical_case_studies.json` is the mechanism-coverage template.
- `data/sourced_historical_cases.json` contains the first provenance-bearing point-in-time cases.

The sourced bundle currently covers four different mechanisms:

1. 2022 U.S. semiconductor export controls.
2. 2022 EU restrictions on specified Russian-origin oil imports.
3. the 2021 Suez Canal / Ever Given shipping disruption and later observed freight-rate effect.
4. 2022 U.S. CHIPS industrial policy and an initial implementation observation.

Every source record carries a publication/availability timestamp plus a SHA-256 digest over the committed normalized evidence capsule. Event records may not cite evidence whose `available_at` is after the event's `known_at`.

These four cases are now `BOUND_MINIMAL_CANONICAL_SUBGRAPH`. Their event relations point only to physical IDs present in the sourced physical subgraph owned by the physical-dependency package. The bindings are deliberately minimal: descriptive hints are not promoted into additional supply-chain links unless the evidence supports them.

## Tests

From this directory:

```powershell
$env:PYTHONPATH=(Resolve-Path '.\\src').Path
python -m unittest discover -s tests -t . -v
```

The tests exercise point-in-time cutoff, clock separation, provenance, causal/motive quarantine, relationship evidence, warning-sign replay, deterministic hashing, sourced-evidence digest integrity, source-availability cutoffs, canonical physical binding, downstream structural traversal, and replay-evidence emission.

## Physical dependency and replay integration

This PR is stacked on the historical physical dependency foundation and also merges the historical replay foundation for integration testing. Physical `Relation.entity_id` references are resolved through `DependencyGraph.resolve_reference(...)` rather than by reading graph internals or copying its schema.

`physical_adapter.py` enforces point-in-time resolution and type compatibility for resource, infrastructure, strategic-asset, dependency, and bottleneck/constraint references. A policy event can then traverse the real physical graph structurally through `trace_event_downstream()`.

The binding uses the event's `KNOWN_AT` as the knowledge cutoff while physical validity defaults to `EFFECTIVE_AT` (then `OBSERVED_AT`, then `KNOWN_AT`). This lets an already-announced future-effective action bind to evidence that was genuinely known at announcement time without importing later evidence.

`to_replay_evidence()` emits `hydra_constraint_replay.models.Evidence` directly; there is no duplicate replay-evidence dataclass in the policy package. Cross-package CI installs and tests the physical, replay, and policy packages together.

The policy → physical → replay integration is executable for the current sourced case set. The component remains **THIN in historical breadth** because four bounded cases do not constitute broad geopolitical/resource/infrastructure coverage. The remaining gap is evidence population at scale, not an unresolved cross-layer API.
