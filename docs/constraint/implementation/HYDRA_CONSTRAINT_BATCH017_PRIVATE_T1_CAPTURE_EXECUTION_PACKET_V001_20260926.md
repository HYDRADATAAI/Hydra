# HYDRA Constraint — Batch017 Private T1 Capture Execution Packet
## Exact nine registered first-slice sources — 2026-09-26

Purpose: execute the remaining private source-version materialization dependency without publishing raw third-party source bodies or changing any outcome/evaluation policy.

## Preconditions

- Windows HYDRA workstation with Python 3.11 available as `python`.
- Repository checkout containing PR #64 source/private-record changes.
- Write access to:
  - `D:\HYDRA_PRIVATE\constraint\raw`
  - `D:\HYDRA_PRIVATE\constraint\capture-staging`
  - `D:\HYDRA_PRIVATE\constraint\metadata`
- Operator has reviewed/authorized public acquisition of the nine already-registered source locators.
- Current capture does not prove historical public availability before the acquisition timestamp.

## One-command execution

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\private\Invoke-HYDRAConstraintFirstSlicePrivateCapture_V001_20260926.ps1 `
  -AuthorizedPublicAcquisition
```

Optional path overrides are available, but all private paths must remain outside the public repository.

## What the command does

1. Loads the authoritative Batch003 nine-source registry.
2. Requires exactly nine unique registered source IDs.
3. Uses only each registered HTTPS locator.
4. Downloads each body into a timestamped directory under the private capture-staging root.
5. Validates non-empty capture and expected HTML/PDF content type.
6. Computes SHA-256 locally.
7. Creates unique source-version IDs.
8. Writes a private capture-plan JSON under the private metadata root.
9. Invokes the network-blind T1 first-slice materializer.
10. Persists raw objects, exact source-version receipts, and one exact release manifest in the private T1 raw root.
11. Writes a sanitized materialization attestation in private metadata.
12. Runs the sanitized public-attestation validator.
13. Prints explicit NO claims for historical backdating, ordinary replay promotion, and canonical admission.

## What never enters Git

- raw source bodies;
- private capture-staging paths in a committed artifact;
- private T1 object paths;
- private receipts/releases;
- any source body content.

Only a separately reviewed sanitized attestation may later be committed.

## Temporal rule

This execution uses `AVAILABLE_AT = ACQUIRED_AT`.

It does not infer historical `available_at` from publication date, current reachability, event date, report cover date, or URL metadata.

## Success output

```text
HYDRA_FIRST_SLICE_PRIVATE_CAPTURE=PASS
RAW_BODIES_PUBLISHED_TO_GIT=NO
HISTORICAL_BACKDATING=NO
ORDINARY_REPLAY_PROMOTED=NO
CANONICAL_ADMISSION_PROMOTED=NO
```

## After successful local execution

Do not claim ordinary replay immediately.

1. retain the private raw objects/receipts/release;
2. retain the private capture plan;
3. retain the private sanitized attestation;
4. validate the attestation again with `python .\tools\validate_constraint_t1_first_slice_attestation.py --attestation <private-attestation-path>`;
5. review the attestation for absence of private/raw fields;
6. only then create a successor repo status containing the sanitized hashes/identities;
7. separately satisfy the native signed T5→T6 admission receipt.

Until both lineage and native admission are present, canonical admission remains blocked.
