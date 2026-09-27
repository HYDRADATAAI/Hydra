# NYX Task 5 — Temporal / authority fail-closed re-audit

Base: `684f59ceea89114f6ac8b356e9b4dfb2b9cafa89`

Disposition: **PASS_NO_NEW_REPAIR_REQUIRED**

`TEMPORAL_AUTHORITY_FAIL_CLOSED = PASS`

## Current temporal boundary

The current T1 raw store rejects availability earlier than acquisition both:
- at persistence entry;
- when validating a persisted receipt, including a caller that recomputes the receipt digest.

Equivalent instants with different UTC offsets remain valid. No historical exception exists in the v1 raw-store contract.

The conservative point-in-time overlay rejects:
- `TIMESTAMP_UNVERIFIED` as an acquisition timestamp;
- missing / malformed acquisition values;
- backdated conservative availability;
- unknown status or authority fields;
- attempts to smuggle canonical admission or production activation metadata.

The overlay validates before temporal eligibility is evaluated, and does not rewrite the caller's status fields.

## Time concept separation

The repository keeps these concepts separate:
- event / effective time;
- source publication time;
- acquisition / capture time;
- conservative availability;
- replay `known_at` cutoff;
- timestamp verification state.

Publication/event dates, Git timestamps, file timestamps, equality of acquisition and availability, hashes, and persisted-custody identity are not treated as independent proof of acquisition time.

## Authority boundary

Current fail-closed controls continue to block:
- ordinary T1 eligibility without exact persisted receipt and release identity;
- native T5→T6 admission without the contract-bound signed receipt/verifier;
- canonical constraint or beneficiary minting from missing authority;
- ordinary replay promotion from shadow/no-lookahead fixtures;
- full-run/readiness or production activation from incomplete evidence.

The current Batch019 admission review remains fail-closed. No receipt was manufactured and no admission authority is inferred.

## PR #97 timestamp review

The current main copies of the three Batch016 correction artifacts are byte-identical to PR #97's repaired head:
- outcome source registry extension: `c2a0f294f9ce37cf94498a05e6029f81a056d600`;
- outcome record supplement: `22ca2612f7c4e99ed5686137050914c856e01d98`;
- Batch016 artifact manifest: `163501b2f03b970b25247e5fd1b7263532e2760d`.

The Eaton and GE Vernova review classifications therefore remain **TIMESTAMP_UNVERIFIED**. Their stored acquisition literals are not independently certified by this audit. No timestamp, source record, or private evidence has been changed.

## Regression evidence reviewed

Current implementation/test evidence includes:
- T1 tests rejecting `available_at < acquired_at`, including recomputed-receipt attacks;
- conservative availability hostile cases for `TIMESTAMP_UNVERIFIED`, malformed/missing acquisition, backdating, canonical-admission smuggling, production activation, and unknown fields;
- first-slice integration / hostile validation;
- NYX successor-chain validation / hostile mutations;
- current public repository hygiene.

No new fail-open path was found in the repository-visible temporal or authority surface.

## Result

```ini
TEMPORAL_AUTHORITY_FAIL_CLOSED=PASS
ACQUISITION_TIMESTAMP_RECONSTRUCTION=NO
BACKDATING_AUTHORIZED=NO
CANONICAL_PROMOTION_FROM_MISSING_EVIDENCE=NO
READINESS_PROMOTION_FROM_MISSING_EVIDENCE=NO
T1_AUTHORITY_PROMOTION_FROM_MISSING_EVIDENCE=NO
T5_T6_ADMISSION_FROM_MISSING_EVIDENCE=NO
PRODUCTION_ACTIVATION_FROM_MISSING_EVIDENCE=NO
EATON_ACQUISITION_CLASSIFICATION=TIMESTAMP_UNVERIFIED
GE_VERNOVA_ACQUISITION_CLASSIFICATION=TIMESTAMP_UNVERIFIED
D_OWNER_GATE=BLOCKED
```
