# HYDRA CONSTRAINT — Thread 6 Successor Batch 029 Micron Capture-Locator Remediation

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`  
**Predecessor:** Batch 028  
**Result:** `PASS_MICRON_CAPTURE_LOCATOR_REMEDIATION_READY_NOT_EXECUTED`

The first Batch-028 browser attempt stopped cleanly at source 001 with zero accepted captures.

The registered Micron `investors.micron.com/static-files/...` locator now navigates to Micron's investor-relations overview in an interactive browser rather than returning the expected PDF. This is capture-locator drift, not a reason to mutate historical source identity.

## Remediation

Seven Micron source IDs are covered by a successor locator-remediation overlay.

For each source Hydra preserves:

```text
source_id
original registered source_locator
fiscal year / fiscal quarter
document kind
```

At runtime the browser adapter loads Micron's official quarterly-results page and resolves the current document link.

The resolved link must satisfy all of:

```text
scheme = https
host = s25.q4cdn.com
account path = /621799436/files/doc_financials/
quarter path = exact expected fiscal year/quarter
document kind = prepared remarks OR presentation as declared
captured bytes = valid PDF
```

No arbitrary redirect, search-engine result, mirror, or third-party copy is accepted.

## T1 provenance

The Batch-026 queue and earlier source registries are immutable and unchanged.

The actual resolved Q4CDN URL is written to the capture sidecar and then to the T1 raw-artifact receipt.

The private handback records:

```text
registered_source_locator
capture_source_locator
```

so locator evolution remains explicit.

## Current state

```ini
MICRON_LOCATORS_REMEDIATED=7
ORIGINAL_SOURCE_IDENTITIES_PRESERVED=YES
RAW_SOURCE_VERSIONS_MATERIALIZED=0
VALID_T1_RECEIPTS=0
ORDINARY_T2_ELIGIBLE_SOURCES=0
HISTORICAL_REPLAY=BLOCKED
FIRST_SEMICONDUCTOR_RUN=BLOCKED
NEXT_REQUIRED_ACTION=RERUN_BATCH028_BROWSER_CAPTURE_WITH_BATCH029_LOCATOR_REMEDIATION
```
