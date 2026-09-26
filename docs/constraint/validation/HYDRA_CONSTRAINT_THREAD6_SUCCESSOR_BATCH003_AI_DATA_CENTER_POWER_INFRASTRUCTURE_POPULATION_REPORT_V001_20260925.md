# HYDRA CONSTRAINT — Thread 6 Successor Batch 003 First-Slice Population Seed

**Slice:** `AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1`  
**Mode:** manual-reviewed public-source seed  
**Live source acquisition:** **NO**  
**Result:** `PASS_PARTIAL_POPULATION`

Batch 003 moves the first serious Constraint slice from registration into evidence-backed population without bypassing the still-closed live-source gate.

## Added

- 9 authoritative public source records.
- 24 frozen first-slice fields.
- 9 reviewed evidence observations.
- 14 graph nodes.
- 14 graph edges: 11 evidence-backed, 3 explicit source gaps.

## Evidence-backed areas

The current seed covers:

- AI/data-center electricity demand;
- regional load growth;
- generation/interconnection dependency;
- interconnection queue backlog and duration;
- FERC interconnection reform;
- large-power-transformer supply/import dependence;
- transformer lead-time constraints;
- water/cooling dependency;
- PJM and ERCOT regional large-load growth.

## Explicit gaps

The seed does **not** guess missing data.

These remain unpopulated:

- switchgear lead time;
- land/permitting status;
- fiber/connectivity capacity;
- supplier-specific capacity;
- beneficiary qualification/outcomes.

## Point-in-time rule

These sources are reviewed and useful for current graph population, but they are **not yet admitted to strict `ORIGINAL_AS_OF` replay** because exact Hydra `acquired_at` and/or source `available_at` timestamps have not been captured.

No publication date is silently converted into an exact historical availability timestamp.

## Current state

```ini
THREAD6_SUCCESSOR_BATCH003=PASS_PARTIAL_POPULATION
SOURCE_REGISTRY_READY=YES
FIRST_24_FIELDS_FROZEN=YES
EVIDENCE_SEED_READY=YES
GRAPH_SEED_READY=YES_PARTIAL
LIVE_SOURCE_USED=NO
STRICT_ORIGINAL_AS_OF_READY=NO
DOMAIN_DATA_POPULATED=PARTIAL
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
NEXT_POPULATION_BLOCKER=PIT-001-EXACT-ACQUIRED-AT-AND-AVAILABLE-AT-CAPTURE
```
