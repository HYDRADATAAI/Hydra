# HYDRA Constraint Batch017 Automated Browser Private Source Capture

## Purpose

This is the successor execution path for the first-slice private source-acquisition blocker on PR #65.

It does not replace T1 custody, persisted receipt/release identity, the exact-nine-source registry, the sanitized attestation validator, or replay-lineage semantics. It replaces the normal manual HAR acquisition step with a browser-backed acquisition runner.

## Normal Windows workflow

The canonical normal workflow is Python-only:

```powershell
python .\tools\private\HYDRA_CONSTRAINT_T1_WINDOWS_PYTHON_BROWSER_CAPTURE_BOOTSTRAP_V001_20260926.py --authorized-public-acquisition
```

The Python bootstrap is anchored to its own repository path, rejects audit/snapshot clones, enables Git long-path support, fast-forwards the canonical capture branch, creates or reuses the private Playwright virtual environment under `D:\HYDRA\_PRIVATE\constraint\browser-runtime`, installs only the Python Playwright client when absent, and invokes the authoritative browser runner.

The PowerShell launcher remains available for compatibility, but it is not required for the normal workflow.

The browser is headed by default. A dedicated browser profile is stored only under the private root. The runner does not export or replay browser credentials or session material.

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


## Failure recovery

The Python browser runner writes a private, non-authoritative capture journal after every accepted source under the private metadata root. The journal records exact source identity, locator, acquisition time, HTTP status, content type, byte length, SHA-256, browser channel, redirect chain, and private staged-body path. It is not a T1 release.

If the controlled browser/context is closed while a source is in progress, the runner may relaunch the installed Chrome/Edge session and retry that same registered source up to two times by default. This does not bypass a challenge or substitute a source.

The journal is marked `t1_release_written=true` only after all nine sources complete and the existing materializer, sanitized attestation validator, deterministic replay-lineage builder, post-capture sanitized status builder, and final post-output validation all pass.


## Resume behavior

Unless `--fresh` is supplied, the Python runner automatically looks for the latest incomplete automated-browser capture journal in the private metadata root. Every candidate journal remains non-authoritative and is revalidated before reuse.

Resume accepts only a journal whose entries are an exact prefix of the authoritative nine-source order. For every reused source the runner revalidates exact source ID and registered URL, HTTP 200 metadata, content type, redirect chain, source-version identity, timezone-aware acquisition timestamp, byte length, staged-body existence, SHA-256, and HTML/PDF body rules.

A tampered body, locator drift, identity drift, duplicate or out-of-order journal entry, missing staged body, or completed release fails closed. A resumed run reuses a previously established release identity so downstream materialization retries remain idempotent.


## Concurrent-run protection

The browser capture runner acquires an operating-system lock under the private root before selecting or creating a journal, opening the browser profile, or writing capture state. A second process targeting the same private root fails closed instead of sharing the browser profile or capture journal.

The lock is held by the operating system for the process lifetime. The lock file may remain on disk after a crash, but an abandoned file does not itself block future runs because ownership is determined by the active OS lock, not by file existence.
