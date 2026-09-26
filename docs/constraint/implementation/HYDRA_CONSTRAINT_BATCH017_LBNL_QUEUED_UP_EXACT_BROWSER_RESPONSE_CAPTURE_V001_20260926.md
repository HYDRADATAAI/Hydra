# HYDRA Constraint — Batch017 LBNL Queued Up Exact Browser-Response Capture
## Cloudflare-safe, no-substitution procedure — 2026-09-26

Registered source:

`SRC-LBNL-QUEUED-UP-2025`

Exact authoritative locator:

`https://emp.lbl.gov/publications/queued-2025-edition-characteristics`

## Why this exception exists

Normal browser navigation to the exact registered locator succeeds, but direct byte capture can return HTTP 403 with a Cloudflare block/challenge page.

This procedure does not bypass the challenge, replay browser cookies through curl/PowerShell, substitute the linked report PDF, or use rendered DOM.

It captures the successful browser Network response body for the exact registered document request.

## Browser capture procedure

Use desktop Chrome or Edge with the exact registered page open normally.

1. Open DevTools (`F12` or `Ctrl+Shift+I`).
2. Open the `Network` panel.
3. Clear the network log.
4. Keep Network recording enabled.
5. Reload the exact registered URL normally in the browser.
6. Confirm the main document request URL is exactly the registered locator.
7. Confirm the main document request status is `200` and its response content type is `text/html`.
8. Open the request's `Response` panel and confirm the received HTML source contains `Queued Up: 2025 Edition`.
9. Export the Network log as a **sanitized HAR**. Do not export a HAR with sensitive data.
10. Save the HAR only under the private HYDRA metadata/staging tree, never inside Git.

Do not use:

- `Copy as cURL`;
- copied Cloudflare cookies or `cf_clearance` tokens;
- linked report PDF or XLSX;
- Elements-panel/rendered DOM HTML;
- a 403/Cloudflare challenge response body.

## Resume the exact-nine-source capture

Run the normal private capture helper with the private sanitized HAR:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\private\Invoke-HYDRAConstraintFirstSlicePrivateCapture_V001_20260926.ps1 `
  -AuthorizedPublicAcquisition `
  -LbnlQueuedUpSanitizedHarPath "D:\HYDRA_PRIVATE\constraint\metadata\queued-up-2025-sanitized.har"
```

The helper still attempts the exact registered locator directly. If direct capture is blocked for this source, it invokes the offline HAR extractor only for `SRC-LBNL-QUEUED-UP-2025`.

## HAR acceptance requirements

The offline extractor requires:

- exact request URL equality with the registered locator;
- HTTP status `200`;
- MIME prefix `text/html`;
- response body present in the HAR;
- expected `Queued Up: 2025 Edition` marker;
- no `Cookie`, `Set-Cookie`, `Authorization`, or proxy-authorization header in the HAR;
- no Cloudflare block/challenge markers;
- HAR and extracted body paths outside public Git.

If multiple exact-URL requests exist in the HAR, the extractor may accept the most recent successful exact response and rejects challenge/block responses.

## Provenance semantics

The extracted body is recorded as:

`SANITIZED_BROWSER_HAR_EXACT_RESPONSE_BODY`

and explicitly marks:

- rendered DOM used: `false`;
- linked file substituted: `false`;
- Cloudflare bypass attempted: `false`.

The resulting response body then enters the same network-blind T1 materializer as every other source.

## Temporal semantics

This exception does not alter time rules.

`AVAILABLE_AT = ACQUIRED_AT`

No historical availability is inferred from the page's December 2025 publication date, current browser reachability, or the HAR request time beyond the actual Hydra acquisition timestamp.

## Aborted-run handling

If a prior batch aborted before capture-plan/T1 persistence, any earlier response files are staging-only and non-authoritative.

Do not manually promote them. A rerun creates a fresh timestamped capture directory and a complete nine-source plan.
