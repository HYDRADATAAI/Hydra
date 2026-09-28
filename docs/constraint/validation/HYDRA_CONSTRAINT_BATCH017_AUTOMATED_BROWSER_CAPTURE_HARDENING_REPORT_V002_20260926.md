# HYDRA Constraint — Batch017 Automated Browser Capture Hardening
## V002 — 2026-09-26

Scope: canonical private browser-backed source acquisition for the exact nine registered first-slice sources.

## Defects closed in this hardening pass

1. Corrected the automated browser private root from the accidental `D:\HYDRA\_PRIVATE\constraint` spelling to the existing `D:\HYDRA_PRIVATE\constraint` root.
2. Added explicit operator authorization at both the PowerShell launcher and direct Python-runner layers.
3. Added the automated launcher/runner/requirements files to T1 workflow path triggers.
4. Extended PowerShell syntax validation to both the legacy/private capture launcher and the automated browser launcher.
5. Wired the post-capture sanitized-status builder into the automated runner so implementation matches the documented four-stage post-capture flow.
6. Added post-output validation that confirms raw materialization closes only after 9/9 eligible sources while historical replay/native admission/canonical promotion remain blocked.
7. Added launcher-level regression tests for authorization, installed-browser-only operation, exact main-document response requirements, private-root correctness, and post-capture status invocation.
8. Replaced the earlier custody-only supersession interpretation with a V002 map that keeps the T1 store network-blind while allowing explicitly authorized operator browser acquisition.

## Automated browser boundary

The runner uses installed Chrome or Edge through the Python Playwright client.

It does not install a Playwright browser build. The launcher may bootstrap only the Python Playwright package into the private runtime.

The acquisition runner requires:

- the authoritative nine-source registry;
- explicit operator authorization;
- installed Chrome or Edge;
- exact registered main-document response URL;
- no accepted redirect chain;
- HTTP 200;
- expected MIME family;
- non-empty/non-suspicious body;
- PDF signature for registered PDFs;
- challenge/interstitial rejection for HTML;
- source-specific body markers for the previously blocked LBNL/FERC/PJM pages.

The browser may display a normal site challenge for operator interaction, but the runner performs no CAPTCHA solving, stealth modification, credential export/replay, source substitution, DOM substitution, or mirror substitution.

## T1 boundary

Browser acquisition is not implemented inside `RawArtifactStore`.

After all nine browser responses are accepted, the runner calls the existing network-blind T1 materializer, then:

1. sanitized attestation validation;
2. deterministic replay-lineage construction;
3. post-capture sanitized-status construction.

`AVAILABLE_AT = ACQUIRED_AT` remains mandatory.

## Output posture

A successful private run may establish:

- exact current source-version bytes/hashes;
- persisted T1 receipts and release membership;
- 9/9 ordinary current T1→T2 eligibility;
- source-version hash lineage for the captured versions;
- sanitized post-capture raw-materialization closure.

It does not establish historical availability before acquisition, ordinary historical replay, native signed T5→T6 admission, canonical constraint admission, or beneficiary qualification.

## Execution state

Repository CI does not execute the real browser capture because it does not possess the user's private Windows browser/profile/source bodies.

Actual private capture remains `NOT_EXECUTED_BY_REPOSITORY_CI`.
