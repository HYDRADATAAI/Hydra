# HYDRA Constraint — Batch017 Windows Workstation From-Anywhere Capture Bootstrap
## Version 001 — 2026-09-26

Purpose: eliminate repo-path and branch-selection mistakes before launching the canonical private installed-browser capture.

## Canonical local repository

`D:\HYDRA_GITHUB\Hydra`

This is the root-level `HYDRA_GITHUB` directory on drive `D:`. It is not `D:\HYDRA\_GITHUB\Hydra`.

## What the bootstrap validates

- repository directory exists;
- `.git` metadata exists;
- Git top-level path equals the configured repository root;
- configured remote resolves to `HYDRADATAAI/Hydra`;
- tracked working tree is clean;
- canonical capture branch exists remotely;
- branch update is fetch + fast-forward only;
- current branch after checkout is exactly `constraint/t1-private-capture-execution-packet-20260926`;
- canonical installed-browser capture launcher exists.

The bootstrap does not stash, hard reset, force-update the local capture branch, create a capture plan, write T1 records, or create a release.

## From-anywhere command

Once this bootstrap PR is present locally, the operator can run it from any PowerShell working directory by using its full path:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\HYDRA_GITHUB\Hydra\tools\private\Start-HYDRAConstraintFirstSliceCaptureFromAnywhere_V001_20260926.ps1"
```

The bootstrap validates the correct clone, fetches the canonical capture branch, checks it out or tracks it if absent locally, fast-forwards it, and then invokes:

`Invoke-HYDRAConstraintFirstSliceAutomatedBrowserCapture_V001_20260926.ps1 -AuthorizedPublicAcquisition`

## Failure posture

The bootstrap fails closed on:

- wrong/nonexistent repo path;
- accidental `C:\Users\Selene` repository context;
- missing/incorrect remote;
- tracked local changes;
- missing canonical branch;
- non-fast-forward update requirement;
- missing capture launcher;
- capture-runner failure.

Untracked files do not by themselves block checkout because they are not altered by the bootstrap; Git still protects conflicting paths during checkout.

## Authority posture

The bootstrap is workstation orchestration only.

It does not create source authority. T1 authority remains created only by the existing private materializer after a complete 9/9 exact-source capture succeeds.

The bootstrap status is not evidence that the private capture completed. Runtime completion must come from the private capture journal, materializer receipts, sanitized attestation, replay-lineage result, and sanitized post-capture status.
