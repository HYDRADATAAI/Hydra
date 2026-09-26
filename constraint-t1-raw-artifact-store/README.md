# HYDRA Constraint T1 Private Raw Artifact Store

Status: SOURCE-ONLY IMPLEMENTATION SUPPORT — NO LIVE ACQUISITION

This package implements the Thread-1 raw-artifact persistence boundary required
before ordinary T1-to-T2 evidence normalization.

It deliberately performs no network access. A caller supplies bytes already
captured through an authorized or reviewed acquisition path.

## Safety and public-repo boundary

Raw source bytes must live in a private HYDRA data root outside the public Git
repository. The store rejects a private root nested inside the public repo and
resolves every object, receipt, and release path before use so descendant
symlinks cannot redirect private storage into the public repository or outside
the configured private root.

The public repository contains only persistence code, schemas/contracts,
synthetic tests, and status/manifests. It does not publish third-party source
bodies.

## Guarantees

- SHA-256 content-addressed raw objects.
- Atomic immutable writes.
- Immutable per-source-version receipts, with eligibility bound to the exact persisted receipt record.
- Explicit source_id versus source_version_id.
- acquired_at and available_at retained separately.
- Deterministic immutable T1 release manifests.
- Ordinary T1-to-T2 eligibility requires the exact persisted release manifest; a valid in-memory lookalike is insufficient.
- Quarantine and ineligible dispositions fail closed.
- No URL fetching or live-source authority.

## Local use

Set PYTHONPATH to the package src directory, then run:

python -m hydra_constraint_t1_raw.cli --private-root D:\HYDRA_PRIVATE\constraint\raw --public-repo-root C:\HYDRA --input-file C:\captures\source.bin --source-id SRC-EXAMPLE --source-version-id SV-EXAMPLE-001 --content-type application/octet-stream --source-locator reviewed-manual-capture --acquired-at 2026-09-25T23:52:01.573251Z --available-at 2026-09-25T23:52:01.573251Z

The command persists only the supplied local file. It does not acquire remote content.

## Complete first-slice materialization

For the AI/data-center power first slice, use the reviewed nine-source capture-plan
template in:

`docs/constraint/implementation/HYDRA_CONSTRAINT_AI_DATA_CENTER_POWER_INFRASTRUCTURE_PRIVATE_T1_CAPTURE_PLAN_TEMPLATE_V001_20260926.json`

Capture the source bytes through an authorized/reviewed path into a private staging
directory outside Git, replace every template placeholder with the exact local
capture path, a unique source-version ID, and the actual acquisition timestamp,
then run:

```bash
hydra-constraint-t1-first-slice \
  --registry docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json \
  --capture-plan C:\\HYDRA_PRIVATE\\constraint\\capture-plan.json \
  --private-root D:\\HYDRA_PRIVATE\\constraint\\raw \
  --public-repo-root C:\\HYDRA \
  --attestation-output D:\\HYDRA_PRIVATE\\constraint\\first-slice-materialization-attestation.json
```

The batch materializer is network-blind. It requires the capture set to match the
source registry exactly, rejects source-locator substitution, rejects raw input
files located inside the public repository, writes exact persisted receipts and
one exact persisted release manifest, and verifies ordinary T1→T2 eligibility
against those persisted records.

This first materialization mode is intentionally conservative:
`AVAILABLE_AT = ACQUIRED_AT`. It does not backdate current bytes to a publication
date and does not promote strict historical replay. Historical availability
requires a separate provenance-bearing proof.
