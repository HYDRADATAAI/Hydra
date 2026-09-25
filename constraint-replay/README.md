# HYDRA Constraint — Historical Outcomes & Point-in-Time Replay

This package is the fail-closed evaluation boundary for historical Constraint hypotheses.

## Invariant

Evidence may enter a replay only when `KNOWN_AT <= REPLAY_T`. Outcome-side/subsequent evidence must be known after the replay boundary. Missing provenance fails the replay rather than silently degrading it.

## Flow

raw historical evidence -> availability gate -> PIT state -> frozen hypothesis -> future observations -> outcome label -> metrics

The frozen state receives a deterministic SHA-256 prediction hash so later evaluation cannot silently rewrite the historical hypothesis.

## Outcome labels

TRUE_POSITIVE, FALSE_POSITIVE, TRUE_NEGATIVE, FALSE_NEGATIVE, PARTIAL_REALIZATION, RIGHT_MECHANISM_WRONG_TIMING, RIGHT_CONSTRAINT_WRONG_BENEFICIARY, INVALIDATED, UNRESOLVED, UNEVALUABLE.

## Metrics

The first implementation reports precision, observable recall, false positives/negatives, mean lead time, Brier score, historical coverage, provenance completeness, and lookahead violations.

## Corpus policy

`corpus/gold_cases.jsonl` begins as explicit unpopulated scaffolding. A case is not gold until its historical evidence has source identity/hash and defensible KNOWN_AT timestamps. This deliberately prevents fabricated historical test evidence.

## Run

```bash
cd constraint-replay
python -m pytest -q
```

## Integration contract

Upstream Constraint domains should emit provenance-bearing evidence with stable evidence IDs, KNOWN_AT, OBSERVED_AT, source URI, source hash, and payload. Geography/resource/infrastructure/entity relationships belong in the frozen hypothesis/state; this package does not create a parallel domain ontology.

## Next integration gate

Populate 20–40 sourced historical cases across materially different mechanisms, execute multiple replay cuts per case, then connect this evaluator to the authoritative Constraint ingestion/state layer once that layer is present in the repository.
