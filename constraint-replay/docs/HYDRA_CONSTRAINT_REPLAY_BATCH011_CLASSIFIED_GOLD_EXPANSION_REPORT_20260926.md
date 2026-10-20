# HYDRA Constraint — Classified Gold Expansion
## Batch 011 — 2026-09-26

Status: **12 CLASSIFIED GOLD / 0 CALIBRATED GOLD**

Batch 011 expands the governed `CLASSIFIED_GOLD_UNCALIBRATED` corpus from nine to twelve cases.

It also adds the first classified case whose correct governed outcome is `UNEVALUABLE` because an explicit historical horizon remains open.

## Newly classified cases

### PDVSA sanctions / Venezuelan crude production (2019)

Independent historical hypothesis:
- U.S. Energy Information Administration, 20 May 2019.
- EIA expected Venezuelan crude production to keep declining through 2019 and said sanctions-related deadlines could accelerate the decline, while also identifying power outages, industry mismanagement, staffing losses and service-company departures as additional causes.

Quantitative outcome:
- OPEC December 2019 Monthly Oil Market Report.
- Venezuela crude production, secondary sources:
  - 1Q19: 975 kb/d
  - 2Q19: 776 kb/d
  - 3Q19: 714 kb/d
  - September: 644 kb/d
  - November: 697 kb/d

Governed class:
`PARTIAL_REALIZATION`

Reason:
The decline mechanism continued in the expected direction, but the contemporaneous evidence itself identifies several non-sanctions causes. HYDRA does not convert a multi-causal decline into a sanctions-only causal claim.

Confidence status:
`NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

### Germany / Uniper nationalization and recapitalisation (2022–2024)

Independent historical hypothesis:
- European Commission, 21 December 2022.
- The approved recapitalisation was expected to permit continued customer service, help prevent serious disruption in the German gas market, and restore Uniper's financial position and liquidity.

Quantitative outcome:
- Uniper, 28 February 2024.
- adjusted EBIT:
  - 2022: -€10.877B
  - 2023: +€6.367B
- adjusted net income:
  - 2022: -€7.401B
  - 2023: +€4.432B
- IFRS net income:
  - 2022: -€19.144B
  - 2023: +€6.336B

Governed class:
`PARTIAL_REALIZATION`

Reason:
Financial stabilization is strongly supported, but the outcome publisher also attributes 2023 performance to commodity-price changes, hedging, portfolio optimization and non-recurrence of replacement-procurement costs. Recapitalisation is not treated as the sole cause.

Confidence status:
`NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

### U.S. CHIPS industrial policy (2021–ongoing)

Independent historical hypothesis:
- Boston Consulting Group / Semiconductor Industry Association analysis, 1 April 2021.
- A roughly $50B manufacturing-incentive program was estimated to enable 19 advanced fabs over ten years, approximately double the no-action expectation.

Interim quantitative evidence:
- U.S. Department of Commerce, 9 August 2024.
- more than $30B in proposed CHIPS private-sector investment
- 23 projects
- 15 states
- 16 new semiconductor manufacturing facilities
- more than 115,000 expected manufacturing and construction jobs

Governed class:
`UNEVALUABLE`

Reason:
The selected historical hypothesis has an explicit ten-year horizon. The 2024 Commerce evidence is an interim implementation snapshot, not a completed ten-year outcome window.

Batch 011 therefore does **not** force CHIPS into:
- TRUE_POSITIVE;
- FALSE_POSITIVE;
- RIGHT_MECHANISM_WRONG_TIMING.

The horizon remains open.

Confidence status:
`NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

The projected 19-fab quantity is a conditional forecast quantity, not a probability.

## Generic open-horizon rule

Batch 011 found and fixed a governance edge case.

Previously, a case with:
- an explicit historical horizon;
- an incomplete observation window;
- no defensible current `horizon_met` value

could not pass validation.

The generic outcome mapper now permits:

`explicit_horizon_defined = true`
`horizon_met = null`
`outcome_observation_complete = false`

Such a case maps to:

`UNEVALUABLE`

This prevents unfinished long-horizon policies from being prematurely scored as timing successes or failures.

A regression test covers this behavior independently of CHIPS.

## Corpus state

Batch 008:
- 3 classified
- 0 calibrated

Batch 009:
- 6 classified
- 0 calibrated

Batch 010:
- 9 classified
- 0 calibrated

Batch 011:
- **12 classified**
- **0 calibrated**

Outcome classes:
- 11 `PARTIAL_REALIZATION`
- 1 `UNEVALUABLE`

## Evidence-availability lead time

For the three new records:

- PDVSA: 205.0 days
- Uniper: approximately 433.27 days
- CHIPS: 1,226.0 days to the admitted interim outcome source

Across all twelve classified records:

- mean evidence-availability lead time: approximately **547.34 days**
- median: **309.5 days**

These are source-availability intervals, not estimates of the first instant that economic effects occurred.

In particular:
- long USITC retrospective-study intervals do not imply tariff effects began years later;
- CHIPS' 1,226-day interval is not a completed outcome horizon and remains `UNEVALUABLE`.

## Governance reuse

Batch 011 reuses:
- historical confidence admissibility;
- publisher-independence rules;
- `POSITIVE_CONSTRAINT_RULESET_V1`;
- `CLASSIFIED_GOLD_UNCALIBRATED`;
- Git-blob source pinning;
- the classification/calibration blocker split.

No case-specific scoring algorithm is introduced.

## Integrity checks

Batch 011 tests require:

- all nine Batch 010 predecessor records remain unchanged;
- all three new cases already exist in the immutable 22-case replay-ready corpus;
- hypothesis/outcome publisher independence;
- hypothesis availability before admitted outcome evidence;
- no numeric confidence admitted;
- mapping evidence exactly equals admitted enrichment evidence;
- PDVSA and Uniper map to `PARTIAL_REALIZATION`;
- CHIPS maps to `UNEVALUABLE`;
- CHIPS retains an explicit open historical horizon;
- all three new cases have zero classification blockers;
- only the two calibration blockers remain;
- governing artifact Git blob pins match checked-out bytes;
- twelve-case Brier score remains disabled.

## Next material step

Twelve of the original twenty-two replay-ready cases now have governed historical classification.

The next expansion should prioritize cases with independent outcome studies already available rather than lowering evidence standards.

Strong remaining candidates include:
- Section 45X manufacturing incentive;
- EU battery IPCEI;
- CBAM;
- Japan-Korea export-control relations;
- EU fifth-package coal/port restrictions;
- Russia food-import embargo;
- Eastern Mediterranean drilling framework;
- Nord Stream 2 certification state.

The calibration problem remains separate. If authentic contemporaneous probability provenance does not exist, HYDRA should continue expanding the uncalibrated classified corpus rather than inventing it.
