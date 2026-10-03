# HYDRA Constraint semiconductor Pass 003 — owner lineage validation repair

Base: `07e03eeede02e77c3076a75aef274f3f8b424158` (main).
Predecessor authority recovery: published Pass 002, commit `2a945efa1fde2025317c68d27fe396222475f32d`.

## Concrete failure and repair

The existing `hydra_t6_failclosed.owner_seam_conformance.validate_owner_seams` returned `PASS_CURRENT_FAIL_CLOSED_OWNER_SEAMS` after either of these independent mutations to the committed first-slice inputs:

1. Append `UNRESOLVED-NOT-A-REFERENCE` to the first candidate's `evidence_roles.demand_context`.
2. Append `EV-NONEXISTENT` to the first beneficiary's `evidence_lineage.disconfirming_or_blocking`.

Candidate roles previously checked membership only when the string happened to start with a recognized prefix. Beneficiary blocker entries were not checked. Some malformed containers could also iterate as empty collections or raise raw Python type errors.

The existing validator now requires candidate evidence references to resolve to the supplied claim/evidence universe, checks reference-shaped beneficiary blocker entries, checks lineage collection/member types, rejects absent/empty candidate role mappings, and rejects non-object rows with `OwnerSeamConformanceError`. No runtime object, graph, identity service or provenance policy was added.

Batch010 beneficiary blocker lists contain prose research limitations as well as possible references. Those existing notes remain valid notes; they are not promoted into evidence. Empty lists remain allowed for the blocked beneficiary hypotheses. This patch does not pretend that all five causal links are complete or that an ineligible beneficiary is qualified.

## Authority alignment and current integration state

Recovered Thread-3 Batch 7 sections 8, 19, 26–30 and 33 require queryable evidence linkage, supported causal links and distinct missing/empty states. Batch 8 Decisions 304–305 preserve T5 candidate versus T6 canonical ownership. These references explain the repair; the test target is the existing first-slice conformance validator, not the entire Batch-9 campaign.

Main now contains Thread-6 Batch017 semiconductor scope, authority map, 60 field requirements and 14 required cases. Pass003 reuses that scope instead of constructing another semiconductor envelope. Its `NEXT_REPO_EXECUTABLE_LANE` remains `SECOND-SLICE-SOURCE-AUTHORITY-AND-FIRST-POPULATION`.

## Validation

- Existing owner-boundary test module: 19 tests passed, including 8 added regression methods with malformed-input subcases.
- Complete T6 test suite: 149 tests passed.
- `python3 tools/validate_constraint_lily_owner_seams.py`: PASS; 10 claims, 3 candidates, 4 beneficiary evaluations; zero canonical constraints and zero qualified beneficiaries; Batch016 strict acceptance BLOCKED.
- `python3 tools/validate_constraint_second_slice_batch017_audit.py`: PASS; 60 field requirements, 14 required cases; no semiconductor population; first semiconductor run BLOCKED.
- Existing owner-conformance and T6 CI workflows already execute the modified tests; no duplicate workflow added.

Reference membership here means membership in the supplied claim artifact's declared evidence universe. It does not prove raw artifact custody, independent source corroboration or canonical identity resolution. Those owner implementations and admission evidence remain separate dependencies. No readiness flag, semantic closure, historical authority artifact or capability-ledger entry was upgraded.

Next: populate the Batch017 source-authority registry and first evidence-backed records through existing acquisition/provenance boundaries, then run the required semiconductor cases. Canonical identity and ordinary runtime admission still require their own proven implementations; this repair is a prerequisite validation improvement only.
