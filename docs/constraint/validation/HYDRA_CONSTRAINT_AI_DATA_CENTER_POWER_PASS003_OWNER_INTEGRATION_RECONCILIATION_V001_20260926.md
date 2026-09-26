# HYDRA Constraint AI/data-center/power — Pass 003 owner integration

Status: **VERTICAL_INTEGRATION_THIN**. The two Pass002 repository integration failures are resolved in this candidate. Ordinary replay and the full requested vertical remain blocked. This is a proposed branch integration, not mainline admission.

## Authority selection and preservation

Base: Thread6 Batch016 `cb866ead19948942558b926f11925bf54e1741b4`, which explicitly succeeds Batch015 on main `acd44839a2ed97f7a19d637a139d0a6e04ea5eae`.

Physical/policy/replay stack: PR59 `cd3752edfdee3a8829adfb470c4c585b61f37f55`, including the tested physical repair. These branches merge cleanly.

Owner-seam source: PR56 `1c941ad84ceb5b54c9db0eb6d055c9313ff82c88`. Reuse its exact candidate temporal/identity overlay and executable validator entry point. Adapt its existing conformance module and tests to mainline's immutable Batch014 dimension gate. Do not import the conflicting branch-local Batch014 gate/master/manifest or unrelated materialization work. No new semantic owner is introduced.

All existing Batch003–Batch016 docs at the base remain unchanged. The imported overlay retains its exact predecessor pin and later availability time. It does not supersede Batch015 typed-confidence readiness or retroactively populate confidence. Historical Batch014 remains blocked; Batch015/016 confidence semantics remain ready with explicit unknowns. The distinction is preserved by running both existing acceptance validators.

## F001 resolved by reuse

Batch016 already declares the exact custody store predecessor `c360aff06500ef19ac2f76e3b5efb9ef7debd90d` → successor `040af0ee154e3cf6e64a145125fc1254ce170902` mapping. Its existing validator now passes in the combined tree. No hash was edited, ignored or repinned by this pass. Historical Batch008 is unchanged.

## F002 resolved in the consumer

The old owner-seam validator expected a branch-local `gates`/`overall_result` representation. Reproduced failure against mainline: `Batch014 strict constraint-formation gate is not fail-closed`.

The existing module now consumes the canonical `dimensions` shape, checks its exact schema/record/slice identity, requires BLOCKED implementation admission and both native/canonical admission blockers, and requires blocked overall/run state. It rejects mixed legacy representations. Canonical IDs and qualified beneficiaries remain forbidden by the existing checks. No historical gate/master/manifest was rewritten.

Two original negative tests now mutate the actual authoritative fields. Added tests reject ten shape/identity/run-state mutations and removal of the native admission blocker. Existing candidate/beneficiary lineage and no-backdating tests remain active.

## Validation

- Combined physical, policy, replay, T1 custody and T6 suites: **282 tests, 427 subtests passed**.
- Owner-seam targeted suite: 14 tests, 10 subtests passed (included above).
- First-slice integration, owner seams, historical Batch014 acceptance, Batch015 typed-confidence/evaluation, and NYX successor chain through Batch016: PASS.
- Existing hostile matrices: 9 first-slice + 11 strict acceptance + 9 confidence/evaluation cases PASS.
- Default pytest import collection initially collided on multiple `tests` packages. `--import-mode=importlib` resolved test discovery without changing production packages; the integrated CI uses that mode.
- Existing first-slice CI now invokes the reused owner-seam validator. Added combined-owner CI executes all five packages and the five validators together.

Local test counts do not imply remote CI success for a future published commit. Remote results must be read against its exact SHA.

## Remaining blockers and scope

Real nine-source raw materialization, complete ordinary source-version lineage, signed native T5→T6 admission, acceptance-grade outcomes and the requested joined facility/compute/chip/water evidence remain incomplete. The physical graph remains structural; neither importing it nor passing its tests grants T5/T6 formation, canonicalization or beneficiary authority. No real evidence, capacity estimate, lifecycle state, source timestamp, confidence number or canonical identity was invented.

V1 is not frozen. Next work should consume the current materialization/outcome owner lanes and source evidence, not re-create graph or authority schemas.
