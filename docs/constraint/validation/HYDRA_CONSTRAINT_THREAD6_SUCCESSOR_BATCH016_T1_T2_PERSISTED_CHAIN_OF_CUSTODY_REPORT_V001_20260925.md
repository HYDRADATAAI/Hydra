# HYDRA CONSTRAINT — Thread 6 Successor Batch 016 Persisted T1→T2 Chain-of-Custody Hardening

**Predecessor:** Batch 015  
**Owner:** `PIPELINE_T1_SOURCE_ACQUISITION`  
**Result:** `PASS_CUSTODY_HARDENED_FIRST_SERIOUS_RUN_STILL_BLOCKED`

Batch 016 hardens the private T1 raw-artifact mechanism before real first-slice
source bodies are materialized. It preserves Batch 015 typed-confidence and
evaluation-protocol progress unchanged.

## Integrity defect closed

The Batch 008 raw store persisted immutable source-version receipts and release
manifests, but ordinary T1→T2 eligibility could still validate caller-supplied
receipt/release mappings without proving those mappings were the exact immutable
records actually persisted by the store.

That permitted a self-consistent reconstruction to masquerade as release
authority. Batch 016 removes that ambiguity.

## Current ordinary T1→T2 requirements

Ordinary eligibility now requires:

- valid raw artifact bytes and matching SHA-256;
- source and source-version identity;
- acquired_at and available_at;
- ELIGIBLE processing disposition;
- exact persisted source-version receipt identity;
- exact persisted release-manifest identity;
- exact release membership.

A caller-supplied lookalike is not authority.

Release creation also rejects any receipt that is not the exact persisted
record.

## Private/public boundary

Object, receipt, and release destinations are resolved before use. Descendant
symlinks cannot redirect private writes into the public Git repository or
outside the configured private root.

## Preserved Batch 015 progress

Typed formation-confidence and beneficiary-confidence semantics remain ready
with explicit unknowns. The bounded shadow evaluation protocol remains ready.
No confidence blocker is reopened.

## Blockers deliberately unchanged

The seven Batch 015 blockers remain unchanged. Real raw bodies are not
materialized, ordinary replay remains blocked, native T5→T6 admission is absent,
and acceptance-grade evaluation remains unavailable.

The next repo-executable lane remains:

`FIRST-SLICE-REAL-OUTCOME-COVERAGE-EXPANSION`

No raw source body, private D-drive fixture, runtime authority, canonical
promotion, ranking, model-training authority, trading authority, or external
effect is introduced.

```ini
THREAD6_SUCCESSOR_BATCH016=PASS
T1_T2_PERSISTED_CHAIN_OF_CUSTODY_READY=YES
CALLER_SUPPLIED_IN_MEMORY_RELEASE_AUTHORITY=NO
FORGED_RECEIPT_DISPOSITION_UPGRADE=BLOCKED
CONFIDENCE_READY=YES_WITH_EXPLICIT_UNKNOWNS
EVALUATION_PROTOCOL_READY=YES_SHADOW_BOUNDED
REAL_RAW_ARTIFACTS_MATERIALIZED=NO
IMPLEMENTATION_ADMITTED=NO
ORDINARY_HISTORICAL_REPLAY_READY=NO
OUTCOME_EVALUATION_READY=NO_ACCEPTANCE
FULL_CONSTRAINT_RUN_READY=NO
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
NEXT_REPO_EXECUTABLE_LANE=FIRST-SLICE-REAL-OUTCOME-COVERAGE-EXPANSION
```
