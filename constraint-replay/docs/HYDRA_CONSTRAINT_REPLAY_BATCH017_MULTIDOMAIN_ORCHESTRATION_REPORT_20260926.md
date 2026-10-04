# HYDRA Constraint — Multi-Domain Read-Only Orchestration
## Batch 017 — 2026-09-26

Status: **READ-ONLY / MULTI-DOMAIN / AUTHORITY-PRESERVING**

Batch 017 creates one deterministic consumer view across the current historical Constraint domains:

- governed replay/query state;
- geopolitical/policy historical events;
- sourced physical-dependency graphs.

It does not create a parallel policy schema, physical schema, replay schema, canonical store, or T6 runtime.

## Authority ownership

Batch 017 reuses existing package ownership.

### Replay

`constraint-replay` owns:

- replay-ready history;
- governed historical classifications;
- Batch 015 deterministic aggregate replay;
- Batch 016 read-only replay query semantics.

### Policy

`constraint-geopolitical-policy` owns:

- HistoricalEvent;
- TemporalFacts;
- policy/geopolitical provenance;
- case-bundle validation;
- policy → physical relation semantics.

Batch 017 loads policy bundles only through:

- `load_sourced_case_bundle()`;
- `events_from_sourced_case_bundle()`.

### Physical

`constraint-physical-dependency` owns:

- physical node/edge schemas;
- point-in-time physical validity;
- canonical physical reference resolution;
- sourced physical-graph validation.

Batch 017 loads physical graphs only through:

`load_sourced_policy_case_graph()`

Policy events are joined to physical state only through the existing:

- `bind_event_to_physical_graph()`;
- `trace_event_downstream()`.

Batch 017 does not read a copied physical ontology or invent replacement entity IDs.

## Source-pair architecture

The orchestrator preserves the original four bounded integration pairs:

1. Batch 001 policy bundle ↔ Batch 001 physical graph
2. Batch 002 policy bundle ↔ Batch 002 physical graph
3. Batch 003 policy bundle ↔ Batch 003 physical graph
4. Batch 004 policy bundle ↔ Batch 004 physical graph

It deliberately does not construct a synthetic cross-batch mega-graph.

Each historical case is resolved against the physical graph that originally admitted its canonical relations.

## Frozen join invariants

The Batch 017 runtime manifest pins:

- 4 policy bundles;
- 4 sourced physical graphs;
- Batch 016 replay-query manifest;
- Batch 017 implementation module;
- Batch 017 CLI;
- package export;
- request/response contracts.

The expected joined state is:

- cases: **22**
- executable policy events: **31**
- original policy observations: **9**
- policy → physical bindings: **51**
- unique bound physical entity IDs: **47**
- source pairs: **4**
- replay cuts: **82**
- replay outcome classes:
  - 17 PARTIAL_REALIZATION
  - 5 UNEVALUABLE
- calibrated cases: **0**

The service refuses construction if those counts drift.

## Read-only contract

Contract version:

`hydra-constraint-multidomain-readonly/v1`

Mode:

`READ_ONLY_MULTIDOMAIN_HISTORICAL`

Every response inherits the Batch 016 inert capability state:

- canonical promotion: false
- canonical-store mutation: false
- external actions: false
- model training: false
- ranking: false
- trading: false

## Operations

### summary

Returns one joined aggregate view containing:

- Batch 015 replay summary;
- policy case/event/observation counts;
- policy event-type counts;
- physical binding count;
- unique bound physical entity count;
- source-pair count;
- multi-domain join integrity.

### integrity

Returns:

- Batch 016 replay-query integrity;
- Batch 017 join integrity;
- Batch 017 manifest identity;
- T6 status.

### case

Exact case-ID query returning:

- frozen replay classification row;
- source-pair identity;
- policy binding status;
- executable policy events;
- known/effective/observed/resolved clocks;
- canonical physical bindings;
- downstream structural edge paths;
- original policy observations.

Physical downstream paths are structural reachability evidence, not forecasts.

