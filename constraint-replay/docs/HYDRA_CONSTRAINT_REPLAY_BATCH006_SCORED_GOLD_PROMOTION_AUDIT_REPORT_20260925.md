# HYDRA Constraint — Scored-Gold Promotion Audit
## Batch 006 — 2026-09-25

Status: **PROMOTION AUDITED / ZERO SCORE-READY / TARGETED OUTCOME QUEUE CREATED**

This pass audits the 22-case Batch 005 replay-ready corpus against the requirements for honest scored historical evaluation.

It does not add prediction scores.

## Result

- replay-ready cases audited: **22**
- cases with any later observation evidence: **8**
- cases with outcome evidence strong enough to justify targeted enrichment: **3**
- cases with independently sourced historical hypothesis provenance: **0**
- cases with historically sourced confidence provenance: **0**
- cases eligible for scored-gold promotion: **0**

Zero is the correct result under the current evidence.

## Why zero cases were promoted

A scored replay needs more than a documented historical event followed by a later observation.

For promotion, the audit requires all of the following:

1. independent historical hypothesis source;
2. historically grounded confidence source;
3. source-grounded confidence value;
4. later outcome evidence;
5. evidence-supported outcome-class mapping;
6. no lookahead leakage.

The existing geopolitical/policy case bundles were designed to prove historical evidence/state reconstruction. They do not contain independent precommitted probability/confidence records.

HYDRA therefore refuses to invent them.

## Promotion gate

Batch 006 adds `hydra_constraint_replay.promotion`.

The gate classifies:

- replay-only records;
- records with later outcome evidence;
- records with historical hypothesis evidence;
- records with historical confidence evidence;
- truly score-ready records.

A confidence value cannot exist without a historical confidence source ID.

An outcome class cannot be supplied unless the audit explicitly marks its supporting evidence as sufficient.

`assert_scored_gold_eligible()` fails closed for every currently audited case.

## Outcome evidence inventory

Eight cases contain later observations in their committed source bundles.

Five are currently **context-only** for scoring because the later evidence documents implementation, escalation, guidance, or contested status rather than a mapped measurable constraint outcome.

Three cases are targeted for deeper outcome work:

### Suez / Ever Given

Existing evidence:
- navigation restored;
- UNCTAD reported a later container spot-freight-rate surge.

Current status:
`SCORABLE_CANDIDATE_QUALITATIVE`

Still needed:
- quantitative dated freight/shipping cost series;
- independent contemporaneous historical hypothesis;
- historically grounded confidence;
- explicit outcome mapping.

### Black Sea Grain Initiative

Existing evidence:
- the first shipment under the Initiative was cleared;
- the underlying source records a physical shipment quantity.

Current status:
`SCORABLE_CANDIDATE_QUANTITATIVE`

Still needed:
- multi-date shipment/throughput series;
- independent contemporaneous hypothesis;
- historically grounded confidence;
- explicit outcome mapping.

### Wilhelmshaven LNG

Existing evidence:
- trial, commercial and regular-operation dates;
- upstream physical graph contains sourced 5 bcm/year nameplate capacity.

Current status:
`SCORABLE_CANDIDATE_OPERATIONAL`

Still needed:
- actual throughput/utilization evidence;
- independent pre-operation hypothesis;
- historically grounded confidence;
- explicit outcome mapping.

## Audit integrity

Batch 006 requires:

- exact case-set equality with the Batch 005 replay corpus;
- every outcome source ID to exist in that case's committed observation records;
- no unsupported confidence value;
- no unsupported outcome class;
- no duplicate source IDs in promotion inputs;
- replay-ready status to remain unchanged during audit;
- no case silently becoming score-ready from the presence of a later observation alone.

## Artifacts

- `constraint-replay/corpus/HYDRA_CONSTRAINT_REPLAY_PROMOTION_AUDIT_BATCH006_20260925.json`
- `constraint-replay/corpus/HYDRA_CONSTRAINT_REPLAY_PROMOTION_QUEUE_BATCH006_20260925.json`
- `constraint-replay/src/hydra_constraint_replay/promotion.py`
- promotion gate unit tests;
- cross-layer audit-to-source integration tests.

## Next evidence pass

Do **not** broadly enrich all 22 cases.

The next evidence acquisition pass should concentrate on the three outcome candidates above and attempt to resolve, in order:

1. outcome-side quantitative history;
2. independent contemporaneous hypothesis evidence;
3. historically grounded confidence evidence.

If no defensible historical confidence source exists for a case, it should remain unscored even if its eventual outcome is obvious in hindsight.
