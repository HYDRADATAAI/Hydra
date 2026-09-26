# HYDRA Constraint T1 Private Raw Artifact Store

Status: SOURCE-ONLY IMPLEMENTATION SUPPORT — NO LIVE ACQUISITION

This package implements the Thread-1 raw-artifact persistence boundary required
before ordinary T1-to-T2 evidence normalization.

It deliberately performs no network access. A caller supplies bytes already
captured through an authorized or reviewed acquisition path.

## Safety and public-repo boundary

Raw source bytes must live in a private HYDRA data root outside the public Git
repository. The store rejects a private root nested inside the public repo and
re-checks every artifact, receipt, and release destination after symlink
resolution so descendant links cannot redirect private writes into the public
repository or outside the configured private root.

The public repository contains only persistence code, schemas/contracts,
synthetic tests, and status/manifests. It does not publish third-party source
bodies.

## Guarantees

- SHA-256 content-addressed raw objects.
- Atomic immutable writes.
- Immutable per-source-version receipts.
- Explicit source_id versus source_version_id.
- acquired_at and available_at retained separately.
- Deterministic T1 release manifests.
- Release membership required for ordinary T1-to-T2 eligibility.
- Quarantine and ineligible dispositions fail closed.
- No URL fetching or live-source authority.

## Local use

Set PYTHONPATH to the package src directory, then run:

python -m hydra_constraint_t1_raw.cli --private-root D:\HYDRA_PRIVATE\constraint\raw --public-repo-root C:\HYDRA --input-file C:\captures\source.bin --source-id SRC-EXAMPLE --source-version-id SV-EXAMPLE-001 --content-type application/octet-stream --source-locator reviewed-manual-capture --acquired-at 2026-09-25T23:52:01.573251Z --available-at 2026-09-25T23:52:01.573251Z

The command persists only the supplied local file. It does not acquire remote content.
