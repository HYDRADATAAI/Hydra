# NYX Task 4 — Repository stale-path / evidence-leak re-audit

Base: `684f59ceea89114f6ac8b356e9b4dfb2b9cafa89`

Disposition: **BOUNDED_REPAIR**

## Deterministic repository drift found

The active Batch030 workstation launcher still defaulted its private paths to the stale sibling tree:

- `D:\HYDRA_PRIVATE\constraint\raw`
- `D:\HYDRA_PRIVATE\constraint\capture_inbox\semiconductor_batch030`
- `D:\HYDRA_PRIVATE\constraint\handback`

Current first-slice path authority and the hardened T1 README use the canonical private tree:

- `D:\HYDRA\_PRIVATE\constraint\raw`
- `D:\HYDRA\_PRIVATE\constraint\...`

The launcher is explicitly excluded from the sealed Batch030 artifact manifest, so correcting its workstation defaults does not rewrite Batch030 domain evidence or successor authority.

Repair:
- update all Batch030 launcher private defaults to the canonical `D:\HYDRA\_PRIVATE\constraint` tree;
- keep repository root derived from `$PSScriptRoot`, with caller override retained;
- extend the existing Batch030 validator to require the canonical launcher defaults and reject the stale sibling root.

## Historical sealed metadata

Batch026 and Batch030 sealed queue/contract artifacts contain older workstation-path literals. They are preserved as immutable historical batch artifacts and are not rewritten by this repair. Operational Batch030 execution receives explicit launcher arguments and now defaults to the canonical private tree.

No historical path literal is treated by this repair as proof of private evidence availability.

## Evidence-leak audit

The post-Task6 delta from `7e5619b3b0d816ed1c7447d16d95069db68b5c2e` through current main contains 28 changed files. Repository inspection found:
- no committed content-addressed T1 raw object path;
- no committed private receipt/release directory;
- no raw source bodies copied into the public repository;
- no private Windows evidence copied or reconstructed;
- Batch030 capture queue remains metadata/locator configuration only;
- materializer/verifier/handback code still requires caller-supplied private roots and does not embed source bodies.

## Authority boundaries

This repair does not:
- execute private capture;
- create or verify missing D-owner evidence;
- alter acquisition timestamps;
- authorize backdating;
- mint canonical constraints or beneficiaries;
- change readiness or production state;
- issue native T5→T6 admission.

`D_OWNER_GATE=BLOCKED` and `NYX_FIRST_SLICE_REPO_WORK=HOLD` remain unchanged where owner-gate evidence is required.
