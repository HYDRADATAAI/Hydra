# HYDRA Constraint — Geopolitical & Policy Historical Layer
## Batch 004 State-Transition & Capacity Expansion — 2026-09-25

Status: **SOURCED / POINT-IN-TIME / CAPACITY-AWARE / CROSS-LAYER TESTED**, pending successor-branch CI.

This successor pass preserves Batches 001–003 unchanged and targets the remaining state-transition gaps: diplomatic/economic deterioration, territorial-resource disputes, infrastructure certification halts, explicit tax incentives, and infrastructure commissioning.

## Batch 004 cases

| Case | Mechanism | New historical proof |
|---|---|---|
| Japan–Korea export-control relations (2019) | ECONOMICALLY_RELEVANT_DIPLOMATIC_CHANGE | physical validity and evidence knowledge are separated; July action does not import September-only material identities |
| Eastern Mediterranean offshore drilling framework (2019–2020) | TERRITORIAL_DISPUTE | EU characterization is stored as attributed evidence rather than HYDRA adjudicating sovereignty |
| Nord Stream 2 certification state (2021–2022) | REGULATORY_CHANGE + INFRASTRUCTURE_POLICY | legal-form suspension and later government halt remain separate certification states |
| U.S. section 45X (2022–2023) | INCENTIVE | enacted tax incentive is known before its 1 January 2023 production eligibility boundary |
| Wilhelmshaven LNG terminal (2022–2023) | INFRASTRUCTURE_POLICY | commissioning state plus typed ~5 bcm/year sourced capacity and later operational observation |

## Validity vs knowledge

The Japan–Korea case intentionally encodes:

- physical/action validity from 4 July 2019;
- source knowledge from the WTO record on 10 July 2019.

The later September WTO dispute record names fluorinated polyimide, resist polymers and hydrogen fluoride. Those later-pinned identities are **not** backfilled into the July event.

This proves:

`VALID_AT != KNOWN_AT`

and prevents hindsight from enriching an earlier replay cut.

## Territorial-resource neutrality

The Eastern Mediterranean case records the Council of the EU's 11 November 2019 restrictive-measures framework and later February 2020 listings.

HYDRA does not independently decide:
- maritime sovereignty;
- EEZ delimitation;
- whether a drilling activity was legally authorised under competing claims.

The event statement explicitly attributes the "unauthorised" characterization to the Council source.

## Infrastructure cancellation / certification history

Nord Stream 2 is represented as two separate documented states:

1. 16 November 2021 — Bundesnetzagentur suspended certification on legal/organizational grounds.
2. 22 February 2022 — the German Federal Government withdrew the prior Security of Supply Report and halted the procedure pending reassessment.

The later state does not rewrite the earlier regulatory reason.

## Explicit incentive

Public Law 117-169 established section 45X on 16 August 2022 and made the credit applicable to eligible components produced and sold after 31 December 2022.

The physical graph therefore stores 45X manufacturing/component identities as:
- `known_at = 2022-08-16`
- `valid_from = 2023-01-01`

The later Treasury/IRS proposed guidance is an observation, not retroactive knowledge at enactment.

## Infrastructure commissioning and capacity

The Wilhelmshaven source states that the FSRU would provide about 5 billion cubic metres per year of regasification capacity from January.

Batch 004 upgrades the sourced physical-graph loader so JSON capacity fields become typed:

- `Snapshot.capacity_nameplate`
- `Snapshot.capacity_usable`
- `Snapshot.capacity_unit`
- `Snapshot.utilization`
- `Snapshot.market_share`
- `Edge.share`
- `Edge.capacity`
- `Edge.capacity_unit`
- `Edge.substitution_time_days`

Invalid numeric types, negative capacities, invalid fractions, invalid units and invalid substitution-time values now fail closed during sourced-graph admission.

The Wilhelmshaven record is stored as:

`capacity_nameplate = 5.0`
`capacity_unit = bcm/year`

with knowledge on 17 December 2022 and validity from 1 January 2023.

## Batch 004 validation

The successor tests require:

- 5 case families;
- 6 executable historical events;
- 10 provenance-bearing sources;
- unique event IDs across Batches 001–004;
- canonical physical binding for every event;
- authoritative replay Evidence emission;
- no September material-identity leakage into July 2019;
- source-attributed territorial characterization;
- distinct Nord Stream 2 certification states;
- known-before-effective section 45X incentive state;
- typed point-in-time Wilhelmshaven capacity;
- rejection of nonnumeric and negative sourced capacities.

## Coverage state after Batch 004

Constraint now has sourced examples for all major event classes in the current taxonomy, including:
- SANCTION
- EXPORT_CONTROL
- IMPORT_RESTRICTION
- TARIFF
- EMBARGO
- NATIONALIZATION
- INDUSTRIAL_POLICY
- TRADE_DISPUTE
- TERRITORIAL_DISPUTE
- STRATEGIC_RESOURCE_DISPUTE
- SHIPPING_DISRUPTION
- PORT_RESTRICTION
- SUPPLY_AFFECTING_CONFLICT-adjacent transport restoration context
- ECONOMICALLY_RELEVANT_DIPLOMATIC_CHANGE
- REGULATORY_CHANGE
- INFRASTRUCTURE_POLICY
- SUBSIDY
- INCENTIVE

The largest remaining weakness is no longer event-type coverage. It is **depth**:

- larger observed-outcome histories;
- multi-cut replay across each case;
- historical quantitative capacity/share series;
- broader geography and actor coverage;
- 20–40+ defensible gold cases suitable for serious warning-sign evaluation;
- explicit contradiction/revision examples from competing contemporaneous sources.

Those remain coverage goals, not implied completeness.
