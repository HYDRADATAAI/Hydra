# HYDRA CONSTRAINT — Thread 6 Successor Batch 027 Workstation Execution Launcher

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`  
**Predecessor:** Batch 026  
**Result:** `PASS_WORKSTATION_EXECUTION_LAUNCHER_READY_PRIVATE_CAPTURE_NOT_EXECUTED`

Batch 027 turns the Batch-026 private execution packet into one bounded Windows workstation workflow.

## Launcher

`tools/Invoke-HydraConstraintSemiconductorBatch026PrivateT1.ps1`

Modes:

- **ContractCheck** — public wiring only;
- **Prep** — creates the private inbox, 41-row capture checklist, expected-sidecar templates, and local instructions;
- **Status** — validates whether all 41 capture files/sidecars are ready, without persisting anything;
- **Materialize** — runs the Batch-026 immutable T1 materializer;
- **Verify** — verifies receipts/release/ordinary-T2 eligibility and writes the private handback;
- **All** — materialize + verify + handback.

## Handback

The private handback builder emits:

`HYDRA_CONSTRAINT_SEMI_B026_PRIVATE_T1_HANDBACK_V001.json`

only after all 41 expected receipts validate, exact release membership matches the queue, and all 41 members pass ordinary-T2 eligibility.

The handback includes release identity/digest and per-source artifact/receipt hashes for the successor replay lane.

## Safety boundaries

The launcher performs no web/network acquisition.

It does not infer capture time from file timestamps.

It does not backdate `available_at` to the earlier public review.

It does not allow incomplete receipt sets to create a release or handback.

## Current state

```ini
WORKSTATION_LAUNCHER_READY=YES
PRIVATE_HANDBACK_BUILDER_READY=YES
EXPECTED_PRIVATE_SOURCE_COUNT=41
RAW_SOURCE_VERSIONS_MATERIALIZED=0
VALID_T1_RECEIPTS=0
ORDINARY_T2_ELIGIBLE_SOURCES=0
HISTORICAL_REPLAY=BLOCKED
FIRST_SEMICONDUCTOR_RUN=BLOCKED
NEXT_REQUIRED_ACTION=RUN_BATCH027_WORKSTATION_PREP_THEN_CAPTURE_THEN_ALL
```
