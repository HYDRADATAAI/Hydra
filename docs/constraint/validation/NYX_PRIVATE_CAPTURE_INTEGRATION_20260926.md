# Private capture integration

This branch combines PR #74 (including #70 and #71), #73 preflight, and #66 post-capture status. It is a review branch, not a claim that real source capture has occurred. Existing source artifacts and manifests are preserved.

## Validation

- 78 Python raw-store, HAR preflight, and post-capture tests pass.
- Windows CI exercises synthetic response rejection, exact byte preservation, nine-source materialization, and the post-capture status CLI.
- Synthetic status output is temporary and removed by the test.
- Historical replay, native signed admission, and canonical admission remain blocked.

## Windows operator sequence

Use this branch in a separate checkout. Python must be on PATH. Keep all raw bodies, HAR files, and private receipts outside the public repository.

1. Run the read-only HAR preflight with the three authorized sanitized HARs. Its default paths are documented in the existing wrapper:
   `powershell.exe -NoProfile -File .\tools\private\Test-HYDRAConstraintThreeSourceSanitizedHarPreflight_V001_20260926.ps1`
2. Only after successful preflight, invoke capture with the same three HAR files:

```powershell
powershell.exe -NoProfile -File .\tools\private\Invoke-HYDRAConstraintFirstSlicePrivateCapture_V001_20260926.ps1 -AuthorizedPublicAcquisition -LbnlQueuedUpSanitizedHarPath "D:\HYDRA_PRIVATE\constraint\metadata\lbnl-queued-up-sanitized.har" -FercOrder2023SanitizedHarPath "D:\HYDRA_PRIVATE\constraint\metadata\ferc-order-2023-sanitized.har" -Pjm2025YearInReviewSanitizedHarPath "D:\HYDRA_PRIVATE\constraint\metadata\pjm-2025-year-review-sanitized.har"
```

3. Use the exact PRIVATE_ATTESTATION path printed by that successful run with:
   `python .\tools\build_constraint_t1_post_capture_public_status.py --attestation "<exact PRIVATE_ATTESTATION path>" --output "D:\HYDRA_PRIVATE\constraint\metadata\post-capture-public-status.json"`
4. Review that sanitized status before publishing it. Do not publish the capture plan, HARs, raw bodies, or private receipts.

A missing HAR or failed acquisition is a blocker, not permission to substitute a source or manufacture an outcome. A valid capture attestation supports current custody and source-version hashes; it does not establish historical availability or signed T5/T6 authority.

## Manifest reconciliation

The report's introducing commit, de10beb, already stores blob 881c82941acf129e5fa2060f6d828afbbee98544. The V001 Batch017 manifest recorded a different hash. V002 corrects that pin against the introducing commit, preserves V001, and changes no report or outcome bytes.

The V002 private-record supersession map retains all four existing transitions and adds the exact Batch008 workflow-to-Windows-CI transition. Its predecessor map remains unchanged. The first-slice validator now selects this explicit revision.

Both formerly failing validators pass locally with these revisions. This is manifest repair only; external admission and capture blockers are unchanged.
