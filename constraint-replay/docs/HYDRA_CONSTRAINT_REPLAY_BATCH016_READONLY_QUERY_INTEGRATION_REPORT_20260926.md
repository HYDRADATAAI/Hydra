# HYDRA Constraint — Read-Only Historical Replay Query Integration
## Batch 016 — 2026-09-26

Status: **READ-ONLY QUERY SURFACE / BATCH 015 PINNED / T6 REMAINS DORMANT**

Batch 016 integrates the completed 22-case historical replay into a stable, deterministic query surface.

It does not activate a live production runtime.

## Architectural decision

Repository audit found:

- historical replay semantics owned by `constraint-replay`;
- physical identity/reference ownership in `constraint-physical-dependency`;
- geopolitical/policy evidence ownership in `constraint-geopolitical-policy`;
- the public `t6-fail-closed-validator` explicitly marked **SOURCE-ONLY, DORMANT, NOT ACTIVATED**;
- the T6 dormant adapter explicitly refuses runtime execution.

Batch 016 therefore does **not** register the historical replay into T6 or mutate T6 authority semantics.

The query service lives inside `constraint-replay`, which already owns the Batch 015 replay result.

## Authority input

The query service serves only the frozen Batch 015 run:

`constraint-replay/runs/HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_RUN_20260926.json`

Source run digest:

`db28edfea01800cf85dd234edb99d003d0a185ab39f7ba8cd31af416542890f1`

Before serving a query, initialization verifies:

- Batch 015 run status is PASS;
- run kind is supported;
- run digest matches the Batch 015 execution manifest;
- committed run bytes match the manifest output Git blob pin;
- all Batch 015 manifest input pins match checked-out bytes;
- runner module and CLI pins match;
- Batch 015 CI-contract pins match;
- expected aggregate counts match;
- Batch 015 integrity flags remain green;
- calibrated case count remains zero;
- calibration status remains explicitly blocked.

A stale or tampered Batch 015 state prevents the query service from starting.

## Query contract

Contract version:

`hydra-constraint-readonly-query/v1`

Mode:

`READ_ONLY_HISTORICAL_REPLAY`

Supported operations:

1. `summary`
2. `integrity`
3. `case`
4. `list_cases`

Unknown operations fail closed.

Unknown request fields fail closed.

## Read-only authority boundary

Every response includes the following capability state:

- canonical promotion authorized: **false**
- canonical-store mutation authorized: **false**
- external actions authorized: **false**
- model training authorized: **false**
- ranking authorized: **false**
- trading authorized: **false**

There is no query operation for:

- promotion;
- ranking;
- canonicalization;
- state mutation;
- trading;
- execution;
- model training;
- T6 activation.

## Summary query

Returns the frozen Batch 015 aggregate sections:

- coverage;
- outcome distribution;
- evidence-availability lead-time distribution;
- calibration status;
- integrity status.

Expected current state:

- 22 cases;
- 82 replay cuts;
- 31 historical event IDs;
- 17 PARTIAL_REALIZATION;
- 5 UNEVALUABLE;
- 0 calibrated cases.

## Exact case query

`case(case_id)` performs exact ID lookup.

There is no fuzzy entity resolution in this surface.

Unknown IDs fail rather than returning a guessed match.

Each case result includes:

- case ID;
- replay-cut count;
- first/last replay cut;
- classified replay time;
- first admitted outcome time;
- evidence-availability lead;
- outcome class;
- classification stage;
- calibration blockers;
- calibrated flag.

## Filtered list query

Supported deterministic filters:

- outcome class;
- calibrated true/false;
- minimum evidence-availability lead;
- maximum evidence-availability lead;
- calibration blocker.

Supported sorting:

- case ID;
- lead time ascending;
- lead time descending.

Optional result limit:

1–100.

Unsupported outcome classes, malformed bounds, invalid limits and unknown sort modes fail closed.

## CLI

Script:

`constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH016_readonly_replay_20260926.py`

Examples:

```bash
python constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH016_readonly_replay_20260926.py summary

python constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH016_readonly_replay_20260926.py integrity

python constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH016_readonly_replay_20260926.py case suez-ever-given-2021

python constraint-replay/scripts/query_HYDRA_CONSTRAINT_BATCH016_readonly_replay_20260926.py list \
  --outcome-class UNEVALUABLE \
  --sort-by lead_time_asc
```

## Adversarial validation

Batch 016 tests prove:

- exact case lookup works;
- unknown cases fail;
- the five UNEVALUABLE cases filter exactly;
- shortest-lead ordering is deterministic;
- calibration-blocker filtering returns all 22 cases;
- invalid filters fail closed;
- authority-smuggling fields are rejected;
- unsupported operations are rejected;
- every response advertises inert capabilities;
- copied/tampered Batch 015 run bytes fail Git-blob integrity before the service starts.

## T6 boundary

Batch 016 explicitly preserves:

`t6-fail-closed-validator = DORMANT_NOT_ACTIVATED`

The query service:

- does not call T6;
- does not prepare a T6 binding;
- does not register with T6;
- does not change T6 authority envelopes;
- does not turn ABSTAIN/QUARANTINE validation into canonical promotion.

## What Batch 016 accomplishes

A HYDRA consumer can now deterministically ask:

- What is the current governed historical replay summary?
- What happened in one exact historical case?
- Which cases are UNEVALUABLE?
- Which cases have the shortest/longest evidence-availability intervals?
- Which cases remain blocked by a given calibration blocker?
- Is the frozen replay authority state still byte-for-byte intact?

without directly parsing the underlying corpus files.

## What Batch 016 does not claim

This is not:

- a live production HTTP service;
- an activated T6 runtime;
- a trading API;
- a canonical-truth selector;
- a mutation interface;
- a probabilistically calibrated replay engine.

It is a deterministic read-only integration surface over the governed Batch 015 historical replay.

## Next material step

After Batch 016, the next useful work is no longer basic replay querying.

The next integration should connect this read-only historical query surface to a broader Constraint orchestration/reporting layer or execute a multi-domain Constraint run that consumes physical, policy, replay and other Constraint domains under explicit authority.

T6 activation remains a separate authority decision and should not be inferred from this query integration.
