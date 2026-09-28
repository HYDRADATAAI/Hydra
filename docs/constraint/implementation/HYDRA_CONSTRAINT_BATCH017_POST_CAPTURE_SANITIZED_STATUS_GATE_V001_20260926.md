# HYDRA Constraint — Batch017 Post-Capture Sanitized Status Gate
## 2026-09-26

Purpose: consume a successful private T1 materialization attestation and emit only a repo-safe successor status.

## Preconditions

- all nine registered source bodies have been materialized into private T1 custody;
- all nine source-version receipts are exact persisted records;
- the persisted release manifest is exact and contains all nine members;
- all nine members are `ELIGIBLE` and ordinary T1→T2 eligible;
- the private attestation has already passed `validate_constraint_t1_first_slice_attestation.py`.

## Command

```powershell
python .\tools\build_constraint_t1_post_capture_public_status.py `
  --attestation "D:\HYDRA\_PRIVATE\constraint\metadata\<validated-attestation>.json" `
  --output ".\docs\constraint\architecture\HYDRA_CONSTRAINT_BATCH017_POST_CAPTURE_PUBLIC_STATUS_V001_20260926.json"
```

## Allowed closure

A valid 9/9 attestation may close:

- `PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION`;
- current captured source-version hash completeness;
- persisted current T1→T2 custody.

## Forbidden promotion

The generated status must still report:

- ordinary historical point-in-time replay: `NO`;
- historical `available_at` before capture: `UNPROVEN`;
- native signed T5→T6 receipt: absent;
- canonical admission: blocked.

The combined blocker `ORDINARY-POINT-IN-TIME-REPLAY-SOURCE-VERSION-HASHES-INCOMPLETE` is not silently deleted. The generated status records its hash component as complete while preserving the historical-as-of component as blocked.

## Public-safety boundary

The output contains only source IDs, source-version IDs, SHA-256 values, byte lengths, content types, acquisition/availability timestamps, release identity/hash, and eligibility states.

It does not contain private paths, raw bytes, HAR files, receipt paths, raw object paths, or source body content.
