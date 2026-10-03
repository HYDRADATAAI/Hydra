# HYDRA Constraint — T1 Private Raw Store Path Authority

## Canonical path

The one canonical private tree is `D:\HYDRA\_PRIVATE\constraint`. Its T1 raw store is `D:\HYDRA\_PRIVATE\constraint\raw`. The browser runtime, browser profile, capture staging, and private metadata are siblings under that same tree.

The identity `HYDRA_CONSTRAINT_T1_RAW_STORE_V1` maps to the `raw` child above. T1 objects are addressed by content hash using the repository store's relative key rule:

`objects/sha256/<first-two-hex>/<next-two-hex>/<sha256>.raw`

The absolute workstation path stays in this authority record and operational runbooks. Sanitized attestations and public hash inventories use the store identity and relative object key; they do not publish raw bodies or private staging paths.

## Reconciliation

Repository authority requires a private root outside public Git. The existing browser runtime, capture journal, browser profile, and staged browser bodies are all under `D:\HYDRA\_PRIVATE\constraint`; Batch008's raw-persistence contract remains unchanged. The source-discovery audit and report from Batch017 are preserved as historical evidence and are not rewritten.

`D:\HYDRA_PRIVATE\constraint\raw` is a stale spelling and is not an alias. Its prior direct-download contents were excluded, their hashes were recorded in private reconciliation metadata, and that sibling `raw` subtree was removed after canonical nine-source materialization. The Batch017 operational README/runbook path references have been corrected to this canonical tree. The stale Batch017 evidence records remain unchanged; this record supersedes their path field for current operations.

## Scope of authority

This record selects storage location only. It does not grant source authority, historical availability, strict point-in-time eligibility, native T5→T6 admission, or Constraint promotion. Current raw receipts and release manifests remain the evidence for exact stored source versions.
