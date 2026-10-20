# HYDRA Constraint — Operating & Readiness Report
## Batch 018 — 2026-09-26

Status: **PASS_WITH_EXPLICIT_BLOCKERS**

Batch 018 creates the first deterministic operating/readiness layer over the current joined historical Constraint stack.

It does not change historical classifications, policy evidence, physical graphs, replay outcomes, or authority.

## Current governed state

The operating snapshot is generated from the Batch 017 multi-domain read-only view.

Current state:

- historical cases: **22**
- point-in-time replay cuts: **82**
- executable policy events: **31**
- original policy observations: **9**
- policy → physical canonical bindings: **51**
- unique bound physical entity IDs: **47**
- policy/physical source pairs: **4**
- `PARTIAL_REALIZATION`: **17**
- `UNEVALUABLE`: **5**
- calibrated historical cases: **0**

Canonical operating snapshot:

`constraint-replay/operating/HYDRA_CONSTRAINT_BATCH018_OPERATING_SNAPSHOT_20260926.json`

Snapshot digest:

`6d767e34f1f644ae5e4716d907c887425fdce0c15fbf521af530d5e50f0891b0`

## Readiness classification

Batch 018 uses the established operating labels:

- FULL
- THIN
- EMPTY
- MISSING
- DUPLICATE_STALE

The labels are dimension-specific. They are not collapsed into one broad production-readiness claim.

### FULL — current declared scope

#### Historical case classification

Status: **FULL**

Scope:

`CURRENT_22_CASE_REPLAY_CORPUS`

Evidence:

- 22 / 22 current replay-ready cases have governed classifications;
- 17 partial realizations;
- 5 unevaluable;
- classification coverage = 100%.

This does not imply probabilistic calibration.

#### Deterministic historical replay execution

Status: **FULL**

Scope:

`BATCH015_FROZEN_RUN`

Evidence:

- 82 replay cuts;
- exact case-set equality;
- source bundle pins valid;
- classified governing-artifact pins valid;
- zero classification blockers;
- deterministic Batch 015 CI replay contract.

#### Policy → physical binding

Status: **FULL**

Scope:

`CURRENT_22_CASE_CORPUS`

Evidence:

- 31 executable policy events;
- all 31 physically bound;
- 51 canonical bindings;
- 47 unique bound physical entity IDs.

#### Read-only query access

Status: **FULL**

Scope:

`BATCH016_REPLAY_AND_BATCH017_MULTIDOMAIN`

Evidence:

- read-only replay query service;
- read-only multi-domain policy/physical/replay orchestration;
- canonical mutation disabled;
- canonical promotion disabled;
- trading disabled;
- external actions disabled.

## THIN

### Policy event taxonomy sourced coverage

Status: **THIN**

Current taxonomy:

- 18 event types.

Sourced current corpus:

- 17 event types.

Missing:

`SUPPLY_AFFECTING_CONFLICT`

Blocker:

`NO_SOURCED_SUPPLY_AFFECTING_CONFLICT_CASE`

This is a corpus-coverage gap, not a missing enum or schema gap.

## EMPTY

### Probabilistic calibration

Status: **EMPTY**

Current state:

- calibrated historical cases: 0;
- Brier score: null;
- no admitted historic numeric confidence values.

Blocker:

`NO_ADMISSIBLE_NUMERIC_HISTORICAL_CONFIDENCE`

Underlying calibration blockers:

- `NO_PRECOMMITTED_CONFIDENCE_SOURCE`
- `NO_SOURCE_GROUNDED_CONFIDENCE_VALUE`

The historical corpus remains useful for governed mechanism classification and evidence-availability analysis, but not for probability calibration.

## MISSING

### Live current-data ingestion

Status: **MISSING**

Scope:

`PUBLIC_CONSTRAINT_RUNTIME`

The current public Constraint evidence proves historical sourced ingestion and deterministic replay.

It does not prove a live/current-data ingestion runtime for this Constraint stack.

Blocker:

`NO_LIVE_CURRENT_INGESTION_PROOF_IN_PUBLIC_RUNTIME`

### Canonical mutation runtime

Status: **MISSING**

Intentional: **yes**

Current authority:

- canonical promotion: false;
- canonical-store mutation: false.

Blocker:

`NO_CANONICAL_MUTATION_AUTHORITY`

Read-only orchestration working correctly is not authority to mutate canonical state.

### T6 activation

