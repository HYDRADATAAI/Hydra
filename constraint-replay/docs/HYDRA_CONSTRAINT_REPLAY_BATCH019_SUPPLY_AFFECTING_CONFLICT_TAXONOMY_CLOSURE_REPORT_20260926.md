# HYDRA Constraint — Supply-Affecting Conflict Taxonomy Closure
## Batch 019 — 2026-09-26

Status: **18 / 18 POLICY EVENT TYPES SOURCED · REPLAY CORPUS UNCHANGED AT 22**

Batch 019 closes the only remaining sourced policy-event taxonomy gap:

`SUPPLY_AFFECTING_CONFLICT`

It does **not** create a 23rd replay/classification case.

## Architecture choice

The governed Batch 015 replay, Batch 016 query, Batch 017 multi-domain orchestration, and Batch 018 operating snapshot are all preserved unchanged.

Batch 019 adds a separately pinned taxonomy supplement:

- one sourced policy case;
- one `SUPPLY_AFFECTING_CONFLICT` event;
- one later observation;
- one bounded physical graph;
- three event-time canonical physical bindings.

The supplement is explicitly excluded from frozen Batch 015 replay membership.

## Historical event

Case:

`ukraine-war-agricultural-supply-shock-2022-taxonomy-supplement`

Event:

`ukraine-war-agricultural-supply-shock-2022-04-26`

Event type:

`SUPPLY_AFFECTING_CONFLICT`

### Primary source

World Bank — 26 April 2022.

The World Bank documented the war in Ukraine as a major commodity supply shock that altered patterns of trade, production, and consumption and materially affected food commodities for which Ukraine and Russia were major producers.

The event is encoded as:

- `effective_at = 2022-02-24`
- `known_at = 2022-04-26`

This preserves the distinction between when the conflict began and when the admitted source evidence became available.

## Later observation

FAO — 5 July 2022.

FAO reported:

- normal Ukrainian grain exports of roughly 6 million tonnes/month;
- March exports: 322,000 tonnes;
- April: 970,000 tonnes;
- May: 1.2 million tonnes;
- June: over 1 million tonnes;
- pre-war total storage capacity: 75 million tonnes;
- storage capacity then available considering directly affected areas: 60.9 million tonnes;
- spring-crop planted area: 19.4% below the prior year.

This later evidence remains outcome/context-side evidence for the supplement and is not leaked into the April event cut.

## Physical representation

Event-time canonical bindings:

- `resource:ukraine-grain-supply-conflict-2022`
- `extraction:ukraine-agricultural-production-conflict-2022`
- `bottleneck:ukraine-war-agricultural-supply-shock-2022`

Later-known physical identities include:

- `transport:ukraine-grain-export-logistics-conflict-2022`
- `infrastructure:ukraine-grain-storage-conflict-2022`

Those July-known transport/storage identities are intentionally absent from the April point-in-time view.

## Replay boundary

The supplement case is **not** admitted into:

`HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl`

The replay corpus remains:

- 22 cases;
- 82 replay cuts;
- 31 replay-bound executable policy events;
- 17 PARTIAL_REALIZATION;
- 5 UNEVALUABLE;
- 0 calibrated cases.

The taxonomy supplement exists only to close evidence breadth for the policy event taxonomy.

## Operating successor

Batch 019 adds operating report contract v2:

`hydra-constraint-operating-report/v2`

Canonical successor snapshot:

`constraint-replay/operating/HYDRA_CONSTRAINT_BATCH019_OPERATING_SNAPSHOT_20260926.json`

Snapshot digest:

`4e6d3de489457c125d27aa243f983891c0ee988a4b0671b6d496d4c00125fa03`

### Readiness change

Batch 018:

- FULL: 4
- THIN: 1
- EMPTY: 1
- MISSING: 3
- DUPLICATE_STALE: 1

Batch 019:

- **FULL: 5**
- **THIN: 0**
- EMPTY: 1
- MISSING: 3
- DUPLICATE_STALE: 1

The only dimension that changes is:

`policy_event_taxonomy_sourced_coverage`

from:

`THIN — 17/18`

to:

`FULL — 18/18`

## Remaining blockers

Closing taxonomy breadth does not change:

### Probabilistic calibration

Still:

`EMPTY`

Blocker:

`NO_ADMISSIBLE_NUMERIC_HISTORICAL_CONFIDENCE`

### Live current-data ingestion

Still:

`MISSING`

Blocker:

`NO_LIVE_CURRENT_INGESTION_PROOF_IN_PUBLIC_RUNTIME`

### Canonical mutation authority

Still:

`MISSING` intentionally.

### T6 activation

Still:

`DORMANT_NOT_ACTIVATED`

No runtime binding or activation authority is created.

### Legacy replay evaluation report

Still:

`DUPLICATE_STALE`

The supplement does not rewrite historical foundation artifacts.

## Validation

Batch 019 tests require:

- policy bundle validation;
- physical graph validation;
- exactly one supplement case;
- exactly one `SUPPLY_AFFECTING_CONFLICT` event;
- exactly one later observation;
- exactly three event-time canonical physical bindings;
- April event-time view cannot see July-known export-logistics/storage identities;
- downstream structural reachability from the conflict bottleneck;
- supplement case absent from the frozen 22 replay IDs;
- successor snapshot reports 18/18 sourced event types;
- readiness contains no THIN dimension;
- only the five pre-existing non-taxonomy gaps remain;
- calibration and T6 states remain unchanged;
- successor snapshot bytes/digest and all authority pins remain deterministic.

## Dedicated CI

Workflow:

`.github/workflows/constraint-policy-taxonomy-closure.yml`

It:

1. installs the stacked policy/physical/replay packages;
2. regenerates the Batch 019 successor operating snapshot;
3. validates the Batch 019 operating manifest;
4. validates the supply-affecting-conflict policy/physical supplement;
5. validates the operating taxonomy closure.

## Current interpretation

The current policy event taxonomy is now fully sourced for at least one historical example per event type:

**18 / 18**

That does not mean the corpus is broad enough for every geography, actor, mechanism, or market context.

It means the explicit event-type breadth gap identified by Batch 018 is closed.

## Next material step

Do not add another event-type coverage batch.

The remaining operating gaps are now materially different:

- probabilistic calibration;
- live/current ingestion;
- canonical mutation authority;
- T6 activation;
- stale historical reporting artifact.

The next useful work should address one of those distinct gaps or integrate additional authoritative Constraint domains beyond the current policy/physical/replay stack.
