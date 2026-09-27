# NYX Task 6 — stacked temporal regression closeout

Base: refreshed PR96 `794dcdc87f60bdfc4c67d72fec6ec771d0c46669` on PR64 `6b693c788319afbc489ab0a644ecbddaa1afdb94`, PR62 `5a88a51f8c9bd7649a8c799d0c5b2225330a29d8`, main `3cafc16f6a42a2eeeefa74f66a223ca8594374a9`.

Integrated existing repairs `28747d8a35e56dd0c4e44129f832819bb14ca139` (Task5) and `3f29ab75fcad4c0b29bf83c0267872ba7608ff6f` (Task4). No merge to main or existing PR branch is performed by this closeout.

## Proven defects closed

- Task5's custody map adds independent T6 transitions; PR96's private T1 map incorrectly required its count to equal the entire shared map. The validator now compares the exact T1 subset, preserving count, uniqueness, predecessor and current-successor checks. No T6 transition is removed.
- First-slice capture normalization dropped explicit `acquisition_verification_status=TIMESTAMP_UNVERIFIED`. Attestation validation and replay construction accepted this caveat and additional canonical/production fields. Four new regression methods produced 15 failing assertions/subcases before repair. They now pass: unsupported fields are rejected at the capture, attestation and replay-packet boundaries, including a recomputed packet digest attack.
- The conservative temporal overlay still ignored additional status/authority fields after the Task5 direct-call repair. One new regression method produced four failing subcases. Unknown record fields now fail validation; input status remains unchanged.
- README path examples combine PR96's canonical private tree with Task4's removal of C-drive examples. The corrected README-successor relationship is retained with exact updated pins and the original/intermediate predecessor assertions. The capture-plan template now asks for an authorized private capture path rather than suggesting a C-drive staging directory; no files were captured or relocated.
- Only new preparation/capture manifest pins and explicit successor-map entries affected by these changes were updated. The preexisting historical T1 README intermediate remains `5958840f95811a147758913bce8e42419ed55750`.

## Temporal and authority boundaries

`SRC-EATON-Q1-2026-RESULTS-2026-05-05` and `SRC-GEV-Q2-2026-RESULTS-2026-07-22` both retain the stored acquisition literal `2026-09-26T13:11:19Z`; their independent verification classification remains **TIMESTAMP_UNVERIFIED**. The repository source/outcome records do not encode that review classification. Neither record was changed or certified. Equality of acquisition and availability, publication dates, Git times, and hashes are not independent acquisition evidence.

The accepted public Batch018 attestation remains a metadata validation input; this closeout did not verify private raw bytes, create captures, issue admission receipts, activate production, or promote canonical/readiness authority. D-owner gate remains blocked pending inaccessible Windows evidence.

## Validation

- Combined five-owner pytest run: **339 tests, 469 subtests PASS**.
- Refreshed PR96 before integration: **328 tests, 432 subtests PASS**.
- All 40 repository workflow validator/hostile commands passed in the integrated working tree; affected first-slice/successor guards rerun after final T6 edits.
- Metadata boundary regressions: **4 methods PASS** after 15 pre-repair failures.
- Conservative overlay suite: **11 tests PASS**; status-smuggling method had four pre-repair failures.
- README successor binding: **2 methods PASS**, including hostile map mutations.
- Sanitized nine-source attestation validation PASS without private bytes.
- PR97's Batch016 source and outcome files exactly match main.
- Policy, physical dependency, replay, public repository validation and root hygiene PASS. No root transfer artifacts.
- PowerShell-only execution/AST steps are not available in this runtime; no local Windows verification claimed.
