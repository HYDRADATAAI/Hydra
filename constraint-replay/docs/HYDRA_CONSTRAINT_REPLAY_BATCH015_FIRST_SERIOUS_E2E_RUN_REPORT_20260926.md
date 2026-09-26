# HYDRA Constraint — First Serious End-to-End Classified Replay
## Batch 015 — 2026-09-26

Status: **PASS / DETERMINISTIC / CI-GATED**

Batch 015 is the first repository-executed aggregate replay run across the complete governed historical corpus.

It does not create new classifications.

## Frozen inputs

The run consumes exactly:

1. `HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl`
2. `HYDRA_CONSTRAINT_CLASSIFIED_GOLD_UNCALIBRATED_BATCH014_20260926.jsonl`
3. `HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH014_20260926.json`

The run artifact pins those files by Git blob SHA and the execution manifest separately pins the runner, CLI, output artifact and CI workflows.

## Deterministic run identity

Run artifact:

`constraint-replay/runs/HYDRA_CONSTRAINT_BATCH015_CLASSIFIED_REPLAY_E2E_RUN_20260926.json`

Canonical run digest:

`812c7eac1d68f7c07f195acb7831a04bd710e827ceb9dee24975ae8a728785c0`

CI regenerates the run in memory and requires byte-equivalent JSON output through the Batch 015 CLI check mode.

## Coverage

- historical cases: **22**
- replay cuts: **82**
- unique executable historical event IDs: **31**
- original replay-corpus observation IDs: **9**
- classification coverage: **100%**
- classified-gold uncalibrated: **22**
- calibrated/scored cases: **0**

The replay-ready, classified and promotion-audit case sets must be exactly equal.

## Outcome distribution

- `PARTIAL_REALIZATION`: **17**
- `UNEVALUABLE`: **5**

The five unevaluable cases are:

- CHIPS industrial policy — explicit long horizon still open
- WTO rare-earths implementation — contested compliance state
- Japan–Korea export-control normalization — conflicting official characterization
- Eastern Mediterranean drilling dispute — unresolved legal/territorial state
- CBAM — operational deployment observed but modeled economic outcome window incomplete

## Evidence-availability lead time

Across all 22 cases:

- minimum: **5.35 days**
- p25: **203.25 days**
- median: **450.14 days**
- mean: **735.22 days**
- p75: **1,187.25 days**
- maximum: **2,304 days**

Shortest admitted outcome-evidence intervals:

1. Suez / Ever Given — ~5.35 days
2. Black Sea Grain Initiative — 10 days
3. Panama Canal drought — 72 days
4. Wilhelmshaven LNG — ~95.42 days
5. Nord Stream 2 certification — 98 days

Longest intervals:

1. EU battery IPCEI — 2,304 days
2. Section 232 steel — 1,792 days
3. Eastern Mediterranean drilling — ~1,682.74 days
4. Section 301 — 1,645 days
5. CBAM — 1,645 days

These are **evidence-availability intervals**.

They are not effect-onset estimates, market lead times, causal lags or profitability windows.

## Calibration

Calibration state:

`BLOCKED_NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

Common blockers:

- `NO_PRECOMMITTED_CONFIDENCE_SOURCE`
- `NO_SOURCE_GROUNDED_CONFIDENCE_VALUE`

Therefore:

- calibrated case count: **0**
- Brier score: **null**

This is an explicit blocked state, not missing implementation.

## Fail-closed integrity checks

The Batch 015 runner aborts if:

- classified IDs differ from replay-ready IDs;
- promotion-audit IDs differ from replay-ready IDs;
- any replay source-bundle Git blob pin is stale;
- any classified governing-artifact pin is stale;
- any classified case still has classification blockers;
- a promotion outcome class disagrees with the classified corpus;
- a supposedly uncalibrated run unexpectedly contains a score-ready case;
- any case has non-positive outcome-evidence lead;
- CI-generated output differs from the committed run artifact.

## CI integration

Batch 015 is now a standing contract in:

- `constraint-replay` workflow;
- full Constraint policy/physical/replay integration workflow.

Future changes to replay, policy or source-state artifacts must reproduce this run exactly unless a deliberate successor run updates the frozen artifact and its evidence lineage.

## Result

The first serious end-to-end classified historical replay **passes**.

Current demonstrated state:

- point-in-time replay corpus exists;
- all 22 current cases are governed/classified;
- source and governing-artifact lineage is pinned;
- aggregate run output is deterministic;
- calibration limitations are explicit;
- CI enforces reproducibility.

## Next material step

Do not create another classification batch.

The next high-value work should be one of:

1. integrate this replay-run result into the authoritative central Constraint query/runtime path;
2. build queryable case-level and aggregate runtime APIs over the Batch 015 result;
3. acquire authentic numeric historical confidence for a subset and create the first calibrated successor run;
4. perform the broader serious Constraint end-to-end system run that includes additional Constraint domains beyond geopolitical/policy historical replay.
