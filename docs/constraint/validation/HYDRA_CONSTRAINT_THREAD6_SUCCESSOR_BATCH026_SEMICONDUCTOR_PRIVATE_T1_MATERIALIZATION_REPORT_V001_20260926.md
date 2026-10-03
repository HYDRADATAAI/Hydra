# HYDRA CONSTRAINT — Thread 6 Successor Batch 026 Semiconductor Private T1 Materialization Execution Packet

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`  
**Predecessor:** Batch 025  
**Result:** `PASS_PRIVATE_T1_EXECUTION_PACKET_READY_MATERIALIZATION_NOT_EXECUTED`

Batch 026 converts the remaining private raw-lineage blocker into an exact workstation execution packet.

## Capture queue

The packet contains **41 unique source capture intents**, covering every unique source registered across semiconductor Batches 018–025.

Each intent freezes:

- `source_id`;
- reserved `source_version_id`;
- source locator;
- publisher/title;
- source-family context;
- preferred capture representation;
- unique inbox filename;
- reviewed availability timestamp for reference only.

## Critical temporal rule

The earlier public-review `available_at` is **not** copied into the private T1 receipt.

For Batch 026:

```text
receipt.acquired_at
=
actual private capture timestamp

receipt.available_at
=
actual private capture timestamp
```

unless a future execution has explicit proof that the exact captured version was available earlier. This packet authorizes no historical backdating.

## Execution model

The existing T1 private raw store remains authoritative and performs no network acquisition.

The workstation flow is:

```text
authorized browser/manual acquisition
→ private inbox file
→ capture sidecar
→ Batch026 local materializer
→ immutable SHA256 raw object
→ immutable source-version receipt
→ exact 41-member T1 release
→ Batch026 private verifier
→ ordinary T2 eligibility
```

Raw source bytes never enter the public repository.

## Public status

No private capture has been executed by this repository batch.

```ini
PRIVATE_CAPTURE_EXECUTION_PACKET_READY=YES
UNIQUE_SOURCE_CAPTURE_INTENTS=41
SOURCE_VERSION_IDS_RESERVED=41
RAW_SOURCE_VERSIONS_MATERIALIZED=0
VALID_T1_RECEIPTS=0
T1_RELEASE_MANIFEST_PRESENT=NO
ORDINARY_T2_ELIGIBLE_SOURCES=0
REQUIRED_CASES_COVERED=13/14
HISTORICAL_REPLAY=BLOCKED
FIRST_SEMICONDUCTOR_RUN=BLOCKED
NEXT_REQUIRED_ACTION=EXECUTE_BATCH026_PRIVATE_CAPTURE_QUEUE_ON_WORKSTATION
```
