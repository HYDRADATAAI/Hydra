# HYDRA Constraint — Classified Gold Expansion
## Batch 013 — 2026-09-26

Status: **18 CLASSIFIED GOLD / 0 CALIBRATED GOLD**

Batch 013 expands `CLASSIFIED_GOLD_UNCALIBRATED` from fifteen to eighteen cases under unchanged governance.

## New cases

### Russia food-import embargo (2014)

Independent historical hypothesis:
- World Bank, 11 August 2014.
- The World Bank expected the new food-import ban to raise short-term inflationary pressure.

Outcome:
- FAO, 3 March 2015.
- Russian food prices: +14% in 2014.
- bread prices over the prior three months: +7%.
- flour prices over the prior three months: +10%.

Governed class:
`PARTIAL_REALIZATION`

Reason:
Inflationary pressure realized in the expected direction, but FAO explicitly attributed the surge to both ruble depreciation and the embargo.

### BIS advanced-computing / semiconductor controls (2022)

Historical mechanism source:
- U.S. Bureau of Industry and Security, 7 October 2022.
- BIS stated that the controls were intended to restrict PRC access to specified advanced-computing chips, semiconductor-manufacturing equipment and related production capabilities.

Independent operating outcome:
- NVIDIA Form 10-Q, 28 August 2024.
- NVIDIA reported that it had received no licenses to ship specified restricted products to China.
- partners/customers had experienced license delays or non-receipt.
- China Data Center revenue share remained below levels seen before the later October 2023 control expansion.
- NVIDIA had adapted with China-specific products not requiring export licenses.

Governed class:
`PARTIAL_REALIZATION`

Reason:
The licensing-barrier mechanism clearly operated, but the observed 2024 state reflects the original 2022 controls plus subsequent 2023 updates and product adaptation. HYDRA does not attribute the full outcome to the October 2022 rule alone.

### WTO China rare-earths dispute implementation (2014–2015)

Historical mechanism source:
- USTR, 26 March 2014.
- USTR described China's rare-earth, tungsten and molybdenum export restraints as a mechanism that raised foreign input costs and distorted downstream competition.

Outcome:
- WTO Dispute Settlement Body record, 20 May 2015.
- China reported that the challenged duties, quotas and specified trading-right restrictions had been removed.
- the United States remained concerned that a licensing requirement could still function as an export restriction and did not accept China's assessment of full compliance.

Governed class:
`UNEVALUABLE`

Reason:
The implementation mechanism moved materially, but the authoritative WTO record itself preserves a live compliance disagreement. HYDRA therefore does not convert one party's compliance statement into uncontested historical truth.

## Corpus state

- Batch 008: 3 classified / 0 calibrated
- Batch 009: 6 / 0
- Batch 010: 9 / 0
- Batch 011: 12 / 0
- Batch 012: 15 / 0
- Batch 013: **18 / 0**

Outcome mix:
- 16 `PARTIAL_REALIZATION`
- 2 `UNEVALUABLE`

Mean first admitted outcome-evidence lead time across all 18 records: approximately **654.95 days**.
Median: approximately **426.64 days**.

New-case evidence-availability intervals:
- Russia food embargo: 204 days
- BIS semiconductor controls: 691 days
- rare-earths dispute: 420 days

These are source-availability intervals, not effect-onset or trading-profit intervals.

## Confidence discipline

New confidence semantics:
- Russia / World Bank: `QUALITATIVE_EXPECTATION`
- BIS: `TARGET_OR_OBJECTIVE`
- rare earths / USTR: `QUALITATIVE_RISK`

None supplies an admissible numeric historical probability.

## Integrity

Batch 013 requires:
- all 15 Batch 012 predecessor records unchanged;
- all new cases already exist in the immutable replay-ready corpus;
- hypothesis/outcome publisher independence;
- hypothesis-before-outcome timing;
- no numeric confidence admission;
- exact mapping/enrichment source agreement;
- Russia and BIS map to `PARTIAL_REALIZATION`;
- rare earths maps to `UNEVALUABLE`;
- the rare-earths contradiction flag remains open;
- governing Git blob pins match checked-out bytes;
- only the two calibration blockers remain;
- Brier score remains disabled.

## Remaining unclassified replay-ready cases

After Batch 013, four of the original twenty-two replay-ready cases remain without governed historical classification:

- Eastern Mediterranean offshore-drilling dispute
- EU CBAM transitional phase
- Japan-Korea export-control relations
- Nord Stream 2 certification state

These remaining cases are materially thinner and should not be promoted merely to reach a round number.
