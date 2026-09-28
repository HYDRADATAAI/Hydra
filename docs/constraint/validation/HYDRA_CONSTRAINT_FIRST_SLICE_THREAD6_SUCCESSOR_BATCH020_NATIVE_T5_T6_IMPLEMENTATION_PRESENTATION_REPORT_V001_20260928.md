# HYDRA CONSTRAINT — First Slice Thread 6 Successor Batch020 Native T5→T6 Implementation Presentation

**Slice:** `AI_DATA_CENTER_POWER_INFRASTRUCTURE_V1`  
**Predecessor:** Batch019  
**Result target:** `PASS_IMPLEMENTATION_PRESENTED_AUTHORITY_RECEIPT_STILL_REQUIRED`

## What Batch020 adds

Batch020 closes the repository-side prerequisite identified by Batch019: an exact native T5→T6 implementation is now presented for admission review.

The implementation is a pure deterministic bridge. It accepts the existing governed T5 candidate-proposal record plus the V002 temporal/identity overlay and emits the existing `t6-candidate-handoff.v1` / `constraint-candidate.v2` shape.

It does not perform I/O, registration, ranking, canonicalization, beneficiary qualification, canonical-store mutation, runtime activation, live-source acquisition, model training, trading, or any other external effect.

## Exact admission bindings

- implementation id: `HYDRA_CONSTRAINT_FIRST_SLICE_NATIVE_T5_T6_BRIDGE_V001_20260928`
- artifact: `t6-fail-closed-validator/src/hydra_t6_failclosed/native_t5_t6_bridge.py`
- artifact SHA-256: `e090e1326ee4ff03fca378925b1316dd3c870ccf70a9fe313c9c8fb1e00e476f`
- test evidence: `t6-fail-closed-validator/tests/test_native_t5_t6_bridge.py`
- test-evidence SHA-256: `d614733a65943334ab9a2f5c41b7b94b2d8a111d23953b79622a975d5a636294`
- producer: `PIPELINE_T5_CONSTRAINT_FORMATION`
- consumer: `PIPELINE_T6_CANONICAL_CANDIDATE_GOVERNANCE`
- handoff schema: `t6-candidate-handoff.v1`
- candidate schema: `constraint-candidate.v2`

The implementation manifest requests no runtime activation, canonical promotion, or live-source authority.

## Fail-closed semantics

The bridge rejects:

- T5 input claiming canonicalization;
- a non-null preexisting canonical constraint identity;
- candidate-set drift between T5 and the temporal overlay;
- T5/overlay eligibility disagreement;
- ineligibility-reason drift;
- invalid evidence-role structures;
- mismatched T5/T6 owner bindings;
- timestamps that would make the handoff precede candidate availability.

The current first-slice ambiguity and unknown effective intervals are transported unchanged rather than resolved.

## Remaining authority boundary

Batch020 does **not** issue or self-sign the admission receipt.

The implementation-admission gate must still receive a current, non-revoked, artifact-bound signed receipt from the `IMPLEMENTATION_CONTRACT` authority before it can return `ADMITTED_EXACT_ARTIFACT`.

Even such an admission would not authorize runtime activation, canonical promotion, live sources, model training, or trading.

## Separate historical gate

The nine-source T1 materialization remains complete for current captured versions, but exact pre-acquisition historical availability is still unproven. Strict original-as-of replay therefore remains blocked and is not closed by this implementation work.

```ini
BATCH020_NATIVE_IMPLEMENTATION_PRESENTED=YES
IMPLEMENTATION_ARTIFACT_SHA256=e090e1326ee4ff03fca378925b1316dd3c870ccf70a9fe313c9c8fb1e00e476f
TEST_EVIDENCE_SHA256=d614733a65943334ab9a2f5c41b7b94b2d8a111d23953b79622a975d5a636294
SIGNED_IMPLEMENTATION_CONTRACT_RECEIPT=ABSENT
IMPLEMENTATION_ADMITTED=NO
RUNTIME_ACTIVATION_AUTHORIZED=NO
CANONICAL_PROMOTION_AUTHORIZED=NO
STRICT_HISTORICAL_REPLAY=BLOCKED
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
```
