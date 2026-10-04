# HYDRA Constraint — Confidence & Outcome-Mapping Governance
## Batch 008 — Classified Gold Without Fabricated Calibration — 2026-09-26

Status: **CLASSIFIED GOLD CREATED / CALIBRATION BLOCKED BY EVIDENCE**

Batch 008 closes the outcome-class mapping gate for the three best historical replay candidates while preserving the prohibition against invented confidence values.

## Result

Current promotion state:

- replay-ready source corpus: 22 cases;
- quantitative/hypothesis-enriched candidates: 3;
- classified-gold uncalibrated cases: **3**;
- calibrated scored-gold cases: **0**;
- admissible numeric historical confidence values: **0**.

The first classified-gold corpus is:

`constraint-replay/corpus/HYDRA_CONSTRAINT_CLASSIFIED_GOLD_UNCALIBRATED_BATCH008_20260926.jsonl`

It contains:

- Suez / Ever Given — `PARTIAL_REALIZATION`
- Black Sea Grain Initiative — `PARTIAL_REALIZATION`
- Wilhelmshaven LNG — `PARTIAL_REALIZATION`

## Why classified gold is separate from scored gold

Historical mechanism evaluation and probabilistic calibration are different questions.

A case can have:

1. a genuine pre-outcome hypothesis;
2. point-in-time source provenance;
3. later quantitative outcome evidence;
4. a governed outcome classification;

while still lacking a defensible historical probability.

Batch 008 therefore introduces:

`CLASSIFIED_GOLD_UNCALIBRATED`

This tier permits:

- outcome-class counts;
- point-in-time mechanism evaluation;
- historical lead-time measurement;
- source-pinned case comparison.

It does **not** permit:

- Brier score;
- calibration curves;
- confidence-weighted precision;
- invented `confidence_at_t`.

For the first three records, the first admitted outcome evidence arrives approximately:

- Suez: 5.35 days after the independent hypothesis source;
- Black Sea Grain: 10.0 days after the independent hypothesis source;
- Wilhelmshaven LNG: 95.42 days after the independent hypothesis source.

Across these three records:

- mean first-outcome lead time: approximately **36.92 days**;
- median first-outcome lead time: **10.0 days**.

These are evidence-availability lead times, not market-profit claims.

## Confidence admissibility

Batch 008 adds:

`hydra_constraint_replay.confidence`

and:

`HYDRA_CONSTRAINT_REPLAY_CONFIDENCE_ADMISSIBILITY_BATCH008_20260926.json`

Admissible numeric confidence may come only from:

1. an explicit numeric probability;
2. an explicit numeric probability range;
3. a predeclared ordinal-to-probability mapping available no later than the historical evidence.

The following are not probabilities:

- "expected";
- "likely" without a declared mapping;
- "risk";
- "could";
- "high utilization";
- targets/objectives;
- contractual or operating commitments expressed as percentages.

### Suez

The audited S&P Global source states that market watchers expected the backlog to take weeks to clear.

Classification:

`QUALITATIVE_EXPECTATION`

Admissible numeric confidence:

`NONE`

### Black Sea Grain

The audited IMF source described food-security risks and stated that easing Black Sea logistics hurdles could allay those risks.

Classification:

`QUALITATIVE_RISK`

Admissible numeric confidence:

`NONE`

### Wilhelmshaven

The audited Bundesnetzagentur source described high utilization as an objective and a commitment to use 100% of allocated unloading slots.

Classification:

`OPERATIONAL_COMMITMENT`

Admissible numeric confidence:

`NONE`

The 100% figure describes slot use obligations. It is not a 100% probability that the terminal would achieve a future supply-security outcome.

## Outcome mapping governance

Batch 008 adds:

`POSITIVE_CONSTRAINT_RULESET_V1`

The rule set is mechanism-generic and is declared before Batch 008 writes any candidate outcome class into the promotion audit.

The rule set can produce:

