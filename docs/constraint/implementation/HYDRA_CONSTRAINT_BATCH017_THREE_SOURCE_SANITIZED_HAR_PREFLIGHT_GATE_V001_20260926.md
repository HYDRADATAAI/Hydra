# HYDRA Constraint — Batch017 Three-Source Sanitized HAR Preflight Gate
## LBNL + FERC + PJM — 2026-09-26

Purpose: validate the three exact-response sanitized HAR files before rerunning the complete nine-source private capture.

## Scope

This preflight is read-only with respect to source custody.

It does not:

- write response bodies;
- create a capture plan;
- create T1 raw objects;
- create T1 source-version receipts;
- create a T1 release;
- promote ordinary replay;
- promote canonical admission.

## Required HAR files

- LBNL Queued Up exact registered response;
- FERC Order 2023 fact-sheet exact registered response;
- PJM 2025 Year in Review exact registered response.

Each HAR remains private and outside Git.

## Run

```powershell
python .\tools\private\Test-HYDRAConstraintThreeSourceSanitizedHarPreflight_V001_20260926.py `
  --lbnl-har "D:\HYDRA_PRIVATE\constraint\metadata\lbnl-queued-up-sanitized.har" `
  --ferc-har "D:\HYDRA_PRIVATE\constraint\metadata\ferc-order-2023-sanitized.har" `
  --pjm-har "D:\HYDRA_PRIVATE\constraint\metadata\pjm-2025-year-review-sanitized.har" `
  --summary-output "D:\HYDRA_PRIVATE\constraint\metadata\three-source-har-preflight-summary.json"
```

## Acceptance rules

For every source the preflight requires:

- exact registered request URL;
- HTTP 200;
- `text/html` response MIME;
- response body embedded in the HAR;
- source-specific title/body marker;
- no Cookie, Set-Cookie, Authorization, or Proxy-Authorization header;
- no Cloudflare/block/challenge body;
- HAR path outside the public repository.

## Success semantics

`HYDRA_THREE_SOURCE_HAR_PREFLIGHT=PASS` means only that the three private HARs contain acceptable exact registered response bodies.

It is not T1 materialization and does not make the six earlier staged bodies authoritative.

After PASS, rerun the complete nine-source private capture helper from PR #65 with all three HAR parameters. The complete helper will create a fresh timestamped capture set and only then may form the nine-source capture plan and private T1 release.
