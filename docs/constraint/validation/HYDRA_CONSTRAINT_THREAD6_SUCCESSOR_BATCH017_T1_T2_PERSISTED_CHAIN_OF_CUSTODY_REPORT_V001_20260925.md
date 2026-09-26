# HYDRA CONSTRAINT — Thread 6 Successor Batch 017 Persisted T1→T2 Chain-of-Custody Hardening

**Predecessor:** Batch 016  
**Owner:** `PIPELINE_T1_SOURCE_ACQUISITION`  
**Result:** `PASS_CUSTODY_HARDENED_ACCEPTANCE_STILL_BLOCKED_EXTERNAL_ONLY`

Batch 017 hardens the private T1 raw-artifact mechanism after the first-slice
repo-executable acceptance blockers were closed in Batch 016.

It does not reopen or close any Batch 016 acceptance blocker.

## Integrity defect closed

The original raw store persisted immutable source-version receipts and release
manifests, but ordinary T1→T2 eligibility could still accept caller-supplied
receipt/release mappings without proving that those mappings were the exact
immutable records persisted by the store.

Batch 017 requires exact persisted identity for both receipt and release.

A recomputed self-consistent lookalike is not authority.

## Fail-closed behavior

- reconstructed QUARANTINED receipts cannot be relabelled ELIGIBLE;
- an unpersisted release manifest cannot grant ordinary T2 eligibility;
- release creation requires exact persisted receipt records;
- changed membership under an existing release identity is rejected;
- missing persisted receipt or release records block eligibility;
- symlink-resolved destinations may not escape the private root or enter the
  public Git repository.

## Preserved Batch 016 state

Batch 016 remains the outcome-coverage closure:

- 5 real outcome records;
- 4 outcome labels;
- 3/3 core evaluation dimensions covered;
- thin-outcome blocker closed;
- 0 repo-executable first-slice acceptance blockers.

Batch 017 preserves those results unchanged.

## Remaining boundary

The first serious run remains blocked only on external/private gates already
recorded by Batch 016: private raw materialization, ordinary replay lineage,
native T5→T6 admission, and canonical outputs required for acceptance-grade
evaluation.

No raw third-party source body, private D-drive fixture, runtime authority,
canonical promotion, ranking, model-training authority, trading authority, or
external effect is introduced.

```ini
THREAD6_SUCCESSOR_BATCH017=PASS
T1_T2_PERSISTED_CHAIN_OF_CUSTODY_READY=YES
CALLER_SUPPLIED_IN_MEMORY_RELEASE_AUTHORITY=NO
FORGED_RECEIPT_DISPOSITION_UPGRADE=BLOCKED
REAL_OUTCOME_RECORDS=5
CORE_REAL_OUTCOME_DIMENSIONS=3_OF_3
REPO_EXECUTABLE_ACCEPTANCE_BLOCKERS=0
REAL_RAW_ARTIFACTS_MATERIALIZED=NO
IMPLEMENTATION_ADMITTED=NO
ORDINARY_HISTORICAL_REPLAY_READY=NO
FULL_CONSTRAINT_RUN_READY=NO
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
NEXT_REPO_EXECUTABLE_LANE=NONE_FIRST_SLICE_ACCEPTANCE_REQUIRES_PRIVATE_RAW_MATERIALIZATION_AND_NATIVE_ADMISSION
```