### entity_usage

Exact canonical physical entity-ID lookup across policy events.

Returns:

- cases/events that referenced the entity;
- relation kind;
- relation confidence;
- physical reference type/kind;
- downstream structural paths as-of the historical event.

Unknown entities fail closed.

### list_cases

Cross-domain deterministic filtering by:

- replay outcome class;
- policy event type;
- canonical physical entity ID;
- bounded result limit.

## T6 boundary

Repository audit confirmed that:

`t6-fail-closed-validator`

is explicitly:

`SOURCE-ONLY, DORMANT, NOT ACTIVATED`

and its dormant adapter refuses runtime execution.

Batch 017 therefore records:

- T6 status: `DORMANT_NOT_ACTIVATED`
- runtime binding created: false
- activation authority granted: false

The orchestrator never invokes or prepares the T6 dormant adapter.

## Fail-closed behavior

Service construction fails if:

- Batch 016 replay query cannot validate Batch 015;
- Batch 017 implementation/contract pins drift;
- policy or physical source-pair pins drift;
- policy bundle validation fails;
- physical graph validation fails;
- replay and policy case sets differ;
- an executable case has no policy events;
- a policy event fails canonical physical binding;
- any event resolves to zero physical bindings;
- joined counts differ from the manifest.

Query execution fails on:

- unknown operations;
- unknown request fields;
- unknown case IDs;
- unknown physical entity IDs;
- invalid traversal depth;
- malformed filters or limits.

## Integration proof

Tests are split by authority boundary.

### Replay package tests

Validate:

- Batch 017 implementation pins;
- request/response contract pins;
- all four source-pair pins;
- Batch 016 replay-query manifest pin;
- frozen joined counts;
- inert capabilities;
- T6 dormant status.

These tests do not require policy/physical packages to be installed.

### Stacked policy/physical/replay tests

Instantiate the real multi-domain service after all three packages are installed.

They prove:

- 22-case replay/policy equality;
- 31 executable policy events;
- 9 policy observations;
- 51 canonical physical bindings;
- 47 unique bound entities;
- Suez case joins replay + policy + physical state;
- `infrastructure:suez-canal` resolves through canonical physical binding;
- EXPORT_CONTROL filtering crosses policy and replay;
- physical-entity filtering is exact;
- the five UNEVALUABLE replay cases remain five;
- unknown cases/entities fail closed;
- authority-smuggling query fields fail closed;
- T6 remains dormant.

## CLI

Script:

`constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH017_multidomain_readonly_20260926.py`

Examples:

```bash
python constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH017_multidomain_readonly_20260926.py summary

python constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH017_multidomain_readonly_20260926.py case suez-ever-given-2021 --max-depth 3

python constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH017_multidomain_readonly_20260926.py entity infrastructure:suez-canal --max-depth 3

python constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH017_multidomain_readonly_20260926.py list --event-type EXPORT_CONTROL
```

The CLI requires the stacked Constraint packages installed together, as done by the existing cross-layer integration workflow.

## What Batch 017 accomplishes

A single read-only consumer can now answer:

- What is the governed replay result for this historical case?
- Which policy events belong to it?
- What physical entities were canonically bound at the historical cutoff?
- What downstream structural paths were reachable?
- Which cases involve a specific event type?
- Which cases use a specific canonical physical entity?
- Is the replay/policy/physical join still fully valid?

without duplicating domain schemas or bypassing their validators.

## What Batch 017 does not claim

This is not:

- a canonical production runtime;
- a live external service;
- T6 activation;
- a trading system;
- a ranking engine;
- a mutation interface;
- a probabilistically calibrated forecasting system.

It is an authority-preserving read-only orchestration layer over the current historical Constraint evidence stack.

## Next material step

If Batch 017 is green, the next useful work is a broader Constraint operating/reporting layer that can consume this joined view alongside additional Constraint domains.

Do not activate T6 or create mutation authority merely because the read-only orchestration works.