Status: **MISSING**

Intentional: **yes**

Current state:

`DORMANT_NOT_ACTIVATED`

- runtime binding created: false;
- activation authority granted: false.

Blocker:

`T6_ACTIVATION_NOT_AUTHORIZED`

Batch 018 does not infer activation from the presence of a working read-only operating layer.

## DUPLICATE_STALE

### Legacy replay evaluation report

Artifact:

`constraint-replay/EVALUATION_REPORT.md`

Status:

`DUPLICATE_STALE`

The historical report says:

> Real historical gold corpus: NOT YET POPULATED

That statement was historically valid for the earlier foundation stage, but it no longer represents the current repository state.

Current state:

- 22 classified historical cases;
- 82 replay cuts;
- deterministic aggregate replay;
- read-only replay query;
- multi-domain policy/physical/replay orchestration.

The legacy report is preserved unchanged as historical evidence.

It is not the current operating authority.

Blocker:

`LEGACY_REPORT_PREDATES_BATCH005_TO_BATCH017_STATE`

## Unevaluable cases

The five current `UNEVALUABLE` cases are not grouped together without explanation.

### CHIPS

Reason:

`OPEN_EXPLICIT_HORIZON`

The selected historical hypothesis used a ten-year outcome horizon that remains open.

### WTO rare-earths implementation

Reason:

`CONTESTED_IMPLEMENTATION_COMPLIANCE`

The authoritative WTO record preserves disagreement over full compliance.

### Japan–Korea export-control normalization

Reason:

`CONFLICTING_OFFICIAL_NORMALIZATION_CHARACTERIZATION`

Korean and Japanese official descriptions of the normalization state materially differed.

### Eastern Mediterranean drilling dispute

Reason:

`UNRESOLVED_LEGAL_TERRITORIAL_RESOURCE_DISPUTE`

The later evidence does not resolve the underlying legal/territorial/resource claims.

### CBAM

Reason:

`INCOMPLETE_MODELED_ECONOMIC_OUTCOME_WINDOW`

Operational rollout is observed, but the modeled medium-term trade/export/emissions effects are not yet resolved by the admitted evidence.

## Fail-closed operating contract

Batch 018 refuses to serve an operating snapshot when:

- Batch 017 multi-domain orchestration cannot validate;
- Batch 018 implementation pins drift;
- the Batch 017 authority manifest pin drifts;
- the preserved legacy-report pin drifts;
- current joined counts diverge from the manifest;
- taxonomy coverage changes without a successor operating snapshot;
- readiness-status counts diverge;
- the committed operating snapshot differs from the live generated state;
- snapshot Git blob or SHA-256 digest drifts.

## Operating queries

The Batch 018 service exposes:

- `snapshot()`
- `readiness()`
- `gaps()`
- exact `dimension(name)`

It remains fully read-only.

## Dedicated CI

Workflow:

`.github/workflows/constraint-operating-report.yml`

The workflow:

1. installs the stacked physical, replay and policy packages;
2. regenerates the Batch 018 operating snapshot;
3. compares it byte-for-byte with the committed snapshot;
4. validates the operating manifest/pins;
5. runs stacked operating integration tests.

The older Batch 015/016 pinned workflows are not modified.

## Operating conclusion

The historical Constraint stack is now strong enough to support a deterministic operating view, but it is not a live production/canonical runtime.

Current high-level interpretation:

- historical replay/classification: **FULL for current corpus**
- policy/physical binding: **FULL for current corpus**
- read-only query/orchestration: **FULL**
- sourced event-taxonomy breadth: **THIN**
- probabilistic calibration: **EMPTY**
- live current-data ingestion: **MISSING**
- canonical mutation authority: **MISSING intentionally**
- T6 activation: **MISSING intentionally / dormant**
- legacy foundation report: **DUPLICATE_STALE**

## Next material work

The highest-value next work is not another historical replay batch.

Candidates:

1. add a defensible sourced `SUPPLY_AFFECTING_CONFLICT` historical case to close the one taxonomy breadth gap;
2. build a broader Constraint operating layer that includes additional non-policy domains when they are present and authoritative;
3. integrate real live/current ingestion when its source authority and runtime contracts exist;
4. acquire authentic historical probability provenance for calibrated evaluation;
5. separately decide whether any T6 activation authority exists.

Do not infer production readiness, canonical mutation authority, or trading authority from this operating report.
