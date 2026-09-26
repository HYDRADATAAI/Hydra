# HYDRA CONSTRAINT - Thread 6 Successor Batch 018 Semiconductor Source Authority + First Population

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`  
**Predecessor:** Batch 017  
**Result:** `PASS_REVIEWED_SOURCE_AUTHORITY_AND_FIRST_POPULATION_SHADOW_ONLY`

Batch 018 executes the repository-declared next lane from Batch 017: source authority plus first population.

## What changed

- Added a reviewed primary-source registry with 10 source authorities.
- Added 11 reviewed evidence observations covering H200/HBM3E, NVIDIA supply dependencies, TSMC CoWoS and Arizona N4 ramp, ASML lithography-license restrictions, and BIS semiconductor/HBM controls.
- Added the first bounded company/product/facility/geography/policy population.
- Added 24 evidence-backed dependency edges.
- Seeded a cross-slice path from the existing first-slice AI compute demand node into H200, HBM3E and a memory producer.
- Preserved Batch 017 field requirements, authority map and 14-case matrix unchanged.

## Fail-closed boundaries

This batch deliberately does **not** claim T1 custody, source-version hashes, acquired_at, available_at, ordinary T2 evidence, ordinary T3 relationships, canonical constraints, qualified beneficiaries, historical outcomes or replay readiness.

Every source remains `strict_original_as_of_eligible=false` until raw source versions are captured by the authoritative T1 path.

Samsung's February 2024 HBM3E 12H announcement is represented as **development**, not volume production or NVIDIA qualification.

TSMC's 2023 Arizona schedule and its 2024 actual high-volume-production statement are preserved as separate temporal observations; the later outcome does not rewrite the earlier plan.

## Remaining blockers

1. T1 raw-artifact/source-version custody and real acquired_at/available_at.
2. Semiconductor-grade critical-material population.
3. Deeper advanced-packaging/OSAT facility population.
4. Ordinary cross-slice graph admission.
5. Historical replay corpus and outcome corpus.
6. Functional/adversarial case execution (still 0/14).

## Truthful readiness

```ini
THREAD6_SUCCESSOR_BATCH018=PASS
SOURCE_AUTHORITY_REGISTRY=POPULATED_REVIEWED_SHADOW
FIRST_POPULATION=PARTIAL
DEPENDENCY_EDGES=24
CROSS_SLICE_AI_SEMICONDUCTOR=PARTIAL_REVIEWED_SHADOW
T1_CUSTODY=NO
AVAILABLE_AT=NO
HISTORICAL_REPLAY=BLOCKED
OUTCOMES=EMPTY
REQUIRED_CASES=0_OF_14
FIRST_SEMICONDUCTOR_RUN=BLOCKED
NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-CRITICAL-MATERIAL-AND-PACKAGING-DEPTH-WITHOUT-REPLAY-PROMOTION
```
