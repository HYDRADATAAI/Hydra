# HYDRA CONSTRAINT — Thread 6 Successor Batch 004 Point-in-Time Acquisition Capture

**Slice:** `AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1`  
**Predecessor:** `HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003`  
**Mode:** governed manual public-source capture  
**Runtime live-source authority used:** **NO**  
**Result:** `PASS_WITH_STRICT_REPLAY_BLOCKED`

## What Batch 004 closes

Batch 003 correctly refused strict `ORIGINAL_AS_OF` replay because `acquired_at` and exact historical `available_at` were not captured.

Batch 004 decomposes that blocker instead of conflating the two timestamps.

- `PIT-001A-EXACT-ACQUIRED-AT-CAPTURE` → **CLOSED**.
- `PIT-001B-EXACT-AVAILABLE-AT-HISTORICAL-PROOF` → **OPEN / BLOCKING STRICT REPLAY**.

All nine source IDs from the Batch 003 registry were resolved in one governed manual capture window. The batch-completion UTC timestamp is recorded as Hydra `acquired_at` for the capture. No source body, PDF, report, or private fixture is stored in this Batch 004 artifact.

## What Batch 004 does not claim

Current source reachability is not historical availability proof.

Publication day/month/year is not silently promoted to an exact `available_at` timestamp.

Hydra acquisition time is not substituted for source availability time.

This pass does not authorize runtime live-source acquisition, implementation admission, canonical promotion, model training, trading, ranking, or external effects.

## Current state

```ini
THREAD6_SUCCESSOR_BATCH004=PASS_WITH_STRICT_REPLAY_BLOCKED
REGISTERED_SOURCES_PRESERVED=9
ACQUIRED_AT_CAPTURE_READY=YES
AVAILABLE_AT_CAPTURE_READY=NO
STRICT_ORIGINAL_AS_OF_READY=NO
RUNTIME_LIVE_SOURCE_USED=NO
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
NEXT_POPULATION_BLOCKER=PIT-001B-EXACT-AVAILABLE-AT-HISTORICAL-PROOF
```
