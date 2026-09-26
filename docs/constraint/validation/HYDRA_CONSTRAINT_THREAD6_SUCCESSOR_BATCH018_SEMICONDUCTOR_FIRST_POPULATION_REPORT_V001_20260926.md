# HYDRA CONSTRAINT — Thread 6 Successor Batch 018 Second-Slice Source Authority + First Population

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`  
**Predecessor:** Batch 017  
**Result:** `PASS_FIRST_POPULATION_PARTIAL`

Batch 018 creates the first real semiconductor population without parallel semantics.

## Primary source stack

Six reviewed primary sources are registered:

- NVIDIA current HGX technical documentation;
- Micron fiscal-Q2-2025 prepared remarks;
- two SK hynix HBM production/sales disclosures;
- TSMC Q1-2025 earnings transcript;
- TSMC 2024 annual report.

All receive conservative Hydra `available_at=2026-09-26T21:05:03Z`. Their older publication/event dates are preserved separately. Raw source bodies are not materialized, so none is ordinary historical replay eligible.

## First dependency chain

The graph now connects the existing first-slice AI-demand node into semiconductor demand:

```text
AI_COMPUTE_DEMAND
→ AI_ACCELERATOR_DEMAND
→ NVIDIA H200 / B200
→ HBM3E
→ Micron / SK hynix HBM supply
```

and in parallel:

```text
AI_ACCELERATOR_DEMAND
→ TSMC CoWoS
→ advanced-packaging capacity
```

This is the first cross-slice semiconductor linkage, not yet the full AI→semiconductor→power chain.

## Capacity, yield and qualification

Six typed capacity observations are populated.

Important examples:

- Micron calendar-2025 HBM output is represented as `BOOKED`, not as zero installed capacity.
- Micron HBM3E 12H is `RAMPING`; yield is `RAMPING_UNQUANTIFIED`, never fabricated numerically.
- SK hynix HBM3E is represented as `OPERATIONAL` after disclosed volume production.
- TSMC CoWoS is `OPERATIONAL` and `FULLY_LOADED`; the 2025 doubling plan is a separate ramp/expansion observation, not realized capacity.

## First shadow constraints

Two T5 proposals are formed:

1. `T5C-SEMI-TSMC-COWOS-CAPACITY-2025-001` — bounded TSMC CoWoS advanced-packaging capacity constraint.
2. `T5C-SEMI-HBM-BOOKED-SUPPLY-2024-2025-001` — bounded cross-supplier HBM booked/committed supply constraint using Micron and SK hynix evidence.

Neither is canonical and neither is ordinary-T6 eligible.

## Required cases

Cases 1 and 2 are now covered at bounded reviewed-shadow scope:

- real advanced-packaging bottleneck;
- announced/expected capacity relief that does not erase the prior constrained state.

The remaining 12 cases stay explicit gaps.

```ini
THREAD6_SUCCESSOR_BATCH018=PASS_FIRST_POPULATION_PARTIAL
SOURCE_AUTHORITY_REGISTRY_READY=YES
PRIMARY_SOURCES_REGISTERED=6
EVIDENCE_OBSERVATIONS=10
SUPPLIERS_POPULATED=4
PRODUCTS_TECHNOLOGIES_POPULATED=7
FACILITIES_POPULATED=0
MATERIALS_POPULATED=0
CAPACITY_STATE_OBSERVATIONS=6
DEPENDENCY_EDGES=13
CROSS_SLICE_EDGES=1
CONSTRAINTS_FORMED_SHADOW=2
CANONICAL_CONSTRAINTS_MINTED=0
REQUIRED_CASES_COVERED=2/14
HISTORICAL_REPLAY=BLOCKED
FIRST_SEMICONDUCTOR_RUN=BLOCKED
NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-FACILITY-MATERIAL-EQUIPMENT-AND-QUALIFICATION-POPULATION
```
