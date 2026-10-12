# HYDRA Constraint — Quantitative Outcome Enrichment
## Batch 007 — 2026-09-26

Status: **HYPOTHESIS-PROVENANCE ADDED / QUANTITATIVE OUTCOMES ADDED / ZERO SCORED-GOLD**

Batch 007 executes the targeted evidence queue created in Batch 006.

It enriches only:

- Suez / Ever Given
- Black Sea Grain Initiative
- Wilhelmshaven LNG

No other replay-ready case is modified.

## Promotion state

Before Batch 007:

- 3 targeted cases had promising outcome evidence;
- 0 had independent historical hypothesis provenance;
- 0 had historical confidence provenance;
- 0 were score-ready.

After Batch 007:

- all 3 have publisher-independent historical hypothesis evidence;
- all 3 have quantitative outcome evidence;
- 0 have historical confidence provenance;
- 0 are score-ready.

This is progress without score invention.

## Independence rule

A historical hypothesis source must:

1. be available before the first admitted outcome source;
2. come from a publisher distinct from all admitted outcome publishers for that case;
3. include an explicit independence rationale;
4. carry a pinned normalized-evidence SHA-256.

The validator fails if hypothesis and outcome publishers overlap.

## Suez / Ever Given

### Hypothesis evidence

S&P Global, 26 March 2021:

- around 240 vessels were poised to transit;
- some vessels were diverting;
- market watchers expected the backlog to take weeks to clear;
- tanker/container freight rates had risen sharply.

This source predates the admitted post-blockage outcome records.

### Quantitative / observed outcomes

Suez Canal Authority, 31 March 2021:

- 81 ships transited that day;
- 4.8 million net tons passed;
- round-the-clock operation continued to clear waiting vessels.

UNCTAD, 23 April 2021:

- the blockage was identified as triggering a renewed surge in container spot freight rates in an already disrupted freight market.

The case is upgraded to `SCORABLE_CANDIDATE_QUANTITATIVE`, but no outcome class is assigned.

## Black Sea Grain Initiative

### Independent hypothesis evidence

IMF World Economic Outlook Update, 26 July 2022:

- identified food/trade barriers and the Black Sea blockade as material logistics risks;
- stated that easing those logistical hurdles could allay food-crisis risks.

This source is independent of the FAO and Joint Coordination Centre outcome publishers.

### Price outcomes

FAO, 5 August 2022:

- Food Price Index: 140.9;
- month-over-month Food Price Index change: -8.6%;
- Cereal Price Index: -11.5%;
- wheat prices: down as much as 14.5%;
- maize prices: down 10.7%.

FAO explicitly identified the Black Sea export agreement as one contributing factor while also naming other market and seasonal factors.

HYDRA therefore does **not** attribute the full price change to the Initiative.

### Physical-flow outcomes

UN Joint Coordination Centre:

- 9,729,083 tonnes cumulative by 1 November 2022;
- 30,288,930 tonnes cumulative by 26 May 2023;
- monthly export series stored for August 2022 through April 2023.

This turns the case into a genuine multi-date quantitative outcome record.

## Wilhelmshaven LNG

### Independent hypothesis evidence

Bundesnetzagentur, 29 September 2022:

- stated the Wilhelmshaven/Brunsbuettel FSRUs would contribute to winter gas security;
- stated the objective was high utilization once operational.

The regulator is distinct from Uniper, the terminal operator/outcome publisher.

### Quantitative outcomes

Uniper:

3 January 2023:
- first full cargo: about 170,000 m³ LNG;
- natural-gas equivalent: 97,147,000 m³.

15 December 2023:
- 42 LNG carriers;
- around 7 million m³ LNG delivered;
- around 4 billion m³ natural gas fed into the grid;
- around 6% of German gas consumption in 2023.

These are outcome measurements, not a confidence score.

## Why the cases remain unscored

All three still lack:

- historical confidence/probability provenance;
- source-grounded `confidence_at_t`;
- an audited outcome-class mapping rule.

Batch 007 deliberately does not derive a pseudo-confidence from phrases such as "expected", "likely" or "would contribute".

It also does not assign `TRUE_POSITIVE` merely because later evidence moved in the same direction.

## New validation

Batch 007 adds checks for:

- hypothesis-source role;
- outcome-source role;
- hypothesis availability before outcome availability;
- hypothesis/outcome publisher separation;
- evidence digest integrity;
- metric source admission;
- metric timestamp consistency;
- numeric metric values;
- time-series uniqueness and minimum length;
- quantitative enrichment alignment with the Batch 007 promotion audit.

## Next gate

The remaining problem is now narrow.

For these three cases, search specifically for contemporaneous probability/confidence evidence that was available before the measured outcome.

If none exists, retain the cases as:

`HYPOTHESIS_EVIDENCE_PRESENT / UNSCORED`

and do not manufacture probabilistic backtests.

A separate next pass may also define outcome-class mapping rules using predeclared thresholds, but those rules must be audited before historical outcomes are classified.
