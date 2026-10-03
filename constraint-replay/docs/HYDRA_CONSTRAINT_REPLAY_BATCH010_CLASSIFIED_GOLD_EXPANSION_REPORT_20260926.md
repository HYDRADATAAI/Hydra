# HYDRA Constraint — Classified Gold Expansion
## Batch 010 — 2026-09-26

Status: **9 CLASSIFIED GOLD / 0 CALIBRATED GOLD**

Batch 010 expands the governed `CLASSIFIED_GOLD_UNCALIBRATED` corpus from six to nine cases without changing the confidence or outcome-mapping rules.

## Newly classified cases

### U.S.-China Section 301 multi-stage trade actions (2018)

Independent historical hypothesis:
- Federal Reserve Beige Book, 12 September 2018.
- Tariffs were contributing to manufacturers' input-cost pressure and many contacts had experienced or anticipated price hikes and/or supply disruptions.

Quantitative outcome:
- USITC retrospective analysis, 15 March 2023.
- covered imports from China: -13%
- U.S. prices for covered products: +0.2%
- U.S. production value: +0.4%
- semiconductor imports: -72.3%
- semiconductor U.S. prices: +4.1%
- semiconductor U.S. production value: +6.4%

Governed class:
`PARTIAL_REALIZATION`

Confidence status:
`NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

The Beige Book expectation is qualitative and does not carry a numeric probability.

### China gallium/germanium export controls (2023)

Independent historical hypothesis:
- IEA Critical Minerals Market Review 2023, 11 July 2023.
- The IEA described the July export curbs as evidence that highly concentrated niche-mineral supply chains may be disrupted by reliance on a small number of suppliers.

Quantitative outcome:
- U.S. Geological Survey Mineral Commodity Summaries 2024.

Gallium:
- China low-purity price: $240/kg in June 2023 → $375/kg by October
- reported increase: +56%

Germanium:
- China germanium-metal exports: 0 kg in August and 1 kg in September after controls began
- full-year exports: 39,400 kg, down 10% from 2022
- European germanium metal price: $1,150/kg in January → $1,550/kg in October
- germanium dioxide: $725/kg → $940/kg

Governed class:
`PARTIAL_REALIZATION`

Reason:
The export interruption and price-pressure mechanism appeared in the expected direction, but the USGS evidence also identifies demand and other market conditions; HYDRA does not claim clean single-cause attribution.

Confidence status:
`NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

### IMO 2020 sulfur regulation

Independent historical hypothesis:
- U.S. EPA, 11 December 2019.
- EPA expected the global marine-fuel sulfur reduction from 35,000 ppm to 5,000 ppm to deliver significant global health and welfare benefits.

Quantitative outcome:
- International Maritime Organization, 28 January 2021.
- total shipping sulfur-oxide emissions: -70%
- compliant-fuel non-availability reports during 2020: 55

Governed class:
`PARTIAL_REALIZATION`

Reason:
The emissions-reduction mechanism strongly realized in the expected direction, but the independent historical hypothesis did not define a numeric outcome target for health/welfare realization.

Confidence status:
`NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

The 0.50% sulfur standard is a regulatory threshold, not a probability.

## Corpus state

Batch 008:
- 3 classified
- 0 calibrated

Batch 009:
- 6 classified
- 0 calibrated

Batch 010:
- **9 classified**
- **0 calibrated**

All nine currently map conservatively to `PARTIAL_REALIZATION`.

## Evidence-availability lead times

For the three new records:

- Section 301: approximately 1,645 days
- gallium/germanium: approximately 203 days
- IMO 2020: approximately 414 days

Across the nine-case classified corpus:

- mean first admitted outcome-evidence lead time: approximately **522.64 days**
- median: **203 days**

These measure evidence availability, not first economic effect or market profitability.

Long retrospective-study intervals, especially USITC tariff analysis, should not be interpreted as implying that the underlying effect began only when the study was published.

## Governance reuse

Batch 010 creates no new mapping or confidence semantics.

It reuses:

- `POSITIVE_CONSTRAINT_RULESET_V1`
- Batch 008 confidence admissibility
- `CLASSIFIED_GOLD_UNCALIBRATED`
- the existing classification/calibration promotion split

The expansion therefore tests generality rather than introducing case-specific logic.

## Integrity

Batch 010 tests require:

- all six Batch 009 predecessor records remain unchanged;
- the three new cases already exist in the immutable 22-case replay-ready corpus;
- hypothesis/outcome publishers are independent;
- hypothesis evidence predates admitted outcome evidence;
- confidence audit returns no numeric confidence;
- mapping evidence exactly equals admitted enrichment evidence;
- all new mapping decisions equal `PARTIAL_REALIZATION`;
- all new cases have zero classification blockers;
- only the two calibration blockers remain;
- Git blob pins match the governing Batch 010 artifacts;
- Brier score remains disabled.

## Remaining replay-ready population

Nine of the original 22 replay-ready cases now satisfy the classified-gold standard.

The remaining cases should be promoted only where independent historical hypothesis evidence and defensible later outcomes can be found.

Good next audit targets include:

- BIS semiconductor controls;
- PDVSA sanctions;
- Germany/Uniper nationalization;
- CHIPS industrial policy;
- EU battery IPCEI;
- Section 45X;
- CBAM;
- Japan-Korea export-control relations.

Calibration remains a separate evidence problem and should not block further expansion of the uncalibrated classified corpus.
