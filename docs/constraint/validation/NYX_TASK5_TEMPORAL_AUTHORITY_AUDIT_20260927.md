# Task 5 — Temporal and authority fail-closed audit

Base: `3cafc16f6a42a2eeeefa74f66a223ca8594374a9` (main inspected on 2026-09-27).
Disposition: bounded repair; two independently reproduced temporal bypasses closed.
No merge, real-source capture, timestamp evidence creation, receipt issuance, or readiness promotion.

## Defects and repair evidence

1. `temporally_eligible` checked only conservative availability and the query cutoff. Direct calls accepted an acquisition value of `TIMESTAMP_UNVERIFIED`, absent/malformed acquisition, backdated availability, and invalid overlay authority flags. Three new regression methods produced 16 failing subcases before repair. The helper now applies the existing overlay validator before deciding temporal eligibility. The tests also verify that inputs are not rewritten.
2. T1 v1 persistence and receipt validation accepted availability before acquisition without an evidence contract. Two new tests failed before repair, including a persisted receipt with a recomputed digest. Both entry points now reject this ordering. Valid equivalent instants with different UTC offsets and later availability remain supported. v1 does not carry historical-availability proof, so a historical exception requires a separately authorized evidence contract, not a caller-supplied date.

Historical manifests remain unchanged. The existing exact-blob supersession map identifies the repaired implementation and tests. Validator strictness is retained.

## Separation and authority findings

- Event/effective time and source publication time remain distinct from acquisition and availability. Existing temporal-audit tests explicitly prohibit using document/event dates as availability.
- Policy replay uses `known_at` and source availability for its cutoff, retaining `effective_at` separately. The Batch020 hostile suite rejects backdating `known_at` to the effective date.
- Timestamp parsing, chronological consistency, byte hashes, and receipt persistence are not independent verification of an acquisition claim. The raw store is network-blind and accepts capture metadata from its authorized caller; this audit does not certify caller evidence or real capture times.
- Missing persisted receipt/release identity cannot grant ordinary T2 eligibility; T1 tests cover forged in-memory receipts/releases, quarantine upgrades, and missing custody records.
- Native T5-to-T6 admission requires a bound signed receipt and verifier. Existing tests reject absent receipt/verifier, invalid signature, mismatched binding, expiry/revocation, and runtime/canonical authority smuggling.
- The dormant adapter refuses runtime execution. Acceptance, confidence, outcome, custody, and successor hostile matrices reject readiness and canonical promotion.

## Unresolved acquisition evidence

The two acquisition timestamps covered by the PR #97 review remain classified **TIMESTAMP_UNVERIFIED**. No timestamp or source record has been changed. The main checkout stores acquisition literals but does not encode that review classification as a `TIMESTAMP_UNVERIFIED` field. Consequently this audit does not claim that those literals are independently verified. Private Windows capture evidence was not accessed; inaccessible evidence is not declared absent. Publication dates, public-page contents, Git times, and filesystem times have not been substituted as acquisition proof.

## Validation

Executed locally with Python 3.12.14 against the repository checkout, using synthetic temporary data. This is repo-side testing, not private Windows execution or a hosted-CI result.

| Check | Result |
| --- | --- |
| T6 complete unittest suite | PASS — 158 tests |
| T1 raw-store complete unittest suite | PASS — 20 tests |
| Policy, physical dependency, replay suites | PASS — 121 tests; 196 subtests |
| First-slice integration validator | PASS — 8 manifests; 57 members |
| First-slice hostile matrix | PASS — 9 cases |
| Strict acceptance validator / hostile matrix | PASS / 11 cases |
| Confidence/evaluation validator / hostile matrix | PASS / 9 cases |
| Outcome coverage validator / hostile matrix | PASS / 10 cases |
| Persisted custody validator / hostile matrix | PASS / 7 cases |
| Lily owner-seam integration | PASS |
| Successor-chain guard / hostile matrix | PASS / 19 cases |
| Batch020 policy temporal hostile suite | PASS — 15 tests |
| Public repository validation / root hygiene | PASS |
| `git diff --check` | PASS |

The tested current-main status remains `IMPLEMENTATION_ADMITTED=NO`, canonical counts zero, and `FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED`. No conclusion is drawn about refreshed PR #62/#64/#96 heads; those are separate reconciliation lanes.
