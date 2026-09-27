# NYX Task 4 — Repository Stale-Path / Evidence-Leak Audit

Base: `3cafc16f6a42a2eeeefa74f66a223ca8594374a9`

Disposition: **BOUNDED_REPAIR**

## Deterministic repository defect

The active Batch027 PowerShell launcher hard-coded:

`D:\HYDRA_GITHUB\Hydra`

as its default public repository root. A later browser launcher already resolves the repository from its own script location, so the fixed workstation root is unnecessary and stale.

Repair:
- remove the fixed `RepoRoot` default;
- derive the repository root from `$PSScriptRoot` when the caller does not supply `-RepoRoot`;
- retain explicit caller override support;
- add validator and hostile regression coverage prohibiting a fixed workstation root.

Historical Batch027 contract artifacts are not rewritten. The operational launcher is explicitly excluded from the sealed Batch027 artifact manifest and may evolve independently.

## Evidence-leak audit

Repository tree inspection found no committed T1 content-addressed raw object paths, persisted receipt directories, or persisted release directories. Public Constraint artifacts continue to report raw-source publication as false where applicable.

Second-slice capture queue/inbox metadata remains repository-visible configuration only; this audit does not treat source locators or capture requirements as raw evidence.

No private Windows files, raw source bodies, private receipts, or local filesystem state were accessed or copied.

## Other requested checks

- obsolete `D:\HYDRA\_GITHUB\Hydra` / fixed workstation-root assumptions: one active launcher defect repaired as above;
- capture-inbox references: current Batch026 operational references remain scoped to the semiconductor private capture workflow and are not proven stale;
- private raw-store paths: no change made without a repository-authoritative reason;
- stale hashes/successor maps: no immutable historical artifact rewritten; existing successor validation remains authoritative;
- duplicate/superseded artifacts: no deterministic active-authority collision found that justified deleting history;
- nonexistent private evidence: no inaccessible evidence is represented by this repair as newly available.

No canonical, readiness, production, replay, admission, or acquisition authority is changed.