- TRUE_POSITIVE
- FALSE_POSITIVE
- PARTIAL_REALIZATION
- RIGHT_MECHANISM_WRONG_TIMING
- INVALIDATED
- UNEVALUABLE

### Conservative mapping logic

A TRUE_POSITIVE requires:

- the predicted mechanism to be observed;
- the predicted direction to be consistent;
- an explicit numeric target;
- that target to be met;
- clean causal attribution.

If mechanism and direction are supported but the explicit target or clean causal proof is absent, the rule returns:

`PARTIAL_REALIZATION`

An open contradiction or incomplete observation window maps to:

`UNEVALUABLE`

A timing miss can become:

`RIGHT_MECHANISM_WRONG_TIMING`

only when an explicit historical horizon was actually defined.

## Why all three are PARTIAL_REALIZATION

### Suez

Congestion/backlog and freight pressure appeared in the expected direction, but the hypothesis did not define a numeric success target and freight-market attribution was embedded in a wider disrupted shipping market.

### Black Sea Grain

Large physical export flows were restored and food-price indicators moved in the expected direction, but FAO explicitly identified multiple contributing factors. HYDRA therefore does not claim the Initiative caused the entire observed price change.

### Wilhelmshaven

The terminal entered operation and supplied material gas volumes, but "high utilization" and system-level security contribution were not expressed as a numeric success threshold in the historical hypothesis.

## Promotion gate split

Batch 008 updates the promotion state machine:

1. REPLAY_READY_ONLY
2. OUTCOME_EVIDENCE_PRESENT
3. HYPOTHESIS_EVIDENCE_PRESENT
4. **CLASSIFIED_GOLD_UNCALIBRATED**
5. CONFIDENCE_EVIDENCE_PRESENT
6. SCORE_READY

The three current candidates now have:

- no classification blockers;
- two calibration blockers.

Those calibration blockers are:

- `NO_PRECOMMITTED_CONFIDENCE_SOURCE`
- `NO_SOURCE_GROUNDED_CONFIDENCE_VALUE`

## Source immutability

Each classified-gold record pins the exact Git blob SHA for:

- Batch 007 outcome enrichment;
- Batch 008 confidence audit;
- Batch 008 outcome mapping;
- Batch 008 promotion audit.

The test suite recomputes Git blob hashes from checked-out bytes.

A later edit to any governing artifact invalidates the old classified-gold record rather than silently rewriting history.

## Calibration queue

The remaining evidence search is recorded in:

`HYDRA_CONSTRAINT_REPLAY_CALIBRATION_QUEUE_BATCH008_20260926.json`

The queue does not ask analysts to "estimate" historical confidence.

It asks for:

- contemporaneous explicit probability/range evidence; or
- a contemporaneous predeclared ordinal confidence mapping.

If neither exists, the historical case remains classified but uncalibrated.

That is an admissible final state.

## Validation

Batch 008 adds regression coverage for:

- operational percentages not becoming probabilities;
- qualitative expectation/risk language not becoming probabilities;
- invalid probability ranges;
- ordinal mappings declared after evidence;
- target success being impossible to smuggle into a case without an explicit target;
- timing classifications requiring an explicit historical horizon;
- contradiction → UNEVALUABLE mapping;
- source-pinned classified-gold artifacts;
- classified-gold promotion summary;
- Brier score remaining disabled for uncalibrated cases;
- the promotion audit retaining only calibration blockers for the three promoted cases.

## Next material step

The next useful pass should **not** weaken the confidence gate.

There are two defensible directions:

1. search for truly contemporaneous numeric confidence provenance for the three calibration-queue cases; and/or
2. expand the classified-gold uncalibrated corpus to additional replay-ready cases that can satisfy the same hypothesis/outcome/mapping standards.

If no historical probability source exists, HYDRA should accumulate a larger uncalibrated classified corpus and reserve calibration metrics for the subset where genuine confidence provenance exists.
