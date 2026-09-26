# HYDRA CONSTRAINT — Thread 6 Successor Batch 015 Persisted T1→T2 Chain-of-Custody Hardening

**Predecessor:** Batch 014  
**Owner:** `PIPELINE_T1_SOURCE_ACQUISITION`  
**Result:** `PASS_CUSTODY_HARDENED_FIRST_SERIOUS_RUN_STILL_BLOCKED`

Batch 015 hardens the private T1 raw-artifact mechanism before real first-slice
source bodies are materialized. It does not close any data, replay, confidence,
evaluation, or implementation-admission blocker.

## Integrity defect closed

The original Batch 008 store persisted immutable source-version receipts and
release manifests, but ordinary T1→T2 eligibility could still validate
caller-supplied receipt/release mappings without proving those mappings were the
exact immutable records persisted by the store.

A caller could therefore reconstruct metadata around a real artifact, recompute
the record digest, and fabricate a structurally valid in-memory release. That
was inconsistent with the intended release-authority boundary.

Batch 015 requires exact persisted identity.

## Current ordinary T1→T2 requirements

Ordinary eligibility now requires:

- valid raw artifact bytes and matching SHA-256;
- source and source-version identity;
- acquired_at and available_at;
- ELIGIBLE processing disposition;
- the exact persisted source-version receipt;
- the exact persisted release manifest;
- exact release membership.

A caller-supplied lookalike is not authority.

Release creation itself also rejects any receipt that is not the exact
persisted record.

## Private/public boundary

Object, receipt, and release destinations are resolved before use. A descendant
symlink may not redirect a private write into the public Git repository or
outside the configured private root.

## Blockers deliberately unchanged

The nine real original first-slice source bodies are still not materialized.
Ordinary historical replay is still blocked. Native T5→T6 admission remains
absent. Batch 014 confidence/evaluation blockers remain unchanged.

The next repo-executable lane therefore remains:

`FIRST-SLICE-TYPED-CONFIDENCE-AND-EVALUATION-READINESS-CLOSURE`

No raw source body, private D-drive fixture, runtime authority, canonical
promotion, ranking, model-training authority, trading authority, or external
effect is introduced.

```ini
THREAD6_SUCCESSOR_BATCH015=PASS
T1_T2_PERSISTED_CHAIN_OF_CUSTODY_READY=YES
CALLER_SUPPLIED_IN_MEMORY_RELEASE_AUTHORITY=NO
FORGED_RECEIPT_DISPOSITION_UPGRADE=BLOCKED
REAL_RAW_ARTIFACTS_MATERIALIZED=NO
IMPLEMENTATION_ADMITTED=NO
ORDINARY_HISTORICAL_REPLAY_READY=NO
FULL_CONSTRAINT_RUN_READY=NO
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
NEXT_REPO_EXECUTABLE_LANE=FIRST-SLICE-TYPED-CONFIDENCE-AND-EVALUATION-READINESS-CLOSURE
```
