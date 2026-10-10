# HYDRA Constraint Lily AI infrastructure Pass005

Status: VERTICAL_INTEGRATION_THIN. Mainline replay repair proposed; no runtime admission.

## Why this successor exists

Main at 07e03eeede02e77c3076a75aef274f3f8b424158 now contains its own persisted-custody reconciliation and V002 owner-seam overlay, but still contains the original unconditional-candidate shadow replay. PR85's older owner stack is therefore unnecessary for delivering the replay repair to this mainline parent.

This candidate carries only the tested replay module and its 19 lineage regressions from Pass004, adapts the replay fixture to the current V002 overlay, and adds a current-owner four-window verification command to first-slice CI. The production module is byte-for-byte the tested Pass004 repair. No Pass004 custody pin transition, old V001 owner authority, legacy acceptance shape or physical/policy implementation is imported.

## Exact behavior

Candidates require their knowledge time and visible parent claims. Dependent relief and beneficiary references require available support. Claim references cannot be replaced by evidence IDs. Unknown support and missing candidate time cannot qualify. Independent outcome observations retain their own availability and claim checks. These are normalized shadow availability semantics, not effective-world-state or ordinary source-lineage admission.

The new runner consumes the existing mainline owner validator's exact input paths and validates V002 owner conformance first. It reproduces four windows and checks all five ID sets, dependent leakage and determinism. Its outcomes are scoped to the historical Batch011 fixture, not the expanded Batch016 outcome corpus. The unchanged existing outcome-coverage validator separately checks that newer corpus.

Historical Batch011 snapshots and receipt hashes remain unchanged as predecessor evidence; the updated tests reproduce stored hashes without presenting those old snapshots as the repaired algorithm's output. New window hashes are recorded in the Pass005 verification receipt.

## Validation and preservation

160 T6 tests and 17 T1 tests pass on this mainline parent. Existing first-slice integration, strict acceptance, typed confidence, real outcome coverage and NYX successor checks pass, along with their five hostile matrices. The verification receipt records commands and outputs. Different suite counts from Pass004 reflect the current mainline test inventory, not a claim that branch-local tests were all merged.

Only replay code/tests, the scoped verification runner, CI wiring and new Pass005 reports change. No pre-existing docs, masters, authority bindings, historical manifests, raw bytes or private records change. Production activation, canonical promotion and native signed admission remain unavailable.

## Routing

This is a direct-to-main successor candidate to stacked drafts #61 and #85; those remain historical and unmerged. Physical/policy integration already has a separate owner candidate, inspected at f3ca593, and is not duplicated here. The next review should assess this narrow replay delta against main. Remaining vertical work still belongs to physical/policy integration, private source materialization, native admission and bounded facility/chip/water evidence. Passing this repair does not freeze V1 or admit ordinary replay.
