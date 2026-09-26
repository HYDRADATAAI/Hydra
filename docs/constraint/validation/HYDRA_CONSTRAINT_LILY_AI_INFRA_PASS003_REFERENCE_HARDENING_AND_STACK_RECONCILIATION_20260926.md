# HYDRA Constraint Lily AI infrastructure Pass003

Status: VERTICAL_INTEGRATION_THIN. Ordinary replay remains blocked.

## Implemented

Carries forward Pass002 commit 57253ee without modifying predecessor reports. Repairs additional reference-type confusion in the existing shadow replay owner: candidate and outcome claim references must resolve to visible claims, not evidence IDs. Relief claim and evidence references resolve in their respective namespaces. Lineage arrays reject scalar or malformed references. Beneficiary mixed lineage retains its existing contract.

Four added regression methods failed before their respective repairs. The final verification runs all 166 T6 tests, successor integration, Lily owner seams and the hostile mutation matrix. The machine-readable Pass003 receipt records actual outputs. No native admission or production activation is granted.

## Stack reconciliation attempted

Fetched repository state on 2026-09-26. Main was acd44839a2ed97f7a19d637a139d0a6e04ea5eae. Direct cherry-pick to main conflicted in the workflow and lacks the required owner-seam implementation; aborted without changing main.

Applied Pass002 to updated owner-seam tip 1c941ad in an isolated local branch. All 162 T6 tests passed but successor integration failed: Batch008 manifest expected store.py Git blob c360aff06500ef19ac2f76e3b5efb9ef7debd90d, while the updated stack has 040af0ee154e3cf6e64a145125fc1254ce170902. No historical manifest was changed to hide the mismatch. This newer-stack trial is not qualified for integration.

The review base is therefore pinned to b79a8533a94d8101e213e5971066f8518cf3742d, the original tested owner-seam parent. The repair is submitted as a stacked draft against that preserved base; it is not a mainline integration or permission to merge. Reviewers must reconcile the newer T1 custody stack and historical/current manifest semantics before promoting the whole stack.

## Remaining gates

Physical/policy owner reconciliation remains unresolved; no physical graph code was copied into T6. Private raw-source materialization, immutable lineage, native signed T5/T6 admission, facility identity/capacity/lifecycle bindings and complete historical A–E cases remain blockers. No source bodies, private fixtures, policy authorities or sealed reviews were added. No V1 freeze or readiness upgrade.
