# HYDRA Constraint — Classified Gold Expansion
## Batch 009 — 2026-09-26

Status: **6 CLASSIFIED GOLD / 0 CALIBRATED GOLD**

Batch 009 expands the Batch 008 `CLASSIFIED_GOLD_UNCALIBRATED` corpus from three to six cases without modifying the predecessor records.

## Newly classified cases

### U.S. Section 232 steel tariffs (2018)

Independent historical hypothesis:
- Federal Reserve Beige Book, 18 April 2018.
- Business contacts reported tariff-related steel-price increases and generally expected additional steel/building-material price increases.

Quantitative outcome:
- USITC retrospective analysis, 15 March 2023.
- affected steel imports: -24%
- U.S. steel prices: +2.4%
- U.S. steel production: +1.9%
- 2021 steel production attributable increment: +$1.3 billion
- downstream prices: +0.2%
- downstream production: -0.6%

Governed class:
`PARTIAL_REALIZATION`

Reason:
The expected price-pressure mechanism and domestic-production direction were later supported by USITC estimates, but the contemporaneous hypothesis had no explicit numeric success target.

Confidence status:
`NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

### EU Russian-oil import restrictions (2022)

Independent historical hypothesis:
- IEA Oil Market Report, 15 June 2022.
- The IEA expected tougher sanctions and the planned EU import ban to reduce Russian supply availability and force major trade reallocation.

Quantitative outcome:
- Eurostat, 25 September 2023.
- monthly-average Russian petroleum-oil imports: 8.7 Mt in Q2 2022 → 1.6 Mt in Q2 2023
- mass change: -82%
- Russia share of total EU petroleum-oil imports: 21.6% → 4.0%
- monthly-average imports from non-Russian extra-EU partners: +5.8 Mt

Governed class:
`PARTIAL_REALIZATION`

Reason:
The trade-reallocation mechanism realized strongly in the expected direction, but sanctions, war-related adjustments and broader energy-market responses prevent single-cause attribution.

Confidence status:
`NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

The IEA's reference to a 90% EU import ban describes policy scope, not a 90% probability of the forecast result.

### Panama Canal drought / transit restrictions (2023–2024)

Independent historical hypothesis:
- IMF, 15 November 2023.
- IMF staff expected drought restrictions to hamper trade for months after already reducing throughput and increasing transit times.

Quantitative outcome:
- UNCTAD, 26 January 2024.
- total Panama Canal transits were reported 36% below the year-earlier level over the prior month.

Governed class:
`PARTIAL_REALIZATION`

Reason:
The continuing drought-restriction mechanism occurred in the expected direction. Batch 009 deliberately does not convert the separate operational projection of 18 ships/day into the success target of the selected qualitative hypothesis.

Confidence status:
`NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

## Corpus state

Batch 008:
- 3 classified-gold uncalibrated cases
- 0 calibrated cases

Batch 009:
- **6 classified-gold uncalibrated cases**
- **0 calibrated cases**

All six currently map to `PARTIAL_REALIZATION`.

The original three Batch 008 records are required by regression tests to remain semantically identical inside the Batch 009 corpus.

## Evidence-availability lead times

Lead time here means:

`first admitted outcome source availability - historical hypothesis availability`

It does **not** mean time-to-market-profit or the first instant the economic effect occurred.

Approximate values:

- Suez / Ever Given: 5.35 days
- Black Sea Grain Initiative: 10.0 days
- Wilhelmshaven LNG: 95.42 days
- Panama Canal drought: 72.0 days
- EU Russian-oil restrictions: 467.0 days
- Section 232 steel: 1,792.0 days

Across all six classified records:

- mean evidence-availability lead time: approximately **406.96 days**
- median: approximately **83.71 days**

The long Section 232 interval reflects the use of a later independent retrospective USITC causal study. It must not be interpreted as saying the steel-price effect began only in 2023.

## Governance reuse

Batch 009 introduces no new confidence or outcome-class semantics.

It reuses:

- Batch 008 confidence admissibility rules;
- `POSITIVE_CONSTRAINT_RULESET_V1`;
- `CLASSIFIED_GOLD_UNCALIBRATED`;
- the existing promotion state machine.

This is intentional: expansion should test the generality of the governance system rather than creating case-specific rules.

## Confidence audit

New hypothesis evidence is classified as:

- Section 232 / Federal Reserve: `QUALITATIVE_EXPECTATION`
- EU Russian oil / IEA: `QUALITATIVE_EXPECTATION`
- Panama Canal / IMF: `QUALITATIVE_EXPECTATION`

None supplies:
- explicit numeric probability;
- explicit numeric probability range;
- predeclared ordinal-to-probability mapping.

Therefore all three remain calibration-ineligible.

## Source independence

Hypothesis/outcome publisher pairs are distinct:

- Federal Reserve System → USITC
- IEA → Eurostat
- IMF → UNCTAD

The enrichment validator requires hypothesis evidence to be available before the first admitted outcome source.

## Integrity

Batch 009 regression checks require:

- the new cases already exist in the immutable 22-case replay-ready corpus;
- Batch 008 gold records remain unchanged;
- hypothesis/outcome publishers are disjoint;
- confidence remains non-probabilistic;
- mapping evidence exactly equals admitted enrichment sources;
- all new mappings resolve to `PARTIAL_REALIZATION`;
- all new promotion decisions have zero classification blockers;
- only the two calibration blockers remain;
- governing artifact Git blob SHAs match checked-out bytes;
- six-case corpus Brier score remains disabled.

## Next material step

The classified-gold path is now proven across six materially different mechanisms:

- shipping chokepoint disruption;
- agricultural export-corridor restoration;
- LNG infrastructure commissioning;
- tariff-driven industrial price/production effects;
- sanctions/import-restriction trade reallocation;
- climate-driven canal capacity restriction.

The next pass should prioritize additional replay-ready cases where independent quantitative outcome studies already exist, rather than forcing probability calibration.

Good candidates for a subsequent expansion audit include:
- Section 301 trade actions;
- gallium/germanium export controls;
- IMO 2020 sulfur regulation;
- sanctions/nationalization cases with defensible quantitative outcome series.

Calibration should remain a separate evidence problem.
