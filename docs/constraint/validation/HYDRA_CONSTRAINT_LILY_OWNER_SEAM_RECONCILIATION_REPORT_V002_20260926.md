# HYDRA CONSTRAINT — Lily Owner-Seam Reconciliation Rebase

## Scope

This is the bounded rebase of PR #56 onto current main after Batch016 and the merged T1 persisted-custody hardening.

It retains only the T5→T6 temporal/identity seam work that remains unique.

## Retained

The rebased seam makes the following states explicit without rewriting Batch010:

- a successor-only candidate `available_at`;
- unknown effective interval remains unknown;
- null canonical constraint ID remains `NOT_EVALUATED`, not implicitly distinct/merged;
- T5 candidate IDs remain separate from T6 canonical and beneficiary identities;
- beneficiary evidence must remain linked to parent constraint-support evidence;
- ordinary-T6 eligibility remains false while raw lineage and signed admission are blocked.

## Removed from the old PR #56 stack

The old PR also carried T1 custody/materialization work. That is not brought forward here.

Persisted T1→T2 custody hardening is already merged separately at:

`288c06e86aca58256875183d18fa425b7adbf594`

This rebase therefore sets:

- `T1_CUSTODY_REIMPLEMENTED=NO`;
- `RAW_SOURCE_BODIES_MATERIALIZED=NO`;
- `NETWORK_ACQUISITION=NONE`.

## Confidence reconciliation

The old PR #56 overlay used `NOT_EVALUATED` for formation confidence. That representation is stale after Batch015.

Current authority is reused from:

`HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH015_AI_DATA_CENTER_POWER_INFRASTRUCTURE_TYPED_CONFIDENCE_OVERLAY_V001`

Current states remain:

- T5 formation confidence: `UNKNOWN_NOT_MEASURED`;
- beneficiary confidence: `UNKNOWN_INELIGIBLE_TO_EVALUATE`;
- no numeric confidence invented.

The temporal/identity overlay does not duplicate or override those confidence semantics.

## Current acceptance boundary

Batch016 remains authoritative:

- canonical constraints: 0;
- qualified beneficiaries: 0;
- implementation admission: BLOCKED;
- provenance: BLOCKED;
- ordinary replay: BLOCKED;
- evaluation acceptance: BLOCKED;
- first serious Constraint run: BLOCKED.

No source capture, signed receipt issuance, canonical minting, or replay promotion is performed by this rebase.

## Result

```ini
OWNER_SEAM_REBASE=PASS_EXPECTED
UNIQUE_T5_T6_SEAM_RETAINED=YES
T1_CUSTODY_DUPLICATION=NO
BATCH015_CONFIDENCE_REUSED=YES
CANONICAL_CONSTRAINTS_MINTED=0
QUALIFIED_BENEFICIARIES=0
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
FIRST_SLICE_REPO_EXPANSION=HOLD
```
