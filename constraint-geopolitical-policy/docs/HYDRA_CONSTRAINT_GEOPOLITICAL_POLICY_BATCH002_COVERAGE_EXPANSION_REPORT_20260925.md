# HYDRA Constraint — Geopolitical & Policy Historical Layer
## Batch 002 Coverage Expansion — 2026-09-25

Status: **SOURCED / POINT-IN-TIME / CROSS-LAYER TESTED**, subject to CI on this successor branch.

This pass extends the Batch 001 proof without rewriting its case files.

## Batch 002 additions

Seven new historical case families and eight executable historical events:

| Case | Mechanism | KNOWN_AT vs EFFECTIVE_AT proof | Physical binding |
|---|---|---|---|
| U.S. Section 232 steel tariff (2018) | TARIFF | Published before tariff effective date | covered steel articles + U.S. steel production |
| China gallium/germanium controls (2023) | EXPORT_CONTROL / strategic resource access | announcement 3 Jul; effective 1 Aug | gallium + germanium controlled-item resources |
| U.S. PDVSA designation (2019) | SANCTION | designation represented at source availability | PDVSA + Venezuela ownership relation |
| IMO sulphur 2020 | REGULATORY_CHANGE | 2016 decision; 2020 implementation | ship fuel oil + global maritime shipping |
| Germany / Uniper (2022) | NATIONALIZATION | announcement separated from later completed ownership | Uniper + time-gated Germany control edge |
| EU CBAM transitional phase (2023) | REGULATORY_CHANGE | Aug rules before Oct phase start | CBAM-covered goods |
| Black Sea Grain Initiative (2022) | SHIPPING_DISRUPTION / supply-access restoration | agreement separated from later first shipment | grain → corridor → Odesa / Chornomorsk / Yuzhny-Pivdennyi |

## Temporal discipline

Where the source provides a calendar date but not a publication clock time, Batch 002 conservatively records source availability at **23:59:59 UTC** for that date rather than pretending the evidence was available at midnight.

The MOFCOM source exposes a publication time, so its 18:00 China Standard Time timestamp is represented as 10:00 UTC.

This reduces same-day lookahead leakage relative to date-only midnight defaults.

## Nationalization state transition

The Uniper case intentionally uses two events:

1. 21 September 2022 — the intended approximately 99% federal takeover was publicly announced.
2. 22 December 2022 — completion of federal participation was publicly documented.

The physical ownership edge:

`company:uniper → controlled_by → country:germany`

is not visible at the September replay cut and becomes resolvable only at the December completion cut.

## Multi-node logistics proof

The Black Sea case adds a resource/logistics chain:

`Ukrainian grain/foodstuffs → transported_via → Black Sea export corridor`

and the corridor requires the three ports named in the UN material:

- Odesa
- Chornomorsk
- Yuzhny/Pivdennyi

The later 3 August first-shipment record remains an observation and is not available at the 22 July agreement cut.

## Claim discipline

This pass records documented actions and source-described infrastructure/resource relationships.

It does not encode:
- unsupported state motives;
- a geopolitical "winner" or "loser";
- predicted market effects;
- causal economic outcomes not established by the cited evidence;
- inferred supply-chain links solely to increase graph density.

## Batch-level validation

The successor tests require:

- unique IDs across Batch 001 + Batch 002;
- provenance digest integrity;
- valid source availability before KNOWN_AT;
- canonical physical binding for every Batch 002 event;
- authoritative replay Evidence emission;
- announced-before-effective preservation;
- future ownership edge exclusion;
- multi-port Black Sea traversal;
- point-in-time eligibility for long-lead regulations.

## Remaining coverage gaps after Batch 002

The architecture now has sourced examples for sanctions, export controls, tariffs, nationalization, industrial policy, regulatory change, import restrictions, and shipping disruptions.

Still materially thin or absent:

- explicit embargo case;
- subsidy/incentive case distinct from broader industrial policy;
- port restriction case;
- major infrastructure-policy case with asset commissioning/capacity observations;
- trade-dispute sequence with multiple escalatory actions;
- territorial/resource-dispute case with neutral, defensible sourcing;
- diplomatic deterioration case with direct documented economic relevance;
- larger observed-outcome corpus.

These remain coverage gaps rather than fabricated green status.
