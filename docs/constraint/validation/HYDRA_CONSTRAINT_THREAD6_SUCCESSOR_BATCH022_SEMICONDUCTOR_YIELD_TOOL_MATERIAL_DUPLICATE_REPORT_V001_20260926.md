# HYDRA CONSTRAINT — Thread 6 Successor Batch 022 Yield / Tool / Material / Duplicate Evidence Depth

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`  
**Predecessor:** Batch 021  
**Result:** `PASS_TOOL_MATERIAL_DUPLICATE_CASE_DEPTH_YIELD_PROGRESS`

## Case 4 — tool bottleneck

TSMC's Q2-2026 call contains a real backend-equipment bottleneck: customer products required more testers and TSMC stated the tester was in shortage, requiring additional CapEx in tester/packaging areas.

This is paired with TSMC's annual-report equipment dependency: limited suppliers and long delivery cycles can prevent timely capacity expansion.

Hydra closes the **tool bottleneck** case at a bounded backend variant. It does **not** fabricate a specific fab completion delay from tester shortage.

## Case 5 — material bottleneck

The high-purity quartz chain now proves the intended semantic distinction:

```text
quartz geologically abundant
!= high-purity quartz
!= ultra-high-purity processed quartz
!= semiconductor crucible input availability
```

USGS links HPQ to fused-quartz crucibles used for semiconductor silicon-ingot/wafer production and identifies two U.S. HPQ producers around Spruce Pine in 2024.

Hurricane Helene caused both reviewed Spruce Pine producers, Sibelco and The Quartz Corp, to halt operations.

The constraint is therefore attached to **high-purity processing/operational availability**, not geological quartz existence. No downstream semiconductor shutdown is invented.

## Case 14 — duplicate-source inflation

Micron's February-26-2024 HBM3E volume-production announcement exists on Micron's investor site and as a GlobeNewswire distribution copy attributed to Micron.

Hydra represents:

```text
2 source occurrences
1 underlying origin event
1 independence cluster
0 extra confidence from the distribution copy
```

This closes the duplicate-source inflation case.

## Case 3 — HBM yield

Primary evidence confirms that yield is a distinct HBM mass-production dimension and that 12-layer HBM3E adds process complexity. However, reviewed evidence still does not prove a bounded episode where nominal capacity was sufficient while effective usable output was bindingly constrained by yield.

Case 3 therefore remains open.

## Current coverage

Newly covered: **4, 5, 14**.

Coverage becomes **11/14**.

Remaining cases:

- 3 — HBM yield constraint;
- 11 — constraint migration;
- 12 — historical no-lookahead / ordinary replay.

```ini
THREAD6_SUCCESSOR_BATCH022=PASS
NEW_REQUIRED_CASES_COVERED=4,5,14
REQUIRED_CASES_COVERED=11/14
HBM_YIELD_CASE=CURRENT_PROGRESS_ONLY
CONSTRAINT_MIGRATION_CASE=CURRENT_PROGRESS_ONLY
HISTORICAL_REPLAY=BLOCKED
FIRST_SEMICONDUCTOR_RUN=BLOCKED
NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-HBM-YIELD-AND-CONSTRAINT-MIGRATION-DEPTH
```
