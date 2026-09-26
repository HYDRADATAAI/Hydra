# HYDRA Constraint Batch017 Automated Browser Private Source Capture

## Purpose

This is the successor execution path for the first-slice private source-acquisition blocker on PR #65.

It does not replace T1 custody, persisted receipt/release identity, the exact-nine-source registry, the sanitized attestation validator, or replay-lineage semantics. It replaces the normal manual HAR acquisition step with a browser-backed acquisition runner.

## Normal Windows workflow

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\private\Invoke-HYDRAConstraintFirstSliceAutomatedBrowserCapture_V001_20260926.ps1 -AuthorizedPublicAcquisition
```

The launcher creates a Python virtual environment only under `D:\HYDRA\_PRIVATE\constraint\browser-runtime`, installs the Python Playwright client there when absent, and uses an already-installed Chrome or Edge browser. It does not download a Playwright browser build.

The browser is headed by default. A dedicated persistent browser profile is stored under the private root. Normal site cookies/session state in that dedicated profile may therefore persist across runs. The runner never exports browser cookies or credentials.

If a site presents a normal visible challenge, the browser may be used normally by the operator. The runner performs no CAPTCHA solving, stealth changes, anti-bot bypass, cookie theft, credential replay, DOM substitution, or mirror substitution.

## Exact-source rules

For every registered source the runner requires:

- the source ID and URL to come directly from the authoritative nine-source registry;
- nine unique source IDs and nine unique registered locators;
- HTTPS;
- HTTP 200;
- the accepted main-document response URL to equal the exact registered locator;
- no redirect chain on the accepted response;
- the expected MIME family;
- a non-empty and non-suspicious body;
- PDF signature checks for direct PDF sources;
- block/challenge/interstitial rejection for HTML;
- source-specific body markers for the three previously blocked HTML sources.

The response body, capture manifest, generated capture plan, sanitized attestation, and replay-lineage packet are written only under `D:\HYDRA\_PRIVATE\constraint`.

## Existing authority reused

After all nine browser captures succeed, the runner generates the existing local capture-plan schema and invokes, in order:

1. `hydra_constraint_t1_raw.first_slice_cli`;
2. `tools/validate_constraint_t1_first_slice_attestation.py`;
3. `tools/build_constraint_t1_first_slice_replay_lineage.py`;
4. `tools/build_constraint_t1_post_capture_public_status.py`.

The materializer remains network-blind. `AVAILABLE_AT=ACQUIRED_AT` remains mandatory. No historical availability is inferred or backdated.

## Success posture

A successful local execution prints:

```text
SOURCE_CAPTURE=9/9
PRIVATE_MATERIALIZATION=PASS
ATTESTATION=PASS
SOURCE_VERSION_HASH_LINEAGE=PASS
REPLAY_LINEAGE=PASS
POST_CAPTURE_SANITIZED_STATUS=PASS
STRICT_HISTORICAL_REPLAY=BLOCKED
NATIVE_T5_T6_ADMISSION=BLOCKED
RAW_SOURCE_PUBLICATION=NO
```

No successful source-capture result is claimed by repository CI because CI does not possess the private Windows browser/profile or private source bodies.
