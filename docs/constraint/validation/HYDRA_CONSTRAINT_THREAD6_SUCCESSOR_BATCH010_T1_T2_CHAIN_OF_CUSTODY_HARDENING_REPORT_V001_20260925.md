# HYDRA CONSTRAINT — Thread 6 Successor Batch 010 T1→T2 Persisted Chain-of-Custody Hardening

Predecessor: Batch 009  
Owner: PIPELINE_T1_SOURCE_ACQUISITION  
Result: PASS_CHAIN_OF_CUSTODY_HARDENED_RUN_STILL_BLOCKED

## Defect closed

The Batch 008 private raw store correctly persisted immutable source-version
receipts and immutable release manifests, but ordinary T1→T2 eligibility still
accepted caller-supplied receipt and release objects after structural and digest
validation.

That allowed a self-consistent in-memory reconstruction to stand in for the
durable record that was intended to define authority. In particular, a caller
could reconstruct metadata around a real artifact, recompute record digests, and
construct a syntactically valid release object without proving that either
record was the exact immutable object persisted by the store.

Batch 010 closes that gap.

## Current ordinary T1→T2 lineage requirements

Ordinary eligibility now requires all of the following:

- valid raw artifact bytes;
- matching artifact SHA-256;
- source identity and source-version identity;
- acquired_at and available_at;
- ELIGIBLE processing disposition;
- exact persisted source-version receipt identity;
- exact persisted release-manifest identity;
- exact release membership.

A valid-looking in-memory receipt or release manifest is not authority.

## Historical authority preservation

Batch 008 remains unchanged and historically valid as the mechanism-creation
snapshot. Batch 009 remains unchanged and historically valid as the original
first-slice source-gap closure.

This batch explicitly supersedes only the changed raw-store implementation
artifacts. The cross-batch validator accepts a historical blob mismatch only
when the Batch 010 supersession record binds the exact historical blob SHA to
the exact successor blob SHA.

## Safety boundary

No real raw third-party source bodies are added to Git. No live acquisition,
runtime activation, ranking, canonical promotion, model training, trading
authority, or external network effects are granted.

The nine real first-slice raw artifacts remain unmaterialized. Native T5→T6
implementation admission remains blocked pending an exact signed admission
receipt.

THREAD6_SUCCESSOR_BATCH010=PASS
PERSISTED_RECEIPT_IDENTITY_REQUIRED=YES
PERSISTED_RELEASE_IDENTITY_REQUIRED=YES
FORGED_IN_MEMORY_RELEASE_AUTHORITY=NO
FORGED_RECEIPT_DISPOSITION_UPGRADE=BLOCKED
ORIGINAL_FIRST_SLICE_SOURCE_GAPS_CLOSED=YES
NINE_REAL_SOURCE_ARTIFACTS_MATERIALIZED=NO
IMPLEMENTATION_ADMITTED=NO
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
