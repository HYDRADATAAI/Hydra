# HYDRA Constraint AI data center / power — Pass 002 integration rehearsal

Status: VERTICAL_INTEGRATION_THIN. No authority or runtime admission granted.

## Exact inputs

- Repair PR #59: d49f1f46239a1c4b5082214494975f0e26ed3179; tree 727fb9ba10af27645073df5319f707dc4143e9df.
- Physical closure parent: 425ea997853e69bc41265fa1f142112cc7161329.
- T5/T6 owner-seam PR #56: 1c941ad84ceb5b54c9db0eb6d055c9313ff82c88.
- Main inspected: acd44839a2ed97f7a19d637a139d0a6e04ea5eae.

## Verified remote CI on the repair commit

- Public repository hygiene run 36244364411: completed, success.
- Constraint policy integration run 36244364476: completed, success.
- Job 108410660599: package installation, compilation, physical foundation, replay foundation and policy/cross-layer integration all succeeded.
- PR #59 was draft, open, unmerged and conflict-free against its own physical closure base when inspected.

These results apply to the repair commit, not to the combined rehearsal or future mainline.

## Combined local execution

The repair and the exact owner-seam commit merged without conflicts in a detached, isolated checkout. Temporary local merge commit d5cdbfd was used only for rehearsal; it was not published.

Physical, policy, replay and T6 tests together: **268 passed, 417 subtests passed**.

Owner-seam conformance: PASS; 10 claims, 3 T5 candidates, 4 blocked T6 evaluations, zero canonical constraints and zero qualified beneficiaries. Formation confidence and canonical identity remain NOT_EVALUATED; raw lineage and strict acceptance remain BLOCKED.

The rehearsal tests left generated untracked acceptance artifacts in the isolated checkout. None is included in this PR, admitted as authority or used to upgrade readiness.

## Integration failures

### F001 — Historical manifest versus current custody implementation

First-slice integration validator: FAIL.

Batch008 manifest pins:
- path: constraint-t1-raw-artifact-store/src/hydra_constraint_t1_raw/store.py
- expected Git blob: c360aff06500ef19ac2f76e3b5efb9ef7debd90d
- combined checkout / exact owner-seam branch blob: 040af0ee154e3cf6e64a145125fc1254ce170902
- inspected main blob: c360aff06500ef19ac2f76e3b5efb9ef7debd90d

This is a current-implementation versus historical-artifact binding mismatch, not evidence of physical repair failure. Preserve Batch008. The successor validator/manifest owner must explicitly distinguish immutable historical artifact verification from current implementation admission; blindly repinning or ignoring the digest is not a fix.

### F002 — Mainline authority reconciliation conflicts

Merging inspected main into the combined checkout produced add/add conflicts in:
- docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_MASTER_STATUS_V001_20260925.json
- docs/constraint/first_slice/ai_data_center_power_infrastructure_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_AI_DATA_CENTER_POWER_INFRASTRUCTURE_STRICT_ACCEPTANCE_GATE_V001_20260925.json
- docs/constraint/validation/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH014_ARTIFACT_MANIFEST_V001_20260925.json

The main merge was aborted. Neither side was selected by timestamp and no historical authority file was overwritten. The current successor authority owner must reconcile these versions through an explicit successor mapping.

## Next dependency order

1. Resolve the exact Batch014 authority/manifests across main and owner-seam work without rewriting predecessor authority.
2. Repair current-versus-historical custody manifest binding through its existing successor validation owner.
3. Rerun combined first-slice acceptance in a clean checkout and integrate the physical repair through the existing branch stack.
4. Continue real source materialization and signed native T5/T6 admission before ordinary replay.
5. Only then close the representative chip/power/water vertical evidence and query gaps.

No public PR was merged or retargeted. No additional graph, schema, confidence policy, historical evidence record or canonical entity was created. V1 remains unfrozen.
