# HYDRA Constraint — Geopolitical & Policy Historical Layer
## Batch 003 Gap-Closure Expansion — 2026-09-25

Status: **SOURCED / POINT-IN-TIME / CROSS-LAYER TESTED**, pending successor-branch CI.

This successor pass preserves Batch 001 and Batch 002 artifacts unchanged and closes additional historical-mechanism gaps.

## Batch 003 cases

| Case | Mechanism | Historical proof |
|---|---|---|
| Russia food import ban (2014) | EMBARGO | first-class embargo event with conservative same-day availability |
| EU fifth restrictive package (2022) | EMBARGO + PORT_RESTRICTION | Russian coal import ban and Russian-flagged vessel entry ban to EU ports |
| EU battery IPCEI (2019) | SUBSIDY | explicit multi-state public aid tied to battery industrial capacity/value chain |
| Panama Canal drought measures (2023) | INFRASTRUCTURE_POLICY | water constraint → canal → transit-capacity policy, then later slot adjustment |
| U.S.-China Section 301 sequence (2018) | TRADE_DISPUTE | three separate tariff stages with distinct KNOWN_AT and EFFECTIVE_AT clocks |
| WTO China rare-earths dispute (2014–2015) | STRATEGIC_RESOURCE_DISPUTE | neutral multilateral dispute record covering rare earths, tungsten and molybdenum |

## Temporal hardening

Batch 003 retains the conservative rule from Batch 002:

When an official publication exposes a historical date but no reliable publication clock time, the evidence becomes available at **23:59:59 UTC** on that date.

This prevents a document published sometime during a date from being incorrectly visible at 00:00 UTC that morning.

The regression suite explicitly proves this on the 7 August 2014 Russian food-import action.

## Port access as physical evidence

The EU fifth-package case represents:

`transport:russian-flagged-vessels-2022 → transported_via → infrastructure:eu-ports-restrictive-measures-2022`

The policy event references the transport and infrastructure identities; the graph edge is structural context, not a prediction of trade volume or economic loss.

## Explicit subsidy case

The 2019 battery IPCEI adds a first-class `SUBSIDY` event and a minimal physical chain:

`manufacturing:eu-battery-ipcei-participants-2019 → manufactures → product:eu-battery-value-chain-ipcei-2019`

The source establishes approved public support and the covered battery-value-chain project. No later project-output assumption is imported into the 2019 snapshot.

## Panama water / infrastructure constraint

The sourced Panama Canal subgraph represents:

`bottleneck:panama-canal-water-deficit-2023 → constrains → infrastructure:panama-canal`

and:

`infrastructure:panama-canal → requires → resource:gatun-lake-water-storage`

`infrastructure:panama-canal → supplies → transport:panama-canal-transit`

A-48-2023 is stored as an announced reduction policy with a later effective date. A-54-2023 is a later policy adjustment and does not retroactively alter the October replay state.

## Multi-stage trade dispute

The Section 301 case deliberately does not collapse the 2018 sequence into one generic "trade war" record.

It stores separately:

1. List 1 announcement → 6 July effective date.
2. List 2 finalization → 23 August effective date.
3. List 3 finalization → 24 September effective date.

The associated USTR allegations and stated rationale remain source-attributed context; HYDRA records the documented tariff actions as facts.

## Strategic-resource dispute

The WTO case uses the WTO Secretariat's dispute-settlement record rather than adopting a national government's framing.

It records:
- DSB adoption of the rare-earths/tungsten/molybdenum reports on 29 August 2014;
- a later 20 May 2015 observation that China reported removal of specified export duties, quotas and trading-right restrictions, while the WTO summary also recorded remaining U.S. concern over licensing.

The observation therefore preserves disagreement rather than silently converting one party's compliance statement into uncontested fact.

## Batch 003 validation

The successor test suite requires:

- 6 case families;
- 10 executable historical events;
- 10 provenance-bearing policy sources;
- unique event IDs across Batches 001–003;
- canonical physical binding for every event;
- authoritative replay Evidence emission;
- same-day lookahead prevention;
- embargo and port-restriction event-type admission;
- subsidy → industrial-capacity traversal;
- Panama water/canal/transit traversal;
- three-stage trade-dispute replay cuts;
- strategic-resource dispute linkage.

## Remaining material gaps

After Batch 003 the historical architecture has sourced examples for:

- sanctions;
- export controls;
- import restrictions;
- tariffs;
- embargoes;
- nationalization;
- industrial policy;
- subsidies;
- trade disputes;
- strategic-resource disputes;
- shipping disruptions;
- port restrictions;
- regulatory changes;
- infrastructure operating policy.

Still materially thin or absent:

- territorial-dispute history with defensible neutral evidence;
- diplomatic deterioration with direct documented economic relevance;
- infrastructure commissioning/cancellation histories;
- incentive programs distinct from direct subsidy;
- agricultural/water-policy cases beyond transit water availability;
- much broader observed-outcome coverage;
- larger cross-region corpus suitable for serious warning-sign evaluation.

Those remain explicit coverage gaps rather than implied completeness.
