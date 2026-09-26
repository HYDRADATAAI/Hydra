# HYDRA Constraint — Lily Raw-Lineage Pre-Materialization Closure
## AI/Data-Center Power First Slice — 2026-09-26

PR: #56
Branch: `constraint/lily-owner-seam-reconciliation-v1-20260926`

## Defect found and repaired

Batch 14 reported persisted T1→T2 chain-of-custody as READY and cited `constraint-t1-raw-artifact-store@0.2.0`, but the stacked implementation initially still carried the earlier `0.1.0` store behavior. The old `is_ordinary_t2_eligible()` accepted caller-supplied receipt/release objects after structural/digest validation and did not prove they were the exact persisted records.

This pass integrated the previously authored Batch-11 custody hardening from PR #48 into the current stack without rewriting historical artifacts.

Current T1 custody now requires:

- exact persisted raw artifact bytes and SHA-256;
- exact persisted source-version receipt identity;
- exact persisted release-manifest identity;
- exact release membership;
- `ELIGIBLE` processing disposition;
- a private root outside the public repository;
- symlink-resolved containment inside the private root and outside public Git.

Self-consistent in-memory receipt/release reconstructions are not authority.

## Nine-source materialization tooling

Added an offline, network-blind first-slice materializer. It consumes the authoritative nine-source registry plus a local capture plan and:

- requires the capture source set to equal the registry exactly;
- rejects missing, extra, or duplicate sources;
- requires each source locator to exactly match the registry URL;
- rejects raw input files inside the public repository;
- writes bytes only through the private immutable T1 store;
- writes persisted receipts and one persisted release manifest;
- verifies ordinary T1→T2 eligibility against those persisted records;
- permits quarantine/ineligible materialization without pretending those members are ordinary eligible.

## Temporal rule

The first materialization mode is intentionally conservative:

`AVAILABLE_AT = ACQUIRED_AT`

A caller cannot provide `available_at`. The materializer will not backdate current captured bytes to publication time or any earlier date. This means a successful private capture can establish present/current ordinary lineage without fabricating strict historical replay availability.

## Public sanitized proof

The materializer emits a sanitized attestation containing source/version identities, artifact/receipt hashes, byte lengths, acquisition/availability timestamps, release identity/hash, and ordinary-T2 eligibility state.

The public attestation validator rejects:

- private paths or raw-byte fields;
- source-set drift;
- duplicate source IDs;
- invalid artifact/receipt hashes;
- conservative availability that differs from acquisition time;
- eligibility/disposition contradictions;
- release-hash mismatch;
- historical replay/backdating claims.

Raw source bodies are not required for public validation of the sanitized proof.

## Endpoint audit

All nine registered public endpoints were reachable during the 2026-09-26 audit. Observed endpoint types were seven HTML endpoints and two PDF endpoints.

This is reachability only. It is not T1 acquisition, source-version custody, or historical-availability proof.

## Validation

Raw-store/materialization CI after reconciliation:

- 30 tests — PASS;
- exact persisted receipt/release authority — PASS;
- complete exact-set synthetic materialization — PASS;
- source substitution rejection — PASS;
- raw-public-path rejection — PASS;
- conservative anti-backdating — PASS;
- quarantine handling — PASS;
- sanitized public-attestation validation — PASS;
- private-path leakage rejection — PASS;
- attestation digest tamper rejection — PASS.

Cross-system validation on the same code-bearing stack:

- Constraint first-slice integration — PASS;
- T6 fail-closed validator — PASS;
- NYX successor-chain guard + hostile matrix — PASS;
- public repository validation — PASS;
- public repository hygiene — PASS.

## What is actually still missing

The repository side of the raw-lineage gate is now implemented and tested.

The actual nine third-party source bodies have **not** been durably captured into a user-controlled private T1 root in this execution environment. Therefore the repository must not mark the following complete:

- `PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION`;
- ordinary first-slice source-version/raw-hash lineage;
- strict historical replay;
- native signed T5→T6 admission;
- canonical constraint promotion;
- beneficiary qualification.

## Next executable action

On an authorized HYDRA workstation/private data root:

1. capture the exact nine registered source bodies into private staging outside Git;
2. fill the provided capture-plan template with unique source-version IDs and actual acquisition timestamps;
3. execute `python -m hydra_constraint_t1_raw.first_slice_cli`;
4. validate the generated sanitized attestation with `tools/validate_constraint_t1_first_slice_attestation.py`;
5. add only the sanitized attestation/status to the repository;
6. then rerun the native T5→T6 signed-admission gate.

## Truthful status

`REPLAYABLE_WITH_BLOCKERS`

The blocker is no longer missing custody architecture or missing materialization tooling. It is the real private acquisition/materialization event plus subsequent native admission.
