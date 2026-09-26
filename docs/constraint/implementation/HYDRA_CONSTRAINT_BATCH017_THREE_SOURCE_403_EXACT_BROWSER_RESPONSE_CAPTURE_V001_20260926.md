# HYDRA Constraint — Batch017 Three-Source 403 Exact Browser-Response Capture
## LBNL Queued Up + FERC Fact Sheet + PJM Year in Review — 2026-09-26

Scope: controlled exact-response fallback for three registered HTML sources whose direct byte capture can return HTTP 403 while normal browser navigation succeeds.

## Allowed source IDs

- `SRC-LBNL-QUEUED-UP-2025`
- `SRC-FERC-ORDER-2023-FACT-SHEET`
- `SRC-PJM-2025-YEAR-IN-REVIEW-2026-01-08`

No other registered source is eligible for this fallback.

## Exact registered locators and body markers

### LBNL

Locator:
`https://emp.lbl.gov/publications/queued-2025-edition-characteristics`

Required body marker:
`Queued Up: 2025 Edition`

### FERC

Locator:
`https://www.ferc.gov/news-events/news/fact-sheet-improvements-generator-interconnection-procedures-and-agreements`

Required body marker:
`Fact Sheet | Improvements to Generator Interconnection Procedures and Agreements`

### PJM

Locator:
`https://insidelines.pjm.com/2025-year-in-review-planning-prepares-for-burgeoning-electricity-demand/`

Required body marker:
`2025 Year in Review: Planning Prepares for Burgeoning Electricity Demand`

## Shared acceptance contract

The sanitized-HAR extractor accepts a candidate response only when:

- request URL equals the registered locator exactly;
- HTTP status is `200`;
- response MIME starts with `text/html`;
- response body exists in the HAR;
- source-specific title/body marker is present;
- HAR contains no `Cookie`, `Set-Cookie`, `Authorization`, or `Proxy-Authorization` header;
- response body does not contain known Cloudflare block/challenge markers;
- HAR input and extracted response path remain outside public Git.

An alternate page, linked PDF, mirror, cached text extraction, rendered DOM, Elements-panel serialization, or copied browser credentials cannot satisfy the contract.

## Parameters

The private capture helper accepts:

- `-LbnlQueuedUpSanitizedHarPath`
- `-FercOrder2023SanitizedHarPath`
- `-Pjm2025YearInReviewSanitizedHarPath`

Each parameter is private and source-specific. The helper still attempts direct capture first and only invokes the exact-response HAR path after direct capture fails for the corresponding allowlisted source.

## Example

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\private\Invoke-HYDRAConstraintFirstSlicePrivateCapture_V001_20260926.ps1 `
  -AuthorizedPublicAcquisition `
  -LbnlQueuedUpSanitizedHarPath "D:\HYDRA_PRIVATE\constraint\metadata\lbnl-queued-up-sanitized.har" `
  -FercOrder2023SanitizedHarPath "D:\HYDRA_PRIVATE\constraint\metadata\ferc-order-2023-sanitized.har" `
  -Pjm2025YearInReviewSanitizedHarPath "D:\HYDRA_PRIVATE\constraint\metadata\pjm-2025-year-review-sanitized.har"
```

## Current in-app limitation

The Codex in-app browser used in the current chat can display these pages but does not expose a supported HAR/raw-Network-response export surface to the assistant. Therefore this session cannot generate the private HAR files itself.

The actual exact-response capture must be performed in an authorized browser environment that can export a sanitized Network HAR while preserving the exact registered locator.

## Aborted batch semantics

Six direct captures already staged privately remain staging-only.

No capture plan, T1 object, receipt, or release exists yet. Therefore no partial T1 authority exists and nothing is promoted from the six staged bodies.

A subsequent complete run may use fresh direct captures plus the three validated exact-response HAR bodies to form one complete nine-source private capture plan.
