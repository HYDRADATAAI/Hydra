# HYDRA Constraint — Replay Depth Expansion
## Batch 005 Replay-Ready Corpus, Contradictions & Revisions — 2026-09-25

Status: **REPLAY-READY / UNSCORED / SOURCE-PINNED**, pending successor-branch CI.

This pass changes the Constraint historical work from mostly case accumulation into a reproducible replay corpus without fabricating prediction scores.

## Corpus state

Batch 005 derives a replay-ready corpus from Batches 001–004:

- 22 sourced case families
- 31 executable historical events
- 9 later observations
- 82 point-in-time replay cuts
- 4 pinned upstream policy-bundle Git blobs

The corpus artifact is:

`constraint-replay/corpus/HYDRA_CONSTRAINT_REPLAY_READY_CORPUS_BATCH005_20260925.jsonl`

The exact source pins are stored in:

`constraint-replay/corpus/HYDRA_CONSTRAINT_REPLAY_BATCH005_SOURCE_BUNDLE_PINS_20260925.json`

## Replay-cut construction

Each case includes multiple historical cuts derived from actual clocks rather than arbitrary calendar intervals.

Candidate cuts include:

- one second before the first event becomes knowable;
- each distinct event `KNOWN_AT`;
- one second before a future `EFFECTIVE_AT`;
- one second before later observations;
- the timestamp when later observations become knowable.

Each cut records:

- eligible event IDs;
- future event IDs;
- known-but-not-yet-effective event IDs;
- observations already available;
- observations still in the future.

The integration suite recomputes all of those sets from the executable policy objects and requires exact agreement.

## Why this is not scored gold

The sourced cases prove historical evidence availability and mechanism/state transitions.

They do **not**, by themselves, prove that HYDRA historically generated an independent hypothesis with a historically grounded confidence before the outcome.

Therefore every Batch 005 record remains:

`tier = REPLAY_READY_UNSCORED`

`score_status = UNSCORED`

Scored fields such as `confidence_at_t` and `outcome_class` are forbidden in this tier.

Common promotion blockers are:

- `NO_INDEPENDENT_HISTORICAL_HYPOTHESIS_SOURCE`
- `NO_PRECOMMITTED_CONFIDENCE_SOURCE`
- `NO_OUTCOME_OBSERVATION_IN_CASE_BUNDLE`
- `OUTCOME_NOT_MAPPED_TO_SCORABLE_CLASS`

HYDRA must resolve blockers with evidence, not by deleting labels.

## Source immutability

Each replay-ready record pins the Git blob SHA of its upstream source bundle.

The integration test recomputes the Git blob SHA from the checked-out bytes and requires exact equality.

This makes later silent edits to historical case data detectable.

## Contradiction handling

Batch 005 adds a non-adjudicating contested-claim model.

A claim can carry contemporaneous evidence classified as:

- supporting;
- opposing;
- neutral.

The claim state at a historical timestamp can be:

- NO_AVAILABLE_EVIDENCE
- SUPPORT_ONLY
- OPPOSITION_ONLY
- CONTESTED
- NEUTRAL_ONLY

The state describes the evidence record. It does not decide political or legal truth.

### WTO rare-earths implementation example

The 20 May 2015 WTO record contains:

- China's statement that specified export duties, quotas and trading-right restrictions had been removed;
- a U.S. concern about an export licensing requirement.

The Batch 005 fixture therefore becomes `CONTESTED` once both pieces of contemporaneous evidence are available.

HYDRA does not collapse this into a unilateral "complied" or "did not comply" fact.

## Revision handling

Historical changes are represented separately from contradiction.

A revision relation can be:

- MODIFIES
- SUPERSEDES
- RETRACTS
- CLARIFIES

The Panama Canal A-54 record is modeled as `MODIFIES` the prior A-48 transit-slot policy.

That means the later booking-slot adjustment changes the applicable operating policy without retroactively making the earlier A-48 state false.

## Validation

Batch 005 adds fail-closed checks for:

- duplicate corpus case IDs;
- invalid Git blob pins;
- non-monotonic replay cuts;
- event universes changing across cuts;
- observations regressing across cuts;
- known-but-not-effective events that are not eligible;
- scored fields appearing in replay-ready records;
- replay-ready records with no promotion blockers;
- corpus source bundles drifting from pinned Git blob SHAs;
- corpus eligibility sets diverging from `eligible_as_of()`;
- claim evidence with missing attribution;
- duplicate claim evidence IDs;
- naive timestamps;
- revision self-reference;
- duplicate revision IDs.

## What Batch 005 accomplishes

Constraint can now answer a more rigorous version of:

> What was actually knowable at this historical cut?

for every currently sourced case, across repeated cuts, while keeping later observations and later-known events on the correct side of the replay boundary.

It can also preserve contested evidence and later policy revisions without overwriting earlier historical states.

## Next promotion gate

The next serious step is not more taxonomy.

It is to locate or construct defensible independent historical hypothesis records and outcome-side quantitative evidence for a subset of these 22 cases.

Only then should cases move from:

`REPLAY_READY_UNSCORED`

to a genuinely scored historical evaluation corpus.

The target remains 20–40+ scored gold cases, but source-count inflation is not accepted as a substitute for historically grounded hypotheses.
