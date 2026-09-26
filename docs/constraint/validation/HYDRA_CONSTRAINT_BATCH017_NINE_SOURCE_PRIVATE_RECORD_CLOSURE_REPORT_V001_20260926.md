# HYDRA Constraint — Batch017 Nine-Source Discovery + Private-Record Closure
## Source/private-record dependency only — 2026-09-26

PR: #64  
Stacked on: Batch017 / PR #62  
Branch: `constraint/t1-private-record-source-discovery-20260926`

## Scope

This pass takes only the remaining source-discovery/private-record dependency for the exact nine registered AI/data-center power first-slice sources.

It does not modify:
- Batch017 outcome records;
- evaluation protocol or thresholds;
- canonical constraint admission;
- beneficiary qualification;
- native signed T5→T6 admission.

## Source discovery

The exact nine registered locators were checked against their authoritative public endpoints.

Result:
- registered sources: 9;
- exact registered locators currently resolved: 9;
- missing registered sources: 0;
- locator substitutions required: 0.

The registered locators remain authoritative acquisition targets. Related PDFs, data files, DOI pages, or publisher mirrors do not silently replace them.

Two registered locators are direct PDFs:
- DOE Large Power Transformer Resilience Report;
- NERC Long-Term Reliability Assessment.

The remaining seven are HTML pages.

Existing temporal semantics remain unchanged:
- DOE LPT July 2024 is a document/cover date, not proof of public `available_at`;
- DOE transformer webinar March 5, 2026 is an event date, not automatically publication/availability time;
- NERC remains assessment year 2025 with the existing Batch005 correction to January 2026 report/release month;
- current reachability does not prove historical availability.

## Private-record gap found

Batch017 was still carrying the earlier public raw-store implementation snapshot:

`hydra-constraint-t1-raw-artifact-store 0.1.0`

That implementation validated caller-supplied receipt/release objects structurally but did not require them to be the exact persisted custody records.

The hardened persisted-custody implementation already existed separately and is reconciled here as:

`hydra-constraint-t1-raw-artifact-store 0.2.0`

Ordinary T1→T2 eligibility now requires:
- raw artifact bytes and matching SHA-256;
- exact persisted source-version receipt identity;
- exact persisted release-manifest identity;
- exact release membership;
- `ELIGIBLE` processing disposition;
- private-root containment outside public Git.

A self-consistent in-memory reconstruction is not authority.

## Exact-nine-source private materialization path

Added the network-blind offline first-slice materializer.

It:
- consumes the authoritative nine-source registry;
- requires all nine and only those nine;
- rejects duplicate, missing, extra, or unregistered sources;
- requires each capture locator to exactly match the registry;
- rejects raw input files inside the public repository;
- writes only through the private T1 custody store;
- writes exact persisted receipts and one exact persisted release;
- checks ordinary T1→T2 eligibility against those persisted records;
- supports `QUARANTINED` / `INELIGIBLE` without promoting them.

Existing private root:

`D:\HYDRA_PRIVATE\constraint\raw`

## Temporal guardrail

The private materializer uses only:

`AVAILABLE_AT = ACQUIRED_AT`

for this first conservative capture.

It rejects caller-supplied `available_at`.

Therefore actual local materialization will establish durable current source-version custody and hashes, but it will not fabricate earlier historical availability.

## Sanitized public attestation

A private execution can emit a sanitized attestation containing:
- source IDs;
- source-version IDs;
- artifact SHA-256;
- receipt SHA-256;
- byte lengths;
- acquisition/availability timestamps;
- persisted release ID/hash;
- ordinary-T2 eligibility state.

The validator rejects:
- private path leakage;
- raw-byte fields;
- source-set drift;
- digest tampering;
- release-hash mismatch;
- historical backdating;
- replay/canonical promotion claims.

Raw third-party bodies remain outside Git.

## Validation

Source/private-record suite:
- 42 tests: PASS;
- replay-lineage derivation/no-lookahead tests: 5/5 PASS;
- exact registry/plan/discovery alignment: PASS;
- persisted receipt authority: PASS;
- persisted release authority: PASS;
- forged receipt/release authority: blocked;
- quarantine reconstruction: blocked;
- raw public-path capture: blocked;
- source-locator substitution: blocked;
- missing/extra source set: blocked;
- conservative anti-backdating: PASS;
- sanitized attestation validation: PASS.

Constraint first-slice integration and hostile matrices: PASS.

Public repository hygiene: PASS.

The inherited Batch017 real-outcome report manifest pin was repaired on PR #62 without changing report semantics. PR #64 then consumed that repaired base. NYX successor-chain validation and its hostile matrix now PASS on the current source/private branch.

## What remains external/private

Source discovery is complete.

The actual nine source bodies have not been materialized by this chat/session into the workstation private root. Therefore these remain open:

- `PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION`;
- `ORDINARY-POINT-IN-TIME-REPLAY-SOURCE-VERSION-HASHES-INCOMPLETE`.

Separately, native T5→T6 admission remains blocked by the absent signed admission receipt.

## Truthful state

Source-discovery repo lane: `COMPLETE`

Private-record tooling/custody lane: `READY_FOR_LOCAL_EXECUTION`

Actual private source-version materialization: `NOT_EXECUTED`

Ordinary replay: `BLOCKED`

Canonical admission: `BLOCKED`

No new outcome or evaluation threshold was introduced.


## Replay-lineage preparation

A deterministic sanitized replay-lineage builder is now included for the step
immediately after private materialization/attestation.

It consumes only the validated public-safe attestation and registry, then binds:

- exact source IDs and source-version IDs;
- artifact SHA-256 and receipt SHA-256;
- persisted release ID/hash;
- conservative acquisition/availability timestamps;
- deterministic availability boundaries;
- as-of membership under `SOURCE_VISIBLE_IFF_AVAILABLE_AT_LTE_AS_OF`.

The builder refuses incomplete or quarantined source sets and preserves the
historical boundary:

- ordinary current source-version lineage can become complete after actual
  nine-source materialization;
- strict historical replay remains **NO** under conservative first-capture
  availability;
- no pre-capture visibility is inferred;
- no native T5→T6 or canonical admission is granted.

Current execution state remains unchanged because no real sanitized
materialization attestation exists in this session:

`ACTUAL_REPLAY_LINEAGE_PACKET_BUILT=NO`.
