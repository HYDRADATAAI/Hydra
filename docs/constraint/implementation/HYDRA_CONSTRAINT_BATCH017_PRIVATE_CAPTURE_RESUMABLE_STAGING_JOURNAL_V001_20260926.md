# HYDRA Constraint — Batch017 Private Capture Resumable Staging Journal
## Version 001 — 2026-09-26

Purpose: preserve exact metadata for successful private staging captures when a nine-source run aborts before T1 materialization.

## Authority boundary

The journal is explicitly non-authoritative.

It is not:

- a T1 raw object;
- a T1 source-version receipt;
- a T1 release manifest;
- a capture-plan admission record;
- proof of ordinary replay;
- proof of canonical admission.

No partial T1 authority is created from a journal.

## Journal contents

After each successful exact-source capture, the helper records privately:

- source ID;
- exact registered source locator;
- source-version ID;
- private staged file path;
- content type;
- exact Hydra acquisition timestamp;
- SHA-256;
- byte length;
- capture method;
- processing disposition.

The journal remains under `D:\HYDRA_PRIVATE\constraint\metadata` and outside Git.

## Resume validation

A later run may use `-ResumeJournalPath <private-journal-path>`.

Before reusing any staged body, the helper rechecks:

- journal schema and slice identity;
- journal remains non-authoritative;
- no completed T1 release is recorded;
- source ID equals the current authoritative registry source ID;
- source locator equals the current authoritative registry URL;
- expected content type matches;
- staged file still exists outside the public repository;
- staged byte length matches the journal;
- staged SHA-256 matches the journal;
- disposition remains `ELIGIBLE`;
- original source-version ID and original `acquired_at` are preserved.

If any check fails, reuse is rejected.

## T1 boundary

The helper still requires all nine capture entries before writing the complete capture plan or invoking the T1 materializer.

Journal state transitions are informational only:

- `capture_plan_written` remains false until all nine captures exist;
- `t1_materialization_started` remains false until the complete plan is handed to T1;
- `t1_release_written` becomes true only after materialization and sanitized attestation validation succeed.

## Current six staged files

The six bodies staged by the earlier aborted run predate this journal implementation.

They must remain non-authoritative staging files and **must not be retroactively adopted** using filesystem creation/modification timestamps or newly invented source-version IDs.

A fresh run with the new journal-enabled helper is required to create resumable metadata prospectively.

## Example resume command

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\private\Invoke-HYDRAConstraintFirstSlicePrivateCapture_V001_20260926.ps1 `
  -AuthorizedPublicAcquisition `
  -ResumeJournalPath "D:\HYDRA_PRIVATE\constraint\metadata\HYDRA_CONSTRAINT_FIRST_SLICE_PRIVATE_CAPTURE_JOURNAL_<run>.json" `
  -LbnlQueuedUpSanitizedHarPath "D:\HYDRA_PRIVATE\constraint\metadata\lbnl-queued-up-sanitized.har" `
  -FercOrder2023SanitizedHarPath "D:\HYDRA_PRIVATE\constraint\metadata\ferc-order-2023-sanitized.har" `
  -Pjm2025YearInReviewSanitizedHarPath "D:\HYDRA_PRIVATE\constraint\metadata\pjm-2025-year-review-sanitized.har"
```
