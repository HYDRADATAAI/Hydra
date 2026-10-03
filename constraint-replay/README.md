# HYDRA Constraint — Historical Outcomes & Point-in-Time Replay

This package is the fail-closed evaluation boundary for historical Constraint hypotheses.

## Invariant

Evidence may enter a replay only when `KNOWN_AT <= REPLAY_T`. Outcome-side/subsequent evidence must be known after the replay boundary. Missing provenance fails the replay rather than silently degrading it.

## Flow

`raw historical evidence → availability gate → PIT state → frozen hypothesis → future observations → outcome label → metrics`

The frozen state receives a deterministic SHA-256 prediction hash so later evaluation cannot silently rewrite the historical hypothesis.

## Outcome labels

TRUE_POSITIVE, FALSE_POSITIVE, TRUE_NEGATIVE, FALSE_NEGATIVE, PARTIAL_REALIZATION, RIGHT_MECHANISM_WRONG_TIMING, RIGHT_CONSTRAINT_WRONG_BENEFICIARY, INVALIDATED, UNRESOLVED, UNEVALUABLE.

## Metrics

The scored replay implementation reports precision, observable recall, false positives/negatives, mean and median lead time, Brier score, historical coverage, provenance completeness, and lookahead violations.

## Corpus tiers

HYDRA now separates **replay readiness** from **scored gold evaluation**.

### Replay-ready, unscored

`corpus/HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl` is generated from the provenance-bearing geopolitical/policy case bundles.

It contains:
- 22 sourced case families;
- 82 historical replay cuts;
- 31 executable historical events;
- 9 later observations.

Each replay cut pins:
- the upstream source-bundle Git blob SHA;
- events legitimately eligible by that cut;
- future events;
- known-but-not-yet-effective actions;
- observations already available;
- observations still in the future.

This tier is intentionally **UNSCORED**. It may not contain `confidence_at_t` or `outcome_class`.

### Scored gold

`corpus/gold_cases.jsonl` remains template/scaffold material until a case has independently defensible:

1. historical hypothesis provenance;
2. precommitted or otherwise historically grounded confidence;
3. outcome evidence;
4. outcome-class mapping;
5. point-in-time evidence cut.

HYDRA does not fabricate confidence scores or true-positive labels merely to increase the gold-case count.

## Promotion blockers

Replay-ready records explicitly carry promotion blockers. Current common blockers include:

- `NO_INDEPENDENT_HISTORICAL_HYPOTHESIS_SOURCE`
- `NO_PRECOMMITTED_CONFIDENCE_SOURCE`
- `NO_OUTCOME_OBSERVATION_IN_CASE_BUNDLE`
- `OUTCOME_NOT_MAPPED_TO_SCORABLE_CLASS`

Promotion requires evidence that resolves the applicable blockers; deleting the blocker strings is not sufficient.

## Run

```bash
cd constraint-replay
python -m pytest -q
```

The stacked Constraint integration CI also runs the physical, replay and geopolitical/policy suites together.

## Integration contract

Upstream Constraint domains emit provenance-bearing evidence with stable evidence IDs, KNOWN_AT, OBSERVED_AT, source URI, source hash and payload. Geography/resource/infrastructure/entity relationships belong in the frozen historical state; replay does not create a parallel domain ontology.

## Next integration gate

Deepen the replay-ready corpus with:
- independent historical hypotheses where available;
- outcome-side quantitative evidence;
- contradictions and revisions;
- repeated replay cuts around material state transitions;
- promotion of only defensible cases into scored gold.

The target remains a serious 20–40+ **scored** historical-case corpus, but replay-ready source count alone is not treated as equivalent to scored gold.
