# HYDRA CONSTRAINT — Thread 6 Successor Batch 011 T1→T2 Persisted Chain-of-Custody Hardening

Predecessor: Batch 010  
Owner: PIPELINE_T1_SOURCE_ACQUISITION  
Result: PASS_CHAIN_OF_CUSTODY_HARDENED_RUN_STILL_BLOCKED

## Defect closed

The Batch 008 private raw store persisted immutable source-version receipts and
immutable release manifests, but ordinary T1→T2 eligibility still accepted
caller-supplied receipt and release objects after structural and digest
validation.

That allowed a self-consistent in-memory reconstruction to stand in for the
durable record intended to define release authority. A caller could reconstruct
metadata around a real artifact, recompute record digests, and construct a
syntactically valid release object without proving that either record was the
exact immutable object persisted by the store.

Batch 011 closes that gap.

## Current ordinary T1→T2 lineage requirements

Ordinary eligibility now requires:

- valid raw artifact bytes;
- matching artifact SHA-256;
- source identity and source-version identity;
- acquired_at and available_at;
- ELIGIBLE processing disposition;
- exact persisted source-version receipt identity;
- exact persisted release-manifest identity;
- exact release membership.

A valid-looking in-memory receipt or release manifest is not authority.

## Current-state reconciliation

Batch 010 remains the authoritative claim/candidate/beneficiary population
closure and is preserved unchanged. Batch 011 consumes that state and adds only
the T1→T2 custody hardening dimension.

Batch 008 remains historically valid as the raw-store mechanism snapshot.
Batch 011 explicitly supersedes only the changed raw-store implementation
artifacts and current integration tooling. Historical blob mismatches are
accepted only when this batch binds the exact predecessor blob SHA to the exact
successor blob SHA.

## Safety boundary

No real raw third-party source bodies are added to Git. No live acquisition,
runtime activation, ranking, canonical promotion, model training, trading
authority, or external network effects are granted.

The first-slice real raw artifacts remain unmaterialized. Native T5→T6
implementation admission remains blocked pending an exact signed admission
receipt. Batch 010 shadow claims and blocked beneficiary evaluations remain
shadow/blocked.

THREAD6_SUCCESSOR_BATCH011=PASS
PERSISTED_RECEIPT_IDENTITY_REQUIRED=YES
PERSISTED_RELEASE_IDENTITY_REQUIRED=YES
FORGED_IN_MEMORY_RELEASE_AUTHORITY=NO
FORGED_RECEIPT_DISPOSITION_UPGRADE=BLOCKED
CLAIM_LAYER_POPULATED=YES_SHADOW
QUALIFIED_BENEFICIARIES_MINTED=NO
NINE_REAL_SOURCE_ARTIFACTS_MATERIALIZED=NO
IMPLEMENTATION_ADMITTED=NO
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
