# HYDRA CONSTRAINT — Thread 6 Successor Batch 028 Semiconductor Browser Acquisition Adapter

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`  
**Predecessor:** Batch 027  
**Result:** `PASS_BROWSER_ACQUISITION_ADAPTER_READY_NOT_EXECUTED`

Batch 028 reuses the proven first-slice browser acquisition pattern without reusing the first-slice nine-source authority.

## Why a separate adapter

The local first-slice runner is intentionally frozen to:

- `AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1`;
- exactly nine source records;
- the first-slice source registry and release path.

The semiconductor slice therefore gets a distinct queue-bound acquisition adapter rather than changing or overloading that runner.

## Adapter

`tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py`

The adapter:

- reads the exact Batch-026 41-source queue;
- requires explicit public-acquisition authorization;
- launches installed Chrome or Edge through a private Playwright runtime/profile;
- captures the raw main-document response body;
- writes the exact queue filename into the Batch-026 private inbox;
- writes the exact Batch-026 `.capture.json` sidecar;
- records actual acquisition time;
- authorizes no historical backdating;
- resumes already-complete capture/sidecar pairs only after revalidation;
- keeps an incremental non-authoritative private journal.

It does **not** write T1 receipts or a T1 release. Batch 026/027 remains the persistence boundary.

## Redirect policy

Default:

`exact`

Optional:

`same-origin`

Same-origin mode still rejects HTTP downgrade and cross-host redirects.

## Current state

```ini
BROWSER_ACQUISITION_ADAPTER_READY=YES
EXPECTED_SOURCE_COUNT=41
DEFAULT_REDIRECT_POLICY=exact
RAW_SOURCE_VERSIONS_MATERIALIZED=0
ORDINARY_T2_ELIGIBLE_SOURCES=0
HISTORICAL_REPLAY=BLOCKED
FIRST_SEMICONDUCTOR_RUN=BLOCKED
NEXT_REQUIRED_ACTION=RUN_BATCH028_BROWSER_CAPTURE_IN_CLEAN_WORKTREE
```
