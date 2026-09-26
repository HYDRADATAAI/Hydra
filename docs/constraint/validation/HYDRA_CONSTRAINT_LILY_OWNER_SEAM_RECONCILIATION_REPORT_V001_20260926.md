# HYDRA CONSTRAINT — Lily Owner-Seam Reconciliation Report
## T5 Constraint Formation → T6 Canonical / Beneficiary Boundary
Date: 2026-09-26
PR: #56
Branch: `constraint/lily-owner-seam-reconciliation-v1-20260926`
Stacked base: `constraint-t6-successor-batch014-strict-acceptance-20260925`

## Mission result

This pass did not add another constraint, beneficiary, identity, replay, or provenance subsystem.

It located and reused the existing authoritative Thread-6 successor implementation artifacts for:

- T5 constraint-candidate formation;
- T6 beneficiary evaluation;
- Thread-3 canonical/beneficiary policy binding;
- T1→T2 persisted chain-of-custody;
- Batch-14 strict acceptance.

The pass then closed one concrete representation defect in the current T5 shadow-candidate handoff without rewriting Batch 010.

## Existing owners confirmed

### T5

Batch 010 is explicitly produced under:

`PIPELINE_T5_CONSTRAINT_FORMATION`

It contains three immutable reviewed-shadow candidate proposals. None has a canonical constraint ID and none is ordinary-T6 eligible.

### T6

Batch 010 beneficiary evaluation is explicitly consumed under:

`PIPELINE_T6_CANONICAL_CANDIDATE_GOVERNANCE`

It pins:

`LILY_THREAD_3_MASTER_CLOSURE_BUNDLE@ab7e4c05c9210a90256b8cdea89eeb9f3bb551453dfe13ebfe44616f750cb366`

Four beneficiary relationships exist as blocked evaluations. Zero are qualified.

### T1→T2 custody

The current Batch-14 strict gate now reports:

`PERSISTED_T1_CHAIN_OF_CUSTODY = PASS`

This materially narrows the older provenance-owner blocker. The implementation now requires exact persisted source-version receipts and release-manifest identity.

It does **not** mean the nine first-slice raw source bodies have been materialized. Raw provenance and complete replay lineage remain blocked.

## Concrete defect found

The Batch-10 T5 candidate artifact has mechanism, constrained target, scope, claim/evidence roles, canonical-ID null state, and ordinary-T6 blockers.

However, candidate rows do not explicitly carry:

- per-candidate `available_at`;
- typed T5 formation-confidence state;
- explicit unresolved effective interval;
- explicit canonical-identity evaluation state.

Leaving those dimensions implicit creates four failure risks:

1. later interpretation can be accidentally backdated;
2. missing formation confidence can be interpreted as zero/high/default confidence;
3. `CURRENT` can be misread as a known effective interval;
4. a null canonical ID can be misread as resolved-distinct instead of not-yet-evaluated.

## Repair

Added:

`HYDRA_CONSTRAINT_LILY_OWNER_SEAM_RECONCILIATION_T5_CANDIDATE_TEMPORAL_IDENTITY_OVERLAY_V001_20260926.json`

The overlay:

- pins the exact unchanged Batch-10 candidate Git blob;
- receives its own later `available_at`;
- does not reconstruct an earlier candidate availability time;
- sets `formation_confidence = null`;
- sets `formation_confidence_state = NOT_EVALUATED`;
- leaves `effective_from/effective_to = null`;
- marks effective state `UNRESOLVED_NOT_FABRICATED`;
- keeps `canonical_constraint_id = null`;
- marks canonical identity `NOT_EVALUATED`;
- preserves incomplete T1/T2 lineage as blocking;
- preserves ordinary-T6 eligibility as false;
- copies the existing admission/materialization blockers without deleting or weakening them.

No predecessor artifact was edited.

## New conformance gate

Added `owner_seam_conformance.py`, a standalone validator, CI integration, and hostile regression coverage.

The gate proves:

- only T5 forms the candidate rows;
- T5 cannot mint a canonical constraint ID;
- T5 cannot smuggle authoritative beneficiary fields;
- every candidate retains mechanism, target, scope, and valid claim/evidence references;
- successor availability cannot predate required parent-claim availability;
- missing formation confidence remains `NOT_EVALUATED`;
- unknown effective intervals remain unknown;
- canonical identity remains explicitly not evaluated;
- beneficiary relationship IDs remain separate from company/candidate/constraint IDs;
- T6 beneficiary constraint evidence must derive from the parent candidate's constraint-support evidence;
- an ordinary-ineligible parent forces beneficiary qualification to remain blocked;
- Batch-13 shadow prequalification cannot fabricate economic capture;
- Batch-14 constraint formation and beneficiary qualification cannot be converted from strict FAIL to PASS merely because shadow coverage exists.

## CI evidence

Code-bearing head:

`307e64f6f3216c0e48ca8bc9aa80ace953c13911`

All relevant lanes passed:

- T6 fail-closed validator run 58 / run ID 36243474345 — **PASS**, 147 tests;
- Constraint first-slice integration run 27 / run ID 36243474341 — **PASS**;
- Lily owner-seam standalone conformance — **PASS**;
- first-slice hostile mutation matrix — **PASS**;
- NYX successor-chain guard run 10 / run ID 36243474348 — **PASS**;
- NYX hostile successor-chain mutation matrix — **PASS**;
- public repository validation run 60 — **PASS**;
- public repository hygiene run 141 — **PASS**.

Observed owner state remained:

- claims: 10;
- shadow T5 candidates: 3;
- T6 beneficiary evaluations: 4;
- canonical constraints: 0;
- qualified beneficiaries: 0;
- strict acceptance: BLOCKED.

## Current Batch-14 acceptance after custody update

Current strict gate:

- PASS: 9;
- FAIL: 7;
- overall: `BLOCKED`.

The added PASS is persisted T1→T2 chain-of-custody. The remaining failures are not semantic-owner ambiguity.

## Remaining blockers

### Raw evidence / historical replay

- `PIT-002B-FIRST-SLICE-NINE-SOURCE-RAW-CAPTURE-MATERIALIZATION`
- `ORDINARY-POINT-IN-TIME-REPLAY-SOURCE-VERSION-HASHES-INCOMPLETE`

The custody system exists, but the real first-slice source bodies and immutable source-version hash chain are not yet materialized.

### Native T5→T6 admission

- `CI-TEST-008-BLOCKER-001B-NATIVE-T5-T6-SIGNED-ADMISSION-RECEIPT-ABSENT`
- `CANONICAL-T5-T6-CONSTRAINT-AND-BENEFICIARY-ADMISSION-NOT-AUTHORIZED`

Therefore shadow candidates cannot become ordinary-T6 candidates, no canonical constraint can be minted, and no beneficiary can be qualified.

### Physical-domain branch integration

Historical Geography / Strategic Assets / Resource Dependency closure remains in PR #46 on its separate stack.

This pass does not copy those objects into Thread 6, because doing so would create duplicate architecture and bypass normal repository integration.

## Readiness

`REPLAYABLE_WITH_BLOCKERS`

Owner semantics are no longer the reason this slice is blocked.

The next legitimate closure action is operational evidence/admission work:

1. materialize the real first-slice source versions through the authoritative T1 custody path;
2. establish complete source-version/raw hashes and ordinary PIT eligibility;
3. execute the native signed T5→T6 admission path;
4. only then permit canonical constraint or beneficiary qualification logic to advance;
5. integrate PR #46 through normal branch/PR reconciliation rather than cloning its physical graph into this stack.

No further geography/resource taxonomy expansion is justified by this owner-seam pass.
