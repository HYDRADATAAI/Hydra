# HYDRA Constraint semiconductor Pass009 — registry-selectable capture

Extends the existing capture-owner runner on top of Pass008. The optional `--semiconductor-registry` selects the semiconductor slice, requires exactly 20 distinct sources and explicit HTML/PDF declarations, and retains exact-source, private-storage, response-integrity and resume checks. Default invocation remains the nine-source power workflow.

The committed capture registry is a pinned execution projection of Batch018, Batch019 and supplementary Pass004. Input paths and hashes are recorded. It does not replace population authority or include later Thread6 source additions. MIME declarations are expected-format requirements, not claims of observed responses.

Semiconductor output names use `SEMICONDUCTOR_PASS009`; resume selection checks the slice. After successful browser capture, the runner reuses the existing T1 materializer and public-attestation validator. It stops before power-specific replay and post-capture builders. T2 normalization, canonical identity resolution, semiconductor receipt intake and runtime admission remain separate gates.

## Workstation execution after this branch is available

From the verified HYDRA checkout, run the existing Python runner with these arguments:

```
python tools/private/HYDRA_CONSTRAINT_T1_AUTOMATED_BROWSER_FIRST_SLICE_CAPTURE_V001_20260926.py --semiconductor-registry docs/constraint/implementation/HYDRA_CONSTRAINT_SEMICONDUCTOR_PASS009_CAPTURE_REGISTRY_20260926.json --private-root D:\HYDRA_PRIVATE\constraint_semiconductor --preflight
```

Preflight reads inputs and validates paths without opening a browser or writing capture data. To perform actual capture, replace `--preflight` with `--authorized-public-acquisition`. Playwright and an installed Chrome/Edge browser must already be available in that Python environment. This pass does not modify the workstation bootstrap. The registry path is resolved from the working directory, so run the command from the checkout root.

A site that redirects, presents a challenge, denies access or returns a different document type remains blocked; do not weaken acceptance checks to manufacture completion. Re-run the same capture command to resume a matching incomplete journal.

## Verification

118 tests ran successfully, one environment-dependent test skipped. The new orchestration integration test supplies 20 synthetic browser bodies, executes the real materializer and attestation validator, verifies 20 persisted receipts and one release, and verifies that no replay output is claimed. Wrong slice/count inputs are rejected. The committed 20-source profile passed read-only preflight.

Actual browser/site capture in this pass: not run. Real source bytes captured: zero. Runtime admission: blocked. The synthetic test proves orchestration and storage integration, not production-site compatibility or documentary authenticity.
