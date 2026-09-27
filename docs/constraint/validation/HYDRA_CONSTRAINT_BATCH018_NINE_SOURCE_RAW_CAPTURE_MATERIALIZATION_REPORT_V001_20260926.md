# HYDRA Constraint — Batch018 Nine-Source Browser Capture and T1 Materialization

## Result

The exact nine registered first-slice sources were captured through installed Chrome with Playwright and materialized into the canonical private T1 raw store. The offline T1 materializer wrote nine immutable content-addressed objects, nine persisted source-version receipts, and one immutable release. Its attestation reports 9/9 ordinary T1→T2 eligible source versions.

The canonical private root is `D:\HYDRA\_PRIVATE\constraint`; the raw-store child is `D:\HYDRA\_PRIVATE\constraint\raw`. The path authority record corrects the stale `D:\HYDRA_PRIVATE\constraint\raw` spelling in earlier operational documentation. The sibling raw subtree was removed after its eight non-browser objects were verified and excluded; a private metadata-only reconciliation record preserves their identities and hashes. Batch008 and Batch017 historical authority records remain unchanged.

## Capture evidence

Nine of nine registered identities have source URL, publisher/title identity, browser acquisition timestamp, browser method, response status, MIME type, byte size, SHA-256, source-version identity, and a private staging-to-object mapping. Seven were captured in the final browser run. The final run received HTTP 403 for Queued Up and FERC; their selected artifacts are the earlier exact-locator Chrome responses (HTTP 200) retained in the same canonical staging tree. The current failed attempts remain in private capture metadata and were not materialized.

An initial browser pass exposed Chrome's 536-byte inline-PDF viewer wrapper for the DOE and NERC URLs; those wrapper bytes were rejected. The corrected Chrome download preference captured the native PDFs (DOE LPT 1,943,412 bytes; NERC LTRA 7,847,418 bytes) with `%PDF-` signatures. The other seven selected artifacts are the exact registered HTML documents. No related page or file substituted for a registered locator. All nine selected final artifacts returned HTTP 200.

The sanitized [source hash inventory](../first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_HASH_INVENTORY_V001_20260926.json) maps each SHA-256 to a T1 relative object key, version receipt hash, release membership, source URL, acquisition time, and media/size metadata. The sanitized [T1 attestation](HYDRA_CONSTRAINT_BATCH018_T1_NINE_SOURCE_MATERIALIZATION_ATTESTATION_V001_20260926.json) contains no raw bodies or absolute private paths.

## Historical availability and replay boundary

For every source, T1 uses conservative `AVAILABLE_AT = ACQUIRED_AT`. Publication dates, HTTP `Date`, and HTTP `Last-Modified` values are recorded as metadata but are not treated as proof that the exact captured version was available before acquisition. No historical archive/version record proving availability by the intended earlier case cutoffs was obtained. Historical availability is therefore **not established before each acquisition time**.

The exact source-version hash/receipt/release completeness blocker is closed for these nine versions at or after their conservative `available_at` values. Replay from earlier historical cutoffs remains blocked; the full `PIT-002B` target is not closed because its intended-PIT historical availability evidence is still missing. No historical backdating or lookahead replay was performed.

## Target status

- `PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION`: raw capture and T1 custody **PASS**; overall target **OPEN** pending adequate historical-availability evidence for the intended PIT slice.
- `ORDINARY-POINT-IN-TIME-REPLAY-SOURCE-VERSION-HASHES-INCOMPLETE`: **CLOSED for the nine captured source versions' hashes, receipts, release membership, and ordinary T1 eligibility**. This does not claim strict replay for cutoffs before acquisition.
- T5→T6 artifact/hash inventory is prepared for the admission lane. This pass did not issue or self-sign a T5→T6 receipt.
- First serious Constraint run: **BLOCKED**.

## Validation

Validation results:
- focused T1 persistence/replay suite: 45 tests passed; 4 symlink tests skipped because this Windows session does not have directory-symlink privilege;
- sanitized T1 attestation validator: PASS;
- direct persisted release/receipt/object eligibility verification: PASS, 9/9;
- final selected browser artifacts and their T1 object hashes/byte lengths: PASS, 9/9.

The T5→T6 input inventory includes exact source/version IDs, artifact and receipt SHA-256, content type, byte length, `acquired_at`/conservative `available_at`, source URL, browser capture provenance, private object-key mapping, and release ID/hash. It is an input inventory only; no T5→T6 receipt or signature was issued.
